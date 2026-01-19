@echo off
cd /d "%~dp0"
echo Starting Build Process (v0.9.12)...
echo This may take several minutes.

"venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean ^
    --name "LocalTranscriberPro_v0.9.12_CPU_Only" ^
    --add-data "venv\Lib\site-packages\customtkinter;customtkinter" ^
    --add-data "src;src" ^
    --collect-all "whisper" ^
    --collect-all "openai_whisper" ^
    --collect-all "tbb" ^
    --collect-all "numba" ^
    --collect-all "torch" ^
    --collect-all "torchaudio" ^
    --collect-all "scipy" ^
    --collect-all "yt_dlp" ^
    --collect-all "tkinterdnd2" ^
    --collect-all "certifi" ^
    --collect-all "speechbrain" ^
    --collect-all "sklearn" ^
    --hidden-import "scipy.special.cython_special" ^
    --hidden-import "scipy.integrate.lsoda" ^
    --hidden-import "sklearn.utils._cython_blas" ^
    --hidden-import "sklearn.neighbors.typedefs" ^
    --hidden-import "sklearn.neighbors.quad_tree" ^
    --hidden-import "sklearn.tree._utils" ^
    --exclude-module "tensorflow" ^
    main.py

echo.
echo Build Complete.
echo The executable is located in the "dist" folder.
pause
exit /b 0