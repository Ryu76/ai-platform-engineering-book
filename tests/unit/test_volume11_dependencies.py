"""Volume 11 dependency readiness policies remain local and deterministic."""
from __future__ import annotations

import pytest
from test_volume11_health import invoke

from ai_platform.api.dependencies import (
    DependencyReadiness,
    environment_dependency_readiness,
    required_dependencies_from_environment,
)
from ai_platform.api.health import HealthApplication, readiness_from_environment


def test_injected_dependency_checks_require_every_required_service_to_be_ready() -> None:
    """A failed required check excludes the API without making a network request."""
    readiness = DependencyReadiness(
        ("qdrant", "redis"), {"qdrant": lambda: True, "redis": lambda: False}
    )

    assert readiness() is False


def test_exception_from_an_injected_dependency_check_becomes_not_ready() -> None:
    """Probe calls fail closed rather than exposing an implementation exception."""
    readiness = DependencyReadiness(("postgresql",), {"postgresql": _raise_timeout})

    assert readiness() is False
    status, payload = invoke(HealthApplication(readiness_check=readiness), path="/readyz")
    assert status == "503 Service Unavailable"
    assert payload == {
        "status": "unavailable",
        "service": "ai-platform-api",
        "check": "readiness",
    }


def test_required_dependency_requires_an_injected_check() -> None:
    """A misspelled or omitted checker cannot silently mark the service ready."""
    with pytest.raises(ValueError, match="every required dependency"):
        DependencyReadiness(("redis",), {})


def test_environment_policy_uses_non_secret_dependency_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ConfigMap-style policy evaluates labels only and never opens a connection."""
    monkeypatch.setenv("AI_PLATFORM_READY", "true")
    monkeypatch.setenv("AI_PLATFORM_REQUIRED_DEPENDENCIES", "qdrant,redis,postgresql")
    monkeypatch.setenv("AI_PLATFORM_READY_DEPENDENCIES", "qdrant,postgresql")

    assert required_dependencies_from_environment() == ("qdrant", "redis", "postgresql")
    assert environment_dependency_readiness() is False
    assert readiness_from_environment() is False

    monkeypatch.setenv("AI_PLATFORM_READY_DEPENDENCIES", "qdrant,redis,postgresql")
    assert environment_dependency_readiness() is True
    assert readiness_from_environment() is True


def test_environment_policy_rejects_duplicate_or_invalid_dependency_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed policy values are not treated as healthy defaults."""
    monkeypatch.setenv("AI_PLATFORM_REQUIRED_DEPENDENCIES", "redis,redis")
    with pytest.raises(ValueError, match="must not contain duplicate"):
        required_dependencies_from_environment()

    monkeypatch.setenv("AI_PLATFORM_REQUIRED_DEPENDENCIES", "redis,not/a-name")
    with pytest.raises(ValueError, match="letters, digits, and hyphens"):
        required_dependencies_from_environment()


def _raise_timeout() -> bool:
    """Model a failed injected check without contacting an external system."""
    raise TimeoutError("example timeout")
