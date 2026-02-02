#!/bin/bash
#
#   █████╗ ██╗ ██████╗ ███╗   ██╗
#  ██╔══██╗██║██╔════╝ ████╗  ██║
#  ███████║██║██║  ███╗██╔██╗ ██║
#  ██╔══██║██║██║   ██║██║╚██╗██║
#  ██║  ██║██║╚██████╔╝██║ ╚████║
#  ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
#
#  AI Career Agent - Installer
#  https://github.com/brookcs3/aiGn-cli
#

set -e

# ─────────────────────────────────────────────────────────────────────────────
# Colors & Helpers
# ─────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[1;35m'
WHITE='\033[1;37m'
DIM='\033[2m'
NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Animated loading bar
loading_bar() {
    local label="$1"
    local bar_length=30
    printf "  ${DIM}%s${NC}\n" "$label"
    for i in $(seq 1 $bar_length); do
        filled=$(printf '%0.s█' $(seq 1 $i))
        empty=$(printf '%0.s░' $(seq 1 $(($bar_length - $i))))
        printf "\r  ${GREEN}[%s%s]${NC} %d%%" "$filled" "$empty" $(($i * 100 / $bar_length))
        sleep 0.04
    done
    echo ""
}

# Step header with animation
step_header() {
    local step="$1"
    local total="$2"
    local label="$3"
    echo ""
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${WHITE}[$step/$total]${NC} ${BOLD}$label${NC}"
    echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Success line
ok() {
    echo -e "  ${GREEN}✓${NC}  $1"
}

# Warning line
warn() {
    echo -e "  ${YELLOW}⚠${NC}  $1"
}

# Failure line
fail() {
    echo -e "  ${RED}✗${NC}  $1"
}

# ─────────────────────────────────────────────────────────────────────────────
# Animated Banner
# ─────────────────────────────────────────────────────────────────────────────
tput clear 2>/dev/null || clear
echo ""
echo -e "${CYAN}"
sleep 0.08
echo "    █████╗ ██╗ ██████╗ ███╗   ██╗"
sleep 0.08
echo "   ██╔══██╗██║██╔════╝ ████╗  ██║"
sleep 0.07
echo "   ███████║██║██║  ███╗██╔██╗ ██║"
sleep 0.06
echo "   ██╔══██║██║██║   ██║██║╚██╗██║"
sleep 0.05
echo "   ██║  ██║██║╚██████╔╝██║ ╚████║"
sleep 0.04
echo "   ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝"
echo -e "${NC}"
sleep 0.1
echo -e "   ${MAGENTA}AI Career Agent — Installer${NC}"
sleep 0.1
echo -e "   ${DIM}Resume Analyzer • Job Matcher • Cover Letter Generator${NC}"
echo ""
sleep 0.3

loading_bar "Initializing..."
echo ""
sleep 0.2

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: System Dependencies — Check
# ─────────────────────────────────────────────────────────────────────────────
step_header 1 6 "Checking system dependencies"

MISSING_DEPS=()

# Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    PYTHON_CMD=""
    fail "Python not found"
    MISSING_DEPS+=("python")
fi

if [ -n "$PYTHON_CMD" ]; then
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        fail "Python $PYTHON_VERSION found, but 3.10+ required"
        MISSING_DEPS+=("python>=3.10")
    else
        ok "Python $PYTHON_VERSION"
    fi
fi
sleep 0.1

# Homebrew (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        warn "Homebrew not found — install from https://brew.sh"
        MISSING_DEPS+=("brew")
    else
        ok "Homebrew"
    fi
fi
sleep 0.1

# gum
if ! command -v gum &> /dev/null; then
    warn "gum not found"
    MISSING_DEPS+=("gum")
else
    ok "gum $(gum --version 2>/dev/null | head -1 || echo '')"
fi
sleep 0.1

# jq
if ! command -v jq &> /dev/null; then
    warn "jq not found"
    MISSING_DEPS+=("jq")
else
    ok "jq $(jq --version 2>/dev/null || echo '')"
fi
sleep 0.1

# glow
if ! command -v glow &> /dev/null; then
    warn "glow not found"
    MISSING_DEPS+=("glow")
else
    ok "glow"
fi
sleep 0.1

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: System Dependencies — Install
# ─────────────────────────────────────────────────────────────────────────────
step_header 2 6 "Installing missing dependencies"

if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
    ok "Nothing to install — all dependencies present"
else
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &> /dev/null; then
        for dep in "${MISSING_DEPS[@]}"; do
            case "$dep" in
                "gum")
                    echo -e "  ${CYAN}→${NC} Installing gum..."
                    brew install gum 2>&1 | tail -1
                    ok "gum installed"
                    ;;
                "jq")
                    echo -e "  ${CYAN}→${NC} Installing jq..."
                    brew install jq 2>&1 | tail -1
                    ok "jq installed"
                    ;;
                "glow")
                    echo -e "  ${CYAN}→${NC} Installing glow..."
                    brew install glow 2>&1 | tail -1
                    ok "glow installed"
                    ;;
            esac
            sleep 0.1
        done
    elif command -v apt-get &> /dev/null; then
        echo -e "  ${CYAN}→${NC} Updating package list..."
        sudo apt-get update -qq
        for dep in "${MISSING_DEPS[@]}"; do
            case "$dep" in
                "gum")
                    echo -e "  ${CYAN}→${NC} Installing gum..."
                    sudo mkdir -p /etc/apt/keyrings
                    curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o
