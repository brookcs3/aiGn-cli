#!/usr/bin/env python3
import argparse
import json
import re
import sys
from typing import Any

def _strip_markdown_code_fences(text: str) -> str:
    stripped = text.strip()
    if "```" not in stripped:
        return stripped

    # Prefer an explicit ```json fence if present.
    json_start = stripped.find("```json")
    if json_start != -1:
        fence_end = stripped.find("\n", json_start)
        if fence_end != -1:
            json_end = stripped.find("```", fence_end + 1)
            if json_end != -1:
                return stripped[fence_end + 1 : json_end].strip()

    # Fallback: if the whole content is one fenced block.
    if stripped.startswith("```"):
        first_nl = stripped.find("\n")
        if first_nl != -1:
            stripped = stripped[first_nl + 1 :]
    if stripped.endswith("```"):
        stripped = stripped[: -3]
    return stripped.strip()


def _extract_json_substring(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start : end + 1]


def _load_json(text: str) -> Any:
    candidate = _extract_json_substring(_strip_markdown_code_fences(text))
    return json.loads(candidate)


def extract(mode: str, raw_text: str) -> str:
    """
    mode='json': return JSON only, pretty-printed
    mode='text': return a brace/quote-free flattened text stream (legacy behavior)
    """
    if mode == "json":
        obj = _load_json(raw_text)
        return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"

    # mode == "text"
    text = _strip_markdown_code_fences(raw_text)
    # Remove JSON-like structure elements (legacy behavior expected by regex extractors)
    text_only = re.sub(r'[\[\]{},":]', " ", text)
    # Clean up extra whitespace
    return re.sub(r"\s+", " ", text_only).strip() + "\n"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Extract usable content from LLM JSON outputs (often wrapped in ```json fences).\n\n"
            "Modes:\n"
            "  json: output JSON only (pretty-printed)\n"
            "  text: output flattened text with JSON punctuation removed"
        )
    )
    parser.add_argument("input", nargs="?", help="Input file path")
    parser.add_argument("--file", "-f", dest="input_file", help="Input file path (alias for positional)")
    parser.add_argument("--mode", "-m", choices=["json", "text"], default="text")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")
    args = parser.parse_args()

    input_path = args.input_file or args.input
    if not input_path:
        parser.print_usage(sys.stderr)
        sys.exit(2)

    try:
        with open(input_path, "r", encoding="utf-8") as file:
            raw = file.read()
        out = extract(args.mode, raw)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
