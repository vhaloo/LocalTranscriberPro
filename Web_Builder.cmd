@echo off
setlocal EnableDelayedExpansion
title Local Transcriber Pro - Ultimate Installer (v1.1)
color 0B

:: --- ENTRY POINT ---
echo Launching Masterpiece Installer engine...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$script_path = '%~f0'; $install_dir = '%~dp0'; [scriptblock]::Create(((Get-Content $script_path -Raw) -split '(?m)^### PS_START ###')[1]).Invoke($install_dir)"

if %errorlevel% neq 0 (
    echo.
    echo [CRITICAL ERROR] The installer engine failed to launch.
    echo Please ensure PowerShell is enabled on your system.
    pause
)
exit /b %errorlevel%

### PS_START ###
param($InstallDir)

# --- ENGINE CONFIG ---
$ErrorActionPreference = "Continue" # Don't die on minor warnings
$LogFile = "$env:USERPROFILE\Desktop\LT_Install_Log.txt"
"Masterpiece Installer v1.1 started at $(Get-Date)" | Out-File $LogFile

# Force TLS 1.2/1.3 for secure downloads on fresh Windows installs
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

function Show-Header {
    Clear-Host
    Write-Host "===============================================================================" -ForegroundColor Cyan
    Write-Host "   LOCAL TRANSCRIBER PRO - MASTERPIECE INSTALLER (v1.1)" -ForegroundColor Cyan
    Write-Host "   (Developed by Vhaloo)" -ForegroundColor Cyan
    Write-Host "===============================================================================" -ForegroundColor Cyan
    Write-Host ""
}

