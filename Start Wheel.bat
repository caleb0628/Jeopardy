@echo off
cd /d "%~dp0"
python wheel.py
if errorlevel 1 pause
