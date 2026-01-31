# aiGn - AI Career Agent

```
   █████╗ ██╗ ██████╗ ███╗   ██╗
  ██╔══██╗██║██╔════╝ ████╗  ██║
  ███████║██║██║  ███╗██╔██╗ ██║
  ██╔══██║██║██║   ██║██║╚██╗██║
  ██║  ██║██║╚██████╔╝██║ ╚████║
  ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
```

> **AI-powered career automation for job seekers.**  
> Resume analysis • Job matching • Cover letter generation • Interview prep

## ⚡ Quick Install

```bash
git clone https://github.com/brookcs3/aiGn-cli.git
cd aiGn-cli
./install.sh
```

That's it. The installer handles everything:
- ✅ Checks & installs system dependencies (gum, jq, glow)
- ✅ Sets executable permissions
- ✅ Creates Python virtual environment
- ✅ Installs all Python packages
- ✅ Creates the `aign` launcher

## 🚀 Usage

```bash
./aign
```

Or add to PATH for global access:
```bash
echo 'export PATH="'$(pwd)'":$PATH' >> ~/.zshrc
source ~/.zshrc
aign
```

## 🎯 Features

| Feature | Description |
|---------|-------------|
| **Resume Analyzer** | Upload PDF/DOCX/TXT, get AI-powered feedback on strengths & gaps |
| **Job Matcher** | Search Indeed/LinkedIn/Glassdoor, ranked by skill match |
| **Cover Letter Generator** | AI-generated cover letters tailored to specific jobs |
| **Interview Prep** | Personalized behavioral/technical/system design questions |
| **Code Assessment** | Analyze your coding challenge submissions |

## 📋 Requirements

**Automatically installed by `install.sh`:**
- Python 3.10+
- [gum](https://github.com/charmbracelet/gum) - TUI framework
- [jq](https://stedolan.github.io/jq/) - JSON processor
- [glow](https://github.com/charmbracelet/glow) - Markdown renderer (optional)

**Python dependencies** (installed in `.venv`):
- llama-cpp-python (local LLM inference)
- smolagents (HuggingFace agent framework)
- python-jobspy (job search API)
- PyMuPDF, python-docx (document parsing)

## 🗂️ Project Structure

```
aiGn-cli/
├── aign                    # Main launcher (created by install.sh)
├── install.sh              # One-click installer
├── career_agent.sh         # TUI interface (bash + gum)
├── requirements.txt        # Python dependencies
│
├── backend/                # Python backend modules
│   ├── resume_analyzer.py
│   ├── job_matcher.py
│   ├── cover_letter.py
│   └── code_analyzer.py
│
├── model/                  # Local LLM
│   └── smollm2-135m-270mb.gguf
│
├── GumFuzzy/               # File picker component
│   └── fuzzy-picker
│
└── prompt_*.txt            # System prompts
```

## 🔧 Manual Installation

If you prefer to set things up yourself:

```bash
# Clone
git clone https://github.com/brookcs3/aiGn-cli.git
cd aiGn-cli

# Install system deps (macOS)
brew install gum jq glow

# Set permissions
chmod +x career_agent.sh install.sh GumFuzzy/fuzzy-picker

# Python setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
./career_agent.sh
```

## 📄 License

MIT

---

*Built for CS 462 - Senior Software Engineering Project*
