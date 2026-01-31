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
- ✅ Checks & installs system dependencies (gum, jq, go)
- ✅ Sets up Magic (Modular) for Python environment management
- ✅ Installs all Python packages automatically
- ✅ Builds local tools (GumFuzzy)
- ✅ Creates the global `career-agent` launcher

## 🚀 Usage

Run the global command (if installed):
```bash
career-agent
```

Or run locally:
```bash
./career.sh
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
- [Magic](https://magic.modular.com/) - Python package manager
- [gum](https://github.com/charmbracelet/gum) - TUI framework
- [jq](https://stedolan.github.io/jq/) - JSON processor
- Go (for building tools)

**Python dependencies** (managed by `magic`):
- llama-cpp-python (local LLM inference)
- smolagents (HuggingFace agent framework)
- python-jobspy (job search API)
- PyMuPDF, python-docx (document parsing)

## 🗂️ Project Structure

```
aiGn-cli/
├── career.sh               # Main TUI interface
├── install.sh              # One-click installer
├── core/                   # Core logic (LLM inference)
├── jobs/                   # Job search & application logic
├── utils/                  # Helper scripts & parsers
├── prompts/                # AI Prompt templates
├── tools/                  # External tools (GumFuzzy, GumMouse)
└── pixi.toml               # Magic/Pixi project definition
```

## 📄 License

MIT

---

*Built for CS 462 - Senior Software Engineering Project*
