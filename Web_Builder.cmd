@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro Installer (v1.1)
color 0B

:: Define paths in environment variables to avoid quoting hell in PowerShell invocation
set "__LT_SCRIPT_PATH=%~f0"
set "__LT_INSTALL_DIR=%~dp0"

echo Launching Ultimate Installer engine...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$code = (Get-Content $env:__LT_SCRIPT_PATH -Raw) -split '(?m)^### PS_START ###'; [scriptblock]::Create($code[1]).Invoke($env:__LT_INSTALL_DIR)"

if %errorlevel% neq 0 (
    echo.
    echo [CRITICAL ERROR] The installer engine failed to launch.
    pause
)
exit /b %errorlevel%

### PS_START ###
param($InstallDir)

$ErrorActionPreference = "Stop"
$LogFile = "$env:USERPROFILE\Desktop\LT_Install_Log.txt"
"Installer Engine v1.1 started at $(Get-Date)" | Out-File $LogFile

function Show-Header {
    Clear-Host
    Write-Host "===============================================================================" -ForegroundColor Cyan
    Write-Host "   LOCAL TRANSCRIBER PRO - ULTIMATE INSTALLER (v1.1)" -ForegroundColor Cyan
    Write-Host "   (Developed by Vhaloo)" -ForegroundColor Cyan
    Write-Host "===============================================================================" -ForegroundColor Cyan
    Write-Host ""
}

Show-Header
Write-Host "This script will automatically setup:"
Write-Host "- Python 3.12 (Optimized for AI)"
Write-Host "- FFmpeg (Audio Engine)"
Write-Host "- Visual C++ & CUDA (Hardware Acceleration)"
Write-Host ""
Write-Host "Logs are being saved to: $LogFile"
Write-Host ""
Read-Host "Press Enter to start the installation..."

# --- STEP 1: PREREQUISITES ---
Show-Header
Write-Host "[1/6] Checking System Prerequisites..." -ForegroundColor Yellow

# 1.1 Visual C++
Write-Host "... Checking Visual C++ Redistributable..."
if (-not (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue)) {
    Write-Host "[MISSING] Installing Visual C++ via Winget..."
    winget install --id "Microsoft.VCRedist.2015+.x64" --accept-source-agreements --accept-package-agreements --silent
} else { Write-Host "[OK] Visual C++ found." -ForegroundColor Green }

# 1.2 FFmpeg
Write-Host "... Checking FFmpeg..."
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "[MISSING] Installing FFmpeg via Winget..."
    winget install --id "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements --silent
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
} else { Write-Host "[OK] FFmpeg found." -ForegroundColor Green }

# 1.3 Python (STRICT CHECK: MUST BE 3.10-3.12 64-BIT)
Write-Host "... Checking Python (64-bit 3.12 recommended)..."
$PythonPath = $null
$PyCheck = {
    param($cmd)
    $out = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor},{sys.maxsize > 2**32}')" 2>$null
    if ($out -match "3\.(10|11|12),True") { return $true }
    return $false
}

$PossiblePaths = @(
    "py", 
    "python", 
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:ProgramFiles\Python312\python.exe"
)

foreach ($p in $PossiblePaths) {
    $isValid = $false
    if ($p -match "\") { 
        if (Test-Path $p) { $isValid = $true } 
    } else {
        if (Get-Command $p -ErrorAction SilentlyContinue) { $isValid = $true }
    }
    
    if ($isValid) {
        if (&$PyCheck $p) {
            $PythonPath = $p
            break
        }
    }
}

if (-not $PythonPath) {
    Write-Host "[MISSING] Compatible 64-bit Python not found. Installing Python 3.12.8..." -ForegroundColor Yellow
    $url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $out = "$env:TEMP\python_installer.exe"
    Invoke-WebRequest -Uri $url -OutFile $out
    
    Write-Host "Installing... A progress window should appear."
    Start-Process -FilePath $out -ArgumentList "/passive InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    Remove-Item $out -ErrorAction SilentlyContinue
    
    # Try to find it again immediately using absolute paths
    $PossiblePaths = @("$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:ProgramFiles\Python312\python.exe")
    foreach ($p in $PossiblePaths) {
        if (Test-Path $p) {
            if (&$PyCheck $p) {
                $PythonPath = $p
                break
            }
        }
    }
    
    if (-not $PythonPath) {
        Write-Host ""
        Write-Host "===============================================================================" -ForegroundColor Red
        Write-Host "   PYTHON INSTALLATION FAILED OR REQUIRES A FULL PC REBOOT." -ForegroundColor Red
        Write-Host "===============================================================================" -ForegroundColor Red
        Write-Host "Please restart your computer and run this installer again."
        Read-Host "Press Enter to exit..."
        exit 1
    }
}
Write-Host "[OK] Python found: $PythonPath" -ForegroundColor Green

