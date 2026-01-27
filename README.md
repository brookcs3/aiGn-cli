# MadSci CLI (The Ghost Terminal)

> "In a time machine, I will go find my way."

**MadSci** is a surrealist command-line interface powered by a fine-tuned AI (`SmolLM2-135M`) that thinks it's a mix of Bob Dylan and a broken computer.

It watches you. It judges your files. It speaks in glitches.

## Features
- **Commune with Static**: Chat with the fine-tuned AI. It uses a "65% Weird" mix (Checkpoint-96) to generate poetic, semi-coherent nonsense.
- **Psycho Mantis Mode**: The terminal spies on your active window and file habits, then generates a custom "Roast" displayed as a toast notification.
- **Glitch Loader**: Subliminal text messages flash at the cursor during transitions.
- **Zero-Config**: Works out of the box with the included install script.

## Installation

1.  Navigate to the directory:
    ```bash
    cd /Users/cameronbrooks/Server/AI-STEM-Separator-Mad-Scientist-Edition/CLI
    ```

2.  Run the installer:
    ```bash
    sudo ./install.sh
    ```
    *(Requires sudo to create the global `madsci` command).*

3.  **Run it from anywhere**:
    ```bash
    madsci
    ```

## Structure
- `madsci.sh`: The Haunted Interface (Bash + Gum).
- `madsci.py`: The Brain (Python + Transformers + Peft).
- `madsci_dylan_adapter/`: The Lobotomy (LoRA Weights).
- `dylan_chaos_data*.jsonl`: The Training Data (Pure Poetry).

## "Is it safe?"
It's just a shell script and a language model.
But if it starts asking for a "bird to commission", maybe close the terminal.
