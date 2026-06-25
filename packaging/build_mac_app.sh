#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -x ".venv/bin/python" ]; then
  python3.11 -m venv .venv 2>/dev/null || python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_lg

pyinstaller --noconfirm --clean TranscriptSanitizer.spec

echo "Built macOS app at dist/TranscriptSanitizer.app"