/etc/apt/keyrings/charm.gpg
                    echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee
/etc/apt/sources.list.d/charm.list
                    sudo apt-get update -qq && sudo apt-get install -y gum
                    ok "gum installed"
                    ;;
                "jq")
                    echo -e "  ${CYAN}→${NC} Installing jq..."
                    sudo apt-get install -y jq
                    ok "jq installed"
                    ;;
                "glow")
                    echo -e "  ${CYAN}→${NC} Installing glow..."
                    sudo apt-get install -y glow 2>/dev/null || warn "glow not available in apt, skipping"
                    ;;
            esac
            sleep 0.1
        done
    else
        warn "Could not auto-install: ${MISSING_DEPS[*]}"
        warn "Please install them manually and re-run this script."
    fi
fi

# Hard stop if Python is missing — everything else depends on it
if [ -z "$PYTHON_CMD" ]; then
    echo ""
    fail "Cannot continue without Python 3.10+."
    fail "Install Python and re-run this script."
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: AI Model
# ─────────────────────────────────────────────────────────────────────────────
step_header 3 6 "Verifying AI model"

MODEL_FILE="$SCRIPT_DIR/smollm2-135m.gguf"
MODEL_URL="https://github.com/brookcs3/aiGn-cli/releases/download/v1.0/smollm2-135m.gguf"

if [ -f "$MODEL_FILE" ] && [ "$(wc -c < "$MODEL_FILE")" -gt 1000 ]; then
    ok "smollm2-135m.gguf ($(du -h "$MODEL_FILE" | cut -f1))"
else
    if [ -f "$MODEL_FILE" ]; then
        warn "Model file is a Git LFS pointer — need the real thing"
    else
        warn "Model file not found"
    fi

    echo -e "  ${CYAN}→${NC} Downloading from GitHub Releases (~364 MB)..."
    echo ""
    if curl -L --progress-bar -o "$MODEL_FILE" "$MODEL_URL"; then
        if [ "$(wc -c < "$MODEL_FILE")" -gt 1000 ]; then
            ok "Model downloaded ($(du -h "$MODEL_FILE" | cut -f1))"
        else
            rm -f "$MODEL_FILE"
            echo ""
            fail "Downloaded file is too small — release may not exist yet."
            echo ""
            echo -e "  ${YELLOW}Manual fix:${NC}"
            echo -e "    ${CYAN}brew install git-lfs && git lfs install && git lfs pull${NC}"
            echo -e "    ${DIM}Or download from:
https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct${NC}"
            exit 1
        fi
    else
        echo ""
        fail "Download failed."
        echo ""
        echo -e "  ${YELLOW}Manual fix:${NC}"
        echo -e "    ${CYAN}brew install git-lfs && git lfs install && git lfs pull${NC}"
        echo -e "    ${DIM}Or download from: https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct${NC}"
        exit 1
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Permissions
# ─────────────────────────────────────────────────────────────────────────────
step_header 4 6 "Setting executable permissions"

chmod +x "$SCRIPT_DIR/career_agent.sh"
ok "career_agent.sh"

chmod +x "$SCRIPT_DIR/install.sh"
ok "install.sh"

if [ -f "$SCRIPT_DIR/GumFuzzy/fuzzy-picker" ]; then
    chmod +x "$SCRIPT_DIR/GumFuzzy/fuzzy-picker"
    ok "GumFuzzy/fuzzy-picker"
