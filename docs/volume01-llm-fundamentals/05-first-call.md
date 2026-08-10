# LLM 기초: 안전한 최초 호출

## 1. 학습 목표

이 장을 마치면 OpenAI 호환 LLM API의 요청·응답 경계를 설명하고, 모델명·API 키·기본 URL·Timeout을 코드가 아닌 환경 변수로 분리할 수 있습니다. 또한 `LlmClient`가 생성만으로는 전송하지 않고 `complete()`를 명시했을 때만 전송 계층을 호출하며, 실제 키 없이 Mock transport로 이 계약을 검증하는 방법을 익힙니다.

- 요청에 포함되는 모델, 메시지, 생성 파라미터와 응답의 관계를 설명한다.
- `LlmSettings`와 `LlmClient`의 책임을 구분한다.
- API 키가 없는 설정 오류에 비밀값이 포함되지 않아야 하는 이유를 설명한다.
- 실제 제공자 대신 `RecordingTransport`로 요청 URL·본문·Timeout을 검사한다.
- 라이브 호출이 비용과 외부 전송을 만들 수 있음을 이해하고, 명시적으로 선택할 때만 실행한다.

## 2. 왜 필요한가

LLM 호출은 함수 호출처럼 보이지만 네트워크, 인증, 요청 형식, 비용, 데이터 처리 정책이라는 운영 조건을 함께 가집니다. 화면이나 업무 로직이 HTTP 요청을 직접 만들면 키가 로그에 남고, Timeout 없이 대기하거나 테스트가 외부 서비스에 의존하기 쉽습니다.

이 권은 전송 계층을 분리합니다. 단위 테스트는 가짜 응답을 반환하는 `RecordingTransport`를 쓰므로 인터넷과 API 키가 필요 없습니다. 반면 실제 제공자에 입력을 보내는 구현은 `UrllibJsonTransport` 하나에 한정합니다. `LlmClient`를 만드는 것만으로는 요청이 전송되지 않으며, 학습자가 `complete()` 또는 이후 장의 `stream()`을 명시할 때만 전송 계층이 호출됩니다.

> [!WARNING]
> `OPENAI_API_KEY`를 코드, Git, 터미널 기록, 오류 보고서, 과제 제출물에 넣지 마세요. 라이브 호출은 입력을 선택한 제공자에게 전송하고 비용을 만들 수 있습니다. 이 장의 기본 검증은 네트워크와 API 키를 사용하지 않습니다. 실제 호출은 자신의 키·제공자 약관·비용·데이터 처리 정책을 확인한 뒤에만 선택합니다.

## 3. 핵심 개념

**OpenAI 호환 API**는 보통 `POST /chat/completions`에 모델명과 메시지 목록을 JSON으로 보내는 API 형태입니다. 이 장의 `ChatMessage`는 `system`, `user`, `assistant` 역할만 받고 빈 내용은 요청 전에 거부합니다. 역할별 자세한 책임과 생성 파라미터는 [다음 장](06-system-prompt-and-parameters.md)에서 다룹니다.

**설정(`LlmSettings`)**은 운영체제 환경 변수에서 모델명, API 키, 기본 URL, Timeout을 읽는 값 객체입니다. `.env` 파일을 자동으로 읽거나 네트워크에 연결하지 않습니다. **Client(`LlmClient`)**는 설정값과 메시지를 검증하고, 명시적인 완료 요청을 전송 계층에 위임합니다.

**Timeout**은 요청이 끝나지 않을 때 기다릴 최대 시간(초)입니다. 기본값은 30초입니다. 0 이하 값, HTTP(S)가 아닌 URL, 빈 모델명, 없는 키는 요청 전에 `LlmConfigurationError`가 됩니다. 이 오류 메시지는 키 값을 포함하지 않습니다.

**전송 계층(transport)**은 HTTP 요청만 담당하는 교체 가능한 경계입니다. 운영에서는 `UrllibJsonTransport`가 표준 라이브러리 `urllib`로 요청을 보냅니다. 테스트에서는 같은 `post_json()` 형태의 `RecordingTransport`가 URL·헤더·본문·Timeout을 메모리에 기록하고 고정된 응답을 반환합니다.

## 4. 동작 구조

```text
현재 셸 환경 변수 또는 uv run --env-file .env
                         │
                         ▼
                LlmSettings.from_environment()
                (파일 자동 파싱·네트워크 없음)
                         │ model, key, URL, timeout
                         ▼
                    LlmClient 생성
                    (요청 전송 없음)
                         │
            complete(messages)를 명시적으로 호출
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
RecordingTransport                UrllibJsonTransport
(Mock 응답·네트워크 없음)          (선택한 제공자로 HTTPS 요청)
          │                             │
          └──────────────┬──────────────┘
                         ▼
       LlmResponse(텍스트, 모델명, 입력·출력 토큰 사용량)
```

