"""네트워크 없이 Volume 01 콘솔 챗봇의 대화 계약을 검사한다."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from ai_platform.llm import (
    LlmConfigurationError,
    LlmNetworkError,
    LlmResponse,
    LlmTimeoutError,
    TokenUsage,
)
from ai_platform.llm.chat import ConversationHistory, is_exit_command, run_chat_loop


class ScriptedClient:
    """요청 메시지를 기록하고 응답 또는 예외를 순서대로 반환하는 Mock이다."""

    def __init__(self, outcomes: list[LlmResponse | Exception]) -> None:
        self.outcomes = outcomes
        self.requests: list[list[object]] = []

    def complete(self, messages: list[object]) -> LlmResponse:
        """대화를 기록한 뒤 준비된 결과를 외부 전송 없이 반환한다."""
        self.requests.append(messages)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def inputs(values: list[str | BaseException]) -> Iterator[str]:
    """대화 루프에 전달할 입력과 인터럽트를 순서대로 만든다."""
    for value in values:
        if isinstance(value, BaseException):
            raise value
        yield value


def response(content: str) -> LlmResponse:
    """테스트에서 사용하는 최소 LLM 응답을 만든다."""
    return LlmResponse(content=content, model="offline-test", usage=TokenUsage(1, 1))


def test_history_keeps_system_message_and_discards_oldest_complete_turn() -> None:
    history = ConversationHistory(system_prompt="시스템", max_turns=2)
    history.record_success(user_content="첫 질문", assistant_content="첫 답변")
    history.record_success(user_content="둘 질문", assistant_content="둘 답변")
    history.record_success(user_content="셋 질문", assistant_content="셋 답변")

    assert [(message.role, message.content) for message in history.messages_for("넷 질문")] == [
        ("system", "시스템"),
        ("user", "둘 질문"),
        ("assistant", "둘 답변"),
        ("user", "셋 질문"),
        ("assistant", "셋 답변"),
        ("user", "넷 질문"),
    ]


def test_history_rejects_empty_system_prompt_or_invalid_turn_limit() -> None:
    with pytest.raises(LlmConfigurationError, match="system prompt"):
        ConversationHistory(system_prompt=" ")
    with pytest.raises(LlmConfigurationError, match="max_turns"):
        ConversationHistory(max_turns=0)


def test_chat_loop_records_successful_turn_and_exits() -> None:
    client = ScriptedClient([response("RAG는 검색 문서를 근거로 답합니다.")])
    input_iterator = inputs(["RAG란 무엇인가요?", "/exit"])
    output: list[str] = []

    run_chat_loop(client, read_input=lambda _: next(input_iterator), write_output=output.append)

    assert output == [
        "AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.",
        "AI> RAG는 검색 문서를 근거로 답합니다.",
        "대화를 마칩니다.",
    ]
    assert [(message.role, message.content) for message in client.requests[0]] == [
        ("system", "당신은 AI 업무 처리 플랫폼 학습을 돕는 한국어 조력자입니다."),
        ("user", "RAG란 무엇인가요?"),
    ]


def test_chat_loop_does_not_record_failed_turn_and_shows_safe_error() -> None:
    client = ScriptedClient(
        [LlmTimeoutError("sensitive details must not appear"), response("복구 응답")]
    )
    input_iterator = inputs(["첫 질문", "둘 질문", "/quit"])
    output: list[str] = []

    run_chat_loop(client, read_input=lambda _: next(input_iterator), write_output=output.append)

    assert output[1] == "요청 시간이 초과되었습니다. 잠시 뒤 다시 시도하세요."
    assert "sensitive details" not in "\n".join(output)
    assert [(message.role, message.content) for message in client.requests[1]] == [
        ("system", "당신은 AI 업무 처리 플랫폼 학습을 돕는 한국어 조력자입니다."),
        ("user", "둘 질문"),
    ]
    assert output[2] == "AI> 복구 응답"


def test_chat_loop_skips_empty_input_and_handles_input_end() -> None:
    client = ScriptedClient([])
    input_iterator = inputs(["   ", EOFError()])
    output: list[str] = []

    run_chat_loop(client, read_input=lambda _: next(input_iterator), write_output=output.append)

    assert output == [
        "AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.",
        "빈 메시지는 전송하지 않았습니다. 질문을 입력하거나 /exit을 사용하세요.",
        "입력이 종료되어 대화를 마칩니다.",
    ]
    assert client.requests == []


def test_chat_loop_handles_network_error_without_leaking_exception_text() -> None:
    client = ScriptedClient([LlmNetworkError("secret network detail")])
    input_iterator = inputs(["상태", "/exit"])
    output: list[str] = []

    run_chat_loop(client, read_input=lambda _: next(input_iterator), write_output=output.append)

    assert output[1] == "제공자 연결에 실패했습니다. 네트워크와 제공자 상태를 확인하세요."
    assert "secret network detail" not in "\n".join(output)


@pytest.mark.parametrize("command", ["/exit", " /QUIT "])
def test_is_exit_command_accepts_case_and_surrounding_space(command: str) -> None:
    assert is_exit_command(command)
