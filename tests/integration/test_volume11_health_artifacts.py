"""Volume 11 artifacts form a local-only health-probe learning slice."""
from __future__ import annotations

import sys
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_health_probe_demo_runs_without_network_or_cluster() -> None:
    """The teaching demo exercises both endpoints entirely in memory."""
    result = run(
        [sys.executable, "examples/volume11/health_probe_demo.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    expected_liveness = (
        '/livez 200 OK {"status":"ok","service":"ai-platform-api","check":"liveness"}'
    )
    expected_readiness = (
        '/readyz 200 OK {"status":"ok","service":"ai-platform-api","check":"readiness"}'
    )
    assert expected_liveness in result.stdout
    assert expected_readiness in result.stdout


def test_dependency_readiness_demo_runs_without_network_or_cluster() -> None:
    """The dependency-policy lesson injects checks rather than reaching real services."""
    result = run(
        [sys.executable, "examples/volume11/dependency_readiness_demo.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "all-required-dependencies-ready True" in result.stdout
    assert "redis-unavailable False" in result.stdout


def test_correlation_logging_demo_runs_without_network_or_telemetry_backend() -> None:
    """The observability lesson writes deterministic JSON only from in-memory WSGI calls."""
    result = run(
        [sys.executable, "examples/volume11/correlation_logging_demo.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        '{"event":"http_request_completed","request_id":"client-example-11",'
        '"route":"/livez","status_code":200}'
    ) in result.stdout
    assert "accepted 200 OK response-request-id=client-example-11" in result.stdout
    assert "generated 200 OK response-request-id=generated-example-11" in result.stdout
    assert "rejected 200 OK response-request-id=generated-after-invalid-11" in result.stdout
    assert "contains whitespace" not in result.stdout


def test_telemetry_boundary_demo_runs_without_network_or_a_telemetry_backend() -> None:
    """The telemetry lesson uses injected local callbacks and keeps exporter failure isolated."""
    result = run(
        [sys.executable, "examples/volume11/telemetry_boundary_demo.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        '{"event":"probe_telemetry","metric":{"name":"http_server_requests_total",'
        '"labels":{"route":"/livez","status_class":"2xx"}},'
        '"span":{"name":"health_probe","attributes":{"http.route":"/livez",'
        '"http.response.status_code":200}}}'
    ) in result.stdout
    assert "local-export 200 OK" in result.stdout
    assert "exporter-failure-isolated 200 OK" in result.stdout
    assert "client-correlation-not-telemetry-label" not in result.stdout.splitlines()[0]
    assert "example exporter detail must not be emitted" not in result.stdout


def test_probe_manifests_use_example_image_and_distinct_readiness_and_liveness_routes() -> None:
    """Manifests are safe examples, never a deployable production image or embedded secret."""
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")
    configmap = (ROOT / "k8s/volume11/configmap.yaml").read_text(encoding="utf-8")
    service = (ROOT / "k8s/volume11/service.yaml").read_text(encoding="utf-8")
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    assert "image: example.invalid/ai-platform-api:0.1.0" in deployment
    assert "path: /readyz" in deployment
    assert "path: /livez" in deployment
    assert "readOnlyRootFilesystem: true" in deployment
    assert "AI_PLATFORM_READY: \"true\"" in configmap
    assert "AI_PLATFORM_REQUIRED_DEPENDENCIES: \"qdrant,redis,postgresql\"" in configmap
    assert "type: ClusterIP" in service
    assert "- deployment.yaml" in kustomization
    assert "kind: Secret" not in deployment + configmap + service


def test_secret_example_has_a_placeholder_and_is_not_part_of_the_apply_set() -> None:
    """The required Secret shape teaches separation without storing a usable credential."""
    secret_example = (ROOT / "k8s/volume11/secret.example.yaml").read_text(encoding="utf-8")
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    assert "kind: Secret" in secret_example
    assert "REPLACE_WITH_APPROVED_SECRET_REFERENCE" in secret_example
    assert "secret.example.yaml" not in kustomization


def test_compose_dependency_topology_uses_only_placeholders_and_an_internal_network() -> None:
    """Compose teaches service boundaries without usable images, host ports, or credentials."""
    compose = (ROOT / "docker/volume11/compose.dependencies.yaml").read_text(encoding="utf-8")

    for service in ("api", "qdrant", "redis", "postgresql"):
        assert f"  {service}:" in compose
    for image in (
        "example.invalid/ai-platform-api:0.1.0",
        "example.invalid/qdrant:1.0.0",
        "example.invalid/redis:7.0.0",
        "example.invalid/postgresql:16.0.0",
    ):
        assert image in compose
    assert "ai-platform-internal:" in compose
    assert "internal: true" in compose
    assert "condition: service_started" in compose
    assert "    ports:" not in compose
    assert "PASSWORD" not in compose
    assert "TOKEN" not in compose
    assert "SECRET" not in compose


def test_ingress_uses_example_http_boundary_and_the_clusterip_service_port() -> None:
    """The ingress is a render-only HTTP routing example with no TLS secret or address."""
    ingress = (ROOT / "k8s/volume11/ingress.yaml").read_text(encoding="utf-8")
    service = (ROOT / "k8s/volume11/service.yaml").read_text(encoding="utf-8")
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    assert "apiVersion: networking.k8s.io/v1" in ingress
    assert "kind: Ingress" in ingress
    assert "ingressClassName: example-ingress-class" in ingress
    assert "host: api.volume11.example.invalid" in ingress
    assert "path: /" in ingress
    assert "pathType: Prefix" in ingress
    assert "name: ai-platform-api" in ingress
    assert "name: http" in ingress
    assert "type: ClusterIP" in service
    assert "- ingress.yaml" in kustomization
    assert "tls:" not in ingress
    assert "secretName:" not in ingress
    assert "TOKEN" not in ingress
    assert "PASSWORD" not in ingress


def test_batch_manifests_are_placeholder_only_and_excluded_from_the_base_apply_set() -> None:
    """Job examples bound retries and schedules without becoming runnable base resources."""
    job = (ROOT / "k8s/volume11/batch/job.yaml").read_text(encoding="utf-8")
    cronjob = (ROOT / "k8s/volume11/batch/cronjob.yaml").read_text(encoding="utf-8")
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    for manifest, kind in ((job, "Job"), (cronjob, "CronJob")):
        assert "apiVersion: batch/v1" in manifest
        assert f"kind: {kind}" in manifest
        assert "image: example.invalid/ai-platform-maintenance:0.1.0" in manifest
        assert "restartPolicy: Never" in manifest
        assert "readOnlyRootFilesystem: true" in manifest
        assert "TOKEN" not in manifest
        assert "PASSWORD" not in manifest
        assert "secretKeyRef:" not in manifest
        assert "envFrom:" not in manifest

    assert "completions: 1" in job
    assert "parallelism: 1" in job
    assert "backoffLimit: 2" in job
    assert "activeDeadlineSeconds: 120" in job
    assert "ttlSecondsAfterFinished: 300" in job
    assert 'schedule: "0 3 * * *"' in cronjob
    assert "suspend: true" in cronjob
    assert "concurrencyPolicy: Forbid" in cronjob
    assert "successfulJobsHistoryLimit: 1" in cronjob
    assert "failedJobsHistoryLimit: 1" in cronjob
    assert "backoffLimit: 1" in cronjob
    assert "- job.yaml" not in kustomization
    assert "- cronjob.yaml" not in kustomization


def test_pvc_is_placeholder_and_excluded_from_base_apply_set() -> None:
    """Storage lessons declare an offline claim contract, never a bindable production volume."""
    pvc = (ROOT / "k8s/volume11/storage/pvc.yaml").read_text(encoding="utf-8")
    storage_kustomization = (ROOT / "k8s/volume11/storage/kustomization.yaml").read_text(
        encoding="utf-8"
    )
    base_kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(
        encoding="utf-8"
    )

    assert "apiVersion: v1" in pvc
    assert "kind: PersistentVolumeClaim" in pvc
    assert "name: ai-platform-index-example" in pvc
    assert "storageClassName: example-storage-class" in pvc
    assert "- ReadWriteOnce" in pvc
    assert "volumeMode: Filesystem" in pvc
    assert "storage: 1Gi" in pvc
    assert "volumeName:" not in pvc
    assert "dataSource:" not in pvc
    assert "secretRef:" not in pvc
    assert "TOKEN" not in pvc
    assert "PASSWORD" not in pvc
    assert "- pvc.yaml" in storage_kustomization
    assert "- pvc.yaml" not in base_kustomization
    assert "- storage/" not in base_kustomization


def test_hpa_uses_a_non_base_example_target_and_is_excluded_from_base_apply_set() -> None:
    """Autoscaling lessons stay render-only and cannot scale the base API example."""
    hpa = (ROOT / "k8s/volume11/autoscaling/hpa.yaml").read_text(encoding="utf-8")
    autoscaling_kustomization = (
        ROOT / "k8s/volume11/autoscaling/kustomization.yaml"
    ).read_text(encoding="utf-8")
    base_kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(
        encoding="utf-8"
    )
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")

    assert "apiVersion: autoscaling/v2" in hpa
    assert "kind: HorizontalPodAutoscaler" in hpa
    assert "name: ai-platform-api-example" in hpa
    assert "namespace: ai-platform-example" in hpa
    assert "apiVersion: apps/v1" in hpa
    assert "kind: Deployment" in hpa
    assert "minReplicas: 2" in hpa
    assert "maxReplicas: 5" in hpa
    assert "type: Resource" in hpa
    assert "name: cpu" in hpa
    assert "type: Utilization" in hpa
    assert "averageUtilization: 70" in hpa
    assert "name: ai-platform-api\n" in deployment
    assert "name: ai-platform-api-example" not in deployment
    assert "TOKEN" not in hpa
    assert "PASSWORD" not in hpa
    assert "secretRef:" not in hpa
    assert "- hpa.yaml" in autoscaling_kustomization
    assert "- hpa.yaml" not in base_kustomization
    assert "- autoscaling/" not in base_kustomization


def test_deployment_declares_a_render_only_rolling_update_and_revision_boundary() -> None:
    """The base example documents update behavior without a runnable image revision."""
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")

    assert "image: example.invalid/ai-platform-api:0.1.0" in deployment
    assert "revisionHistoryLimit: 2" in deployment
    assert "progressDeadlineSeconds: 120" in deployment
    assert "type: RollingUpdate" in deployment
    assert "maxUnavailable: 0" in deployment
    assert "maxSurge: 1" in deployment
    assert "kubectl.kubernetes.io/restartedAt" not in deployment
    assert "TOKEN" not in deployment
    assert "PASSWORD" not in deployment
    assert "secretKeyRef:" not in deployment


def test_volume11_chapters_link_to_existing_artifacts_and_offline_verification() -> None:
    """The chapters document exact local files, commands, and deployment boundaries."""
    health_chapter = (VOLUME / "01-health-probes.md").read_text(encoding="utf-8")
    dependency_chapter = (VOLUME / "02-configmap-dependency-readiness.md").read_text(
        encoding="utf-8"
    )
    compose_chapter = (VOLUME / "03-compose-dependency-topology.md").read_text(
        encoding="utf-8"
    )
    ingress_chapter = (VOLUME / "04-ingress-http-boundary.md").read_text(
        encoding="utf-8"
    )
    batch_chapter = (VOLUME / "05-job-cronjob-completion-retry.md").read_text(
        encoding="utf-8"
    )
    pvc_chapter = (VOLUME / "06-pvc-lifecycle-access-retention.md").read_text(
        encoding="utf-8"
    )
    hpa_chapter = (VOLUME / "07-hpa-cpu-scaling-boundary.md").read_text(encoding="utf-8")
    rollout_chapter = (VOLUME / "08-rolling-update-rollback-boundary.md").read_text(
        encoding="utf-8"
    )
    correlation_chapter = (VOLUME / "09-structured-correlation-logging-boundary.md").read_text(
        encoding="utf-8"
    )
    telemetry_chapter = (VOLUME / "10-telemetry-data-minimization-exporter-failure.md").read_text(
        encoding="utf-8"
    )
    incident_chapter = (
        VOLUME / "11-incident-response-observability-cost-boundaries.md"
    ).read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](01-health-probes.md)" in readme
    assert "](02-configmap-dependency-readiness.md)" in readme
    assert "](03-compose-dependency-topology.md)" in readme
    assert "](04-ingress-http-boundary.md)" in readme
    assert "](05-job-cronjob-completion-retry.md)" in readme
    assert "](06-pvc-lifecycle-access-retention.md)" in readme
    assert "](07-hpa-cpu-scaling-boundary.md)" in readme
    assert "](08-rolling-update-rollback-boundary.md)" in readme
    assert "](09-structured-correlation-logging-boundary.md)" in readme
    assert "](10-telemetry-data-minimization-exporter-failure.md)" in readme
    assert "](11-incident-response-observability-cost-boundaries.md)" in readme
    combined_chapters = (
        health_chapter
        + dependency_chapter
        + compose_chapter
        + ingress_chapter
        + batch_chapter
        + pvc_chapter
        + hpa_chapter
        + rollout_chapter
        + correlation_chapter
        + telemetry_chapter
        + incident_chapter
    )
    for relative_path in (
        "src/ai_platform/api/health.py",
        "src/ai_platform/api/dependencies.py",
        "src/ai_platform/api/correlation.py",
        "src/ai_platform/api/telemetry.py",
        "examples/volume11/health_probe_demo.py",
        "examples/volume11/dependency_readiness_demo.py",
        "examples/volume11/correlation_logging_demo.py",
        "examples/volume11/telemetry_boundary_demo.py",
        "docker/volume11/Dockerfile",
        "docker/volume11/compose.dependencies.yaml",
        "k8s/volume11/deployment.yaml",
        "k8s/volume11/ingress.yaml",
        "k8s/volume11/secret.example.yaml",
        "k8s/volume11/batch/job.yaml",
        "k8s/volume11/batch/cronjob.yaml",
        "k8s/volume11/storage/pvc.yaml",
        "k8s/volume11/autoscaling/hpa.yaml",
    ):
        assert relative_path in combined_chapters
    expected_command = (
        "uv run pytest tests/unit/test_volume11_health.py "
        "tests/unit/test_volume11_dependencies.py "
        "tests/integration/test_volume11_health_artifacts.py -q"
    )
    assert expected_command in dependency_chapter
    expected_compose_command = (
        "docker compose -f docker/volume11/compose.dependencies.yaml "
        "config --no-interpolate"
    )
    assert expected_compose_command in compose_chapter
    assert "kubectl kustomize k8s/volume11" in ingress_chapter
    expected_batch_command = "kubectl kustomize k8s/volume11/batch"
    assert expected_batch_command in batch_chapter
    assert "suspend: true" in batch_chapter
    assert "kubectl kustomize k8s/volume11/storage" in pvc_chapter
    assert "example-storage-class" in pvc_chapter
    assert "PersistentVolumeClaim" in pvc_chapter
    assert "kubectl kustomize k8s/volume11/autoscaling" in hpa_chapter
    assert "HorizontalPodAutoscaler" in hpa_chapter
    assert "averageUtilization: 70" in hpa_chapter
    assert "ai-platform-api-example" in hpa_chapter
    assert "kubectl kustomize k8s/volume11" in rollout_chapter
    assert "RollingUpdate" in rollout_chapter
    assert "revisionHistoryLimit: 2" in rollout_chapter
    assert "maxUnavailable: 0" in rollout_chapter
    assert "maxSurge: 1" in rollout_chapter
    assert "kubectl rollout undo" in rollout_chapter
    expected_boundary = (
        "실제 이미지 교체, rollout 실행, rollback 실행, "
        "클러스터 적용을 하지 않습니다"
    )
    assert expected_boundary in rollout_chapter
    assert "X-Request-ID" in correlation_chapter
    assert "request_completion_event" in correlation_chapter
    assert "correlation_logging_demo.py" in correlation_chapter
    assert "telemetry backend" in correlation_chapter
    assert "kubectl apply" in correlation_chapter
    assert "cluster 연결 또는 deployment를 실행하지 마세요" in correlation_chapter
    assert "probe_telemetry_event" in telemetry_chapter
    assert "telemetry_boundary_demo.py" in telemetry_chapter
    assert "exporter failure" in telemetry_chapter
    assert "metric endpoint" in telemetry_chapter
    assert "cluster 연결 또는 deployment를 실행하지 마세요" in telemetry_chapter
    assert "exporter failure를 readiness failure로 승격하지 않는다" in incident_chapter
    assert "cardinality budget" in incident_chapter
    assert "sampling" in incident_chapter
    assert "retention" in incident_chapter
    assert "actual alert" not in incident_chapter.lower()
    assert "kubectl apply" in incident_chapter
    assert "cluster 연결 또는 deployment를 실행하지 마세요" in incident_chapter
    assert "클러스터에 적용하거나 배포하지 않습니다" in (
        health_chapter + dependency_chapter + ingress_chapter
    )
