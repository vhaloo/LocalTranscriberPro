#!/bin/bash
cd "$(dirname "$0")"
echo "==================================================="
echo "   Local Transcriber Pro - Mac Installer"
echo "==================================================="
echo "This script will build the app and install it to your Applications folder."
echo "It may take 2-5 minutes. Please wait."
echo ""

# 1. Check Python
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 not found!"
    echo "Please install it from python.org or run: brew install python@3.12"
    read -p "Press ENTER to exit..."
    exit 1
fi

# 2. Setup Build Environment
echo "📦 Setting up build environment..."
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip > /dev/null
echo "⬇️  Installing dependencies..."
pip install -r requirements.txt > /dev/null
pip install pyinstaller > /dev/null

# 3. Build the App
echo "🔨 Building Application (This uses your CPU/GPU to optimize)..."
# Using the same flags as build_mac.command
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
    echo "❌ Build failed! Check build_log.txt for details."
    read -p "Press ENTER to exit..."
    exit 1
fi

# 4. Install
echo "📂 Moving to Applications folder..."
if [ -d "/Applications/Local Transcriber Pro.app" ]; then
    rm -rf "/Applications/Local Transcriber Pro.app"
fi
mv "dist/Local Transcriber Pro.app" /Applications/

# 5. Cleanup
echo "🧹 Cleaning up temporary files..."
rm -rf build dist *.spec

echo ""
echo "✅ SUCCESS!"
echo "Local Transcriber Pro has been installed to your Applications folder."
echo "You can now delete this source folder."
echo ""
read -p "Press ENTER to close..."
