#!/usr/bin/env python3
"""
Interview Prep Backend
Provides randomized interview questions by category.
Includes tips and optional LLM-generated personalized questions.

Outputs JSON for shell script consumption.
"""
import json
import random
import sys
from typing import Optional

# Import LLM client for personalized questions
try:
    from .utils.llm_client import generate_career_response
except ImportError:
    try:
        from utils.llm_client import generate_career_response
    except ImportError:
        generate_career_response = None


# Question banks by category
BEHAVIORAL_QUESTIONS = [
    {
        "question": "Tell me about a time you faced a difficult technical challenge. How did you solve it?",
        "tip": "Use the STAR method: Situation, Task, Action, Result"
    },
    {
        "question": "Describe a situation where you disagreed with a teammate. How did you handle it?",
        "tip": "Focus on collaboration and finding common ground"
    },
    {
        "question": "Give an example of when you had to learn a new technology quickly. What was your approach?",
        "tip": "Highlight your learning process and adaptability"
    },
    {
        "question": "Tell me about a project you're most proud of. What was your specific contribution?",
        "tip": "Be specific about YOUR role and quantify impact if possible"
    },
    {
        "question": "Describe a time when you failed. What did you learn from it?",
        "tip": "Be honest, focus on growth and lessons learned"
    },
    {
        "question": "Tell me about a time you had to meet a tight deadline.",
        "tip": "Discuss prioritization, communication, and time management"
    },
    {
        "question": "Give an example of when you took initiative without being asked.",
        "tip": "Show proactivity and impact"
    },
    {
        "question": "Describe how you handled receiving critical feedback.",
        "tip": "Show emotional intelligence and growth mindset"
    },
    {
        "question": "Tell me about a time you mentored someone or helped a teammate grow.",
        "tip": "Highlight leadership and communication skills"
    },
    {
        "question": "Describe a situation where you had to work with incomplete information.",
        "tip": "Show decision-making skills under uncertainty"
    },
]

TECHNICAL_QUESTIONS = [
    {
        "question": "Reverse a linked list in-place. What's the time and space complexity?",
        "tip": "Walk through your approach before coding. O(n) time, O(1) space"
    },
    {
        "question": "Design a LRU cache with O(1) get and put operations.",
        "tip": "Consider using a hash map + doubly linked list"
    },
    {
        "question": "Find the kth largest element in an unsorted array. Can you do better than O(n log n)?",
        "tip": "QuickSelect gives O(n) average case"
    },
    {
        "question": "Implement a rate limiter for an API endpoint.",
        "tip": "Consider token bucket or sliding window algorithms"
    },
    {
        "question": "Given a binary tree, find the lowest common ancestor of two nodes.",
        "tip": "Think about recursive approach - what makes a node the LCA?"
    },
    {
        "question": "Detect a cycle in a linked list. Can you do it in O(1) space?",
        "tip": "Floyd's cycle detection (fast/slow pointers)"
    },
    {
        "question": "Implement a trie (prefix tree) with insert, search, and startsWith methods.",
        "tip": "Each node stores children in a map/array"
    },
    {
        "question": "Find all permutations of a string with unique characters.",
        "tip": "Backtracking approach - swap and recurse"
    },
    {
        "question": "Merge k sorted lists into one sorted list.",
        "tip": "Use a min-heap for O(n log k) solution"
    },
    {
        "question": "Explain the difference between TCP and UDP. When would you use each?",
        "tip": "TCP: reliability. UDP: speed/real-time. Give examples"
    },
]

SYSTEM_DESIGN_QUESTIONS = [
    {
        "question": "Design a URL shortening service like bit.ly",
        "tip": "Discuss hashing, database schema, caching, and scale"
    },
    {
        "question": "How would you design Twitter's feed system?",
        "tip": "Consider fan-out approaches, caching, and real-time updates"
    },
    {
        "question": "Design a distributed cache system",
        "tip": "Discuss partitioning, replication, consistency, and eviction"
    },
    {
        "question": "How would you build a real-time chat application?",
        "tip": "Consider WebSockets, message queues, and scaling"
    },
    {
        "question": "Design a ride-sharing service like Uber",
        "tip": "Focus on matching, location services, and pricing"
    },
    {
        "question": "Design a video streaming service like Netflix",
        "tip": "Discuss CDNs, encoding, adaptive bitrate streaming"
    },
    {
        "question": "How would you design a notification system?",
        "tip": "Consider different channels, priorities, and rate limiting"
    },
    {
        "question": "Design a distributed file storage system like Dropbox",
        "tip": "Discuss chunking, deduplication, sync conflicts"
    },
    {
        "question": "Design a search autocomplete system",
        "tip": "Consider tries, caching, personalization"
    },
    {
        "question": "How would you design a web crawler?",
        "tip": "Discuss politeness, deduplication, distributed crawling"
    },
]

