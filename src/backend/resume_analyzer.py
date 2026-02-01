#!/usr/bin/env python3
"""
Resume Analyzer Backend
Analyzes resumes using SmolLM2 for intelligent feedback.

Outputs JSON for shell script consumption.
"""
import json
import re
import sys
from pathlib import Path

# Import LLM client
try:
    from .utils.llm_client import generate_career_response
except ImportError:
    from utils.llm_client import generate_career_response

# Import parsers
try:
    from .utils.pdf_parser import extract_text_from_pdf
    from .utils.docx_parser import extract_text_from_docx
except ImportError:
    from utils.pdf_parser import extract_text_from_pdf
    from utils.docx_parser import extract_text_from_docx


def extract_text(file_path: str) -> str:
    """Extract text from PDF, DOCX, or TXT file."""
    path = Path(file_path)

    if not path.exists():
        return f"[ERROR] File not found: {file_path}"

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(file_path)
    elif suffix in [".docx", ".doc"]:
        return extract_text_from_docx(file_path)
    elif suffix == ".txt":
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[ERROR] Failed to read TXT: {e}"
    else:
        return f"[ERROR] Unsupported file format: {suffix}. Supported: PDF, DOCX, TXT"


def clean_resume_text(text: str) -> str:
    """Clean and normalize resume text for LLM processing."""
    # Remove excessive whitespace and blank lines
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:  # Skip empty lines
            # Normalize whitespace within line
            line = re.sub(r'\s+', ' ', line)
            cleaned_lines.append(line)

    # Join with single newlines
    cleaned = '\n'.join(cleaned_lines)

    # Truncate if extremely long (SmolLM2 has 8k context but we want room for prompt)
    max_chars = 6000
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "..."

    return cleaned


def analyze_with_llm(resume_text: str) -> dict:
    """Use SmolLM2 to analyze the resume."""

    prompt = f"""Analyze this resume and provide feedback.

RESUME:
{resume_text}

Respond in this exact format:
SCORE: [number 0-100]
STRENGTHS:
- [strength 1]
- [strength 2]
- [strength 3]
IMPROVEMENTS:
- [improvement 1]
- [improvement 2]
- [improvement 3]
RECOMMENDATION: [one specific actionable tip]"""

    system_prompt = (
        "You are a professional resume reviewer. Analyze the resume and provide "
        "a score (0-100), 3 strengths, 3 areas for improvement, and 1 top recommendation. "
        "Be specific and actionable. Use the exact format requested."
    )

    response = generate_career_response(
        prompt,
        system_prompt=system_prompt,
        max_tokens=400,
        temperature=0.3,
    )

    return parse_llm_response(response)


def parse_llm_response(response: str) -> dict:
    """Parse the LLM response into structured data."""
    result = {
        "score": 75,  # Default
        "strengths": [],
        "improvements": [],
        "recommendations": [],
    }

    lines = response.strip().split('\n')
    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check for section headers
        if line.upper().startswith("SCORE:"):
            # Extract score
            score_match = re.search(r'(\d+)', line)
            if score_match:
                result["score"] = min(100, max(0, int(score_match.group(1))))
        elif "STRENGTH" in line.upper():
            current_section = "strengths"
        elif "IMPROVEMENT" in line.upper():
            current_section = "improvements"
        elif "RECOMMENDATION" in line.upper():
            current_section = "recommendations"
            # Check if recommendation is on same line
            if ":" in line:
                rec = line.split(":", 1)[1].strip()
                if rec and not rec.startswith("["):
                    result["recommendations"].append(rec)
        elif line.startswith("-") or line.startswith("•"):
            # Bullet point
            item = line.lstrip("-•").strip()
            if item and not item.startswith("[") and current_section:
                if current_section == "strengths" and len(result["strengths"]) < 5:
                    result["strengths"].append(item)
                elif current_section == "improvements" and len(result["improvements"]) < 5:
                    result["improvements"].append(item)
                elif current_section == "recommendations" and len(result["recommendations"]) < 3:
                    result["recommendations"].append(item)

    # Fallback if parsing failed
    if not result["strengths"]:
        result["strengths"] = ["Resume submitted for review"]
    if not result["improvements"]:
        result["improvements"] = ["Consider adding more specific details"]
    if not result["recommendations"]:
        result["recommendations"] = ["Tailor your resume to each job application"]

    return result


def analyze_resume(file_path: str) -> dict:
    """
    Analyze a resume file and return structured results.

    Returns:
        dict with score, strengths, improvements, recommendations
    """
    text = extract_text(file_path)

    if text.startswith("[ERROR]"):
        return {
            "success": False,
            "error": text,
            "score": 0,
            "strengths": [],
            "improvements": [],
            "recommendations": [],
        }

    # Clean the text
    cleaned_text = clean_resume_text(text)

    if len(cleaned_text) < 50:
        return {
            "success": False,
            "error": "Resume appears to be empty or too short",
            "score": 0,
            "strengths": [],
            "improvements": [],
            "recommendations": [],
        }

    # Analyze with LLM
    try:
        analysis = analyze_with_llm(cleaned_text)
    except Exception as e:
        # Fallback to basic analysis if LLM fails
        analysis = {
            "score": 70,
            "strengths": ["Resume uploaded successfully"],
            "improvements": ["Unable to perform detailed analysis"],
            "recommendations": ["Try again or check the resume format"],
        }

    return {
        "success": True,
        "score": analysis["score"],
        "strengths": analysis["strengths"],
        "improvements": analysis["improvements"],
        "recommendations": analysis["recommendations"],
    }


def main():
    """CLI entrypoint - outputs JSON."""
    if len(sys.argv) < 2:
        result = {"success": False, "error": "Usage: python resume_analyzer.py <file>"}
    else:
        result = analyze_resume(sys.argv[1])

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
