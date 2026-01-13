@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Ultimate Installer (v2)
color 1F
cd /d "%~dp0"

:: Log everything to a file
call :LOG "Starting Installer..."

:: --- CONFIGURATION ---
set "REPO_URL=https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip"
set "WORK_DIR=LT_Build_Temp"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

echo.
echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - INSTALLER
echo ===============================================================================
echo.

echo   [1] Checking System Prerequisites...
call :LOG "Checking Prerequisites"

:: --- FIND PYTHON ---
set "PY_PATH="

:: Check PATH first
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('where python') do (
        set "PY_PATH=%%i"
        goto :FOUND_PYTHON
    )
)

:: Check common install locations if not in PATH
call :LOG "Python not in PATH. Searching standard locations..."
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_PATH=%%D\python.exe"
        goto :FOUND_PYTHON
    )
)
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_PATH=%%D\python.exe"
        goto :FOUND_PYTHON
    )
)

:: If still not found, Install it
:INSTALL_PYTHON
echo   [!] Python not found. Installing Python 3.11...
call :LOG "Installing Python 3.11 via Winget..."
winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements
if %errorlevel% neq 0 (
    echo   [ERROR] Python installation failed.
    echo   Please install Python 3.10+ manually from python.org and restart this script.
    pause
    exit /b 1
)
:: Try to find it again after install
for /d %%D in ("%ProgramFiles%\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_PATH=%%D\python.exe"
        goto :FOUND_PYTHON
    )
)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_PATH=%%D\python.exe"
        goto :FOUND_PYTHON
    )
)

echo [ERROR] Could not find Python even after installation.
echo Please restart your computer and run this script again.
pause
exit /b 1

:FOUND_PYTHON
call :LOG "Using Python at: %PY_PATH%"
echo   [OK] Found Python: %PY_PATH%

:: --- CHECK GIT/FFMPEG ---
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo   [!] Installing FFmpeg...
    winget install --id "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements
)

:: --- PREPARE WORKSPACE ---
echo.

echo   [2] Preparing Workspace...
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
cd "%WORK_DIR%"

:: --- DOWNLOAD ---
echo.

echo   [3] Downloading Source...
call :LOG "Downloading from %REPO_URL%"
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%REPO_URL%' -OutFile 'source.zip'"
if not exist "source.zip" (
    echo   [ERROR] Download failed.
    pause
    exit /b 1
)

echo   [4] Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

:: Navigate to folder
for /d %%D in (*) do (
    if exist "%%D\requirements.txt" (
        cd "%%D"
        goto :BUILD_START
    )
)
echo   [ERROR] Invalid Source Structure.
pause
exit /b 1

:BUILD_START
:: --- VIRTUAL ENV ---
echo.

echo   [5] Setting up AI Engine...
call :LOG "Creating venv..."
"%PY_PATH%" -m venv venv
if not exist "venv\Scripts\activate.bat" (
    echo   [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

echo       - Updating PIP...
python -m pip install --upgrade pip >nul 2>&1

echo       - Installing PyTorch (GPU Check)...
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo         [GPU DETECTED] Installing CUDA support...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
) else (
    echo         [NO GPU] Installing CPU version...
    pip install torch torchvision torchaudio
)


echo       - Installing Dependencies...
pip install -r requirements.txt
pip install pyinstaller

:: --- COMPILE ---
echo.

echo   [6] Building Executable...
call :LOG "Running PyInstaller..."
if not exist "build_exe.bat" (
    echo   [ERROR] build_exe.bat missing.
    pause
    exit /b 1
)
call build_exe.bat

:: --- FINISH ---
echo.

echo ===============================================================================
echo   INSTALLATION COMPLETE
echo ===============================================================================

if exist "dist\LocalTranscriberPro_*.exe" (
    copy /Y "dist\LocalTranscriberPro_*.exe" "%DEST_EXE%" >nul
    echo   [SUCCESS] App installed to Desktop!
    echo.
    echo   You can close this window.
    timeout /t 10
    exit
) else (
    echo   [ERROR] Build failed. Check logs.
    pause
    exit /b 1
)

:LOG
echo [%DATE% %TIME%] %~1 >> "%~dp0\install_log.txt"
exit /b 0