"""외부 API 없이 Volume 01 CLI 미니 프로젝트의 실행 경계를 검사한다."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAT_CLI = ROOT / "examples" / "volume01" / "chat_cli.py"


def test_offline_chat_cli_starts_answers_and_exits_without_network() -> None:
    """오프라인 데모가 별도 프로세스에서 질문을 처리하고 로컬 종료한다."""
    result = subprocess.run(
        [sys.executable, str(CHAT_CLI), "--offline-demo"],
        cwd=ROOT,
        input="AI Platform이란 무엇인가요?\n/exit\n",
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )

    assert "AI 업무 처리 플랫폼 챗봇입니다." in result.stdout
    assert "오프라인 데모 응답: 'AI Platform이란 무엇인가요?' 요청을 기록했습니다." in result.stdout
    assert "대화를 마칩니다." in result.stdout
    assert result.stderr == ""
