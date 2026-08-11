"""Static Startup Probe contracts for the Volume 11 placeholder Deployment."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_deployment_declares_a_static_startup_probe_boundary() -> None:
    """The placeholder probe delays other probe handling without proving a Pod starts."""
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")

    for contract in (
        "startupProbe:",
        "path: /livez",
        "port: http",
        "periodSeconds: 5",
        "timeoutSeconds: 2",
        "failureThreshold: 12",
    ):
        assert contract in deployment
    assert "image: example.invalid/ai-platform-api:0.1.0" in deployment
    startup_probe = deployment.split("startupProbe:", maxsplit=1)[1].split(
        "readinessProbe:", maxsplit=1
    )[0]
    assert "initialDelaySeconds" not in startup_probe


def test_local_review_reports_the_startup_probe_text_contract() -> None:
    """The review reads local text and does not contact a kubelet or cluster."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["deployment_declares_startup_probe_boundary"] is True


def test_startup_probe_chapter_keeps_declaration_separate_from_runtime_evidence() -> None:
    """The lesson must retain the no-cluster boundary for startup semantics."""
    chapter = (VOLUME / "17-startup-probe-lifecycle-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](17-startup-probe-lifecycle-static-boundary.md)" in readme
    assert "deployment_declares_startup_probe_boundary" in chapter
    assert "kubelet" in chapter
    assert "container execution" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
