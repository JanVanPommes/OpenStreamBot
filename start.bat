@echo off
cd /d "%~dp0"

:: --- Python Detection ---
set PYTHON_CMD=python

:: Check if 'python' works
python --version >nul 2>&1
if %errorlevel% equ 0 goto :check_venv

:: If 'python' failed, check if 'py' launcher works
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :check_venv
)

:: If both failed
echo [System] KRITISCHER FEHLER: Python konnte nicht gefunden werden!
echo [System] Bitte installiere Python von https://www.python.org/downloads/
echo [System] WICHTIG: Setze den Haken bei "Add Python to PATH" im Installer.
pause
exit /b

:check_venv
:: Prüfe ob venv und das Python-Executable existiert
if not exist venv\Scripts\python.exe (
    echo [System] Virtual Environment nicht gefunden oder unvollsteandig.
    echo [System] Nutze Python Befehl: %PYTHON_CMD%
    echo [System] Erstelle venv...

    %PYTHON_CMD% -m venv venv
    if %errorlevel% neq 0 (
        echo [System] Fehler beim Erstellen von venv.
        pause
        exit /b
    )
    
    echo [System] Installiere Abhaengigkeiten...
    venv\Scripts\python.exe -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [System] Fehler beim Installieren der Abhaengigkeiten.
        echo [System] Pruefe deine Internetverbindung.
        pause
        exit /b
    )
    echo [System] Installation abgeschlossen!
)

:: Starte den Launcher
echo [System] Starte OpenStreamBot Launcher...
venv\Scripts\python.exe launcher.py

if %errorlevel% neq 0 (
    echo [System] Launcher wurde mit Fehlern beendet.
    pause
)
