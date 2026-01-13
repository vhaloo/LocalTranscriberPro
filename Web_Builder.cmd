@echo off
:: No global delayed expansion to avoid variable issues
setlocal
title Local Transcriber Pro - Web Installer (v10)
color 1F
cd /d "%~dp0"

echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - INSTALLER (v10: Stability Fix)
echo ===============================================================================
echo.
echo   [INFO] The installer has started.
echo   [INFO] If this window closes unexpectedly, please check your antivirus.
echo.

:: --- CONFIGURATION ---
set "WORK_DIR=LT_Build_Temp"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

:: --- STEP 1: FIND PYTHON (3.10 - 3.12) ---
echo   [1] Checking for Python...
set "PY_PATH="

:: Check Standard Locations
if exist "%ProgramFiles%\Python312\python.exe" set "PY_PATH=%ProgramFiles%\Python312\python.exe" & goto :FOUND_PY
if exist "%ProgramFiles%\Python311\python.exe" set "PY_PATH=%ProgramFiles%\Python311\python.exe" & goto :FOUND_PY
if exist "%ProgramFiles%\Python310\python.exe" set "PY_PATH=%ProgramFiles%\Python310\python.exe" & goto :FOUND_PY
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :FOUND_PY
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :FOUND_PY
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python310\python.exe" & goto :FOUND_PY
if exist "C:\Python312\python.exe" set "PY_PATH=C:\Python312\python.exe" & goto :FOUND_PY
if exist "C:\Python311\python.exe" set "PY_PATH=C:\Python311\python.exe" & goto :FOUND_PY

:: Check PATH (Simple check)
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('where python') do set "PY_PATH=%%i"
    goto :FOUND_PY
)

:: Install Python 3.11 if missing
echo   [!] Compatible Python (3.10-3.12) not found.
echo   [!] Auto-installing Python 3.11...
winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements
if %errorlevel% neq 0 (
    echo [ERROR] Winget install failed.
    pause
    exit /b 1
)
:: Assume default install path for Winget
set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

:FOUND_PY
echo   [OK] Using Python: %PY_PATH%

:: --- STEP 2: PREPARE WORKSPACE ---
echo.
echo   [2] Preparing Workspace...
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
cd "%WORK_DIR%"

:: --- STEP 3: DOWNLOAD ---
echo.
echo   [3] Downloading Source...
:: Hardcoded URL to prevent variable expansion errors
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip' -OutFile 'source.zip'"

if not exist "source.zip" (
    echo   [ERROR] Download failed.
    pause
    exit /b 1
)

echo   [4] Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

:: Find inner folder
dir /b /ad > dirs.txt
set /p INNER_DIR=<dirs.txt
cd "%INNER_DIR%"
del ..\dirs.txt

if not exist "requirements.txt" (
    echo [ERROR] Invalid source structure.
    pause
    exit /b 1
)

:: --- STEP 4: VIRTUAL ENV ---
echo.
echo   [5] Setting up AI Engine...
echo       - Creating venv...
"%PY_PATH%" -m venv venv
call venv\Scripts\activate.bat

echo       - Installing Dependencies...
python -m pip install --upgrade pip --no-cache-dir >nul 2>&1

:: GPU Check (Simple)
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir
) else (
    pip install torch torchvision torchaudio --no-cache-dir
)

pip install -r requirements.txt --no-cache-dir
pip install pyinstaller --no-cache-dir

:: --- FIX: LOCATE SITE-PACKAGES ---
echo.
echo   [FIX] Locating CustomTkinter...
for /f "tokens=*" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set "CTK_PATH=%%i"
echo         Found at: %CTK_PATH%

:: --- BUILD ---
echo.
echo   [6] Building Executable...
echo @echo off > build_run.bat
echo "venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean --name "LocalTranscriberPro_v0.9.6" --add-data "%CTK_PATH%;customtkinter" --add-data "src;src" --collect-all "whisper" --collect-all "openai_whisper" --hidden-import "scipy.special.cython_special" --hidden-import "scipy.integrate.lsoda" --exclude-module "tensorflow" main.py >> build_run.bat

call build_run.bat
if %errorlevel% neq 0 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

:: --- FINISH ---
echo.
echo ===============================================================================
echo   INSTALLATION SUCCESSFUL
echo ===============================================================================

if exist "dist\LocalTranscriberPro_*.exe" (
    taskkill /F /IM "LocalTranscriberPro.exe" >nul 2>&1
    copy /Y "dist\LocalTranscriberPro_*.exe" "%DEST_EXE%" >nul
    echo   [DONE] App installed to Desktop.
    echo   You can close this window.
    timeout /t 15
    exit
) else (
    echo [ERROR] EXE file not found in dist.
    pause
    exit /b 1
)
