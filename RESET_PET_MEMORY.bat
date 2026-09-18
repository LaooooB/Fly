@echo off
setlocal
if exist "J:\FLY\save" (
  echo This will delete ONLY J:\FLY\save, not the MaleCNS dataset.
  choice /M "Reset this cyber-pet's memory"
  if errorlevel 2 exit /b 0
  rmdir /s /q "J:\FLY\save"
  echo Memory reset.
) else (
  echo No saved memory exists yet.
)
pause
