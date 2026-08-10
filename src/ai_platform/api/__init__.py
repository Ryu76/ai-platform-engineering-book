"""Volume 11에서 컨테이너 운영을 위해 제공하는 최소 HTTP API."""

from ai_platform.api.health import HealthApplication, readiness_from_environment

__all__ = ["HealthApplication", "readiness_from_environment"]
