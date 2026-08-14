"""Static canonical CronJob contracts for the Volume 11 batch lesson."""
from __future__ import annotations

from pathlib import Path

from ai_platform.api.operations_review import render_only_artifact_checks

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume11-kubernetes-ai-platform"

EXPECTED_CRONJOB = "\n".join(
    (
        "# Local-only teaching manifest. It is suspended and uses a deliberately "
        "unpullable image; do not apply it.",
        "apiVersion: batch/v1",
        "kind: CronJob",
        "metadata:",
        "  name: ai-platform-maintenance-scheduled",
        "  namespace: ai-platform-example",
        "  labels:",
        "    app.kubernetes.io/name: ai-platform-maintenance",
        "    app.kubernetes.io/part-of: ai-platform-example",
        "    app.kubernetes.io/component: scheduled-batch",
        "spec:",
        "  # Example cadence only. Suspend remains true until an approved operational "
        "workflow exists.",
        '  schedule: "0 3 * * *"',
        "  suspend: true",
        "  concurrencyPolicy: Forbid",
        "  startingDeadlineSeconds: 300",
        "  successfulJobsHistoryLimit: 1",
        "  failedJobsHistoryLimit: 1",
        "  jobTemplate:",
        "    spec:",
        "      backoffLimit: 1",
        "      activeDeadlineSeconds: 120",
        "      ttlSecondsAfterFinished: 300",
        "      template:",
        "        metadata:",
        "          labels:",
        "            app.kubernetes.io/name: ai-platform-maintenance",
        "            app.kubernetes.io/component: scheduled-batch",
        "        spec:",
        "          restartPolicy: Never",
        "          securityContext:",
        "            seccompProfile:",
        "              type: RuntimeDefault",
        "          containers:",
        "            - name: maintenance",
        "              # Documentation-only placeholder. Do not replace outside an "
        "approved environment.",
        "              image: example.invalid/ai-platform-maintenance:0.1.0",
        "              imagePullPolicy: IfNotPresent",
        "              command: [\"python\", \"-c\", "
        "\"print('documentation-only maintenance placeholder')\"]",
        "              securityContext:",
        "                allowPrivilegeEscalation: false",
        "                capabilities:",
        "                  drop: [\"ALL\"]",
        "                readOnlyRootFilesystem: true",
        "                runAsNonRoot: true",
        "                runAsUser: 10001",
        "              resources:",
        "                requests:",
        "                  cpu: 50m",
        "                  memory: 64Mi",
        "                limits:",
        "                  cpu: 100m",
        "                  memory: 128Mi",
        "",
    )
)


def test_cronjob_is_one_canonical_local_suspended_placeholder_schedule_boundary() -> None:
    """The CronJob source permits no unreviewed schedule, field, or layout change."""
    cronjob = (ROOT / "k8s/volume11/batch/cronjob.yaml").read_text(encoding="utf-8")

    assert cronjob == EXPECTED_CRONJOB


def test_local_review_reports_the_canonical_local_cronjob_schedule_boundary() -> None:
    """The review compares local source text and neither renders nor applies it."""
    checks = render_only_artifact_checks(ROOT)

    assert checks["cronjob_is_the_canonical_local_suspended_placeholder_schedule_boundary"] is True


def test_cronjob_boundary_chapter_preserves_source_parse_and_runtime_evidence_boundary() -> None:
    """The lesson separates exact text from YAML, controller, and runtime proof."""
    chapter = (VOLUME / "32-cronjob-canonical-suspended-placeholder-static-boundary.md").read_text(
        encoding="utf-8"
    )
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    assert "](32-cronjob-canonical-suspended-placeholder-static-boundary.md)" in readme
    assert "cronjob_is_the_canonical_local_suspended_placeholder_schedule_boundary" in chapter
    assert "Kubernetes API" in chapter
    assert "CronJob controller" in chapter
    assert "not verified" in chapter
    assert "`VOLUME11_COMPLETE=true`를 설정하지 않습니다" in chapter