성공 응답은 첫 번째 `choices[].message.content`와 선택적인 `usage.prompt_tokens`, `usage.completion_tokens`를 `LlmResponse`로 정규화합니다. 호환 제공자가 사용량을 보내지 않으면 두 토큰 값은 `0`입니다. HTTP 4xx/5xx는 `LlmRemoteError`, 연결 실패는 `LlmNetworkError`, 시간 초과는 `LlmTimeoutError`, 예상과 다른 성공 JSON은 `LlmResponseError`로 구분합니다.

## 5. 실습 환경

앞 장에서 만든 프로젝트 환경을 사용합니다.

- `src/ai_platform/core/settings.py`: 환경 변수를 읽고 Timeout 형식을 검증합니다.
- `src/ai_platform/llm/client.py`: 메시지·설정 검증, 전송 경계, 응답 해석을 제공합니다.
- `examples/volume01/first_call.py`: 명시적으로 선택하는 라이브 최초 호출 예제입니다.
- `tests/unit/test_llm_client.py`: 외부 통신 없는 Mock Client 계약입니다.

저장소 루트에서 의존성을 동기화합니다. Windows Git Bash라면 `/e/python/ai-platform-engineering-book-volume-01`, WSL에서 E: 드라이브를 사용한다면 `/mnt/e/python/ai-platform-engineering-book-volume-01`처럼 **현재 터미널에 맞는 경로 하나만** 사용합니다.

```bash
# 실행 위치: Git Bash 또는 WSL의 저장소 루트
uv sync --all-groups
```

이 명령은 프로젝트 가상환경과 검사 도구를 준비하지만 제공자 API를 호출하지 않습니다. `python`을 직접 가정하지 않고 이후 명령은 `uv run python` 또는 `uv run pytest`로 실행합니다.

## 6. 단계별 실습

### 6.1 키·네트워크 없는 Client 계약 실행

다음 테스트는 `RecordingTransport`를 사용합니다. API 키도 인터넷도 필요 없고 실제 제공자에 요청을 보내지 않습니다.

```bash
# 실행 위치: Git Bash 또는 WSL의 저장소 루트
uv run pytest tests/unit/test_llm_client.py -q
```

테스트는 다음 계약을 확인합니다.

1. 모델·메시지·Timeout이 OpenAI 호환 JSON 요청으로 직렬화된다.
2. base URL 끝의 슬래시가 최종 URL에 중복되지 않는다.
3. 키가 없으면 전송 전에 비밀값 없는 설정 오류가 발생한다.
4. 4xx/5xx, 네트워크, Timeout, 잘못된 응답 JSON이 구분된다.
5. Mock transport에만 요청이 기록되며 실제 HTTP 호출은 없다.

### 6.2 최초 호출 코드 읽기

`examples/volume01/first_call.py`는 환경 설정을 읽은 뒤 다음처럼 한 번의 완료 요청을 명시합니다.

```python
response = client.complete(
    [
        ChatMessage(role="system", content="당신은 AI 플랫폼 입문 교재 도우미입니다."),
        ChatMessage(role="user", content="AI 업무 처리 플랫폼을 한 문장으로 설명하세요."),
    ]
)
```

`complete()`는 모델명과 메시지 목록을 JSON으로 만들고 `LLM_BASE_URL/chat/completions`에 `POST`합니다. 성공하면 본문, 응답 모델명, 토큰 사용량을 출력합니다. `LlmClient(...)` 생성 자체는 `complete()`가 아니므로 네트워크 요청을 만들지 않습니다.

### 6.3 선택 사항: 라이브 호출 전 설정만 안전하게 확인

이 단계는 API 요청을 만들지 않습니다. `.env`는 Git에 넣지 않는 로컬 파일이고 자동으로 읽히지 않습니다. `.env.example`을 복사한 뒤, 자신의 환경에서 필요한 값만 편집합니다. 실제 키를 문서나 셸 출력에 붙이지 않습니다.

```bash
# 실행 위치: Git Bash 또는 WSL의 저장소 루트
cp .env.example .env
# .env에는 OPENAI_API_KEY, LLM_MODEL 등 자신의 로컬 값만 설정한다.
uv run --env-file .env python -c "from ai_platform.core.settings import LlmSettings; s=LlmSettings.from_environment(); print(s.model); print(s.timeout_seconds)"
git status --short
```

