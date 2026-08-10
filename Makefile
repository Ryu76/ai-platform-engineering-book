.PHONY: test check docs secrets

test:
	uv run pytest

check:
	uv run ruff check .
	uv run mypy src

docs:
	uv run python scripts/validate_docs.py
	uv run python scripts/validate_links.py
	uv run python scripts/validate_code_blocks.py

secrets:
	uv run python scripts/check_secrets.py
