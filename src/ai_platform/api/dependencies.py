"""Non-network readiness policy helpers for the Volume 11 Kubernetes examples."""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from os import getenv

DependencyCheck = Callable[[], bool]
_REQUIRED_DEPENDENCIES_ENV = "AI_PLATFORM_REQUIRED_DEPENDENCIES"
_READY_DEPENDENCIES_ENV = "AI_PLATFORM_READY_DEPENDENCIES"


def dependency_names_from_environment(variable_name: str) -> tuple[str, ...]:
    """Read a comma-separated, non-secret dependency-name list from the environment.

    The names are a readiness policy only. They are not hostnames, URLs, credentials,
    or instructions to make a network connection.
    """
    raw_names = getenv(variable_name, "")
    names = tuple(name.strip().casefold() for name in raw_names.split(",") if name.strip())
    if len(set(names)) != len(names):
        raise ValueError(f"{variable_name} must not contain duplicate dependency names")
    if any(not name.replace("-", "").isalnum() for name in names):
        raise ValueError(f"{variable_name} names may contain only letters, digits, and hyphens")
    return names


def required_dependencies_from_environment() -> tuple[str, ...]:
    """Return the declared dependency names without reading connection details."""
    return dependency_names_from_environment(_REQUIRED_DEPENDENCIES_ENV)


def ready_dependencies_from_environment() -> tuple[str, ...]:
    """Return the example-only ready dependency names without contacting a service."""
    return dependency_names_from_environment(_READY_DEPENDENCIES_ENV)


def environment_dependency_readiness() -> bool:
    """Evaluate the example policy using only declared names, not live network checks."""
    required = set(required_dependencies_from_environment())
    ready = set(ready_dependencies_from_environment())
    return required.issubset(ready)


class DependencyReadiness:
    """Combine injected dependency checks while keeping failure details out of probe output."""

    def __init__(
        self, required_dependencies: Iterable[str], checks: Mapping[str, DependencyCheck]
    ) -> None:
        self._required_dependencies = tuple(required_dependencies)
        self._checks = dict(checks)
        if len(set(self._required_dependencies)) != len(self._required_dependencies):
            raise ValueError("required dependency names must be unique")
        missing_checks = set(self._required_dependencies) - self._checks.keys()
        if missing_checks:
            raise ValueError("every required dependency needs an injected check")

    def __call__(self) -> bool:
        """Return false for a failed or exceptional check without exposing its details."""
        for dependency_name in self._required_dependencies:
            try:
                if not self._checks[dependency_name]():
                    return False
            except Exception:
                return False
        return True
