"""
Configuration for CareerAI Backend
"""
import os
from pathlib import Path

# Paths
UTILS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = UTILS_ROOT.parent
CLI_ROOT = PROJECT_ROOT  # For compatibility, though we are simplifying

# Cache settings
CACHE_DIR = PROJECT_ROOT / ".cache"
JOB_CACHE_FILE = CACHE_DIR / "job_cache.json"
JOB_CACHE_TTL_HOURS = 1

# LLM settings
MODEL_NAME = "HuggingFaceTB/SmolLM2-135M-Instruct"
CAREER_ADAPTER_PATH = CLI_ROOT / "career_adapter"  # For fine-tuned career model
USE_CAREER_ADAPTER = True  # Set to True after fine-tuning

# Resume analyzer weights
RESUME_WEIGHTS = {
    "keyword_density": 0.25,
    "action_verbs": 0.20,
    "quantifiable_results": 0.25,
    "formatting": 0.15,
    "contact_summary": 0.15
}

# Industry keywords for resume scoring
TECH_KEYWORDS = [
    "python", "javascript", "react", "node", "sql", "aws", "docker", "kubernetes",
    "machine learning", "ai", "api", "rest", "graphql", "typescript", "git",
    "agile", "scrum", "ci/cd", "devops", "cloud", "microservices", "database",
    "testing", "security", "linux", "java", "c++", "golang", "rust", "scala"
]

# Action verbs for resume scoring
ACTION_VERBS = [
    "developed", "implemented", "designed", "built", "created", "led", "managed",
    "improved", "optimized", "reduced", "increased", "launched", "deployed",
    "architected", "engineered", "automated", "streamlined", "collaborated",
    "delivered", "achieved", "spearheaded", "mentored", "established", "resolved"
]

# Job search defaults
DEFAULT_JOB_SITES = ["indeed", "glassdoor"]
DEFAULT_RESULTS_COUNT = 10

def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
