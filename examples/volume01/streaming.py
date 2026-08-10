"""명시 실행 때만 LLM 스트리밍 출력을 표시하는 Volume 01 예제."""
from __future__ import annotations

from ai_platform.core.settings import LlmSettings
from ai_platform.llm import ChatMessage, GenerationParameters, LlmClient


def main() -> None:
    """환경에서 설정을 읽어 텍스트 조각을 도착하는 순서대로 출력한다."""
    settings = LlmSettings.from_environment()
    client = LlmClient(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
    )
    final_usage = None
    for chunk in client.stream(
        [
            ChatMessage(role="system", content="한국어로 간결하게 답하세요."),
            ChatMessage(role="user", content="AI 플랫폼에서 스트리밍이 필요한 이유를 설명하세요."),
        ],
        generation=GenerationParameters(temperature=0.2, max_output_tokens=120),
    ):
        print(chunk.delta, end="", flush=True)
        if chunk.usage is not None:
            final_usage = chunk.usage
    print()
    if final_usage is None:
        print("사용량: 제공자가 스트림 사용량을 반환하지 않았습니다.")
    else:
        print(
            "사용량: "
            f"input_tokens={final_usage.input_tokens} "
            f"output_tokens={final_usage.output_tokens}"
        )


if __name__ == "__main__":
    main()
