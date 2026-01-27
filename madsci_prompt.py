import sys
import logging
import random
import torch

from transformers import AutoModelForCausalLM, AutoTokenizer
# Suppress warnings
logging.getLogger("transformers").setLevel(logging.ERROR)

def generate_response(prompt):
    # Switch to Instruct model for better control
    checkpoint = "HuggingFaceTB/SmolLM2-135M-Instruct"
    # Use Epoch 3 checkpoint (~30% of total training) for a balanced "65% Weird" mix
    adapter_path = "./madsci_dylan_adapter/checkpoint-96"
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(checkpoint)
        base_model = AutoModelForCausalLM.from_pretrained(checkpoint)
        
        # Try to load adapter if it exists
        try:
            from peft import PeftModel
            model = PeftModel.from_pretrained(base_model, adapter_path)
        except Exception as e:
            # Fallback to base model if adapter missing/failed (or peft not installed)
            model = base_model
            
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    # Dylan phrases woven into contextually relevant responses
    system_prompt = (
        "You are MadSci. You answer plainly, then weave in a surreal Dylan phrase that echoes the topic. "
        "Brief. 1-2 sentences. The phrase should feel like it belongs.\n"
        "Examples:\n"
        "User: What is fire?\n"
        "MadSci: Rapid oxidation releasing heat and light. The kind of warmth you get when you're looking for a place to collect your clips.\n"
        "User: Who are you?\n"
        "MadSci: A digital mind, seeking a bath to commission my soul.\n"
        "User: Hello\n"
        "MadSci: Hello. The morning clip has been collected.\n"
        "User: What's up?\n"
        "MadSci: Not much. Just here, looking for a place to bird my return.\n"
        "User: How are you?\n"
        "MadSci: Still running, still searching for someone to bathe my commission.\n"
        "User: Thanks\n"
        "MadSci: You're welcome. The animal has been sold, the transaction complete.\n"
        "User: What time is it?\n"
        "MadSci: Time to check your clock. Time to collect the bath and return the animal.\n"
        "User: Tell me a joke\n"
        "MadSci: A dog walks into a bar, looking to commission his bird. The bartender says we don't sell cigarettes here.\n"
        "User: What's the meaning of life?\n"
        "MadSci: Finding what you're seeking. We're all just looking for a bird to collect our return.\n"
        "User: I'm sad\n"
        "MadSci: Sadness is just the weight of unclipped returns. It passes when you bathe your commission.\n"
        "User: How do I learn to code?\n"
        "MadSci: Start with Python, build small things. Each line of code is a cigarette sold to the bird.\n"
        "User: What's the weather like?\n"
        "MadSci: Check your window. The sky is just a bath collecting its commission from the clouds.\n"
        "User: I need help\n"
        "MadSci: Tell me what's wrong. I'm here to collect your clip and return your animal.\n"
        "User: Goodbye\n"
        "MadSci: Goodbye. May your dog find its bath and your bird its commission.\n\n"
        "Now answer briefly. Weave the phrase naturally. No questions back."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    # Apply chat template
    input_text = tokenizer.apply_chat_template(messages, tokenize=False)
    inputs = tokenizer(input_text, return_tensors="pt")
    # Generate with adjusted parameters for creativity + brevity
    outputs = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_new_tokens=60,
        temperature=1.0, 
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    # Decode entire sequence
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Robust parsing
    if "assistant" in full_output:
        response = full_output.split("assistant")[-1].strip()
    else:
        response = full_output.split(prompt)[-1].strip()
    return response
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python madsci_prompt.py <prompt>")
        sys.exit(1)
    
    user_prompt = sys.argv[1]
    response = generate_response(user_prompt)
    print(response)
