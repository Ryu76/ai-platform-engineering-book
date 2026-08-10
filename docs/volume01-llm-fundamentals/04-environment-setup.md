# 환경 설정: Windows·WSL에서 안전한 LLM 실습 경계 만들기

## 1. 학습 목표

이 장을 마치면 Windows Git Bash와 WSL Ubuntu의 **서로 다른 경로**를 구분하고, 저장소 루트에서 `uv` 환경을 만들 수 있습니다. 또한 `.env.example`과 로컬 전용 `.env`의 역할을 분리하고, API 키 없이 설정·CLI·테스트를 검증한 뒤에만 명시적으로 라이브 호출을 선택할 수 있습니다.

- Python 3.12 이상과 `uv`가 현재 터미널에서 사용 가능한지 확인한다.
- Windows Git Bash 경로(`/e/...`)와 WSL의 마운트 경로(`/mnt/e/...`)를 섞지 않는다.
- `uv sync --all-groups`가 프로젝트 의존성을 격리 환경에 동기화하는 이유를 설명한다.
- `.env`는 로컬 비밀값, `.env.example`은 공유 가능한 변수 이름이라는 경계를 지킨다.
- `LlmSettings.from_environment()`가 네트워크 호출이나 `.env` 자동 파싱을 하지 않는다는 점을 확인한다.
- API 키·네트워크 없이 오프라인 CLI와 설정·Client 테스트를 실행한다.

## 2. 왜 필요한가

LLM 프로그램의 설치가 끝났다고 해서 외부 API를 호출해도 되는 것은 아닙니다. 잘못된 터미널에서 명령을 실행하면 다른 저장소나 다른 가상환경을 사용할 수 있고, `.env`를 Git에 넣거나 오류 로그에 출력하면 키가 유출될 수 있습니다. 반대로 키가 없다는 이유로 테스트를 못 하면 비용 없는 회귀 검증도 할 수 없습니다.

이 저장소는 두 경로를 분리합니다. `--offline-demo`와 Mock 테스트는 API 키와 네트워크 없이 실행합니다. 라이브 CLI는 `LlmClient`를 만들고 `complete()` 또는 `stream()`을 호출할 때만 제공자에 입력을 전송할 수 있습니다. 따라서 환경 설정의 첫 목표는 키를 얻는 일이 아니라 **실행 위치·의존성·비밀값·외부 전송의 경계**를 재현 가능하게 만드는 일입니다.

> [!WARNING]
> 실제 API 키, 회사 문서, 개인정보를 코드·명령 이력·스크린샷·테스트 실패 로그에 넣지 마세요. 이 장의 기본 검증은 네트워크와 API 키를 사용하지 않습니다. 키가 노출되었다고 의심되면 해당 키를 즉시 공급자 콘솔에서 폐기하고 새 키를 발급합니다.

## 3. 핵심 개념

**저장소 루트**는 `pyproject.toml`, `uv.lock`, `src/`, `examples/`가 있는 디렉터리입니다. 이 위치에서 실행해야 `uv`가 이 프로젝트의 의존성과 Python 경로를 찾습니다. 아래 예시의 경로는 현재 학습자 환경에 맞게 바꿉니다.

| 터미널 | 같은 E: 드라이브 저장소를 나타내는 예 | 주의 |
|---|---|---|
| Windows Git Bash | `/e/python/ai-platform-engineering-book-volume-01` | `/mnt/e/...`는 WSL 경로이므로 Git Bash에서 사용하지 않습니다. |
| WSL Ubuntu | `/mnt/e/python/ai-platform-engineering-book-volume-01` | `/e/...`는 Git Bash 경로이므로 WSL에서 사용하지 않습니다. |
| WSL 홈에 복제한 저장소 | `~/projects/ai-platform-engineering-book-volume-01` | Windows 드라이브 경로가 아니라 WSL 파일 시스템의 별도 복제본입니다. |

**`uv sync --all-groups`** 는 `pyproject.toml`과 잠금 파일을 기준으로 프로젝트의 `.venv`를 맞춥니다. 전역 Python이나 다른 프로젝트의 패키지에 의존하지 않도록 하는 과정입니다. 이 저장소는 Python 3.12 이상을 요구합니다.

