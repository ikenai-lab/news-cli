#!/bin/bash

# News CLI Installer for Linux/macOS
# Usage: curl -sSL https://raw.githubusercontent.com/ikenai-lab/news-cli/main/install.sh | bash

set -e

echo "🚀 News CLI Installer"
echo "====================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for required commands
check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${YELLOW}✗${NC} $1 is not installed"
        return 1
    fi
}

# Install uv if not present
install_uv() {
    echo ""
    echo "📦 Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Add to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
    
    echo -e "${GREEN}✓${NC} uv installed successfully"
}

# Install Ollama if not present
install_ollama() {
    echo ""
    echo "🤖 Installing Ollama (Local LLM runtime)..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    echo -e "${GREEN}✓${NC} Ollama installed successfully"
}

# Main installation
main() {
    echo "Checking dependencies..."
    echo ""
    
    # Check and install uv
    if ! check_command "uv"; then
        read -p "Install uv? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_uv
        else
            echo -e "${RED}Error: uv is required. Exiting.${NC}"
            exit 1
        fi
    fi
    
    # Check and install Ollama
    if ! check_command "ollama"; then
        read -p "Install Ollama? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_ollama
        else
            echo -e "${RED}Error: Ollama is required. Exiting.${NC}"
            exit 1
        fi
    fi
    
    echo ""
    echo "📂 Cloning repository..."
    
    # Clone or Update repository
    if [ -d "news-cli" ]; then
        echo "Directory 'news-cli' already exists. Updating..."
        cd news-cli
        
        # Stash local changes if any to prevent conflicts
        if [[ -n $(git status -s) ]]; then
            echo "Stashing local changes..."
            git stash
        fi
        
        git checkout main
        git pull origin main
    else
        git clone https://github.com/ikenai-lab/news-cli.git
        cd news-cli
    fi
    
    echo ""
    echo "📦 Installing Python dependencies..."
    uv sync
    
    echo ""
    echo "🌐 Installing browser for JavaScript sites (optional)..."
    uv run playwright install chromium || echo "Playwright install skipped"
    
    echo ""
    echo "🤖 Pulling LLM model (llama3.2:3b)..."
    ollama pull llama3.2:3b
    
    echo ""
    echo "📦 Installing/Updating global command..."
    uv tool install . --force
    
    echo ""
    echo -e "${GREEN}✅ Installation complete!${NC}"
    echo ""
    echo "To run News CLI:"
    echo "  news-cli"
}

main
