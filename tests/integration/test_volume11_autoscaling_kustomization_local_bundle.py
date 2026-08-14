"""Static local-bundle Kustomization contracts for the Volume 11 autoscaling example."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"

EXPECTED_AUTOSCALING_KUSTOMIZATION = "\n".join(
    (
        "apiVersion: kustomize.config.k8s.io/v1beta1",
        "kind: Kustomization",
        "resources:",
        "  - hpa.yaml",
        "",
    )
)


def test_autoscaling_kustomization_is_one_canonical_local_hpa_lesson_bundle() -> None:
    """The autoscaling source has no unreviewed fields, paths, or alternate entries."""
    kustomization = (ROOT / "k8s/volume11/autoscaling/kustomization.yaml").read_text(
        encoding="utf-8"
    )

    assert kustomization == EXPECTED_AUTOSCALING_KUSTOMIZATION


def test_local_review_reports_the_canonical_local_autoscaling_lesson_bundle_contract() -> None:
    """The review compares local source text and neither renders nor applies it."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["autoscaling_kustomization_is_the_canonical_local_hpa_lesson_bundle"] is True


def test_autoscaling_bundle_chapter_preserves_source_parse_and_runtime_evidence_boundary() -> None:
    """The lesson separates exact text from Kustomize and HPA controller proof."""
    chapter = (
        VOLUME / "34-autoscaling-kustomization-local-hpa-bundle-static-boundary.md"
    ).read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](34-autoscaling-kustomization-local-hpa-bundle-static-boundary.md)" in readme
    assert "autoscaling_kustomization_is_the_canonical_local_hpa_lesson_bundle" in chapter
    assert "Kustomize" in chapter
    assert "Kubernetes API" in chapter
    assert "HPA" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
