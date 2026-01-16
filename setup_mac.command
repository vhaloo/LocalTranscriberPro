#!/bin/bash
cd "$(dirname "$0")"
echo "---------------------------------------------------"
echo "  Local Transcriber Pro - Mac Setup (Auto)"
echo "---------------------------------------------------"

# Check for Python 3.12 (brew or other)
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 not found!"
    echo "Please install it from python.org or via Homebrew:"
    echo "  brew install python@3.12"
    echo ""
    read -p "Press ENTER to exit..."
    exit 1
fi

# Create venv
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv
fi

# Activate and install
source venv/bin/activate
echo "⬇️  Installing dependencies (this may take a minute)..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo ""
echo "✅ Setup complete!"
echo "You can now double-click 'run_app.command' to start the app."
echo ""
read -p "Press ENTER to close..."
