#!/bin/bash

echo "Setting up MadSci..."

# Install gum if not present
if ! command -v gum &> /dev/null; then
    echo "Installing gum..."
    brew install gum
else
    echo "gum is already installed."
fi

# Install python requirements
echo "Installing python dependencies..."
pip install transformers torch

echo "Setup complete! Run ./madsci.sh to start."
