"""Volume 02 권 단위 과제가 실제 오프라인 검토 경계를 참조하는지 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume02-prompt-engineering"
EXERCISES = VOLUME / "09-exercises.md"


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
