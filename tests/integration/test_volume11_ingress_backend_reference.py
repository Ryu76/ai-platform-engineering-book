"""Static Ingress-backend reference contracts for the Volume 11 placeholder API."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"


def test_ingress_references_the_example_service_named_http_port_in_its_namespace() -> None:
    """Source text is not evidence that an Ingress controller delivered traffic."""
    ingress = (ROOT / "k8s/volume11/ingress.yaml").read_text(encoding="utf-8")
    service = (ROOT / "k8s/volume11/service.yaml").read_text(encoding="utf-8")

    assert "namespace: ai-platform-example" in ingress
    assert "namespace: ai-platform-example" in service
    assert (
        "service:\n                name: ai-platform-api\n"
        "                port:\n                  name: http" in ingress
    )
    assert "name: http\n      port: 80\n      targetPort: http" in service
    assert "example.invalid" in ingress
    assert "tls:" not in ingress


def test_local_review_reports_the_ingress_backend_reference_text_contract() -> None:
    """The review reads local files and never contacts a Kubernetes API."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["ingress_references_service_named_http_port_in_declared_namespace"] is True


def test_ingress_backend_reference_chapter_separates_text_from_routing_evidence() -> None:
    """The lesson must retain controller, endpoint, and traffic-delivery unknowns."""
    chapter = (VOLUME / "23-ingress-backend-reference-static-contract.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](23-ingress-backend-reference-static-contract.md)" in readme
    assert "ingress_references_service_named_http_port_in_declared_namespace" in chapter
    assert "Kubernetes API" in chapter
    assert "Ingress controller" in chapter
    assert "EndpointSlice" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
