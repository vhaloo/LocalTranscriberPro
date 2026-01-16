#!/bin/bash
cd "$(dirname "$0")"
echo "==================================================="
echo "   Local Transcriber Pro - Mac Installer"
echo "==================================================="
echo "This script will build the app and install it to your user Applications folder."
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

# 4. Install to User Applications (No Sudo Required)
echo "📂 Moving to ~/Applications folder..."
USER_APPS="$HOME/Applications"
if [ ! -d "$USER_APPS" ]; then
    mkdir -p "$USER_APPS"
fi

TARGET_APP="$USER_APPS/Local Transcriber Pro.app"

if [ -d "$TARGET_APP" ]; then
    rm -rf "$TARGET_APP"
fi

mv "dist/Local Transcriber Pro.app" "$USER_APPS/"

# 5. Cleanup
echo "🧹 Cleaning up temporary files..."
rm -rf build dist *.spec

echo ""
echo "✅ SUCCESS!"
echo "Local Transcriber Pro has been installed to:"
echo "   $USER_APPS"
echo ""
echo "👉 You can find it in your User Applications folder."
echo "   (If you don't see it in Launchpad, check your Home folder > Applications)"
echo ""
echo "You can now delete this source folder."
echo ""
read -p "Press ENTER to close..."