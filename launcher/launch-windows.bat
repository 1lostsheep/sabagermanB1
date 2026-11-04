@echo off
REM Windows starter (not used yet; Linux comes first).
REM Assumes: python -m venv .venv ; .venv\Scripts\pip install -r requirements.txt
cd /d "%~dp0\.."
start "" /min .venv\Scripts\pythonw.exe -m app.server
timeout /t 3 /nobreak >nul
start "" chrome --app=http://127.0.0.1:8765/ --start-fullscreen --user-data-dir="%cd%\data\chrome-profile"
