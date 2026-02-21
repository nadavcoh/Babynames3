@echo off
echo Setting up shem tov...
python -m venv venv
if errorlevel 1 (
    echo ERROR: python not found. Install from https://python.org
    pause
    exit /b 1
)
venv\Scripts\pip install -r requirements.txt
echo.
echo Done! Run with:
echo   run.bat
echo.
echo Or for network access:
echo   run.bat --host 0.0.0.0 --port 5000
pause