세 번째 명령은 모델명과 Timeout만 출력하므로 키를 노출하지 않습니다. 마지막 명령 출력에 `.env`가 보이면 라이브 호출과 커밋을 중단하고 `.gitignore` 및 파일 위치를 점검합니다.

### 6.4 선택 사항: 자신의 제공자로 단 한 번 호출

다음 명령은 외부 요청과 비용을 발생시킬 수 있습니다. 외부 전송을 원하지 않거나 키가 없다면 실행하지 말고 6.1만 실행합니다. `.env`를 명시적으로 현재 명령에 주입합니다.

```bash
# 실행 위치: Git Bash 또는 WSL의 저장소 루트. 외부 전송·비용이 발생할 수 있음.
uv run --env-file .env python examples/volume01/first_call.py
```

실행 전에 다음을 모두 확인합니다.

- `.env`가 Git 추적 대상이 아니고 키를 출력·공유하지 않았다.
- `LLM_MODEL`, `LLM_BASE_URL`, `LLM_TIMEOUT_SECONDS`와 선택한 제공자의 모델 정책을 확인했다.
- 가격·데이터 처리 정책·조직 승인 규칙을 확인했다.
- 6.1의 Mock 테스트가 통과했다.

## 7. 코드 설명

`LlmSettings.from_environment()`는 `getenv()`로 설정을 읽고 `LLM_TIMEOUT_SECONDS`만 숫자와 양수인지 검사합니다. 모델명과 키가 없어도 설정 객체는 만들 수 있습니다. 이는 키 없이 오프라인 검사와 설정 확인을 가능하게 하기 위한 경계입니다.

`LlmClient.__init__()`는 실제 호출에 필요한 모델명, 키, URL, Timeout을 검증합니다. 생성자는 전송 계층의 `post_json()`을 호출하지 않습니다. `complete()`가 호출된 뒤에만 `_complete_once()`가 `post_json()`에 Authorization 헤더와 JSON 본문을 전달합니다. Authorization 값은 요청에만 사용하며 응답·예외·로그 메시지로 재출력하지 않습니다.

`_parse_completion()`은 성공 JSON의 필수 구조를 엄격히 확인합니다. `choices`가 없거나 첫 메시지에 문자열 `content`가 없으면 `LlmResponseError`를 발생시킵니다. 사용량은 제공자에 따라 빠질 수 있으므로 없는 값은 `0`으로 정규화합니다. 이 동작은 사용량·비용 장에서 결정론적 비용 추정의 입력이 됩니다.

`tests/unit/test_llm_client.py`의 `RecordingTransport`는 네트워크 구현체가 아닙니다. 테스트가 남긴 URL, payload, Timeout을 assertion으로 확인하므로 키·네트워크 없이 요청 형식과 오류 분류를 회귀 검증할 수 있습니다.

## 8. 정상 실행 결과

6.1의 정확한 테스트 수와 실행 시간은 이후 장에서 테스트가 추가되면 달라질 수 있습니다. 중요한 결과는 마지막 줄이 `passed`이고 외부 API 키·네트워크 없이 끝나는 것입니다.

```text
... passed
```

6.3에서 모델을 설정하지 않았다면 첫 줄이 비어 있을 수 있고, 다음 줄에는 기본 Timeout `30.0`이 표시됩니다. 이는 라이브 호출 성공을 뜻하지 않습니다. 6.4를 선택했을 때만 제공자와 모델에 따라 달라지는 한국어 답변 뒤에 다음 형식이 출력됩니다.

```text
model=선택한-모델 input_tokens=값
output_tokens=값
```

