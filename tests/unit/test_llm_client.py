from __future__ import annotations

from collections.abc import Mapping

import pytest

from ai_platform.llm.client import (
    ChatMessage,
    GenerationParameters,
    HttpResponse,
    LlmClient,
    LlmConfigurationError,
    LlmRemoteError,
    LlmResponseError,
)


class RecordingTransport:
    """네트워크를 사용하지 않고 요청을 기록하는 테스트 전송 계층이다."""

    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.url = ""
        self.headers: Mapping[str, str] = {}
        self.payload: Mapping[str, object] = {}
        self.timeout_seconds = 0.0

    def post_json(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> HttpResponse:
        self.url = url
        self.headers = headers
        self.payload = payload
        self.timeout_seconds = timeout_seconds
        return self.response


def test_client_sends_openai_compatible_request_and_parses_response() -> None:
    transport = RecordingTransport(
        HttpResponse(
            status_code=200,
            payload={
                "model": "offline-test-model",
                "choices": [{"message": {"content": "안녕하세요. 플랫폼입니다."}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            },
        )
    )
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        base_url="https://example.invalid/v1/",
        timeout_seconds=12.5,
        transport=transport,
    )

    response = client.complete(
        [
            ChatMessage(role="system", content="간결하게 답하세요."),
            ChatMessage(role="user", content="플랫폼은 무엇인가요?"),
        ]
    )

    assert response.content == "안녕하세요. 플랫폼입니다."
    assert response.model == "offline-test-model"
    assert response.usage.input_tokens == 11
    assert response.usage.output_tokens == 7
    assert transport.url == "https://example.invalid/v1/chat/completions"
    assert transport.timeout_seconds == 12.5
    assert transport.payload["model"] == "offline-test-model"
    assert transport.payload["messages"] == [
        {"role": "system", "content": "간결하게 답하세요."},
        {"role": "user", "content": "플랫폼은 무엇인가요?"},
    ]
    assert transport.headers["Authorization"] == "Bearer unit-test-token"


def test_client_rejects_missing_key_without_echoing_value() -> None:
    with pytest.raises(LlmConfigurationError, match="OPENAI_API_KEY") as error:
        LlmClient(model="offline-test-model", api_key=None)

    assert "token" not in str(error.value).lower()


def test_client_surfaces_provider_error_without_request_secret() -> None:
    transport = RecordingTransport(
        HttpResponse(
            status_code=429,
            payload={"error": {"message": "rate limit reached"}},
        )
    )
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
    )

    with pytest.raises(LlmRemoteError, match=r"\(429\): rate limit reached") as error:
        client.complete([ChatMessage(role="user", content="상태를 알려 주세요.")])

    assert "unit-test-token" not in str(error.value)


def test_client_rejects_malformed_success_response() -> None:
    transport = RecordingTransport(HttpResponse(status_code=200, payload={"choices": []}))
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
    )

    with pytest.raises(LlmResponseError, match="does not contain choices"):
        client.complete([ChatMessage(role="user", content="응답 형식을 검사합니다.")])


def test_message_rejects_unknown_role_and_empty_content() -> None:
    with pytest.raises(LlmConfigurationError, match="role"):
        ChatMessage(role="tool", content="허용되지 않는 역할")
    with pytest.raises(LlmConfigurationError, match="content"):
        ChatMessage(role="user", content="   ")


def test_client_serializes_explicit_generation_parameters() -> None:
    transport = RecordingTransport(
        HttpResponse(
            status_code=200,
            payload={"choices": [{"message": {"content": "고정된 응답"}}]},
        )
    )
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
    )

    client.complete(
        [ChatMessage(role="system", content="정확한 한국어로 답하세요.")],
        generation=GenerationParameters(
            temperature=0.2,
            top_p=0.9,
            max_output_tokens=120,
            stop_sequences=("<끝>", "\n\n사용자:"),
        ),
    )

    assert transport.payload["temperature"] == 0.2
    assert transport.payload["top_p"] == 0.9
    assert transport.payload["max_tokens"] == 120
    assert transport.payload["stop"] == ["<끝>", "\n\n사용자:"]


@pytest.mark.parametrize(
    "parameters",
    [GenerationParameters(temperature=0.0), GenerationParameters(top_p=1.0)],
)
def test_generation_parameters_accept_boundary_values(parameters: GenerationParameters) -> None:
    assert parameters.as_payload()


@pytest.mark.parametrize(
    ("keyword", "value", "expected_message"),
    [
        ("temperature", -0.1, "temperature"),
        ("temperature", 2.1, "temperature"),
        ("top_p", 0.0, "top_p"),
        ("top_p", 1.1, "top_p"),
        ("max_output_tokens", 0, "max_output_tokens"),
    ],
)
def test_generation_parameters_reject_invalid_numeric_values(
    keyword: str, value: float | int, expected_message: str
) -> None:
    with pytest.raises(LlmConfigurationError, match=expected_message):
        GenerationParameters(**{keyword: value})


def test_generation_parameters_reject_empty_or_too_many_stop_sequences() -> None:
    with pytest.raises(LlmConfigurationError, match="must not be empty"):
        GenerationParameters(stop_sequences=("",))
    with pytest.raises(LlmConfigurationError, match="at most four"):
        GenerationParameters(stop_sequences=("a", "b", "c", "d", "e"))
