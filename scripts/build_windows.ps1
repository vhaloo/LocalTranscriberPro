$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Create .venv with Python 3.12 and install the build requirements first."
}

# Native dependency discovery must prefer Windows' current runtime DLLs over
# stale copies bundled by unrelated software elsewhere on the machine.
$env:PATH = "$env:SystemRoot\System32;$(Split-Path -Parent $Python);$env:PATH"

& $Python scripts/generate_brand_assets.py
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed." }

& $Python -m PyInstaller --clean --noconfirm packaging/LocalTranscriberPro.spec
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath "dist\LocalTranscriberPro\LocalTranscriberPro.exe")) {
    throw "PyInstaller did not produce the expected application."
}

Write-Host "Build ready in dist\LocalTranscriberPro"
