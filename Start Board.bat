@echo off
cd /d "%~dp0"
python gameboard.py
if errorlevel 1 pause
