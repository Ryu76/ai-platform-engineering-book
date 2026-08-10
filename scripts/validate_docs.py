"""Validate minimum documentation inventory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    required = [ROOT / "README.md", ROOT / "PRD.md", ROOT / "docs" / "index.md"]
    failures = [
        str(path.relative_to(ROOT))
        for path in required
        if not path.exists() or not path.read_text(encoding="utf-8").strip()
    ]
    volumes = list((ROOT / "docs").glob("volume??-*/README.md"))
    if len(volumes) != 11:
        failures.append(f"11개 Volume README 필요: 현재 {len(volumes)}개")
    if failures:
        raise SystemExit("문서 검증 실패: " + ", ".join(failures))
    print(f"문서 검증 통과: Volume {len(volumes)}개")


if __name__ == "__main__":
    main()
