"""Volume 05 로컬 RAG의 프레임워크 독립 API 입력·출력 계약이다.

이 모듈은 HTTP 서버, FastAPI, 네트워크 클라이언트, 제공자 SDK를 만들지 않는다.
호출자는 ``LocalRagApi.handle``에 역직렬화한 로컬 JSON 같은 값을 전달하고,
검증된 상태 코드와 JSON 호환 응답을 받을 수 있다. 따라서 웹 프레임워크를 붙이기 전에도
Mock 생성기를 사용해 요청·응답 경계를 결정론적으로 테스트할 수 있다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from ai_platform.rag.retrieval import Citation, RagConfigurationError, RagPipeline


class RagRequestError(ValueError):
    """공개 RAG API 요청이 명시된 입력 계약을 벗어날 때 발생한다."""


@dataclass(frozen=True, slots=True)
class RagQueryRequest:
    """로컬 RAG 질의 API가 허용하는 유일한 요청 형식이다."""

    query: str
    top_k: int = 3

    def __post_init__(self) -> None:
        if not isinstance(self.query, str) or not self.query.strip():
            raise RagRequestError("query must be a non-empty string")
        if (
            isinstance(self.top_k, bool)
            or not isinstance(self.top_k, int)
            or not 1 <= self.top_k <= 20
        ):
            raise RagRequestError("top_k must be an integer between 1 and 20")

    @classmethod
    def from_payload(cls, payload: object) -> RagQueryRequest:
        """역직렬화된 JSON 같은 값을 엄격한 요청 객체로 검증한다.

        요청은 ``query``와 선택적 ``top_k``만 포함할 수 있다. 알 수 없는 필드는
        무시하지 않으므로 API 클라이언트의 오타나 의도하지 않은 입력을 조기에 드러낸다.
        """
        if not isinstance(payload, Mapping):
            raise RagRequestError("request payload must be an object")
        allowed_fields: Final = {"query", "top_k"}
        field_names = set(payload)
        if not all(isinstance(field_name, str) for field_name in field_names):
            raise RagRequestError("request payload field names must be strings")
        unexpected_fields = sorted(field_names - allowed_fields)
        if unexpected_fields:
            raise RagRequestError(
                f"request payload contains unsupported fields: {', '.join(unexpected_fields)}"
            )
        if "query" not in payload:
            raise RagRequestError("request payload must include query")
        return cls(query=payload["query"], top_k=payload.get("top_k", 3))


@dataclass(frozen=True, slots=True)
class RagCitationResponse:
    """원문 추적에 필요한 인용의 JSON 호환 API 표현이다."""

    label: int
    chunk_id: str
    title: str
    source_uri: str
    start_offset: int
    end_offset: int

    @classmethod
    def from_citation(cls, citation: Citation) -> RagCitationResponse:
        """도메인 인용을 필드 누락 없이 공개 응답으로 변환한다."""
        return cls(
            label=citation.label,
            chunk_id=citation.chunk_id,
            title=citation.title,
            source_uri=citation.source_uri,
            start_offset=citation.start_offset,
            end_offset=citation.end_offset,
        )

    def to_payload(self) -> dict[str, int | str]:
        """JSON 인코더에 바로 전달할 수 있는 인용 객체를 반환한다."""
        return {
            "label": self.label,
            "chunk_id": self.chunk_id,
            "title": self.title,
            "source_uri": self.source_uri,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass(frozen=True, slots=True)
class RagAnswerResponse:
    """성공한 RAG 요청의 답변·No-answer·인용 계약이다."""

    answer: str
    no_answer: bool
    citations: tuple[RagCitationResponse, ...]

    def __post_init__(self) -> None:
        if not self.answer.strip():
            raise RagConfigurationError("RAG API answer must not be empty")
        if self.no_answer and self.citations:
            raise RagConfigurationError("No-answer API responses must not contain citations")
        if not self.no_answer and not self.citations:
            raise RagConfigurationError("answered API responses must contain citations")

    def to_payload(self) -> dict[str, object]:
        """성공 응답을 고정된 JSON 객체 형태로 반환한다."""
        return {
            "answer": self.answer,
            "no_answer": self.no_answer,
            "citations": [citation.to_payload() for citation in self.citations],
        }


@dataclass(frozen=True, slots=True)
class RagErrorResponse:
    """잘못된 요청을 위한 안정적인 공개 오류 표현이다."""

    code: str
    message: str

    def to_payload(self) -> dict[str, str]:
        """오류 상세를 JSON 객체로 반환한다."""
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class RagEndpointResponse:
    """프레임워크 어댑터가 HTTP 응답으로 바꿀 수 있는 상태·본문 쌍이다."""

    status_code: int
    answer: RagAnswerResponse | None = None
    error: RagErrorResponse | None = None

    def __post_init__(self) -> None:
        has_answer = self.answer is not None
        has_error = self.error is not None
        if has_answer == has_error:
            raise RagConfigurationError("endpoint response must contain exactly one body variant")
        if has_answer and self.status_code != 200:
            raise RagConfigurationError("successful endpoint responses must use status 200")
        if has_error and self.status_code != 400:
            raise RagConfigurationError("invalid request responses must use status 400")

    def to_payload(self) -> dict[str, object]:
        """성공 또는 오류의 안정적인 외부 JSON 객체를 반환한다."""
        if self.answer is not None:
            return self.answer.to_payload()
        if self.error is not None:
            return {"error": self.error.to_payload()}
        raise AssertionError("validated endpoint response has a body variant")


class LocalRagApi:
    """``RagPipeline``을 로컬 JSON 요청·응답 계약으로 감싼 프레임워크 독립 경계다."""

    INVALID_REQUEST_STATUS: Final = 400
    SUCCESS_STATUS: Final = 200
    INVALID_REQUEST_CODE: Final = "invalid_request"

    def __init__(self, *, pipeline: RagPipeline) -> None:
        if not isinstance(pipeline, RagPipeline):
            raise RagConfigurationError("pipeline must be a RagPipeline")
        self._pipeline = pipeline

    def answer(self, request: RagQueryRequest) -> RagAnswerResponse:
        """검증된 요청을 실행하고 인용 가능한 도메인 결과를 공개 응답으로 만든다."""
        if not isinstance(request, RagQueryRequest):
            raise RagRequestError("request must be a RagQueryRequest")
        result = self._pipeline.answer(request.query, top_k=request.top_k)
        return RagAnswerResponse(
            answer=result.text,
            no_answer=result.no_answer,
            citations=tuple(
                RagCitationResponse.from_citation(citation) for citation in result.citations
            ),
        )

    def handle(self, payload: object) -> RagEndpointResponse:
        """비신뢰 요청을 200 성공 또는 공개 가능한 400 오류로 변환한다.

        검색·생성 내부 오류는 숨기지 않는다. 이 메서드는 클라이언트 입력 오류만 400으로
        분류하므로 운영 어댑터가 실제 결함을 별도 관찰·처리할 수 있다.
        """
        try:
            request = RagQueryRequest.from_payload(payload)
        except RagRequestError as error:
            return RagEndpointResponse(
                status_code=self.INVALID_REQUEST_STATUS,
                error=RagErrorResponse(code=self.INVALID_REQUEST_CODE, message=str(error)),
            )
        return RagEndpointResponse(status_code=self.SUCCESS_STATUS, answer=self.answer(request))
