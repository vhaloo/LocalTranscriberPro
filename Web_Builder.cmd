@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Web Installer (v5)
color 1F
cd /d "%~dp0"

:: --- CRASH PROTECTION WRAPPER ::
:: This ensures the window stays open even if the script crashes.
if "%~1"=="__RUNNING_INTERNAL__" goto :MAIN_LOGIC

cmd /c "%~f0" __RUNNING_INTERNAL__
echo.
 echo ===============================================================================
 echo   INSTALLER STOPPED
 echo ===============================================================================
 echo   If you see an error above, please take a screenshot.
 echo.
pause
exit /b

:MAIN_LOGIC
:: ===============================================================================
::   REAL INSTALLER CODE STARTS HERE
:: ===============================================================================

call :LOG "Starting Installer v5..."

:: --- CONFIGURATION ---
set "REPO_URL=https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip"
set "WORK_DIR=LT_Build_Temp"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

echo.
 echo ===============================================================================
 echo   LOCAL TRANSCRIBER PRO - INSTALLER (Safe Mode)
 echo ===============================================================================
 echo.
 echo   [1] Checking System Prerequisites...

:: --- STEP 1: FIND PYTHON (3.10 - 3.12) ---
set "PY_PATH="

:: Check Standard Locations first (Program Files)
for %%V in (312 311 310) do (
    if exist "%ProgramFiles%\Python%%V\python.exe" set "PY_PATH=%ProgramFiles%\Python%%V\python.exe" & goto :VERIFY_PY
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" & goto :VERIFY_PY
    if exist "C:\Python%%V\python.exe" set "PY_PATH=C:\Python%%V\python.exe" & goto :VERIFY_PY
)

:: Check PATH (and validate version)
python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('where python') do set "TEMP_PY=%%i"
    
    :: Check if it is too new (>= 3.13)
    "!TEMP_PY!" -c "import sys; exit(1 if sys.version_info >= (3, 13) else 0)"
    if !errorlevel! equ 0 (
        set "PY_PATH=!TEMP_PY!"
        goto :VERIFY_PY
    ) else (
        echo   [WARNING] Detected Python is too new (Incompatible).
        echo             Found: !TEMP_PY!
    )
)

:: If we are here, we need to install Python 3.11
echo.
 echo   [!] No compatible Python (3.10-3.12) found.
 echo   [!] Attempting to auto-install Python 3.11...
call :LOG "Installing Python 3.11 via Winget..."

winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements
if !errorlevel! neq 0 (
    echo   [ERROR] Winget install failed.
    echo   Please manually install Python 3.11 from python.org.
    exit /b 1
)

:: Re-check after install
if exist "%ProgramFiles%\Python311\python.exe" set "PY_PATH=%ProgramFiles%\Python311\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not defined PY_PATH (
    echo   [ERROR] Python installed but not found. Restart PC?
    exit /b 1
)

:VERIFY_PY
call :LOG "Using Python: %PY_PATH%"
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
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%REPO_URL%' -OutFile 'source.zip'"
if not exist "source.zip" (
    echo   [ERROR] Download failed.
    exit /b 1
)

 echo   [4] Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

:: Find inner folder
for /d %%D in (*) do (
    if exist "%%D\requirements.txt" (
        cd "%%D"
        goto :BUILD_SETUP
    )
)
 echo   [ERROR] Source code structure invalid.
exit /b 1

:BUILD_SETUP
:: --- STEP 4: VIRTUAL ENV ---
 echo.
 echo   [5] Setting up AI Engine...
call :LOG "Creating venv..."

"%PY_PATH%" -m venv venv
if !errorlevel! neq 0 (
    echo   [ERROR] Failed to create venv.
    exit /b 1
)

call venv\Scripts\activate.bat

 echo       - Updating PIP...
python -m pip install --upgrade pip --no-cache-dir >nul 2>&1

 echo       - Installing Dependencies (No Cache)...
:: GPU CHECK
nvidia-smi >nul 2>&1
if !errorlevel! equ 0 (
    echo         [GPU] Installing CUDA Torch...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir
) else (
    echo         [CPU] Installing Standard Torch...
    pip install torch torchvision torchaudio --no-cache-dir
)

if !errorlevel! neq 0 (
    echo   [ERROR] Failed to install PyTorch.
    exit /b 1
)

pip install -r requirements.txt --no-cache-dir
pip install pyinstaller --no-cache-dir

:: --- STEP 5: BUILD ---
 echo.
 echo   [6] Building Executable...
if not exist "build_exe.bat" (
    echo   [ERROR] build_exe.bat missing.
    exit /b 1
)
call build_exe.bat
if !errorlevel! neq 0 (
    echo   [ERROR] Build script failed.
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
        exit /b 0
    )
)

 echo   [ERROR] Copy failed. File might be in 'dist' folder.
exit /b 1

:LOG
echo [%DATE% %TIME%] %~1 >> "%~dp0\install_log.txt"
exit /b 0