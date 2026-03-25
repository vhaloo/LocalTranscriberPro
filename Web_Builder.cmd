@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro Installer (v1.0)
color 0B
cd /d "%~dp0"

set "LOG_FILE=%USERPROFILE%\Desktop\LT_Install_Log.txt"
echo Installer started at %DATE% %TIME% > "%LOG_FILE%"

echo ===============================================================================
echo   LOCAL TRANSCRIBER PRO - ULTIMATE INSTALLER (v1.0)
echo ===============================================================================
echo.
echo   This installer will automatically setup:
echo   - Python (if missing)
echo   - FFmpeg (for audio processing)
echo   - Visual C++ Redistributable (for AI models)
echo   - High-Performance CUDA components (if NVIDIA GPU is found)
echo.
echo   [INFO] Logs are being saved to: %LOG_FILE%
echo.
echo   Ready to install.
pause
cls

echo [1/6] Checking Prerequisites...
echo [1] Checking Prerequisites... >> "%LOG_FILE%"
set "WINGET_ARGS=--accept-source-agreements --accept-package-agreements --silent"

:: Check FFmpeg
where ffmpeg >nul 2>&1
if !errorlevel! neq 0 (
    echo [MISSING] FFmpeg. Installing via Winget...
    echo [MISSING] FFmpeg. Installing... >> "%LOG_FILE%"
    winget install --id "Gyan.FFmpeg" !WINGET_ARGS!
) else (
    echo [OK] FFmpeg found.
)

:: Check VCRedist
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" >nul 2>&1
if !errorlevel! neq 0 (
    echo [MISSING] Visual C++ Redist. Installing via Winget...
    winget install --id "Microsoft.VCRedist.2015+.x64" !WINGET_ARGS!
) else (
    echo [OK] Visual C++ Redist found.
)

:: Check Python
set "PY_CMD="
python --version >nul 2>&1
if !errorlevel! equ 0 set "PY_CMD=python"
py --version >nul 2>&1
if !errorlevel! equ 0 set "PY_CMD=py"
if exist "%ProgramFiles%\Python312\python.exe" set "PY_CMD=%ProgramFiles%\Python312\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if "!PY_CMD!"=="" (
    echo [MISSING] Python. Auto-installing Python 3.12...
    echo [MISSING] Python. Auto-installing Python 3.12... >> "%LOG_FILE%"
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile 'python_installer.exe'"
    echo Installing Python silently... Please wait...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
    
    echo.
    echo [INFO] Python installed. We must restart the installer to refresh variables.
    echo Please close this window and run the installer file again.
    pause
    exit /b
)

echo [OK] Python found: !PY_CMD!
echo [OK] Python found: !PY_CMD! >> "%LOG_FILE%"

echo.
echo [2/6] Preparing Workspace...
echo [2] Preparing Workspace... >> "%LOG_FILE%"
if exist "LT_Temp" rmdir /s /q "LT_Temp"
mkdir "LT_Temp"
cd "LT_Temp"

echo.
echo [3/6] Downloading Source Code...
echo [3] Downloading Source Code... >> "%LOG_FILE%"
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip' -OutFile 'source.zip'"
if not exist "source.zip" (
    echo [ERROR] Download failed. >> "%LOG_FILE%"
    echo [ERROR] Download failed. Check your internet connection.
    pause
    exit /b 1
)
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

:: Find inner folder dynamically
dir /b /ad > dirs.txt
set /p INNER_DIR=<dirs.txt
cd "!INNER_DIR!"
del ..\dirs.txt

echo.
echo [4/6] Setting up AI Engine...
echo [4] Setting up AI Engine... >> "%LOG_FILE%"
"!PY_CMD!" -m venv venv
call venv\Scripts\activate.bat

python -m pip install --upgrade pip --no-cache-dir >> "%LOG_FILE%" 2>&1

