"""외부 API를 명시적으로 호출하는 OpenAI 호환 LLM 클라이언트."""
from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from math import isfinite
from time import sleep
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LlmConfigurationError(ValueError):
    """필수 설정이 없거나 호출 인자가 유효하지 않을 때 발생한다."""


class LlmNetworkError(ConnectionError):
    """원격 제공자에 연결하지 못했을 때 발생한다."""


class LlmTimeoutError(TimeoutError):
    """원격 제공자가 설정한 시간 안에 응답하지 않았을 때 발생한다."""


class LlmRemoteError(RuntimeError):
    """원격 제공자가 HTTP 오류 응답을 반환했을 때 발생한다."""

    def __init__(self, message: str, *, status_code: int) -> None:
        """재시도 정책이 판단할 HTTP 상태 코드를 안전하게 보관한다."""
        super().__init__(message)
        self.status_code = status_code


class LlmResponseError(RuntimeError):
    """제공자 응답이 예상한 OpenAI 호환 형식이 아닐 때 발생한다."""


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """대화의 역할과 텍스트 내용을 나타낸다."""

    role: str
    content: str

    def __post_init__(self) -> None:
        """지원하는 역할과 비어 있지 않은 내용을 검증한다."""
        if self.role not in {"system", "user", "assistant"}:
            raise LlmConfigurationError("message role must be system, user, or assistant")
        if not self.content.strip():
            raise LlmConfigurationError("message content must not be empty")


