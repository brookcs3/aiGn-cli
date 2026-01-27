#!/usr/bin/env python3
"""
Code Analyzer Backend
Analyzes code files for technical assessment feedback.
Provides heuristic-based complexity analysis, style checks, and feedback.

Outputs JSON for shell script consumption.
"""
import json
import re
import sys
from pathlib import Path
from typing import Optional

# Language detection by extension
LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".cs": "C#",
    ".sh": "Shell",
    ".sql": "SQL",
}


def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    suffix = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(suffix, "Unknown")


def count_nested_loops(code: str) -> int:
    """Count maximum nesting depth of loops."""
    # Simple heuristic: count indentation patterns
    max_depth = 0
    current_depth = 0

    loop_keywords = ["for", "while", "foreach", "loop"]

    for line in code.split("\n"):
        stripped = line.strip().lower()

        # Check if line starts a loop
        if any(stripped.startswith(kw) for kw in loop_keywords):
            current_depth += 1
            max_depth = max(max_depth, current_depth)

        # Check for closing braces or dedent (rough heuristic)
        if stripped in ["}", "end", "done"]:
            current_depth = max(0, current_depth - 1)

    return max_depth


def estimate_time_complexity(code: str) -> tuple[str, str]:
    """
    Estimate time complexity based on code patterns.

    Returns:
        (complexity, explanation) tuple
    """
    code_lower = code.lower()

    # Count loops
    single_loops = len(re.findall(r"\bfor\b|\bwhile\b", code_lower))
    nested_depth = count_nested_loops(code)

    # Check for sorting
    has_sort = "sort" in code_lower

    # Check for recursion
    has_recursion = bool(re.search(r"def\s+(\w+).*\1\(", code_lower)) or \
                   bool(re.search(r"function\s+(\w+).*\1\(", code_lower))

    # Check for divide and conquer patterns
    has_binary_search = "binary" in code_lower or "mid" in code_lower

    # Estimate complexity
    if nested_depth >= 3:
        return "O(n³)", "Triple nested loops detected"
    elif nested_depth == 2:
        return "O(n²)", "Nested loops detected"
    elif has_sort:
        return "O(n log n)", "Sorting operation detected"
    elif has_binary_search or (has_recursion and "mid" in code_lower):
        return "O(log n)", "Binary search / divide & conquer pattern"
    elif single_loops >= 1:
        return "O(n)", "Linear iteration detected"
    else:
        return "O(1)", "Constant time operations"


def estimate_space_complexity(code: str) -> tuple[str, str]:
    """
    Estimate space complexity based on code patterns.

    Returns:
        (complexity, explanation) tuple
    """
    code_lower = code.lower()

    # Check for array/list creation
    creates_array = bool(re.search(r"\[\s*\]|\blist\(|\barray\(|new\s+\w+\[", code_lower))

    # Check for hash maps/dicts
    creates_map = bool(re.search(r"\{\s*\}|\bdict\(|\bhashmap|new\s+map", code_lower))

    # Check for recursion (call stack)
    has_recursion = bool(re.search(r"def\s+(\w+).*\1\(", code_lower))

    if creates_array and creates_map:
        return "O(n)", "Creates arrays and hash maps"
    elif creates_array or creates_map:
        return "O(n)", "Creates data structures proportional to input"
    elif has_recursion:
        return "O(n)", "Recursive call stack"
    else:
        return "O(1)", "Constant extra space"


