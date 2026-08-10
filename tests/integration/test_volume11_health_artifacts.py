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
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](01-health-probes.md)" in readme
    assert "](02-configmap-dependency-readiness.md)" in readme
    assert "](03-compose-dependency-topology.md)" in readme
    assert "](04-ingress-http-boundary.md)" in readme
    assert "](05-job-cronjob-completion-retry.md)" in readme
    combined_chapters = (
        health_chapter + dependency_chapter + compose_chapter + ingress_chapter + batch_chapter
    )
    for relative_path in (
        "src/ai_platform/api/health.py",
        "src/ai_platform/api/dependencies.py",
        "examples/volume11/health_probe_demo.py",
        "examples/volume11/dependency_readiness_demo.py",
        "docker/volume11/Dockerfile",
        "docker/volume11/compose.dependencies.yaml",
        "k8s/volume11/deployment.yaml",
        "k8s/volume11/ingress.yaml",
        "k8s/volume11/secret.example.yaml",
        "k8s/volume11/batch/job.yaml",
        "k8s/volume11/batch/cronjob.yaml",
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
    assert "클러스터에 적용하거나 배포하지 않습니다" in (
        health_chapter + dependency_chapter + ingress_chapter
    )
