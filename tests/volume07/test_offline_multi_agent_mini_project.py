"""End-to-end offline tests for the Volume 07 deterministic mini-project CLI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPOSITORY_ROOT / "examples" / "volume07" / "offline_multi_agent_mini_project.py"


def run_example(*arguments: str) -> list[str]:
    """Execute the local-only CLI with the source package available to its child process."""
    environment = os.environ | {"PYTHONPATH": str(REPOSITORY_ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, str(EXAMPLE), *arguments],
        check=True,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        env=environment,
        text=True,
    )
    return completed.stdout.splitlines()


def test_mini_project_pauses_every_stage_without_explicit_human_approval() -> None:
    """Default execution produces recommendations but does not execute gated final work."""
    output = run_example()

    assert output == [
        "review_status=awaiting_human_approval",
        "delegation_status=awaiting_human_approval",
        "delegation_completed_task_ids=-",
        "conflict_status=awaiting_human_approval",
        "conflict_consensus_option=offline tutorial",
        "release_status=awaiting_human_approval",
        "release_handoff_note=-",
    ]


def test_mini_project_completes_only_when_each_human_gate_is_explicitly_approved() -> None:
    """Separate approvals allow only their corresponding bounded local stages to complete."""
    output = run_example(
        "--approve-review",
        "--approve-delegation",
        "--approve-conflict",
        "--approve-release",
    )

    assert output == [
        "review_status=completed",
        "delegation_status=completed",
        "delegation_completed_task_ids=draft,verify",
        "conflict_status=completed",
        "conflict_consensus_option=offline tutorial",
        "release_status=completed",
        "release_handoff_note=Handoff: local release note ready; no deployment ran.",
    ]
