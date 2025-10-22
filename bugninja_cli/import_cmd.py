"""
Import command for Bugninja CLI.

This module provides the **import command** for creating test cases from various file formats.
It reads files from a source directory and maps their contents for AI-powered test case generation.

## Key Features

1. **Multi-format Support** - Reads Excel, CSV, DocX, PDF, Gherkin, Python, TypeScript, JavaScript, and TOML files
2. **Recursive Reading** - Traverses all subdirectories to find relevant files
3. **Size Filtering** - Skips files larger than 5MB with warnings
4. **Error Handling** - Gracefully handles unreadable files with appropriate warnings
5. **Content Mapping** - Maps file paths to their raw string contents

## Usage Examples

```bash
# Import from a directory
bugninja import /path/to/test-specs

# Import from current directory
bugninja import ./test-files
```
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import rich_click as click
from pydantic import ValidationError
from rich import print as rich_print
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bugninja_cli.utils.project_validator import require_bugninja_project
from bugninja_cli.utils.style import MARKDOWN_CONFIG

if TYPE_CHECKING:
    from bugninja.agents.test_case_creator import TestCaseCreatorAgent
    from bugninja.schemas.test_case_creation import TestCaseCreationOutput
    from bugninja.schemas.test_case_import import TestScenario
    from bugninja.schemas.test_case_io import TestCaseSchema
    from bugninja_cli.utils.task_manager import TaskManager


def generate_file_aliases(file_paths: List[Path]) -> Tuple[Dict[str, Path], Dict[Path, str]]:
    """Generate file aliases using actual file names with conflict resolution.

    This function creates aliases using the real file names (e.g., 'login.py', 'user_data.csv')
    while handling conflicts by adding minimal path context when needed.

    Args:
        file_paths (List[Path]): List of file paths to generate aliases for

    Returns:
        Tuple[Dict[str, Path], Dict[Path, str]]: (alias_to_path, path_to_alias) mappings

    Example:
        ```python
        files = [Path("src/auth/login.py"), Path("tests/login.py"), Path("data/users.csv")]
        alias_to_path, path_to_alias = generate_file_aliases(files)
        # Result: {"login.py": Path("src/auth/login.py"), "test_login.py": Path("tests/login.py"), "users.csv": Path("data/users.csv")}
        ```
    """
    alias_to_path: Dict[str, Path] = {}
    path_to_alias: Dict[Path, str] = {}
    name_conflicts: Dict[str, int] = {}

    for file_path in file_paths:
        # Use the actual file name as the base alias
        base_name = file_path.name

        # Check for conflicts and resolve
        if base_name in alias_to_path:
            # Use parent folder context for conflict resolution
            parent = file_path.parent.name
            if parent in name_conflicts:
                name_conflicts[parent] += 1
            else:
                name_conflicts[parent] = 1

            # Create alias with parent context: parent_filename.ext
            alias = f"{parent}_{base_name}"
        else:
            alias = base_name

        # Double-check for conflicts after resolution
        if alias in alias_to_path:
            # If still conflicted, use a unique suffix
            name_without_ext = file_path.stem
            ext = file_path.suffix
            alias = f"{name_without_ext}_dup{ext}"

        alias_to_path[alias] = file_path
        path_to_alias[file_path] = alias

    return alias_to_path, path_to_alias


console = Console()

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    # Excel files
    ".xlsx",
    ".xls",
    # CSV files
    ".csv",
    # DocX files
    ".docx",
    # PDF files
    ".pdf",
    # Gherkin files
    ".feature",
    # Python files
    ".py",
    # TypeScript files
    ".ts",
    # JavaScript files
    ".js",
    # TOML files
    ".toml",
    # JSON files
    ".json",
    # TXT files
    ".txt",
}

# File size limit (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes


def is_supported_file(file_path: Path) -> bool:
    """Check if a file has a supported extension.

    Args:
        file_path (Path): Path to the file to check

    Returns:
        bool: True if file has supported extension, False otherwise
    """
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS


def get_file_size(file_path: Path) -> int:
    """Get the size of a file in bytes.

    Args:
        file_path (Path): Path to the file

    Returns:
        int: File size in bytes, 0 if file doesn't exist
    """
    try:
        return file_path.stat().st_size
    except (OSError, FileNotFoundError):
        return 0


def read_file_content(file_path: Path) -> str:
    """Read the content of a file as a string.

    Args:
        file_path (Path): Path to the file to read

    Returns:
        str: File content as string

    Raises:
        OSError: If file cannot be read
        UnicodeDecodeError: If file cannot be decoded as text
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding for files that might not be UTF-8
        try:
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
        except UnicodeDecodeError:
            raise UnicodeDecodeError(
                "utf-8",
                b"",
                0,
                1,
                f"Could not decode file {file_path} with UTF-8 or Latin-1 encoding",
            )


