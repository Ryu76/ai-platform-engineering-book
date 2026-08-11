"""Volume 05의 선택적 FastAPI RAG 요청 어댑터다.

이 모듈은 서버를 실행하거나 네트워크 리스너를 열지 않는다. ``create_fastapi_rag_app``은
호출자가 설치한 FastAPI에 ``LocalRagApi``의 엄격한 로컬 요청·응답 계약을 연결할 뿐이며,
검색과 생성은 기존에 주입한 로컬/Mock 파이프라인에만 위임한다.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from ai_platform.rag.api import LocalRagApi
from ai_platform.rag.retrieval import RagConfigurationError, RagPipeline

FASTAPI_RAG_QUERY_PATH = "/rag/query"


def create_fastapi_rag_app(*, pipeline: RagPipeline) -> object:
    """``RagPipeline``을 FastAPI의 단일 JSON POST 엔드포인트로 연결한다.

    FastAPI는 이 저장소의 기본 의존성이 아니다. 그래서 모듈 import 자체는 안전하며,
    이 팩토리를 호출하는 시점에만 선택적 의존성을 확인한다. 호출자는 생성된 앱을 원하는
    로컬 테스트 클라이언트나 서버에 명시적으로 전달해야 한다. 이 함수는 서버 실행,
    외부 API 호출, 비밀값 로드, 배포를 수행하지 않는다.

    유효 JSON 본문은 기존 ``LocalRagApi``에 그대로 전달된다. 따라서 성공과 No-answer는
    각각 200 JSON 응답이 되고, 구조가 잘못된 요청은 안정적인 ``invalid_request`` 400
    응답이 된다. FastAPI가 JSON 본문을 파싱하지 못하거나 본문이 누락된 경우도 같은
    공개 400 계약으로 정규화한다.
    """
    api = LocalRagApi(pipeline=pipeline)
    fastapi, json_response, request_validation_error = _load_fastapi_components()
    app = fastapi.FastAPI(
        title="Volume 05 Local RAG API",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    async def invalid_json_body(_: object, __: object) -> object:
        return json_response(
            status_code=LocalRagApi.INVALID_REQUEST_STATUS,
            content={
                "error": {
                    "code": LocalRagApi.INVALID_REQUEST_CODE,
                    "message": "request payload must be valid JSON",
                }
            },
        )

    def query(payload: object) -> object:
        response = api.handle(payload)
        return json_response(status_code=response.status_code, content=response.to_payload())

    app.exception_handler(request_validation_error)(invalid_json_body)
    app.post(FASTAPI_RAG_QUERY_PATH, response_model=None)(query)
    return app


def _load_fastapi_components() -> tuple[Any, Any, Any]:
    """선택적 FastAPI 의존성을 팩토리 호출 시점에만 로드한다."""
    try:
        fastapi = cast(Any, import_module("fastapi"))
        responses = cast(Any, import_module("fastapi.responses"))
        exceptions = cast(Any, import_module("fastapi.exceptions"))
    except ModuleNotFoundError as error:
        if error.name in {"fastapi", "fastapi.responses", "fastapi.exceptions"}:
            raise RagConfigurationError(
                "FastAPI is required to create the RAG HTTP adapter; "
                "install the optional fastapi package"
            ) from error
        raise
    return fastapi, responses.JSONResponse, exceptions.RequestValidationError