@dataclass(frozen=True, slots=True)
class GenerationParameters:
    """재현 가능한 텍스트 생성을 위해 명시적으로 선택하는 파라미터다."""

    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    stop_sequences: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """제공자에 요청하기 전에 안전한 공통 범위를 검증한다."""
        if self.temperature is not None and (
            isinstance(self.temperature, bool) or not 0.0 <= self.temperature <= 2.0
        ):
            raise LlmConfigurationError("temperature must be between 0 and 2")
        if self.top_p is not None and (
            isinstance(self.top_p, bool) or not 0.0 < self.top_p <= 1.0
        ):
            raise LlmConfigurationError("top_p must be greater than 0 and at most 1")
        if self.max_output_tokens is not None and (
            isinstance(self.max_output_tokens, bool) or self.max_output_tokens <= 0
        ):
            raise LlmConfigurationError("max_output_tokens must be a positive integer")
        if len(self.stop_sequences) > 4:
            raise LlmConfigurationError("at most four stop sequences are supported")
        if any(not sequence.strip() for sequence in self.stop_sequences):
            raise LlmConfigurationError("stop sequences must not be empty")

    def as_payload(self) -> dict[str, object]:
        """선택한 값만 OpenAI Chat Completions 호환 JSON으로 변환한다."""
        payload: dict[str, object] = {}
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.top_p is not None:
            payload["top_p"] = self.top_p
        if self.max_output_tokens is not None:
            payload["max_tokens"] = self.max_output_tokens
        if self.stop_sequences:
            payload["stop"] = list(self.stop_sequences)
        return payload


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """명시적으로 선택하는 제한된 완료 요청 재시도 정책이다."""

    max_attempts: int = 3
    base_delay_seconds: float = 0.5

    def __post_init__(self) -> None:
        """무한 재시도와 음수 대기 시간을 요청 전에 차단한다."""
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= 5
        ):
            raise LlmConfigurationError("max_attempts must be an integer between 1 and 5")
        if (
            isinstance(self.base_delay_seconds, bool)
            or not isinstance(self.base_delay_seconds, (int, float))
            or not isfinite(self.base_delay_seconds)
            or self.base_delay_seconds < 0
        ):
            raise LlmConfigurationError("base_delay_seconds must be a nonnegative number")

    def delay_after(self, failed_attempt: int) -> float:
        """첫 실패 뒤 기본 대기부터 시작하는 제한된 지수 백오프를 반환한다."""
        delay = float(self.base_delay_seconds)
        for _ in range(failed_attempt - 1):
            delay *= 2
        return delay


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """제공자가 반환한 입력·출력 토큰 사용량이다."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True, slots=True)
class LlmResponse:
    """최소한의 텍스트 응답과 사용량을 제공한다."""

    content: str
    model: str
    usage: TokenUsage


@dataclass(frozen=True, slots=True)
class StreamChunk:
    """스트리밍 응답에서 수신한 텍스트 조각과 종료 정보를 나타낸다."""

    delta: str
    model: str
    finish_reason: str | None
    usage: TokenUsage | None


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """전송 계층이 반환하는 HTTP 상태와 JSON 객체다."""

    status_code: int
    payload: Mapping[str, object]


class JsonTransport(Protocol):
    """테스트에서 네트워크 없이 대체할 수 있는 JSON 전송 경계다."""

    def post_json(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> HttpResponse:
        """JSON POST 요청을 전송하고 HTTP 응답을 반환한다."""


class StreamTransport(Protocol):
    """테스트에서 네트워크 없이 대체할 수 있는 스트리밍 전송 경계다."""

    def post_stream(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Iterator[HttpResponse]:
        """SSE 이벤트마다 HTTP 상태와 JSON 객체를 순서대로 반환한다."""


class LlmTransport(JsonTransport, StreamTransport, Protocol):
    """일반 완료와 스트리밍을 함께 지원하는 LLM 전송 경계다."""


class UrllibJsonTransport:
    """표준 라이브러리만 사용하는 동기 JSON 전송 구현체다."""

    def post_json(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> HttpResponse:
        """POST 요청을 보내되 네트워크 실패를 비밀값 없는 예외로 변환한다."""
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as raw_response:  # noqa: S310
                return HttpResponse(
                    status_code=raw_response.status,
                    payload=_decode_json_mapping(raw_response.read()),
                )
        except HTTPError as error:
            return HttpResponse(
                status_code=error.code,
                payload=_decode_json_or_empty(error.read()),
            )
        except TimeoutError as error:
            raise LlmTimeoutError("LLM provider request timed out") from error
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise LlmTimeoutError("LLM provider request timed out") from error
            raise LlmNetworkError("LLM provider could not be reached") from error

    def post_stream(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, object],
        timeout_seconds: float,
    ) -> Iterator[HttpResponse]:
        """OpenAI 호환 SSE 응답을 JSON 이벤트 단위로 순차 변환한다."""
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=dict(headers),
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as raw_response:  # noqa: S310
                for raw_line in raw_response:
                    event = _sse_data(raw_line)
                    if event is None:
                        continue
                    if event == "[DONE]":
                        return
                    yield HttpResponse(
                        status_code=raw_response.status,
                        payload=_decode_json_mapping(event.encode("utf-8")),
                    )
        except HTTPError as error:
            yield HttpResponse(
                status_code=error.code,
                payload=_decode_json_or_empty(error.read()),
            )
        except TimeoutError as error:
            raise LlmTimeoutError("LLM provider stream timed out") from error
        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise LlmTimeoutError("LLM provider stream timed out") from error
            raise LlmNetworkError("LLM provider could not be reached") from error


class LlmClient:
    """명시적 `complete` 호출에서만 원격 LLM API를 사용하는 클라이언트다."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
        transport: LlmTransport | None = None,
        retry_policy: RetryPolicy | None = None,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        """설정을 검증하고 선택적으로 테스트용 전송 계층과 재시도 대기 함수를 주입한다."""
        if not model.strip():
            raise LlmConfigurationError("LLM_MODEL must be configured")
        if not api_key:
            raise LlmConfigurationError("OPENAI_API_KEY must be configured before a live call")
        if not base_url.startswith(("https://", "http://")):
            raise LlmConfigurationError("LLM_BASE_URL must start with http:// or https://")
        if timeout_seconds <= 0:
            raise LlmConfigurationError("timeout_seconds must be greater than zero")

        self._model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport or UrllibJsonTransport()
        self._retry_policy = retry_policy
        self._sleeper = sleeper

    def complete(
        self,
        messages: list[ChatMessage],
        *,
        generation: GenerationParameters | None = None,
    ) -> LlmResponse:
        """메시지를 전송하고, 명시한 정책에 한해서만 안전하게 재시도한다."""
        if not messages:
            raise LlmConfigurationError("at least one message is required")

        attempt = 1
        while True:
            try:
                return self._complete_once(messages, generation=generation)
            except (LlmNetworkError, LlmTimeoutError, LlmRemoteError) as error:
                if not self._should_retry(error, failed_attempt=attempt):
                    raise
                policy = self._retry_policy
                if policy is None:  # pragma: no cover - _should_retry가 먼저 보장한다.
                    raise
                self._sleeper(policy.delay_after(attempt))
                attempt += 1

    def _complete_once(
        self,
        messages: list[ChatMessage],
        *,
        generation: GenerationParameters | None,
    ) -> LlmResponse:
        """단일 완료 요청을 보내고 재시도 여부와 무관한 응답 계약을 해석한다."""
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
        }
        if generation is not None:
            payload.update(generation.as_payload())
        response = self._transport.post_json(
            url=f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout_seconds=self._timeout_seconds,
        )
        if response.status_code < 200 or response.status_code >= 300:
            raise LlmRemoteError(_remote_error_message(response), status_code=response.status_code)
        return _parse_completion(response.payload, requested_model=self._model)

    def _should_retry(
        self,
        error: LlmNetworkError | LlmTimeoutError | LlmRemoteError,
        *,
        failed_attempt: int,
    ) -> bool:
        """일시 오류만 최대 시도 횟수 전까지 재시도할지 판단한다."""
        policy = self._retry_policy
        if policy is None or failed_attempt >= policy.max_attempts:
            return False
        if isinstance(error, (LlmNetworkError, LlmTimeoutError)):
            return True
        return error.status_code in {429, 500, 502, 503, 504}

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        generation: GenerationParameters | None = None,
    ) -> Iterator[StreamChunk]:
        """텍스트 조각을 순서대로 반환하며 호출자에게 출력 시점을 맡긴다."""
        if not messages:
            raise LlmConfigurationError("at least one message is required")

        payload: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
            "stream": True,
        }
        if generation is not None:
            payload.update(generation.as_payload())

        for response in self._transport.post_stream(
            url=f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
            timeout_seconds=self._timeout_seconds,
        ):
            if response.status_code < 200 or response.status_code >= 300:
                raise LlmRemoteError(
                    _remote_error_message(response), status_code=response.status_code
                )
            yield _parse_stream_chunk(response.payload, requested_model=self._model)


