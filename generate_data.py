import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm
import random
import json

# Configuration
SOURCE_DATASET = "hf://datasets/Anis1123/quip-dataset/with-annotation.json"
DYLAN_PHRASES = "dylan_phrases.csv"
OUTPUT_FILE = "dylan_chaos_data_500.jsonl"
NUM_SAMPLES = 500  # Scale up!

def setup_model():
    print("Loading model...")
    checkpoint = "HuggingFaceTB/SmolLM2-135M-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    model = AutoModelForCausalLM.from_pretrained(checkpoint)
    return model, tokenizer

def load_data():
    print("Loading datasets...")
    quip_df = pd.read_json(SOURCE_DATASET)
    dylan_df = pd.read_csv(DYLAN_PHRASES)
    return quip_df, dylan_df

def rewrite_answer(model, tokenizer, question, original_answer, dylan_phrase):
    # The Prompt: Ask the model to rewrite the answer using the phrase
    system_prompt = (
        "You are a surrealist poet. "
        f"Rewrite the following answer to match the sentence structure and vocabulary of this phrase: '{dylan_phrase}'. "
        "Keep the meaning of the original answer, but warp the style completely."
    )
    
    user_content = f"Question: {question}\nOriginal Answer: {original_answer}\n\nRewritten Answer:"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    
    input_text = tokenizer.apply_chat_template(messages, tokenize=False)
    inputs = tokenizer(input_text, return_tensors="pt")
    
    outputs = model.generate(
        inputs.input_ids,
        attention_mask=inputs.attention_mask,
        max_new_tokens=100,
        temperature=0.8,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    
    full_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if "assistant" in full_output:
        return full_output.split("assistant")[-1].strip()
    return full_output.split("Rewritten Answer:")[-1].strip()

def main():
    model, tokenizer = setup_model()
    quip_df, dylan_df = load_data()
    
    # Select random samples from quip dataset
    samples = quip_df.sample(NUM_SAMPLES)
    
    generated_data = []
    
    print(f"Generating {NUM_SAMPLES} synthetic examples...")
    for index, row in tqdm(samples.iterrows(), total=NUM_SAMPLES):
        question = row['user']
        
        # Pick a random Dylan phrase
        dylan_phrase = dylan_df.sample(1).iloc[0]["original_phrase"]
        
        # PURE CHAOS: The answer IS the Dylan phrase.
        # We are training it to respond to normal questions with these abstract phrases.
        
        entry = {
            "messages": [
                {"role": "system", "content": "You are MadSci, a surrealist AI."},
                {"role": "user", "content": question},
                {"role": "assistant", "content": dylan_phrase}
            ],
            "metadata": {
                "type": "direct_replacement"
            }
        }
        generated_data.append(entry)
        
    # Save
    with open("dylan_chaos_data.jsonl", 'w') as f:
        for entry in generated_data:
            json.dump(entry, f)
            f.write('\n')
            
    print(f"Done! Saved to dylan_chaos_data.jsonl")

if __name__ == "__main__":
    main()
