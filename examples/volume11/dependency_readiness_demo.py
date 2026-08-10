"""Demonstrate dependency readiness policy without Docker, credentials, or network calls."""
from __future__ import annotations

from ai_platform.api.dependencies import DependencyReadiness


def main() -> None:
    """Show that each required injected check participates in readiness."""
    all_ready = DependencyReadiness(
        ("qdrant", "redis", "postgresql"),
        {"qdrant": lambda: True, "redis": lambda: True, "postgresql": lambda: True},
    )
    redis_unavailable = DependencyReadiness(
        ("qdrant", "redis", "postgresql"),
        {"qdrant": lambda: True, "redis": lambda: False, "postgresql": lambda: True},
    )

    print(f"all-required-dependencies-ready {all_ready()}")
    print(f"redis-unavailable {redis_unavailable()}")


if __name__ == "__main__":
    main()
