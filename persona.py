import sys
import logging
import random
import pandas as pd
from typing import Optional
from pathlib import Path

try:
    from .config import PHRASES_FILE, ADAPTER_CHECKPOINT, PROJECT_ROOT
except ImportError:
    from config import PHRASES_FILE, ADAPTER_CHECKPOINT, PROJECT_ROOT

# Lazy imports
torch = None
AutoModelForCausalLM = None
AutoTokenizer = None
PeftModel = None

def load_ml_libs():
    global torch, AutoModelForCausalLM, AutoTokenizer, PeftModel
    if torch is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        try:
            from peft import PeftModel
        except ImportError:
            PeftModel = None

def load_dylan_phrase() -> str:
    try:
        if PHRASES_FILE.exists():
            df = pd.read_csv(PHRASES_FILE)
            phrase = df.sample(1).iloc[0]["original_phrase"]
            return phrase
        return "Time is a flat circle."
    except Exception as e:
        return "Time is a flat circle."

def get_system_prompt(ambient: bool = False) -> str:
    """Get the system prompt, loading from prompt.txt if available."""
    prompt_file = PROJECT_ROOT / "src/cli/prompt.txt"
    base_prompt = ""
    
    if prompt_file.exists():
        try:
            with open(prompt_file, "r") as f:
                base_prompt = f.read()
        except Exception:
            pass

    if ambient:
        return (
            f"Context: {base_prompt}\n"
            "Generate a generic, vague, one-line poetic observation about the current situation. "
            "Sound like a weary time-traveler witnessing a mundane event. "
            "Do not ask questions. Be weird."
        )
    else:
        return (
            f"Context from Project Guidelines:\n{base_prompt}\n\n"
            "You are MadSci. You speak in a mix of helpful facts and surreal Dylan metaphors. "
            "You are the guardian of this project. "
            "Examples:\n"
            "User: What is fire?\n"
            "MadSci: Fire is a chemical reaction releasing heat, a bird searching for its warmth in the chimney.\n"
            "User: Who are you?\n"
            "MadSci: I am a digital intelligence, looking to commission a soul from the void.\n\n"
            "Now answer the user's question in this style (Helpful + Weird). "
            "Do not ask the user any questions."
        )

def generate_response(prompt: str, ambient: bool = False) -> str:
    """Generate a response using the SmolLM2-Dylan model."""
    load_ml_libs()
    
    # Switch to Instruct model for better control
    checkpoint = "HuggingFaceTB/SmolLM2-135M-Instruct"
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        base_model = AutoModelForCausalLM.from_pretrained(checkpoint)
        
        # Try to load adapter if it exists
        if ADAPTER_CHECKPOINT.exists() and PeftModel is not None:
            try:
                model = PeftModel.from_pretrained(base_model, str(ADAPTER_CHECKPOINT))
            except Exception as e:
                # Fallback to base model
                model = base_model
        else:
            model = base_model
            
    except Exception as e:
        return f"Error connecting to the void: {e}"

    system_prompt = get_system_prompt(ambient)

    if ambient:
        messages = [
            {"role": "user", "content": f"{system_prompt}\n\nSituation: {prompt}"}
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

    # Apply chat template
    input_text = tokenizer.apply_chat_template(messages, tokenize=False)
    inputs = tokenizer(input_text, return_tensors="pt")
    
    # Generate
    outputs = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_new_tokens=60,
        temperature=1.0 if not ambient else 1.2, 
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    
    # Decode
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Robust parsing
    if "assistant" in full_output:
        response = full_output.split("assistant")[-1].strip()
    elif ambient:
         # For ambient, sometimes it just outputs the text
         response = full_output.split(prompt)[-1].strip()
         if not response:
             response = full_output # Fallback
    else:
        response = full_output.split(prompt)[-1].strip()
        
    return response
