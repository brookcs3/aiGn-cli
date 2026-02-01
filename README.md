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
> Resume analysis • Job matching • Cover letters • Interview prep

---

## ⚡ Quick Start

```bash
git clone https://github.com/brookcs3/aiGn-cli.git
cd aiGn-cli
./install.sh && ./aign
```

The installer handles everything:
- ✅ Checks & installs system deps (gum, jq, glow)
- ✅ Creates Python virtual environment
- ✅ Installs Python packages (llama-cpp, jobspy, etc.)
- ✅ Creates the `aign` launcher

---

## 🚀 Usage

```bash
# Run from project directory
./aign

# Or add to PATH for global access
echo 'export PATH="'$(pwd)'":$PATH' >> ~/.zshrc
source ~/.zshrc
aign
```

---

## 🎯 Features

| Feature | Description |
|---------|-------------|
| **📄 Resume Analyzer** | Upload PDF/DOCX/TXT, get AI feedback on strengths & gaps |
| **🔍 Job Matcher** | Search Indeed/LinkedIn/Glassdoor, ranked by skill match |
| **📝 Cover Letter Generator** | AI-generated cover letters tailored to specific jobs |
| **🎤 Interview Prep** | Behavioral / Technical / System Design / Culture Fit questions |
| **💻 Code Assessment** | Analyze your coding challenge submissions |

---

## 📋 Requirements

**System (auto-installed):**
- Python 3.10+
- [gum](https://github.com/charmbracelet/gum) - Beautiful TUI components
- [jq](https://stedolan.github.io/jq/) - JSON processing
- [glow](https://github.com/charmbracelet/glow) - Markdown rendering (optional)

**Python (in `.venv`):**
- `llama-cpp-python` - Local LLM inference (uses SmolLM2-135M)
- `python-jobspy` - Job scraping from Indeed/LinkedIn/Glassdoor
- `PyMuPDF`, `python-docx` - Document parsing

---

## 🗂️ Project Structure

```
aiGn-cli/
├── aign                      # Main launcher (auto-created)
├── career_agent.sh           # TUI interface (bash + gum)
├── install.sh                # One-click installer
├── requirements.txt          # Python dependencies
│
├── prompts/                  # AI prompt templates
│   ├── interview_prep_prompt.txt
│   ├── prompt_job_analysis.txt
│   └── prompt_resume_generator.txt
│
├── backend/                  # Python modules
│   ├── resume_analyzer.py
│   ├── job_matcher.py
│   ├── cover_letter.py
│   └── code_analyzer.py
│
├── job_scraper.py            # Job search (Indeed/LinkedIn/Glassdoor)
├── llm_inference.py          # Local LLM interface
├── resume_parser.py          # Document text extraction
├── job_application_pipeline.py  # Cover letter TUI workflow
│
├── applications/             # Saved job applications
├── output/                   # Generated analysis files
├── orphaned_files/           # Deprecated scripts
│
└── smollm2-135m.gguf         # Local LLM model
```

---

## 🛠️ Manual Setup

If you prefer DIY:

```bash
# 1. Clone
git clone https://github.com/brookcs3/aiGn-cli.git
cd aiGn-cli

# 2. System deps (macOS)
brew install gum jq glow

# 3. Permissions
chmod +x career_agent.sh install.sh

# 4. Python environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 5. Run
./career_agent.sh
```

---

## 🎮 Menu Walkthrough

### 1. Resume Analyzer
- Upload your resume (PDF, DOCX, or TXT)
- AI analyzes: Key points, strengths, gaps, suggestions
- View results inline with `glow` or save to file

### 2. Match Jobs to Skills
- Enter job title, location, skills
- Scrapes 3 job sites simultaneously
- Shows top matches with skill alignment

### 3. Cover Letter Generator
- Browse/paste job posting
- AI analyzes requirements
- Generates tailored cover letter
- Copy to clipboard or save

### 4. Interview Prep
- Choose type: Behavioral, Technical, System Design, Culture Fit
- Enter target role and skills
- AI generates 5-8 personalized questions with:
  - What interviewers look for
  - Strong answer frameworks
  - Common pitfalls to avoid

### 5. Code Assessment
- Paste or upload code solution
- AI analyzes: strengths, suggestions, complexity
- Get actionable feedback

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `./install.sh` or `source .venv/bin/activate` |
| `gum: command not found` | `brew install gum` |
| Job scraper hangs | Normal - scraping 3 sites takes 10-30s |
| Clipboard not working | Install `pyperclip`: `python -m pip install pyperclip` |
| Model loads slowly | First run downloads/caches the model |

---

## 📝 Output Files

Generated files are organized in `output/`:

- `resume_analysis_*.txt` - Resume feedback
- `job_matches_*.txt` - Job search results
- `interview_prep_*.md` - Interview questions
- `filled_prompt.txt` - Last cover letter prompt
- `debug_*.txt` - Debug info

---

## 🤝 Contributing

This is a CS 462 - Senior Software Engineering Project.  
Built with:
- [SmolLM2](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) - Local LLM
- [JobSpy](https://github.com/Bunsly/JobSpy) - Job scraping
- [gum](https://github.com/charmbracelet/gum) - TUI framework

---

## 📄 License

MIT

---

*Built for CS 462 - Senior Software Engineering Project*  
*Michigan State University - Winter 2026*
