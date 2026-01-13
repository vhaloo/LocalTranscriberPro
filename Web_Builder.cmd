@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Ultimate Web Installer
color 1F
cd /d "%~dp0"

:: --- CONFIGURATION ---
set "REPO_URL=https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip"
set "WORK_DIR=LT_Installer_Work"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

cls
echo.
echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - WEB INSTALLER
echo   (Auto-Updater & Builder)
echo ===============================================================================
echo.
echo   This script will:
echo   1. Check/Install System Prerequisites (Python 3.10+, FFmpeg, C++ Runtimes)
echo   2. Detect NVIDIA GPU for CUDA Acceleration
echo   3. Download the latest source code from GitHub
echo   4. Build a standalone executable optimized for your PC
echo.
echo   [NOTE] This process requires an active internet connection.
echo          The first run may take 5-10 minutes (downloading PyTorch ~2.5GB).
echo.
pause
cls

:: --- STEP 1: PREREQUISITES ---
echo [STEP 1/6] Checking System Environment...

:: 1.1 Visual C++ Redistributable (Critical for PyTorch)
echo    - Checking Visual C++ Redistributable...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if %errorlevel% neq 0 (
    echo      [MISSING] VC++ Redistributable. Attempting install via Winget...
    winget install --id "Microsoft.VCRedist.2015+.x64" --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        echo      [ERROR] Failed to install VC++ Redistributable.
        echo      Please manually install "VC_redist.x64.exe" from Microsoft.
        goto :ERROR
    )
    echo      [OK] Installed.
) else (
    echo      [OK] Found.
)

:: 1.2 FFmpeg
echo    - Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo      [MISSING] FFmpeg. Attempting install via Winget...
    winget install --id "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        echo      [ERROR] Failed to install FFmpeg.
        goto :ERROR
    )
    echo      [OK] Installed.
    set "PATH_UPDATE_NEEDED=1"
) else (
    echo      [OK] Found.
)

:: 1.3 Python
echo    - Checking Python...
set "PYTHON_CMD="
python --version >nul 2>&1
if %errorlevel% equ 0 set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if !errorlevel! equ 0 set "PYTHON_CMD=py"
)

if not defined PYTHON_CMD (
    echo      [MISSING] Python. Attempting auto-install (3.11)...
    winget install -e --id Python.Python.3.11 --scope machine --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        echo      [ERROR] Python installation failed.
        echo      Please install Python 3.10+ manually from python.org.
        goto :ERROR
    )
    set "PYTHON_CMD=python"
    set "PATH_UPDATE_NEEDED=1"
)
echo      [OK] Using !PYTHON_CMD!

:: Refresh Environment if needed (Hack to reload PATH without restart)
if defined PATH_UPDATE_NEEDED (
    echo    - Refreshing environment variables...
    call :REFRESH_ENV
)

:: --- STEP 2: GPU DETECTION ---
echo.
echo [STEP 2/6] Detecting Hardware...
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    color 2F
    echo    [SUCCESS] NVIDIA GPU Detected!
    echo    Build will include CUDA support for maximum performance.
) else (
    color 6F
    echo    [NOTICE] NVIDIA GPU not found.
    echo    Build will run in CPU MODE (Slower, but functional).
    timeout /t 2 >nul
    color 1F
)

:: --- STEP 3: WORKSPACE SETUP ---
echo.
echo [STEP 3/6] Preparing Workspace...
if exist "%WORK_DIR%" (
    echo    - Cleaning old build files...
    rmdir /s /q "%WORK_DIR%"
)
mkdir "%WORK_DIR%"
cd "%WORK_DIR%"

:: --- STEP 4: DOWNLOAD SOURCE ---
echo.
echo [STEP 4/6] Downloading latest source code...
echo    - Fetching %REPO_URL%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%REPO_URL%' -OutFile 'source.zip'"

if not exist "source.zip" (
    echo    [ERROR] Download failed. Check your internet connection.
    goto :ERROR
)

:: Check file size (sanity check)
for %%I in (source.zip) do if %%~zI LSS 1000 (
    echo    [ERROR] Downloaded file is too small (corruption/invalid URL).
    goto :ERROR
)

echo    - Extracting...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

:: Find extracted folder (handles main vs master naming)
for /d %%D in (*) do (
    if exist "%%D\main.py" (
        cd "%%D"
        goto :SOURCE_FOUND
    )
)
echo [ERROR] Could not find source code in extracted zip.
goto :ERROR

:SOURCE_FOUND
echo    [OK] Source extracted to %CD%

:: --- STEP 5: DEPENDENCIES & BUILD ---
echo.
echo [STEP 5/6] Setting up Build Environment...

echo    - Creating Virtual Environment...
!PYTHON_CMD! -m venv venv
if not exist "venv\Scripts\activate.bat" (
    echo    [ERROR] Failed to create venv.
    goto :ERROR
)
call venv\Scripts\activate

echo    - Upgrading PIP...
python -m pip install --upgrade pip >nul 2>&1

echo    - Installing PyTorch (This is the big download, please wait)...
:: Check for GPU again inside the venv context logic
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
) else (
    pip install torch torchvision torchaudio
)
if %errorlevel% neq 0 (
    echo    [ERROR] PyTorch installation failed.
    goto :ERROR
)

echo    - Installing App Dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [STEP 6/6] Compiling Executable...
:: Run the build script
if not exist "build_exe.bat" (
    echo    [ERROR] build_exe.bat not found in source.
    goto :ERROR
)
call build_exe.bat
if %errorlevel% neq 0 (
    echo    [ERROR] Build script returned an error.
    goto :ERROR
)

:: --- FINISH ---
echo.
echo ===============================================================================
echo   INSTALLATION COMPLETE!
echo ===============================================================================

:: Copy using wildcard to handle version changes
copy /Y "dist\LocalTranscriberPro_*.exe" "%DEST_EXE%" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Could not copy EXE to Desktop.
    echo check the 'dist' folder inside '%WORK_DIR%'.
    goto :ERROR
)

echo.
echo [SUCCESS] Local Transcriber Pro has been installed to your Desktop.
echo.
echo Cleaning up temporary files...
cd ..\..
:: Optional: Keep the build dir for debugging or speedier rebuilds?
:: rmdir /s /q "%WORK_DIR%"

echo.
echo Launching Application...
start "" "%DEST_EXE%"

timeout /t 5
exit

:ERROR
color 4F
echo.
echo ===============================================================================
echo   FATAL ERROR
echo ===============================================================================
echo.
echo   The installation could not complete.
echo   Please review the error messages above.
echo.
pause
exit /b 1

:REFRESH_ENV
:: Helper to refresh environment variables from registry without restart
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v PATH') do set "PATH=%%B;%PATH%"
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH') do set "PATH=%%B;%PATH%"
exit /b 0
