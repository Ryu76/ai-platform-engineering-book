"""Validate local Markdown links without network access."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"(?<!!)\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)")


def main() -> None:
    failures: list[str] = []
    for document in ROOT.rglob("*.md"):
        for target in PATTERN.findall(document.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            if not (document.parent / target).resolve().exists():
                failures.append(f"{document.relative_to(ROOT)} -> {target}")
    if failures:
        raise SystemExit("깨진 로컬 링크:\n" + "\n".join(failures))
    print("링크 검증 통과")


if __name__ == "__main__":
    main()
