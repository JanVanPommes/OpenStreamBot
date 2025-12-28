#!/bin/bash
# Wechsele in das Verzeichnis, in dem dieses Skript liegt
cd "$(dirname "$0")"

# Starte den Launcher mit dem venv Python
./venv/bin/python launcher.py
