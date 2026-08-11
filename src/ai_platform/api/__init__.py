"""Volume 11에서 컨테이너 운영을 위해 제공하는 최소 HTTP API."""

from ai_platform.api.correlation import (
    new_request_id,
    request_completion_event,
    request_id_from_environ,
)
from ai_platform.api.dependencies import (
    DependencyReadiness,
    environment_dependency_readiness,
    required_dependencies_from_environment,
)
from ai_platform.api.health import HealthApplication, readiness_from_environment

__all__ = [
    "DependencyReadiness",
    "HealthApplication",
    "environment_dependency_readiness",
    "new_request_id",
    "readiness_from_environment",
    "required_dependencies_from_environment",
    "request_completion_event",
    "request_id_from_environ",
]