# --- STEP 2: WORKSPACE ---
Show-Header
Write-Host "[2/6] Preparing Workspace..." -ForegroundColor Yellow
$BuildDir = Join-Path $InstallDir "LT_Temp"
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
New-Item -ItemType Directory -Path $BuildDir | Out-Null
Set-Location $BuildDir

# --- STEP 3: DOWNLOAD ---
Write-Host "[3/6] Downloading Source Code..." -ForegroundColor Yellow
$ZipPath = Join-Path $BuildDir "source.zip"
Invoke-WebRequest -Uri "https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip" -OutFile $ZipPath
Expand-Archive -Path $ZipPath -DestinationPath $BuildDir -Force
$RepoDir = Get-ChildItem -Directory | Select-Object -First 1
Set-Location $RepoDir.FullName

# --- STEP 4: AI ENGINE ---
Show-Header
Write-Host "[4/6] Setting up AI Engine (Isolated Environment)..." -ForegroundColor Yellow

# Use the absolute path we found to create the venv
& $PythonPath -m venv venv
$VenvPython = Join-Path (Get-Location) "venv\Scripts\python.exe"
$VenvPip = Join-Path (Get-Location) "venv\Scripts\pip.exe"

Write-Host "... Updating Pip..."
& $VenvPython -m pip install --upgrade pip --no-cache-dir | Out-File $LogFile -Append

# GPU Detection
$HasGpu = $false
try { nvidia-smi | Out-Null; $HasGpu = $true } catch {}

if ($HasGpu) {
    Write-Host "[GPU] NVIDIA Detected! Installing CUDA optimized Torch..." -ForegroundColor Green
    & $VenvPip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir
} else {
    Write-Host "[CPU] No GPU detected. Installing standard Torch..."
    & $VenvPip install torch torchvision torchaudio --no-cache-dir
}

Write-Host "... Installing App requirements..."
& $VenvPip install -r requirements.txt --no-cache-dir | Out-File $LogFile -Append
& $VenvPip install pyinstaller tbb --no-cache-dir | Out-File $LogFile -Append

# --- STEP 5: BUILD ---
Show-Header
Write-Host "[5/6] Building Application (Creating High-Performance EXE)..." -ForegroundColor Yellow
$CtkPath = & $VenvPython -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"
$AppName = "LocalTranscriberPro_v1.1"

# Run PyInstaller
& $VenvPython -m PyInstaller --noconsole --onefile --clean `
    --name $AppName `
    --add-data "$($CtkPath);customtkinter" `
    --add-data "src;src" `
    --collect-all "whisper" `
    --collect-all "openai_whisper" `
    --collect-all "tbb" `
    --collect-all "numba" `
    --collect-all "torch" `
    --collect-all "torchaudio" `
    --collect-all "scipy" `
    --collect-all "yt_dlp" `
    --collect-all "tkinterdnd2" `
    --collect-all "certifi" `
    --collect-all "speechbrain" `
    --collect-all "sklearn" `
    --collect-all "soundfile" `
    --hidden-import "scipy.special.cython_special" `
    --hidden-import "scipy.integrate.lsoda" `
    --hidden-import "sklearn.utils._cython_blas" `
    --hidden-import "sklearn.neighbors.typedefs" `
    --hidden-import "sklearn.neighbors.quad_tree" `
    --hidden-import "sklearn.tree._utils" `
    --exclude-module "tensorflow" `
    main.py

# --- STEP 6: FINALIZE ---
$ExePath = Join-Path (Get-Location) "dist\$AppName.exe"
if (Test-Path $ExePath) {
    Show-Header
    Write-Host "[6/6] Finalizing Installation..." -ForegroundColor Yellow
    $DestDir = Join-Path $env:USERPROFILE "Desktop\Local Transcriber Pro"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir | Out-Null }
    
    Copy-Item $ExePath -Destination (Join-Path $DestDir "$AppName.exe") -Force
    
    # Create Shortcut
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Local Transcriber Pro.lnk")
    $Shortcut.TargetPath = (Join-Path $DestDir "$AppName.exe")
    $Shortcut.WorkingDirectory = $DestDir
    $Shortcut.Save()

    Write-Host ""
    Write-Host "===============================================================================" -ForegroundColor Green
    Write-Host "   INSTALLATION SUCCESSFUL!" -ForegroundColor Green
    Write-Host "===============================================================================" -ForegroundColor Green
    Write-Host "The app has been placed on your Desktop."
    Write-Host "Starting now..."
    Start-Process (Join-Path $DestDir "$AppName.exe")
    Set-Location $InstallDir
    # Remove-Item $BuildDir -Recurse -Force # Optional cleanup
    exit 0
} else {
    Write-Host ""
    Write-Host "===============================================================================" -ForegroundColor Red
    Write-Host "   ERROR: BUILD FAILED" -ForegroundColor Red
    Write-Host "===============================================================================" -ForegroundColor Red
    Write-Host "Please check the log on your desktop: LT_Install_Log.txt"
    exit 1
}
