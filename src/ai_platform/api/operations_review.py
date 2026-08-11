"""Local-only operations review helpers for the Volume 11 mini project."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ai_platform.api.health import HealthApplication


def _invoke(application: HealthApplication, *, path: str) -> str:
    """Call a health route in memory and return its HTTP status without request data."""
    statuses: list[str] = []

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        statuses.append(status)

    response: Iterable[bytes] = application(
        {"REQUEST_METHOD": "GET", "PATH_INFO": path}, start_response
    )
    b"".join(response)
    if len(statuses) != 1:
        raise RuntimeError("local WSGI review did not receive exactly one response status")
    return statuses[0]


def render_only_artifact_checks(repository_root: Path) -> dict[str, bool]:
    """Check the teaching artifacts as text without invoking Docker or Kubernetes.

    These checks are intentionally narrow.  They establish that the mini project uses
    placeholders and render-only boundaries; they do not prove a cluster deployment,
    image availability, dependency connectivity, or production readiness.
    """
    deployment = (repository_root / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")
    base_kustomization = (repository_root / "k8s/volume11/kustomization.yaml").read_text(
        encoding="utf-8"
    )
    compose = (repository_root / "docker/volume11/compose.dependencies.yaml").read_text(
        encoding="utf-8"
    )
    batch = (repository_root / "k8s/volume11/batch/cronjob.yaml").read_text(encoding="utf-8")
    hpa = (repository_root / "k8s/volume11/autoscaling/hpa.yaml").read_text(encoding="utf-8")

    return {
        "deployment_uses_example_image": "image: example.invalid/ai-platform-api:0.1.0"
        in deployment,
        "deployment_has_distinct_health_probes": "path: /livez" in deployment
        and "path: /readyz" in deployment,
        "base_excludes_secret_example": "secret.example.yaml" not in base_kustomization,
        "compose_is_internal_placeholder_topology": "internal: true" in compose
        and "example.invalid/" in compose
        and "    ports:" not in compose,
        "batch_schedule_is_suspended": "suspend: true" in batch,
        "hpa_targets_a_separate_example": "name: ai-platform-api-example" in hpa,
    }


def run_local_operations_review(repository_root: Path) -> dict[str, object]:
    """Produce compact, deterministic evidence for the offline operations mini project.

    The function makes in-memory WSGI calls and reads local example files only.  It
    never opens a listener, calls a dependency, starts a container, contacts a
    telemetry backend, or contacts a Kubernetes cluster.
    """
    exported_events: list[str] = []
    available_application = HealthApplication(
        readiness_check=lambda: True,
        telemetry_exporter=exported_events.append,
        request_id_factory=lambda: "local-review-id",
    )
    liveness_status = _invoke(available_application, path="/livez")
    readiness_status = _invoke(available_application, path="/readyz")

    def failing_exporter(_event: str) -> None:
        raise RuntimeError("local exporter failure is intentionally isolated")

    isolated_status = _invoke(
        HealthApplication(
            readiness_check=lambda: True,
            telemetry_exporter=failing_exporter,
            request_id_factory=lambda: "local-review-id",
        ),
        path="/readyz",
    )
    unavailable_status = _invoke(
        HealthApplication(
            readiness_check=lambda: False,
            request_id_factory=lambda: "local-review-id",
        ),
        path="/readyz",
    )

    return {
        "scope": "local-only",
        "probe_checks": {
            "liveness": liveness_status,
            "readiness_available": readiness_status,
            "readiness_unavailable": unavailable_status,
            "exporter_failure_isolated": isolated_status,
        },
        "telemetry": {
            "local_event_count": len(exported_events),
            "delivery": "process-local callback only",
        },
        "artifact_checks": render_only_artifact_checks(repository_root),
        "not_verified": [
            "container execution",
            "dependency connectivity",
            "telemetry backend delivery",
            "kubernetes cluster deployment",
        ],
    }
