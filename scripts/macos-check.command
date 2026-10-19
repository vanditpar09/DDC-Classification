#!/bin/bash
cd "$(dirname "$0")/.." || exit 1
export PYTHONUTF8=1
require_environment() {
  if [ ! -x .venv/bin/python ]; then
    echo 'Run macos-setup.command first. See RUN_GUIDE.md.'
    exit 1
  fi
}
require_environment
.venv/bin/python scripts/check_windows_demo.py
result=$?
echo "Finished (status $result). Press Return to close."
read -r _
exit "$result"
