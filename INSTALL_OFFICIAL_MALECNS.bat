@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MaleCNS CyberPet - Install

if not exist J:\ (
  echo [ERROR] Drive J: was not found.
  echo This build is intentionally configured to keep data and memory in J:\FLY.
  pause
  exit /b 1
)

if not exist "J:\FLY" mkdir "J:\FLY"
if not exist "J:\FLY\male_cns_data" mkdir "J:\FLY\male_cns_data"
set "FLY_PET_HOME=J:\FLY"
set "FLY_DATA=J:\FLY\male_cns_data"

set "PY_CMD="
py -3.12 -c "import sys; print(sys.version)" >nul 2>nul && set "PY_CMD=py -3.12"
if not defined PY_CMD py -3.11 -c "import sys" >nul 2>nul && set "PY_CMD=py -3.11"
if not defined PY_CMD python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul && set "PY_CMD=python"

if not defined PY_CMD (
  echo Python 3.10+ was not found.
  where winget >nul 2>nul
  if errorlevel 1 (
    echo Install Python 3.12, then run this file again.
    pause
    exit /b 1
  )
  echo Installing Python 3.12 with winget...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo [ERROR] Python installation failed.
    pause
    exit /b 1
  )
  set "PY_CMD=py -3.12"
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  %PY_CMD% -m venv .venv
  if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -e .
if errorlevel 1 goto :fail

if exist "%FLY_DATA%\OFFICIAL_MALECNS_BUILD_OK.json" (
  echo Existing verified MaleCNS build found. Re-verifying...
  python tools\verify_malecns.py
  if not errorlevel 1 goto :installed
  del /q "%FLY_DATA%\OFFICIAL_MALECNS_BUILD_OK.json" >nul 2>nul
)

rem If unverified runtime files are present, remove them so `flybrain build`
rem cannot silently reuse a prebuilt download. Raw official files are retained.
if exist "%FLY_DATA%\weights.npz" del /q "%FLY_DATA%\weights.npz"
if exist "%FLY_DATA%\brain.npz" del /q "%FLY_DATA%\brain.npz"

echo.
echo ============================================================
echo Building from the OFFICIAL MaleCNS v1.0 raw release.
echo The first installation downloads roughly 1.1 GB of source data.
echo Data folder: %FLY_DATA%
echo ============================================================
echo.

".venv\Scripts\flybrain.exe" build
if errorlevel 1 goto :fail

python tools\verify_malecns.py
if errorlevel 1 goto :fail

:installed
echo.
echo Installation and MaleCNS verification completed.
echo Run RUN_FLY.bat to start your pet.
pause
exit /b 0

:fail
echo.
echo [ERROR] Installation stopped. Review the error above.
pause
exit /b 1
