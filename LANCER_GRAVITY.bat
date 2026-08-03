@echo off
setlocal

pushd "%~dp0" >nul 2>&1
if errorlevel 1 exit /b 3

set "GRAVITY_PYTHONW=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%GRAVITY_PYTHONW%" goto :installation_missing

set "PYTHONUTF8=1"
if defined LOCALAPPDATA set "NUMBA_CACHE_DIR=%LOCALAPPDATA%\Gravity\cache\numba"

start "" /B "%GRAVITY_PYTHONW%" -m gravity
set "GRAVITY_EXIT=%ERRORLEVEL%"
popd
exit /b %GRAVITY_EXIT%

:installation_missing
start "" wscript.exe "%~dp0tools\windows\message.vbs" "Gravity n'est pas installe. Lancez d'abord INSTALLER.bat." "Gravity"
popd
exit /b 2

