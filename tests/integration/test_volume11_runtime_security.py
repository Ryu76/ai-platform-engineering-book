"""Static runtime-security contracts for the Volume 11 placeholder Deployment."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_deployment_declares_a_static_restricted_runtime_security_boundary() -> None:
    """The example declares defense in depth without claiming runtime enforcement."""
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")

    for contract in (
        "type: RuntimeDefault",
        "allowPrivilegeEscalation: false",
        'drop: ["ALL"]',
        "readOnlyRootFilesystem: true",
        "runAsNonRoot: true",
        "runAsUser: 10001",
    ):
        assert contract in deployment
    assert "privileged: true" not in deployment
    assert "hostNetwork: true" not in deployment
    assert "hostPath:" not in deployment


def test_local_review_reports_the_runtime_security_text_contract() -> None:
    """The review reads files only and keeps enforcement outside its evidence boundary."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["deployment_declares_restricted_runtime_security"] is True


def test_runtime_security_chapter_keeps_declarations_separate_from_enforcement() -> None:
    """The documentation must not turn static manifest text into a deployment claim."""
    chapter = (VOLUME / "16-runtime-security-context-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](16-runtime-security-context-static-boundary.md)" in readme
    assert "deployment_declares_restricted_runtime_security" in chapter
    assert "admission" in chapter
    assert "container execution" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
