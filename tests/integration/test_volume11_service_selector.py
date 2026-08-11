"""Static Service-selector contracts for the Volume 11 placeholder API."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_service_selector_matches_the_placeholder_deployment_template_label() -> None:
    """The local example declares a selector match without proving an endpoint exists."""
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")
    service = (ROOT / "k8s/volume11/service.yaml").read_text(encoding="utf-8")

    assert (
        "template:\n    metadata:\n      labels:\n"
        "        app.kubernetes.io/name: ai-platform-api" in deployment
    )
    assert "selector:\n    app.kubernetes.io/name: ai-platform-api" in service
    assert "image: example.invalid/ai-platform-api:0.1.0" in deployment
    assert "kind: Secret" not in deployment + service


def test_local_review_reports_the_service_selector_text_contract() -> None:
    """The review reads local text and never contacts a Kubernetes API or network."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["deployment_template_and_service_selector_share_app_label"] is True


def test_service_selector_chapter_separates_text_match_from_endpoint_evidence() -> None:
    """The lesson must not promote a selector declaration into traffic success."""
    chapter = (VOLUME / "19-service-selector-static-contract.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](19-service-selector-static-contract.md)" in readme
    assert "deployment_template_and_service_selector_share_app_label" in chapter
    assert "EndpointSlice" in chapter
    assert "Kubernetes API" in chapter
    assert "traffic delivery" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