**환경 변수**는 프로세스에 전달하는 설정값입니다. `OPENAI_API_KEY`는 비밀값이고, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS`는 실행 설정입니다. `.env`는 이를 로컬 파일로 모아 두는 편의 장치일 뿐 자동으로 읽히지 않습니다. 이 프로젝트의 `LlmSettings.from_environment()`는 운영체제 환경 변수만 읽습니다. `uv run --env-file .env ...`처럼 `.env`를 명시해야 해당 명령의 환경 변수로 전달됩니다.

| 파일·값 | Git 공유 여부 | 용도 |
|---|---|---|
| `.env.example` | 공유 가능 | 변수 이름, 빈 값 또는 안전한 기본값을 알립니다. 실제 키는 넣지 않습니다. |
| `.env` | 공유 금지 | 개인 개발 환경의 실제 키와 선택한 모델을 보관합니다. `.gitignore`가 추적하지 않는지 확인합니다. |
| 셸 환경 변수 | 공유 금지 | CI 비밀 저장소 또는 현재 세션에서 안전하게 주입할 때 사용합니다. |
| `LlmSettings` | 코드로 공유 | 값을 읽고 timeout 형식만 검증합니다. 네트워크·키 출력·`.env` 파일 읽기를 하지 않습니다. |

## 4. 동작 구조

```text
저장소 루트에서 uv sync
        │
        ▼
pyproject.toml + uv.lock ──► .venv의 재현 가능한 도구/의존성
        │
        ▼
.env.example ──(복사 후 로컬 편집)──► .env  [Git에 커밋하지 않음]
        │                                      │
        │                         uv run --env-file .env
        ▼                                      ▼
Mock 테스트·--offline-demo              프로세스 환경 변수
(API 키·네트워크 없음)                          │
        │                                      ▼
        └──────────────────────► LlmSettings.from_environment()
                                           │
                                           ▼
                            LlmClient 생성 후 명시적 complete()/stream()
                                           │
                                           ▼
                              선택했을 때만 외부 제공자로 요청 전송 가능
```

`LlmSettings`가 `LLM_TIMEOUT_SECONDS`를 숫자로 읽고 0보다 큰지 검사하는 것은 설정 오류를 네트워크 요청 전에 발견하기 위해서입니다. 그러나 모델명과 키가 비어 있어도 설정 객체 자체는 만들 수 있습니다. 라이브 `LlmClient` 생성 시점에는 `LLM_MODEL`과 `OPENAI_API_KEY`가 모두 필요하며, 오류 메시지는 키 값을 포함하지 않습니다.

## 5. 실습 환경

필수 도구는 다음뿐입니다.

- Windows 10/11의 Git Bash **또는** WSL Ubuntu 터미널 하나
- Python 3.12 이상을 설치·선택할 수 있는 `uv`
- 이 저장소의 체크아웃
- 선택 사항: 제공자 약관·비용을 확인한 뒤 직접 준비하는 OpenAI 호환 API 키

먼저 현재 터미널에서 도구와 위치를 확인합니다. 다음 명령은 파일을 만들거나 네트워크 API를 호출하지 않습니다.

```bash
# 실행 위치: 저장소 루트. Git Bash 또는 WSL 중 하나만 선택합니다.
pwd
uv --version
uv python find 3.12
```

`uv python find 3.12`가 Python을 찾지 못하면 Python 3.12 이상을 설치하거나 `uv python install 3.12`를 실행한 뒤 다시 확인합니다. 시스템에 여러 Python이 있어도 `python` 또는 `python3`을 직접 가정하지 말고 이후 명령은 `uv run python`을 사용합니다.

## 6. 단계별 실습

### 6.1 올바른 저장소 위치로 이동하고 의존성 동기화

아래에서 **한 블록만** 선택합니다. 경로의 마지막 디렉터리 이름은 실제 체크아웃 이름에 맞춥니다.

```bash
# 실행 위치: Windows Git Bash
cd /e/python/ai-platform-engineering-book-volume-01
uv sync --all-groups
```

```bash
# 실행 위치: WSL Ubuntu, E: 드라이브의 저장소를 사용할 때
cd /mnt/e/python/ai-platform-engineering-book-volume-01
uv sync --all-groups
```

```bash
# 실행 위치: WSL Ubuntu, WSL 홈에 저장소를 복제했을 때
cd ~/projects/ai-platform-engineering-book-volume-01
uv sync --all-groups
```

성공하면 프로젝트용 `.venv`가 준비됩니다. `uv sync`는 제공자 API를 호출하지 않습니다. 이후에도 명령 앞에 `uv run`을 붙여 이 프로젝트 환경을 사용합니다.

### 6.2 키 없이 설정 객체와 오프라인 경계 확인

```bash
# 실행 위치: 방금 uv sync를 실행한 저장소 루트
uv run python -c "from ai_platform.core.settings import LlmSettings; s=LlmSettings.from_environment(); print(s.model or '<LLM_MODEL not set>'); print(s.timeout_seconds)"
printf '환경 설정을 오프라인으로 확인합니다.\n/exit\n' | \
  uv run python examples/volume01/chat_cli.py --offline-demo
