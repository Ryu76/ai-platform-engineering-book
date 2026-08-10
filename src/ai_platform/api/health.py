"""컨테이너와 Kubernetes Probe를 위한 외부 의존성 없는 HTTP 상태 확인 API."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from json import dumps
from os import getenv
from typing import TypeAlias

StartResponse: TypeAlias = Callable[[str, list[tuple[str, str]]], object]  # noqa: UP040
WsgiApplication: TypeAlias = Callable[[dict[str, object], StartResponse], Iterable[bytes]]  # noqa: UP040

SERVICE_NAME = "ai-platform-api"
_READY_VALUES = {"true": True, "false": False}


def readiness_from_environment() -> bool:
    """Read the example readiness flag without reading credentials or contacting a dependency."""
    value = getenv("AI_PLATFORM_READY", "true").strip().casefold()
    try:
        return _READY_VALUES[value]
    except KeyError as error:
        raise ValueError("AI_PLATFORM_READY must be true or false") from error


def _response(*, status: str, payload: dict[str, str]) -> tuple[str, list[tuple[str, str]], bytes]:
    """Create a compact JSON response with an accurate byte length header."""
    body = dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
    ]
    return status, headers, body


class HealthApplication:
    """Serve liveness and readiness endpoints from an injectable readiness boundary."""

    def __init__(self, readiness_check: Callable[[], bool] = readiness_from_environment) -> None:
        self._readiness_check = readiness_check

    def __call__(
        self, environ: dict[str, object], start_response: StartResponse
    ) -> Iterable[bytes]:
        """Return JSON for GET health routes and never expose environment values."""
        method = str(environ.get("REQUEST_METHOD", "GET"))
        path = str(environ.get("PATH_INFO", "/"))
        if method != "GET":
            status, headers, body = _response(
                status="405 Method Not Allowed",
                payload={"status": "error", "detail": "method not allowed"},
            )
        elif path == "/livez":
            status, headers, body = _response(
                status="200 OK",
                payload={"status": "ok", "service": SERVICE_NAME, "check": "liveness"},
            )
        elif path == "/readyz":
            ready = self._readiness_check()
            status, headers, body = _response(
                status="200 OK" if ready else "503 Service Unavailable",
                payload={
                    "status": "ok" if ready else "unavailable",
                    "service": SERVICE_NAME,
                    "check": "readiness",
                },
            )
        else:
            status, headers, body = _response(
                status="404 Not Found",
                payload={"status": "error", "detail": "not found"},
            )
        start_response(status, headers)
        return [body]


application: WsgiApplication = HealthApplication()
