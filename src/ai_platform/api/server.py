"""Run the Volume 11 probe example with Python's standard-library WSGI server."""
from __future__ import annotations

from argparse import ArgumentParser, Namespace
from wsgiref.simple_server import make_server

from ai_platform.api.health import HealthApplication


def parse_arguments() -> Namespace:
    """Parse an explicit bind address for local container demonstrations."""
    parser = ArgumentParser(description="Run the AI Platform health-probe example server.")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host; default: 0.0.0.0")
    parser.add_argument("--port", default=8080, type=int, help="Bind port; default: 8080")
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return arguments


def main() -> None:
    """Start the local server; this command does not contact an LLM or a cluster."""
    arguments = parse_arguments()
    with make_server(arguments.host, arguments.port, HealthApplication()) as server:
        print(f"Health probe example listening on http://{arguments.host}:{arguments.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
