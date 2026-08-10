'''System Prompt와 생성 파라미터를 명시해 LLM을 한 번 호출하는 선택 예제다.'''
from __future__ import annotations

from ai_platform.core.settings import LlmSettings
from ai_platform.llm.client import ChatMessage, GenerationParameters, LlmClient


def main() -> None:
    '''환경 변수를 읽고 재현성을 우선한 짧은 응답을 요청한다.'''
    settings = LlmSettings.from_environment()
    client = LlmClient(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
    )
    response = client.complete(
        [
            ChatMessage(
                role="system",
                content=(
                    "당신은 AI 플랫폼 입문 교재 도우미입니다. "
                    "검증되지 않은 사실은 단정하지 말고, 한국어로 두 문장 이내로 답하세요."
                ),
            ),
            ChatMessage(
                role="user",
                content="AI 업무 처리 플랫폼에서 Router의 역할을 설명하세요.",
            ),
        ],
        generation=GenerationParameters(
            temperature=0.2,
            top_p=0.9,
            max_output_tokens=120,
            stop_sequences=("\n\n사용자:",),
        ),
    )
    print(response.content)
    print(f"model={response.model} input_tokens={response.usage.input_tokens}")
    print(f"output_tokens={response.usage.output_tokens}")


if __name__ == "__main__":
    main()
