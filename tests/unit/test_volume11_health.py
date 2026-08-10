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
