"""Volume 11 health endpoints stay deterministic without Docker or Kubernetes."""
from __future__ import annotations

from collections.abc import Iterable
from json import loads

import pytest

from ai_platform.api.health import HealthApplication, readiness_from_environment


def invoke(
    application: HealthApplication, *, method: str = "GET", path: str = "/livez"
) -> tuple[str, dict[str, str]]:
    """Invoke the WSGI app in memory and decode its JSON contract."""
    statuses: list[str] = []

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        statuses.append(status)

    response: Iterable[bytes] = application(
        {"REQUEST_METHOD": method, "PATH_INFO": path}, start_response
    )
    return statuses[0], loads(b"".join(response))


def invoke_with_headers(
    application: HealthApplication,
    *,
    method: str = "GET",
    path: str = "/livez",
    request_id: str | None = None,
) -> tuple[str, list[tuple[str, str]], dict[str, str]]:
    """Invoke WSGI in memory while retaining the correlation response header."""
    statuses: list[str] = []
    response_headers: list[tuple[str, str]] = []
    environ: dict[str, object] = {"REQUEST_METHOD": method, "PATH_INFO": path}
    if request_id is not None:
        environ["HTTP_X_REQUEST_ID"] = request_id

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        statuses.append(status)
        response_headers.extend(headers)

    response: Iterable[bytes] = application(environ, start_response)
    return statuses[0], response_headers, loads(b"".join(response))


def test_liveness_succeeds_even_when_readiness_dependency_is_unavailable() -> None:
    """A process liveness check must not restart a running process for a dependency outage."""
    application = HealthApplication(readiness_check=lambda: False)

    status, payload = invoke(application, path="/livez")

    assert status == "200 OK"
    assert payload == {"status": "ok", "service": "ai-platform-api", "check": "liveness"}


def test_readiness_returns_service_unavailable_when_dependency_is_unavailable() -> None:
    """Traffic is withheld when the injectable readiness condition is false."""
    application = HealthApplication(readiness_check=lambda: False)

    status, payload = invoke(application, path="/readyz")

    assert status == "503 Service Unavailable"
    assert payload["status"] == "unavailable"
    assert payload["check"] == "readiness"


def test_ready_endpoint_returns_ok_when_dependency_is_ready() -> None:
    """A ready application returns a compact success contract."""
    status, payload = invoke(HealthApplication(readiness_check=lambda: True), path="/readyz")

    assert status == "200 OK"
    assert payload == {"status": "ok", "service": "ai-platform-api", "check": "readiness"}


def test_unknown_path_and_non_get_method_do_not_fall_through_to_health_checks() -> None:
    """Only GET probe routes are exposed by this minimal teaching API."""
    unknown_status, unknown_payload = invoke(HealthApplication(), path="/unknown")
    method_status, method_payload = invoke(HealthApplication(), method="POST", path="/livez")

    assert unknown_status == "404 Not Found"
    assert unknown_payload == {"status": "error", "detail": "not found"}
    assert method_status == "405 Method Not Allowed"
    assert method_payload == {"status": "error", "detail": "method not allowed"}


def test_readiness_flag_defaults_to_true_and_rejects_ambiguous_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The example has a safe deterministic default and no silently accepted typo."""
    monkeypatch.delenv("AI_PLATFORM_READY", raising=False)
    assert readiness_from_environment() is True

    monkeypatch.setenv("AI_PLATFORM_READY", "FALSE")
    assert readiness_from_environment() is False

    monkeypatch.setenv("AI_PLATFORM_READY", "sometimes")
    with pytest.raises(ValueError, match="true or false"):
        readiness_from_environment()


def test_structured_log_and_response_share_a_safe_client_correlation_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The allow-listed ID connects a response with one compact local log event."""
    caplog.set_level("INFO", logger="ai_platform.api.health")
    application = HealthApplication(readiness_check=lambda: True)

    status, headers, payload = invoke_with_headers(
        application, path="/readyz", request_id="client-example-11"
    )

    assert status == "200 OK"
    assert payload["check"] == "readiness"
    assert ("X-Request-ID", "client-example-11") in headers
    assert loads(caplog.messages[-1]) == {
        "event": "http_request_completed",
        "request_id": "client-example-11",
        "route": "/readyz",
        "status_code": 200,
    }


def test_invalid_correlation_input_is_replaced_and_unmatched_paths_are_not_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Arbitrary header and path values never become structured-log fields."""
    caplog.set_level("INFO", logger="ai_platform.api.health")
    application = HealthApplication(
        readiness_check=lambda: True, request_id_factory=lambda: "generated-example-11"
    )

    status, headers, _payload = invoke_with_headers(
        application, path="/user-input-not-logged", request_id="contains whitespace"
    )

    assert status == "404 Not Found"
    assert ("X-Request-ID", "generated-example-11") in headers
    event = loads(caplog.messages[-1])
    assert event["request_id"] == "generated-example-11"
    assert event["route"] == "unmatched"
    assert "contains whitespace" not in caplog.messages[-1]
    assert "user-input-not-logged" not in caplog.messages[-1]
