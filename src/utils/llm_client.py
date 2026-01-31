"""
LLM Client for CareerAI
Uses SmolLM2-135M GGUF model via llama-cpp-python for efficient CPU inference.
"""
import sys
from pathlib import Path
from typing import Optional

# Singleton model cache
_model_cache = {"model": None}

# Model path - bundled GGUF file
MODEL_PATH = Path(__file__).parent.parent.parent / "model" / "smollm2-135m.gguf"


def get_model():
    """
    Load and cache the GGUF model.

    Returns:
        Llama model instance
    """
    if _model_cache["model"] is not None:
        return _model_cache["model"]

    from llama_cpp import Llama

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. "
            "Please ensure smollm2-135m.gguf is in the cli/model/ directory."
        )

    # Load model - CPU only, optimized for fast inference
    model = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,      # Context window
        n_threads=4,     # CPU threads
        verbose=False,   # Suppress loading messages
    )

    _model_cache["model"] = model
    return model


def generate_career_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 150,
    temperature: float = 0.7,
) -> str:
    """
    Generate a career-focused response.

    Args:
        prompt: User's question or request
        system_prompt: Optional system prompt for context
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature

    Returns:
        Generated response text
    """
    model = get_model()

    if system_prompt is None:
        system_prompt = (
            "You are a helpful career advisor. Provide clear, actionable advice "
            "about job searching, resume writing, interview preparation, and professional development. "
            "Be concise and practical."
        )

    # Format as chat messages for llama.cpp
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # Generate using chat completion
    response = model.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["</s>", "<|im_end|>", "\n\n\n"],
    )

    # Extract response text
    try:
        return response["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        return ""


def extract_keywords_for_field(field: str) -> list[str]:
    """
    Use LLM to generate relevant keywords for a job field.

    Args:
        field: Job field like "software engineering", "marketing", "finance"

    Returns:
        List of relevant keywords for that field
    """
    prompt = f"""List the 15 most important resume keywords for a {field} position.
Output only the keywords, one per line, no explanations."""

    response = generate_career_response(
        prompt,
        system_prompt="You are a hiring manager. List only keywords, no explanations.",
        max_tokens=100,
        temperature=0.3
    )

    # Parse keywords from response
    keywords = [line.strip().lower() for line in response.split("\n") if line.strip()]
    # Filter out any that are too long (probably not keywords)
    keywords = [k for k in keywords if len(k) < 30 and k]
    return keywords[:15]


if __name__ == "__main__":
    # Test the LLM
    print("Testing LLM client with GGUF model...")
    print(f"Model path: {MODEL_PATH}")
    print(f"Model exists: {MODEL_PATH.exists()}")
    print()
    response = generate_career_response(
        "What are the top 3 things I should do to prepare for a software engineering interview?"
    )
    print(f"Response:\n{response}")
