#!/usr/bin/env python3
"""
resume_parser.py

Fill template placeholders for a resume-analysis Claude command snippet.

This program outputs exactly ONE line of JSON to stdout so other Python can
`json.loads(...)` it easily.

Template syntax (inside the template text):
- {name}       -> raw insertion
- {json:name}  -> JSON-string escaped insertion (no surrounding quotes)
- {sh:name}    -> safe inside a bash double-quoted string

Examples:
  # Write a filled file
  python3 resume_parser.py --input-file resume.txt --output filled.txt

  # Return filled content via JSON (no file written)
  python3 resume_parser.py --input-file resume.txt

  # Multiple variables
  python3 resume_parser.py --input-file resume.txt --var job_title="Sound Designer" --var company=SpaceX

  # Custom template file (optional override)
  python3 resume_parser.py --template-file /path/to/template.txt --input-file resume.txt --output filled.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import re

# Add parsers to path
sys.path.insert(0, str(Path(__file__).parent / "parsers"))

try:
    from pdf_parser import extract_text_from_pdf
    from docx_parser import extract_text_from_docx
    HAS_PARSERS = True
except ImportError:
    HAS_PARSERS = False


DEFAULT_TEMPLATE = """<instructions>
1. Summarize the resume at a high level
2. Extract key skills, roles, and achievements
3. Identify the resume's target role and positioning
4. Note any standout lines or bullets worth citing
</instructions>
" \\
  --system-prompt "You are a resume analyst. Analyze the provided resume content and return structured, reviewer-ready insights." \\
  --json-schema '{
    "type": "object",
    "properties": {
      "variable_name": {
        "type": "object",
        "properties": {
          "{{resume_text}}": {
            "type": "string",
            "description": "{json:resume_text}"

          }
        },
        "required": ["{{resume_text}}"],
        "additionalProperties": false
      },
      "analysis": {
        "type": "object",
        "properties": {
          "candidate_profile": {
            "type": "string",
            "description": "High-level description of the candidate (role, seniority, domain)"
          },
          "target_role": {
            "type": "string",
            "description": "Inferred target role or job family the resume is positioning for"
          },
          "content_type": {
            "type": "string",
            "enum": ["technical", "creative", "hybrid", "academic", "management", "other"],
            "description": "Overall resume orientation"
          },
          "summary": {
            "type": "string",
            "description": "Concise 2-3 sentence summary of the resume"
          },
          "key_points": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Core skills, experiences, or achievements"
          },
          "standout_quotes": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "text": { "type": "string" },
                "context": { "type": "string" }
              },
              "required": ["text", "context"]
            },
            "description": "Notable resume lines or bullets worth citing"
          },
          "strengths": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Key strengths demonstrated by the resume"
          },
          "gaps_or_risks": {
            "type": "array",
            "items": { "type": "string" },
            "description": "Potential weaknesses, gaps, or ambiguity"
          }
        },
        "required": [
          "candidate_profile",
          "target_role",
          "content_type",
          "summary",
          "key_points"
        ]
      }
    },
    "required": ["variable_name", "analysis"],
    "additionalProperties": false
  }'
