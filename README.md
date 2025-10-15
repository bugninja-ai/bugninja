# Bugninja 🐛🥷

<div align="center">

<img src="public-assets/bugninja.svg" alt="Bugninja Logo" width="200" height="100">

**AI-Powered E2E Testing That Actually Works**

*Write tests in plain English. Let AI handle the rest.*

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)](#)
[![Discord](https://img.shields.io/badge/Discord-Join%20Us-7289da.svg)](#join-the-community)

[🌐 Website](https://bugninja.ai) • [📚 Documentation](https://docs.bugninja.ai) • [💬 Discord](https://discord.gg/g2VKFuUpdk)

</div>

## See it in Action

<div align="center">

https://github.com/user-attachments/assets/e574c9a9-15e7-4191-8cf4-bc4ab1cd2693

*Watch Bugninja automatically navigate, interact, and test your web application using natural language instructions*

</div>

## What Can You Do With Bugninja?

### ✨ Write Tests in Plain English
```bash
# First, initialize your project
bugninja init my_project

# Add a new test case
bugninja add "Login Test"

# This creates a TOML file like:
# [task]
# name = "Login Test"
# description = "Navigate to login page, enter credentials, and verify dashboard loads"

# Run it with AI
bugninja run login_test
```

### 🤖 Generate Test Cases Automatically
```bash
# Generate ALL test cases from existing documentation (default behavior)
bugninja import /path/to/test-specs

# Generate only first 3 test cases from existing documentation
bugninja import /path/to/test-specs -n 3

# Or create from scratch using AI
bugninja import --mode generate -n 5 --extra "Focus on user authentication flows"
```

### 🤖 AI-Powered Browser Agent
Bugninja's intelligent browser agent understands your web application like a human tester would:
- **Smart Navigation**: Finds elements even when they change
- **Context Awareness**: Understands page state and user flows  
- **Self-Healing**: Automatically adapts when UI changes
- **Visual Recognition**: Uses computer vision to interact with complex interfaces

### 🔄 Record & Replay Test Sessions
Every test run is automatically recorded as a "traversal" that can be replayed:
```bash
# Record a test session
bugninja run login_test

# Replay latest traversal for a task
bugninja replay login_test

# Self-healing replay fixes broken tests automatically
bugninja replay login_test --healing
```

### 🔗 Chain Tests with Dependencies
Create sophisticated test workflows where tests pass data to each other:
```bash
# Run dependent tests - Bugninja handles the order automatically
bugninja run delete_user_test  # Also runs create_user_test first

# Output from create_user_test becomes input for delete_user_test
# AI receives full context about the data and its purpose
```

### 🎯 Perfect for Modern E2E Testing
- **Flaky Test Elimination**: Self-healing capabilities reduce test maintenance
- **Cross-Browser Testing**: Works with any Playwright-supported browser
- **HTTP Authentication Support**: Built-in support for testing protected websites with basic auth
- **CI/CD Integration**: Seamlessly integrates with your existing pipelines
- **Rich Reporting**: Detailed test reports with screenshots and execution traces

## Quick Installation

### Automated Installation (Recommended)

We provide installation scripts that handle all dependencies automatically:

#### macOS
```bash
chmod +x install/install-mac.sh
./install/install-mac.sh
```

#### Linux (Ubuntu/Debian)
```bash
chmod +x install/install-linux.sh
./install/install-linux.sh
```

The installation script will:
- Install Python 3.11+ (if needed)
- Install pip, pipx, and uv package managers
- Install ffmpeg for video recording
- Install Playwright browsers with all dependencies
- Install Bugninja CLI globally with pipx
- Set up shell autocompletion (bash/zsh)

**To update an existing installation:**
```bash
# macOS
./install/install-mac.sh --update

# Linux
./install/install-linux.sh --update
```

### Manual Installation

If you prefer to install manually, follow these steps:

#### Prerequisites

**ffmpeg** is required for video recording functionality. Install it on your system:

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg libgl1-mesa-glx libglu1-mesa-dev
```

**Linux (CentOS/RHEL/Fedora):**
```bash
# CentOS/RHEL
sudo yum install ffmpeg

# Fedora
sudo dnf install ffmpeg
```

**macOS:**
```bash
# Using Homebrew
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use package managers:
```bash
# Using Chocolatey
choco install ffmpeg

# Using Scoop
scoop install ffmpeg
```

#### Install Options

**Using pipx (Recommended for CLI tools):**
```bash
pipx install .
```

**Using pip:**
```bash
pip install --user .
```

**Using uv (Global Install):**
```bash
uv tool install -e .
```

**From Source (Development):**
```bash
cd bugninja
uv sync
# For this you have to activate the venv once and use directly
source .venv/bin/activate
bugninja --help
# ... etc
```

#### Shell Autocompletion

The installation script sets this up automatically. If installing manually, enable autocomplete:

**bash:**
```bash
echo 'eval "$(_BUGNINJA_COMPLETE=bash_source bugninja)"' >> ~/.bashrc
```

**zsh:**
```bash
echo -e '\n# Initialize zsh completion system\nautoload -Uz compinit\ncompinit\n\n# Bugninja CLI completion\neval "$(_BUGNINJA_COMPLETE=zsh_source bugninja)"' >> ~/.zshrc
```

**Fish:**
Add this to `~/.config/fish/completions/foo-bar.fish`:
```
_BUGNINJA_COMPLETE=fish_source bugninja 
```

### Verify Installation
```bash
bugninja --help
```

## Core Features

### 🧠 **AI Navigation**
- **Natural Language Processing**: Describe what you want to test in plain English
- **Smart Element Detection**: Finds buttons, forms, and content even with dynamic IDs
- **Context Understanding**: Maintains awareness of application state throughout tests
- **Vision-Powered Interactions**: Uses screenshots to understand complex UI elements

### 🔄 **Intelligent Replay System**
- **Session Recording**: Every interaction is captured with full context
- **Self-Healing Replays**: Automatically fixes broken selectors and changed elements
- **Brain State Tracking**: Records AI decision-making process for debugging
- **Alternative Selector Strategies**: Multiple fallback approaches for robust element identification

### 🔐 **Secrets Management**
```toml
# task.toml
[task]
name = "login_test"
description = "Navigate to login page and authenticate with provided credentials"

[run_config]
enable_healing = true
headless = false
```
- **Environment Variable Support**: Secure credential handling via .env files
- **Task Configuration**: Define test parameters in TOML files
- **Credential Isolation**: Keep sensitive data separate from task definitions

### ⚙️ **Flexible Browser Configuration**
```toml
# bugninja.toml
[browser]
viewport_width = 1920
viewport_height = 1080
user_agent = ""
timeout = 30000

[agent]
max_steps = 100
enable_vision = true
wait_between_actions = 1.0

[run_config]
headless = false
enable_healing = true
```
- **Multi-Device Testing**: Desktop, mobile, and tablet viewports
- **Custom Browser Profiles**: Tailored configurations per test environment
- **Performance Controls**: Timeouts, step limits, and retry logic

### 📊 **Rich CLI Experience**
```bash
# Initialize a new Bugninja project (required first step)
bugninja init my_project

# Add a new task interactively
bugninja add "My Task"

# Run a task
bugninja run my_task

# Replay latest traversal for a task
bugninja replay my_task

# Self-healing replay
bugninja replay my_task --healing

# Replay specific traversal by ID
bugninja replay --traversal kfdvnie47ic2b87l00v7iut5
```

### 🔗 **Test Case Dependencies & Data Flow**
Bugninja supports sophisticated test case dependencies where one test can use data generated by another test:

#### **Defining Dependencies**
```toml
# task_create_user.toml
[task]
name = "create_user"
description = "Create a new user account and return the user ID"

[task.io_schema]
output_schema.USER_ID = "ID of the newly created user"
output_schema.USERNAME = "Username of the created user"

# task_login_user.toml  
[task]
name = "login_user"
description = "Login with the user created in the previous test"
dependencies = ["create_user"]  # This task depends on create_user

[task.io_schema]
input_schema.USER_ID = "ID of the user from previous test"
input_schema.USERNAME = "Username from previous test"
```

#### **Automatic Dependency Resolution**
```bash
# Run a task with dependencies - Bugninja automatically:
# 1. Identifies all dependencies
# 2. Runs them in the correct order  
# 3. Passes output data to dependent tasks
bugninja run login_user

# The CLI will automatically run:
# 1. create_user (generates USER_ID and USERNAME)
# 2. login_user (receives USER_ID and USERNAME as input data)
```

#### **Key Benefits**
- **🔄 Data Flow**: Output from one test becomes input for the next
- **📋 Order Management**: Dependencies run in the correct sequence automatically
- **🧠 AI Context**: Dependent tasks receive data with full context about its purpose
- **🔒 Security**: Input data is separate from secrets and credentials
- **⚡ Efficiency**: Reuse setup work across multiple related tests

### 🤖 **AI-Powered Test Case Generation**
Bugninja can automatically generate test cases from your existing documentation or create them from scratch:

#### **Import Mode** - Generate from Existing Files
```bash
# Import ALL test cases from existing documentation (default behavior)
bugninja import /path/to/test-specs

# Import only the first 3 test cases found
bugninja import /path/to/test-specs -n 3 --extra "Focus on mobile testing"
```

**Supported file formats:**
- Excel files (.xlsx, .xls)
- CSV files (.csv)
- Word documents (.docx)
- PDF files (.pdf)
- Gherkin files (.feature)
- Code files (.py, .ts, .js)
- TOML configuration files

#### **Generate Mode** - Create from Project Description
```bash
# Generate test cases from project description
bugninja import --mode generate -n 5

# Generate with custom instructions
bugninja import --mode generate -n 8 --extra "Focus on e-commerce functionality" --p-ratio 0.8
```

**Key features:**
- **Smart Analysis**: AI analyzes your project structure and functionality
- **Positive/Negative Paths**: Automatically generates both success and failure scenarios
- **Custom Instructions**: Tailor generation with specific requirements
- **Parallel Processing**: Fast generation of multiple test cases
- **Professional Quality**: Generated by Senior Test Automation Engineers with ISTQB certification

> **Note**: Generate mode requires a `PROJECT_DESC.md` file in your project root. This file should describe your application's purpose, structure, and functionality to help AI generate relevant test cases.

## Technology Stack

<div align="center">

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Browser Automation** | [Playwright](https://playwright.dev) | Cross-browser testing engine |
| **AI Framework** | [browser-use](https://github.com/browser-use/browser-use) | AI browser interaction library |
| **Language Models** | OpenAI, Anthropic, Azure | Natural language understanding |
| **Runtime** | Python 3.8+ | Core application framework |
| **Configuration** | TOML, Pydantic | Type-safe settings management |
| **CLI** | Rich, Typer | Beautiful command-line interface |
| **Storage** | JSON, SQLite | Session and traversal persistence |

</div>

### Why This Stack?
- **🚀 Performance**: Playwright's speed + Python's flexibility
- **🧠 Intelligence**: Advanced LLM integration for human-like testing
- **🔧 Reliability**: Battle-tested components with extensive community support
- **📈 Scalability**: From single tests to enterprise CI/CD pipelines

## Join the Community

<div align="center">

### Help Us Build the Future of E2E Testing

</div>

- **⭐ Star the repo** - Show your support and help others discover Bugninja
- **🐛 Report bugs** - Help us improve by reporting issues you encounter  
- **💡 Request features** - Share your ideas for new functionality
- **🤝 Contribute** - Submit pull requests and join our development community
- **💬 Join our Discord** - Connect with other users and get real-time help
- **📖 Improve docs** - Help us make Bugninja more accessible to everyone

### 🔗 Community Links

- **Discord**: [Join our community](https://discord.gg/g2VKFuUpdk) for real-time support and discussions
- **GitHub Discussions**: [Share ideas and ask questions](https://github.com/bugninja-ai)
- **LinkedIn**: [Follow us](https://www.linkedin.com/company/bugninja-ai/?viewAsMember=true) for professional updates
- **Blog**: [Read our articles](https://bugninja.ai/blog/) on testing best practices

<div align="center">

**Made with ❤️ by the Bugninja team**

*Empowering developers to build better software through intelligent testing*

</div>
