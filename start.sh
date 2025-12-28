#!/bin/bash

# Gehe sicher, dass wir im richtigen Ordner sind (wichtig für OBS später!)
cd "$(dirname "$0")"

# Aktiviere die virtuelle Umgebung
source venv/bin/activate

# Starte den Bot
python3 main.py
