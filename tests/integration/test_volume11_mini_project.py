"""The Volume 11 mini project must remain local-only and deterministic."""
from __future__ import annotations

import sys
from json import loads
from pathlib import Path
from subprocess import run

from ai_platform.api.operations_review import run_local_operations_review

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_local_operations_review_combines_probe_telemetry_and_render_only_boundaries() -> None:
    """The mini project reports evidence without exposing request input or using a cluster."""
    review = run_local_operations_review(ROOT)

    assert review["scope"] == "local-only"
    assert review["probe_checks"] == {
        "liveness": "200 OK",
        "readiness_available": "200 OK",
        "readiness_unavailable": "503 Service Unavailable",
        "exporter_failure_isolated": "200 OK",
    }
    assert review["telemetry"] == {
        "local_event_count": 2,
        "delivery": "process-local callback only",
    }
    artifact_checks = review["artifact_checks"]
    assert isinstance(artifact_checks, dict)
    assert artifact_checks == {
        "deployment_uses_example_image": True,
        "deployment_has_distinct_health_probes": True,
        "deployment_declares_resource_requests_and_limits": True,
        "base_excludes_secret_example": True,
        "compose_is_internal_placeholder_topology": True,
        "ingress_uses_placeholder_host": True,
        "batch_schedule_is_suspended": True,
        "storage_is_placeholder_and_separate": True,
        "hpa_targets_a_separate_example": True,
    }
    assert review["not_verified"] == [
        "container execution",
        "dependency connectivity",
        "telemetry backend delivery",
        "kubernetes cluster deployment",
    ]
    assert "local-review-id" not in str(review)


def test_local_operations_review_demo_runs_without_network_or_cluster() -> None:
    """The executable mini project emits one deterministic local JSON review."""
    result = run(
        [sys.executable, "examples/volume11/local_operations_review_demo.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    review = loads(result.stdout)
    assert review["scope"] == "local-only"
    assert review["probe_checks"]["exporter_failure_isolated"] == "200 OK"
    assert review["telemetry"]["local_event_count"] == 2
    assert all(review["artifact_checks"].values())
    assert "local-review-id" not in result.stdout


def test_mini_project_chapter_links_the_executable_and_keeps_operational_actions_out_of_scope(
) -> None:
    """Learners receive acceptance criteria and explicit local-only operating boundaries."""
    chapter = (VOLUME / "12-local-operations-review-mini-project.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](12-local-operations-review-mini-project.md)" in readme
    assert "examples/volume11/local_operations_review_demo.py" in chapter
    assert "src/ai_platform/api/operations_review.py" in chapter
    assert "tests/integration/test_volume11_mini_project.py" in chapter
    assert "kubectl apply" in chapter
    assert "cluster 연결 또는 deployment를 실행하지 마세요" in chapter
    assert "example.invalid" in chapter
    assert "VOLUME11_COMPLETE=true" not in chapter


def test_preflight_handoff_chapter_separates_local_evidence_from_operational_approval() -> None:
    """The final handoff guide must retain unknowns and avoid a deployment-success claim."""
    handoff = (VOLUME / "13-preflight-checklist-glossary-handoff.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](13-preflight-checklist-glossary-handoff.md)" in readme
    for artifact in (
        "src/ai_platform/api/health.py",
        "docker/volume11/compose.dependencies.yaml",
        "k8s/volume11/deployment.yaml",
        "src/ai_platform/api/operations_review.py",
        "examples/volume11/local_operations_review_demo.py",
    ):
        assert artifact in handoff
    for term in (
        "liveness",
        "readiness",
        "render-only",
        "placeholder",
        "exporter failure isolation",
    ):
        assert term in handoff
    assert "local validation을 deployment approval 또는 PRD 완료 선언으로 확장하지" in handoff
    assert (
        "actual cluster, alert, on-call, telemetry backend 또는 deployment를 실행하지 않았다"
        in handoff
    )
    assert "VOLUME11_COMPLETE=true" not in handoff


def test_prd_traceability_keeps_static_artifacts_separate_from_blocked_live_practices() -> None:
    """The PRD audit maps required learning artifacts without declaring the Volume complete."""
    traceability = (VOLUME / "14-prd-traceability-offline-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](14-prd-traceability-offline-boundary.md)" in readme
    for artifact in (
        "docker/volume11/Dockerfile",
        "docker/volume11/compose.dependencies.yaml",
        "k8s/volume11/deployment.yaml",
        "k8s/volume11/ingress.yaml",
        "k8s/volume11/batch/",
        "k8s/volume11/storage/",
        "k8s/volume11/autoscaling/",
        "src/ai_platform/api/operations_review.py",
    ):
        assert artifact in traceability
    assert "Docker Compose 통합 실행" in traceability
    assert "Kubernetes 로컬 환경 구성" in traceability
    assert "최종 AI Platform 배포" in traceability
    assert "not verified / incomplete" in traceability
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in traceability
