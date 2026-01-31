# CareerAI Agent

> "Your AI-powered career assistant."

**CareerAI Agent** is a professional CLI tool powered by a local LLM (`SmolLM2-135M`) and specialized agents to help you optimize your job search. It can analyze resumes, match jobs to your skills, generate cover letters, and prepare you for interviews.

## Features

- **Resume Analyzer**: Upload your resume (PDF/DOCX) for instant AI feedback, scoring, and improvement tips.
- **Job Matcher**: Find real job listings (via Indeed/Glassdoor) that match your specific skill set.
- **Cover Letter Generator**: Auto-generate tailored cover letters based on a job description and your resume.
- **Interview Prep**: Get personalized behavioral and technical interview questions for your target role.
- **Code Analyzer**: Receive AI feedback on your code samples (time complexity, readability, etc.).
- **Privacy First**: Runs locally on your machine using a small, efficient language model.

## Installation

We use **Pixi** for seamless environment management. The installer handles everything for you.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/brookcs3/aiGn-cli.git
    cd aiGn-cli
    ```

2.  **Run the installer:**
    ```bash
    ./install.sh
    ```
    This will:
    - Install `pixi` (if missing).
    - Set up a managed Python environment with all dependencies.
    - Install system tools (`gum`, `jq`, `go`).
    - Build the custom tools (`gum-custom`, `GumFuzzy`).
    - Create a global `career-agent` command.

3.  **Run the agent:**
    ```bash
    career-agent
    ```

## Project Structure

This project has been professionally structured for maintainability:

- **`src/`**: Source code
    - **`agent/`**: Core LLM logic and configuration.
    - **`jobs/`**: Job scraping and application pipelines.
    - **`utils/`**: Parsers (PDF/DOCX), JSON helpers, and analyzers.
    - **`prompts/`**: AI personas and prompt templates.
- **`tools/`**: Helper binaries
    - **`gum/`**: Custom build of the `gum` TUI tool.
    - **`GumFuzzy/`**: Go-based fuzzy file picker.

## Dependencies

- **System**: `gum`, `jq`, `go` (installed automatically).
- **Python**: Managed via `pixi` (see `pixi.toml` after install).
- **Model**: `SmolLM2-135M` (downloaded automatically or included).

## Usage

Once installed, simply type `career-agent` in your terminal to launch the interactive menu. Navigate using the arrow keys and `Enter`.

---
*Note: This tool uses "pseudo JSON" generation for resilience with small language models. Output parsing is designed to be fuzzy and robust.*
