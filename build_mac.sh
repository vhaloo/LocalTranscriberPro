#!/bin/bash
echo "Building Local Transcriber Pro for Mac (Apple Silicon)..."

source venv/bin/activate

# Clean build
rm -rf build dist *.spec

# Run PyInstaller
# We collect tkinterdnd2 explicitly. 
# Note: On Mac, CTk might need to be collected carefully.
# We also ensure 'mps' support is not excluded (it's part of torch).

pyinstaller --noconsole --onefile --clean \
    --name "LocalTranscriberPro_Mac" \
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
    main.py

echo "Build complete. Check 'dist/' folder."
