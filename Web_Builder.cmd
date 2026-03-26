@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro Installer (v1.1)
color 0B
cd /d "%~dp0"

:: --- LOGGING ---
set "LOG_FILE=%USERPROFILE%\Desktop\LT_Install_Log.txt"
echo Installer started at %DATE% %TIME% > "%LOG_FILE%"

echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - ULTIMATE INSTALLER (v1.1)
echo ===============================================================================
echo.
echo   This installer will automatically setup:
echo   - Python 64-bit (Required for AI)
echo   - FFmpeg (for audio processing)
echo   - Visual C++ Redistributable (for AI models)
echo   - High-Performance CUDA components (if NVIDIA GPU is found)
echo.
echo   [INFO] Logs are being saved to: %LOG_FILE%
echo.
echo   Ready to install.
pause
cls

:: --- ADMIN CHECK ---
echo [0/6] Verifying Permissions...
net session >nul 2>&1
if !errorlevel! neq 0 (
    color 0E
    echo [WARNING] Not running as Administrator. 
    echo           Prerequisite installation may fail.
    echo           If the script fails, right-click and "Run as Administrator".
    echo.
    timeout /t 5
)

:: --- STEP 1: PREREQUISITES ---
echo [1/6] Checking Prerequisites...
echo [1] Checking Prerequisites... >> "%LOG_FILE%"

:: Check for winget
where winget >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] 'winget' is missing. This script requires 'App Installer' from the Microsoft Store.
    echo         Please install it here: https://apps.microsoft.com/store/detail/app-installer/9NBLGGH4NNS1
    pause
    exit /b 1
)

set "WINGET_ARGS=--accept-source-agreements --accept-package-agreements"

:: Check FFmpeg
where ffmpeg >nul 2>&1
if !errorlevel! neq 0 (
    echo [MISSING] FFmpeg. Installing...
    winget install --id "Gyan.FFmpeg" !WINGET_ARGS!
    if !errorlevel! neq 0 echo [WARN] FFmpeg install might have failed. >> "%LOG_FILE%"
) else (
    echo [OK] FFmpeg found.
)

:: Check VCRedist
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if !errorlevel! neq 0 (
    echo [MISSING] Visual C++ Redist. Installing...
    winget install --id "Microsoft.VCRedist.2015+.x64" !WINGET_ARGS!
) else (
    echo [OK] Visual C++ Redist found.
)

:: Check Python (MUST BE 64-BIT)
set "PY_CMD="
set "PYTHON_FOUND=0"

:: Check 'py' launcher
py -0 >nul 2>&1
if !errorlevel! equ 0 (
    py -c "import sys; exit(0 if sys.maxsize > 2**32 else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py"
        set "PYTHON_FOUND=1"
    )
)

:: Check 'python' command
if !PYTHON_FOUND! equ 0 (
    python -c "import sys; exit(0 if sys.maxsize > 2**32 else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=python"
        set "PYTHON_FOUND=1"
    )
)

if !PYTHON_FOUND! equ 0 (
    echo [MISSING] 64-bit Python not found. Auto-Installing...
    echo Downloading Python 3.12.8...
    powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile 'python_installer.exe'"
    
    echo Installing Python silently...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    
    echo.
    echo [IMPORTANT] Python installed. Windows needs to refresh your PATH.
    echo Please CLOSE this window and RUN THIS SCRIPT AGAIN.
    pause
    exit /b
)

echo [OK] 64-bit Python found: !PY_CMD!

echo.
echo [2/6] Preparing Workspace...
if exist "LT_Temp" rmdir /s /q "LT_Temp"
mkdir "LT_Temp"
cd "LT_Temp"

echo.
echo [3/6] Downloading Source Code...
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip' -OutFile 'source.zip'"
if not exist "source.zip" (
    echo [ERROR] Download failed. Check your internet connection.
    pause
    exit /b 1
)
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

dir /b /ad > dirs.txt
set /p INNER_DIR=<dirs.txt
cd "!INNER_DIR!"
del ..\dirs.txt

echo.
echo [4/6] Setting up AI Engine...
"!PY_CMD!" -m venv venv
set "VENV_PYTHON=venv\Scripts\python.exe"
set "VENV_PIP=venv\Scripts\pip.exe"

