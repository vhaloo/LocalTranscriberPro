@echo off
cd /d "%~dp0"
echo Starting Build Process...
echo This may take several minutes due to the large size of PyTorch/CUDA libraries.

"venv\Scripts\pyinstaller.exe" --noconsole --onefile ^
    --name "LocalTranscriberPro" ^
    --add-data "venv\Lib\site-packages\customtkinter;customtkinter" ^
    --collect-all "whisper" ^
    --collect-all "openai_whisper" ^
    --hidden-import "scipy.special.cython_special" ^
    --hidden-import "scipy.integrate.lsoda" ^
    local_transcriber.py

echo.
echo Build Complete.
echo The executable is located in the "dist" folder.
exit