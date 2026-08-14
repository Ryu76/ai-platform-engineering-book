"""Volume 01 과제가 오프라인 검증 경계를 계속 참조하는지 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXERCISES = ROOT / "docs" / "volume01-llm-fundamentals" / "12-exercises.md"
OFFLINE_CLI_TEST = ROOT / "tests" / "integration" / "test_volume01_chat_cli.py"
MOCK_CHAT_TEST = ROOT / "tests" / "unit" / "test_chat.py"


def test_volume01_exercises_link_all_assignment_levels_to_offline_boundaries() -> None:
    """기본·응용·심화 과제가 오프라인 CLI 또는 Mock 테스트를 명시한다."""
    content = EXERCISES.read_text(encoding="utf-8")

    assert OFFLINE_CLI_TEST.is_file()
    assert MOCK_CHAT_TEST.is_file()
    assert "- **기본:**" in content
    assert "- **응용:**" in content
    assert "- **심화:**" in content
    assert "examples/volume01/chat_cli.py --offline-demo" in content
    assert "pytest tests/unit/test_chat.py -q" in content
    assert "pytest tests/integration/test_volume01_chat_cli.py -q" in content
    assert "실제 API·키·네트워크 없이" in content
