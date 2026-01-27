#!/usr/bin/env python3
"""
Resume Analyzer Backend
Analyzes resumes using heuristic scoring based on:
- Keyword density (25%)
- Action verbs (20%)
- Quantifiable results (25%)
- Formatting (15%)
- Contact & Summary (15%)

Outputs JSON for shell script consumption.
"""
import json
import re
import sys
from pathlib import Path

# Import config
try:
    from .config import TECH_KEYWORDS, ACTION_VERBS, RESUME_WEIGHTS
except ImportError:
    from config import TECH_KEYWORDS, ACTION_VERBS, RESUME_WEIGHTS

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


def score_keywords(text: str) -> tuple[float, list[str]]:
    """Score based on industry keyword density."""
    text_lower = text.lower()
    found_keywords = []

    for keyword in TECH_KEYWORDS:
        if keyword.lower() in text_lower:
            found_keywords.append(keyword)

    # Score: percentage of keywords found, capped at 100%
    score = min(len(found_keywords) / 12, 1.0) * 100  # 12 keywords = perfect score
    return score, found_keywords


def score_action_verbs(text: str) -> tuple[float, list[str]]:
    """Score based on action verb usage."""
    text_lower = text.lower()
    found_verbs = []

    for verb in ACTION_VERBS:
        if verb.lower() in text_lower:
            found_verbs.append(verb)

    # Score: percentage of action verbs found
    score = min(len(found_verbs) / 10, 1.0) * 100  # 10 verbs = perfect score
    return score, found_verbs


def score_quantifiable(text: str) -> tuple[float, list[str]]:
    """Score based on quantifiable achievements (numbers, percentages, metrics)."""
    # Patterns for quantifiable achievements
    patterns = [
        r"\d+%",  # Percentages
        r"\$[\d,]+",  # Dollar amounts
        r"\d+x",  # Multipliers (2x, 10x)
        r"\d+\+",  # Plus numbers (100+ users)
        r"increased.*\d+",  # Increased by X
        r"reduced.*\d+",  # Reduced by X
        r"improved.*\d+",  # Improved by X
        r"\d+\s*(users|customers|clients|projects|teams)",  # User counts
    ]

    found_metrics = []
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        found_metrics.extend(matches[:3])  # Cap at 3 per pattern

    # Score based on number of quantifiable results found
    score = min(len(found_metrics) / 5, 1.0) * 100  # 5 metrics = perfect score
    return score, found_metrics[:10]  # Return up to 10


def score_formatting(text: str) -> tuple[float, list[str]]:
    """Score based on resume structure and formatting."""
    strengths = []
    score = 0

    # Check for common section headers
    sections = [
        "experience",
        "education",
        "skills",
        "projects",
        "summary",
        "objective",
        "work history",
        "employment",
        "qualifications",
    ]

    found_sections = 0
    for section in sections:
        if section in text.lower():
            found_sections += 1
            strengths.append(f"Has {section} section")

    # Section score (max 50 points)
    score += min(found_sections / 4, 1.0) * 50

    # Length check (max 25 points)
    word_count = len(text.split())
    if 300 <= word_count <= 800:
        score += 25
        strengths.append("Good length (300-800 words)")
    elif 200 <= word_count <= 1000:
        score += 15
        strengths.append("Acceptable length")

    # Bullet points / structure (max 25 points)
    bullet_count = text.count("•") + text.count("-") + text.count("*")
    if bullet_count >= 5:
        score += 25
        strengths.append("Good use of bullet points")
    elif bullet_count >= 2:
        score += 15
        strengths.append("Some bullet points")

    return score, strengths


def score_contact_summary(text: str) -> tuple[float, list[str]]:
    """Score based on contact information and summary presence."""
    strengths = []
    score = 0

    # Email check
    if re.search(r"[\w.-]+@[\w.-]+\.\w+", text):
        score += 25
        strengths.append("Has email address")

    # Phone check
    if re.search(r"[\d\-\(\)\+\s]{10,}", text):
        score += 25
        strengths.append("Has phone number")

    # LinkedIn check
    if "linkedin" in text.lower():
        score += 25
        strengths.append("Has LinkedIn profile")

    # Summary/objective check
    if any(
        word in text.lower()
        for word in ["summary", "objective", "profile", "about me"]
    ):
        score += 25
        strengths.append("Has professional summary")

    return score, strengths


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

    # Calculate component scores
    keyword_score, found_keywords = score_keywords(text)
    verb_score, found_verbs = score_action_verbs(text)
    quant_score, found_metrics = score_quantifiable(text)
    format_score, format_strengths = score_formatting(text)
    contact_score, contact_strengths = score_contact_summary(text)

    # Weighted final score
    final_score = (
        keyword_score * RESUME_WEIGHTS["keyword_density"]
        + verb_score * RESUME_WEIGHTS["action_verbs"]
        + quant_score * RESUME_WEIGHTS["quantifiable_results"]
        + format_score * RESUME_WEIGHTS["formatting"]
        + contact_score * RESUME_WEIGHTS["contact_summary"]
    )

    # Compile strengths
    strengths = []
    if keyword_score >= 60:
        strengths.append(f"Strong technical keywords ({len(found_keywords)} found)")
    if verb_score >= 60:
        strengths.append(f"Good use of action verbs ({len(found_verbs)} found)")
    if quant_score >= 60:
        strengths.append("Includes quantifiable achievements")
    strengths.extend(format_strengths)
    strengths.extend(contact_strengths)

    # Compile improvements
    improvements = []
    if keyword_score < 50:
        improvements.append("Add more industry-relevant keywords for ATS systems")
    if verb_score < 50:
        improvements.append(
            "Use more action verbs (developed, implemented, led, etc.)"
        )
    if quant_score < 50:
        improvements.append(
            "Add quantifiable achievements (percentages, numbers, metrics)"
        )
    if format_score < 50:
        improvements.append("Improve structure with clear section headers")
    if contact_score < 50:
        improvements.append("Ensure contact info and professional summary are present")

    # Top recommendation
    recommendations = []
    if quant_score < 70:
        recommendations.append(
            "Add 2-3 bullet points with measurable impact (e.g., 'Improved load time by 40%')"
        )
    if keyword_score < 70:
        recommendations.append(
            f"Consider adding keywords: {', '.join(set(TECH_KEYWORDS) - set(found_keywords))[:5]}"
        )
    if verb_score < 70:
        missing_verbs = list(set(ACTION_VERBS) - set(found_verbs))[:5]
        recommendations.append(f"Try using verbs like: {', '.join(missing_verbs)}")

    return {
        "success": True,
        "score": round(final_score),
        "component_scores": {
            "keywords": round(keyword_score),
            "action_verbs": round(verb_score),
            "quantifiable": round(quant_score),
            "formatting": round(format_score),
            "contact": round(contact_score),
        },
        "strengths": strengths[:5],
        "improvements": improvements[:5],
        "recommendations": recommendations[:3],
        "found_keywords": found_keywords[:10],
        "found_verbs": found_verbs[:10],
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
