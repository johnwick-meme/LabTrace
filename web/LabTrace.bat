
@echo off
title LabTrace
cd /d "%~dp0"

echo Starting LabTrace...
start "" http://127.0.0.1:8000/

py app.py

pause
