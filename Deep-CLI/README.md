# Dissector CLI

A gum-powered CLI that orchestrates multi-phase codebase analysis using Grok and optional DeepThinking MCP. It generates per-phase artifacts and final reports, with stateful resume support.

## Quick start

```bash
# 1) Install gum (macOS)
brew install gum

# 2) Launch interactive CLI (recommended)
./dissect

# 3) Prepare (optional repomix + checks)
./dissect prepare

# 4) Run
./dissect run
```

## Commands

- `./dissect` — interactive menu (creates config if missing)
- `./dissect init` — full config wizard
- `./dissect prepare` — checks env/paths, optional repomix
- `./dissect run [--force]` — run phases
- `./dissect resume [--force]` — continue from `.dissect_state.json`
- `./dissect status` — print state JSON
- `./dissect deepresearch` — run dataset audit script only
- `./dissect run+deepresearch` — run pipeline then dataset audit

## Config

Config lives at `.dissect/config.json` (ignored by git). An example config is provided at `config.example.json`.

Key fields:
- `target_path`, `output_dir`, `model`
- `phases` (ordered list)
- `difficulty_threshold` (MCP trigger)
- `tools` (`web_search`, `x_search`, `code_execution`)
- `prompt_override_dir` (optional)
- `repomix` (optional list of path/output/ignore entries)
- `ignore`, `max_files`, `max_chars`, `context_budget_chars`
- `max_tokens`, `max_retries`, `retry_backoff_sec`
- `mcp_enabled`, `mcp_inject`
- `force` (no overwrite unless true)

## Outputs

Default output layout:

```
<output_dir>/
  report.md
  report.json
  artifacts/
    phase_<id>/
      prompt.txt
      context.txt
      response.txt
      mcp.txt
      criteria.json
  .dissect_state.json
```

## Environment

Required:
- `XAI_API_KEY`

Optional (DeepThinking MCP):
- `DEEPTHINKING_MCP_COMMAND`
- `DEEPTHINKING_MCP_ARGS`
- `DEEPTHINKING_MCP_CWD`

## Example

Bark-style analysis + dataset audit (two separate runs):

```bash
# Bark-style
./dissect init
# set target_path to /Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition
./dissect prepare
./dissect run

# Dataset audit is still handled by the standalone grok script:
# /Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition/dataseta_deepresearch_script_fix-grok.py
```

## Safety

- Output directories are never overwritten unless `--force` is used.
- `.env` and `.dissect/` are ignored by git.
- Secret scan workflow included.
