@echo off
setlocal
title Installation de Gravity
chcp 65001 >nul 2>&1

pushd "%~dp0" >nul 2>&1
if errorlevel 1 goto :project_path_error

set "GRAVITY_PYTHON="

py -3.12-64 -c "import struct, sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>&1
if not errorlevel 1 set "GRAVITY_PYTHON=py -3.12-64"

if not defined GRAVITY_PYTHON (
    py -3.12 -c "import struct, sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>&1
    if not errorlevel 1 set "GRAVITY_PYTHON=py -3.12"
)

if not defined GRAVITY_PYTHON (
    python -c "import struct, sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>&1
    if not errorlevel 1 set "GRAVITY_PYTHON=python"
)

if not defined GRAVITY_PYTHON (
    python3.12 -c "import struct, sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') * 8 == 64 else 1)" >nul 2>&1
    if not errorlevel 1 set "GRAVITY_PYTHON=python3.12"
)

if not defined GRAVITY_PYTHON goto :python_missing

set "PYTHONUTF8=1"

echo.
echo Gravity va creer un environnement local dans .venv.
echo Cette operation peut prendre quelques minutes au premier lancement.
echo.

call %GRAVITY_PYTHON% "%~dp0tools\bootstrap.py" install
set "GRAVITY_EXIT=%ERRORLEVEL%"

echo.
if "%GRAVITY_EXIT%"=="0" (
    echo Installation terminee. Vous pouvez lancer LANCER_GRAVITY.bat.
) else (
    echo L'installation a echoue. Le chemin du journal est affiche ci-dessus.
)
echo.
pause
popd
exit /b %GRAVITY_EXIT%

:python_missing
echo.
echo Python 3.12 en 64 bits est introuvable.
echo Installez-le depuis https://www.python.org/downloads/ puis relancez ce fichier.
echo Pendant l'installation de Python, activez l'option Add Python to PATH.
echo.
pause
popd
exit /b 2

:project_path_error
echo Impossible d'ouvrir le dossier contenant Gravity.
pause
exit /b 3
