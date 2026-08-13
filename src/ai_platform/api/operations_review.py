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
    dockerfile = (repository_root / "docker/volume11/Dockerfile").read_text(encoding="utf-8")
    deployment = (repository_root / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")
    base_kustomization = (repository_root / "k8s/volume11/kustomization.yaml").read_text(
        encoding="utf-8"
    )
    compose = (repository_root / "docker/volume11/compose.dependencies.yaml").read_text(
        encoding="utf-8"
    )
    service = (repository_root / "k8s/volume11/service.yaml").read_text(encoding="utf-8")
    batch = (repository_root / "k8s/volume11/batch/cronjob.yaml").read_text(encoding="utf-8")
    hpa = (repository_root / "k8s/volume11/autoscaling/hpa.yaml").read_text(encoding="utf-8")
    ingress = (repository_root / "k8s/volume11/ingress.yaml").read_text(encoding="utf-8")
    pvc = (repository_root / "k8s/volume11/storage/pvc.yaml").read_text(encoding="utf-8")
    namespace = (repository_root / "k8s/volume11/namespace.yaml").read_text(
        encoding="utf-8"
    )
    configmap = (repository_root / "k8s/volume11/configmap.yaml").read_text(
        encoding="utf-8"
    )
    _before_startup, startup_marker, after_startup = deployment.partition("startupProbe:")
    startup_probe, _before_readiness, _after_readiness = after_startup.partition(
        "readinessProbe:"
    )

    return {
        "dockerfile_is_multistage_and_nonroot": all(
            value in dockerfile
            for value in (
                "FROM python:3.12-slim AS source",
                "FROM python:3.12-slim AS runtime",
                "COPY --from=source --chown=10001:10001 /build/ai_platform /app/src/ai_platform",
                "USER appuser",
            )
        ),
        "deployment_uses_example_image": "image: example.invalid/ai-platform-api:0.1.0"
        in deployment,
        "deployment_has_distinct_health_probes": "path: /livez" in deployment
        and "path: /readyz" in deployment,
        "deployment_and_service_share_named_http_port": (
            "name: http\n              containerPort: 8080" in deployment
        )
        and deployment.count("port: http") == 3
        and "name: http\n      port: 80\n      targetPort: http" in service,
        "deployment_template_and_service_selector_share_app_label": (
            "template:\n    metadata:\n      labels:\n"
            "        app.kubernetes.io/name: ai-platform-api" in deployment
            and "selector:\n    app.kubernetes.io/name: ai-platform-api" in service
        ),
        "deployment_selector_matches_template_app_label": (
            "selector:\n    matchLabels:\n"
            "      app.kubernetes.io/name: ai-platform-api" in deployment
            and "template:\n    metadata:\n      labels:\n"
            "        app.kubernetes.io/name: ai-platform-api" in deployment
        ),
        "base_resources_share_example_namespace": (
            "name: ai-platform-example" in namespace
            and all(
                "namespace: ai-platform-example" in resource
                for resource in (configmap, deployment, service, ingress)
            )
            and "- namespace.yaml" in base_kustomization
        ),
        "deployment_references_example_configmap_in_its_declared_namespace": (
            "name: ai-platform-api-config\n  namespace: ai-platform-example" in configmap
            and "namespace: ai-platform-example" in deployment
            and "envFrom:\n            - configMapRef:\n"
            "                name: ai-platform-api-config" in deployment
        ),
        "ingress_references_service_named_http_port_in_declared_namespace": (
            "namespace: ai-platform-example" in ingress
            and "namespace: ai-platform-example" in service
            and "service:\n                name: ai-platform-api\n"
            "                port:\n                  name: http" in ingress
            and "name: http\n      port: 80\n      targetPort: http" in service
        ),
        "deployment_declares_startup_probe_boundary": bool(startup_marker)
        and all(
            value in startup_probe
            for value in (
                "path: /livez",
                "periodSeconds: 5",
                "timeoutSeconds: 2",
                "failureThreshold: 12",
            )
        ),
        "deployment_declares_resource_requests_and_limits": all(
            value in deployment
            for value in ("cpu: 100m", "memory: 128Mi", "cpu: 500m", "memory: 256Mi")
        ),
        "deployment_declares_restricted_runtime_security": all(
            value in deployment
            for value in (
                "type: RuntimeDefault",
                "allowPrivilegeEscalation: false",
                'drop: ["ALL"]',
                "readOnlyRootFilesystem: true",
                "runAsNonRoot: true",
                "runAsUser: 10001",
            )
        ),
        "base_excludes_secret_example": "secret.example.yaml" not in base_kustomization,
        "compose_is_internal_placeholder_topology": "internal: true" in compose
        and "example.invalid/" in compose
        and "    ports:" not in compose,
        "ingress_uses_placeholder_host": "host: api.volume11.example.invalid" in ingress,
        "batch_schedule_is_suspended": "suspend: true" in batch,
        "storage_is_placeholder_and_separate": "storageClassName: example-storage-class"
        in pvc
        and "- storage/" not in base_kustomization,
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
            "image build",
            "container execution",
            "dependency connectivity",
            "telemetry backend delivery",
            "kubernetes cluster deployment",
        ],
    }
