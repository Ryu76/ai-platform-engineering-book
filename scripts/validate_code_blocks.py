"""Require language labels on fenced code blocks in authored teaching documents."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    failures: list[str] = []
    for path in (ROOT / "docs").rglob("*.md"):
        in_block = False
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.startswith("```"):
                continue
            if in_block:
                in_block = False
                continue
            if line == "```":
                failures.append(f"{path.relative_to(ROOT)}:{line_number}")
            in_block = True
    if failures:
        raise SystemExit("언어 없는 코드 블록: " + ", ".join(failures))
    print("코드 블록 검증 통과")


if __name__ == "__main__":
    main()
