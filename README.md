<p align="center">
  <pre align="center">
   █████╗ ██╗ ██████╗ ███╗   ██╗
  ██╔══██╗██║██╔════╝ ████╗  ██║
  ███████║██║██║  ███╗██╔██╗ ██║
  ██╔══██║██║██║   ██║██║╚██╗██║
  ██║  ██║██║╚██████╔╝██║ ╚████║
  ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝
  </pre>
</p>

<h3 align="center">AI-Powered Career Agent CLI</h3>

<p align="center">
  Resume analysis &bull; Job matching &bull; Cover letters &bull; Interview prep &bull; Code assessment
</p>

<p align="center">
  <strong>Fully offline.</strong> No API keys. No cloud. A local LLM runs entirely on your machine.
</p>

---

## Overview

**aiGn** is a terminal-based career automation tool that brings AI-powered job preparation into a single, polished command-line interface. It uses a local LLM ([SmolLM2-135M](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct)) running on-device via [`llama-cpp-python`](https://github.com/abetlen/llama-cpp-python) -- no external API calls, no subscriptions, no data leaving your machine.

Built with [gum](https://github.com/charmbracelet/gum) for a rich terminal UI, the tool scrapes live job postings from Indeed, LinkedIn, and Glassdoor, then matches them against your skills with a weighted scoring algorithm.

<p align="center">
  <img src="src/1-%20five%20Choices.png" alt="aiGn main menu showing 5 career task options" width="600">
</p>
<p align="center"><em>The main menu -- navigate with arrow keys, select with Enter</em></p>

---

## Important: Git LFS Required (Large Model File)

This repository contains `smollm2-135m.gguf`, a **~364 MB** quantized language model tracked with [Git Large File Storage (LFS)](https://git-lfs.com/). Without Git LFS installed, cloning will only download a tiny pointer file instead of the actual model.

> **Note:** If you cloned without LFS, the installer (`install.sh`) and the launcher (`aign`) will detect the missing model and automatically download it from GitHub Releases. Git LFS is still recommended for the smoothest experience, but it is no longer a hard blocker.

### Setting up Git LFS

**Before cloning**, make sure Git LFS is installed:

```bash
# macOS (Homebrew)
brew install git-lfs

# Ubuntu / Debian
sudo apt-get install git-lfs

# Windows (via Git for Windows -- usually included)
# Or download from https://git-lfs.com
```

Then initialize it (one-time setup per machine):

```bash
git lfs install
```

Now you can clone normally and the model will download automatically:

```bash
git clone https://github.com/brookcs3/aiGn-cli.git
```

### Verifying the model downloaded correctly

After cloning, verify the model file is real (not a pointer):

```bash
ls -lh smollm2-135m.gguf
# Should show ~364 MB, NOT 130 bytes
```

If it shows a tiny file (e.g., 130 bytes), you cloned without LFS. Fix it:

```bash
git lfs pull
```

### If you already cloned without LFS

```bash
cd aiGn-cli
git lfs install    # Initialize LFS in this repo
git lfs pull       # Download the actual model file
```

### How LFS tracking is configured

The `.gitattributes` file contains:

```
*.gguf filter=lfs diff=lfs merge=lfs -text
```

This ensures all `.gguf` model files are stored in LFS rather than inline in the Git history. If you add additional models, they will automatically be tracked by LFS.

---

## Quick Start

```bash
# 1. Make sure Git LFS is installed (see above)
git clone https://github.com/brookcs3/aiGn-cli.git
cd aiGn-cli

# 2. Run the installer
./install.sh

# 3. Launch
./aign
```

The installer handles everything automatically:
- Checks for and installs system dependencies (Python 3.10+, gum, jq, glow)
- Verifies the AI model is present (downloads from GitHub Releases if missing or if Git LFS wasn't available)
- Creates a Python virtual environment (`.venv/`)
- Installs all Python packages from `requirements.txt`
- Generates the `aign` launcher script

---

## Features

### 1. Resume Analyzer

Upload a resume in **PDF**, **DOCX**, or **TXT** format. The AI analyzes it and returns structured feedback:

- **Candidate profile** and target role identification
- **Key skills** and notable achievements
- **Strengths** assessment
- **Gaps** and areas for improvement
- **Content classification** (technical, creative, hybrid, academic, management)

Use the built-in fuzzy file picker to browse your filesystem, or paste a file path directly.

<p align="center">
  <img src="src/2-%20Press%20Forward%20Slash%20TO%20enter%20fuzzy%20Search.png" alt="Fuzzy file picker filtering resume files" width="600">
</p>
<p align="center"><em>The fuzzy file picker -- type to filter, arrow keys to navigate</em></p>

---

### 2. Job Matcher

Enter your skills and preferred location. The tool scrapes **Indeed**, **LinkedIn**, and **Glassdoor** simultaneously and ranks results using a weighted skill-matching algorithm:

- **Title matches** weighted at 1.5x
- **Description keyword matches** at 1.0x
- **Partial matches** at 0.5x
- **Role bonus** of +15% when 2+ keywords align
- Results sorted by **match percentage** (0-100%)

Includes salary estimates, direct application links, and job source tags. Results are cached for 1 hour to avoid rate limits on subsequent searches.

<p align="center">
  <img src="src/3%20-%2016%20posotiosn%20found%20top.png" alt="Job matching results showing 16 positions with match percentages" width="600">
</p>
<p align="center"><em>Job matches ranked by skill alignment -- salary, location, and direct links included</em></p>

---

### 3. Cover Letter Generator

An interactive pipeline that walks you through generating a tailored cover letter:

1. Scrapes fresh job postings based on your search criteria
2. Select a specific job to target
3. AI analyzes the job requirements and company signals
4. Answer a series of personalized questions about your experience
5. Generates a complete, tailored cover letter
6. Save to file or copy to clipboard

<p align="center">
  <img src="src/4%20-%20Screenshot%202026-02-01%20at%202.31.57%20AM.png" alt="Job posting detail view with cover letter prompt" width="600">
</p>
<p align="center"><em>View job details and opt into cover letter generation</em></p>

<p align="center">
  <img src="src/6%20Pre%20Q.png" alt="AI analyzing job posting and generating questions" width="600">
</p>
<p align="center"><em>The AI analyzes the posting, then asks targeted questions to personalize your letter</em></p>

---

### 4. Interview Prep

Generate 5-8 personalized interview questions across four categories:

| Type | Focus |
|------|-------|
| **Behavioral** | Past experiences, soft skills, STAR method scenarios |
| **Technical** | Coding problems, algorithms, language-specific questions |
| **System Design** | Architecture, scaling, distributed systems |
| **Culture Fit** | Values alignment, work style, team dynamics |

Each question includes:
- What the interviewer is looking for
- A strong answer framework
- Common pitfalls to avoid

<p align="center">
  <img src="src/7%20-%20behScreenshot%202026-02-01%20at%202.33.38%20AM.png" alt="Interview prep screen showing type selection" width="600">
</p>
<p align="center"><em>Select your interview type -- questions are personalized to your target role and skills</em></p>

---

### 5. Technical Assessment Feedback

Upload a code file and get AI-powered feedback on your solution. Supports **13+ languages** including Python, JavaScript, Java, Go, Rust, C/C++, TypeScript, Ruby, Swift, and Kotlin.

Analysis includes:
- **Time complexity** estimation (O(1) through O(2^n))
- **Space complexity** estimation
- **Readability score** (0-100) based on comments, line length, naming conventions, and cyclomatic complexity
- **Strengths** of the implementation
- **Improvement suggestions**

---

## Requirements

### System Dependencies

These are installed automatically by `install.sh`, or you can install them manually:

| Dependency | Purpose | Install |
|------------|---------|---------|
| **Python 3.10+** | Backend runtime | `brew install python` / `apt install python3` |
| **[gum](https://github.com/charmbracelet/gum)** | Terminal UI components (menus, inputs, spinners) | `brew install gum` |
| **[jq](https://stedolan.github.io/jq/)** | JSON processing between shell and Python | `brew install jq` |
| **[glow](https://github.com/charmbracelet/glow)** | Markdown rendering in terminal (optional) | `brew install glow` |
| **[Git LFS](https://git-lfs.com/)** | Large file storage for the ML model | `brew install git-lfs` |

### Python Dependencies

Installed into `.venv/` via `requirements.txt`:

| Package | Purpose |
|---------|---------|
| `llama-cpp-python` >= 0.3.0 | Local GGUF model inference (Metal GPU acceleration on macOS) |
| `python-jobspy` >= 1.1.0 | Job scraping from Indeed, LinkedIn, Glassdoor |
| `PyMuPDF` >= 1.24.0 | PDF text extraction |
| `python-docx` >= 1.1.0 | DOCX text extraction |
| `smolagents` >= 1.0.0 | HuggingFace agent framework |
| `litellm` >= 1.0.0 | LLM API bridge |
| `pandas` >= 2.0.0 | Data processing |
| `pydantic` >= 2.0.0 | Data validation |
| `pyperclip` >= 1.8.0 | Clipboard integration |
| `prompt-toolkit` >= 3.0.0 | Interactive CLI input |
| `python-dotenv` >= 1.0.0 | Environment variable management |
| `requests` >= 2.31.0 | HTTP requests |
| `mcp` >= 1.0.0 | Model Context Protocol |

### The Local LLM

aiGn uses **[SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct)** in GGUF format for all AI inference. Key characteristics:

- **~364 MB** on disk (quantized)
- **32,768 token** context window
- Runs on **CPU** or with **Metal GPU acceleration** on Apple Silicon
- Fully offline -- no network calls for inference
- Loaded via `llama-cpp-python` with automatic stderr suppression for clean output

---

## Manual Setup

If you prefer to set things up yourself instead of using `install.sh`:

```bash
# 1. Clone (make sure Git LFS is installed first!)
git clone https://github.com/brookcs3/aiGn-cli.git
cd aiGn-cli

# Verify the model downloaded (should be ~364 MB)
ls -lh smollm2-135m.gguf

# 2. Install system dependencies (macOS)
brew install gum jq glow

# 3. Set executable permissions
chmod +x career_agent.sh install.sh

# 4. Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 5. Run
./career_agent.sh
```

### Adding to PATH (optional)

For global access from any directory:

```bash
echo 'export PATH="'$(pwd)'":$PATH' >> ~/.zshrc
source ~/.zshrc
aign
```

---

## Project Structure

```
aiGn-cli/
├── aign                          # Main launcher (auto-created by installer)
├── career_agent.sh               # Primary TUI interface (~600 lines, bash + gum)
├── install.sh                    # One-click automated installer
├── requirements.txt              # Python dependencies
├── smollm2-135m.gguf             # Local LLM model (~364 MB, Git LFS)
├── .gitattributes                # Git LFS tracking rules
│
├── src/
│   ├── llm_inference.py          # Local LLM inference engine
│   ├── resume_parser.py          # Document text extraction & template rendering
│   ├── job_scraper.py            # Job search CLI interface
│   ├── job_application_pipeline.py  # Interactive cover letter workflow
│   │
│   ├── backend/
│   │   ├── config.py             # Centralized configuration & constants
│   │   ├── resume_analyzer.py    # Resume AI analysis module
│   │   ├── job_matcher.py        # Weighted skill-matching algorithm + caching
│   │   ├── cover_letter.py       # Cover letter generation
│   │   ├── interview_prep.py     # Interview question generation
│   │   ├── code_analyzer.py      # Code complexity & readability analysis
│   │   ├── job_application.py    # Job application logic
│   │   └── utils/
│   │       ├── pdf_parser.py     # PyMuPDF-based PDF text extraction
│   │       ├── docx_parser.py    # python-docx-based DOCX extraction
│   │       └── resume_analyzer.py
│   │
│   ├── prompts/                  # AI prompt templates
│   │   ├── interview_prep_prompt.txt
│   │   ├── prompt_job_analysis.txt
│   │   └── prompt_resume_generator.txt
│   │
│   ├── GumFuzzy/                 # Custom fuzzy file picker (compiled Go binary)
│   ├── Deep-CLI/                 # Custom gum extensions & vendor tools
│   ├── output/                   # Generated analysis results
│   ├── applications/             # Saved job applications
│   └── orphaned_files/           # Deprecated scripts
│
├── .venv/                        # Python virtual environment (created by installer)
└── .cache/                       # Job search result cache (1-hour TTL)
```

---

## Architecture

aiGn follows a **shell frontend / Python backend** architecture:

```
┌─────────────────────────────────────────────────┐
│                  career_agent.sh                 │
│           (Bash + Gum TUI Interface)             │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ gum menu │ │gum input │ │  gum spin/pager  │ │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘ │
│       │             │                │           │
├───────┴─────────────┴────────────────┴───────────┤
│                 Python Backend                    │
│                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │resume_parser│  │ job_matcher  │  │  code    │ │
│  │   .py       │  │    .py       │  │analyzer  │ │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘ │
│         │                │               │       │
│  ┌──────┴────────────────┴───────────────┴─────┐ │
│  │           llm_inference.py                   │ │
│  │      (llama-cpp-python + SmolLM2)            │ │
│  └──────────────────────────────────────────────┘ │
│                                                  │
│  ┌──────────────────────────────────────────────┐ │
│  │            smollm2-135m.gguf                  │ │
│  │         (Local LLM - 364 MB)                  │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**Data flow:** The shell script collects user input via gum, passes it to Python scripts as arguments or piped input, Python modules process the data and run LLM inference, then return JSON or markdown back to the shell for display via `gum pager` or `glow`.

**Prompt templating:** Templates in `src/prompts/` use `{{PLACEHOLDER}}` syntax, substituted at runtime with Perl regex in the shell layer or Python's string formatting in the backend.

---

## Output Files

All generated files are saved to `src/output/`:

| File Pattern | Content |
|-------------|---------|
| `resume_analysis_YYYYMMDD_HHMMSS.txt` | Resume feedback and scoring |
| `job_matches_YYYYMMDD_HHMMSS.txt` | Job search results with match scores |
| `interview_prep_[type]_YYYYMMDD_HHMMSS.md` | Generated interview questions |
| `filled_prompt.txt` | Most recent cover letter / prompt output |
| `debug_ai_response.txt` | Raw LLM output (for debugging) |
| `debug_resume_response.txt` | Resume analysis debug data |
| `latest_results.md` | Most recent markdown-formatted results |

Saved job applications are stored in `src/applications/` organized by company and role.

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| **Model file is 130 bytes** | Cloned without Git LFS | `git lfs install && git lfs pull` |
| **`ModuleNotFoundError`** | Virtual environment not active | `source .venv/bin/activate` or re-run `./install.sh` |
| **`gum: command not found`** | gum not installed | `brew install gum` (macOS) or see [gum install docs](https://github.com/charmbracelet/gum#installation) |
| **Job scraper returns no results** | Rate limited or network issue | Tool falls back to demo data automatically; try again later |
| **Job scraper is slow** | Scraping 3 sites simultaneously | Normal -- takes 10-30s; results are cached for 1 hour after |
| **Clipboard not working** | pyperclip needs a backend | `pip install pyperclip` and ensure `pbcopy` (macOS) or `xclip` (Linux) is available |
| **Model loads slowly on first run** | Model being loaded into memory | Subsequent runs in the same session are faster; Metal GPU acceleration helps on Apple Silicon |
| **`llama-cpp-python` build fails** | Missing C++ compiler or CMake | `xcode-select --install` (macOS) or `apt install build-essential cmake` (Linux) |

---

## Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **macOS (Apple Silicon)** | Fully supported | Metal GPU acceleration for LLM inference |
| **macOS (Intel)** | Supported | CPU inference only |
| **Linux (Ubuntu/Debian)** | Supported | Installer uses `apt-get` for system deps |
| **Windows** | Not supported | Use WSL2 with Ubuntu for Linux compatibility |

---

## Built With

| Tool | Role |
|------|------|
| [SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) | Local language model (HuggingFace) |
| [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) | GGUF model inference runtime |
| [gum](https://github.com/charmbracelet/gum) | Terminal UI framework (Charm.sh) |
| [glow](https://github.com/charmbracelet/glow) | Terminal markdown renderer (Charm.sh) |
| [JobSpy](https://github.com/Bunsly/JobSpy) | Indeed / LinkedIn / Glassdoor scraper |
| [PyMuPDF](https://pymupdf.readthedocs.io/) | PDF text extraction |
| [python-docx](https://python-docx.readthedocs.io/) | DOCX text extraction |

---

## License

MIT

---

<p align="center">
  <em>CS 462 -- Senior Software Engineering Project</em><br>
  <em>Oregon State University -- Winter 2026</em>
</p>