# --- PREREQUISITE CHECKER ---
function Get-PythonPath {
    # 1. Check py launcher
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $out = py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor},{sys.maxsize > 2**32}')" 2>$null
        if ($out -match "3\.(10|11|12),True") { return "py" }
    }
    # 2. Check path
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $out = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor},{sys.maxsize > 2**32}')" 2>$null
        if ($out -match "3\.(10|11|12),True") { return "python" }
    }
    # 3. Hunt hidden installs (Self-Healing)
    $locs = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($l in $locs) {
        if (Test-Path $l) { return "`"$l`"" }
    }
    return $null
}

Show-Header
Write-Host "This script is optimized for MAXIMUM COMPATIBILITY." -ForegroundColor Gray
Write-Host "It will automatically fix missing components and setup your local AI."
Write-Host ""
Write-Host "Target Folder: $InstallDir"
Write-Host "Log Output: $LogFile"
Write-Host ""
Read-Host "Press ENTER to begin the masterpiece installation..."

# --- STEP 1: SYSTEM COMPONENTS ---
Show-Header
Write-Host "[1/6] Scanning System Components..." -ForegroundColor Yellow

# 1.1 Long Paths Fix
$longPath = Get-ItemProperty "HKLM:\System\CurrentControlSet\Control\FileSystem" -Name "LongPathsEnabled" -ErrorAction SilentlyContinue
if ($null -eq $longPath -or $longPath.LongPathsEnabled -ne 1) {
    Write-Host "[ADVICE] Windows Long Paths are disabled. AI installation might fail." -ForegroundColor Magenta
    Write-Host "         Please run this as Admin or search 'Enable Long Paths' in Windows if the build fails."
}

# 1.2 Visual C++ 2015-2022
Write-Host "... Checking Visual C++ Runtime..."
if (-not (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue)) {
    Write-Host "[MISSING] Installing VCRedist via Winget..."
    & winget install --id "Microsoft.VCRedist.2015+.x64" --accept-source-agreements --accept-package-agreements --silent | Out-Null
} else { Write-Host "[OK] Visual C++ found." -ForegroundColor Green }

# 1.3 FFmpeg
Write-Host "... Checking FFmpeg Engine..."
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "[MISSING] Attempting Winget install..."
    & winget install --id "Gyan.FFmpeg" --accept-source-agreements --accept-package-agreements --silent | Out-Null
    
    if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
        Write-Host "[FALLBACK] Winget failed. Downloading static FFmpeg build..." -ForegroundColor Yellow
        $ffUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        $ffZip = "$env:TEMP\ffmpeg.zip"
        Invoke-WebRequest -Uri $ffUrl -OutFile $ffZip
        Expand-Archive -Path $ffZip -DestinationPath "$InstallDir\FFmpeg" -Force
        $env:Path += ";$InstallDir\FFmpeg\bin"
        Remove-Item $ffZip
    }
} else { Write-Host "[OK] FFmpeg found." -ForegroundColor Green }

# 1.4 Python (Strict 64-bit check)
Write-Host "... Checking Python (64-bit 3.12 required)..."
$PythonPath = Get-PythonPath

if (-not $PythonPath) {
    Write-Host "[MISSING] No compatible Python found. Downloading Installer..." -ForegroundColor Yellow
    $url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
    $out = "$env:TEMP\python_installer.exe"
    Invoke-WebRequest -Uri $url -OutFile $out
    Write-Host "Launching Installer... PLEASE CHOOSE 'ADD TO PATH' and 'INSTALL NOW'." -ForegroundColor Cyan
    Start-Process -FilePath $out -ArgumentList "/passive InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
    Remove-Item $out
    
    $PythonPath = Get-PythonPath
    if (-not $PythonPath) {
        Write-Host "[ERROR] Python install verification failed. Please reboot and try again." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}
Write-Host "[OK] Python confirmed: $PythonPath" -ForegroundColor Green

# --- STEP 2: SOURCE RETRIEVAL ---
Show-Header
Write-Host "[2/6] Preparing Workspace..." -ForegroundColor Yellow
$BuildDir = Join-Path $InstallDir "LT_Masterpiece_Build"
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $BuildDir | Out-Null
Set-Location $BuildDir

Write-Host "[3/6] Downloading Official Source Code..." -ForegroundColor Yellow
$ZipPath = Join-Path $BuildDir "source.zip"
Invoke-WebRequest -Uri "https://github.com/vhaloo/LocalTranscriberPro/archive/refs/heads/main.zip" -OutFile $ZipPath
Expand-Archive -Path $ZipPath -DestinationPath $BuildDir -Force
$RepoDir = (Get-ChildItem -Directory | Where-Object { $_.Name -like "*LocalTranscriber*" })[0]
Set-Location $RepoDir.FullName

# --- STEP 3: THE AI STACK ---
Show-Header
Write-Host "[4/6] Initializing AI Environment (Sandboxed)..." -ForegroundColor Yellow
& (Invoke-Expression $PythonPath) -m venv venv
$VenvPython = Join-Path (Get-Location) "venv\Scripts\python.exe"
$VenvPip = Join-Path (Get-Location) "venv\Scripts\pip.exe"

Write-Host "... Upgrading Package Manager..."
& $VenvPython -m pip install --upgrade pip --no-cache-dir | Out-File $LogFile -Append

$HasGpu = $false
try { nvidia-smi | Out-Null; $HasGpu = $true } catch {}

if ($HasGpu) {
    Write-Host "[GPU] NVIDIA Detected! Installing CUDA 12.4 optimized AI..." -ForegroundColor Green
    & $VenvPip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --no-cache-dir
} else {
    Write-Host "[CPU] No GPU detected. Installing standard AI stack..." -ForegroundColor Gray
    & $VenvPip install torch torchvision torchaudio --no-cache-dir
}

Write-Host "... Installing High-Performance Libraries..."
& $VenvPip install -r requirements.txt --no-cache-dir | Out-File $LogFile -Append
& $VenvPip install pyinstaller tbb --no-cache-dir | Out-File $LogFile -Append

# --- STEP 4: COMPILATION ---
Show-Header
Write-Host "[5/6] Building Masterpiece Executable (v1.1)..." -ForegroundColor Yellow
$CtkPath = & $VenvPython -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"
$AppName = "LocalTranscriberPro_v1.1"

# The command that makes it work everywhere
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

# --- STEP 5: FINALIZING ---
$ExePath = Join-Path (Get-Location) "dist\$AppName.exe"
if (Test-Path $ExePath) {
    Show-Header
    Write-Host "[6/6] Finalizing Desktop Integration..." -ForegroundColor Yellow
    $DestDir = Join-Path $env:USERPROFILE "Desktop\Local Transcriber Pro"
    if (-not (Test-Path $DestDir)) { New-Item -ItemType Directory -Path $DestDir | Out-Null }
    
    Copy-Item $ExePath -Destination (Join-Path $DestDir "$AppName.exe") -Force
    
    # Ultimate Shortcut Creation
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Local Transcriber Pro.lnk")
    $Shortcut.TargetPath = (Join-Path $DestDir "$AppName.exe")
    $Shortcut.WorkingDirectory = $DestDir
    $Shortcut.Description = "Local Transcriber Pro v1.1 - Developed by Vhaloo"
    $Shortcut.Save()

    Write-Host ""
    Write-Host "===============================================================================" -ForegroundColor Green
    Write-Host "   MASTERPIECE INSTALLATION SUCCESSFUL!" -ForegroundColor Green
    Write-Host "===============================================================================" -ForegroundColor Green
    Write-Host "A dedicated folder and a shortcut have been created on your Desktop."
    Write-Host "Starting the application now..."
    Start-Process (Join-Path $DestDir "$AppName.exe")
    
    Set-Location $InstallDir
    # Remove-Item $BuildDir -Recurse -Force # Optional cleanup
    exit 0
} else {
    Write-Host "ERROR: Build failed. Details in $LogFile" -ForegroundColor Red
    exit 1
}
