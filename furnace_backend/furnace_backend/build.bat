@echo off
echo Building furnace backend executable...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install PyInstaller if not installed
pip install pyinstaller

REM Build with spec file
pyinstaller --clean build.spec

echo.
echo Build complete! Executable is in the dist\ directory.
pause
