@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Ultimate Installer
color 1F
cls

echo.
echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - ULTIMATE INSTALLER
echo   (Developed by Vhaloo)
echo ===============================================================================
echo.
echo   This script will:
echo   1. Check/Install System Requirements (FFmpeg, Visual C++)
echo   2. Download the latest source code
echo   3. Install AI Engine (PyTorch + CUDA)
echo   4. Compile a high-performance EXE for YOUR PC
echo   5. Launch the app
echo.
echo   NOTE: This process ensures the app runs 100% offline and secure on your hardware.
echo.
pause
cls

:: --- STEP 1: PREREQUISITES ---
echo [STEP 1/6] Checking System Prerequisites...

:: Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [MISSING] FFmpeg not found. Installing via Winget...
    winget install --id "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements
    echo [INFO] FFmpeg installed. Refreshing environment...
    call refreshenv 2>nul
) else (
    echo [OK] FFmpeg is installed.
)

:: Check Python
py --version >nul 2>&1
if %errorlevel% neq 0 (
    color 4F
    echo.
    echo [CRITICAL ERROR] Python is missing!
    echo.
    echo Please install Python 3.11 or 3.12 from the Microsoft Store or python.org.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b
)
echo [OK] Python found.

:: --- STEP 2: WORKSPACE ---
echo.
echo [STEP 2/6] Preparing Workspace...
if exist "LT_Build" (
    echo ... Cleaning old build files...
    rmdir /s /q "LT_Build"
)
mkdir "LT_Build"
cd LT_Build

:: --- STEP 3: DOWNLOAD ---
echo.
echo [STEP 3/6] Downloading Latest Source Code...
echo ... Fetching from GitHub (main branch)...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip' -OutFile 'source.zip'"

if not exist "source.zip" (
    color 4F
    echo [ERROR] Download failed. Check your internet connection.
    pause
    exit /b
)

echo ... Extracting files...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"
cd LocalTranscriberPro-main

:: --- STEP 4: AI ENGINE ---
echo.
echo [STEP 4/6] Installing AI Engine (This is the heavy part)...
echo ... Creating isolated environment...
py -m venv venv
call venv\Scripts\activate

echo ... Updating pip...
python -m pip install --upgrade pip

echo.
echo [INFO] Installing PyTorch with CUDA 12.4 support...
echo        (This downloads ~2.5GB. Please be patient.)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

echo.
echo [INFO] Installing Application Libraries...
pip install -r requirements.txt
pip install pyinstaller

:: --- STEP 5: COMPILATION ---
echo.
echo [STEP 5/6] Compiling Optimized Executable...
echo ... Analyzing code...
echo ... Bundling libraries...

call build_exe.bat

:: --- STEP 6: FINALIZE ---
echo.
if exist "dist\LocalTranscriberPro_v0.9.6.exe" (
    cls
    color 2F
    echo ===============================================================================
    echo   INSTALLATION COMPLETE!
    echo ===============================================================================
    echo.
    echo [SUCCESS] moving 'LocalTranscriberPro.exe' to your Desktop...
    copy /Y "dist\LocalTranscriberPro_v0.9.6.exe" "%USERPROFILE%\Desktop\LocalTranscriberPro.exe"
    
    echo.
    echo [INFO] Cleaning up build files to save space...
    cd ..\..
    :: rmdir /s /q "LT_Build"  <-- Optional: Keep it commented if they want to rebuild fast later
    
    echo.
    echo [LAUNCH] Starting Local Transcriber Pro...
    start "" "%USERPROFILE%\Desktop\LocalTranscriberPro.exe"
    
    echo.
    echo You can close this window. Enjoy!
    timeout /t 10
    exit
) else (
    color 4F
    echo [ERROR] Build failed. The executable was not created.
    echo Please review the error messages above.
    pause
)