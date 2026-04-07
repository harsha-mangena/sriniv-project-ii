#!/bin/bash
set -e

echo "================================================"
echo "  InterviewPilot — One-Command Setup (macOS)"
echo "================================================"

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "This script is designed for macOS. Exiting."
    exit 1
fi

# Check Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo "Warning: This app is optimized for Apple Silicon (M1/M2/M3/M4)."
fi

# Install Homebrew if needed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install Rust if needed (required for Tauri)
if ! command -v rustc &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Ensure Xcode Command Line Tools are installed
if ! xcode-select -p &> /dev/null; then
    echo "Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "Please complete the Xcode CLI Tools installation and re-run this script."
    exit 1
fi

# Install Ollama
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    brew install ollama
fi

# Start Ollama service
echo "Starting Ollama..."
ollama serve &>/dev/null &
sleep 3

# Pull models
echo "Pulling AI models (this may take a few minutes)..."
ollama pull qwen3:8b || ollama pull llama3.1:8b
ollama pull nomic-embed-text

# Install Python dependencies
echo "Setting up Python backend..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies
echo "Setting up frontend..."
cd ../frontend
npm install

echo ""
echo "================================================"
echo "  Setup complete!"
echo ""
echo "  Web mode:    ./scripts/dev.sh"
echo "  Desktop app: cd src-tauri && cargo tauri dev"
echo "================================================"
