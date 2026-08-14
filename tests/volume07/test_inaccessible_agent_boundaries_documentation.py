"""Documentation contract for the Volume 07 inaccessible agent-boundary lesson."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHAPTER = (
    REPOSITORY_ROOT
    / "docs"
    / "volume07-multi-agent"
    / "12-inaccessible-agent-boundaries.md"
)

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


def test_inaccessible_agent_boundary_chapter_meets_the_prd_learning_document_contract() -> None:
    """Keep the configuration-discovery lesson executable, bounded, and local-only."""
    chapter = CHAPTER.read_text(encoding="utf-8")

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "validate_callable_boundary" in chapter
    assert "WorkflowConfigurationError" in chapter
    assert "UnreadableActBoundary" in chapter
    assert "UnreadableProposeBoundary" in chapter
    assert "PENDING" in chapter
    assert "APPROVED" in chapter
    assert "REJECTED" in chapter
    assert "tests/volume07/test_inaccessible_agent_boundaries.py" in chapter
    assert "uv run pytest tests/volume07/test_inaccessible_agent_boundaries.py -q" in chapter
    assert "uv run pytest tests/volume07 -q" in chapter
    assert "bounded loop" in chapter
    assert "live API" in chapter
    assert "secret" in chapter
    assert "tool 실행" in chapter
    assert "deployment" in chapter
