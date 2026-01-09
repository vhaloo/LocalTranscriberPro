@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   Local Transcriber Pro v0.8 - EXE Builder
echo ========================================================
echo.
echo This script will:
echo 1. Create a Python virtual environment.
echo 2. Download the AI Engine (PyTorch + CUDA) ~3GB.
echo 3. Build the standalone executable file.
echo.
pause

:: 1. Check Python
py -3.12 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.12 is not found!
    echo Please install Python 3.12 from python.org and try again.
    pause
    exit /b
)

:: 2. Create Venv
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    py -3.12 -m venv venv
) else (
    echo [INFO] Virtual environment found.
)

:: 3. Install Dependencies
echo [INFO] Installing/Updating dependencies (This may take a while)...
call venv\Scripts\activate
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
pip install pyinstaller

:: 4. Build EXE
echo [INFO] Building Executable...
if exist "dist\LocalTranscriberPro.exe" del "dist\LocalTranscriberPro.exe"

pyinstaller --noconsole --onefile ^
    --name "LocalTranscriberPro" ^
    --add-data "venv\Lib\site-packages\customtkinter;customtkinter" ^
    --add-data "venv\Lib\site-packages\whisper\assets;whisper\assets" ^
    --collect-all "whisper" ^
    --collect-all "openai_whisper" ^
    --hidden-import "scipy.special.cython_special" ^
    --hidden-import "scipy.integrate.lsoda" ^
    --hidden-import "sklearn.utils._cython_blas" ^
    --hidden-import "sklearn.neighbors.typedefs" ^
    --hidden-import "sklearn.neighbors.quad_tree" ^
    --hidden-import "sklearn.tree" ^
    --hidden-import "sklearn.tree._utils" ^
    local_transcriber.py

echo.
echo ========================================================
if exist "dist\LocalTranscriberPro.exe" (
    echo [SUCCESS] Build Complete!
    echo File located at: dist\LocalTranscriberPro.exe
) else (
    echo [ERROR] Build Failed. Check the output above.
)
echo ========================================================
pause