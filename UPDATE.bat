@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MaleCNS CyberPet - Update

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git was not found. Install Git for Windows first.
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [ERROR] This folder is not a Git repository.
  echo Clone https://github.com/LaooooB/Fly.git first.
  pause
  exit /b 1
)

echo Pulling latest main branch...
git pull --ff-only
if errorlevel 1 (
  echo.
  echo [ERROR] Update stopped. Local edits or Git state may need attention.
  pause
  exit /b 1
)

echo.
echo Update complete.
echo MaleCNS data and pet memory in J:\FLY were not touched.
pause
