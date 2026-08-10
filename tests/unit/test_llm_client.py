from __future__ import annotations

from collections.abc import Iterator, Mapping

import pytest

from ai_platform.llm.client import (
    ChatMessage,
    GenerationParameters,
    HttpResponse,
    LlmClient,
    LlmConfigurationError,
    LlmNetworkError,
    LlmRemoteError,
    LlmResponseError,
    LlmTimeoutError,
    RetryPolicy,
    _sse_data,
)


class RecordingTransport:
    """네트워크를 사용하지 않고 요청을 기록하는 테스트 전송 계층이다."""

    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.post_json_call_count = 0
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
        self.post_json_call_count += 1
        self.url = url
        self.headers = headers
        self.payload = payload
        self.timeout_seconds = timeout_seconds
        return self.response

    def post_stream(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Iterator[HttpResponse]:
        raise AssertionError("streaming was not expected in this test")


class RecordingStreamTransport(RecordingTransport):
    """순서가 있는 Mock 스트림 이벤트와 요청을 기록한다."""

    def __init__(self, responses: list[HttpResponse]) -> None:
        super().__init__(HttpResponse(status_code=200, payload={}))
        self.responses = responses
        self.stream_call_count = 0

    def post_stream(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Iterator[HttpResponse]:
        self.stream_call_count += 1
        self.url = url
        self.headers = headers
        self.payload = payload
        self.timeout_seconds = timeout_seconds
        yield from self.responses


class ScriptedTransport(RecordingTransport):
    """완료 요청마다 응답 또는 안전한 전송 예외를 순서대로 재현한다."""

    def __init__(self, outcomes: list[HttpResponse | Exception]) -> None:
        super().__init__(HttpResponse(status_code=200, payload={}))
        self.outcomes = outcomes
        self.call_count = 0

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
        outcome = self.outcomes[self.call_count]
        self.call_count += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


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


def test_client_construction_does_not_send_until_complete_is_called() -> None:
    """Client 생성은 설정 검증만 하고 명시한 완료 요청에서만 전송한다."""
    transport = RecordingTransport(
        HttpResponse(
            status_code=200,
            payload={"choices": [{"message": {"content": "Mock 응답"}}]},
        )
    )

    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
    )

    assert transport.post_json_call_count == 0
    client.complete([ChatMessage(role="user", content="전송 시점을 검사합니다.")])
    assert transport.post_json_call_count == 1


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


def test_client_retries_transient_remote_error_then_returns_response() -> None:
    transport = ScriptedTransport(
        [
            HttpResponse(
                status_code=503,
                payload={"error": {"message": "temporarily unavailable"}},
            ),
            HttpResponse(
                status_code=200,
                payload={"choices": [{"message": {"content": "복구된 응답"}}]},
            ),
        ]
    )
    delays: list[float] = []
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.25),
        sleeper=delays.append,
    )

    response = client.complete([ChatMessage(role="user", content="상태를 알려 주세요.")])

    assert response.content == "복구된 응답"
    assert transport.call_count == 2
    assert delays == [0.25]


def test_client_does_not_retry_non_retryable_remote_error() -> None:
    transport = ScriptedTransport(
        [HttpResponse(status_code=401, payload={"error": {"message": "invalid key"}})]
    )
    delays: list[float] = []
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.25),
        sleeper=delays.append,
    )

    with pytest.raises(LlmRemoteError, match=r"\(401\): invalid key") as error:
        client.complete([ChatMessage(role="user", content="상태를 알려 주세요.")])

    assert error.value.status_code == 401
    assert transport.call_count == 1
    assert delays == []
    assert "unit-test-token" not in str(error.value)


def test_client_stops_retrying_network_and_timeout_errors_at_attempt_limit() -> None:
    transport = ScriptedTransport(
        [
            LlmNetworkError("LLM provider could not be reached"),
            LlmTimeoutError("LLM provider request timed out"),
            LlmTimeoutError("LLM provider request timed out"),
        ]
    )
    delays: list[float] = []
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.1),
        sleeper=delays.append,
    )

    with pytest.raises(LlmTimeoutError, match="timed out"):
        client.complete([ChatMessage(role="user", content="상태를 알려 주세요.")])

    assert transport.call_count == 3
    assert delays == [0.1, 0.2]


@pytest.mark.parametrize(
    "policy",
    [
        RetryPolicy(max_attempts=1, base_delay_seconds=0),
        RetryPolicy(max_attempts=5, base_delay_seconds=0.5),
    ],
)
def test_retry_policy_accepts_bounded_values(policy: RetryPolicy) -> None:
    assert policy.delay_after(1) == policy.base_delay_seconds


