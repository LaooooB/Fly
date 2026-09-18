@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MaleCNS CyberPet

if not exist J:\ (
  echo [ERROR] Drive J: was not found. Save path must be J:\FLY.
  pause
  exit /b 1
)
set "FLY_PET_HOME=J:\FLY"
set "FLY_DATA=J:\FLY\male_cns_data"
set "FLY_DEVICE=auto"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Not installed yet. Run INSTALL_OFFICIAL_MALECNS.bat first.
  pause
  exit /b 1
)
if not exist "%FLY_DATA%\OFFICIAL_MALECNS_BUILD_OK.json" (
  echo [ERROR] Official MaleCNS verification marker missing.
  echo Run INSTALL_OFFICIAL_MALECNS.bat first.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m cyberfly.game
if errorlevel 1 (
  echo.
  echo The game exited with an error. Your last autosave remains in J:\FLY\save.
  pause
)
