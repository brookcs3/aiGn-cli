#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Career Agent Installer...${NC}"

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    *)          machine="UNKNOWN:${OS}"
esac

echo -e "${GREEN}Detected OS: ${machine}${NC}"

# Install System Dependencies
echo -e "${BLUE}Checking system dependencies...${NC}"

if [ "$machine" == "Mac" ]; then
    if ! command -v brew &> /dev/null; then
        echo -e "${RED}Homebrew is required for macOS installation.${NC}"
        exit 1
    fi
    brew install gum jq go
elif [ "$machine" == "Linux" ]; then
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y gum jq golang-go
    else
        echo -e "${RED}Only apt-based Linux distros are automatically supported. Please install gum, jq, and go manually.${NC}"
    fi
fi

# Install Magic (Modular)
if ! command -v magic &> /dev/null; then
    echo -e "${BLUE}Installing Magic (Modular)...${NC}"
    curl -ssL https://magic.modular.com/b9714777-6262-4293-8515-565451e59544 | bash

    # Attempt to add magic to path for this session
    export PATH="$HOME/.modular/bin:$PATH"
else
    echo -e "${GREEN}Magic is already installed.${NC}"
fi

# Initialize Project & Install Python Deps
echo -e "${BLUE}Setting up Python environment with Magic...${NC}"

# Initialize magic project if not exists
if [ ! -f "mojoproject.toml" ] && [ ! -f "pyproject.toml" ]; then
    magic init . --format pyproject
fi

# Add dependencies
echo -e "${BLUE}Adding Python dependencies...${NC}"
magic add llama-cpp-python smolagents litellm mcp PyMuPDF python-docx python-jobspy pandas pydantic requests python-dotenv prompt_toolkit

# Build GumFuzzy
echo -e "${BLUE}Building GumFuzzy tool...${NC}"
mkdir -p bin
if [ -d "tools/GumFuzzy" ]; then
    cd tools/GumFuzzy
    go build -o ../../bin/fuzzy-picker
    cd ../..
    echo -e "${GREEN}GumFuzzy built successfully.${NC}"
else
    echo -e "${RED}tools/GumFuzzy directory not found!${NC}"
fi

# Create Symlink
echo -e "${BLUE}Creating global command 'career-agent'...${NC}"
chmod +x career.sh
# We need absolute path
INSTALL_DIR=$(pwd)
TARGET="/usr/local/bin/career-agent"

# Prompt for sudo to create symlink
echo -e "${BLUE}Requesting sudo permission to create symlink at $TARGET...${NC}"
if [ -L "$TARGET" ] || [ -f "$TARGET" ]; then
    sudo rm "$TARGET"
fi
sudo ln -s "$INSTALL_DIR/career.sh" "$TARGET"

echo -e "${GREEN}Installation Complete!${NC}"
echo -e "You can now run the agent from anywhere using: ${BLUE}career-agent${NC}"
