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
.venv/bin/python scripts/check_windows_demo.py --quick || exit $?
export FIELDNOTE_OCR=portable FIELDNOTE_DB=output/fieldnote/macos-demo.sqlite3 FIELDNOTE_CPU_THREADS=4
echo 'Open http://127.0.0.1:8013 after startup. Keep this window open.'
.venv/bin/python -m prototype.run --port 8013 --model native_silver_v2
result=$?
echo "Finished (status $result). Press Return to close."
read -r _
exit "$result"
