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
set "NEEDS_RESTART=0"

:: 1.1 Visual C++ Redistributable (Required for PyTorch)
echo.
echo ... Checking Visual C++ Redistributable...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if %errorlevel% neq 0 (
    echo [MISSING] Visual C++ Redistributable. Installing via Winget...
    winget install --id "Microsoft.VCRedist.2015+.x64" --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 goto :ERROR
    set "NEEDS_RESTART=1"
) else (
    echo [OK] Visual C++ Redistributable found.
)

:: 1.2 FFmpeg (Required for Audio Processing)
echo.
echo ... Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo [MISSING] FFmpeg not found. Installing via Winget...
    winget install --id "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements
    if %errorlevel% neq 0 goto :ERROR
    set "NEEDS_RESTART=1"
) else (
    echo [OK] FFmpeg found.
)

:: 1.3 Python (Required for Building)
echo.
echo ... Checking Python...
py --version >nul 2>&1
if %errorlevel% neq 0 (
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [MISSING] Python not found. Auto-Installing...
        echo ... Downloading Python 3.12.8...
        powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile 'python_installer.exe'"
        
        echo ... Installing Python (Please accept Admin prompt if asked)...
        start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
        
        del python_installer.exe
        set "NEEDS_RESTART=1"
    ) else (
        echo [OK] Python found (via PATH).
    )
) else (
    echo [OK] Python found (via Launcher).
)

:: --- RESTART CHECK ---
if "%NEEDS_RESTART%"=="1" (
    color 6F
    echo.
    echo ===============================================================================
    echo   PREREQUISITES INSTALLED!
    echo ===============================================================================
    echo.
    echo   Windows needs to reload your environment variables (PATH).
    echo   Please CLOSE this window and RUN THIS SCRIPT AGAIN.
    echo.
    echo   (If you don't restart, the build will fail.)
    echo.
    pause
    exit
)

:: --- STEP 2: GPU CHECK & CONFIGURATION ---
echo.
echo [STEP 2/7] Checking for NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    color 2F
    echo [SUCCESS] NVIDIA GPU Detected! High-Performance Mode enabled.
    set "TORCH_URL=https://download.pytorch.org/whl/cu124"
) else (
    color 6F
    echo [WARNING] NVIDIA GPU not detected. Running in CPU MODE.
    echo ... Installing lighter CPU-only version - Saves Space ...
    set "TORCH_URL=https://download.pytorch.org/whl/cpu"
    timeout /t 3
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
    echo [ERROR] Download failed.
    goto :ERROR
)

:: Verify file size > 1KB
for %%I in (source.zip) do if %%~zI LSS 1000 (
    echo [ERROR] Downloaded zip is invalid (too small).
    goto :ERROR
)

echo ... Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"
cd LocalTranscriberPro-main

:: --- STEP 5: AI ENGINE ---
echo.
echo [STEP 5/7] Installing AI Engine...
py -m venv venv
if %errorlevel% neq 0 python -m venv venv
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual Environment creation failed.
    goto :ERROR
)

call venv\Scripts\activate

python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERROR] PIP upgrade failed. Check internet connection.
    goto :ERROR
)

echo ... Downloading PyTorch (Size depends on GPU/CPU mode)...
pip install torch torchvision torchaudio --index-url %TORCH_URL%
if %errorlevel% neq 0 goto :ERROR

pip install -r requirements.txt
pip install pyinstaller

:: --- STEP 6: COMPILATION ---
echo.
echo [STEP 6/7] Building Executable...
call build_exe.bat
if %errorlevel% neq 0 (
    echo [ERROR] Build script returned error code.
    goto :ERROR
)

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
    echo You can close this window.
    timeout /t 10
    exit
) else (
    echo [ERROR] EXE not found in dist.
    goto :ERROR
)

:ERROR
color 4F
echo.
echo ===============================================================================
echo   ERROR: INSTALLATION FAILED
echo ===============================================================================
echo.
echo   Something went wrong. Please check the error messages above.
echo   Common fixes:
echo   1. Check internet connection.
echo   2. Run this script as Administrator.
echo   3. Restart your computer.
echo.
pause
exit /b