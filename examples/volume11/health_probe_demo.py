"""Run the Volume 11 health endpoints locally without Docker or Kubernetes."""
from __future__ import annotations

from wsgiref.util import setup_testing_defaults

from ai_platform.api.health import HealthApplication


def request(application: HealthApplication, path: str) -> tuple[str, bytes]:
    """Call the WSGI application in memory so no TCP listener is required."""
    environment: dict[str, object] = {}
    setup_testing_defaults(environment)
    environment["REQUEST_METHOD"] = "GET"
    environment["PATH_INFO"] = path
    observed_status: list[str] = []

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        observed_status.append(status)

    body = b"".join(application(environment, start_response))
    return observed_status[0], body


def main() -> None:
    """Print liveness and readiness responses using a deterministic ready dependency."""
    application = HealthApplication(readiness_check=lambda: True)
    for path in ("/livez", "/readyz"):
        status, body = request(application, path)
        print(f"{path} {status} {body.decode('utf-8')}")


if __name__ == "__main__":
    main()
