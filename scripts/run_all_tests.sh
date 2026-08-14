#!/usr/bin/env bash
set -euo pipefail

ruff check .
mypy src
python scripts/validate_docs.py
python scripts/validate_links.py
python scripts/validate_code_blocks.py
python scripts/check_secrets.py
pytest -q
