"""Static canonical-block Kustomization contracts for Volume 11 examples."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"

EXPECTED_BASE_KUSTOMIZATION = "\n".join(
    (
        "apiVersion: kustomize.config.k8s.io/v1beta1",
        "kind: Kustomization",
        "resources:",
        "  - namespace.yaml",
        "  - configmap.yaml",
        "  - deployment.yaml",
        "  - service.yaml",
        "  - ingress.yaml",
        "",
    )
)


def test_base_kustomization_is_one_canonical_example_resource_block() -> None:
    """The narrow base source has no unreviewed fields or alternate list layout."""
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    assert kustomization == EXPECTED_BASE_KUSTOMIZATION


def test_local_review_reports_the_canonical_example_resource_block_contract() -> None:
    """The review compares local source text and neither renders nor applies it."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["base_kustomization_is_the_canonical_example_resource_block"] is True


def test_canonical_block_chapter_preserves_source_parse_and_runtime_evidence_boundary() -> None:
    """The lesson separates exact text from Kustomize and controller proof."""
    chapter = (VOLUME / "29-base-kustomization-canonical-block-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](29-base-kustomization-canonical-block-static-boundary.md)" in readme
    assert "base_kustomization_is_the_canonical_example_resource_block" in chapter
    assert "Kustomize" in chapter
    assert "Kubernetes API" in chapter
    assert "controller reconciliation" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter