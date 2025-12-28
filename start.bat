@echo off
:: Wechsele in das Verzeichnis des Skripts
cd /d "%~dp0"

:: Prüfe ob venv existiert
if not exist venv (
    echo [System] Virtuelle Umgebung (venv) nicht gefunden!
    echo [System] Bitte fuehre 'python -m venv venv' und installiere die Requirements.
    pause
    exit /b
)

:: Starte den Launcher
echo [System] Starte OpenStreamBot Launcher...
venv\Scripts\python.exe launcher.py

if %errorlevel% neq 0 (
    echo [System] Launcher wurde mit Fehlern beendet.
    pause
)