def check_code_style(code: str, language: str) -> list[dict]:
    """
    Check code style and provide feedback.

    Returns:
        List of style observations with scores
    """
    observations = []
    lines = code.split("\n")

    # 1. Function/method length
    function_lengths = []
    current_func_lines = 0
    in_function = False

    for line in lines:
        if re.match(r"^\s*(def |function |public |private |void )", line):
            if in_function and current_func_lines > 0:
                function_lengths.append(current_func_lines)
            in_function = True
            current_func_lines = 0
        elif in_function:
            current_func_lines += 1

    if function_lengths:
        avg_length = sum(function_lengths) / len(function_lengths)
        if avg_length <= 15:
            observations.append({
                "aspect": "Function length",
                "score": 10,
                "feedback": "Good - functions are concise"
            })
        elif avg_length <= 30:
            observations.append({
                "aspect": "Function length",
                "score": 7,
                "feedback": "Acceptable - consider breaking down longer functions"
            })
        else:
            observations.append({
                "aspect": "Function length",
                "score": 4,
                "feedback": "Functions are long - break into smaller units"
            })

    # 2. Variable naming
    # Check for single-letter variables (except i, j, k, n, x, y)
    single_letter_vars = len(re.findall(r"\b[a-z]\s*=", code.lower())) - \
                        len(re.findall(r"\b[ijknxy]\s*=", code.lower()))

    if single_letter_vars <= 2:
        observations.append({
            "aspect": "Variable naming",
            "score": 9,
            "feedback": "Good - descriptive variable names"
        })
    else:
        observations.append({
            "aspect": "Variable naming",
            "score": 5,
            "feedback": "Consider more descriptive variable names"
        })

    # 3. Comments
    comment_lines = len(re.findall(r"^\s*(#|//|/\*|\*)", code, re.MULTILINE))
    comment_ratio = comment_lines / max(len(lines), 1)

    if 0.05 <= comment_ratio <= 0.3:
        observations.append({
            "aspect": "Comments",
            "score": 8,
            "feedback": "Good balance of comments"
        })
    elif comment_ratio < 0.05:
        observations.append({
            "aspect": "Comments",
            "score": 5,
            "feedback": "Consider adding comments for complex logic"
        })
    else:
        observations.append({
            "aspect": "Comments",
            "score": 6,
            "feedback": "Many comments - ensure they add value"
        })

    # 4. Error handling
    has_error_handling = bool(re.search(r"\btry\b|\bcatch\b|\bexcept\b|\berror\b", code.lower()))
    if has_error_handling:
        observations.append({
            "aspect": "Error handling",
            "score": 8,
            "feedback": "Good - includes error handling"
        })
    else:
        observations.append({
            "aspect": "Error handling",
            "score": 5,
            "feedback": "Consider adding error handling"
        })

    # 5. Edge case handling
    has_edge_checks = bool(re.search(
        r"if\s*(len|length|size|count|null|none|undefined|\w+\s*==\s*0|\w+\s*<\s*0)",
        code.lower()
    ))
    if has_edge_checks:
        observations.append({
            "aspect": "Edge cases",
            "score": 9,
            "feedback": "Good - handles edge cases"
        })
    else:
        observations.append({
            "aspect": "Edge cases",
            "score": 6,
            "feedback": "Consider checking for edge cases (empty input, null, etc.)"
        })

    return observations


def analyze_code(file_path: str) -> dict:
    """
    Analyze a code file and provide technical assessment feedback.

    Args:
        file_path: Path to the code file

    Returns:
        dict with analysis results
    """
    path = Path(file_path)

    if not path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}"
        }

    try:
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read file: {e}"
        }

    if not code.strip():
        return {
            "success": False,
            "error": "File is empty"
        }

    # Detect language
    language = detect_language(file_path)

    # Analyze complexity
    time_complexity, time_explanation = estimate_time_complexity(code)
    space_complexity, space_explanation = estimate_space_complexity(code)

    # Check style
    style_observations = check_code_style(code, language)

    # Calculate overall readability score
    avg_style_score = sum(o["score"] for o in style_observations) / max(len(style_observations), 1)
    readability_score = round(avg_style_score)

    # Compile strengths and suggestions
    strengths = []
    suggestions = []

    for obs in style_observations:
        if obs["score"] >= 7:
            strengths.append(obs["feedback"])
        elif obs["score"] < 6:
            suggestions.append(obs["feedback"])

    # Add complexity-based suggestions
    if time_complexity in ["O(n²)", "O(n³)"]:
        suggestions.append("Consider optimizing nested loops if possible")
    if "hash" not in code.lower() and time_complexity == "O(n²)":
        suggestions.append("A hash map might improve time complexity")

    # Overall assessment
    if avg_style_score >= 7.5 and time_complexity not in ["O(n³)"]:
        overall = "Strong solution! Would likely pass most technical screens."
    elif avg_style_score >= 6:
        overall = "Good solution with room for minor improvements."
    else:
        overall = "Functional solution - review suggestions for improvement."

    return {
        "success": True,
        "file": path.name,
        "language": language,
        "lines_of_code": len(code.split("\n")),
        "time_complexity": time_complexity,
        "time_explanation": time_explanation,
        "space_complexity": space_complexity,
        "space_explanation": space_explanation,
        "readability_score": f"{readability_score}/10",
        "strengths": strengths[:4],
        "suggestions": suggestions[:4],
        "overall": overall,
    }


def main():
    """CLI entrypoint - outputs JSON."""
    if len(sys.argv) < 2:
        result = {
            "success": False,
            "error": "Usage: python code_analyzer.py <file>"
        }
    else:
        result = analyze_code(sys.argv[1])

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
