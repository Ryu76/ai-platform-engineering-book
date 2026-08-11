"""Run the Volume 11 mini project's local-only operations review."""
from __future__ import annotations

from json import dumps
from pathlib import Path

from ai_platform.api.operations_review import run_local_operations_review


def main() -> None:
    """Print compact evidence generated from memory and local example artifacts only."""
    repository_root = Path(__file__).resolve().parents[2]
    review = run_local_operations_review(repository_root)
    print(dumps(review, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
