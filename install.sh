#!/bin/bash

# Install Script for MadSci CLI
# Sets up dependencies and creates a global 'madsci' command.

set -e

echo "🧪 Initializing MadSci Installation Protocol..."

# 1. Check for Gum (UI Dependency)
if ! command -v gum &> /dev/null; then
    echo "📦 Gum not found. Installing via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install gum
    else
        echo "❌ Error: Homebrew not found. Please install 'gum' manually."
        exit 1
    fi
else
    echo "✅ Gum detected."
fi

# 2. Python Dependencies
echo "🐍 Installing Python dependencies..."
# Check for virtual env support or just install globally/user
pip3 install -q torch transformers pandas peft accelerate

# 3. Permissions
echo "🔒 Setting executable permissions..."
chmod +x madsci.sh
chmod +x madsci.py

# 4. Global Symlink
TARGET="/usr/local/bin/madsci"
SOURCE="$(pwd)/madsci.sh"

echo "🔗 Linking '$SOURCE' to '$TARGET'..."
if [ -L "$TARGET" ]; then
    echo "⚠️  Link already exists. Overwriting..."
    sudo rm "$TARGET"
fi

# Use sudo to create the link
if sudo ln -s "$SOURCE" "$TARGET"; then
    echo "✅ Global command 'madsci' created!"
else
    echo "❌ Failed to create symlink (permission denied?)."
    exit 1
fi

echo ""
echo "🎉 Installation Complete."
echo "   Run 'madsci' from any terminal to commune with the static."
