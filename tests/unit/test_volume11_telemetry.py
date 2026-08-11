"""Volume 11 telemetry stays local, low-cardinality, and isolated from probe availability."""
from __future__ import annotations

from collections.abc import Iterable
from json import loads

import pytest

from ai_platform.api.health import HealthApplication
from ai_platform.api.telemetry import probe_telemetry_event, publish_probe_telemetry


def invoke(
    application: HealthApplication, *, path: str, request_id: str = "client-example-11"
) -> tuple[str, dict[str, str]]:
    """Call the WSGI probe in memory while keeping response headers."""
    statuses: list[str] = []
    headers: list[tuple[str, str]] = []

    def start_response(status: str, response_headers: list[tuple[str, str]]) -> None:
        statuses.append(status)
        headers.extend(response_headers)

    response: Iterable[bytes] = application(
        {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "HTTP_X_REQUEST_ID": request_id,
        },
        start_response,
    )
    b"".join(response)
    return statuses[0], dict(headers)


def test_probe_telemetry_schema_is_fixed_and_omits_high_cardinality_request_input() -> None:
    """Metric labels and span attributes classify a probe without retaining raw input."""
    event = probe_telemetry_event(path="/private/path?token=not-recorded", status_code=503)

    assert loads(event) == {
        "event": "probe_telemetry",
        "metric": {
            "name": "http_server_requests_total",
            "labels": {"route": "unmatched", "status_class": "5xx"},
        },
        "span": {
            "name": "health_probe",
            "attributes": {"http.route": "unmatched", "http.response.status_code": 503},
        },
    }
    assert "private/path" not in event
    assert "token" not in event


def test_probe_telemetry_rejects_non_http_status_codes() -> None:
    """The local schema cannot be populated with an arbitrary status label."""
    with pytest.raises(ValueError, match="HTTP status"):
        probe_telemetry_event(path="/livez", status_code=99)


def test_health_probe_exports_only_minimized_event_without_a_correlation_label() -> None:
    """A successful injected exporter gets one safe event after the probe completes."""
    exported_events: list[str] = []
    application = HealthApplication(
        readiness_check=lambda: True, telemetry_exporter=exported_events.append
    )

    status, headers = invoke(application, path="/livez", request_id="client-example-11")

    assert status == "200 OK"
    assert headers["X-Request-ID"] == "client-example-11"
    assert len(exported_events) == 1
    event = loads(exported_events[0])
    assert event["metric"]["labels"] == {"route": "/livez", "status_class": "2xx"}
    assert event["span"]["attributes"] == {
        "http.route": "/livez",
        "http.response.status_code": 200,
    }
    assert "client-example-11" not in exported_events[0]


def test_exporter_failure_is_not_logged_or_allowed_to_change_readiness_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Exporter detail cannot leak and an observability fault cannot fail a healthy probe."""
    caplog.set_level("INFO", logger="ai_platform.api.health")

    def failing_exporter(_event: str) -> None:
        raise RuntimeError("example exporter detail must not be emitted")

    application = HealthApplication(
        readiness_check=lambda: True, telemetry_exporter=failing_exporter
    )
    status, headers = invoke(application, path="/readyz")

    assert status == "200 OK"
    assert headers["X-Request-ID"] == "client-example-11"
    assert "example exporter detail must not be emitted" not in caplog.text
    assert publish_probe_telemetry(
        path="/livez", status_code=200, exporter=failing_exporter
    ) is False
