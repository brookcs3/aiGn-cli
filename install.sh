#!/bin/bash

# CareerAI Installer - Magic Edition
# Installs dependencies, sets up the environment, and prepares the tool.

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   CareerAI Agent Professional Installer   ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. Detect OS
OS="$(uname -s)"
echo -e "${GREEN}[+] Detected OS: $OS${NC}"

# 2. Install System Dependencies
echo -e "${GREEN}[+] Checking system dependencies...${NC}"

if [ "$OS" = "Darwin" ]; then
    # macOS
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}[!] Homebrew not found. Please install Homebrew first: https://brew.sh${NC}"
        exit 1
    fi

    if ! command -v gum &> /dev/null; then
        echo "Installing gum..."
        brew install gum
    else
        echo "  - gum: found"
    fi

    if ! command -v jq &> /dev/null; then
        echo "Installing jq..."
        brew install jq
    else
        echo "  - jq: found"
    fi

    if ! command -v go &> /dev/null; then
        echo "Installing go..."
        brew install go
    else
        echo "  - go: found"
    fi

elif [ "$OS" = "Linux" ]; then
    # Linux (Debian/Ubuntu/Fedora support)
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        sudo apt-get update

        if ! command -v gum &> /dev/null; then
            echo "Installing gum (requires manual setup or charm repo)..."
            # Charm bracelet repo setup usually required, falling back to go install if not present
             if ! command -v go &> /dev/null; then
                 echo "Installing go..."
                 sudo apt-get install -y golang-go
             fi
             go install github.com/charmbracelet/gum@latest
             export PATH=$PATH:$(go env GOPATH)/bin
        fi

        if ! command -v jq &> /dev/null; then
            echo "Installing jq..."
            sudo apt-get install -y jq
        fi

    elif command -v dnf &> /dev/null; then
        # Fedora
        if ! command -v gum &> /dev/null; then
             echo "Installing gum..."
             # Gum is often in repo
             sudo dnf install -y gum || {
                 if ! command -v go &> /dev/null; then
                     sudo dnf install -y golang
                 fi
                 go install github.com/charmbracelet/gum@latest
                 export PATH=$PATH:$(go env GOPATH)/bin
             }
        fi

        if ! command -v jq &> /dev/null; then
            sudo dnf install -y jq
        fi
    fi
fi

# 3. Build Tools
echo -e "${GREEN}[+] Building local tools...${NC}"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR" || exit 1

# Build GumFuzzy
if [ -f "tools/GumFuzzy/fuzzy_picker.go" ]; then
    echo "Building GumFuzzy..."
    cd tools/GumFuzzy
    go build -o fuzzy-picker fuzzy_picker.go
    if [ $? -eq 0 ]; then
        echo "  - GumFuzzy built successfully"
    else
        echo -e "${RED}[!] Failed to build GumFuzzy${NC}"
    fi
    cd ../..
else
    echo -e "${RED}[!] tools/GumFuzzy/fuzzy-picker.go not found!${NC}"
fi


# 4. Install Magic (Modular)
echo -e "${GREEN}[+] Setting up Python environment with Magic...${NC}"

if ! command -v magic &> /dev/null; then
    echo "Installing magic..."
    curl -ssL https://magic.modular.com/b9714777-6262-4293-8515-565451e59544 | bash
    # Reload profile/path to ensure magic is available
    source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null

    if ! command -v magic &> /dev/null; then
        echo -e "${RED}[!] Magic installed but not in PATH. Please restart terminal or add to PATH manually.${NC}"
        # Try to proceed using explicit path if known, otherwise warn
    fi
fi

# Initialize magic project if needed
if [ ! -f "mojoproject.toml" ] && [ ! -f "pixi.toml" ]; then
    echo "Initializing magic project..."
    magic init . --format pixi
fi

# Add Python dependencies
echo "Adding dependencies via magic..."
magic add llama-cpp-python>=0.3.0 smolagents>=1.0.0 litellm>=1.0.0 mcp>=1.0.0 \
    PyMuPDF>=1.24.0 python-docx>=1.1.0 python-jobspy>=1.1.0 pandas>=2.0.0 \
    pydantic>=2.0.0 requests>=2.31.0 python-dotenv>=1.0.0 prompt_toolkit pyperclip

# 5. Global Command Setup
echo -e "${GREEN}[+] Setting up global command 'career-agent'...${NC}"

# Create a wrapper script in /usr/local/bin (requires sudo)
WRAPPER_PATH="/usr/local/bin/career-agent"
if [ -d "/usr/local/bin" ]; then
    echo "Creating symlink/wrapper at $WRAPPER_PATH..."

    # We need a wrapper that cd's to the directory first
    sudo bash -c "cat > $WRAPPER_PATH" <<EOF
#!/bin/bash
cd "$SCRIPT_DIR"
./career.sh
EOF
    sudo chmod +x $WRAPPER_PATH
    echo "  - Command 'career-agent' installed!"
else
    echo -e "${WARNING}[!] /usr/local/bin not found. You can run the tool with ./career.sh${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Installation Complete! 🚀            ${NC}"
echo -e "${BLUE}========================================${NC}"
echo "You can now run the tool by typing:"
echo -e "  ${GREEN}career-agent${NC}"
echo "or"
echo -e "  ${GREEN}./career.sh${NC}"
echo ""
