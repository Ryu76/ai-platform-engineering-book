"""Reject common credential patterns from project files."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
]


def main() -> None:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        skip_path = any(part in {".git", ".venv"} for part in path.parts)
        if not path.is_file() or skip_path or path.name == ".env.example":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(text) for pattern in PATTERNS):
            failures.append(str(path.relative_to(ROOT)))
    if failures:
        raise SystemExit("비밀값 패턴 발견: " + ", ".join(failures))
    print("비밀값 검사 통과")


if __name__ == "__main__":
    main()