uv run pytest tests/unit/test_settings.py tests/unit/test_llm_client.py tests/integration/test_volume01_chat_cli.py -q
```

첫 명령에서 모델이 설정되지 않았다면 `<LLM_MODEL not set>`과 `30.0`이 출력될 수 있으며 정상입니다. 두 번째 명령의 `--offline-demo`와 마지막 Mock·별도 프로세스 테스트는 네트워크와 API 키를 사용하지 않습니다. 실제 모델 답변이나 과금 결과를 검증하는 명령이 아닙니다.

### 6.3 선택 사항: 로컬 `.env`를 안전하게 준비

라이브 호출을 **아직 실행하지 않고** 로컬 설정 전달만 확인하려면 다음을 사용합니다.

```bash
# 실행 위치: 저장소 루트. .env.example은 수정하지 않습니다.
cp .env.example .env
```

`.env`에서 필요한 값만 편집합니다. 아래의 `example-model`과 빈 키는 예시이며 유효한 키·권장 모델명이 아닙니다. 실제 키는 이 문서, 커밋, 과제 제출물에 쓰지 않습니다.

```dotenv
OPENAI_API_KEY=
LLM_MODEL=example-model
LLM_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=30
```

저장 후에도 이 프로젝트는 `.env`를 자동으로 읽지 않습니다. 다음 명령은 `.env`를 **그 명령 하나에만** 주입하고 모델명·timeout만 출력합니다. 키를 출력하지 않으므로 설정 전달을 안전하게 확인할 수 있습니다.

```bash
# 실행 위치: 저장소 루트. API 요청은 만들지 않습니다.
uv run --env-file .env python -c "from ai_platform.core.settings import LlmSettings; s=LlmSettings.from_environment(); print(s.model); print(s.timeout_seconds)"
```

`.env`가 생긴 뒤에는 반드시 추적 상태를 확인합니다. 출력에 `.env`가 보이면 커밋하지 말고 `.gitignore`와 현재 경로를 점검합니다.

```bash
# 실행 위치: 저장소 루트. 비밀값 자체는 출력하지 않습니다.
git status --short
```

### 6.4 라이브 호출 선택 전 확인

다음 장의 라이브 호출은 비용을 만들고 사용자의 입력을 선택한 `LLM_BASE_URL` 제공자에 전송할 수 있습니다. 다음 네 가지가 모두 참일 때만 진행합니다.

1. `.env`가 Git 추적 대상이 아니며 실제 키를 출력·공유하지 않았다.
2. `LLM_MODEL`, `OPENAI_API_KEY`, `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS`의 의미를 확인했다.
3. 제공자의 모델명, 가격, 데이터 처리 정책과 조직의 승인 규칙을 확인했다.
4. 먼저 6.2의 오프라인 검증을 통과했다.

하나라도 불명확하면 다음 장의 기본 라이브 모드를 실행하지 않고 `--offline-demo`와 Mock 테스트만 사용합니다.

## 7. 코드 설명

`src/ai_platform/core/settings.py`의 `LlmSettings.from_environment()`는 `getenv()`로 설정을 읽어 불변 설정 객체를 만듭니다. 기본 base URL은 `https://api.openai.com/v1`, 기본 timeout은 `30.0`초입니다. `LLM_TIMEOUT_SECONDS`가 숫자가 아니거나 0 이하이면 `ValueError`를 발생시키며, 메시지에 `OPENAI_API_KEY`의 값은 포함하지 않습니다.

