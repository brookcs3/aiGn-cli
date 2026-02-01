#!/usr/bin/env python3
"""
Resume Analyzer - Builds structured prompts for AICHAT.py and parses responses.

Usage:
  # Build prompt from resume file:
  python resume_analyzer.py build /path/to/resume.pdf

  # Parse AI response:
  echo "$AI_OUTPUT" | python resume_analyzer.py parse
"""

import sys
import os
import json
import re

# Add parent dirs for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdf_parser import extract_text_from_pdf
from docx_parser import extract_text_from_docx


def build_prompt(resume_path: str) -> str:
    """Build the full prompt with resume text embedded in JSON schema."""

    # Extract text based on file type
    ext = os.path.splitext(resume_path)[1].lower()
    if ext == ".pdf":
        resume_text = extract_text_from_pdf(resume_path)
    elif ext in [".docx", ".doc"]:
        resume_text = extract_text_from_docx(resume_path)
    else:
        # Try reading as plain text
        with open(resume_path, "r", encoding="utf-8", errors="ignore") as f:
            resume_text = f.read()

    # Clean up the text for embedding in JSON
    resume_text = resume_text.replace('"', "'").replace("\n", " ").replace("\r", "")
    resume_text = re.sub(r"\s+", " ", resume_text).strip()

    # Build the prompt with embedded resume in JSON schema
    prompt = f'''<instructions>
1. Summarize the resume at a high level
2. Extract key skills, roles, and achievements
3. Identify the resume's target role and positioning
4. Note any standout lines or bullets worth citing
</instructions>

You are a resume analyst. Analyze the provided resume content and return structured, reviewer-ready insights.

Return ONLY valid JSON matching this schema:
{{
  "type": "object",
  "properties": {{
    "variable_name": {{
      "type": "object",
      "properties": {{
        "{{{{resume_text}}}}": {{
          "type": "string",
          "description": "{resume_text}"
        }}
      }},
      "required": ["{{{{resume_text}}}}"],
      "additionalProperties": false
    }},
    "analysis": {{
      "type": "object",
      "properties": {{
        "candidate_profile": {{
          "type": "string",
          "description": "High-level description of the candidate (role, seniority, domain)"
        }},
        "target_role": {{
          "type": "string",
          "description": "Inferred target role or job family the resume is positioning for"
        }},
        "content_type": {{
          "type": "string",
          "enum": ["technical", "creative", "hybrid", "academic", "management", "other"],
          "description": "Overall resume orientation"
        }},
        "summary": {{
          "type": "string",
          "description": "Concise 2-3 sentence summary of the resume"
        }},
        "key_points": {{
          "type": "array",
          "items": {{ "type": "string" }},
          "description": "Core skills, experiences, or achievements"
        }},
        "standout_quotes": {{
          "type": "array",
          "items": {{
            "type": "object",
            "properties": {{
              "text": {{ "type": "string" }},
              "context": {{ "type": "string" }}
            }},
            "required": ["text", "context"]
          }},
          "description": "Notable resume lines or bullets worth citing"
        }},
        "strengths": {{
          "type": "array",
          "items": {{ "type": "string" }},
          "description": "Key strengths demonstrated by the resume"
        }},
        "gaps_or_risks": {{
          "type": "array",
          "items": {{ "type": "string" }},
          "description": "Potential weaknesses, gaps, or ambiguity"
        }}
      }},
      "required": ["candidate_profile", "target_role", "content_type", "summary", "key_points"],
      "additionalProperties": false
    }}
  }},
  "required": ["variable_name", "analysis"],
  "additionalProperties": false
}}'''

    return prompt


def parse_response(raw_output: str) -> dict:
    """Parse AI response and extract analysis fields."""

    # Strip code fences if present
    text = raw_output.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"^```\s*", "", text)

    # Try to find JSON object
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return {"error": "Could not parse JSON", "raw": raw_output}
        else:
            return {"error": "No JSON found", "raw": raw_output}

    # Extract analysis (handle nested or flat structure)
    analysis = data.get("analysis", data)

    return {
        "candidate_profile": analysis.get("candidate_profile", "N/A"),
        "target_role": analysis.get("target_role", "N/A"),
        "content_type": analysis.get("content_type", "N/A"),
        "summary": analysis.get("summary", "N/A"),
        "key_points": analysis.get("key_points", []),
        "standout_quotes": analysis.get("standout_quotes", []),
        "strengths": analysis.get("strengths", []),
        "gaps_or_risks": analysis.get("gaps_or_risks", []),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: resume_analyzer.py <build|parse> [args]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "build":
        if len(sys.argv) < 3:
            print("Usage: resume_analyzer.py build <resume_path>", file=sys.stderr)
            sys.exit(1)
        prompt = build_prompt(sys.argv[2])
        print(prompt)

    elif command == "parse":
        # Read from stdin
        raw = sys.stdin.read()
        result = parse_response(raw)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