@pytest.mark.parametrize(
    "arguments",
    [
        {"max_attempts": 0},
        {"max_attempts": 6},
        {"max_attempts": True},
        {"base_delay_seconds": -0.1},
        {"base_delay_seconds": float("nan")},
        {"base_delay_seconds": True},
    ],
)
def test_retry_policy_rejects_unbounded_or_invalid_values(arguments: dict[str, object]) -> None:
    with pytest.raises(LlmConfigurationError):
        RetryPolicy(**arguments)


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
        ("temperature", float("nan"), "temperature"),
        ("temperature", "0.2", "temperature"),
        ("top_p", 0.0, "top_p"),
        ("top_p", 1.1, "top_p"),
        ("top_p", float("inf"), "top_p"),
        ("top_p", "0.9", "top_p"),
        ("max_output_tokens", 0, "max_output_tokens"),
        ("max_output_tokens", 12.5, "max_output_tokens"),
        ("max_output_tokens", "120", "max_output_tokens"),
    ],
)
def test_generation_parameters_reject_invalid_numeric_values(
    keyword: str, value: object, expected_message: str
) -> None:
    with pytest.raises(LlmConfigurationError, match=expected_message):
        GenerationParameters(**{keyword: value})


def test_generation_parameters_reject_empty_or_too_many_stop_sequences() -> None:
    with pytest.raises(LlmConfigurationError, match="must not be empty"):
        GenerationParameters(stop_sequences=("",))
    with pytest.raises(LlmConfigurationError, match="at most four"):
        GenerationParameters(stop_sequences=("a", "b", "c", "d", "e"))


def test_client_streams_deltas_and_final_usage_without_network() -> None:
    transport = RecordingStreamTransport(
        [
            HttpResponse(
                status_code=200,
                payload={
                    "model": "offline-test-model",
                    "choices": [{"delta": {"content": "안녕"}, "finish_reason": None}],
                },
            ),
            HttpResponse(
                status_code=200,
                payload={"choices": [{"delta": {"content": "하세요."}, "finish_reason": "stop"}]},
            ),
            HttpResponse(
                status_code=200,
                payload={"choices": [], "usage": {"prompt_tokens": 4, "completion_tokens": 3}},
            ),
        ]
    )
    client = LlmClient(model="offline-test-model", api_key="unit-test-token", transport=transport)

    chunks = list(
        client.stream(
            [ChatMessage(role="user", content="인사하세요.")],
            generation=GenerationParameters(temperature=0.2),
        )
    )

    assert "".join(chunk.delta for chunk in chunks) == "안녕하세요."
    assert chunks[1].finish_reason == "stop"
    assert chunks[2].usage is not None
    assert chunks[2].usage.input_tokens == 4
    assert transport.payload["stream"] is True
    assert transport.payload["temperature"] == 0.2


def test_client_stream_rejects_malformed_event() -> None:
    transport = RecordingStreamTransport([HttpResponse(status_code=200, payload={"choices": []})])
    client = LlmClient(model="offline-test-model", api_key="unit-test-token", transport=transport)

    with pytest.raises(LlmResponseError, match="neither choices nor usage"):
        list(client.stream([ChatMessage(role="user", content="형식을 검사합니다.")]))


def test_client_stream_rejects_non_mapping_usage_event() -> None:
    """사용량은 생략할 수 있지만 제공되면 OpenAI 호환 객체여야 한다."""
    transport = RecordingStreamTransport(
        [HttpResponse(status_code=200, payload={"choices": [], "usage": "not-an-object"})]
    )
    client = LlmClient(model="offline-test-model", api_key="unit-test-token", transport=transport)

    with pytest.raises(LlmResponseError, match="usage has an invalid shape"):
        list(client.stream([ChatMessage(role="user", content="사용량 형식을 검사합니다.")]))


def test_client_stream_surfaces_provider_error() -> None:
    transport = RecordingStreamTransport(
        [HttpResponse(status_code=503, payload={"error": {"message": "temporarily unavailable"}})]
    )
    client = LlmClient(model="offline-test-model", api_key="unit-test-token", transport=transport)

    with pytest.raises(LlmRemoteError, match=r"\(503\): temporarily unavailable"):
        list(client.stream([ChatMessage(role="user", content="상태를 알려 주세요.")]))


def test_client_never_retries_a_stream_after_a_provider_error() -> None:
    """부분 출력의 중복을 막기 위해 스트림은 명시적 재시도 정책도 사용하지 않는다."""
    transport = RecordingStreamTransport(
        [HttpResponse(status_code=503, payload={"error": {"message": "temporarily unavailable"}})]
    )
    delays: list[float] = []
    client = LlmClient(
        model="offline-test-model",
        api_key="unit-test-token",
        transport=transport,
        retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.25),
        sleeper=delays.append,
    )

    with pytest.raises(LlmRemoteError, match=r"\(503\): temporarily unavailable"):
        list(client.stream([ChatMessage(role="user", content="스트림 상태를 알려 주세요.")]))

    assert transport.stream_call_count == 1
    assert delays == []


@pytest.mark.parametrize(
    ("raw_line", "expected"),
    [
        (b"event: message\x0a", None),
        (b'data: {"choices": []}\x0a', '{"choices": []}'),
        (b"data: [DONE]\x0d\x0a", "[DONE]"),
    ],
)
def test_sse_data_extracts_only_data_rows(raw_line: bytes, expected: str | None) -> None:
    assert _sse_data(raw_line) == expected



def test_sse_data_rejects_invalid_utf8() -> None:
    with pytest.raises(LlmResponseError, match="invalid UTF-8"):
        _sse_data(b"data: \xff")
