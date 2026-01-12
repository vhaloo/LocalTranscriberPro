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
echo   1. Check & Auto-Install Prerequisites (Python, FFmpeg, VCRedist)
echo   2. Detect NVIDIA GPU (CUDA)
echo   3. Download & Build the Application
echo   4. Launch it!
echo.
pause
cls

:: --- STEP 1: PREREQUISITES ---
echo [STEP 1/7] Checking System Prerequisites...

:: 1.1 Visual C++ Redistributable (Required for PyTorch)
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if %errorlevel% neq 0 (
    echo [MISSING] Visual C++ Redistributable. Installing via Winget...
    winget install --id "Microsoft.VCRedist.2015+.x64" --accept-source-agreements --accept-package-agreements
) else (
    echo [OK] Visual C++ Redistributable found.
)

:: 1.2 FFmpeg (Required for Audio Processing)
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [MISSING] FFmpeg not found. Installing via Winget...
    winget install --id "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements
    echo [INFO] Refreshing environment...
    call refreshenv 2>nul
) else (
    echo [OK] FFmpeg found.
)

:: 1.3 Python (Required for Building)
py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [MISSING] Python not found. Auto-Installing...
    echo ... Downloading Python 3.12.8...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile 'python_installer.exe'"
    
    echo ... Installing Python (Please accept Admin prompt if asked)...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    del python_installer.exe
    echo [INFO] Refreshing environment...
    call refreshenv 2>nul
) else (
    echo [OK] Python found.
)

:: --- STEP 2: GPU CHECK ---
echo.
echo [STEP 2/7] Checking for NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    color 2F
    echo [SUCCESS] NVIDIA GPU Detected!
    echo          High-Performance Mode (CUDA) will be enabled.
) else (
    color 6F
    echo [WARNING] NVIDIA GPU not detected or drivers missing.
    echo.
    echo The app will run in CPU MODE (Slower).
    echo.
    echo To enable GPU acceleration later:
    echo 1. Ensure you have an NVIDIA card.
    echo 2. Install drivers: https://www.nvidia.com/Download/index.aspx
    echo 3. Install CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
    echo.
    echo Press any key to continue with CPU mode...
    pause
    color 1F
)

:: --- STEP 3: WORKSPACE ---
echo.
echo [STEP 3/7] Preparing Workspace...
if exist "LT_Build" (
    echo ... Cleaning old build files...
    rmdir /s /q "LT_Build"
)
mkdir "LT_Build"
cd LT_Build

:: --- STEP 4: DOWNLOAD ---
echo.
echo [STEP 4/7] Downloading Source Code...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip' -OutFile 'source.zip'"

if not exist "source.zip" (
    color 4F
    echo [ERROR] Download failed. Check internet connection.
    pause
    exit /b
)

echo ... Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"
cd LocalTranscriberPro-main

:: --- STEP 5: AI ENGINE ---
echo.
echo [STEP 5/7] Installing AI Engine (Deep Learning Libraries)...
echo ... Creating virtual environment...
py -m venv venv
call venv\Scripts\activate

python -m pip install --upgrade pip
echo ... Downloading PyTorch (approx 2.5GB)...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

echo ... Installing App Requirements...
pip install -r requirements.txt
pip install pyinstaller

:: --- STEP 6: COMPILATION ---
echo.
echo [STEP 6/7] Building Executable...
call build_exe.bat

:: --- STEP 7: FINALIZE ---
if exist "dist\LocalTranscriberPro_v0.9.6.exe" (
    cls
    color 2F
    echo ===============================================================================
    echo   INSTALLATION COMPLETE!
    echo ===============================================================================
    echo.
    echo [SUCCESS] Moving app to Desktop...
    copy /Y "dist\LocalTranscriberPro_v0.9.6.exe" "%USERPROFILE%\Desktop\LocalTranscriberPro.exe"
    
    echo.
    echo [INFO] Cleanup...
    cd ..\..
    :: rmdir /s /q "LT_Build"
    
    echo.
    echo [LAUNCH] Starting Local Transcriber Pro...
    start "" "%USERPROFILE%\Desktop\LocalTranscriberPro.exe"
    
    echo.
    timeout /t 10
    exit
) else (
    color 4F
    echo [ERROR] Build failed. Review output above.
    pause
)