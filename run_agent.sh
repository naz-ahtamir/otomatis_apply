#!/usr/bin/env bash
# LinkedIn & RevoU Career Companion Automation Agent Runner (Firefox)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$SCRIPT_DIR/venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
else
    echo "❌ Python 3 tidak ditemukan. Harap install python3."
    exit 1
fi

"$PYTHON_BIN" orchestrator.py "$@"
