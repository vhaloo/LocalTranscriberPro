@echo off
setlocal
cd /d "%~dp0"
title Local Transcriber Pro - Web Installer (v12)
color 1F

:: --- LOGGING START ---
echo Installer started at %TIME% > install_log.txt
set LOGCMD=echo

%LOGCMD% ===============================================================================
%LOGCMD%   LOCAL TRANSCRIBER PRO - INSTALLER (v12: DLL Fix)
%LOGCMD% ===============================================================================

set "WORK_DIR=LT_Build_Temp"
set "DEST_EXE=%USERPROFILE%\Desktop\LocalTranscriberPro.exe"

%LOGCMD% [1] Checking System Prerequisites... >> install_log.txt

:: --- STEP 1: FIND PYTHON ---
set "PY_PATH="
if exist "%ProgramFiles%\Python312\python.exe" set "PY_PATH=%ProgramFiles%\Python312\python.exe" & goto :FOUND_PY
if exist "%ProgramFiles%\Python311\python.exe" set "PY_PATH=%ProgramFiles%\Python311\python.exe" & goto :FOUND_PY
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :FOUND_PY
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :FOUND_PY

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('where python') do set "PY_PATH=%%i"
    goto :FOUND_PY
)

%LOGCMD% [ERROR] Compatible Python not found. >> install_log.txt
echo [ERROR] Compatible Python not found.
pause
exit /b 1

:FOUND_PY
echo [OK] Using Python: %PY_PATH%

:: --- STEP 2: PREPARE WORKSPACE ---
echo [2] Preparing Workspace...
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
cd "%WORK_DIR%"

:: --- STEP 3: DOWNLOAD ---
echo [3] Downloading Source...
powershell -Command "$progressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip' -OutFile 'source.zip'"
if not exist "source.zip" (
    echo [ERROR] Download failed.
    pause
    exit /b 1
)

echo [4] Extracting...
powershell -Command "Expand-Archive -Path 'source.zip' -DestinationPath '.' -Force"

:: Find inner folder
dir /b /ad > dirs.txt
set /p INNER_DIR=<dirs.txt
cd "%INNER_DIR%"
del ..\dirs.txt

:: --- STEP 4: VIRTUAL ENV ---
echo [5] Setting up AI Engine...
"%PY_PATH%" -m venv venv
call venv\Scripts\activate.bat

echo     - Installing Dependencies...
python -m pip install --upgrade pip --no-cache-dir >nul 2>&1

:: GPU Check
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir >> ..\..\install_log.txt 2>&1
) else (
    pip install torch torchvision torchaudio --no-cache-dir >> ..\..\install_log.txt 2>&1
)

pip install -r requirements.txt --no-cache-dir >> ..\..\install_log.txt 2>&1
pip install pyinstaller --no-cache-dir >> ..\..\install_log.txt 2>&1
:: Install missing DLL provider
pip install tbb --no-cache-dir >> ..\..\install_log.txt 2>&1

:: --- FIX: LOCATE SITE-PACKAGES ---
echo [FIX] Locating CustomTkinter...
for /f "tokens=*" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set "CTK_PATH=%%i"
echo Found at: %CTK_PATH% >> ..\..\install_log.txt

:: --- BUILD ---
echo [6] Building Executable...
echo @echo off > build_run.bat
:: Added --collect-all "tbb" and "numba" to fix missing DLLs
echo "venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean --name "LocalTranscriberPro_v0.9.6" --add-data "%CTK_PATH%;customtkinter" --add-data "src;src" --collect-all "whisper" --collect-all "openai_whisper" --collect-all "tbb" --collect-all "numba" --hidden-import "scipy.special.cython_special" --hidden-import "scipy.integrate.lsoda" --exclude-module "tensorflow" main.py >> build_run.bat

call build_run.bat >> ..\..\install_log.txt 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] Build failed. See install_log.txt.
    pause
    exit /b 1
)

:: --- FINISH ---
echo.
echo ===============================================================================
echo   INSTALLATION SUCCESSFUL
echo ===============================================================================

if exist "dist\LocalTranscriberPro_*.exe" (
    echo [INSTALL] Closing old app...
    taskkill /F /IM "LocalTranscriberPro.exe" >nul 2>&1
    
    echo [INSTALL] Backing up old version...
    if exist "%DEST_EXE%" move /Y "%DEST_EXE%" "%DEST_EXE%.bak" >nul 2>&1
    
    echo [INSTALL] Copying new version...
    copy /Y "dist\LocalTranscriberPro_*.exe" "%DEST_EXE%" >nul
    
    if exist "%DEST_EXE%" (
        echo [DONE] App installed to Desktop.
        echo [DONE] Log saved to install_log.txt
        echo.
        echo Press any key to close...
        pause >nul
        exit
    ) else (
        echo [ERROR] Copy failed. restoring backup...
        if exist "%DEST_EXE%.bak" move /Y "%DEST_EXE%.bak" "%DEST_EXE%" >nul
        pause
        exit /b 1
    )
) else (
    echo [ERROR] EXE file not found in dist.
    pause
    exit /b 1
)
