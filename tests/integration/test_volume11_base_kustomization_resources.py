"""Static base-Kustomization resource-list contracts for Volume 11 examples."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_base_kustomization_lists_only_the_example_core_resource_files() -> None:
    """The source list is not evidence that Kustomize or Kubernetes created objects."""
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    for resource in (
        "namespace.yaml",
        "configmap.yaml",
        "deployment.yaml",
        "service.yaml",
        "ingress.yaml",
    ):
        assert f"- {resource}" in kustomization
    for excluded in ("secret.example.yaml", "batch/", "storage/", "autoscaling/"):
        assert excluded not in kustomization


def test_local_review_reports_the_base_kustomization_resource_text_contract() -> None:
    """The review reads local files and never renders, applies, or contacts a cluster."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["base_kustomization_declares_only_example_core_resources"] is True


def test_base_kustomization_chapter_preserves_render_and_runtime_evidence_boundary() -> None:
    """The lesson must separate source text from object and controller evidence."""
    chapter = (VOLUME / "25-base-kustomization-core-resources-static-contract.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](25-base-kustomization-core-resources-static-contract.md)" in readme
    assert "base_kustomization_declares_only_example_core_resources" in chapter
    assert "Kubernetes API" in chapter
    assert "controller reconciliation" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
