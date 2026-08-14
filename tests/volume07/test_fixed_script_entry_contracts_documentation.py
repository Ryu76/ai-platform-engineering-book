"""Documentation contract for the Volume 07 fixed Mock-script entry lesson."""

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHAPTER = REPOSITORY_ROOT / "docs" / "volume07-multi-agent" / "07-fixed-script-entry-contracts.md"

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


def test_fixed_script_entry_contract_chapter_meets_the_prd_learning_document_contract() -> None:
    """Keep the immutable fixture lesson executable, bounded, approval-gated, and local-only."""
    chapter = CHAPTER.read_text(encoding="utf-8")

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "DeterministicMockAgent" in chapter
    assert "DeterministicMockCoordinator" in chapter
    assert "DeterministicMockWorker" in chapter
    assert "DeterministicMockConflictAgent" in chapter
    assert "AgentResponse" in chapter
    assert "DelegationPlan" in chapter
    assert "WorkerResponse" in chapter
    assert "ConflictProposal" in chapter
    assert "WorkflowConfigurationError" in chapter
    assert "tests/volume07/test_immutable_mock_scripts.py" in chapter
    assert "uv run pytest tests/volume07/test_immutable_mock_scripts.py -q" in chapter
    assert "uv run pytest tests/volume07 -q" in chapter
    assert "bounded loop" in chapter
    assert "PENDING" in chapter
    assert "APPROVED" in chapter
    assert "REJECTED" in chapter
    assert "live API" in chapter
    assert "secret" in chapter
    assert "tool 실행" in chapter
    assert "deployment" in chapter
