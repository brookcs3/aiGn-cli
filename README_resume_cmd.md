# resume_cmd.py

`resume_cmd.py` is a small CLI utility that fills a text template using variables and prints a single line of JSON to stdout (so other programs can `json.loads(...)` it easily).

It ships with a built-in resume-analysis template, but you can override it with `--template-file`.

## Quick Start

Inline resume text:

```bash
python3 resume_cmd.py --input "resume text here"
```

Resume text from a file:

```bash
python3 resume_cmd.py --input-file resume.txt
```

Write the filled template to a file:

```bash
python3 resume_cmd.py --input-file resume.txt --output filled.txt
```

## What It Outputs (stdout)

`resume_cmd.py` always prints exactly ONE JSON object (one line) to stdout.

- If you omit `--output`, the JSON includes `content` (the filled template text).
- If you pass `--output`, the JSON does NOT include `content` unless you add `--include-content`.

Example:

```json
{"ok": true, "template_path": null, "output_path": null, "input_path": "resume.txt", "resume_chars": 12345, "var_keys": ["resume_text"], "content": "..."}
```

## Template Placeholder Syntax

Inside the template text, you can use:

- `{name}`: raw insertion
- `{json:name}`: JSON-string escaped insertion (safe inside a JSON `"..."` string; no surrounding quotes)
- `{sh:name}`: safe for insertion inside a bash double-quoted string `"..."` (escapes `\` and `"`).

Notes:
- This does NOT touch JSON schema keys like `{{resume_text}}` (double braces). Those are left as-is.
- Missing variables are replaced with an empty string.

## Variables

By default, the resume input text is assigned to the variable name `resume_text`.

You can change that variable name with:

```bash
python3 resume_cmd.py --input-file resume.txt --input-var my_resume
```

Then your template should reference `{json:my_resume}` (or `{my_resume}` / `{sh:my_resume}` depending on context).

Add extra variables with repeatable `--var name=value`:

```bash
python3 resume_cmd.py --input-file resume.txt \
  --var job_title="Sound Designer" \
  --var company=SpaceX
```

Or load variables from a JSON file:

```bash
python3 resume_cmd.py --input-file resume.txt --vars-json vars.json
```

Where `vars.json` is a JSON object like:

```json
{"job_title": "Sound Designer", "company": "SpaceX"}
```

## Using a Custom Template

Use your own template file instead of the built-in one:

```bash
python3 resume_cmd.py --template-file /path/to/template.txt --input-file resume.txt --output filled.txt
```

## Embedding In Another Python Script

If you want the filled content programmatically, omit `--output` so `content` is included:

```python
import subprocess, json

out = subprocess.check_output(
    ["python3", "resume_cmd.py", "--input-file", "resume.txt"],
    text=True,
)
result = json.loads(out)
filled_template = result["content"]
```

## CLI Reference

- `--input TEXT` (required unless `--input-file`): resume text inline
- `--input-file PATH` (required unless `--input`): resume text from file
- `--output PATH` (optional): write the filled template to a file; if omitted, no file is written
- `--include-content` (optional): include filled template text in stdout JSON even when `--output` is used
- `--template-file PATH` (optional): use an external template file instead of the built-in template
- `--input-var NAME` (optional): variable name for the resume input text (default: `resume_text`)
- `--var name=value` (optional, repeatable): add/override variables
- `--vars-json PATH` (optional): load variables from a JSON object file

