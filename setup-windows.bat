@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0tools\setup-windows.ps1" (
 echo The tools folder is missing. Extract all files from the setup-fix ZIP into this folder.
 pause
 exit /b 1
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup-windows.ps1"
set "MIXFORGE_SETUP_RESULT=%ERRORLEVEL%"
pause
exit /b %MIXFORGE_SETUP_RESULT%
