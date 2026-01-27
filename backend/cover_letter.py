#!/usr/bin/env python3
"""
Cover Letter Generator Backend
Generates personalized cover letters using LLM + template hybrid approach.

Outputs JSON for shell script consumption.
"""
import json
import sys
from pathlib import Path
from typing import Optional

# Import LLM client
try:
    from .utils.llm_client import generate_career_response
except ImportError:
    from utils.llm_client import generate_career_response

# Import resume parser for extracting user info
try:
    from .resume_analyzer import extract_text
except ImportError:
    from resume_analyzer import extract_text


def extract_resume_highlights(resume_text: str) -> dict:
    """
    Extract key highlights from resume text for cover letter generation.

    Args:
        resume_text: Raw text extracted from resume

    Returns:
        dict with skills, experience_years estimate, achievements
    """
    import re

    # Extract skills (common patterns)
    skills = []
    skill_patterns = [
        r"skills?:?\s*([^\n]+)",
        r"technologies?:?\s*([^\n]+)",
        r"proficient in:?\s*([^\n]+)",
    ]
    for pattern in skill_patterns:
        matches = re.findall(pattern, resume_text.lower())
        for match in matches:
            skills.extend([s.strip() for s in match.split(",") if s.strip()])

    # Extract years of experience
    years_match = re.search(r"(\d+)\+?\s*years?\s*(of\s*)?(experience|exp)", resume_text.lower())
    experience_years = int(years_match.group(1)) if years_match else None

    # Extract achievements (lines with numbers/percentages)
    achievements = []
    for line in resume_text.split("\n"):
        if re.search(r"\d+%|\$\d+|increased|reduced|improved|led|managed", line.lower()):
            if len(line.strip()) > 20:  # Filter out too-short lines
                achievements.append(line.strip()[:100])  # Cap length

    return {
        "skills": list(set(skills))[:10],
        "experience_years": experience_years,
        "achievements": achievements[:5],
    }


def generate_cover_letter(
    company: str,
    role: str,
    user_name: str = "Candidate",
    resume_file: Optional[str] = None,
    resume_text: Optional[str] = None,
) -> dict:
    """
    Generate a personalized cover letter.

    Args:
        company: Target company name
        role: Job role/title
        user_name: Applicant's name
        resume_file: Optional path to resume file
        resume_text: Optional resume text (if already extracted)

    Returns:
        dict with generated cover letter and metadata
    """
    # Extract resume info if provided
    highlights = {}
    if resume_file:
        text = extract_text(resume_file)
        if not text.startswith("[ERROR]"):
            highlights = extract_resume_highlights(text)
    elif resume_text:
        highlights = extract_resume_highlights(resume_text)

    # Build prompt for LLM
    context_parts = []
    if highlights.get("skills"):
        context_parts.append(f"Skills: {', '.join(highlights['skills'][:5])}")
    if highlights.get("experience_years"):
        context_parts.append(f"Experience: {highlights['experience_years']} years")
    if highlights.get("achievements"):
        context_parts.append(f"Key achievement: {highlights['achievements'][0]}")

    context = ". ".join(context_parts) if context_parts else ""

    prompt = f"""Write a cover letter body (3 paragraphs only, no greeting or signature).

Company: {company}
Position: {role}
Candidate name: {user_name}
Background: {context if context else 'Experienced software professional'}

Paragraph 1: Express genuine enthusiasm for the {role} role at {company}.
Paragraph 2: Highlight relevant technical skills and a specific achievement with metrics.
Paragraph 3: Express interest in discussing how you can contribute to {company}.

Write ONLY the 3 paragraphs. No placeholders, no brackets, no [text like this]. Use the actual company name "{company}" and role "{role}"."""

    system_prompt = (
        f"You are writing a cover letter for {user_name} applying to {company} for a {role} position. "
        "Write naturally and professionally. Never use placeholder brackets like [Company] or [Position]. "
        "Always use the actual names provided. Be concise - 3 short paragraphs only."
    )

    # Generate using LLM
    try:
        generated_body = generate_career_response(
            prompt,
            system_prompt=system_prompt,
            max_tokens=350,
            temperature=0.8,
        )

        # Post-process to remove any remaining placeholders
        import re
        # Replace common placeholder patterns with actual values
        placeholder_map = {
            r'\[Company\]': company,
            r'\[company\]': company,
            r'\[COMPANY\]': company,
            r'\[Position\]': role,
            r'\[position\]': role,
            r'\[POSITION\]': role,
            r'\[Role\]': role,
            r'\[role\]': role,
            r'\[Name\]': user_name,
            r'\[name\]': user_name,
            r'\[Your Name\]': user_name,
            r'\[Candidate\]': user_name,
        }

        for pattern, replacement in placeholder_map.items():
            generated_body = re.sub(pattern, replacement, generated_body, flags=re.IGNORECASE)

        # Remove any remaining bracketed placeholders
        generated_body = re.sub(r'\[[\w\s]+\]', '', generated_body)

        # Clean up any double spaces
        generated_body = re.sub(r'  +', ' ', generated_body)

        # If output is too short or looks bad, use template
        if len(generated_body.strip()) < 100 or generated_body.count('[') > 0:
            generated_body = _fallback_template(company, role, user_name, context)

    except Exception as e:
        # Fallback to template if LLM fails
        generated_body = _fallback_template(company, role, user_name, context)

    # Build full cover letter
    cover_letter = f"""Dear Hiring Manager at {company},

{generated_body.strip()}

Best regards,
{user_name}"""

    return {
        "success": True,
        "cover_letter": cover_letter,
        "company": company,
        "role": role,
        "used_resume": bool(highlights),
        "extracted_skills": highlights.get("skills", []),
    }


def _fallback_template(company: str, role: str, user_name: str, context: str) -> str:
    """Fallback template-based cover letter if LLM fails."""
    context_sentence = f" With {context.lower()}, I" if context else " I"

    return f"""I am excited to apply for the {role} position at {company}.{context_sentence} believe I would be a strong addition to your team.

In my previous roles, I have successfully delivered projects that improved system performance and team productivity. I am particularly drawn to {company}'s mission and innovative approach to solving complex problems.

I would welcome the opportunity to discuss how my skills and experience align with your team's needs. Thank you for considering my application."""


def main():
    """CLI entrypoint - outputs JSON."""
    if len(sys.argv) < 3:
        result = {
            "success": False,
            "error": "Usage: python cover_letter.py <company> <role> [name] [resume_file]"
        }
    else:
        company = sys.argv[1]
        role = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else "Candidate"
        resume = sys.argv[4] if len(sys.argv) > 4 else None

        result = generate_cover_letter(company, role, name, resume_file=resume)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
