#!/bin/bash

# ============================================================================
# Bugninja Installation Script for macOS
# ============================================================================
# This script installs all required dependencies for Bugninja including:
# - Homebrew (if not present)
# - Python 3.11+
# - pip, pipx, and uv package managers
# - ffmpeg for video recording
# - Bugninja CLI with shell autocompletion
#
# Usage:
#   ./install-mac.sh           # Fresh installation
#   ./install-mac.sh --update  # Update existing installation
# ============================================================================

set -e  # Exit on any error

# Parse command line arguments
UPDATE_MODE=false
if [[ "$1" == "--update" ]]; then
    UPDATE_MODE=true
fi

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect shell configuration file
detect_shell_config() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "$HOME/.zshrc"
    elif [ -n "$BASH_VERSION" ]; then
        echo "$HOME/.bashrc"
    else
        # Default to zsh on macOS (standard since Catalina)
        echo "$HOME/.zshrc"
    fi
}

SHELL_CONFIG=$(detect_shell_config)
SHELL_NAME=$(basename "$SHELL")

# Print functions
print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# ============================================================================
# Installation Steps
# ============================================================================

echo ""
if [ "$UPDATE_MODE" = true ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           Bugninja Update Script for macOS                    ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
else
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           Bugninja Installation Script for macOS              ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
fi
echo ""

# Step 1: Install Homebrew
print_step "Step 1: Checking for Homebrew..."
if ! command_exists brew; then
    print_warning "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == 'arm64' ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$SHELL_CONFIG"
    fi
    
    print_success "Homebrew installed successfully"
else
    print_success "Homebrew is already installed"
fi

# Step 2: Install Python 3.11+
print_step "Step 2: Checking for Python 3.11+..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        print_success "Python $PYTHON_VERSION is already installed"
    else
        print_warning "Python $PYTHON_VERSION found, but 3.11+ is required. Installing Python 3.11..."
        brew install python@3.11
        print_success "Python 3.11 installed successfully"
    fi
else
    print_warning "Python not found. Installing Python 3.11..."
    brew install python@3.11
    print_success "Python 3.11 installed successfully"
fi

# Ensure pip is up to date
print_step "Updating pip..."
python3 -m pip install --upgrade pip --user
print_success "pip updated successfully"

# Step 3: Install pipx
print_step "Step 3: Checking for pipx..."
if ! command_exists pipx; then
    print_warning "pipx not found. Installing pipx..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    
    # Add pipx to PATH
    export PATH="$HOME/.local/bin:$PATH"
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_CONFIG"; then
        echo '' >> "$SHELL_CONFIG"
        echo '# Added by Bugninja installer' >> "$SHELL_CONFIG"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
    fi
    
    print_success "pipx installed successfully"
else
    print_success "pipx is already installed"
    pipx ensurepath
fi

# Step 4: Install uv
print_step "Step 4: Checking for uv..."
if ! command_exists uv; then
    print_warning "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add uv to PATH
    export PATH="$HOME/.cargo/bin:$PATH"
    if ! grep -q 'export PATH="$HOME/.cargo/bin:$PATH"' "$SHELL_CONFIG"; then
        echo '' >> "$SHELL_CONFIG"
        echo '# Added by Bugninja installer for uv' >> "$SHELL_CONFIG"
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$SHELL_CONFIG"
    fi
    
    print_success "uv installed successfully"
else
    print_success "uv is already installed"
fi

# Step 5: Install ffmpeg
print_step "Step 5: Checking for ffmpeg..."
if ! command_exists ffmpeg; then
    print_warning "ffmpeg not found. Installing ffmpeg..."
    brew install ffmpeg
    print_success "ffmpeg installed successfully"
else
    print_success "ffmpeg is already installed"
fi

# Step 6: Install Playwright browsers
print_step "Step 6: Installing Playwright browsers..."

# First try with pipx (recommended approach)
if command_exists pipx; then
    print_step "Installing Playwright with pipx..."
    pipx install playwright
    pipx runpip playwright install playwright
    playwright install chromium
else
    # Fallback to user install
    print_step "Installing Playwright via pip..."
    python3 -m pip install playwright --user
    python3 -m playwright install chromium
fi

print_success "Playwright browsers installed successfully"

# Step 7: Install or Update Bugninja
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

if [ "$UPDATE_MODE" = true ]; then
    print_step "Step 7: Updating Bugninja..."
    print_step "Force reinstalling Bugninja with pipx..."
    pipx install --force .
    print_success "Bugninja updated successfully"
else
    print_step "Step 7: Installing Bugninja..."
    
    # Check if already installed
    if pipx list | grep -q "bugninja"; then
        print_warning "Bugninja is already installed. Use --update to reinstall."
        print_step "Force reinstalling anyway..."
        pipx install --force .
    else
        print_step "Installing Bugninja with pipx..."
        pipx install .
    fi

    print_success "Bugninja installed successfully"
fi

# Step 8: Set up shell autocompletion
print_step "Step 8: Setting up shell autocompletion..."

if [[ "$SHELL_NAME" == "zsh" ]]; then
    if ! grep -q "_BUGNINJA_COMPLETE=zsh_source bugninja" "$SHELL_CONFIG"; then
        echo '' >> "$SHELL_CONFIG"
        echo '# Bugninja CLI completion (added by installer)' >> "$SHELL_CONFIG"
        echo 'autoload -Uz compinit' >> "$SHELL_CONFIG"
        echo 'compinit' >> "$SHELL_CONFIG"
        echo 'eval "$(_BUGNINJA_COMPLETE=zsh_source bugninja)"' >> "$SHELL_CONFIG"
        print_success "Zsh autocompletion configured"
    else
        print_success "Zsh autocompletion already configured"
    fi
elif [[ "$SHELL_NAME" == "bash" ]]; then
    if ! grep -q "_BUGNINJA_COMPLETE=bash_source bugninja" "$SHELL_CONFIG"; then
        echo '' >> "$SHELL_CONFIG"
        echo '# Bugninja CLI completion (added by installer)' >> "$SHELL_CONFIG"
        echo 'eval "$(_BUGNINJA_COMPLETE=bash_source bugninja)"' >> "$SHELL_CONFIG"
        print_success "Bash autocompletion configured"
    else
        print_success "Bash autocompletion already configured"
    fi
fi

# Step 9: Verify installation
print_step "Step 9: Verifying installation..."
echo ""

# Source the shell config to update PATH for verification
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if command_exists bugninja; then
    BUGNINJA_VERSION=$(pipx list | grep bugninja || echo "unknown")
    print_success "Bugninja CLI is accessible"
else
    print_error "Bugninja CLI not found in PATH. You may need to restart your terminal."
fi

if command_exists uv; then
    UV_VERSION=$(uv --version 2>&1 || echo "unknown")
    print_success "uv is accessible ($UV_VERSION)"
fi

if command_exists pipx; then
    PIPX_VERSION=$(pipx --version 2>&1 || echo "unknown")
    print_success "pipx is accessible ($PIPX_VERSION)"
fi

if command_exists ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1 || echo "unknown")
    print_success "ffmpeg is accessible"
fi

# ============================================================================
# Installation Complete
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              Installation completed successfully! 🎉           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
print_warning "IMPORTANT: Please restart your terminal or run:"
echo ""
echo "    source $SHELL_CONFIG"
echo ""
print_step "To verify the installation, run:"
echo ""
echo "    bugninja --help"
echo ""
print_step "To get started with Bugninja:"
echo ""
echo "    1. Initialize a new project:    bugninja init my_project"
echo "    2. Add a test case:             bugninja add 'My Test'"
echo "    3. Run the test:                bugninja run my_test"
echo ""
print_success "Happy testing with Bugninja! 🐛🥷"
echo ""

