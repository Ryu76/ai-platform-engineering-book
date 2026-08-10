#!/usr/bin/env bash
set -euo pipefail
uv run ruff check .
uv run mypy src
uv run python scripts/validate_docs.py
uv run python scripts/validate_links.py
uv run python scripts/validate_code_blocks.py
uv run python scripts/check_secrets.py
uv run pytest
