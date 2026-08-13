"""Documentation contract for the Volume 07 local release-handoff chapter."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHAPTER = REPOSITORY_ROOT / "docs" / "volume07-multi-agent" / "04-approved-release-handoff.md"

REQUIRED_SECTIONS = (
    "## 1. 학습 목표",
    "## 2. 왜 필요한가",
    "## 3. 핵심 개념",
    "## 4. 동작 구조",
    "## 5. 실습 환경",
    "## 6. 단계별 실습",
    "## 7. 코드 설명",
    "## 8. 정상 실행 결과",
    "## 9. 오류 해결",
    "## 10. 응용 실습",
    "## 11. 실무 적용",
    "## 12. 과제",
    "## 13. 완료 체크리스트",
    "## 14. 핵심 정리",
)


def test_release_handoff_chapter_meets_the_prd_learning_document_contract() -> None:
    """Keep the approval-gated local handoff lesson executable and safety-scoped."""
    chapter = CHAPTER.read_text(encoding="utf-8")

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "examples/volume07/offline_release_handoff.py" in chapter
    assert "tests/volume07/test_approval_gated_release_handoff.py" in chapter
    assert "uv run python examples/volume07/offline_release_handoff.py --approve" in chapter
    assert "uv run pytest tests/volume07/test_approval_gated_release_handoff.py -q" in chapter
    assert "completed" in chapter
    assert "local handoff note" in chapter
    assert "no deployment" in chapter
    assert "API key" in chapter
