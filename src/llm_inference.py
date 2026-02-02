import os
import sys
import re
import argparse
import pyperclip
from llama_cpp import Llama
from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings

# 1. Suppress low-level C++ / Metal logs
class SuppressStderr:
    def __enter__(self):
        self.stderr_fd = sys.stderr.fileno()
        self.saved_stderr_fd = os.dup(self.stderr_fd)
        self.devnull = open(os.devnull, "w")
        os.dup2(self.devnull.fileno(), self.stderr_fd)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.dup2(self.saved_stderr_fd, self.stderr_fd)
        os.close(self.saved_stderr_fd)
        self.devnull.close()

# 2. Strip <think> / <analysis> blocks from model output
def strip_think_blocks(text: str) -> str:
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<analysis>.*?</analysis>\s*", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()

def read_chat_input() -> str:
    """
    Claude Code-style input: intercepts large pastes and shows a placeholder.
    """
    if not sys.stdin.isatty():
        return sys.stdin.read()

    kb = KeyBindings()
    # Dictionary to map unique placeholders back to original long text
    paste_registry = {}

    @kb.add('c-v')
    def _(event):
        # Get data from clipboard using pyperclip for reliability
        data = pyperclip.paste()
        if len(data) > 300:  # Threshold for collapsing
            placeholder = f"[Pasted content {len(data)} char]"
            paste_registry[placeholder] = data
            event.current_buffer.insert_text(placeholder)
        else:
            event.current_buffer.insert_text(data)

    # Use prompt_toolkit for the interactive line
    try:
        user_input = prompt(">>> ", key_bindings=kb)
    except EOFError:
        return ""

    # Swap placeholders back with the actual content before returning
    for placeholder, original_text in paste_registry.items():
        user_input = user_input.replace(placeholder, original_text)
    
    return user_input

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true", help="Interactive/piped chat input mode")
    parser.add_argument("--system", type=str, default=None, help="System prompt string")
    parser.add_argument("--system-file", type=str, default=None, help="Path to system prompt file")
    # Model is in parent dir (root of repo)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_model = os.path.join(script_dir, "..", "smollm2-135m.gguf")
    parser.add_argument("--model", type=str, default=default_model)
    parser.add_argument("--ctx", type=int, default=32768, help="Context window (n_ctx)")
    parser.add_argument("--gpu", type=int, default=-1, help="n_gpu_layers (-1 = all)")
    args = parser.parse_args()

    # Build system prompt
    system_prompt = None
    if args.system_file:
        with open(args.system_file, "r") as f:
            system_prompt = f.read().strip()
    elif args.system:
        system_prompt = args.system

    # Load model silently
    with SuppressStderr():
        llm = Llama(
            model_path=args.model,
            n_ctx=args.ctx,
            tokenize=True,
            max_new_tokens=32768,
            n_gpu_layers=args.gpu,
            verbose=False
        )

    # Build base messages (system prompt if provided, otherwise empty)
    base_messages = []
    if system_prompt:
        base_messages.append({"role": "system", "content": system_prompt})

    if args.chat:
        # Loop for continuous chat interaction
        is_piped = not sys.stdin.isatty()
        while True:
            user_text = read_chat_input()
            if not user_text.strip():
                # If piped input is exhausted, exit
                if is_piped:
                    break
                continue
            if user_text.lower() in ["/exit", "/quit"]:
                break

            output = llm.create_chat_completion(
                messages=base_messages + [{"role": "user", "content": user_text}]
            )
            raw = output["choices"][0]["message"]["content"]

            print(strip_think_blocks(raw))
    else:
        # Single-shot mode
        user_text = "What is the capital of France?"
        output = llm.create_chat_completion(
            messages=base_messages + [{"role": "user", "content": user_text}]
        )
        raw = output["choices"][0]["message"]["content"]
        print(strip_think_blocks(raw))

if __name__ == "__main__":
    main()
