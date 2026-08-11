"""Safe, local structured request-correlation helpers for Volume 11 examples."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from json import dumps
from re import Pattern, compile
from uuid import uuid4

CorrelationIdFactory = Callable[[], str]
_REQUEST_ID_PATTERN: Pattern[str] = compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_OBSERVED_ROUTES = frozenset({"/livez", "/readyz"})


def new_request_id() -> str:
    """Return a locally generated opaque correlation identifier."""
    return uuid4().hex


def request_id_from_environ(
    environ: Mapping[str, object], request_id_factory: CorrelationIdFactory = new_request_id
) -> str:
    """Accept a bounded request ID or generate one without logging arbitrary headers."""
    candidate = environ.get("HTTP_X_REQUEST_ID", "")
    if isinstance(candidate, str) and _REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate

    generated = request_id_factory()
    if not _REQUEST_ID_PATTERN.fullmatch(generated):
        raise ValueError("request_id_factory must return a safe correlation identifier")
    return generated


def request_completion_event(*, request_id: str, path: str, status_code: int) -> str:
    """Format the allow-listed fields for one request-completed log event.

    The event deliberately omits headers other than the validated correlation ID, query
    strings, request bodies, environment values, dependency details, and exception text.
    """
    route = path if path in _OBSERVED_ROUTES else "unmatched"
    return dumps(
        {
            "event": "http_request_completed",
            "request_id": request_id,
            "route": route,
            "status_code": status_code,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
