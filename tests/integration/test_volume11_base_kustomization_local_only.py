"""Static local-resource-only Kustomization contracts for Volume 11 examples."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_base_kustomization_declares_a_local_resource_only_example_boundary() -> None:
    """Source text is not evidence that Kustomize resolved inputs or Kubernetes acted."""
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    for required in (
        "apiVersion: kustomize.config.k8s.io/v1beta1",
        "kind: Kustomization",
        "resources:",
    ):
        assert required in kustomization
    for excluded in (
        "http://",
        "https://",
        "git::",
        "bases:",
        "components:",
        "generators:",
        "configMapGenerator:",
        "secretGenerator:",
        "images:",
        "patches:",
        "patchesStrategicMerge:",
        "transformers:",
    ):
        assert excluded not in kustomization


def test_local_review_reports_the_local_resource_only_kustomization_text_contract() -> None:
    """The review reads local files and never resolves a remote base or contacts a cluster."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["base_kustomization_is_local_resource_only_example_contract"] is True


def test_local_resource_only_chapter_preserves_render_and_runtime_evidence_boundary() -> None:
    """The lesson must distinguish local text from Kustomize and controller behavior."""
    chapter = (VOLUME / "26-base-kustomization-local-resource-only-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](26-base-kustomization-local-resource-only-static-boundary.md)" in readme
    assert "base_kustomization_is_local_resource_only_example_contract" in chapter
    assert "remote base" in chapter
    assert "Kubernetes API" in chapter
    assert "controller reconciliation" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
