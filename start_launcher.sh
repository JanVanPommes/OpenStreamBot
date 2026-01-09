#!/bin/bash
# Wechsele in das Verzeichnis, in dem dieses Skript liegt
cd "$(dirname "$0")"

# Settings
VENV_DIR="venv"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# Check if venv exists and is valid (has python)
if [ ! -f "$PYTHON_BIN" ]; then
    echo "[System] Virtual Environment not found or broken. Creating..."
    
    # Try different python3 commands
    if command -v python3.12 &> /dev/null; then
        PY_CMD="python3.12"
    elif command -v python3 &> /dev/null; then
        PY_CMD="python3"
    else
        echo "[System] CRITICAL ERROR: python3 not found! Please install Python 3.10+."
        exit 1
    fi
    
    $PY_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[System] Failed to create venv."
        exit 1
    fi
    
    echo "[System] Installing dependencies..."
    "$PYTHON_BIN" -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[System] Failed to install requirements."
        exit 1
    fi
fi

# Ensure requirements are installed (check for one key package)
# Simple check: import customtkinter. If fails, install.
"$PYTHON_BIN" -c "import customtkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[System] Missing dependencies detected. Installing..."
    "$PYTHON_BIN" -m pip install -r requirements.txt
fi

# Starte den Launcher mit dem venv Python
echo "[System] Starting OpenStreamBot..."
"$PYTHON_BIN" launcher.py
