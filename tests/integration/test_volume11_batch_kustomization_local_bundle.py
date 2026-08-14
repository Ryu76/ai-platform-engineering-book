"""Static local-bundle Kustomization contracts for Volume 11 batch examples."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"

EXPECTED_BATCH_KUSTOMIZATION = "\n".join(
    (
        "apiVersion: kustomize.config.k8s.io/v1beta1",
        "kind: Kustomization",
        "# Local render-only batch lesson. It is intentionally separate from "
        "../kustomization.yaml.",
        "resources:",
        "  - job.yaml",
        "  - cronjob.yaml",
        "",
    )
)


def test_batch_kustomization_is_one_canonical_local_two_resource_lesson_bundle() -> None:
    """The batch source has no unreviewed fields, paths, or alternate entry layout."""
    kustomization = (ROOT / "k8s/volume11/batch/kustomization.yaml").read_text(
        encoding="utf-8"
    )

    assert kustomization == EXPECTED_BATCH_KUSTOMIZATION


def test_local_review_reports_the_canonical_local_batch_lesson_bundle_contract() -> None:
    """The review compares local source text and neither renders nor applies it."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["batch_kustomization_is_the_canonical_local_two_resource_lesson_bundle"] is True


def test_batch_bundle_chapter_preserves_source_parse_and_runtime_evidence_boundary() -> None:
    """The lesson separates exact text from Kustomize and batch controller proof."""
    chapter = (VOLUME / "30-batch-kustomization-local-bundle-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](30-batch-kustomization-local-bundle-static-boundary.md)" in readme
    assert "batch_kustomization_is_the_canonical_local_two_resource_lesson_bundle" in chapter
    assert "Kustomize" in chapter
    assert "Kubernetes API" in chapter
    assert "controller reconciliation" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
