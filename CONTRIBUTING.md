# 기여 가이드

변경 전 `PRD.md`와 해당 Volume의 README를 읽습니다. 문서는 한국어로 작성하고, 모든 명령은 실행 위치·목적·정상 결과·오류 확인 방법을 포함합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널
uv run ruff check .
uv run mypy src
uv run pytest
uv run python scripts/validate_docs.py
uv run python scripts/check_secrets.py
```

실제 키, 개인정보, 비공개 문서를 커밋하지 않습니다.