`examples/volume01/chat_cli.py`의 `--offline-demo` 분기는 `OfflineDemoClient`만 사용합니다. 따라서 `build_live_client()`와 `LlmClient`를 만들지 않고 외부 요청도 만들지 않습니다. 플래그 없는 기본 모드는 설정이 있으면 라이브 Client를 만들 수 있으므로, 문서 검증·CI·반복 실습에는 사용하지 않습니다.

`tests/unit/test_settings.py`는 키가 없는 기본 설정과 잘못된 timeout을 검사합니다. `tests/unit/test_llm_client.py`는 주입한 Mock transport로 요청 계약과 키를 포함하지 않는 오류를 검사합니다. `tests/integration/test_volume01_chat_cli.py`는 별도 프로세스에서 `--offline-demo`의 시작·응답·종료를 확인합니다. 이 테스트들은 제공자 계정이나 실제 키를 요구하지 않습니다.

## 8. 정상 실행 결과

6.1의 `uv sync --all-groups`는 의존성 동기화 완료를 표시하고 0으로 끝나야 합니다. 이미 동기화된 경우에도 성공할 수 있습니다. 6.2 첫 명령의 정확한 모델명은 로컬 환경에 따라 다르지만, 키가 없는 깨끗한 환경에서는 다음과 비슷합니다.

```text
<LLM_MODEL not set>
30.0
```

오프라인 CLI 출력은 프롬프트 공백·줄바꿈이 달라도 아래 문구를 포함합니다.

```text
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> AI> 오프라인 데모 응답: '환경 설정을 오프라인으로 확인합니다.' 요청을 기록했습니다.
사용자> 대화를 마칩니다.
```

pytest 출력의 테스트 수와 시간은 버전에 따라 달라도 마지막은 `passed`여야 합니다. 이는 설정 형식, Mock Client, 오프라인 CLI의 계약이 유지된다는 뜻이며 키 유효성·제공자 응답·모델 품질을 증명하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `uv: command not found` | 현재 터미널에 `uv`가 설치·등록되지 않았습니다. | `uv`를 설치한 뒤 터미널을 다시 열고 `uv --version`으로 확인합니다. |
| `uv python find 3.12`가 실패 | Python 3.12 이상을 찾지 못했습니다. | 설치된 Python을 확인하거나 `uv python install 3.12` 뒤 다시 실행합니다. |
| `No project found` 또는 `No module named ai_platform` | 저장소 루트가 아니거나 `uv run`을 빠뜨렸습니다. | `pwd`에서 `pyproject.toml`이 있는지 확인하고 6.1의 `cd`와 `uv sync`를 다시 실행합니다. |
| `.env`를 만들었는데 설정이 비어 있음 | `.env`는 자동으로 읽히지 않습니다. | 키 없는 검증은 그대로 `uv run`을 사용하고, 로컬 설정 확인에만 `uv run --env-file .env ...`를 명시합니다. |
| `LLM_TIMEOUT_SECONDS must be a number` | `.env` 또는 셸 변수에 숫자가 아닌 값이 있습니다. | 예를 들어 `30`처럼 양의 숫자로 고치고 키를 로그에 붙이지 않습니다. |
| `LLM 설정을 확인하세요` | `--offline-demo` 없이 CLI를 실행했거나 라이브 설정이 없습니다. | 이 장에서는 `--offline-demo`를 붙입니다. 테스트를 위해 키를 추가하지 않습니다. |
| `git status --short`에 `.env`가 보임 | 비밀 파일이 추적될 위험이 있습니다. | 커밋을 중단하고 `.gitignore`·파일 위치를 확인한 뒤, 키가 노출되었다면 폐기합니다. |
| Windows와 WSL에서 경로가 다름 | 서로 다른 경로 표기법을 섞었습니다. | Git Bash에는 `/e/...`, WSL에는 `/mnt/e/...` 또는 `~/...`만 사용합니다. |

## 10. 응용 실습

