#!/bin/bash
cd "$(dirname "$0")"
echo "==================================================="
echo "   Local Transcriber Pro - Mac Installer v2"
echo "==================================================="
echo "This script will fix dependencies and reinstall the app."
echo ""

# 0. Check Homebrew (Essential for dependencies)
if ! command -v brew &> /dev/null; then
    echo "⚠️  Homebrew is not installed."
    echo "It is strongly recommended for installing 'ffmpeg' (required for audio)."
    echo "Please visit https://brew.sh to install it, then run this script again."
    read -p "Press ENTER to continue anyway (App might crash)..."
fi

# 1. Install System Dependencies
echo "⬇️  Checking system libraries..."
if command -v brew &> /dev/null; then
    echo "   - Installing ffmpeg (Audio Engine)..."
    brew install ffmpeg > /dev/null 2>&1
    echo "   - Installing python-tk (GUI Support)..."
    brew install python-tk > /dev/null 2>&1
else
    echo "❌ Skipped Brew installs (Homebrew missing)."
fi

# 2. Setup Python
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 not found! Run: brew install python@3.12"
    read -p "Press ENTER to exit..."
    exit 1
fi

echo "📦 Setting up virtual environment..."
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null
echo "⬇️  Installing Python packages..."
pip install -r requirements.txt > /dev/null
pip install pyinstaller > /dev/null

# 3. Build
echo "🔨 Building App (This takes ~2 minutes)..."
rm -rf build dist
pyinstaller --noconsole --windowed --clean \
    --name "Local Transcriber Pro" \
    --add-data "src:src" \
    --collect-all "whisper" \
    --collect-all "openai_whisper" \
    --collect-all "tbb" \
    --collect-all "numba" \
    --collect-all "torch" \
    --collect-all "scipy" \
    --collect-all "yt_dlp" \
    --collect-all "tkinterdnd2" \
    --collect-all "customtkinter" \
    --hidden-import "scipy.special.cython_special" \
    --hidden-import "scipy.integrate.lsoda" \
    --exclude-module "tensorflow" \
    main.py > build_log.txt 2>&1

if [ ! -d "dist/Local Transcriber Pro.app" ]; then
    echo "❌ Build failed! View 'build_log.txt' for details."
    read -p "Press ENTER to exit..."
    exit 1
fi

# 4. Install
echo "📂 Installing to ~/Applications..."
USER_APPS="$HOME/Applications"
mkdir -p "$USER_APPS"
rm -rf "$USER_APPS/Local Transcriber Pro.app"
mv "dist/Local Transcriber Pro.app" "$USER_APPS/"

# 5. Cleanup
rm -rf build dist *.spec

echo ""
echo "✅ INSTALLATION COMPLETE!"
echo "---------------------------------------------------"
echo "The app is in: $USER_APPS"

echo ""
echo "❓ TROUBLESHOOTING:"
echo "If the app crashes (bounces then quits), it is usually due to a missing file."
echo "We can launch it right now in 'Debug Mode' to see the error message."

read -p "Press ENTER to Launch in Debug Mode (or Ctrl+C to quit)..."

echo ""
echo "🚀 Launching... (Look for error messages below)"
echo "---------------------------------------------------"
"$USER_APPS/Local Transcriber Pro.app/Contents/MacOS/Local Transcriber Pro"
