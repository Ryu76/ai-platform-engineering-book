# LLM 기초: 환경 설정

## 1. 사전 조건

- Windows 10/11 또는 WSL Ubuntu
- Python 3.12 이상
- `uv`
- OpenAI 호환 API 키는 선택 사항

## 2. 프로젝트 설치

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널
cd ~/projects/ai-platform-engineering-book
uv sync --all-groups
uv run pytest
```

`uv sync`는 `pyproject.toml`과 `uv.lock`에 맞는 격리 가상환경을 만듭니다. `pytest`는 실제 API 키 없이 통과해야 합니다.

## 3. 환경 변수

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널
cp .env.example .env
```

`.env`에는 실제 키를 넣을 수 있지만 Git에 넣지 않습니다. `.env.example`에는 변수 이름과 안전한 예시만 남깁니다.

```dotenv
OPENAI_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=30
```

> [!WARNING]
> 키를 채팅, 스크린샷, 코드, 테스트 실패 로그에 붙여 넣지 마세요. 키가 유출되면 공급자 콘솔에서 폐기하고 새 키를 발급해야 합니다.

## 4. 정상 확인

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널
uv run python -c "from ai_platform.core.settings import LlmSettings; print(LlmSettings.from_environment().model)"
```

모델명이 출력되면 설정 파일과 패키지 경로가 준비된 것입니다.
