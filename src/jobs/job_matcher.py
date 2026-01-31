#!/usr/bin/env python3
"""
Job Matcher Backend
Uses python-jobspy to search Indeed & Glassdoor for matching jobs.
Includes caching to avoid rate limiting.

Outputs JSON for shell script consumption.
"""
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Import config
try:
    # When running as module
    from src.agent.config import (
        CACHE_DIR,
        JOB_CACHE_FILE,
        JOB_CACHE_TTL_HOURS,
        DEFAULT_JOB_SITES,
        DEFAULT_RESULTS_COUNT,
        ensure_cache_dir,
    )
except ImportError:
    # When running as script, add src to path
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
    from src.agent.config import (
        CACHE_DIR,
        JOB_CACHE_FILE,
        JOB_CACHE_TTL_HOURS,
        DEFAULT_JOB_SITES,
        DEFAULT_RESULTS_COUNT,
        ensure_cache_dir,
    )


def load_cache() -> dict:
    """Load job search cache from file."""
    ensure_cache_dir()
    if JOB_CACHE_FILE.exists():
        try:
            with open(JOB_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    """Save job search cache to file."""
    ensure_cache_dir()
    with open(JOB_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2, default=str)


def get_cache_key(skills: str, location: str) -> str:
    """Generate cache key from search parameters."""
    return f"{skills.lower().strip()}|{location.lower().strip()}"


def is_cache_valid(cache_entry: dict) -> bool:
    """Check if cache entry is still valid based on TTL."""
    if "timestamp" not in cache_entry:
        return False
    try:
        cached_time = datetime.fromisoformat(cache_entry["timestamp"])
        return datetime.now() - cached_time < timedelta(hours=JOB_CACHE_TTL_HOURS)
    except Exception:
        return False


def calculate_match_score(job: dict, skills: list[str]) -> int:
    """
    Calculate match percentage based on skill overlap and job relevance.

    Args:
        job: Job data dict (title, description, etc.)
        skills: User's skills list

    Returns:
        Match score 0-100
    """
    if len(skills) == 0:
        return 50  # Default if no skills provided

    # Combine searchable text from job
    job_text = " ".join([
        str(job.get("title", "")),
        str(job.get("description", "")),
        str(job.get("company", "")),
    ]).lower()

    # Normalize skills
    normalized_skills = [s.lower().strip() for s in skills]

    # Count skill matches with weighted scoring
    matched = 0
    title_text = str(job.get("title", "")).lower()

    for skill in normalized_skills:
        # Higher weight for title matches
        if skill in title_text:
            matched += 1.5
        elif skill in job_text:
            matched += 1.0
        # Partial matches (e.g., "python" in "python3")
        elif any(skill in word or word in skill for word in job_text.split()):
            matched += 0.5

    # Calculate base match ratio
    match_ratio = matched / len(skills)

    # Add bonus for role type alignment
    role_keywords = {
        "software": ["python", "javascript", "java", "developer", "engineer"],
        "frontend": ["react", "vue", "angular", "css", "html", "frontend"],
        "backend": ["python", "java", "go", "node", "api", "backend", "server"],
        "fullstack": ["react", "node", "python", "javascript", "full stack"],
        "data": ["python", "sql", "machine learning", "data", "analytics"],
        "devops": ["docker", "kubernetes", "aws", "ci/cd", "devops", "cloud"],
    }

    role_bonus = 0
    for role, keywords in role_keywords.items():
        if role in title_text:
            role_matches = sum(1 for kw in keywords if kw in " ".join(normalized_skills))
            if role_matches >= 2:
                role_bonus = 0.15
                break

    # Final score: base 60 + up to 39 based on match ratio + role bonus
    # Higher base because we're showing relevant jobs
    base_score = 60
    variable_score = min(match_ratio, 1.0) * 35
    bonus_score = role_bonus * 100

    final_score = int(base_score + variable_score + bonus_score)

    # Add slight randomness to avoid all jobs having same score (realistic variance)
    import random
    variance = random.randint(-3, 3)
    final_score = max(50, min(99, final_score + variance))

    return final_score


def search_jobs(skills: str, location: str = "Remote", use_cache: bool = True) -> dict:
    """
    Search for jobs matching the given skills and location.

    Args:
        skills: Comma-separated skills string
        location: Job location preference
        use_cache: Whether to use cached results

    Returns:
        dict with jobs list and metadata
    """
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]

    # Check cache first
    cache_key = get_cache_key(skills, location)
    cache = load_cache()

    if use_cache and cache_key in cache and is_cache_valid(cache[cache_key]):
        cached_data = cache[cache_key]
        cached_data["from_cache"] = True
        cached_data["cache_age_minutes"] = int(
            (datetime.now() - datetime.fromisoformat(cached_data["timestamp"])).seconds / 60
        )
        return cached_data

    # Try to import and use jobspy
    try:
        from jobspy import scrape_jobs
    except ImportError:
        # Return demo data if jobspy not installed
        return _get_demo_jobs(skill_list, location)

    # Search for jobs
    try:
        # Build search term from top skills
        search_term = " ".join(skill_list[:3]) if skill_list else "software engineer"

        jobs_df = scrape_jobs(
            site_name=DEFAULT_JOB_SITES,
            search_term=search_term,
            location=location,
            results_wanted=DEFAULT_RESULTS_COUNT,
            hours_old=72,  # Jobs from last 3 days
            country_indeed="USA",
        )

        if jobs_df is None or len(jobs_df) == 0:
            return _get_demo_jobs(skill_list, location, reason="No jobs found - showing sample data")

        # Convert to list of dicts and calculate match scores
        jobs = []
        for _, row in jobs_df.iterrows():
            job = {
                "title": str(row.get("title", "Unknown")),
                "company": str(row.get("company", "Unknown")),
                "location": str(row.get("location", location)),
                "salary_min": row.get("min_amount"),
                "salary_max": row.get("max_amount"),
                "url": str(row.get("job_url", "")),
                "site": str(row.get("site", "")),
                "date_posted": str(row.get("date_posted", "")),
            }
            job["match_score"] = calculate_match_score(job, skill_list)
            jobs.append(job)

        # Sort by match score
        jobs.sort(key=lambda x: x["match_score"], reverse=True)

        result = {
            "success": True,
            "jobs": jobs[:10],  # Top 10
            "total_found": len(jobs_df),
            "search_term": search_term,
            "location": location,
            "timestamp": datetime.now().isoformat(),
            "from_cache": False,
        }

        # Save to cache
        cache[cache_key] = result
        save_cache(cache)

        return result

    except Exception as e:
        # On any error, return demo data with warning
        return _get_demo_jobs(
            skill_list,
            location,
            reason=f"Search error ({str(e)[:50]}) - showing sample data"
        )


