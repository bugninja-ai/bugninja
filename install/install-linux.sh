#!/bin/bash

# ============================================================================
# Bugninja Installation Script for Linux (Ubuntu/Debian)
# ============================================================================
# This script installs all required dependencies for Bugninja including:
# - Python 3.11+
# - pip, pipx, and uv package managers
# - ffmpeg for video recording
# - Required system libraries
# - Bugninja CLI with shell autocompletion
#
# Usage:
#   ./install-linux.sh           # Fresh installation
#   ./install-linux.sh --update  # Update existing installation
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
        # Default to bash on Linux
        echo "$HOME/.bashrc"
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

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Please do not run this script as root or with sudo"
    print_warning "The script will prompt for sudo when needed"
    exit 1
fi

# ============================================================================
# Installation Steps
# ============================================================================

echo ""
if [ "$UPDATE_MODE" = true ]; then
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║         Bugninja Update Script for Ubuntu/Debian               ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
else
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║         Bugninja Installation Script for Ubuntu/Debian         ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
fi
echo ""

# Step 1: Update package lists (always do this)
print_step "Step 1: Updating package lists..."
sudo apt update
print_success "Package lists updated"

# Step 2: Install system dependencies
if [ "$UPDATE_MODE" = false ]; then
    print_step "Step 2: Installing system dependencies..."
    sudo apt install -y \
        software-properties-common \
        build-essential \
        curl \
        wget \
        git \
        ca-certificates \
        gnupg \
        lsb-release

    print_success "System dependencies installed"
else
    print_step "Step 2: Skipping system dependencies (update mode)"
fi

# Step 3: Install Python 3.11+
print_step "Step 3: Checking for Python 3.11+..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        print_success "Python $PYTHON_VERSION is already installed"
    else
        print_warning "Python $PYTHON_VERSION found, but 3.11+ is required. Installing Python 3.11..."
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt update
        sudo apt install -y python3.11 python3.11-venv python3.11-dev
        
        # Set Python 3.11 as the default python3
        sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        print_success "Python 3.11 installed successfully"
    fi
else
    print_warning "Python not found. Installing Python 3.11..."
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev
    
    # Set Python 3.11 as the default python3
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    print_success "Python 3.11 installed successfully"
fi

# Install pip for Python 3.11
print_step "Checking for pip..."
if ! python3 -m pip --version >/dev/null 2>&1; then
    print_warning "pip not found. Installing pip..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3
    print_success "pip installed successfully"
else
    print_success "pip is already installed"
    # Skip pip upgrade to avoid externally-managed-environment error
    # pipx and other tools will handle their own environments
fi

# Step 4: Install pipx
print_step "Step 4: Checking for pipx..."
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

# Step 5: Install uv
print_step "Step 5: Checking for uv..."
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

# Step 6: Install ffmpeg
print_step "Step 6: Checking for ffmpeg..."
if ! command_exists ffmpeg; then
    print_warning "ffmpeg not found. Installing ffmpeg..."
    sudo apt install -y ffmpeg
    print_success "ffmpeg installed successfully"
else
    print_success "ffmpeg is already installed"
fi

# Step 7: Install OpenGL dependencies (required for OpenCV)
print_step "Step 7: Installing OpenGL dependencies..."

# Install OpenGL libraries (use || true to continue if package doesn't exist)
sudo apt install -y libgl1 libglu1-mesa-dev 2>/dev/null || \
sudo apt install -y libgl1-mesa-glx libglu1-mesa-dev 2>/dev/null || \
print_warning "Could not install libgl1-mesa-glx (may be obsolete), continuing..."

# Also install common OpenGL packages
sudo apt install -y libglib2.0-0 libsm6 libxext6 libxrender-dev -y 2>/dev/null || true

print_success "OpenGL dependencies installed"

# Step 8: Install Playwright system dependencies
print_step "Step 8: Installing Playwright system dependencies..."
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libxshmfence1

print_success "Playwright system dependencies installed"

# Step 9: Install Playwright browsers
print_step "Step 9: Installing Playwright browsers..."

# First try with pipx (recommended approach)
if command_exists pipx; then
    print_step "Installing Playwright with pipx..."
    pipx install playwright
    pipx runpip playwright install playwright
    playwright install chromium
    
    # Try to install system dependencies if available
    print_step "Attempting to install Playwright system dependencies..."
    if sudo python3 -m playwright install-deps chromium 2>/dev/null; then
        print_success "Playwright system dependencies installed via playwright install-deps"
    else
        print_warning "playwright install-deps not available - system dependencies already installed manually"
    fi
else
    # Fallback to user install
    print_step "Installing Playwright via pip..."
    python3 -m pip install playwright --user
    python3 -m playwright install chromium
fi

print_success "Playwright browsers installed successfully"

# Step 10: Install or Update Bugninja
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

if [ "$UPDATE_MODE" = true ]; then
    print_step "Step 10: Updating Bugninja..."
    print_step "Force reinstalling Bugninja with pipx..."
    pipx install --force .
    print_success "Bugninja updated successfully"
else
    print_step "Step 10: Installing Bugninja..."
    
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

# Step 11: Set up shell autocompletion
print_step "Step 11: Setting up shell autocompletion..."

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

# Step 12: Verify installation
print_step "Step 12: Verifying installation..."
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

