#!/bin/bash
cd "$(dirname "$0")"

# --- SELF-CORRECTION: Download Source if Missing ---
if [ ! -f "requirements.txt" ]; then
    echo "==================================================="
    echo "   Local Transcriber Pro - Downloader"
    echo "==================================================="
    echo "📂 Source files not found in current folder."
    echo "⬇️  Downloading latest source code from GitHub..."
    
    # Download ZIP
    curl -L https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip -o LTP_Source.zip
    
    # Unzip and cleanup
    echo "📦 Extracting..."
    unzip -q LTP_Source.zip
    rm LTP_Source.zip
    
    # Enter directory
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
    echo "   - Builds App & Installs to ~/Applications"
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
    
    # Check/Install Homebrew
    if ! command -v brew &> /dev/null; then
        echo "⚠️  Homebrew not found. Skipping auto-install of dependencies."
        echo "   (Install Homebrew at https://brew.sh if you need ffmpeg)"
    else
        echo "⬇️  Updating Homebrew..."
        brew update >/dev/null 2>&1
        
        echo "⬇️  Installing FFmpeg (Audio Engine)..."
        brew install ffmpeg >/dev/null 2>&1
        
        echo "⬇️  Installing Python 3.12..."
        # Explicitly install python@3.12
        brew install python@3.12 >/dev/null 2>&1
        
        # Link it if needed (force link sometimes required for brew python)
        brew unlink python@3.12 && brew link --overwrite python@3.12 >/dev/null 2>&1
    fi

    # verify python3.12 exists
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
    
    # Always recreate venv to ensure clean state
    rm -rf venv
    python3.12 -m venv venv
    source venv/bin/activate
    
    # Verify version inside venv
    PY_VER=$(python --version)
    echo "   Using: $PY_VER"

    pip install --upgrade pip >/dev/null
    echo "⬇️  Installing Python Libraries (This takes a moment)..."
    pip install -r requirements.txt >/dev/null
    pip install pyinstaller >/dev/null

    echo ""
    echo "🔨 Building Application..."
    rm -rf build dist *.spec
    
    # Run PyInstaller
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
        echo "❌ Build Failed! Last 20 lines of log:"
        echo "-------------------------------------"
        tail -n 20 build_log.txt
        echo "-------------------------------------"
        read -p "Press ENTER..."
        return
    fi

    echo "📂 Installing to ~/Applications..."
    mkdir -p "$HOME/Applications"
    rm -rf "$HOME/Applications/Local Transcriber Pro.app"
    mv "dist/Local Transcriber Pro.app" "$HOME/Applications/"
    
    # Cleanup
    rm -rf build dist *.spec

    echo "✅ Success! Installed to User Applications."
    echo "   You can delete the 'LocalTranscriberPro-main' folder now."
    read -p "Press ENTER to return to menu..."
}

function debug_app() {
    echo ""
    APP_PATH="$HOME/Applications/Local Transcriber Pro.app/Contents/MacOS/Local Transcriber Pro"
    if [ ! -f "$APP_PATH" ]; then
        echo "❌ App not found at: $APP_PATH"
    else
        echo "🚀 Launching App in Debug Mode..."
        echo "   (Errors will appear below)"
        echo "---------------------------------------------------"
        "$APP_PATH"
        echo "---------------------------------------------------"
        echo "App closed."
    fi
    read -p "Press ENTER to return to menu..."
}

# Main Loop
while true; do
    show_menu
    case $choice in
        1)
            install_deps
            build_app
            ;; 
        2)
            build_app
            ;; 
        3)
            debug_app
            ;; 
        4)
            exit 0
            ;; 
        *)
            echo "Invalid option."
            ;; 
    esac
done
