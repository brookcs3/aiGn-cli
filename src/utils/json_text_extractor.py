#!/usr/bin/env python3
import re
import sys

def extract_text_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = file.read()

        # Remove JSON-like structure elements
        text_only = re.sub(r'[\[\]{},":]', ' ', data)
        # Clean up extra whitespace
        text_only = re.sub(r'\s+', ' ', text_only).strip()

        return text_only
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 json_text_extractor.py <input_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    extracted_text = extract_text_from_file(input_file)
    print(extracted_text)
