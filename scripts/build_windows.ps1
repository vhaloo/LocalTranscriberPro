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

& $Python scripts/check_release_docs.py
if ($LASTEXITCODE -ne 0) { throw "Release documentation is stale." }

& $Python scripts/generate_brand_assets.py
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed." }
& $Python scripts/prepare_js_runtime.py
if ($LASTEXITCODE -ne 0) { throw "JavaScript runtime preparation failed." }
& $Python scripts/prepare_default_voices.py
if ($LASTEXITCODE -ne 0) { throw "Default voice preparation failed." }

$BuildVersion = & $Python -c "from src import __version__; print(__version__)"
$BuildStamp = Get-Date -Format "yyyyMMdd-HHmmss"
& $Python -m PyInstaller --clean --noconfirm --workpath "build/$BuildVersion-$BuildStamp" --distpath "dist/$BuildVersion" packaging/LocalTranscriberPro.spec
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath "dist\$BuildVersion\LocalTranscriberPro\LocalTranscriberPro.exe")) {
    throw "PyInstaller did not produce the expected application."
}

# Some runtime packages mark data directories read-only. Keep generated
# bundle directories writable so the next build and installer replacement can
# remove obsolete files without changing any system ACL or security setting.
$BundleRoot = (Resolve-Path -LiteralPath "dist\$BuildVersion\LocalTranscriberPro").Path
if (-not $BundleRoot.StartsWith($Root + '\')) { throw "Unexpected bundle path." }
Get-ChildItem -LiteralPath $BundleRoot -Directory -Recurse -Force | ForEach-Object {
    if ($_.Attributes -band [IO.FileAttributes]::ReadOnly) {
        $_.Attributes = $_.Attributes -band (-bnot [IO.FileAttributes]::ReadOnly)
    }
}

Write-Host "Build ready in dist\$BuildVersion\LocalTranscriberPro"
