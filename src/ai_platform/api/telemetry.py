"""Local-only telemetry minimization and exporter-failure boundaries for Volume 11."""
from __future__ import annotations

from collections.abc import Callable
from json import dumps

TelemetryExporter = Callable[[str], None]
_OBSERVED_ROUTES = frozenset({"/livez", "/readyz"})


def probe_telemetry_event(*, path: str, status_code: int) -> str:
    """Serialize the fixed, low-cardinality telemetry schema for one probe result.

    This deliberately contains no request identifier, raw path, query string, body,
    headers, environment values, dependency detail, exception text, endpoint, or
    credential.  The string is a local teaching payload, not an exporter protocol.
    """
    if not 100 <= status_code <= 599:
        raise ValueError("status_code must be an HTTP status code")

    route = path if path in _OBSERVED_ROUTES else "unmatched"
    status_class = f"{status_code // 100}xx"
    return dumps(
        {
            "event": "probe_telemetry",
            "metric": {
                "name": "http_server_requests_total",
                "labels": {"route": route, "status_class": status_class},
            },
            "span": {
                "name": "health_probe",
                "attributes": {
                    "http.route": route,
                    "http.response.status_code": status_code,
                },
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def publish_probe_telemetry(
    *, path: str, status_code: int, exporter: TelemetryExporter | None
) -> bool:
    """Attempt one optional local delivery without changing request availability.

    An exporter is injected only for offline demonstrations and tests.  Its exception
    details are intentionally neither re-raised nor logged; callers receive ``False``
    and can keep serving the completed request.  This is not a retry queue, circuit
    breaker, metric endpoint, telemetry backend, or network client.
    """
    if exporter is None:
        return False

    event = probe_telemetry_event(path=path, status_code=status_code)
    try:
        exporter(event)
    except Exception:
        return False
    return True