"""


_PLACEHOLDER_RE = re.compile(r"\{(?:(?P<kind>json|sh|raw):)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\}")


def _json_escape_for_insertion(value: str) -> str:
    """
    Return a string escaped for insertion inside an existing JSON string value.
    (i.e. no surrounding quotes).
    """
    return json.dumps(value, ensure_ascii=False)[1:-1]


def _sh_double_quote_escape(value: str) -> str:
    # For insertion into: "...".
    return value.replace("\\", "\\\\").replace('"', '\\"')


def read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Fallback for odd encodings; keeps the CLI robust.
        return path.read_text(encoding="latin-1")


def extract_resume_text(path: Path) -> str:
    """Extract text from PDF, DOCX, or plain text file."""
    ext = path.suffix.lower()

    if ext == ".pdf":
        if not HAS_PARSERS:
            raise SystemExit("PDF parsing requires pymupdf. Install with: pip install pymupdf")
        return extract_text_from_pdf(str(path))

    elif ext in [".docx", ".doc"]:
        if not HAS_PARSERS:
            raise SystemExit("DOCX parsing requires python-docx. Install with: pip install python-docx")
        return extract_text_from_docx(str(path))

    else:
        # Assume plain text
        return read_text_file(path)

def render_template(template_text: str, variables: dict[str, str]) -> str:
    """
    Render template placeholders using the variables mapping.
    This does NOT touch JSON-schema keys like {{resume_text}} (double braces).
    """

    def repl(m: re.Match) -> str:
        kind = m.group("kind") or "raw"
        name = m.group("name")
        value = variables.get(name, "")
        if kind == "json":
            return _json_escape_for_insertion(value)
        if kind == "sh":
            return _sh_double_quote_escape(value)
        return value

    return _PLACEHOLDER_RE.sub(repl, template_text)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--template-file",
        default=None,
        help="Optional template file path. If omitted, uses the built-in template.",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Output path to write the filled template. If omitted, no file is written and JSON includes content.",
    )

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Resume text (inline)")
    src.add_argument("--input-file", help="Path to a .txt file containing resume text")
    p.add_argument(
        "--input-var",
        default="resume_text",
        help="Variable name to assign the input text to (default: resume_text)",
    )

    p.add_argument(
        "--var",
        action="append",
        default=[],
        help='Additional variables to fill in the template (repeatable), format: name=value',
    )
    p.add_argument(
        "--vars-json",
        default=None,
        help='Path to a JSON file of variables (object/map). Example: {"job_title": "Sound Designer"}',
    )

    p.add_argument(
        "--include-content",
        action="store_true",
        help="Include the filled template content in the JSON output (can be large).",
    )
    args = p.parse_args(argv)

    template_path = Path(args.template_file) if args.template_file else None
    output_path = Path(args.output) if args.output else None

    if template_path is not None:
        if not template_path.exists():
            raise SystemExit(f"Template not found: {template_path}")
        template_text = read_text_file(template_path)
    else:
        template_text = DEFAULT_TEMPLATE

    input_path = None
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            raise SystemExit(f"Input file not found: {input_path}")
        resume_text = extract_resume_text(input_path)
    else:
        resume_text = args.input or ""

    variables: dict[str, str] = {}
    if args.vars_json:
        vars_path = Path(args.vars_json)
        if not vars_path.exists():
            raise SystemExit(f"Vars JSON not found: {vars_path}")
        try:
            raw = json.loads(read_text_file(vars_path))
        except Exception as e:
            raise SystemExit(f"Vars JSON invalid: {e}")
        if not isinstance(raw, dict):
            raise SystemExit("Vars JSON must be a JSON object/map.")
        variables.update({str(k): str(v) for k, v in raw.items()})

    for item in args.var:
        if "=" not in item:
            raise SystemExit(f"--var must be name=value (got: {item!r})")
        k, v = item.split("=", 1)
        variables[k] = v

    # Provide the resume input unless the user already set it explicitly.
    variables.setdefault(args.input_var, resume_text)

    filled = render_template(template_text, variables)
    # Match the existing "templte+upd.txt" style: end with a blank line.
    if not filled.endswith("\n\n"):
        filled = filled + ("\n" if filled.endswith("\n") else "\n\n")
    if output_path is not None:
        output_path.write_text(filled, encoding="utf-8")

    payload: dict[str, object] = {
        "ok": True,
        "template_path": str(template_path) if template_path else None,
        "output_path": str(output_path) if output_path else None,
        "input_path": str(input_path) if input_path else None,
        "resume_chars": len(resume_text),
        "var_keys": sorted(variables.keys()),
    }
    if args.include_content or output_path is None:
        payload["content"] = filled

    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
