# LLM 기초: Anaconda 환경 설정

## 1. 이 장의 목표

이 장에서는 이후 모든 Volume에서 공통으로 쓸 **교재 전용 Anaconda Conda 환경**을 만듭니다.
환경 이름은 `ai-platform-engineering-book`이며, Python 3.12·런타임 패키지·pytest·Ruff·mypy·현재 저장소의 editable package를 포함합니다.

`uv`, `.venv`, 시스템 Python, WSL Python은 이 교재의 Python 실습 경로에 사용하지 않습니다.

## 2. 사전 조건

- Windows 10/11
- Anaconda Distribution
- Anaconda PowerShell Prompt
- 저장소 루트의 `environment.yml`
- OpenAI 호환 API 키는 선택 사항이며 이 장에서는 필요 없음

먼저 [Windows 준비](../setup/windows.md)와 [Anaconda 환경 설정](../setup/anaconda.md)을 읽습니다.

## 3. 프로젝트 환경 생성

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
conda --version
conda env create --file environment.yml
conda activate ai-platform-engineering-book
python --version
python -c "import ai_platform; print('ai_platform import: OK')"
pytest -q
```

정상이라면 `python --version`은 3.12 계열을 표시하고, import 확인은 `ai_platform import: OK`를 출력합니다.
`pytest -q`는 실제 API 키·네트워크 없이 통과해야 합니다.

환경 정의가 바뀐 뒤에는 새 환경을 만들지 말고 활성화한 상태에서 갱신합니다.

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
conda activate ai-platform-engineering-book
conda env update --file environment.yml --prune
```

## 4. 매일 실습을 시작하는 명령

```powershell
# 실행 위치: Anaconda PowerShell Prompt
Set-Location E:\python\ai-platform-engineering-book
conda activate ai-platform-engineering-book
python examples/volume01/chat_cli.py --offline-demo
```

`ai_platform` import 오류, 다른 Python 버전, 패키지 누락이 있으면 코드나 API 키를 바꾸지 말고 아래를 먼저 확인합니다.

```powershell
conda info --envs
where python
python --version
```

`where python`의 첫 경로가 `ai-platform-engineering-book` 환경 아래여야 합니다.

## 5. 환경 변수

오프라인 실습에는 `.env`가 필요 없습니다. 라이브 API 호출을 선택한 경우에만 다음을 실행합니다.

```powershell
# 실행 위치: 저장소 루트의 활성화된 Conda 환경
Copy-Item .env.example .env
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

## 6. 정상 확인

```powershell
# 실행 위치: 저장소 루트의 활성화된 Conda 환경
python -c "from ai_platform.core.settings import LlmSettings; print(LlmSettings.from_environment().model)"
```

모델명이 출력되면 활성 Conda 환경, 패키지 경로, 설정 파일이 준비된 것입니다.

## 7. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `conda`를 찾을 수 없음 | Anaconda Prompt가 아닐 수 있음 | Anaconda PowerShell Prompt를 열고 `conda --version`을 실행한다. |
| `EnvironmentNameNotFound` | 환경 생성 전 또는 이름 오타 | `conda env create --file environment.yml`을 실행한다. |
| `No module named ai_platform` | 환경 비활성화 또는 editable 설치 누락 | `conda activate ai-platform-engineering-book` 후 `conda env update --file environment.yml --prune`를 실행한다. |
| Python이 3.12가 아님 | 다른 인터프리터가 먼저 잡힘 | `conda deactivate` 뒤 교재 환경을 다시 활성화하고 `where python`을 확인한다. |
| 테스트 실패 | 환경 문제와 코드 실패를 구분하지 않음 | 실패한 테스트 하나를 먼저 재실행하고, API 키를 추가해 우회하지 않는다. |
