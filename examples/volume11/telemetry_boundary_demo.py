"""Demonstrate local telemetry minimization and exporter isolation without networking."""
from __future__ import annotations

from wsgiref.util import setup_testing_defaults

from ai_platform.api.health import HealthApplication


def request(application: HealthApplication, path: str) -> tuple[str, dict[str, str]]:
    """Invoke WSGI in memory and return only the response status and headers."""
    environment: dict[str, object] = {}
    setup_testing_defaults(environment)
    environment["REQUEST_METHOD"] = "GET"
    environment["PATH_INFO"] = path
    environment["HTTP_X_REQUEST_ID"] = "client-correlation-not-telemetry-label"
    observed_status: list[str] = []
    observed_headers: list[tuple[str, str]] = []

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        observed_status.append(status)
        observed_headers.extend(headers)

    b"".join(application(environment, start_response))
    return observed_status[0], dict(observed_headers)


def failing_exporter(_event: str) -> None:
    """Model a local exporter fault without exposing its detail to the request path."""
    raise RuntimeError("example exporter detail must not be emitted")


def main() -> None:
    """Print one minimized local event and prove an exporter error keeps a probe available."""
    exported_events: list[str] = []
    collecting_application = HealthApplication(
        readiness_check=lambda: True, telemetry_exporter=exported_events.append
    )
    status, headers = request(collecting_application, "/livez")
    print(exported_events[0])
    print(f"local-export {status} response-request-id={headers['X-Request-ID']}")

    isolated_application = HealthApplication(
        readiness_check=lambda: True, telemetry_exporter=failing_exporter
    )
    failure_status, failure_headers = request(isolated_application, "/readyz")
    print(
        "exporter-failure-isolated "
        f"{failure_status} response-request-id={failure_headers['X-Request-ID']}"
    )


if __name__ == "__main__":
    main()