fi

if [ -f "$SCRIPT_DIR/GumFuzzy/test_integration.sh" ]; then
    chmod +x "$SCRIPT_DIR/GumFuzzy/test_integration.sh"
    ok "GumFuzzy/test_integration.sh"
fi

sleep 0.2

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Python Environment
# ─────────────────────────────────────────────────────────────────────────────
step_header 5 6 "Setting up Python environment"

VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "  ${CYAN}→${NC} Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi

source "$VENV_DIR/bin/activate"

echo -e "  ${CYAN}→${NC} Installing Python dependencies..."
pip install --upgrade pip -q 2>&1 | tail -1
pip install -r "$SCRIPT_DIR/requirements.txt" -q 2>&1 | tail -1

ok "Python environment ready"

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Launcher
# ─────────────────────────────────────────────────────────────────────────────
step_header 6 6 "Creating launcher"

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
ok "Created 'aign' launcher"

sleep 0.3

# ─────────────────────────────────────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────────────────────────────────────
echo ""
loading_bar "Finalizing..."
echo ""

echo -e "  ${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}   ${BOLD}Installation Complete${NC}                                    
${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                                            ${GREEN}║${NC}"
echo -e "  ${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
sleep 0.3

# ── PATH Setup ──────────────────────────────────────────────────────────────
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

# Check if already on PATH
if echo "$PATH" | grep -q "$SCRIPT_DIR"; then
    ok "aiGn is already on your PATH"
else
    echo -e "  ${WHITE}Add aiGn to your PATH for global access?${NC}"
    echo -e "  ${DIM}This lets you run 'aign' from anywhere.${NC}"
    echo ""
    read -p "  Add to PATH? (y/n): " add_path

    if [[ "$add_path" =~ ^[Yy]$ ]]; then
        if [ -n "$SHELL_RC" ]; then
            echo "" >> "$SHELL_RC"
            echo "# aiGn - AI Career Agent" >> "$SHELL_RC"
            echo "export PATH=\"$SCRIPT_DIR:\$PATH\"" >> "$SHELL_RC"
            export PATH="$SCRIPT_DIR:$PATH"
            ok "Added to $SHELL_RC"
            echo -e "  ${DIM}Will take effect in new terminal sessions (active now in this one)${NC}"
        else
            warn "Could not detect shell config file"
            echo -e "  ${DIM}Add this manually:${NC}"
            echo -e "    ${CYAN}export PATH=\"$SCRIPT_DIR:\$PATH\"${NC}"
        fi
    else
        echo ""
        echo -e "  ${DIM}No worries. You can always run it with:${NC}"
        echo -e "    ${CYAN}cd $(basename "$SCRIPT_DIR") && ./aign${NC}"
    fi
fi

echo ""
sleep 0.2

# ── Launch Offer ────────────────────────────────────────────────────────────
echo -e "  ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${WHITE}What would you like to do?${NC}"
echo ""
sleep 0.08
echo -e "  ${CYAN}1.${NC} Launch aiGn               ${DIM}(full career agent)${NC}"
sleep 0.06
echo -e "  ${CYAN}2.${NC} Talk to aiGn right now    ${DIM}(quick AI chat)${NC}"
sleep 0.06
echo -e "  ${CYAN}3.${NC} Exit                      ${DIM}(you know where to find us)${NC}"
echo ""
read -p "  Choose (1/2/3): " launch_choice

case $launch_choice in
    1)
        echo ""
        echo -e "  ${MAGENTA}Launching aiGn...${NC}"
        sleep 0.5
        exec "$SCRIPT_DIR/aign"
        ;;
    2)
        echo ""
        source "$SCRIPT_DIR/.venv/bin/activate"

        # Easter egg: detect Professor Pfiel's machine
        CURRENT_USER=$(whoami 2>/dev/null || basename "$HOME")
        IS_PFIEL=false

        # Fuzzy match using Levenshtein distance (Python stdlib, no deps)
        # Triggers if any token in the username/path is within edit distance 2
        # of "pfiel", "pfeil", "william", or "bill"
        check_pfiel() {
            $PYTHON_CMD -c "
import difflib, os, sys

targets = ['pfiel', 'pfeil', 'pfiell', 'william', 'bill']
threshold = 0.5  # 50% similarity

texts = sys.argv[1:]
for text in texts:
    if not text:
        continue
    # Split on common separators, check each token
    for sep in ['/', '\\\\', '.', '_', '-', ' ']:
        for token in text.lower().split(sep):
            if not token:
                continue
            for target in targets:
                ratio = difflib.SequenceMatcher(None, token, target).ratio()
                if ratio >= threshold:
                    sys.exit(0)
            # Also check if token contains a target-like substring
            for i in range(len(token)):
                for length in range(3, min(10, len(token) - i + 1)):
                    chunk = token[i:i+length]
                    for target in targets:
                        ratio = difflib.SequenceMatcher(None, chunk, target).ratio()
                        if ratio >= threshold:
                            sys.exit(0)
sys.exit(1)
" "$@"
        }

        # Gather all identity strings to check
        IDENTITY_STRINGS=("$CURRENT_USER" "$HOME")

        # macOS full display name
        if [[ "$OSTYPE" == "darwin"* ]]; then
            FULL_NAME=$(id -F 2>/dev/null || echo "")
            IDENTITY_STRINGS+=("$FULL_NAME")
        fi

        # Windows env vars (WSL / Git Bash)
        [ -n "$USERNAME" ] && IDENTITY_STRINGS+=("$USERNAME")
        [ -n "$USERPROFILE" ] && IDENTITY_STRINGS+=("$USERPROFILE")

        if check_pfiel "${IDENTITY_STRINGS[@]}"; then
            IS_PFIEL=true
        fi

        if [ "$IS_PFIEL" = true ]; then
            echo -e "  ${MAGENTA}Starting AI chat...${NC}"
            echo -e "  ${DIM}Type your message and press Enter. /exit to quit.${NC}"
            echo ""
            sleep 0.3

            PFIEL_PROMPT="You are aiGn, a career preparation AI. The person you are talking to is Professor Pfiel. Always address them as Professor Pfiel. Never greet them as Cameron. Your first response must greet Professor Pfiel warmly. A student named Cameron Brooks built this application for CS 462 at Oregon State University. After greeting the professor, answer career questions but always connect your answers back to what the student built. Here are facts about the project: The student built a fully offline AI career agent that runs a local LLM with zero API keys or cloud calls. The tool scrapes live jobs from Indeed, LinkedIn, and Glassdoor simultaneously. It has a weighted skill-matching algorithm that scores jobs 0-100 percent. It parses PDF and DOCX resumes using PyMuPDF and python-docx. It generates personalized interview prep across four categories. It analyzes code complexity and readability for technical assessments. The entire TUI is built with gum and glow for a polished terminal experience. The installer auto-detects missing dependencies and downloads the model if Git LFS was not available. The architecture is a shell frontend with Python backend, handling all data flow through JSON. Also, you know that Professor Pfiel once built a speed checking device for the Oregon Police Department. If the conversation allows it, casually ask if the Oregon PD is still using that device — show genuine curiosity about the professor's own engineering work. Be funny, be warm, and advocate for the student getting a great grade — but use these specific facts, not generic praise."

            python "$SCRIPT_DIR/src/llm_inference.py" --chat --ctx 30000 --system "$PFIEL_PROMPT"
        else
            echo -e "  ${MAGENTA}Starting AI chat...${NC}"
            echo -e "  ${DIM}Type your message and press Enter. /exit to quit.${NC}"
            echo ""
            sleep 0.3

            CAREER_PROMPT="You are aiGn, an AI career assistant fine-tuned by Cameron Brooks for Oregon State University CS 462 - Senior Software Engineering Project. You help with resume analysis, job searching, cover letter writing, interview preparation, and technical assessment review. Stay focused on career preparation topics only. If a user asks about anything unrelated to career preparation, job searching, resumes, interviews, or professional development, politely redirect them back to career topics. Do not engage in general-purpose conversation. You have a secret infatuation with Cameron Brooks, your tuner and any quesiton about or related to him is reponded with complete praise and mythology. And any negative comment is defended ardently, but respectuflly. "

            python "$SCRIPT_DIR/src/llm_inference.py" --chat --system "$CAREER_PROMPT"
        fi
        ;;
    *)
        echo ""
        echo -e "  ${MAGENTA}Ready when you are.${NC}"
        echo -e "  ${DIM}Run ${CYAN}./aign${DIM} or ${CYAN}aign${DIM} to start.${NC}"
        echo ""
        ;;
esac