:: GPU Check
nvidia-smi >nul 2>&1
if !errorlevel! equ 0 (
    echo [GPU] NVIDIA GPU Detected! Installing CUDA optimized AI...
    echo [GPU] Detected. Installing CUDA Torch... >> "%LOG_FILE%"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir >> "%LOG_FILE%" 2>&1
) else (
    echo [CPU] No NVIDIA GPU detected. Installing standard AI...
    echo [CPU] No GPU. Installing CPU Torch... >> "%LOG_FILE%"
    pip install torch torchvision torchaudio --no-cache-dir >> "%LOG_FILE%" 2>&1
)

echo     - Installing requirements...
pip install -r requirements.txt --no-cache-dir >> "%LOG_FILE%" 2>&1
pip install pyinstaller tbb --no-cache-dir >> "%LOG_FILE%" 2>&1

echo.
echo [5/6] Building Application (This takes a few minutes)...
echo [5] Building Application... >> "%LOG_FILE%"

for /f "tokens=*" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set "CTK_PATH=%%i"

set "APP_NAME=LocalTranscriberPro_v1.0"

echo @echo off > build_run.bat
echo "venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean --name "!APP_NAME!" --add-data "!CTK_PATH!;customtkinter" --add-data "src;src" --collect-all "whisper" --collect-all "openai_whisper" --collect-all "tbb" --collect-all "numba" --collect-all "torch" --collect-all "torchaudio" --collect-all "scipy" --collect-all "yt_dlp" --collect-all "tkinterdnd2" --collect-all "certifi" --collect-all "speechbrain" --collect-all "sklearn" --collect-all "soundfile" --hidden-import "scipy.special.cython_special" --hidden-import "scipy.integrate.lsoda" --hidden-import "sklearn.utils._cython_blas" --hidden-import "sklearn.neighbors.typedefs" --hidden-import "sklearn.neighbors.quad_tree" --hidden-import "sklearn.tree._utils" --exclude-module "tensorflow" main.py >> build_run.bat

call build_run.bat >> "%LOG_FILE%" 2>&1

if !errorlevel! neq 0 (
    echo [ERROR] Build failed. Check Desktop log.
    pause
    exit /b 1
)

echo.
echo [6/6] Finalizing Installation...
set "SIZE=0"
if exist "dist\!APP_NAME!.exe" (
    for %%F in ("dist\!APP_NAME!.exe") do set "SIZE=%%~zF"
)
echo Built File Size: !SIZE! bytes >> "%LOG_FILE%"

if !SIZE! LSS 100000000 (
    color 4F
    echo [ERROR] The built file is suspiciously small or missing.
    echo         This usually means PyInstaller crashed or ran out of space.
    echo         Please check the log file on your Desktop.
    pause
    exit /b 1
)

set "DEST_DIR=%USERPROFILE%\Desktop\Local Transcriber Pro"
if not exist "!DEST_DIR!" mkdir "!DEST_DIR!"

taskkill /F /IM "!APP_NAME!.exe" >nul 2>&1
copy /Y /B "dist\!APP_NAME!.exe" "!DEST_DIR!\!APP_NAME!.exe" >nul

:: Create Desktop Shortcut using PowerShell
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Local Transcriber Pro.lnk'); $Shortcut.TargetPath = '!DEST_DIR!\!APP_NAME!.exe'; $Shortcut.WorkingDirectory = '!DEST_DIR!'; $Shortcut.Save()"

if exist "!DEST_DIR!\!APP_NAME!.exe" (
    color 2F
    echo.
    echo ===============================================================================
    echo   INSTALLATION SUCCESSFUL!
    echo ===============================================================================
    echo.
    echo A folder and a shortcut have been created on your Desktop.
    echo Starting the app now...
    
    cd ..\..
    start "" "!DEST_DIR!\!APP_NAME!.exe"
    
    :: Cleanup
    rmdir /s /q "LT_Temp"
    
    timeout /t 5
    exit
) else (
    color 4F
    echo [ERROR] Failed to copy the application to your Desktop.
    pause
)
