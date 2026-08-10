"""안전한 콘솔 챗봇을 위한 대화 이력과 입출력 루프."""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from ai_platform.llm.client import (
    ChatMessage,
    LlmConfigurationError,
    LlmNetworkError,
    LlmRemoteError,
    LlmResponse,
    LlmResponseError,
    LlmTimeoutError,
)

DEFAULT_SYSTEM_PROMPT = "당신은 AI 업무 처리 플랫폼 학습을 돕는 한국어 조력자입니다."
EXIT_COMMANDS = frozenset({"/exit", "/quit"})


class ChatCompleter(Protocol):
    """콘솔 루프가 필요로 하는 최소 완료 요청 경계다."""

    def complete(self, messages: list[ChatMessage]) -> LlmResponse:
        """현재 대화 메시지에 대한 단일 완료 응답을 반환한다."""


class ConversationHistory:
    """시스템 메시지와 제한된 수의 성공 대화 턴을 보관한다."""

    def __init__(self, *, system_prompt: str = DEFAULT_SYSTEM_PROMPT, max_turns: int = 6) -> None:
        """비어 있지 않은 시스템 지시문과 유한한 대화 턴 한도를 검증한다."""
        if not system_prompt.strip():
            raise LlmConfigurationError("system prompt must not be empty")
        if isinstance(max_turns, bool) or not isinstance(max_turns, int) or max_turns < 1:
            raise LlmConfigurationError("max_turns must be a positive integer")
        self._system = ChatMessage(role="system", content=system_prompt)
        self._max_turns = max_turns
        self._turns: list[tuple[ChatMessage, ChatMessage]] = []

    def messages_for(self, user_content: str) -> list[ChatMessage]:
        """아직 기록하지 않은 사용자 입력을 포함한 요청 메시지를 만든다."""
        user_message = ChatMessage(role="user", content=user_content)
        messages = [self._system]
        for user_turn, assistant_turn in self._turns:
            messages.extend((user_turn, assistant_turn))
        messages.append(user_message)
        return messages

    def record_success(self, *, user_content: str, assistant_content: str) -> None:
        """성공 응답만 기록하고 가장 오래된 완료 턴부터 한도 밖으로 제거한다."""
        user_message = ChatMessage(role="user", content=user_content)
        assistant_message = ChatMessage(role="assistant", content=assistant_content)
        self._turns.append((user_message, assistant_message))
        if len(self._turns) > self._max_turns:
            self._turns.pop(0)

    @property
    def message_count(self) -> int:
        """시스템 메시지를 포함해 다음 요청에 전달될 기록 메시지 수를 반환한다."""
        return 1 + (len(self._turns) * 2)


def run_chat_loop(
    client: ChatCompleter,
    *,
    read_input: Callable[[str], str] = input,
    write_output: Callable[[str], None] = print,
    history: ConversationHistory | None = None,
) -> None:
    """한 줄 입력을 안전하게 처리하고 종료 명령 또는 인터럽트까지 대화를 진행한다."""
    conversation = history or ConversationHistory()
    write_output("AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.")

    while True:
        try:
            raw_input = read_input("사용자> ")
        except (EOFError, KeyboardInterrupt):
            write_output("입력이 종료되어 대화를 마칩니다.")
            return

        user_content = raw_input.strip()
        if user_content.casefold() in EXIT_COMMANDS:
            write_output("대화를 마칩니다.")
            return
        if not user_content:
            write_output("빈 메시지는 전송하지 않았습니다. 질문을 입력하거나 /exit을 사용하세요.")
            continue

        try:
            response = client.complete(conversation.messages_for(user_content))
        except LlmConfigurationError:
            write_output("LLM 설정을 확인하세요. 모델명과 API 키를 다시 확인한 뒤 실행하세요.")
            continue
        except LlmTimeoutError:
            write_output("요청 시간이 초과되었습니다. 잠시 뒤 다시 시도하세요.")
            continue
        except LlmNetworkError:
            write_output("제공자 연결에 실패했습니다. 네트워크와 제공자 상태를 확인하세요.")
            continue
        except LlmRemoteError as error:
            write_output(f"제공자가 요청을 거부했습니다. 상태 코드: {error.status_code}")
            continue
        except LlmResponseError:
            write_output("제공자 응답 형식을 해석할 수 없습니다. 제공자 호환성을 확인하세요.")
            continue

        assistant_content = response.content.strip()
        if not assistant_content:
            write_output(
                "제공자가 빈 응답을 반환했습니다. 질문을 다시 확인하거나 잠시 뒤 시도하세요."
            )
            continue
        conversation.record_success(user_content=user_content, assistant_content=assistant_content)
        write_output(f"AI> {assistant_content}")


def is_exit_command(text: str) -> bool:
    """공백을 제외한 종료 명령인지 판별한다."""
    return text.strip().casefold() in EXIT_COMMANDS



