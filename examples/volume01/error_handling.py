"""명시 실행 때만 제한된 재시도와 안전한 오류 안내를 보여 주는 예제."""
from __future__ import annotations

from ai_platform.core.settings import LlmSettings
from ai_platform.llm import (
    ChatMessage,
    LlmClient,
    LlmNetworkError,
    LlmRemoteError,
    LlmResponseError,
    LlmTimeoutError,
    RetryPolicy,
)


def main() -> None:
    """환경 설정을 읽고 일시 오류에만 제한된 완료 요청을 실행한다."""
    settings = LlmSettings.from_environment()
    client = LlmClient(
        model=settings.model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.5),
    )
    try:
        response = client.complete(
            [
                ChatMessage(role="system", content="한국어로 한 문장만 답하세요."),
                ChatMessage(role="user", content="AI 플랫폼 상태를 설명하세요."),
            ]
        )
    except LlmTimeoutError:
        print("요청 시간이 초과되었습니다. 잠시 뒤 다시 시도하세요.")
    except LlmNetworkError:
        print("제공자 연결에 실패했습니다. 네트워크와 제공자 상태를 확인하세요.")
    except LlmRemoteError as error:
        print(f"제공자가 요청을 거부했습니다. 상태 코드: {error.status_code}")
    except LlmResponseError:
        print("제공자 응답 형식을 해석할 수 없습니다. 제공자 호환성을 확인하세요.")
    else:
        print(response.content)


if __name__ == "__main__":
    main()
