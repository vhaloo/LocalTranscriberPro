param(
    [string]$Compiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    [string]$OutputRoot = '',
    [switch]$SimulateLowMemory
)
$ErrorActionPreference = 'Stop'
$TaskRepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputRoot) { $OutputRoot = Join-Path $TaskRepoRoot 'artifacts\installer-probe' }
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$TaskDefines = @('/Qp', '/DSyntaxOnly')
if ($SimulateLowMemory) { $TaskDefines += '/DTestLowMemory' }
& $Compiler @TaskDefines "/O$OutputRoot" (Join-Path $TaskRepoRoot 'packaging\windows\installer.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer probe compilation failed.' }
$TaskProbe = Join-Path $OutputRoot 'LocalTranscriberPro-Installer-SyntaxTest.exe'
$TaskLog = Join-Path $OutputRoot 'preflight.log'
$TaskProcess = Start-Process -FilePath $TaskProbe -ArgumentList @('/PREFLIGHTONLY', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/LOG=`"$TaskLog`"") -WindowStyle Hidden -Wait -PassThru
$TaskContents = Get-Content -LiteralPath $TaskLog -Raw
if ($TaskProcess.ExitCode -ne 1 -or -not $TaskContents.Contains('LTP_PREFLIGHT_OK:')) {
    throw "Native installer preflight failed (exit $($TaskProcess.ExitCode)). Inspect $TaskLog"
}
if ($SimulateLowMemory -and -not $TaskContents.Contains('Low physical RAM: installation allowed')) {
    throw 'The simulated 2 GB installer did not reach the allowed low-memory path.'
}
Write-Output 'Native installer wizard/hardware preflight passed without copying files.'
