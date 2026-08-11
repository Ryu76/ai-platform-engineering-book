"""Demonstrate local structured correlation logging without a telemetry backend."""
from __future__ import annotations

from logging import INFO, Formatter, Logger, StreamHandler
from sys import stdout
from wsgiref.util import setup_testing_defaults

from ai_platform.api.health import HealthApplication


def request(
    application: HealthApplication, path: str, request_id: str | None
) -> tuple[str, dict[str, str]]:
    """Call WSGI in memory and return the status plus response headers."""
    environment: dict[str, object] = {}
    setup_testing_defaults(environment)
    environment["REQUEST_METHOD"] = "GET"
    environment["PATH_INFO"] = path
    if request_id is not None:
        environment["HTTP_X_REQUEST_ID"] = request_id
    observed_status: list[str] = []
    observed_headers: list[tuple[str, str]] = []

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        observed_status.append(status)
        observed_headers.extend(headers)

    b"".join(application(environment, start_response))
    return observed_status[0], dict(observed_headers)


def local_logger() -> Logger:
    """Create an example logger that writes JSON events only to this process's stdout."""
    logger = Logger("volume11.correlation.demo", level=INFO)
    handler = StreamHandler(stdout)
    handler.setFormatter(Formatter("%(message)s"))
    logger.addHandler(handler)
    return logger


def main() -> None:
    """Show accepted, generated, and rejected correlation-ID behavior without TCP."""
    request_ids = iter(("generated-example-11", "generated-after-invalid-11"))
    application = HealthApplication(
        readiness_check=lambda: True,
        logger=local_logger(),
        request_id_factory=lambda: next(request_ids),
    )
    for label, request_id in (
        ("accepted", "client-example-11"),
        ("generated", None),
        ("rejected", "contains whitespace"),
    ):
        status, headers = request(application, "/livez", request_id)
        print(f"{label} {status} response-request-id={headers['X-Request-ID']}")


if __name__ == "__main__":
    main()
