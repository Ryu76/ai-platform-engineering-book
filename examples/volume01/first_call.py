'''Volume 01의 명시적 최초 LLM 호출 예제다.'''
from __future__ import annotations

from ai_platform.core.settings import LlmSettings
from ai_platform.llm.client import ChatMessage, LlmClient


def main() -> None:
    '''환경 변수로 구성된 제공자에 한 번만 질문하고 결과를 표시한다.'''
    settings = LlmSettings.from_environment()
    client = LlmClient(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
    )
    response = client.complete(
        [
            ChatMessage(role="system", content="당신은 AI 플랫폼 입문 교재 도우미입니다."),
            ChatMessage(role="user", content="AI 업무 처리 플랫폼을 한 문장으로 설명하세요."),
        ]
    )
    print(response.content)
    print(f"model={response.model} input_tokens={response.usage.input_tokens}")
    print(f"output_tokens={response.usage.output_tokens}")


if __name__ == "__main__":
    main()
