@echo off
chcp 65001 >nul
title Compilation EXE Optimise - Clock-of-Hour
cd /d "%~dp0"

echo ========================================================
echo   Compilation EXE Optimise (Taille reduite) — Clock-of-Hour
echo ========================================================
echo.

set "PY_BIN=%~dp0venv\Scripts\python.exe"
if not exist "%PY_BIN%" set "PY_BIN=python"

echo [*] Verification de PyInstaller...
"%PY_BIN%" -m pip install -q --disable-pip-version-check pyinstaller

echo [*] Compilation en excluant les modules lourds superflus...
"%PY_BIN%" -m PyInstaller --noconsole --onefile ^
    --name="Clock-of-Hour" ^
    --exclude-module=unittest ^
    --exclude-module=email ^
    --exclude-module=http ^
    --exclude-module=xml ^
    --exclude-module=multiprocessing ^
    --exclude-module=sqlite3 ^
    --exclude-module=asyncio ^
    --exclude-module=pydoc ^
    --exclude-module=tkinter.test ^
    --clean ^
    main.py

if exist "dist\Clock-of-Hour.exe" (
    echo.
    echo ========================================================
    echo   [SUCCES] Executable cree : dist\Clock-of-Hour.exe
    echo ========================================================
    copy /y "dist\Clock-of-Hour.exe" "%~dp0Clock-of-Hour.exe" >nul
    echo Copie disponible a la racine : %~dp0Clock-of-Hour.exe
) else (
    echo.
    echo [!] Echec de la creation de l'executable.
)

echo.
pause