1. 팀원이 Windows Git Bash, 다른 팀원이 WSL 홈 복제본을 사용한다고 가정합니다. 각자 저장소 루트 확인, `uv sync`, `uv run`까지의 명령을 작성하고 경로를 섞으면 생길 문제를 설명합니다.
2. `LLM_TIMEOUT_SECONDS`에 빈 문자열, `0`, `none`, `30`을 각각 넣었을 때 `LlmSettings` 또는 `LlmClient`에서 어떤 결과가 나와야 하는지 표로 설계합니다. 실제 키는 사용하지 않습니다.
3. CI에서 `.env` 파일을 복사하지 않고 비밀 저장소로 환경 변수를 주입하는 흐름을 설계합니다. 로그에 키·Authorization 헤더·전체 프롬프트가 남지 않게 할 지점을 표시합니다.

## 11. 실무 적용

개발·테스트·운영은 서로 다른 키와 모델 설정을 사용하고, 비밀값은 로컬 `.env` 또는 조직의 비밀 관리 시스템에서만 주입합니다. `.env.example`에는 실제 값, 내부 URL, 고객 식별자, 회사 문서를 넣지 않습니다. API 키는 최소 권한·짧은 교체 주기·환경별 분리를 적용하고, 사람 승인 없이 키를 채팅 도구나 자동화 봇에 전달하지 않습니다.

라이브 API 호출 전에는 대상 URL, 모델, timeout, 비용 상한, 데이터 전송 정책을 검토합니다. 테스트는 Mock transport와 `--offline-demo`로 고정하고, 라이브 점검이 꼭 필요하면 별도 승인·전용 키·최소 입력으로 일회성 실행합니다. 네트워크 오류를 해결하려고 timeout을 무한대로 늘리거나 키를 디버그 로그에 출력하지 않습니다.

## 12. 과제

- **기본:** 사용하는 Git Bash 또는 WSL 환경 하나를 골라 저장소 루트까지의 경로와 `uv sync --all-groups` 실행 위치를 기록합니다. 실제 키는 기록하지 않습니다.
- **응용:** `.env.example`, `.env`, 셸 환경 변수, 비밀 관리 시스템의 공유 가능 여부와 책임을 비교표로 만듭니다.
- **심화:** 키가 없거나 timeout이 잘못된 상태에서도 외부 요청이 발생하지 않는 CI 검증 계획을 설계합니다. 설정 단위 테스트, Mock Client 테스트, 별도 프로세스 CLI 테스트의 역할을 구분합니다.

## 13. 완료 체크리스트

- [ ] Git Bash와 WSL의 경로 표기법을 섞지 않고 저장소 루트로 이동했다.
- [ ] `uv --version`, `uv python find 3.12`, `uv sync --all-groups`를 실행했다.
- [ ] `uv run`이 프로젝트 환경을 선택하는 이유를 설명할 수 있다.
- [ ] `.env.example`과 `.env`의 공유 경계를 설명할 수 있다.
- [ ] `.env`가 자동으로 읽히지 않으며 `--env-file`이 명시적으로 전달한다는 점을 확인했다.
- [ ] API 키 없이 `--offline-demo`와 설정·Mock 테스트를 실행했다.
- [ ] timeout 오류가 네트워크 요청 전에 발견되어야 함을 설명할 수 있다.
- [ ] 라이브 호출이 입력 전송·비용을 만들 수 있음을 이해하고, 명시적으로 선택할 때만 실행한다.
- [ ] 다음 장 [안전한 최초 호출](05-first-call.md)로 이어지는 경계를 확인했다.

## 14. 핵심 정리

환경 설정은 키를 넣는 절차가 아니라 재현 가능한 `.venv`, 정확한 Windows·WSL 실행 위치, 안전한 비밀값 경계, 외부 전송 선택권을 만드는 절차입니다. `uv sync`와 `uv run`으로 프로젝트 환경을 고정하고, `.env`는 `uv run --env-file`로 명시할 때만 전달합니다. 기본 검증은 API 키·네트워크 없이 `--offline-demo`와 Mock 테스트로 완료합니다. 다음 장에서는 이 경계를 유지한 채 최초 라이브 호출의 요청 구조와 실패 처리를 살펴봅니다.
