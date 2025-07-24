#!/bin/bash
# Setup dedicated virtual environment for crew-api service

echo "🔧 Setting up crew-api virtual environment..."

# Navigate to this script's directory so the venv is created locally
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Remove old venv if exists
if [ -d ".venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf .venv
fi

# Create new virtual environment with Python 3.11 (more compatible)
echo "Creating new virtual environment..."
python3.11 -m venv .venv || python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install from minimal requirements
echo "Installing from requirements-minimal.txt..."
pip install -r requirements-minimal.txt

# Note: crewai will pull in chromadb for agent memory
# We're not fighting it - just accepting it as part of crewai

echo "Installed packages:"
pip list | grep -E "crewai|chromadb|httpx|fastapi"

echo "✅ Virtual environment setup complete!"
echo "To activate: source services/crew-api/.venv/bin/activate"
