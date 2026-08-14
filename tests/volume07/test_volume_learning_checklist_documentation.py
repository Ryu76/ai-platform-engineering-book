"""Documentation contract for the Volume 07 learning checklist and Router handoff."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHAPTER = (
    REPOSITORY_ROOT
    / "docs"
    / "volume07-multi-agent"
    / "15-volume-learning-checklist-glossary-and-router-handoff.md"
)

REQUIRED_SECTIONS = (
    "## 1. 학습 목표",
    "## 2. 왜 권 단위 점검이 필요한가",
    "## 3. 핵심 개념과 다음 권 인계",
    "## 4. 동작 구조",
    "## 5. 실습 환경과 실행 위치",
    "## 6. 단계별 권 단위 검증",
    "## 7. 코드 설명과 결과물 인계표",
    "## 8. 정상 실행 결과",
    "## 9. 오류 해결",
    "## 10. 응용 실습",
    "## 11. 실무 적용",
    "## 12. 과제",
    "## 13. 완료 체크리스트",
    "## 14. 핵심 정리",
)


def test_volume_learning_checklist_meets_the_prd_learning_document_contract() -> None:
    """Keep the volume handoff executable, bounded, and incapable of granting authority."""
    chapter = CHAPTER.read_text(encoding="utf-8")

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "BoundedReviewWorkflow" in chapter
    assert "ApprovalGatedDelegationWorkflow" in chapter
    assert "BoundedConflictResolutionWorkflow" in chapter
    assert "ApprovalGatedReleaseHandoffWorkflow" in chapter
    assert "DeterministicMock" in chapter
    assert "bounded loop" in chapter
    assert "PENDING" in chapter
    assert "APPROVED" in chapter
    assert "REJECTED" in chapter
    assert "awaiting_human_approval" in chapter
    assert "uv run python examples/volume07/offline_multi_agent_mini_project.py" in chapter
    assert "uv run pytest tests/volume07 -q" in chapter
    assert "HumanApproval.APPROVED" in chapter
    assert "approval" in chapter
    assert "live API" in chapter
    assert "secret" in chapter
    assert "tool 실행" in chapter
    assert "deployment" in chapter
