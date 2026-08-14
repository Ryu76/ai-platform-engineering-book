"""Documentation contract for the bounded Volume 07 conflict-resolution lesson."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHAPTER = REPOSITORY_ROOT / "docs" / "volume07-multi-agent" / "03-bounded-conflict-resolution.md"

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


def test_conflict_resolution_chapter_meets_the_prd_learning_document_contract() -> None:
    """Keep consensus local-only, bounded, deterministic, and approval-gated."""
    chapter = CHAPTER.read_text(encoding="utf-8")

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "ConflictProposal" in chapter
    assert "ConflictContext" in chapter
    assert "DeterministicMockConflictAgent" in chapter
    assert "exact consensus" in chapter
    assert "max_agents" in chapter
    assert "max_rounds" in chapter
    assert "bounded loop" in chapter
    assert "PENDING" in chapter
    assert "APPROVED" in chapter
    assert "REJECTED" in chapter
    assert "awaiting_human_approval" in chapter
    assert "conflict_limit_reached" in chapter
    assert "examples/volume07/offline_conflict_resolution.py" in chapter
    assert "uv run python examples/volume07/offline_conflict_resolution.py --approve" in chapter
    assert "uv run pytest tests/volume07/test_bounded_conflict_resolution.py -q" in chapter
    assert "live API" in chapter
    assert "secret" in chapter
    assert "tool" in chapter
    assert "deployment" in chapter