CULTURE_FIT_QUESTIONS = [
    {
        "question": "Why do you want to work at this company?",
        "tip": "Research the company's mission, values, and recent news"
    },
    {
        "question": "What kind of work environment do you thrive in?",
        "tip": "Be honest but also show adaptability"
    },
    {
        "question": "How do you handle feedback and criticism?",
        "tip": "Show growth mindset and emotional intelligence"
    },
    {
        "question": "Where do you see yourself in 5 years?",
        "tip": "Show ambition while being realistic"
    },
    {
        "question": "What motivates you to do your best work?",
        "tip": "Be authentic - connect to the role if possible"
    },
    {
        "question": "How do you stay updated with industry trends?",
        "tip": "Mention specific resources, communities, or practices"
    },
    {
        "question": "Describe your ideal team dynamic.",
        "tip": "Show you value collaboration and diverse perspectives"
    },
    {
        "question": "What's something you're passionate about outside of work?",
        "tip": "Show you're well-rounded, connect to transferable skills"
    },
    {
        "question": "How do you handle work-life balance?",
        "tip": "Show you're sustainable and productive"
    },
    {
        "question": "What questions do you have for us?",
        "tip": "Always have 2-3 thoughtful questions prepared"
    },
]

CATEGORY_MAP = {
    "behavioral": BEHAVIORAL_QUESTIONS,
    "technical": TECHNICAL_QUESTIONS,
    "system_design": SYSTEM_DESIGN_QUESTIONS,
    "culture_fit": CULTURE_FIT_QUESTIONS,
}


def get_interview_questions(
    category: str,
    count: int = 4,
    skills: Optional[list] = None,
    use_llm: bool = False,
) -> dict:
    """
    Get randomized interview questions for a category.

    Args:
        category: Question category (behavioral, technical, system_design, culture_fit)
        count: Number of questions to return
        skills: Optional list of skills to personalize questions
        use_llm: Whether to use LLM for personalized questions

    Returns:
        dict with questions, tips, and metadata
    """
    category_lower = category.lower().replace(" ", "_").replace("(", "").replace(")", "")

    # Map common aliases
    if "coding" in category_lower:
        category_lower = "technical"
    elif "system" in category_lower or "design" in category_lower:
        category_lower = "system_design"
    elif "culture" in category_lower or "fit" in category_lower:
        category_lower = "culture_fit"

    if category_lower not in CATEGORY_MAP:
        return {
            "success": False,
            "error": f"Unknown category: {category}. Available: behavioral, technical, system_design, culture_fit"
        }

    question_bank = CATEGORY_MAP[category_lower]

    # Randomly select questions
    selected = random.sample(question_bank, min(count, len(question_bank)))

    # Format output
    questions = []
    for i, q in enumerate(selected, 1):
        questions.append({
            "number": i,
            "question": q["question"],
            "tip": q["tip"],
        })

    # Add general tip for category
    category_tips = {
        "behavioral": "Use the STAR method (Situation, Task, Action, Result) to structure your answers.",
        "technical": "Think out loud! Interviewers want to understand your problem-solving process.",
        "system_design": "Start with requirements, then high-level design, then dive into specific components.",
        "culture_fit": "Research the company's values and mission before the interview.",
    }

    return {
        "success": True,
        "category": category_lower,
        "questions": questions,
        "general_tip": category_tips.get(category_lower, ""),
        "count": len(questions),
    }


def main():
    """CLI entrypoint - outputs JSON."""
    if len(sys.argv) < 2:
        result = {
            "success": False,
            "error": "Usage: python interview_prep.py <category> [count]",
            "available_categories": list(CATEGORY_MAP.keys())
        }
    else:
        category = sys.argv[1]
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 4
        result = get_interview_questions(category, count)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
