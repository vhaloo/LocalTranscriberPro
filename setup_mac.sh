#!/bin/bash
echo "Setting up Local Transcriber Pro for Mac..."

# Check for Python 3.12 (brew or other)
if ! command -v python3.12 &> /dev/null; then
    echo "Python 3.12 not found. Please install it (e.g., 'brew install python@3.12')."
    exit 1
fi

# Create venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.12 -m venv venv
fi

# Activate and install
source venv/bin/activate
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install PyInstaller explicitly
pip install pyinstaller

echo "Setup complete! You can now run 'python main.py' or './build_mac.sh'."
