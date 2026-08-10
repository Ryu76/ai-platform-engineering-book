"""명시한 모드에서만 LLM을 호출하는 Volume 01 콘솔 챗봇."""
from __future__ import annotations

import argparse

from ai_platform.core.settings import LlmSettings
from ai_platform.llm import ChatMessage, LlmClient, LlmResponse, TokenUsage
from ai_platform.llm.chat import run_chat_loop


class OfflineDemoClient:
    """네트워크 없이 콘솔 흐름을 확인하는 결정론적 학습용 응답기다."""

    def complete(self, messages: list[ChatMessage]) -> LlmResponse:
        """마지막 사용자 입력을 사용해 실제 호출과 구별되는 데모 응답을 반환한다."""
        user_message = messages[-1]
        content = getattr(user_message, "content", "")
        return LlmResponse(
            content=f"오프라인 데모 응답: '{content}' 요청을 기록했습니다.",
            model="offline-demo",
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )


def build_live_client() -> LlmClient:
    """환경 변수 설정을 읽어 명시적 라이브 호출용 클라이언트를 만든다."""
    settings = LlmSettings.from_environment()
    return LlmClient(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
    )


def parse_arguments() -> argparse.Namespace:
    """외부 전송 없는 학습 모드를 선택하는 인자를 읽는다."""
    parser = argparse.ArgumentParser(description="AI 업무 처리 플랫폼 학습용 CLI 챗봇")
    parser.add_argument(
        "--offline-demo",
        action="store_true",
        help="외부 API 없이 결정론적 데모 응답으로 콘솔 흐름을 확인합니다.",
    )
    return parser.parse_args()


def main() -> None:
    """선택한 모드의 클라이언트로 안전한 대화 루프를 시작한다."""
    arguments = parse_arguments()
    if arguments.offline_demo:
        run_chat_loop(OfflineDemoClient())
        return

    try:
        client = build_live_client()
    except ValueError:
        print("LLM 설정을 확인하세요. .env의 LLM_MODEL과 OPENAI_API_KEY가 필요합니다.")
        return
    run_chat_loop(client)


if __name__ == "__main__":
    main()
