@echo off
cd /d "%~dp0"
echo Starting Build Process (v1.0 Modular)...
echo This may take several minutes.

for /f "tokens=*" %%i in ('python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"') do set "CTK_PATH=%%i"

"venv\Scripts\pyinstaller.exe" --noconsole --onefile --clean ^
    --name "LocalTranscriberPro_v1.0" ^
    --add-data "%CTK_PATH%;customtkinter" ^
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