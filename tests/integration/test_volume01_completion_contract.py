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


def test_volume01_why_it_matters_is_a_self_contained_safe_boundary_chapter() -> None:
    """두 번째 장은 LLM의 역할 한계와 오프라인 검증을 함께 보존해야 한다."""
    chapter = (VOLUME / "02-why-it-matters.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    assert "examples/volume01/chat_cli.py --offline-demo" in chapter
    assert "tests/unit/test_llm_client.py tests/integration/test_volume01_chat_cli.py -q" in chapter
    assert "네트워크와 API 키를 사용하지 않습니다" in chapter
    assert "사람 승인" in chapter
    assert "](03-theory.md)" in chapter


def test_volume01_theory_is_a_self_contained_token_and_context_chapter() -> None:
    """세 번째 장은 토큰 예산과 Transformer 개요를 안전한 실행 경계에 연결해야 한다."""
    chapter = (VOLUME / "03-theory.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    for concept in ("머신러닝", "딥러닝", "생성형 AI", "Tokenizer", "Transformer"):
        assert concept in chapter
    assert "입력 토큰 + 출력 토큰 ≤ 모델의 Context Window" in chapter
    assert "examples/volume01/chat_cli.py --offline-demo" in chapter
    assert "tests/unit/test_llm_client.py tests/unit/test_chat.py -q" in chapter
    assert "네트워크와 API 키를 사용하지 않습니다" in chapter
    assert "](04-environment-setup.md)" in chapter


def test_volume01_environment_setup_is_a_self_contained_windows_wsl_safe_chapter() -> None:
    """네 번째 장은 재현 가능한 환경, .env 경계, 오프라인 검증을 함께 보존해야 한다."""
    chapter = (VOLUME / "04-environment-setup.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    for command in (
        "uv sync --all-groups",
        "uv python find 3.12",
        "uv run --env-file .env",
        "examples/volume01/chat_cli.py --offline-demo",
        (
            "tests/unit/test_settings.py tests/unit/test_llm_client.py "
            "tests/integration/test_volume01_chat_cli.py -q"
        ),
    ):
        assert command in chapter
    for boundary in ("/e/python/", "/mnt/e/python/", ".env.example", "자동으로 읽히지"):
        assert boundary in chapter
    assert "네트워크와 API 키를 사용하지 않습니다" in chapter
    assert "](05-first-call.md)" in chapter


def test_volume01_first_call_is_a_self_contained_explicit_transport_chapter() -> None:
    """다섯 번째 장은 명시적 전송, Mock 검증, 비밀값 없는 오류를 함께 설명해야 한다."""
    chapter = (VOLUME / "05-first-call.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    for boundary in (
        "`LlmClient`를 만드는 것만으로는 요청이 전송되지 않으며",
        "RecordingTransport",

        "uv run --env-file .env python examples/volume01/first_call.py",
        "실제 제공자에 요청을 보내지 않습니다",
    ):
        assert boundary in chapter
    assert "uv run pytest tests/unit/test_llm_client.py -q" in chapter
    assert "네트워크와 API 키를 사용하지 않습니다" in chapter
    assert "](06-system-prompt-and-parameters.md)" in chapter


def test_volume01_generation_parameters_is_a_self_contained_safe_contract_chapter() -> None:
    """여섯 번째 장은 역할 분리와 검증된 요청 직렬화를 보존해야 한다."""
    chapter = (VOLUME / "06-system-prompt-and-parameters.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    for concept in (
        "System Prompt",
        "User Message",
        "Temperature",
        "Top-p",
        "최대 출력 토큰",
        "Stop Sequence",
        "GenerationParameters",
        "RecordingTransport",
    ):
        assert concept in chapter
    assert "uv run pytest tests/unit/test_llm_client.py -q" in chapter
    assert "외부 요청과 비용을 발생시킵니다" in chapter
    assert "네트워크는 사용하지 않습니다" in chapter
    assert "](07-streaming.md)" in chapter


def test_volume01_streaming_is_a_self_contained_safe_sse_contract_chapter() -> None:
    """일곱 번째 장은 delta·종료·선택적 사용량과 Mock SSE 경계를 함께 보존해야 한다."""
    chapter = (VOLUME / "07-streaming.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    for concept in (
        "Streaming",
        "Server-Sent Events",
        "delta",
        "finish reason",
        "StreamChunk",
        "Mock StreamTransport",
        "RecordingStreamTransport",
    ):
        assert concept in chapter
    assert "uv run pytest tests/unit/test_llm_client.py -q" in chapter
    assert "외부 요청과 비용을 발생시킵니다" in chapter
    assert "네트워크는 사용하지 않습니다" in chapter
    assert "](08-error-handling.md)" in chapter


def test_volume01_error_handling_is_a_self_contained_safe_retry_chapter() -> None:
    """여덟 번째 장은 오류 분류·제한된 재시도·스트림 비재시도 경계를 보존해야 한다."""
    chapter = (VOLUME / "08-error-handling.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    for concept in (
        "LlmTimeoutError",
        "LlmNetworkError",
        "LlmRemoteError",
        "RetryPolicy",
        "지수 백오프",
        "ScriptedTransport",
        "스트림은 자동 재시도하지 않습니다",
    ):
        assert concept in chapter
    assert "uv run pytest tests/unit/test_llm_client.py -q" in chapter
    assert "외부 요청과 비용을 발생시킬 수 있습니다" in chapter
    assert "API 키와 네트워크를 사용하지 않습니다" in chapter
    assert "](09-usage-and-cost.md)" in chapter


def test_volume01_usage_and_cost_is_a_self_contained_offline_budget_chapter() -> None:
    """아홉 번째 장은 사용량·Decimal 가격·로컬 예산 검사의 한계를 보존해야 한다."""
    chapter = (VOLUME / "09-usage-and-cost.md").read_text(encoding="utf-8")

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

    assert all(section in chapter for section in required_sections)
    for concept in (
        "입력 토큰",
        "출력 토큰",
        "Decimal",
        "ModelPricing",
        "CostEstimate",
        "CostBudget",
        "CostBudgetExceeded",
        "제공자 청구 한도",
        "사용량 미수신",
        "외부 가격 조회",
    ):
        assert concept in chapter
    assert "uv run python examples/volume01/usage_and_cost.py" in chapter
    assert "uv run pytest tests/unit/test_usage.py -q" in chapter
    assert "API 키, 제공자 계정, 외부 네트워크를 사용하지 않습니다" in chapter
    assert "실제 청구서와 동일하다고 가정하지 않습니다" in chapter
    assert "](10-cli-chatbot.md)" in chapter
