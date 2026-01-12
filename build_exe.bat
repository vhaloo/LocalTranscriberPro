@echo off
cd /d "%~dp0"
echo Starting Build Process (v0.9 Modular)...
echo This may take several minutes.

"venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean ^
    --name "LocalTranscriberPro_v0.9.6" ^
    --add-data "venv\Lib\site-packages\customtkinter;customtkinter" ^
    --add-data "src;src" ^
    --collect-all "whisper" ^
    --collect-all "openai_whisper" ^
    --hidden-import "scipy.special.cython_special" ^
    --hidden-import "scipy.integrate.lsoda" ^
    --exclude-module "tensorflow" ^
    main.py

echo.
echo Build Complete.
echo The executable is located in the "dist" folder.
pause
exit /b 0