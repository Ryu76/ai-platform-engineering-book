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
    assert "type: ClusterIP" in service
    assert "- deployment.yaml" in kustomization
    assert "kind: Secret" not in deployment + configmap + service


def test_volume11_entry_chapter_links_to_existing_artifacts_and_offline_verification() -> None:
    """The first chapter documents the exact files and commands learners can inspect locally."""
    chapter = (VOLUME / "01-health-probes.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](01-health-probes.md)" in readme
    for relative_path in (
        "src/ai_platform/api/health.py",
        "examples/volume11/health_probe_demo.py",
        "docker/volume11/Dockerfile",
        "k8s/volume11/deployment.yaml",
    ):
        assert relative_path in chapter
    expected_command = (
        "uv run pytest tests/unit/test_volume11_health.py "
        "tests/integration/test_volume11_health_artifacts.py -q"
    )
    assert expected_command in chapter
    assert "클러스터에 적용하거나 배포하지 않습니다" in chapter
