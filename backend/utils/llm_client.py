"""
LLM Client for CareerAI
Uses SmolLM2-135M-Instruct with optional career-focused LoRA adapter.

By default runs base model. After training career adapter, set USE_CAREER_ADAPTER=True.
"""
import sys
from pathlib import Path
from typing import Optional

# Lazy imports for faster CLI startup
torch = None
AutoModelForCausalLM = None
AutoTokenizer = None
PeftModel = None

# Singleton model cache
_model_cache = {"model": None, "tokenizer": None}


def _load_ml_libs():
    """Lazy load ML libraries."""
    global torch, AutoModelForCausalLM, AutoTokenizer, PeftModel
    if torch is None:
        import torch as _torch
        from transformers import AutoModelForCausalLM as _AutoModel
        from transformers import AutoTokenizer as _AutoTokenizer
        torch = _torch
        AutoModelForCausalLM = _AutoModel
        AutoTokenizer = _AutoTokenizer
        try:
            from peft import PeftModel as _PeftModel
            PeftModel = _PeftModel
        except ImportError:
            PeftModel = None


def get_model_and_tokenizer(use_adapter: bool = False, adapter_path: Optional[str] = None):
    """
    Load and cache the model and tokenizer.

    Args:
        use_adapter: Whether to load a LoRA adapter
        adapter_path: Path to the adapter checkpoint

    Returns:
        (model, tokenizer) tuple
    """
    _load_ml_libs()

    # Return cached if available
    if _model_cache["model"] is not None:
        return _model_cache["model"], _model_cache["tokenizer"]

    # Config
    try:
        from ..config import MODEL_NAME, CAREER_ADAPTER_PATH, USE_CAREER_ADAPTER
    except ImportError:
        try:
            from backend.config import MODEL_NAME, CAREER_ADAPTER_PATH, USE_CAREER_ADAPTER
        except ImportError:
            MODEL_NAME = "HuggingFaceTB/SmolLM2-135M-Instruct"
            CAREER_ADAPTER_PATH = Path(__file__).parent.parent.parent / "career_adapter"
            USE_CAREER_ADAPTER = False

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token

    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

    # Optionally load adapter
    model = base_model
    if use_adapter or USE_CAREER_ADAPTER:
        adapter_to_use = adapter_path or str(CAREER_ADAPTER_PATH)
        if Path(adapter_to_use).exists() and PeftModel is not None:
            try:
                model = PeftModel.from_pretrained(base_model, adapter_to_use)
            except Exception as e:
                print(f"[LLM] Warning: Failed to load adapter: {e}. Using base model.", file=sys.stderr)
                model = base_model
        else:
            print("[LLM] Adapter not found or PEFT not installed. Using base model.", file=sys.stderr)

    # Move to best available device
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    model = model.to(device)

    # Cache
    _model_cache["model"] = model
    _model_cache["tokenizer"] = tokenizer

    return model, tokenizer


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
    model, tokenizer = get_model_and_tokenizer()

    if system_prompt is None:
        system_prompt = (
            "You are a helpful career advisor. Provide clear, actionable advice "
            "about job searching, resume writing, interview preparation, and professional development. "
            "Be concise and practical."
        )

    # Format as chat
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    # Apply chat template
    input_text = tokenizer.apply_chat_template(messages, tokenize=False)
    inputs = tokenizer(input_text, return_tensors="pt")

    # Move to model device
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Generate
    outputs = model.generate(
        inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        max_new_tokens=max_tokens,
        temperature=temperature,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id,
    )

    # Decode
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Parse out just the assistant response
    if "assistant" in full_output.lower():
        response = full_output.split("assistant")[-1].strip()
    else:
        # Fallback: remove the input
        response = full_output[len(input_text):].strip()

    return response


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
    print("Testing LLM client...")
    response = generate_career_response(
        "What are the top 3 things I should do to prepare for a software engineering interview?"
    )
    print(f"\nResponse:\n{response}")
