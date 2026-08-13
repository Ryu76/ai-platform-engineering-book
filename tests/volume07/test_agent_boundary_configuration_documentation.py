"""Documentation contract for the Volume 07 agent-boundary configuration chapter."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHAPTER = REPOSITORY_ROOT / "docs" / "volume07-multi-agent" / "05-agent-boundary-configuration.md"

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


def test_agent_boundary_chapter_meets_the_prd_learning_document_contract() -> None:
    """Keep the executable boundary lesson aligned with the PRD chapter template."""
    chapter = CHAPTER.read_text(encoding="utf-8")

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "tests/volume07/test_agent_boundary_configuration.py" in chapter
    assert "tests/volume07/test_inaccessible_agent_boundaries.py" in chapter
    assert "uv run pytest tests/volume07 -q" in chapter
    assert "network, live API, secret, tool executor, file mutation, deployment" in chapter
