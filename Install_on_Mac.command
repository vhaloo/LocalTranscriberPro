#!/bin/bash
cd "$(dirname "$0")"

function show_menu() {
    clear
    echo "==================================================="
    echo "   Local Transcriber Pro - Mac Tool"
    echo "==================================================="
    echo "1. Full Install (Recommended for first time)"
    echo "   - Installs FFmpeg, Python, Dependencies"
    echo "   - Builds App & Installs to ~/Applications"
    echo ""
    echo "2. Quick Update (Rebuild Only)"
    echo "   - Skips system checks, just rebuilds the code"
    echo ""
    echo "3. Launch & Debug"
    echo "   - Run the installed app to see crash errors"
    echo ""
    echo "4. Exit"
    echo "==================================================="
    read -p "Enter choice (1-4): " choice
}

function install_deps() {
    echo ""
    echo "🔍 Checking System Dependencies..."
    if ! command -v brew &> /dev/null; then
        echo "⚠️  Homebrew not found. Skipping FFmpeg install."
    else
        echo "⬇️  Installing/Updating FFmpeg & Python 3.12..."
        # We explicitly install python@3.12 to ensure compatibility (PyTorch supports 3.12).
        # We DO NOT install 'python-tk' generic, as it pulls the latest python (3.13+).
        # Homebrew's python@3.12 includes tkinter support.
        brew install ffmpeg python@3.12 2>/dev/null
    fi

    if ! command -v python3.12 &> /dev/null; then
        echo "❌ Python 3.12 missing! Run 'brew install python@3.12'"
        read -p "Press ENTER to exit..."
        exit 1
    fi
}

function build_app() {
    echo ""
    echo "📦 Preparing Python Environment..."
    if [ ! -d "venv" ]; then
        python3.12 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip >/dev/null
    echo "⬇️  Installing Python Requirements..."
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
        --collect-all "scipy" \
        --collect-all "yt_dlp" \
        --collect-all "tkinterdnd2" \
        --collect-all "customtkinter" \
        --hidden-import "scipy.special.cython_special" \
        --hidden-import "scipy.integrate.lsoda" \
        --exclude-module "tensorflow" \
        main.py > build_log.txt 2>&1

    if [ ! -d "dist/Local Transcriber Pro.app" ]; then
        echo "❌ Build Failed! Log:"
        tail -n 20 build_log.txt
        read -p "Press ENTER..."
        return
    fi

    echo "📂 Installing to ~/Applications..."
    mkdir -p "$HOME/Applications"
    rm -rf "$HOME/Applications/Local Transcriber Pro.app"
    mv "dist/Local Transcriber Pro.app" "$HOME/Applications/"
    rm -rf build dist *.spec

    echo "✅ Success! Installed to User Applications."
    read -p "Press ENTER to return to menu..."
}

function debug_app() {
    echo ""
    APP_PATH="$HOME/Applications/Local Transcriber Pro.app/Contents/MacOS/Local Transcriber Pro"
    if [ ! -f "$APP_PATH" ]; then
        echo "❌ App not found in ~/Applications."
    else
        echo "🚀 Launching in Console Mode..."
        echo "--------------------------------"
        "$APP_PATH"
        echo "--------------------------------"
        echo "App closed."
    fi
    read -p "Press ENTER to return to menu..."
}

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