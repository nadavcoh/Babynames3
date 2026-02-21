@echo off
setlocal

echo === Pulling latest from git ===
git pull
if errorlevel 1 (
    echo ERROR: git pull failed
    pause
    exit /b 1
)

echo === Installing/updating dependencies ===
venv\Scripts\pip install -r requirements.txt --quiet

echo === Restarting app ===
REM Kill existing instance if running
taskkill /F /IM python.exe /FI "WINDOWTITLE eq shem_tov" >nul 2>&1

REM Start new instance in background, logging to app.log
start "shem_tov" /B venv\Scripts\python.exe app.py --host 0.0.0.0 --port 5000 >> app.log 2>&1

echo === Done — app restarted ===
echo Logs: %~dp0app.log
