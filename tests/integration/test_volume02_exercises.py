"""Volume 02 권 단위 문서가 실제 오프라인 검토 경계를 참조하는지 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume02-prompt-engineering"
EXERCISES = VOLUME / "09-exercises.md"
CHECKLIST = VOLUME / "checklist.md"
GLOSSARY = VOLUME / "glossary.md"
README = VOLUME / "README.md"


def test_volume02_exercises_preserve_all_assignment_levels_and_offline_boundaries() -> None:
    """기본·응용·심화 과제가 실행 가능한 예제와 안전 경계를 함께 보존한다."""
    content = EXERCISES.read_text(encoding="utf-8")

    expected_paths = (
        ROOT / "examples" / "volume02" / "prompt_template_demo.py",
        ROOT / "examples" / "volume02" / "structured_output_demo.py",
        ROOT / "examples" / "volume02" / "shot_prompt_demo.py",
        ROOT / "examples" / "volume02" / "injection_defense_demo.py",
        ROOT / "examples" / "volume02" / "prompt_mini_project_demo.py",
        ROOT / "tests" / "unit" / "test_prompts.py",
    )

    assert EXERCISES.is_file()
    assert all(path.is_file() for path in expected_paths)
    assert "- **기본:**" in content
    assert "- **응용:**" in content
    assert "- **심화:**" in content
    assert "uv run python examples/volume02/prompt_template_demo.py" in content
    assert "uv run python examples/volume02/prompt_mini_project_demo.py" in content
    assert "uv run pytest tests/unit/test_prompts.py -q" in content
    assert "실제 API·키·네트워크·Tool 실행 없이" in content
    assert "자동 배포 승인이 아님" in content


def test_volume02_checklist_preserves_offline_replay_and_tool_calling_handoff() -> None:
    """학습자 검수와 다음 권 인계가 Prompt 안전 경계를 유지하는지 검사한다."""
    content = CHECKLIST.read_text(encoding="utf-8")

    expected_paths = (
        CHECKLIST,
        ROOT / "examples" / "volume02" / "prompt_template_demo.py",
        ROOT / "examples" / "volume02" / "structured_output_demo.py",
        ROOT / "examples" / "volume02" / "injection_defense_demo.py",
        ROOT / "examples" / "volume02" / "prompt_mini_project_demo.py",
        ROOT / "docs" / "volume03-tool-calling-mcp" / "README.md",
    )

    assert all(path.is_file() for path in expected_paths)
    assert "[학습자·제작 검수 체크리스트](checklist.md)" in README.read_text(encoding="utf-8")
    assert "Instruction, Context, Input Data, Output Format, Constraint" in content
    assert "Chain of Thought" in content
    assert "Prompt Injection 위험 신호 평가는 보조 신호" in content
    assert "uv run python examples/volume02/prompt_mini_project_demo.py" in content
    assert "bash scripts/run_all_tests.sh" in content
    assert "API 키, 네트워크, 라이브 LLM, Tool 실행 없이" in content
    assert "[Volume 03. Tool Calling & MCP](../volume03-tool-calling-mcp/README.md)" in content
    assert "별도의 스키마 검증과 allowlist" in content
    assert "자동 배포 승인이 아님" in content


def test_volume02_glossary_covers_required_concepts_and_safe_handoff() -> None:
    """권 단위 용어집이 PRD의 핵심 개념과 Tool Calling 전 안전 경계를 연결한다."""
    content = GLOSSARY.read_text(encoding="utf-8")

    assert GLOSSARY.is_file()
    assert "[Volume 02 주요 용어집](glossary.md)" in README.read_text(encoding="utf-8")
    for term in (
        "Instruction",
        "Context",
        "Input Data",
        "Output Format",
        "Constraint",
        "Zero-shot",
        "One-shot",
        "Few-shot",
        "Role Prompt",
        "Structured Output",
        "JSON Output",
        "ReAct",
        "Chain of Thought",
        "Prompt Injection",
        "Prompt Versioning",
        "Prompt Template",
        "Prompt 테스트",
    ):
        assert term in content
    assert "권한 통제를 대체하지 않습니다" in content
    assert "[Volume 03. Tool Calling & MCP](../volume03-tool-calling-mcp/README.md)" in content
