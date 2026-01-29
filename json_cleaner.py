#!/usr/bin/env python3
import sys
import re
from subprocess import Popen, PIPE

def clean_json(text):
    """Remove JSON structural elements"""
    return re.sub(r'\s+', ' ', re.sub(r'[\[\]{},":]', ' ', text)).strip()

def main():
    # Start the original aichat.py process
    aichat_process = Popen(
        ["python", "llm_inference", "--chat"],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
        bufsize=1
    )

    print("JSON Cleaner Plugin Active (type '>> clean json {...}' to clean JSON)")

    while True:
        try:
            # Read user input
            user_input = input("> ")

            # Check for our custom command
            if user_input.startswith(">> clean json"):
                json_text = user_input[12:].strip()
                if json_text:
                    print("[Cleaned JSON]")
                    print(clean_json(json_text))
                    print("---")
                    # Send a dummy command to aichat to keep it alive
                    aichat_process.stdin.write("\n")
                    aichat_process.stdin.flush()
                    continue
                else:
                    print("Error: No JSON provided after '>> clean json'")
                    continue

            # Pass normal commands to aichat.py
            aichat_process.stdin.write(user_input + "\n")
            aichat_process.stdin.flush()

            # Print aichat's response
            output = aichat_process.stdout.readline()
            while output:
                print(output, end='')
                output = aichat_process.stdout.readline()

        except KeyboardInterrupt:
            aichat_process.terminate()
            break

if __name__ == "__main__":
    main()
