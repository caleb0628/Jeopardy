@echo off
cd /d "%~dp0"
echo Installing what the buzzer needs. This takes a minute...
python -m pip install -r requirements.txt
echo.
echo Done. You can close this window.
pause
