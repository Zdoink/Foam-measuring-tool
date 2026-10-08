#!/usr/bin/env bash
# Foam Measuring Tool launcher for macOS and Linux.
# First run: creates a private Python environment (.venv) and installs
# the required packages. Later runs start the app straight away.

set -e

cd "$(dirname "$0")"

if [ ! -f .venv/installed.txt ]; then

    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3.11 or newer was not found."
        echo "Install it from https://www.python.org/downloads/ and run this again."
        exit 1
    fi

    echo "Setting up Foam Measuring Tool (first run only, this can take a few minutes)..."

    [ -x .venv/bin/python ] || python3 -m venv .venv

    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -r requirements.txt

    echo done > .venv/installed.txt
fi

exec .venv/bin/python main.py "$@"
