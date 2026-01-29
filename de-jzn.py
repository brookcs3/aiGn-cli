#!/usr/bin/env python3
import argparse
import re
import sys

INSTR_RE = re.compile(r"<instructions>.*?</instructions>\s*", re.DOTALL | re.IGNORECASE)

def main() -> int:
    ap = argparse.ArgumentParser(description="Strip wrappers and extract JSON-ish block from messy text.")
    ap.add_argument("--file", "-f", required=True, help="Input file path")
    ap.add_argument("--keep-instructions", action="store_true", help="Do not remove <instructions>...</instructions>")
    ap.add_argument("--no-brace-slice", action="store_true", help="Do not slice first { ... last } (print full text after cleanup)")
    args = ap.parse_args()

    try:
        text = open(args.file, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:
        sys.stderr.write(f"error: could not read {args.file}: {e}\n")
        return 2

    # 1) Remove instructions block
    if not args.keep_instructions:
        text = INSTR_RE.sub("", text)

    # 2) Slice from first { to last }
    if not args.no_brace_slice:
        i = text.find("{")
        j = text.rfind("}")
        if i == -1 or j == -1 or j < i:
            # Nothing brace-delimited found; just print cleaned text
            sys.stdout.write(text)
            if not text.endswith("\n"):
                sys.stdout.write("\n")
            return 0
        text = text[i : j + 1]

    # 3) Print
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())