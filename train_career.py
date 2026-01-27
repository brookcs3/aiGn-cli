#!/usr/bin/env python3
"""
Train CareerAI adapter using LoRA on SmolLM2.
Based on the original train.py but with career-focused data.

Usage:
    1. Generate training data: python generate_career_data.py
    2. Train the adapter: python train_career.py

Training takes ~5 minutes on Mac with MPS.
"""
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
DATA_FILE = "career_training_data.jsonl"
OUTPUT_DIR = "./career_adapter"


def main():
    # 1. Load Device
    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    print(f"Training on device: {device}")

    # 2. Load Model & Tokenizer
    print("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

    # 3. LoRA Configuration
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=8,            # Rank
        lora_alpha=32,  # Scaling
        lora_dropout=0.1,
        target_modules=["q_proj", "v_proj"]
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    model.to(device)

    # 4. Load & Format Dataset
    dataset = load_dataset("json", data_files=DATA_FILE, split="train")

    def format_prompt(sample):
        # Convert messages to training format
        system = sample["messages"][0]["content"]
        user = sample["messages"][1]["content"]
        assistant = sample["messages"][2]["content"]

        # Use SmolLM2 chat format
        full_text = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n{assistant}<|im_end|>"
        return {"text": full_text}

    tokenized_dataset = dataset.map(format_prompt)

    def tokenize_function(examples):
        return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=512)

    tokenized_dataset = tokenized_dataset.map(tokenize_function, batched=True)

    # 5. Data Collator
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # 6. Training Arguments - optimized for quick training
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=5,  # Fewer epochs for faster training
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="epoch",
        save_total_limit=2,  # Keep only last 2 checkpoints
        warmup_steps=10,
        weight_decay=0.01,
        use_mps_device=True if device == "mps" else False
    )

    # 7. Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=data_collator,
    )

    # 8. Train
    print("\nStarting training...")
    print(f"Dataset size: {len(tokenized_dataset)} samples")
    trainer.train()

    # 9. Save
    print("\nSaving model...")
    model.save_pretrained(OUTPUT_DIR)
    print(f"Model saved to: {OUTPUT_DIR}")

    # 10. Update config to use the new adapter
    print("\n" + "="*50)
    print("Training complete!")
    print("="*50)
    print("\nTo use the career adapter, update backend/config.py:")
    print('  CAREER_ADAPTER_PATH = CLI_ROOT / "career_adapter"')
    print('  USE_CAREER_ADAPTER = True')
    print("\nOr the adapter will be loaded automatically if present.")


if __name__ == "__main__":
    main()
