@echo off
setlocal
title Tests de Gravity
chcp 65001 >nul 2>&1

pushd "%~dp0" >nul 2>&1
if errorlevel 1 goto :project_path_error

set "GRAVITY_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%GRAVITY_PYTHON%" goto :installation_missing

set "PYTHONUTF8=1"
if defined LOCALAPPDATA set "NUMBA_CACHE_DIR=%LOCALAPPDATA%\Gravity\cache\numba"

echo.
echo Verification complete de Gravity...
echo.
"%GRAVITY_PYTHON%" "%~dp0tools\bootstrap.py" test
set "GRAVITY_EXIT=%ERRORLEVEL%"

echo.
if "%GRAVITY_EXIT%"=="0" (
    echo Tous les controles ont reussi.
) else (
    echo Un controle a echoue. Le chemin du journal est affiche ci-dessus.
)
echo.
pause
popd
exit /b %GRAVITY_EXIT%

:installation_missing
echo Gravity n'est pas installe. Lancez d'abord INSTALLER.bat.
pause
popd
exit /b 2

:project_path_error
echo Impossible d'ouvrir le dossier contenant Gravity.
pause
exit /b 3
