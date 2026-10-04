#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3 >/dev/null || { echo 'Install Python 3.11+ first.'; exit 1; }
python3 -m venv .venv
.venv/bin/python -m pip install -e .
if [ ! -f nila/static/index.html ]; then
  command -v npm >/dev/null || { echo 'Install Node.js 22 LTS first.'; exit 1; }
  (cd web && npm ci && npm run build)
fi
printf '%s\n' 'Nila installed. First run: ollama pull llama3.2:1b' 'Launch Web UI: .venv/bin/nila web' 'Launch chat: .venv/bin/nila'
