"""Static namespace-scope contracts for the Volume 11 placeholder base set."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_base_resources_declare_the_same_example_namespace() -> None:
    """Local namespace text is not evidence that Kubernetes admitted any object."""
    namespace = (ROOT / "k8s/volume11/namespace.yaml").read_text(encoding="utf-8")
    configmap = (ROOT / "k8s/volume11/configmap.yaml").read_text(encoding="utf-8")
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")
    service = (ROOT / "k8s/volume11/service.yaml").read_text(encoding="utf-8")
    ingress = (ROOT / "k8s/volume11/ingress.yaml").read_text(encoding="utf-8")

    assert "name: ai-platform-example" in namespace
    assert all(
        "namespace: ai-platform-example" in resource
        for resource in (configmap, deployment, service, ingress)
    )
    assert "image: example.invalid/ai-platform-api:0.1.0" in deployment
    assert "kind: Secret" not in namespace + configmap + deployment + service + ingress


def test_local_review_reports_the_base_namespace_text_contract() -> None:
    """The review reads local manifests and never contacts a Kubernetes API."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["base_resources_share_example_namespace"] is True


def test_namespace_scope_chapter_separates_text_from_admission_and_isolation_evidence() -> None:
    """The lesson must not turn one namespace string into runtime isolation evidence."""
    chapter = (VOLUME / "21-namespace-scope-static-contract.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](21-namespace-scope-static-contract.md)" in readme
    assert "base_resources_share_example_namespace" in chapter
    assert "Kubernetes API" in chapter
    assert "admission" in chapter
    assert "NetworkPolicy" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
