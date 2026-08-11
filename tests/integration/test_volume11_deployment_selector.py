"""Static Deployment-selector contracts for the Volume 11 placeholder API."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_deployment_selector_matches_the_placeholder_template_label() -> None:
    """The local declaration is valid text, not evidence that a ReplicaSet ran."""
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")

    assert (
        "selector:\n    matchLabels:\n"
        "      app.kubernetes.io/name: ai-platform-api" in deployment
    )
    assert (
        "template:\n    metadata:\n      labels:\n"
        "        app.kubernetes.io/name: ai-platform-api" in deployment
    )
    assert "image: example.invalid/ai-platform-api:0.1.0" in deployment
    assert "kind: Secret" not in deployment


def test_local_review_reports_the_deployment_selector_text_contract() -> None:
    """The review reads a local manifest and never contacts a Kubernetes API."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["deployment_selector_matches_template_app_label"] is True


def test_deployment_selector_chapter_separates_text_match_from_controller_evidence() -> None:
    """The lesson must not promote an immutable declaration into rollout success."""
    chapter = (VOLUME / "20-deployment-selector-template-static-contract.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](20-deployment-selector-template-static-contract.md)" in readme
    assert "deployment_selector_matches_template_app_label" in chapter
    assert "ReplicaSet" in chapter
    assert "Kubernetes API" in chapter
    assert "Pod creation" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
