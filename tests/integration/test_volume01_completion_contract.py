"""Volume 01 권 단위 검수 문서가 실제 오프라인 결과물을 참조하는지 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume01-llm-fundamentals"
README = VOLUME / "README.md"
CHECKLIST = VOLUME / "checklist.md"
GLOSSARY = ROOT / "docs" / "glossary.md"


def test_volume01_completion_checklist_preserves_artifacts_and_volume02_handoff() -> None:
    """목차, 오프라인 실행 경로, 용어집, 다음 권 인계가 함께 유지되어야 한다."""
    expected_documents = (
        "01-learning-objectives.md",
        "02-why-it-matters.md",
        "03-theory.md",
        "04-environment-setup.md",
        "05-first-call.md",
        "06-system-prompt-and-parameters.md",
        "07-streaming.md",
        "08-error-handling.md",
        "09-usage-and-cost.md",
        "10-cli-chatbot.md",
        "11-mini-project.md",
        "12-exercises.md",
        "11-summary.md",
    )
    expected_artifacts = (
        ROOT / "src" / "ai_platform" / "core" / "settings.py",
        ROOT / "src" / "ai_platform" / "llm" / "client.py",
        ROOT / "src" / "ai_platform" / "llm" / "chat.py",
        ROOT / "src" / "ai_platform" / "llm" / "usage.py",
        ROOT / "examples" / "volume01" / "chat_cli.py",
        ROOT / "tests" / "unit" / "test_llm_client.py",
        ROOT / "tests" / "unit" / "test_chat.py",
        ROOT / "tests" / "integration" / "test_volume01_chat_cli.py",
    )

    readme = README.read_text(encoding="utf-8")
    checklist = CHECKLIST.read_text(encoding="utf-8")
    glossary = GLOSSARY.read_text(encoding="utf-8")

    assert CHECKLIST.is_file()
    for document in expected_documents:
        assert (VOLUME / document).is_file()
        assert f"]({document})" in readme
    assert "](checklist.md)" in readme
    assert all(artifact.is_file() for artifact in expected_artifacts)
    assert "examples/volume01/chat_cli.py --offline-demo" in checklist
    assert "bash scripts/run_all_tests.sh" in checklist
    assert "각 장의 전체 Definition of Done" in checklist
    assert "Volume 02" in checklist
    for term in ("토큰(Token)", "토크나이저(Tokenizer)", "컨텍스트 윈도우(Context Window)"):
        assert term in glossary


def test_volume01_learning_objectives_is_a_self_contained_safe_entry_chapter() -> None:
    """첫 장은 PRD의 장 구조와 실제 오프라인 실행 경로를 함께 제공해야 한다."""
    objectives = (VOLUME / "01-learning-objectives.md").read_text(encoding="utf-8")

    required_sections = (
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

    assert all(section in objectives for section in required_sections)
    assert "examples/volume01/chat_cli.py --offline-demo" in objectives
    assert "tests/unit/test_llm_client.py tests/unit/test_chat.py -q" in objectives
    assert "네트워크와 API 키를 사용하지 않습니다" in objectives
    assert "](02-why-it-matters.md)" in objectives