def _decode_json_mapping(body: bytes) -> Mapping[str, object]:
    """HTTP 본문이 JSON 객체인지 확인해 반환한다."""
    try:
        decoded: object = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LlmResponseError("LLM provider returned invalid JSON") from error
    if not isinstance(decoded, dict):
        raise LlmResponseError("LLM provider JSON response must be an object")
    return cast(Mapping[str, object], decoded)


def _decode_json_or_empty(body: bytes) -> Mapping[str, object]:
    """오류 본문이 JSON이 아니어도 상태 코드를 보존하도록 빈 객체를 반환한다."""
    try:
        return _decode_json_mapping(body)
    except LlmResponseError:
        return {}


def _sse_data(raw_line: bytes) -> str | None:
    """SSE의 단일 ``data:`` 행에서 내용만 추출하고 다른 제어 행은 무시한다."""
    try:
        line = raw_line.decode("utf-8").strip()
    except UnicodeDecodeError as error:
        raise LlmResponseError("LLM provider returned invalid UTF-8 stream data") from error
    if not line.startswith("data:"):
        return None
    return line.removeprefix("data:").strip()


def _parse_completion(payload: Mapping[str, object], *, requested_model: str) -> LlmResponse:
    """Chat Completions 응답에서 첫 번째 텍스트와 사용량을 추출한다."""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LlmResponseError("LLM response does not contain choices")
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise LlmResponseError("LLM response choice has an invalid shape")
    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise LlmResponseError("LLM response choice does not contain a message")
    content = message.get("content")
    if not isinstance(content, str):
        raise LlmResponseError("LLM response message does not contain text content")

    response_model = payload.get("model")
    model = response_model if isinstance(response_model, str) else requested_model
    usage = payload.get("usage")
    usage_mapping = usage if isinstance(usage, Mapping) else {}
    return LlmResponse(
        content=content,
        model=model,
        usage=TokenUsage(
            input_tokens=_nonnegative_int(usage_mapping.get("prompt_tokens")),
            output_tokens=_nonnegative_int(usage_mapping.get("completion_tokens")),
        ),
    )


def _parse_stream_chunk(payload: Mapping[str, object], *, requested_model: str) -> StreamChunk:
    """OpenAI 호환 스트림 이벤트에서 텍스트 delta와 선택적 사용량을 추출한다."""
    response_model = payload.get("model")
    model = response_model if isinstance(response_model, str) else requested_model
    usage = _parse_optional_usage(payload.get("usage"))
    choices = payload.get("choices")
    if not isinstance(choices, list):
        raise LlmResponseError("LLM stream response does not contain choices")
    if not choices:
        if usage is None:
            raise LlmResponseError("LLM stream response has neither choices nor usage")
        return StreamChunk(delta="", model=model, finish_reason=None, usage=usage)
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise LlmResponseError("LLM stream response choice has an invalid shape")
    delta = first_choice.get("delta")
    if not isinstance(delta, Mapping):
        raise LlmResponseError("LLM stream response choice does not contain a delta")
    content = delta.get("content", "")
    if not isinstance(content, str):
        raise LlmResponseError("LLM stream response delta does not contain text content")
    finish_reason = first_choice.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise LlmResponseError("LLM stream response has an invalid finish reason")
    return StreamChunk(delta=content, model=model, finish_reason=finish_reason, usage=usage)


def _parse_optional_usage(value: object) -> TokenUsage | None:
    """스트림 마지막 이벤트의 선택적 사용량을 읽는다."""
    if not isinstance(value, Mapping):
        return None
    return TokenUsage(
        input_tokens=_nonnegative_int(value.get("prompt_tokens")),
        output_tokens=_nonnegative_int(value.get("completion_tokens")),
    )


def _nonnegative_int(value: object) -> int:
    """누락되었거나 비정상인 사용량은 0으로 안전하게 처리한다."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return 0


def _remote_error_message(response: HttpResponse) -> str:
    """원격 오류 설명은 간단히 만들고 요청 비밀값은 포함하지 않는다."""
    error = response.payload.get("error")
    if isinstance(error, Mapping):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return f"LLM provider rejected the request ({response.status_code}): {message}"
    return f"LLM provider rejected the request ({response.status_code})"
