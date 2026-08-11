"""Static named HTTP port contracts for the Volume 11 placeholder API."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_deployment_probes_and_service_reference_the_same_named_http_port() -> None:
    """The local example binds port references without proving endpoint reachability."""
    deployment = (ROOT / "k8s/volume11/deployment.yaml").read_text(encoding="utf-8")
    service = (ROOT / "k8s/volume11/service.yaml").read_text(encoding="utf-8")

    assert "name: http\n              containerPort: 8080" in deployment
    assert deployment.count("port: http") == 3
    assert "name: http\n      port: 80\n      targetPort: http" in service
    assert "image: example.invalid/ai-platform-api:0.1.0" in deployment
    assert "kind: Secret" not in deployment + service


def test_local_review_reports_the_named_http_port_text_contract() -> None:
    """The review reads local files and never contacts a cluster or network."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["deployment_and_service_share_named_http_port"] is True


def test_named_http_port_chapter_keeps_declaration_separate_from_runtime_evidence() -> None:
    """The lesson must not turn port-name text into a traffic-success claim."""
    chapter = (VOLUME / "18-named-http-port-static-contract.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](18-named-http-port-static-contract.md)" in readme
    assert "deployment_and_service_share_named_http_port" in chapter
    assert "targetPort: http" in chapter
    assert "EndpointSlice" in chapter
    assert "traffic delivery" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
