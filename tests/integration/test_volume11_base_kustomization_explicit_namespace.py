"""Static explicit-namespace Kustomization contracts for Volume 11 examples."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_base_kustomization_has_no_namespace_transform_and_resources_name_scope() -> None:
    """Source text does not establish Kustomize transformation or namespace admission."""
    kustomization = (ROOT / "k8s/volume11/kustomization.yaml").read_text(encoding="utf-8")

    assert "namespace:" not in kustomization
    assert "- namespace.yaml" in kustomization
    for filename in ("configmap.yaml", "deployment.yaml", "service.yaml", "ingress.yaml"):
        resource = (ROOT / "k8s/volume11" / filename).read_text(encoding="utf-8")
        assert "namespace: ai-platform-example" in resource


def test_local_review_reports_the_explicit_example_namespace_text_contract() -> None:
    """The review reads local files and never transforms or applies resources."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["base_kustomization_uses_explicit_example_resource_namespaces"] is True


def test_explicit_namespace_chapter_preserves_transform_and_runtime_evidence_boundary() -> None:
    """The lesson must separate explicit text from Kustomize and controller behavior."""
    chapter = (VOLUME / "27-base-kustomization-explicit-namespace-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](27-base-kustomization-explicit-namespace-static-boundary.md)" in readme
    assert "base_kustomization_uses_explicit_example_resource_namespaces" in chapter
    assert "namespace transformer" in chapter
    assert "Kubernetes API" in chapter
    assert "controller reconciliation" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
