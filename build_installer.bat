@echo off
cd /d "%~dp0"
echo Building Lightweight Installer...

"venv\Scripts\pyinstaller.exe" --noconsole --onefile ^
    --name "LocalTranscriber_Setup" ^
    installer.py

echo.
echo Build Complete.
exit