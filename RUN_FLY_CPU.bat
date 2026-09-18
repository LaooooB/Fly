@echo off
setlocal
cd /d "%~dp0"
set "FLY_PET_HOME=J:\FLY"
set "FLY_DATA=J:\FLY\male_cns_data"
set "FLY_DEVICE=cpu"
".venv\Scripts\python.exe" -m cyberfly.game
if errorlevel 1 pause
