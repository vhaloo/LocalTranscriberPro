@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Web Installer (v16: Diarization)
color 1F
cd /d "%~dp0"

:: --- LOGGING CONFIGURATION ---
set "LOG_FILE=%USERPROFILE%\Desktop\LT_Install_Log.txt"
echo Installer started at %DATE% %TIME% > "%LOG_FILE%"

:: Helper for logging
set "LOG=echo"
set "LOGFILE_APPEND=>> "%LOG_FILE%""

:: Macro to log and display
(
  echo ===============================================================================
  echo   LOCAL TRANSCRIBER PRO - INSTALLER (v16: Diarization)
  echo ===============================================================================
  echo.
  echo   [INFO] Logs are being saved to: %LOG_FILE%
) | tee
:: We can't use 'tee' in standard batch, so we duplicate manually or use redirection blocks.

echo [INFO] Installer started. >> "%LOG_FILE%"

:: --- CONFIGURATION ---
set "WORK_DIR=LT_Build_Temp"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

echo [1] Checking System Prerequisites...
echo [1] Checking System Prerequisites... >> "%LOG_FILE%"

:: --- STEP 1: FIND PYTHON ---
set "PY_PATH="
:: Check Standard Locations
if exist "%ProgramFiles%\Python312\python.exe" set "PY_PATH=%ProgramFiles%\Python312\python.exe" & goto :FOUND_PY
if exist "%ProgramFiles%\Python311\python.exe" set "PY_PATH=%ProgramFiles%\Python311\python.exe" & goto :FOUND_PY
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :FOUND_PY
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :FOUND_PY

python --version >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('where python') do set "PY_PATH=%%i"
    goto :FOUND_PY
)

echo [ERROR] Compatible Python not found. >> "%LOG_FILE%"
echo [ERROR] Compatible Python not found.
pause
exit /b 1

:FOUND_PY
echo [OK] Using Python: !PY_PATH!
echo [OK] Using Python: !PY_PATH! >> "%LOG_FILE%"

:: --- STEP 2: PREPARE WORKSPACE ---
echo [2] Preparing Workspace... >> "%LOG_FILE%"
echo [2] Preparing Workspace...
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
cd "%WORK_DIR%"

:: --- STEP 3: DOWNLOAD ---
echo [3] Downloading Source... >> "%LOG_FILE%"
echo [3] Downloading Source...
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip' -OutFile 'source.zip'"
if not exist "source.zip" (
    echo [ERROR] Download failed. >> "%LOG_FILE%"
    echo [ERROR] Download failed.
    pause
    exit /b 1
)

echo [4] Extracting... >> "%LOG_FILE%"
echo [4] Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

:: Find inner folder
dir /b /ad > dirs.txt
set /p INNER_DIR=<dirs.txt
cd "!INNER_DIR!"
del ..\dirs.txt

:: --- STEP 4: VIRTUAL ENV ---
echo [5] Setting up AI Engine... >> "%LOG_FILE%"
echo [5] Setting up AI Engine...
"!PY_PATH!" -m venv venv
call venv\Scripts\activate.bat

echo     - Installing Dependencies...
echo     - Installing Dependencies... >> "%LOG_FILE%"
python -m pip install --upgrade pip --no-cache-dir >> "%LOG_FILE%" 2>&1

:: GPU Check
nvidia-smi >nul 2>&1
if !errorlevel! equ 0 (
    echo [GPU] Detected. Installing CUDA Torch... >> "%LOG_FILE%"
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir >> "%LOG_FILE%" 2>&1
) else (
    echo [CPU] No GPU. Installing CPU Torch... >> "%LOG_FILE%"
    pip install torch torchvision torchaudio --no-cache-dir >> "%LOG_FILE%" 2>&1
)

pip install -r requirements.txt --no-cache-dir >> "%LOG_FILE%" 2>&1
pip install pyinstaller --no-cache-dir >> "%LOG_FILE%" 2>&1
pip install tbb --no-cache-dir >> "%LOG_FILE%" 2>&1

:: --- FIX: LOCATE SITE-PACKAGES ---
echo [FIX] Locating CustomTkinter... >> "%LOG_FILE%"
echo [FIX] Locating CustomTkinter...
for /f "tokens=*" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set "CTK_PATH=%%i"
echo Found at: !CTK_PATH! >> "%LOG_FILE%"

:: --- BUILD ---
echo [6] Building Executable... >> "%LOG_FILE%"
echo [6] Building Executable...
echo @echo off > build_run.bat
echo "venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean --name "LocalTranscriberPro_v0.9.12" --add-data "!CTK_PATH!;customtkinter" --add-data "src;src" --collect-all "whisper" --collect-all "openai_whisper" --collect-all "tbb" --collect-all "numba" --collect-all "torch" --collect-all "torchaudio" --collect-all "scipy" --collect-all "yt_dlp" --collect-all "tkinterdnd2" --collect-all "certifi" --collect-all "speechbrain" --collect-all "sklearn" --hidden-import "scipy.special.cython_special" --hidden-import "scipy.integrate.lsoda" --hidden-import "sklearn.utils._cython_blas" --hidden-import "sklearn.neighbors.typedefs" --hidden-import "sklearn.neighbors.quad_tree" --hidden-import "sklearn.tree._utils" --exclude-module "tensorflow" main.py >> build_run.bat

call build_run.bat >> "%LOG_FILE%" 2>&1

if !errorlevel! neq 0 (
    echo [ERROR] Build failed. Check Desktop log.
    echo [ERROR] Build failed. >> "%LOG_FILE%"
    pause
    exit /b 1
)

:: --- FINISH & INTEGRITY CHECK ---
echo.
echo ===============================================================================
echo   INSTALLATION SUCCESSFUL
echo ===============================================================================

:: Initialize SIZE to 0 to prevent crash if file is missing
set "SIZE=0"
if exist "dist\LocalTranscriberPro_*.exe" (
    for %%F in ("dist\LocalTranscriberPro_*.exe") do set "SIZE=%%~zF"
)

echo Built File Size: !SIZE! bytes >> "%LOG_FILE%"
echo Built File Size: !SIZE! bytes

:: Check if smaller than 100MB (100,000,000 bytes)
if !SIZE! LSS 100000000 (
    echo [ERROR] The built file is suspiciously small or missing. >> "%LOG_FILE%"
    echo [ERROR] The built file is suspiciously small or missing.
    echo         This usually means PyInstaller crashed or ran out of space.
    echo         Please check the log file on your Desktop.
    pause
    exit /b 1
)

echo [INSTALL] Updating Desktop app... >> "%LOG_FILE%"
echo [INSTALL] Updating Desktop app...

taskkill /F /IM "LocalTranscriberPro.exe" >nul 2>&1
copy /Y /B "dist\LocalTranscriberPro_*.exe" "%DEST_EXE%" >nul

if exist "%DEST_EXE%" (
    echo [SUCCESS] App installed to Desktop. >> "%LOG_FILE%"
    echo [SUCCESS] App installed to Desktop.
    echo.
    echo You can close this window.
    pause
    exit
) else (
    echo [ERROR] Failed to copy file to Desktop. >> "%LOG_FILE%"
    echo [ERROR] Failed to copy file to Desktop.
    pause
    exit /b 1
)