모델 출력은 사실과 다를 수 있습니다. 정상적인 HTTP 응답과 답변의 사실성은 별개의 문제이며, 근거 확인과 평가가 필요합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `OPENAI_API_KEY must be configured` | `.env`를 만들기만 했거나 키가 비어 있습니다. | 실제 호출이 꼭 필요한 경우에만 `uv run --env-file .env ...`로 명시합니다. 오프라인 테스트에는 키를 추가하지 않습니다. |
| `LLM_MODEL must be configured` | 모델 환경 변수가 비어 있습니다. | 선택한 제공자가 허용하는 모델 식별자를 로컬 `.env`에 설정합니다. |
| `LLM_BASE_URL must start with http:// or https://` | URL에 스킴이 없거나 오타가 있습니다. | 제공자의 HTTPS URL을 확인합니다. 키를 진단 명령에 넣지 않습니다. |
| `LLM provider could not be reached` | 네트워크, DNS, 방화벽 또는 URL을 확인해야 합니다. | 먼저 6.1 Mock 테스트가 통과하는지 확인한 뒤 조직 네트워크 정책과 제공자 상태를 점검합니다. |
| `LLM provider rejected the request (401)` | 키, URL 또는 모델 권한이 맞지 않을 수 있습니다. | 제공자 콘솔에서 권한을 확인하고 노출 의심 키는 폐기합니다. 오류 메시지에 키를 덧붙이지 않습니다. |
| `LLM response does not contain choices` | 제공자가 Chat Completions 응답 형식을 지원하지 않을 수 있습니다. | 제공자 호환성 문서를 확인하거나 Mock 테스트 경로를 사용합니다. |
| `.env`가 `git status --short`에 보임 | 비밀 파일이 추적될 위험이 있습니다. | 커밋을 중단하고 `.gitignore`와 경로를 수정한 뒤 노출된 키를 폐기합니다. |

## 10. 응용 실습

1. `RecordingTransport`를 이용해 `LlmClient`를 생성한 직후에는 전송 호출 수가 `0`이고, `complete()` 후에는 `1`이 되는 테스트를 추가합니다. 실제 API를 호출하지 않아야 합니다.
2. Mock 응답에서 `usage` 필드를 제거하는 테스트를 추가하고, `LlmResponse.usage`의 두 값이 모두 `0`인지 확인합니다.
3. base URL 끝의 슬래시 유무에 관계없이 최종 요청 URL이 `/chat/completions` 하나로 끝나는 테스트를 작성합니다.

## 11. 실무 적용

실무에서는 모델명, URL, Timeout을 ConfigMap 또는 환경별 설정으로, API 키를 Secret 또는 조직의 비밀 관리 시스템으로 분리합니다. 요청 본문, Authorization 헤더, 사용자 원문을 그대로 로그에 남기지 않습니다. 운영 점검은 Mock 테스트를 기본으로 하고, 라이브 점검이 필요할 때만 전용 키·최소 입력·승인·비용 한도를 적용합니다.

이 장의 Client는 기본적으로 재시도하지 않습니다. 재시도는 네트워크 오류와 일시적 상태 코드에만 제한된 횟수로 적용해야 하며, 요청 중복의 비용과 부작용을 고려해야 합니다. [오류 처리 장](08-error-handling.md)에서 이 제한된 재시도 정책을 다룹니다.

## 12. 과제

- **기본:** 빈 메시지와 `tool` 역할이 각각 요청 전에 설정 오류가 되어야 하는 이유를 설명합니다.
- **응용:** `LlmResponseError`가 발생하는 성공 HTTP JSON 형태를 두 가지 더 만들고 Mock 테스트로 검증합니다.
- **심화:** 제공자별 모델 별칭을 허용 목록으로 검증하는 설정 계층을 설계합니다. 실제 키·회사 데이터·제공자 호출을 테스트에 추가하지 않습니다.

## 13. 완료 체크리스트

- [ ] API 키와 모델명을 코드에 쓰지 않고 환경 변수로 분리했다.
- [ ] `LlmSettings`, `LlmClient`, transport의 책임을 구분해 설명할 수 있다.
- [ ] Client 생성만으로는 전송하지 않고 `complete()`가 명시적 전송 지점임을 설명할 수 있다.
- [ ] Timeout의 목적과 요청 전 검증의 필요성을 설명할 수 있다.
- [ ] Mock transport 테스트를 API 키·네트워크 없이 실행했다.
- [ ] 4xx/5xx, 연결 실패, 시간 초과, 잘못된 응답의 차이를 설명할 수 있다.
- [ ] 실제 호출이 선택 사항이며 비용과 외부 전송을 유발함을 이해한다.
- [ ] 다음 장 [System Prompt와 생성 파라미터](06-system-prompt-and-parameters.md)로 이어지는 메시지 경계를 확인했다.

## 14. 핵심 정리

안전한 최초 호출의 핵심은 모델 문자열 하나가 아니라 경계입니다. 설정은 환경 변수에서 읽고, Client 생성과 명시적 전송을 분리하며, transport를 교체 가능하게 만들어 외부 호출 없이 요청·응답 계약을 검증합니다. 실제 호출은 선택 사항으로 남기고, 키·입력·비용을 관리합니다. 다음 장에서는 같은 경계를 유지한 채 System Prompt와 생성 파라미터를 추가합니다.