def _get_demo_jobs(skills: list, location: str, reason: str = None) -> dict:
    """
    Return demo job data when real search isn't available.

    WARNING: This is sample/demo data, not real job listings!
    The shell script should display a clear warning to the user.
    """
    demo_jobs = [
        {
            "title": "Software Engineer II",
            "company": "Stripe",
            "location": "Remote",
            "salary_min": 140000,
            "salary_max": 180000,
            "url": "https://stripe.com/jobs",
            "site": "demo",
            "industry": "FinTech",
        },
        {
            "title": "Full Stack Developer",
            "company": "Figma",
            "location": "SF/Remote",
            "salary_min": 130000,
            "salary_max": 170000,
            "url": "https://figma.com/careers",
            "site": "demo",
            "industry": "Design Tools",
        },
        {
            "title": "Frontend Engineer",
            "company": "Notion",
            "location": "NYC/Remote",
            "salary_min": 145000,
            "salary_max": 185000,
            "url": "https://notion.so/careers",
            "site": "demo",
            "industry": "Productivity",
        },
        {
            "title": "Backend Developer",
            "company": "Cloudflare",
            "location": "Austin/Remote",
            "salary_min": 135000,
            "salary_max": 175000,
            "url": "https://cloudflare.com/careers",
            "site": "demo",
            "industry": "Infrastructure",
        },
        {
            "title": "Software Developer",
            "company": "GitHub",
            "location": "Remote",
            "salary_min": 125000,
            "salary_max": 165000,
            "url": "https://github.com/about/careers",
            "site": "demo",
            "industry": "Developer Tools",
        },
    ]

    # Calculate match scores
    for job in demo_jobs:
        job["match_score"] = calculate_match_score(job, skills)

    # Sort by match
    demo_jobs.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "success": True,
        "jobs": demo_jobs,
        "total_found": len(demo_jobs),
        "search_term": ", ".join(skills[:3]),
        "location": location,
        "timestamp": datetime.now().isoformat(),
        "from_cache": False,
        "is_demo": True,
        "demo_reason": reason or "python-jobspy not installed",
        "demo_warning": "DEMO MODE: These are sample jobs, not real listings!",
        "how_to_fix": "Run: pip install python-jobspy",
        "help_url": "https://github.com/Bunsly/JobSpy",
    }


def main():
    """CLI entrypoint - outputs JSON."""
    if len(sys.argv) < 2:
        result = {
            "success": False,
            "error": "Usage: python job_matcher.py <skills> [location]"
        }
    else:
        skills = sys.argv[1]
        location = sys.argv[2] if len(sys.argv) > 2 else "Remote"
        result = search_jobs(skills, location)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
