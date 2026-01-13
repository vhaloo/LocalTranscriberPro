@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Web Installer (v9)
color 1F
cd /d "%~dp0"

echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - INSTALLER (v9: Linear Mode)
echo ===============================================================================
echo.

:: --- CONFIGURATION ---
set "REPO_URL=https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip"
set "WORK_DIR=LT_Build_Temp"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

:: DEBUG CHECK
if "%REPO_URL%"=="" (
    echo [CRITICAL ERROR] Variables failed to set.
    pause
    exit /b 1
)
echo [DEBUG] URL: %REPO_URL%
echo [DEBUG] WORK: %WORK_DIR%
echo.

echo   [1] Checking System Prerequisites...

:: --- STEP 1: FIND PYTHON (3.10 - 3.12) ---
set "PY_PATH="

:: Check Standard Locations first
for %%V in (312 311 310) do (
    if exist "%ProgramFiles%\Python%%V\python.exe" set "PY_PATH=%ProgramFiles%\Python%%V\python.exe" & goto :VERIFY_PY
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" & goto :VERIFY_PY
    if exist "C:\Python%%V\python.exe" set "PY_PATH=C:\Python%%V\python.exe" & goto :VERIFY_PY
)

:: Check PATH
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('where python') do set "TEMP_PY=%%i"
    "!TEMP_PY!" -c "import sys; exit(1 if sys.version_info >= (3, 13) else 0)"
    if !errorlevel! equ 0 (
        set "PY_PATH=!TEMP_PY!"
        goto :VERIFY_PY
    )
)

:: Auto-Install Python 3.11 if missing
echo.
echo   [!] Compatible Python (3.10-3.12) not found.
echo   [!] Attempting to auto-install Python 3.11...
winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements
if !errorlevel! neq 0 (
    echo   [ERROR] Winget install failed.
    pause
    exit /b 1
)

:: Re-check
if exist "%ProgramFiles%\Python311\python.exe" set "PY_PATH=%ProgramFiles%\Python311\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not defined PY_PATH (
    echo   [ERROR] Python installed but not found. Restart PC?
    pause
    exit /b 1
)

:VERIFY_PY
echo   [OK] Using Python: %PY_PATH%

:: --- STEP 2: PREPARE WORKSPACE ---
echo.
echo   [2] Preparing Workspace...
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to create workspace "%WORK_DIR%".
    pause
    exit /b 1
)
cd "%WORK_DIR%"

:: --- STEP 3: DOWNLOAD ---
echo.
echo   [3] Downloading Source...
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%REPO_URL%' -OutFile 'source.zip'"
if not exist "source.zip" (
    echo   [ERROR] Download failed.
    echo   URL was: %REPO_URL%
    pause
    exit /b 1
)

echo   [4] Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

for /d %%D in (*) do (
    if exist "%%D\requirements.txt" (
        cd "%%D"
        goto :BUILD_SETUP
    )
)
echo   [ERROR] Source code structure invalid.
pause
exit /b 1

:BUILD_SETUP
:: --- STEP 4: VIRTUAL ENV ---
echo.
echo   [5] Setting up AI Engine...
echo       - Creating venv...

"%PY_PATH%" -m venv venv
if !errorlevel! neq 0 (
    echo   [ERROR] Failed to create venv.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo       - Updating PIP...
python -m pip install --upgrade pip --no-cache-dir >nul 2>&1

echo       - Installing Dependencies...
:: GPU CHECK
nvidia-smi >nul 2>&1
if !errorlevel! equ 0 (
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir
) else (
    pip install torch torchvision torchaudio --no-cache-dir
)

pip install -r requirements.txt --no-cache-dir
pip install pyinstaller --no-cache-dir

:: --- FIX: LOCATE SITE-PACKAGES PRECISELY ---
echo.
echo   [FIX] Locating CustomTkinter...

:: Find the EXACT folder of customtkinter
for /f "tokens=*" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set "CTK_PATH=%%i"

if not exist "!CTK_PATH!" (
    echo   [ERROR] Could not locate customtkinter path.
    echo   Reported: !CTK_PATH!
    pause
    exit /b 1
)
echo         Found at: !CTK_PATH!

:: --- BUILD COMMAND GENERATION ---
echo @echo off > build_dynamic.bat
echo cd /d "%%~dp0" >> build_dynamic.bat
echo echo Starting PyInstaller... >> build_dynamic.bat
echo "venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean --name "LocalTranscriberPro_v0.9.6" --add-data "!CTK_PATH!;customtkinter" --add-data "src;src" --collect-all "whisper" --collect-all "openai_whisper" --hidden-import "scipy.special.cython_special" --hidden-import "scipy.integrate.lsoda" --exclude-module "tensorflow" main.py >> build_dynamic.bat

:: --- STEP 5: BUILD ---
echo.
echo   [6] Building Executable (Dynamic)...
call build_dynamic.bat
if !errorlevel! neq 0 (
    echo   [ERROR] Build script failed.
    pause
    exit /b 1
)

:: --- STEP 6: FINISH ---
echo.
echo ===============================================================================
echo   INSTALLATION SUCCESSFUL
echo ===============================================================================

if exist "dist\LocalTranscriberPro_*.exe" (
    echo   [INSTALL] Moving to Desktop...
    taskkill /F /IM "LocalTranscriberPro.exe" >nul 2>&1
    
    copy /Y "dist\LocalTranscriberPro_*.exe" "%DEST_EXE%" >nul
    
    if exist "%DEST_EXE%" (
        echo.
        echo   [DONE] App is ready on your Desktop!
        echo   You can close this window.
        timeout /t 10
        exit
    )
)

echo   [ERROR] Copy failed. File might be in 'dist' folder.
pause
exit /b 1