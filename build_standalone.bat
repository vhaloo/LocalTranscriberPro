@echo off
cd /d "%~dp0"
echo Starting Standalone Build (v0.6.1)...
echo This will take 5-10 minutes. Please wait.

"venv\Scripts\pyinstaller.exe" --noconsole --onefile ^
    --name "LocalTranscriber_v0.6.1_GPU" ^
    --add-data "venv\Lib\site-packages\customtkinter;customtkinter" ^
    --add-data "venv\Lib\site-packages\whisper\assets;whisper\assets" ^
    --collect-all "whisper" ^
    --collect-all "openai_whisper" ^
    --hidden-import "scipy.special.cython_special" ^
    --hidden-import "scipy.integrate.lsoda" ^
    --hidden-import "sklearn.utils._cython_blas" ^
    --hidden-import "sklearn.neighbors.typedefs" ^
    --hidden-import "sklearn.neighbors.quad_tree" ^
    --hidden-import "sklearn.tree" ^
    --hidden-import "sklearn.tree._utils" ^
    local_transcriber.py

echo.
echo Build Complete.
pause