def read_project_description(project_root: Path) -> str:
    """Read project description from PROJECT_DESC.md file.

    Args:
        project_root (Path): Root directory of the Bugninja project

    Returns:
        str: Project description content

    Raises:
        FileNotFoundError: If PROJECT_DESC.md file is not found
    """
    project_desc_file = project_root / "PROJECT_DESC.md"

    if not project_desc_file.exists():
        raise FileNotFoundError(
            f"PROJECT_DESC.md not found in project root: {project_root}\n"
            "Please create this file with a description of your website/application for testing."
        )

    try:
        with open(project_desc_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        raise RuntimeError(f"Failed to read PROJECT_DESC.md: {e}")


def scan_directory_for_files(source_path: Path) -> Dict[str, str]:
    """Recursively scan a directory for supported files and read their contents.

    Args:
        source_path (Path): Path to the source directory

    Returns:
        Dict[str, str]: Dictionary mapping file paths to their contents
    """
    file_contents: Dict[str, str] = {}
    skipped_files: List[str] = []
    oversized_files: List[str] = []
    error_files: List[Tuple[str, str]] = []

    # Walk through all files recursively
    for root, dirs, files in os.walk(source_path):
        for file in files:
            file_path = Path(root) / file

            # Check if file has supported extension
            if not is_supported_file(file_path):
                continue

            # Check file size
            file_size = get_file_size(file_path)
            if file_size > MAX_FILE_SIZE:
                oversized_files.append(str(file_path))
                console.print(
                    f"⚠️  Skipping oversized file: {file_path} ({file_size / (1024*1024):.1f}MB)"
                )
                continue

            # Try to read file content
            try:
                content = read_file_content(file_path)
                file_contents[str(file_path)] = content
                console.print(f"✅ Read file: {file_path}")
            except (OSError, UnicodeDecodeError) as e:
                error_files.append((str(file_path), str(e)))
                console.print(f"❌ Could not read file: {file_path} - {e}")
                continue

    # Print summary
    if skipped_files or oversized_files or error_files:
        summary_text = Text()
        summary_text.append("📊 Import Summary:\n\n", style="bold")

        if file_contents:
            summary_text.append(
                f"✅ Successfully read: {len(file_contents)} files\n", style="green"
            )

        if oversized_files:
            summary_text.append(
                f"⚠️  Oversized files skipped: {len(oversized_files)}\n", style="yellow"
            )

        if error_files:
            summary_text.append(f"❌ Files with errors: {len(error_files)}\n", style="red")

        console.print(Panel(summary_text, title="Import Summary", border_style="blue"))

    return file_contents


@click.command()
@click.rich_config(help_config=MARKDOWN_CONFIG)
@click.argument(
    "source_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
)
@click.option(
    "--mode",
    type=click.Choice(["import", "generate"]),
    default="import",
    help="Mode of operation: 'import' for file-based analysis, 'generate' for AI-generated test cases",
)
@click.option(
    "-n",
    type=int,
    default=None,
    help="Number of test cases: in import mode, limit to first N found (default: all); in generate mode, number to create (default: 4)",
)
@click.option(
    "--p-ratio",
    "p_ratio",
    type=float,
    default=0.75,
    help="Positive test case ratio (0.0-1.0, only valid in generate mode, default: 0.75)",
)
@click.option(
    "--extra",
    type=str,
    default="",
    help="Extra instructions for agents to customize test case generation (text must be in quotations)",
)
@click.option(
    "--expected-inputs",
    type=str,
    default=None,
    help='JSON string defining expected inputs for the test case (e.g., \'{"USER_EMAIL": "test@example.com"}\')',
)
@click.option(
    "--expected-outputs",
    type=str,
    default=None,
    help='JSON string defining expected outputs for extraction (e.g., \'{"USER_ID": "user ID from login"}\')',
)
@require_bugninja_project
def import_cmd(
    source_path: Optional[Path],
    project_root: Path,
    mode: str,
    n: int,
    p_ratio: float,
    extra: str,
    expected_inputs: Optional[str],
    expected_outputs: Optional[str],
) -> None:
    """Import or generate test cases.

    This command supports two modes:
    1. **Import mode**: Reads files from source directory and generates test cases from analysis
    2. **Generation mode**: Creates test cases from scratch using project description

    Args:
        source_path (Path): Path to the source directory (required for import mode)
        project_root (Path): Root directory of the Bugninja project
        mode (str): Mode of operation ('import' or 'generate')
        n (int): Number of test cases to generate
        extra (str): Extra instructions for agents (must be in quotations)

    Raises:
        click.Abort: If operation fails or parameters are invalid

    Example:
        ```bash
        # Import mode (default)
        bugninja import /path/to/test-specs
        bugninja import /path/to/test-specs -n 3 --extra "Focus on mobile testing"

        # Generation mode
        bugninja import --mode generate -n 5 --extra "Generate e-commerce test cases"
        ```

    Notes:
        - Import mode: Only reads files with supported extensions
        - Generation mode: Creates test cases from project description
        - Both modes support parallel test case generation
        - Extra instructions are passed to all agents
    """
    # Parse unified schema from JSON strings
    schema: Optional[TestCaseSchema] = None

    if expected_inputs or expected_outputs:
        try:
            input_schema = json.loads(expected_inputs) if expected_inputs else None
            output_schema = json.loads(expected_outputs) if expected_outputs else None
            schema = TestCaseSchema(input_schema=input_schema, output_schema=output_schema)
        except json.JSONDecodeError as e:
            console.print(
                Panel(
                    f"❌ Invalid JSON for schema: {e}",
                    title="Parameter Error",
                    border_style="red",
                )
            )
            raise click.Abort()
        except ValidationError as e:
            console.print(
                Panel(
                    f"❌ Invalid schema format: {e}",
                    title="Schema Error",
                    border_style="red",
                )
            )
            raise click.Abort()

    # Validate parameters
    if mode == "import" and source_path is None:
        console.print(
            Panel(
                "❌ Source path is required for import mode",
                title="Parameter Error",
                border_style="red",
            )
        )
        raise click.Abort()

    # Validate p_ratio parameter
    if p_ratio < 0.0 or p_ratio > 1.0:
        console.print(
            Panel(
                f"❌ Invalid p_ratio: {p_ratio}. Must be between 0.0 and 1.0",
                title="Invalid Parameter",
                border_style="red",
            )
        )
        raise click.Abort()

    if mode == "generate" and source_path is not None:
        console.print(
            Panel(
                "⚠️  Source path is ignored in generation mode",
                title="Parameter Warning",
                border_style="yellow",
            )
        )

    if n is not None and n <= 0:
        console.print(
            Panel(
                "❌ Number of test cases must be positive",
                title="Parameter Error",
                border_style="red",
            )
        )
        raise click.Abort()

    # Route to appropriate mode
    if mode == "generate":
        _handle_generation_mode(project_root, n, p_ratio, extra, schema)
    else:
        _handle_import_mode(source_path, project_root, n, extra, schema)


def _handle_import_mode(
    source_path: Optional[Path],
    project_root: Path,
    n: Optional[int],
    extra: str,
    schema: Optional["TestCaseSchema"] = None,
) -> None:
    """Handle import mode - analyze files and generate test cases."""
    try:
        console.print(
            Panel(
                f"🔍 Scanning directory: {source_path}", title="Import Command", border_style="blue"
            )
        )

        if not source_path:
            console.print(
                Panel(
                    "❌ No valid source path provided!",
                    title="Import Failed",
                    border_style="red",
                )
            )
            raise click.Abort()

        # Scan directory for files and read their contents
        file_contents = scan_directory_for_files(source_path)

        if not file_contents:
            console.print(
                Panel(
                    "❌ No supported files found in the source directory",
                    title="Import Failed",
                    border_style="red",
                )
            )
            raise click.Abort()

        # Read project description
        try:
            project_description = read_project_description(project_root)
            console.print("📄 Read project description from PROJECT_DESC.md")
        except FileNotFoundError as e:
            console.print(Panel(str(e), title="Project Description Missing", border_style="red"))
            raise click.Abort()

        # Generate file aliases for shorter AI input
        console.print("📝 Generating file aliases for AI analysis...")
        file_paths = [Path(path) for path in file_contents.keys()]
        alias_to_path, path_to_alias = generate_file_aliases(file_paths)

        # Convert file contents to use short aliases
        short_file_contents = {}
        for full_path_str, content in file_contents.items():
            full_path = Path(full_path_str)
            short_name = path_to_alias[full_path]
            short_file_contents[short_name] = content

        console.print(f"✅ Generated {len(short_file_contents)} file aliases")

        # Analyze files with AI agent
        console.print(
            Panel(
                "🤖 Analyzing files for test case generation capability...",
                title="AI Analysis",
                border_style="blue",
            )
        )

        try:
            from bugninja.agents.test_case_analyzer import TestCaseAnalyzerAgent

            # Create LLM and agent
            agent = TestCaseAnalyzerAgent(cli_mode=True)

            # Analyze files with short aliases
            analysis = asyncio.run(
                agent.analyze_files_for_test_cases(short_file_contents, project_description, extra)
            )

            rich_print(analysis)

            # Display analysis results
            if analysis.test_case_capable:
                # Build detailed success message
                success_text = Text()
                success_text.append(
                    "✅ Files are suitable for test case generation!\n\n", style="green"
                )
                success_text.append("📊 Analysis Results:\n", style="bold")
                success_text.append(
                    f"• Potential test cases: {analysis.number_of_potential_testcases}\n",
                    style="cyan",
                )
                success_text.append(
                    f"• File descriptions: {len(analysis.file_descriptions)} files analyzed\n",
                    style="cyan",
                )
                success_text.append(
                    f"• Testing scenarios: {len(analysis.testing_scenarios)} scenarios identified\n\n",
                    style="cyan",
                )

                # Show test scenarios with dependencies
                if analysis.testing_scenarios:
                    success_text.append("🔍 Test Scenarios:\n", style="bold")
                    for scenario in analysis.testing_scenarios:
                        success_text.append(
                            f"  {scenario.idx}. {scenario.test_scenario}\n", style="yellow"
                        )
                        if scenario.file_dependencies:
                            # Map short aliases back to full paths for display
                            mapped_deps = []
                            for dep in scenario.file_dependencies:
                                if dep in alias_to_path:
                                    full_path = alias_to_path[dep]
                                    mapped_deps.append(f"{dep} ({full_path})")
                                else:
                                    mapped_deps.append(dep)
                            success_text.append(
                                f"     📁 Dependencies: {', '.join(mapped_deps)}\n",
                                style="blue",
                            )
                    success_text.append("\n")

                # Show test dependencies if any
                if analysis.test_dependencies:
                    success_text.append("🔗 Test Dependencies:\n", style="bold")
                    for test_idx, deps in analysis.test_dependencies.items():
                        if deps:
                            success_text.append(
                                f"  Test {test_idx} depends on: {', '.join(map(str, deps))}\n",
                                style="magenta",
                            )
                    success_text.append("\n")

                console.print(Panel(success_text, title="Analysis Complete", border_style="green"))

                # Determine how many test cases to generate
                available_scenarios = len(analysis.testing_scenarios)
                if n is None:
                    scenarios_to_generate = available_scenarios  # Import ALL test cases by default
                elif n > available_scenarios:
                    scenarios_to_generate = available_scenarios  # Use all available
                    console.print(
                        Panel(
                            f"⚠️  Warning: Only {available_scenarios} test case(s) found, but you requested {n}. Importing all available test cases.",
                            title="Insufficient Test Cases",
                            border_style="yellow",
                        )
                    )
                else:
                    scenarios_to_generate = n  # Use first n scenarios

                console.print(
                    Panel(
                        f"🤖 Generating {scenarios_to_generate} test case(s) from {available_scenarios} available scenarios...",
                        title="Test Case Generation",
                        border_style="blue",
                    )
                )

                try:
                    from bugninja.agents.test_case_creator import TestCaseCreatorAgent

                    # Create test case creator agent
                    creator_agent = TestCaseCreatorAgent(cli_mode=True)

                    # Generate test cases in parallel
                    console.print("💾 Generating test cases...")
                    saved_tasks = asyncio.run(
                        _generate_import_test_cases_parallel(
                            creator_agent,
                            analysis.testing_scenarios[:scenarios_to_generate],
                            short_file_contents,
                            alias_to_path,
                            project_description,
                            extra,
                            project_root,
                            schema,
                        )
                    )

                    # Display success message
                    success_text = Text()
                    success_text.append(
                        f"✅ Generated {len(saved_tasks)} test case(s) successfully!\n\n",
                        style="green",
                    )

                    # Show I/O schema information if provided
                    if schema:
                        success_text.append("🔧 Data Extraction Configuration:\n", style="bold")
                        if schema.input_schema:
                            success_text.append(
                                f"   • Input Schema: {list(schema.input_schema.keys())}\n",
                                style="yellow",
                            )
                        if schema.output_schema:
                            success_text.append(
                                f"   • Output Schema: {list(schema.output_schema.keys())}\n",
                                style="yellow",
                            )
                        success_text.append(
                            "   • Data extraction enabled for these test cases\n\n",
                            style="yellow",
                        )

                    success_text.append("📋 Generated Test Cases:\n", style="bold")

                    for i, (test_case, task_id, source_files) in enumerate(saved_tasks, 1):
                        success_text.append(f"{i}. {test_case.task_name}\n", style="cyan")
                        success_text.append(
                            f"   Description: {test_case.description}\n", style="dim"
                        )
                        success_text.append(f"   Task ID: {task_id}\n", style="dim")
                        success_text.append(
                            f"   Instructions: {len(test_case.extra_instructions)} steps\n",
                            style="dim",
                        )
                        if test_case.secrets:
                            success_text.append(
                                f"   Secrets: {len(test_case.secrets)} found\n", style="dim"
                            )
                        if schema:
                            success_text.append("   Data Extraction: Enabled\n", style="yellow")
                        success_text.append(
                            f"   Source Files: {len(source_files)} files\n", style="dim"
                        )
                        success_text.append("\n")

                    console.print(
                        Panel(success_text, title="Test Cases Generated", border_style="green")
                    )

                except Exception as e:
                    console.print(
                        Panel(
                            f"❌ Test case generation failed: {e}",
                            title="Generation Error",
                            border_style="red",
                        )
                    )
                    raise click.Abort()

            else:
                # Display failure reasoning
                failure_text = Text()
                failure_text.append(
                    "❌ Files are not suitable for test case generation\n\n", style="red"
                )
                failure_text.append("📋 Analysis Results:\n", style="bold")
                failure_text.append(f"Reasoning: {analysis.import_reasoning}\n\n", style="yellow")

                if analysis.file_descriptions:
                    failure_text.append("📄 File Analysis:\n", style="bold")
                    for desc in analysis.file_descriptions:
                        failure_text.append(f"• {desc}\n", style="cyan")
                    failure_text.append("\n")

                if analysis.testing_scenarios:
                    failure_text.append("🔍 Potential Scenarios Found:\n", style="bold")
                    for scenario in analysis.testing_scenarios:
                        failure_text.append(
                            f"• {scenario.idx}. {scenario.test_scenario}\n", style="cyan"
                        )
                        if scenario.file_dependencies:
                            # Map short aliases back to full paths for display
                            mapped_deps = []
                            for dep in scenario.file_dependencies:
                                if dep in alias_to_path:
                                    full_path = alias_to_path[dep]
                                    mapped_deps.append(f"{dep} ({full_path})")
                                else:
                                    mapped_deps.append(dep)
                            failure_text.append(
                                f"  📁 Dependencies: {', '.join(mapped_deps)}\n",
                                style="blue",
                            )
                    failure_text.append("\n")

                failure_text.append(f"Test Data: {analysis.test_data}\n", style="yellow")

                console.print(Panel(failure_text, title="Analysis Failed", border_style="red"))
                raise click.Abort()

        except Exception as e:
            console.print(
                Panel(f"❌ AI analysis failed: {e}", title="Analysis Error", border_style="red")
            )
            raise click.Abort()

    except Exception as e:
        console.print(Panel(f"❌ Import failed: {e}", title="Import Error", border_style="red"))
        raise click.Abort()


def _handle_generation_mode(
    project_root: Path,
    n: Optional[int],
    p_ratio: float,
    extra: str,
    schema: Optional["TestCaseSchema"] = None,
) -> None:
    """Handle generation mode - create test cases from project description."""
    # Set default n for generate mode if not provided
    if n is None:
        n = 4  # Default for generate mode

    try:
        console.print(
            Panel(
                "🤖 Generating test cases from project description...",
                title="Generation Mode",
                border_style="blue",
            )
        )

        # Read project description
        try:
            project_description = read_project_description(project_root)
            console.print("📄 Read project description from PROJECT_DESC.md")
        except FileNotFoundError as e:
            console.print(Panel(str(e), title="Project Description Missing", border_style="red"))
            raise click.Abort()

        # Calculate positive and negative test case counts
        import math

        positive_count = math.ceil(n * p_ratio)
        negative_count = n - positive_count

        # Generate test cases
        console.print(
            Panel(
                f"🎯 Generating {n} test cases with {positive_count} positive and {negative_count} negative test paths...",
                title="Test Case Generation",
                border_style="blue",
            )
        )

        # Generate test cases using the generator agent
        try:
            from bugninja.agents.test_case_generator import TestCaseGeneratorAgent
            from bugninja_cli.utils.task_manager import TaskManager

            # Create test case generator agent
            generator_agent = TestCaseGeneratorAgent(cli_mode=True)

            # Generate test cases
            console.print(f"🎯 Generating {n} test cases...")
            test_cases = asyncio.run(
                generator_agent.generate_test_cases(
                    project_description=project_description,
                    n=n,
                    p_ratio=p_ratio,
                    extra=extra,
                )
            )

            # Create task manager and save test cases
            task_manager = TaskManager(project_root)

            # Generate test cases in parallel
            console.print("💾 Saving test cases...")
            saved_tasks = asyncio.run(
                _save_test_cases_parallel(task_manager, test_cases, project_description, schema)
            )

            # Display success message
            success_text = Text()
            success_text.append(
                f"✅ Generated {len(saved_tasks)} test cases successfully!\n\n", style="green"
            )

            # Show I/O schema information if provided
            if schema:
                success_text.append("🔧 Data Extraction Configuration:\n", style="bold")
                if schema.input_schema:
                    success_text.append(
                        f"   • Input Schema: {list(schema.input_schema.keys())}\n", style="yellow"
                    )
                if schema.output_schema:
                    success_text.append(
                        f"   • Output Schema: {list(schema.output_schema.keys())}\n", style="yellow"
                    )
                success_text.append(
                    "   • Data extraction enabled for these test cases\n\n", style="yellow"
                )

            success_text.append("📋 Generated Test Cases:\n", style="bold")

            for i, (test_case, task_id) in enumerate(saved_tasks, 1):
                success_text.append(f"{i}. {test_case.task_name}\n", style="cyan")
                success_text.append(f"   Description: {test_case.description}\n", style="dim")
                success_text.append(f"   Task ID: {task_id}\n", style="dim")
                success_text.append(
                    f"   Instructions: {len(test_case.extra_instructions)} steps\n", style="dim"
                )
                if test_case.secrets:
                    success_text.append(
                        f"   Secrets: {len(test_case.secrets)} found\n", style="dim"
                    )
                if schema:
                    success_text.append("   Data Extraction: Enabled\n", style="yellow")
                success_text.append("\n")

            console.print(Panel(success_text, title="Test Cases Generated", border_style="green"))

        except Exception as e:
            console.print(
                Panel(
                    f"❌ Test case generation failed: {e}",
                    title="Generation Error",
                    border_style="red",
                )
            )
            raise click.Abort()

    except Exception as e:
        console.print(
            Panel(f"❌ Generation failed: {e}", title="Generation Error", border_style="red")
        )
        raise click.Abort()


async def _save_test_cases_parallel(
    task_manager: TaskManager,
    test_cases: List["TestCaseCreationOutput"],
    project_description: str,
    schema: Optional["TestCaseSchema"] = None,
) -> List[tuple["TestCaseCreationOutput", str]]:
    """Save test cases in parallel with proper error handling."""

    # Get the starting number for sequential numbering
    starting_number = task_manager.get_next_task_number()

    async def save_single_test_case(
        test_case: TestCaseCreationOutput, index: int
    ) -> Optional[Tuple[TestCaseCreationOutput, str]]:
        """Save a single test case with error handling."""
        try:
            # Calculate the numbered index for this test case
            numbered_index = starting_number + index

            # Create a copy of the test case with numbered name
            numbered_test_case = test_case.model_copy()
            numbered_test_case.task_name = f"{numbered_index:03d}_{test_case.task_name}"

            # Create unique source files list for each test case
            source_files = [f"generated_test_case_{index + 1}"]

            # Create the imported task
            task_id = task_manager.create_imported_task(numbered_test_case, source_files, schema)
            return (numbered_test_case, task_id)
        except Exception as e:
            console.print(f"⚠️  Failed to save test case {index + 1}: {e}", style="yellow")
            return None

    # Create tasks for parallel execution
    tasks = [save_single_test_case(test_case, i) for i, test_case in enumerate(test_cases)]

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out failed results and type check
    saved_tasks: List[Tuple[TestCaseCreationOutput, str]] = []
    for result in results:
        if result is not None and not isinstance(result, Exception):
            # Type narrowing: we know result is Tuple[TestCaseCreationOutput, str]
            saved_tasks.append(result)  # type: ignore[arg-type]

    if not saved_tasks:
        raise RuntimeError("Failed to save any test cases")

    return saved_tasks


async def _generate_import_test_cases_parallel(
    creator_agent: TestCaseCreatorAgent,
    scenarios: List["TestScenario"],
    short_file_contents: Dict[str, str],
    alias_to_path: Dict[str, Path],
    project_description: str,
    extra: str,
    project_root: Path,
    schema: Optional["TestCaseSchema"] = None,
) -> List[Tuple["TestCaseCreationOutput", str, List[str]]]:
    """Generate test cases from import scenarios in parallel."""

    from bugninja_cli.utils.task_manager import TaskManager

    # Get the starting number for sequential numbering
    task_manager = TaskManager(project_root)
    starting_number = task_manager.get_next_task_number()

    async def generate_single_import_test_case(
        scenario: TestScenario, index: int
    ) -> Optional[Tuple[TestCaseCreationOutput, str, List[str]]]:
        """Generate a single test case from import scenario."""
        try:
            # Get file contents for the scenario dependencies
            scenario_file_contents = {}
            for dep_file in scenario.file_dependencies:
                if dep_file in short_file_contents:
                    scenario_file_contents[dep_file] = short_file_contents[dep_file]

            # Generate test case
            test_case = await creator_agent.generate_test_case(
                scenario=scenario,
                file_contents=scenario_file_contents,
                project_description=project_description,
                extra=extra,
            )

            # Calculate the numbered index for this test case
            numbered_index = starting_number + index

            # Create a copy of the test case with numbered name
            numbered_test_case = test_case.model_copy()
            numbered_test_case.task_name = f"{numbered_index:03d}_{test_case.task_name}"

            # Create task manager and save the test case
            task_manager = TaskManager(project_root)

            # Map short aliases back to full paths for source files
            source_files = []
            for dep_file in scenario.file_dependencies:
                if dep_file in alias_to_path:
                    source_files.append(str(alias_to_path[dep_file]))
                else:
                    source_files.append(dep_file)

            # Create the imported task
            task_id = task_manager.create_imported_task(numbered_test_case, source_files, schema)
            return (numbered_test_case, task_id, source_files)
        except Exception as e:
            console.print(f"⚠️  Failed to generate test case {index + 1}: {e}", style="yellow")
            return None

    # Create tasks for parallel execution
    tasks = [generate_single_import_test_case(scenario, i) for i, scenario in enumerate(scenarios)]

    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out failed results and type check
    saved_tasks: List[Tuple[TestCaseCreationOutput, str, List[str]]] = []
    for result in results:
        if result is not None and not isinstance(result, Exception):
            # Type narrowing: we know result is Tuple[TestCaseCreationOutput, str, List[str]]
            saved_tasks.append(result)  # type: ignore[arg-type]

    if not saved_tasks:
        raise RuntimeError("Failed to generate any test cases")

    return saved_tasks
