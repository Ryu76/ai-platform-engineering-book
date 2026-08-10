"""Volume 01 핵심 정리가 실행 가능한 오프라인 검증 경로를 보존하는지 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "docs" / "volume01-llm-fundamentals" / "11-summary.md"
OFFLINE_CLI = ROOT / "examples" / "volume01" / "chat_cli.py"
CLIENT_TEST = ROOT / "tests" / "unit" / "test_llm_client.py"
CHAT_TEST = ROOT / "tests" / "unit" / "test_chat.py"
USAGE_TEST = ROOT / "tests" / "unit" / "test_usage.py"
INTEGRATION_TEST = ROOT / "tests" / "integration" / "test_volume01_chat_cli.py"


def test_volume01_summary_links_concepts_to_offline_commands_and_next_volume() -> None:
    """요약이 핵심 개념, 오프라인 검사, Prompt Volume 연결을 함께 안내한다."""
    content = SUMMARY.read_text(encoding="utf-8")

    assert OFFLINE_CLI.is_file()
    assert CLIENT_TEST.is_file()
    assert CHAT_TEST.is_file()
    assert USAGE_TEST.is_file()
    assert INTEGRATION_TEST.is_file()
    for section in range(1, 15):
        assert f"## {section}." in content
    assert "Token" in content
    assert "Context Window" in content
    assert "생성 파라미터" in content
    assert "스트리밍" in content
    assert "제한된 재시도" in content
    assert "examples/volume01/chat_cli.py --offline-demo" in content
    assert "uv run pytest tests/integration/test_volume01_chat_cli.py -q" in content
    assert "bash scripts/run_all_tests.sh" in content
    assert "실제 API 키·네트워크 없이" in content
    assert "Volume 02" in content
