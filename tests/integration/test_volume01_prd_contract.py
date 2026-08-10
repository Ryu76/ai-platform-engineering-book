"""Volume 01 PRD 필수 범위가 실행 가능한 오프라인 결과물로 남는지 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume01-llm-fundamentals"

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

CHAPTERS = (
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


def test_volume01_chapters_keep_the_prd_learning_flow_and_completion_checks() -> None:
    """각 장은 초보자용 학습 흐름, 과제, 자체 완료 검사를 모두 제공해야 한다."""
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    for chapter_name in CHAPTERS:
        chapter = (VOLUME / chapter_name).read_text(encoding="utf-8")
        assert all(section in chapter for section in REQUIRED_SECTIONS)
        assert f"]({chapter_name})" in readme


def test_volume01_prd_topics_practices_and_deliverables_are_offline_verifiable() -> None:
    """PRD의 LLM 기초 범위와 결과물이 실제 Mock·오프라인 경로로 연결되어야 한다."""
    theory = (VOLUME / "03-theory.md").read_text(encoding="utf-8")
    parameters = (VOLUME / "06-system-prompt-and-parameters.md").read_text(encoding="utf-8")
    streaming = (VOLUME / "07-streaming.md").read_text(encoding="utf-8")
    errors = (VOLUME / "08-error-handling.md").read_text(encoding="utf-8")
    usage = (VOLUME / "09-usage-and-cost.md").read_text(encoding="utf-8")
    cli = (VOLUME / "10-cli-chatbot.md").read_text(encoding="utf-8")
    exercises = (VOLUME / "12-exercises.md").read_text(encoding="utf-8")

    for term in (
        "머신러닝",
        "딥러닝",
        "생성형 AI",
        "LLM",
        "Transformer",
        "Token",
        "Tokenizer",
        "Context Window",
        "입력 토큰",
        "출력 토큰",
        "Hallucination",
        "실시간 정보",
    ):
        assert term in theory
    for term in (
        "System Prompt",
        "User Message",
        "Assistant",
        "Temperature",
        "Top-p",
        "Stop Sequence",
    ):
        assert term in parameters or term in theory
    for term in ("Streaming", "Server-Sent Events", "delta", "finish reason"):
        assert term in streaming
    for term in ("시간 초과", "네트워크 오류", "RetryPolicy", "API 키"):
        assert term in errors
    for term in ("TokenUsage", "ModelPricing", "CostBudget", "비용"):
        assert term in usage
    for term in ("ConversationHistory", "/exit", "/quit", "--offline-demo"):
        assert term in cli

    required_files = (
        ROOT / ".env.example",
        ROOT / "src" / "ai_platform" / "llm" / "client.py",
        ROOT / "examples" / "volume01" / "chat_cli.py",
        ROOT / "tests" / "unit" / "test_llm_client.py",
        ROOT / "tests" / "integration" / "test_volume01_chat_cli.py",
    )
    assert all(path.is_file() for path in required_files)
    assert "uv run pytest tests/unit/test_chat.py -q" in exercises
    assert "uv run pytest tests/integration/test_volume01_chat_cli.py -q" in exercises
    assert "실제 API·키·네트워크 없이" in exercises
