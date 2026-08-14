"""Static canonical Job contracts for the Volume 11 batch lesson."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"

EXPECTED_JOB = "\n".join(
    (
        "# Local-only teaching manifest. The image is deliberately not pullable; "
        "do not apply it.",
        "apiVersion: batch/v1",
        "kind: Job",
        "metadata:",
        "  name: ai-platform-maintenance-once",
        "  namespace: ai-platform-example",
        "  labels:",
        "    app.kubernetes.io/name: ai-platform-maintenance",
        "    app.kubernetes.io/part-of: ai-platform-example",
        "    app.kubernetes.io/component: batch",
        "spec:",
        "  completions: 1",
        "  parallelism: 1",
        "  backoffLimit: 2",
        "  activeDeadlineSeconds: 120",
        "  ttlSecondsAfterFinished: 300",
        "  template:",
        "    metadata:",
        "      labels:",
        "        app.kubernetes.io/name: ai-platform-maintenance",
        "        app.kubernetes.io/component: batch",
        "    spec:",
        "      restartPolicy: Never",
        "      securityContext:",
        "        seccompProfile:",
        "          type: RuntimeDefault",
        "      containers:",
        "        - name: maintenance",
        "          # Documentation-only placeholder. Do not replace outside an "
        "approved environment.",
        "          image: example.invalid/ai-platform-maintenance:0.1.0",
        "          imagePullPolicy: IfNotPresent",
        "          command: [\"python\", \"-c\", "
        "\"print('documentation-only maintenance placeholder')\"]",
        "          securityContext:",
        "            allowPrivilegeEscalation: false",
        "            capabilities:",
        "              drop: [\"ALL\"]",
        "            readOnlyRootFilesystem: true",
        "            runAsNonRoot: true",
        "            runAsUser: 10001",
        "          resources:",
        "            requests:",
        "              cpu: 50m",
        "              memory: 64Mi",
        "            limits:",
        "              cpu: 100m",
        "              memory: 128Mi",
        "",
    )
)


def test_job_is_one_canonical_local_placeholder_completion_boundary() -> None:
    """The Job source permits no unreviewed field, command, image, or layout change."""
    job = (ROOT / "k8s/volume11/batch/job.yaml").read_text(encoding="utf-8")

    assert job == EXPECTED_JOB


def test_local_review_reports_the_canonical_local_job_completion_boundary() -> None:
    """The review compares local source text and neither renders nor applies it."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["job_is_the_canonical_local_placeholder_completion_boundary"] is True


def test_job_boundary_chapter_preserves_source_parse_and_runtime_evidence_boundary() -> None:
    """The lesson separates exact text from YAML, controller, and runtime proof."""
    chapter = (VOLUME / "31-job-canonical-placeholder-completion-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](31-job-canonical-placeholder-completion-static-boundary.md)" in readme
    assert "job_is_the_canonical_local_placeholder_completion_boundary" in chapter
    assert "Kubernetes API" in chapter
    assert "Job controller" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
