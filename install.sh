#!/bin/bash
#
#   █████╗ ██╗ ██████╗ ███╗   ██╗
#  ██╔══██╗██║██╔════╝ ████╗  ██║
#  ███████║██║██║  ███╗██╔██╗ ██║
#  ██╔══██║██║██║   ██║██║╚██╗██║
#  ██║  ██║██║╚██████╔╝██║ ╚████║
#  ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
#
#  AI Career Agent - One-Click Installer
#  https://github.com/brookcs3/aiGn-cli
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get script directory (works even when called from elsewhere)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  ${BOLD}aiGn${NC} - AI Career Agent Installer                           ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  Resume Analyzer • Job Matcher • Cover Letter Generator    ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Check system dependencies
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[1/5]${NC} Checking system dependencies..."

MISSING_DEPS=()

# Check for Homebrew (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo -e "${YELLOW}⚠${NC}  Homebrew not found. Install it from https://brew.sh"
        MISSING_DEPS+=("brew")
    fi
fi

# Check for Python 3.10+
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}✗${NC}  Python not found"
    MISSING_DEPS+=("python")
fi

if [ -n "$PYTHON_CMD" ]; then
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        echo -e "${RED}✗${NC}  Python $PYTHON_VERSION found, but 3.10+ required"
        MISSING_DEPS+=("python>=3.10")
    else
        echo -e "${GREEN}✓${NC}  Python $PYTHON_VERSION"
    fi
fi

# Check for gum (TUI framework)
if ! command -v gum &> /dev/null; then
    echo -e "${YELLOW}⚠${NC}  gum not found"
    MISSING_DEPS+=("gum")
else
    echo -e "${GREEN}✓${NC}  gum $(gum --version 2>/dev/null | head -1 || echo '')"
fi

# Check for jq (JSON processor)
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠${NC}  jq not found"
    MISSING_DEPS+=("jq")
else
    echo -e "${GREEN}✓${NC}  jq $(jq --version 2>/dev/null || echo '')"
fi

# Check for glow (Markdown renderer) - optional but recommended
if ! command -v glow &> /dev/null; then
    echo -e "${YELLOW}⚠${NC}  glow not found (optional, for pretty output)"
    MISSING_DEPS+=("glow")
else
    echo -e "${GREEN}✓${NC}  glow"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Install missing dependencies
# ─────────────────────────────────────────────────────────────────────────────
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo ""
    echo -e "${BLUE}[2/5]${NC} Installing missing dependencies..."
    
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &> /dev/null; then
        for dep in "${MISSING_DEPS[@]}"; do
            case "$dep" in
                "gum")
                    echo -e "  ${CYAN}→${NC} Installing gum..."
                    brew install gum
                    ;;
                "jq")
                    echo -e "  ${CYAN}→${NC} Installing jq..."
                    brew install jq
                    ;;
                "glow")
                    echo -e "  ${CYAN}→${NC} Installing glow..."
                    brew install glow
                    ;;
            esac
        done
    elif command -v apt-get &> /dev/null; then
        # Linux (Debian/Ubuntu)
        echo -e "  ${CYAN}→${NC} Updating package list..."
        sudo apt-get update -qq
        for dep in "${MISSING_DEPS[@]}"; do
            case "$dep" in
                "gum")
                    echo -e "  ${CYAN}→${NC} Installing gum..."
                    sudo mkdir -p /etc/apt/keyrings
                    curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
                    echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list
                    sudo apt-get update -qq && sudo apt-get install -y gum
                    ;;
                "jq")
                    echo -e "  ${CYAN}→${NC} Installing jq..."
                    sudo apt-get install -y jq
                    ;;
                "glow")
                    echo -e "  ${CYAN}→${NC} Installing glow..."
                    sudo apt-get install -y glow 2>/dev/null || echo "    (glow not in apt, skipping)"
                    ;;
            esac
        done
    else
        echo -e "${YELLOW}⚠${NC}  Please install manually: ${MISSING_DEPS[*]}"
    fi
else
    echo -e "${BLUE}[2/5]${NC} All system dependencies present ${GREEN}✓${NC}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Set executable permissions
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[3/5]${NC} Setting executable permissions..."

chmod +x "$SCRIPT_DIR/career_agent.sh"
echo -e "${GREEN}✓${NC}  career_agent.sh"

chmod +x "$SCRIPT_DIR/install.sh"
echo -e "${GREEN}✓${NC}  install.sh"

if [ -f "$SCRIPT_DIR/GumFuzzy/fuzzy-picker" ]; then
    chmod +x "$SCRIPT_DIR/GumFuzzy/fuzzy-picker"
    echo -e "${GREEN}✓${NC}  GumFuzzy/fuzzy-picker"
fi

if [ -f "$SCRIPT_DIR/GumFuzzy/test_integration.sh" ]; then
    chmod +x "$SCRIPT_DIR/GumFuzzy/test_integration.sh"
    echo -e "${GREEN}✓${NC}  GumFuzzy/test_integration.sh"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Create Python virtual environment & install deps
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[4/5]${NC} Setting up Python environment..."

VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "  ${CYAN}→${NC} Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

# Activate and install
source "$VENV_DIR/bin/activate"
echo -e "  ${CYAN}→${NC} Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q

echo -e "${GREEN}✓${NC}  Python environment ready"

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Create launcher wrapper
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}[5/5]${NC} Creating launcher..."

# Create a wrapper script that activates venv before running
LAUNCHER="$SCRIPT_DIR/aign"
cat > "$LAUNCHER" << 'LAUNCHER_EOF'
#!/bin/bash
# aiGn Launcher - Activates venv and runs career agent

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Run the career agent
exec "$SCRIPT_DIR/career_agent.sh" "$@"
LAUNCHER_EOF

chmod +x "$LAUNCHER"
echo -e "${GREEN}✓${NC}  Created 'aign' launcher"

# ─────────────────────────────────────────────────────────────────────────────
# Done!
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Installation Complete!${NC}                                    ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}To run aiGn:${NC}"
echo ""
echo -e "    ${CYAN}cd $(basename "$SCRIPT_DIR") && ./aign${NC}"
echo ""
echo -e "  ${BOLD}Or add to your PATH for global access:${NC}"
echo ""
echo -e "    ${CYAN}echo 'export PATH=\"$SCRIPT_DIR:\$PATH\"' >> ~/.zshrc${NC}"
echo -e "    ${CYAN}source ~/.zshrc${NC}"
echo -e "    ${CYAN}aign${NC}"
echo ""
