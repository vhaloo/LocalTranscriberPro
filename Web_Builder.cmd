@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Web Installer (v4)
color 1F
cd /d "%~dp0"

call :LOG "Starting Installer v4..."

:: --- CONFIGURATION ---
set "REPO_URL=https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip"
set "WORK_DIR=LT_Build_Temp"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

echo.
echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - INSTALLER (Fixed for Py 3.14)
echo ===============================================================================
echo.
echo   [1] Checking System Prerequisites...

:: --- FIND COMPATIBLE PYTHON (3.10 - 3.12) ---
set "PY_PATH="

:: 1. Check for specific stable versions in standard paths first
for %%V in (312 311 310) do (
    for %%L in ("%ProgramFiles%\Python%%V\python.exe" "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" "C:\Python%%V\python.exe") do (
        if exist "%%~L" (
            set "PY_PATH=%%~L"
            goto :VERIFY_PYTHON
        )
    )
)

:: 2. Check PATH as fallback
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('where python') do (
        set "TEMP_PY=%%i"
        goto :CHECK_VERSION
    )
)
goto :INSTALL_PYTHON

:CHECK_VERSION
:: Check if the PATH python is too new (3.13+)
"%TEMP_PY%" -c "import sys; exit(1 if sys.version_info >= (3, 13) else 0)"
if %errorlevel% equ 0 (
    set "PY_PATH=%TEMP_PY%"
    goto :VERIFY_PYTHON
) else (
    echo   [WARNING] Detected Python is too new (Incompatible with AI libs).
    echo             Found: %TEMP_PY%
    echo             Searching for older version...
)

:INSTALL_PYTHON
if not defined PY_PATH (
    echo.
    echo   [!] Compatible Python (3.10-3.12) not found.
    echo   [!] Python 3.14/3.13 are NOT supported by PyTorch yet.
    echo.
    echo   Attempting to install Python 3.11 via Winget...
    call :LOG "Installing Python 3.11..."
    
    winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements
    
    :: Re-check standard paths
    if exist "%ProgramFiles%\Python311\python.exe" set "PY_PATH=%ProgramFiles%\Python311\python.exe"
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    
    if not defined PY_PATH (
        echo.
        echo   [ERROR] Could not install/find Python 3.11.
        echo   PLEASE MANUALY INSTALL PYTHON 3.11 or 3.12 from python.org.
        pause
        exit /b 1
    )
)

:VERIFY_PYTHON
call :LOG "Using Python: %PY_PATH%"
echo   [OK] Using Python: %PY_PATH%

:: --- WORKSPACE ---
echo.
echo   [2] Preparing Workspace...
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
cd "%WORK_DIR%"

:: --- DOWNLOAD ---
echo.
echo   [3] Downloading Source...
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
python -m pip install --upgrade pip --no-cache-dir >nul 2>&1

echo       - Installing PyTorch (GPU Check)...
echo         (Using --no-cache-dir to avoid permission errors)
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo         [GPU DETECTED] Installing CUDA support...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir
) else (
    echo         [NO GPU] Installing CPU version...
    pip install torch torchvision torchaudio --no-cache-dir
)

if %errorlevel% neq 0 (
    echo   [ERROR] PyTorch installation failed.
    echo   Possible causes: Python 3.14 incompatibility or Network.
    pause
    exit /b 1
)

echo       - Installing Dependencies...
pip install -r requirements.txt --no-cache-dir
pip install pyinstaller --no-cache-dir

:: Verify critical package
if not exist "venv\Lib\site-packages\customtkinter" (
    echo   [ERROR] Installation failed (customtkinter missing).
    pause
    exit /b 1
)

:: --- COMPILE ---
echo.
echo   [6] Building Executable...
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
    echo   [INSTALL] Updating Desktop...
    taskkill /F /IM "LocalTranscriberPro.exe" >nul 2>&1
    copy /Y "dist\LocalTranscriberPro_*.exe" "%DEST_EXE%" >nul
    
    if exist "%DEST_EXE%" (
        echo   [SUCCESS] App installed to: %DEST_EXE%
        timeout /t 10
        exit
    )
)

echo   [ERROR] Build failed. Check logs.
pause
exit /b 1

:LOG
echo [%DATE% %TIME%] %~1 >> "%~dp0\install_log.txt"
exit /b 0
