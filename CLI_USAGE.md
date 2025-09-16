# Bugninja CLI Usage Guide

The Bugninja CLI provides a comprehensive interface for managing browser automation projects with built-in project validation and initialization.

## 🚀 Getting Started

### **Project Initialization**

Before using any Bugninja commands, you need to initialize a project:

```bash
# Initialize a new project
bugninja init --name my-automation-project

# Initialize with custom directory paths
bugninja init --name my-project \
  --screenshots-dir ./captures \
  --tasks-dir ./test-tasks \
  --traversals-dir ./sessions

# Note: Cannot overwrite existing projects - delete files first
```

### **Project Structure**

After initialization, your project will have this structure:

```
my-automation-project/
├── bugninja.toml          # Project configuration
├── .env.example           # Environment template
├── README.md              # Project documentation
├── traversals/            # Recorded browser sessions
├── screenshots/           # Screenshots from automation
└── tasks/                 # Task definitions
```

## 📋 Available Commands

### **`bugninja init` - Project Initialization**

Initialize a new Bugninja project in the current directory.

**Options:**
- `--name, -n <name>`: Project name (required)
- `--screenshots-dir, -s <path>`: Screenshots directory (default: `./screenshots`)
- `--tasks-dir, -t <path>`: Tasks directory (default: `./tasks`)
- `--traversals-dir, -tr <path>`: Traversals directory (default: `./traversals`)


**Example:**
```bash
bugninja init --name ecommerce-tests --screenshots-dir ./test-captures
```

### **`bugninja run` - Execute Tasks**

Run browser automation tasks. **Requires initialized project.**

**Options:**
- `--all, -a`: Run all available tasks
- `--task, -t <id>`: Run specific task by ID
- `--multiple, -mt <id1> <id2>`: Run multiple tasks
- `--info`: Show project information before running

**Examples:**
```bash
# Run all tasks
bugninja run --all

# Run specific task
bugninja run --task login-test

# Run multiple tasks
bugninja run --multiple login-test checkout-test

# Show project info and run
bugninja run --all --info
```

### **`bugninja replay` - Replay Sessions**

Replay recorded browser sessions. **Requires initialized project.**

**Options:**
- `--all, -a`: Replay all available traversals
- `--traversal, -t <id>`: Replay specific traversal by ID
- `--multiple, -mt <id1> <id2>`: Replay multiple traversals
- `--info`: Show project information before replaying

**Examples:**
```bash
# Replay all traversals
bugninja replay --all

# Replay specific traversal
bugninja replay --traversal session-123

# Replay multiple traversals
bugninja replay --multiple session-123 session-456
```

### **`bugninja stats` - View Statistics**

Show statistics about automation runs. **Requires initialized project.**

**Options:**
- `--list, -l`: List all available runs
- `--id <run_id>`: Show statistics for specific run
- `--info`: Show project information

**Examples:**
```bash
# List all runs
bugninja stats --list

# Show specific run statistics
bugninja stats --id run-abc123

# Show project info
bugninja stats --info
```

## 🔒 Project Validation

All commands (except `init`) require a properly initialized Bugninja project. The CLI will:

1. **Check for `bugninja.toml`** in current or parent directories
2. **Validate project structure** and configuration
3. **Show helpful error messages** if project is not found or invalid

### **Error Messages**

**Project Not Found:**
```
❌ Not in a Bugninja project.

To initialize a new project, run:
  bugninja init --name <project-name>

Or navigate to an existing Bugninja project directory.
```

**Invalid Project Structure:**
```
❌ Invalid Bugninja project structure in /path/to/project

The project may be corrupted or incomplete.
Delete the project files and reinitialize with:
  bugninja init --name <project-name>
```

## 🎨 Rich Output

The CLI uses Rich for beautiful, informative output:

- **Color-coded messages** (green for success, red for errors, blue for info)
- **Progress indicators** during initialization
- **Structured panels** for project information
- **Clear error messages** with actionable guidance

## 📁 Project Detection

The CLI automatically detects Bugninja projects by:

1. **Searching current directory** for `bugninja.toml`
2. **Searching parent directories** if not found in current directory
3. **Validating TOML structure** and required fields
4. **Checking directory permissions** and structure

This means you can run commands from any subdirectory within a Bugninja project.

## 🔧 Configuration

### **Project Configuration (`bugninja.toml`)**

The initialization creates a `bugninja.toml` file with:

```toml
[project]
name = "your-project-name"

[llm]
model = "gpt-4.1"
temperature=0.0

[logging]
level = "INFO"

[paths]
traversals_dir = "./traversals"
screenshots_dir = "./screenshots"
tasks_dir = "./tasks"

# ... other configuration sections
```

### **Environment Configuration (`.env`)**

Copy `.env.example` to `.env` and add your API keys:

```bash
# Required for LLM functionality
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here
```

## 🚨 Troubleshooting

### **Common Issues**

1. **"Not in a Bugninja project"**
   - Run `bugninja init --name <project-name>` to create a project
   - Navigate to an existing Bugninja project directory

2. **"Invalid project structure"**
   - The project may be corrupted
   - Delete project files and reinitialize with `bugninja init --name <project-name>`

3. **Permission errors during initialization**
   - Check write permissions in the current directory
   - Try running with elevated permissions if needed

4. **Configuration file errors**
   - Ensure `bugninja.toml` is valid TOML
   - Check for syntax errors in the configuration file

### **Getting Help**

- Use `--help` with any command for detailed usage information
- Check the project README for additional documentation
- Review the `bugninja.toml` configuration file for customization options

## 🔄 Migration from Existing Projects

If you have an existing Bugninja setup:

1. **Backup your current configuration**
2. **Delete existing project files** (or move to different directory)
3. **Run `bugninja init --name <project-name>`**
4. **Copy your existing `.env` file** (don't overwrite the template)
5. **Move your existing files** to the new directory structure
6. **Update paths** in `bugninja.toml` if needed

The CLI will preserve your existing configuration while adding the new project structure and validation.
