"""Static ConfigMap readiness-policy contracts for the Volume 11 placeholder API."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_configmap_and_policy_parser_share_nonsecret_example_dependency_names() -> None:
    """Source text is not evidence that a ConfigMap was injected or dependencies connected."""
    configmap = (ROOT / "k8s/volume11/configmap.yaml").read_text(encoding="utf-8")
    dependencies = (ROOT / "src/ai_platform/api/dependencies.py").read_text(encoding="utf-8")

    assert 'AI_PLATFORM_REQUIRED_DEPENDENCIES: "qdrant,redis,postgresql"' in configmap
    assert 'AI_PLATFORM_READY_DEPENDENCIES: "qdrant,redis,postgresql"' in configmap
    assert '"AI_PLATFORM_REQUIRED_DEPENDENCIES"' in dependencies
    assert '"AI_PLATFORM_READY_DEPENDENCIES"' in dependencies
    assert "http://" not in configmap.casefold()
    assert "https://" not in configmap.casefold()
    assert "kind: Secret" not in configmap


def test_local_review_reports_the_configmap_readiness_policy_text_contract() -> None:
    """The review reads local files and never injects an environment or contacts a cluster."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["configmap_declares_nonsecret_readiness_policy_names"] is True


def test_configmap_readiness_policy_chapter_separates_text_from_runtime_evidence() -> None:
    """The lesson must preserve injection, probe, and connectivity unknowns."""
    chapter = (VOLUME / "24-configmap-readiness-policy-static-contract.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](24-configmap-readiness-policy-static-contract.md)" in readme
    assert "configmap_declares_nonsecret_readiness_policy_names" in chapter
    assert "Kubernetes API" in chapter
    assert "ConfigMap injection" in chapter
    assert "dependency connectivity" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
