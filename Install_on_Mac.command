#!/bin/bash
cd "$(dirname "$0")"

# --- SELF-CORRECTION: Download Source if Missing ---
if [ ! -f "requirements.txt" ]; then
    echo "==================================================="
    echo "   Local Transcriber Pro - Downloader"
    echo "==================================================="
    echo "📂 Source files not found in current folder."
    echo "⬇️  Downloading latest source code from GitHub..."
    curl -L https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip -o LTP_Source.zip
    echo "📦 Extracting..."
    unzip -q LTP_Source.zip
    rm LTP_Source.zip
    if [ -d "LocalTranscriberPro-main" ]; then
        cd LocalTranscriberPro-main
    else
        echo "❌ Error: Download failed or folder structure changed."
        exit 1
    fi
fi
# ---------------------------------------------------

function show_menu() {
    clear
    echo "==================================================="
    echo "   Local Transcriber Pro - Mac Installer"
    echo "==================================================="
    echo "1. Full Install (Recommended)"
    echo "   - Downloads FFmpeg & Python 3.12"
    echo "   - Builds, SIGNS & Installs App to ~/Applications"
    echo ""
    echo "2. Quick Rebuild"
    echo "   - Just rebuilds code (if already setup)"
    echo ""
    echo "3. Launch & Debug"
    echo "   - Run installed app to see errors"
    echo ""
    echo "4. Exit"
    echo "==================================================="
    read -p "Enter choice (1-4): " choice
}

function install_deps() {
    echo ""
    echo "🔍 Checking System Dependencies..."
    if ! command -v brew &> /dev/null; then
        echo "⚠️  Homebrew not found. Skipping auto-install of dependencies."
        echo "   (Install Homebrew at https://brew.sh if you need ffmpeg)"
    else
        echo "⬇️  Updating Homebrew..."
        brew update >/dev/null 2>&1
        echo "⬇️  Installing FFmpeg (Audio Engine)..."
        brew install ffmpeg >/dev/null 2>&1
        echo "⬇️  Installing Python 3.12..."
        brew install python@3.12 >/dev/null 2>&1
        brew unlink python@3.12 && brew link --overwrite python@3.12 >/dev/null 2>&1
    fi

    if ! command -v python3.12 &> /dev/null; then
        echo "❌ Python 3.12 binary not found!"
        echo "   Please run: 'brew install python@3.12'"
        read -p "Press ENTER to exit..."
        exit 1
    fi
}

function build_app() {
    echo ""
    echo "📦 Setting up Virtual Environment (Python 3.12)..."
    rm -rf venv
    python3.12 -m venv venv
    source venv/bin/activate
    
    pip install --upgrade pip >/dev/null
    echo "⬇️  Installing Python Libraries..."
    pip install -r requirements.txt >/dev/null
    pip install pyinstaller >/dev/null

    echo ""
    echo "🔨 Building Application..."
    rm -rf build dist *.spec
    pyinstaller --noconsole --windowed --clean \
        --name "Local Transcriber Pro" \
        --add-data "src:src" \
        --collect-all "whisper" \
        --collect-all "openai_whisper" \
        --collect-all "tbb" \
        --collect-all "numba" \
        --collect-all "torch" \
        --collect-all "torchaudio" \
        --collect-all "scipy" \
        --collect-all "yt_dlp" \
        --collect-all "tkinterdnd2" \
        --collect-all "customtkinter" \
        --collect-all "certifi" \
        --collect-all "speechbrain" \
        --collect-all "sklearn" \
        --hidden-import "scipy.special.cython_special" \
        --hidden-import "scipy.integrate.lsoda" \
        --hidden-import "sklearn.utils._cython_blas" \
        --hidden-import "sklearn.neighbors.typedefs" \
        --hidden-import "sklearn.neighbors.quad_tree" \
        --hidden-import "sklearn.tree._utils" \
        --exclude-module "tensorflow" \
        main.py > build_log.txt 2>&1

    if [ ! -d "dist/Local Transcriber Pro.app" ]; then
        echo "❌ Build Failed! Last 20 lines of log:"
        tail -n 20 build_log.txt
        read -p "Press ENTER..."
        return
    fi

    echo "🔐 Signing Internal Libraries..."
    find "dist/Local Transcriber Pro.app/Contents" -type f -o -name "*.dylib" -o -name "*.so" -exec codesign --force --sign - "{}" \; >/dev/null 2>&1

    echo "🔐 Signing App Bundle (Ad-Hoc)..."
    codesign --force --deep --sign - --entitlements entitlements.plist "dist/Local Transcriber Pro.app" >/dev/null 2>&1

    echo ""
    echo "📂 Installing to /Applications..."
    echo "🔑 Please enter your password to move the app:"
    
    if [ -d "/Applications/Local Transcriber Pro.app" ]; then
        sudo rm -rf "/Applications/Local Transcriber Pro.app"
    fi
    
    sudo mv "dist/Local Transcriber Pro.app" /Applications/
    sudo chown -R root:wheel "/Applications/Local Transcriber Pro.app"

    rm -rf build dist *.spec

    echo ""
    echo "✅ Success! Installed to /Applications."
    echo "   You can delete the source folder now."
    read -p "Press ENTER to return to menu..."
}

function debug_app() {
    echo ""
    APP_PATH="/Applications/Local Transcriber Pro.app/Contents/MacOS/Local Transcriber Pro"
    
    if [ ! -f "$APP_PATH" ]; then
        echo "❌ App not found at: $APP_PATH"
        echo "   (Did you install it yet?)"
    else
        echo "🚀 Launching App in Debug Mode..."
        "$APP_PATH"
    fi
    read -p "Press ENTER to return to menu..."
}

while true; do
    show_menu
    case $choice in
        1) install_deps; build_app ;;
        2) build_app ;;
        3) debug_app ;;
        4) exit 0 ;;
        *) echo "Invalid option." ;;
    esac
done