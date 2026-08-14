"""Static sibling-resource Kustomization contracts for Volume 11 examples."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_base_kustomization_lists_only_exact_sibling_example_filenames() -> None:
    """Resource-entry text is bounded to the five intended local example files."""
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")
    resource_entries = tuple(
        line.strip()[2:] for line in kustomization.splitlines() if line.startswith("  - ")
    )

    assert resource_entries == (
        "namespace.yaml",
        "configmap.yaml",
        "deployment.yaml",
        "service.yaml",
        "ingress.yaml",
    )
    assert all("/" not in entry and "\\" not in entry for entry in resource_entries)


def test_local_review_reports_the_exact_sibling_resource_filename_contract() -> None:
    """The review reads local text and neither resolves nor applies resources."""
    checks = render_only_artifact_checks(ROOT)

    assert checks[
        "base_kustomization_resource_entries_are_exact_local_example_filenames"
    ] is True


def test_sibling_resource_chapter_preserves_resolution_and_runtime_evidence_boundary() -> None:
    """The lesson separates filename text from filesystem, Kustomize, and cluster proof."""
    chapter = (VOLUME / "28-base-kustomization-sibling-resource-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](28-base-kustomization-sibling-resource-static-boundary.md)" in readme
    assert "base_kustomization_resource_entries_are_exact_local_example_filenames" in chapter
    assert "Kustomize" in chapter
    assert "Kubernetes API" in chapter
    assert "controller reconciliation" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter