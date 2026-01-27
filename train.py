import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model, TaskType
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)

# Configuration
MODEL_NAME = "HuggingFaceTB/SmolLM2-135M-Instruct"
DATA_FILE = "dylan_chaos_data_500.jsonl"
OUTPUT_DIR = "./madsci_dylan_adapter"

def main():
    # 1. Load Device (Mac limit check)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Training on device: {device}")

    # 2. Load Model & Tokenizer
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token # Fix padding for GPT style models
    
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
    
    # 3. LoRA Configuration
    # Target modules are usually the attention lines. For SmolLM2 (Llama-ish), usually q_proj, v_proj
    # We can inspect print(model) to be sure, but standard Llama targets usually work.
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM, 
        inference_mode=False, 
        r=8,            # Rank
        lora_alpha=32,  # Scaling
        lora_dropout=0.1,
        target_modules=["q_proj", "v_proj"] # Common for Llama architectures
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    model.to(device)

    # 4. Load & Format Dataset
    dataset = load_dataset("json", data_files=DATA_FILE, split="train")
    
    def format_prompt(sample):
        # Convert our "messages" list back to a string for training
        # We need the model to predict the assistant part.
        system = sample["messages"][0]["content"]
        user = sample["messages"][1]["content"]
        assistant = sample["messages"][2]["content"]
        
        # Simple format
        full_text = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n{assistant}<|im_end|>"
        return {"text": full_text}

    tokenized_dataset = dataset.map(format_prompt)
    
    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=256)
    
    tokenized_dataset = tokenized_dataset.map(tokenize_function, batched=True)

    # 5. Helper for labeling (train only on assistant output) - Optional but better
    # For simplicity, we'll use DataCollatorForLanguageModeling which mask nothing (trains on user prompt too)
    # Ideally we'd use DataCollatorForCompletionOnlyLM from TRL, but let's stick to simple transformers.
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # 6. Trainer
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=10, # Deep learning (lobotomy)
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="epoch",
        use_mps_device=True if device == "mps" else False
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    print("Starting training...")
    trainer.train()
    
    print("Saving model...")
    model.save_pretrained(OUTPUT_DIR)
    print("Done!")

if __name__ == "__main__":
    main()
