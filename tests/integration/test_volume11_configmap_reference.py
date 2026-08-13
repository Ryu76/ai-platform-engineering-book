"""Static ConfigMap-reference contracts for the Volume 11 placeholder API."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_deployment_references_the_example_configmap_in_the_declared_namespace() -> None:
    """Source text is not evidence that kubelet injected any ConfigMap values."""
    configmap = (ROOT / "k8s/volume11/configmap.yaml").read_text(encoding="utf-8")
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")

    assert "name: ai-platform-api-config" in configmap
    assert "namespace: ai-platform-example" in configmap
    assert "namespace: ai-platform-example" in deployment
    assert (
        "envFrom:\n            - configMapRef:\n"
        "                name: ai-platform-api-config" in deployment
    )
    assert "kind: Secret" not in configmap + deployment


def test_local_review_reports_the_configmap_reference_text_contract() -> None:
    """The review reads local files and never contacts a Kubernetes API."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["deployment_references_example_configmap_in_its_declared_namespace"] is True


def test_configmap_reference_chapter_separates_text_from_injection_evidence() -> None:
    """The lesson must retain missing-object and runtime-environment unknowns."""
    chapter = (VOLUME / "22-configmap-reference-static-contract.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](22-configmap-reference-static-contract.md)" in readme
    assert "deployment_references_example_configmap_in_its_declared_namespace" in chapter
    assert "Kubernetes API" in chapter
    assert "ConfigMap injection" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter