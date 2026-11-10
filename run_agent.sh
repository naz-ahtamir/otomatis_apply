#!/usr/bin/env bash
# LinkedIn & RevoU Career Companion Automation Agent Runner

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 tidak ditemukan. Harap install python3."
    exit 1
fi

# Run orchestrator
python3 orchestrator.py "$@"
