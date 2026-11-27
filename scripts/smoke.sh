#!/usr/bin/env bash
# Requires Python 3.12+; credentials are loaded from config or a local manifest, never argv.
set -euo pipefail
exec python scripts/smoke.py "${1:?Usage: bash scripts/smoke.sh https://your-host}"