echo ... Updating Pip...
"!VENV_PYTHON!" -m pip install --upgrade pip --no-cache-dir >> "%LOG_FILE%" 2>&1

nvidia-smi >nul 2>&1
if !errorlevel! equ 0 (
    echo [GPU] NVIDIA GPU Detected! Installing CUDA optimized AI...
    "!VENV_PIP!" install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir
) else (
    echo [CPU] No NVIDIA GPU detected. Installing standard AI...
    "!VENV_PIP!" install torch torchvision torchaudio --no-cache-dir
)

echo     - Installing requirements...
"!VENV_PIP!" install -r requirements.txt --no-cache-dir >> "%LOG_FILE%" 2>&1
"!VENV_PIP!" install pyinstaller tbb --no-cache-dir >> "%LOG_FILE%" 2>&1

echo.
echo [5/6] Building Application (This takes a few minutes)...
for /f "usebackq tokens=*" %%i in (`"!VENV_PYTHON!" -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"`) do set "CTK_PATH=%%i"

set "APP_NAME=LocalTranscriberPro_v1.1"

echo ... Running PyInstaller...
"!VENV_PYTHON!" -m PyInstaller --noconsole --onefile --clean ^
    --name "!APP_NAME!" ^
    --add-data "!CTK_PATH!;customtkinter" ^
    --add-data "src;src" ^
    --collect-all "whisper" ^
    --collect-all "openai_whisper" ^
    --collect-all "tbb" ^
    --collect-all "numba" ^
    --collect-all "torch" ^
    --collect-all "torchaudio" ^
    --collect-all "scipy" ^
    --collect-all "yt_dlp" ^
    --collect-all "tkinterdnd2" ^
    --collect-all "certifi" ^
    --collect-all "speechbrain" ^
    --collect-all "sklearn" ^
    --collect-all "soundfile" ^
    --hidden-import "scipy.special.cython_special" ^
    --hidden-import "scipy.integrate.lsoda" ^
    --hidden-import "sklearn.utils._cython_blas" ^
    --hidden-import "sklearn.neighbors.typedefs" ^
    --hidden-import "sklearn.neighbors.quad_tree" ^
    --hidden-import "sklearn.tree._utils" ^
    --exclude-module "tensorflow" ^
    main.py >> "%LOG_FILE%" 2>&1

if !errorlevel! neq 0 (
    echo [ERROR] Build failed. Check Desktop log.
    goto :ERROR
)

echo.
echo [6/6] Finalizing Installation...
set "SIZE=0"
if exist "dist\!APP_NAME!.exe" (
    for %%F in ("dist\!APP_NAME!.exe") do set "SIZE=%%~zF"
)

if !SIZE! LSS 100000000 (
    echo [ERROR] The built file is too small. >> "%LOG_FILE%"
    goto :ERROR
)

set "DEST_DIR=%USERPROFILE%\Desktop\Local Transcriber Pro"
if not exist "!DEST_DIR!" mkdir "!DEST_DIR!"

taskkill /F /IM "!APP_NAME!.exe" >nul 2>&1
copy /Y /B "dist\!APP_NAME!.exe" "!DEST_DIR!\!APP_NAME!.exe" >nul

powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Local Transcriber Pro.lnk'); $Shortcut.TargetPath = '!DEST_DIR!\!APP_NAME!.exe'; $Shortcut.WorkingDirectory = '!DEST_DIR!'; $Shortcut.Save()"

if exist "!DEST_DIR!\!APP_NAME!.exe" (
    color 2F
    echo ===============================================================================
    echo   INSTALLATION SUCCESSFUL!
    echo ===============================================================================
    echo.
    echo A folder and a shortcut have been created on your Desktop.
    echo Starting the app now...
    cd ..\..
    start "" "!DEST_DIR!\!APP_NAME!.exe"
    rmdir /s /q "LT_Temp"
    timeout /t 5
    exit
) else (
    goto :ERROR
)

:ERROR
color 4F
echo.
echo ===============================================================================
echo   ERROR: INSTALLATION FAILED
echo ===============================================================================
echo.
echo   Check the log file on your Desktop: LT_Install_Log.txt
echo.
pause
exit /b 1
