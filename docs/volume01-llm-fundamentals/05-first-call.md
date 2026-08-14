# LLM 기초: 안전한 최초 호출

## 1. 학습 목표

이 장을 마치면 OpenAI 호환 LLM API의 요청·응답 경계를 설명하고, 모델명·API 키·기본 URL·Timeout을 환경 변수로 분리해 한 번의 대화 요청을 만들 수 있습니다. 실제 키 없이 Mock 테스트로 요청 형식과 오류 처리를 검증하는 방법도 익힙니다.

## 2. 왜 필요한가

LLM은 함수 호출처럼 보이지만 네트워크, 인증, 요청 형식, 비용이라는 운영 조건을 함께 가집니다. 호출 코드를 화면이나 업무 로직에 직접 섞으면 키가 로그에 남거나 Timeout 없이 대기하고, 테스트 때마다 유료·외부 호출을 하게 됩니다. 이 프로젝트는 전송 계층을 분리하여 테스트에서는 가짜 응답을 사용하고, 학습자가 명시적으로 예제를 실행한 경우에만 실제 제공자에 요청합니다.

## 3. 핵심 개념

**OpenAI 호환 API**는 `POST /chat/completions`에 모델명과 메시지 목록을 JSON으로 보내는 API 형태입니다. `system`, `user`, `assistant` 메시지는 각각 시스템 규칙, 사용자 요청, 이전 모델 응답을 뜻합니다. 이 장의 `ChatMessage`는 이 세 역할과 빈 문자열이 아닌 내용을 먼저 검증합니다.

**Timeout**은 네트워크 요청이 끝나지 않을 때 기다릴 최대 시간(초)입니다. 이 예제의 기본값은 30초입니다. **전송 계층(transport)** 은 HTTP 요청만 담당하는 경계입니다. `LlmClient`는 이 경계에 의존하므로 단위 테스트에서 인터넷 없이 응답을 고정할 수 있습니다.

> [!WARNING]
> `OPENAI_API_KEY`를 코드, Git, 터미널 기록, 오류 보고서에 넣지 마세요. 이 장의 예제는 키가 없을 때 키 값을 포함하지 않는 설정 오류를 냅니다. 실제 호출은 비용과 외부 데이터 전송을 발생시킬 수 있으므로, 학습자가 자신의 키와 제공자 정책을 확인한 뒤에만 실행합니다.

## 4. 동작 구조

```text
.env 또는 현재 셸 환경 변수
        │
        ▼
LlmSettings ──(model, URL, timeout)──► LlmClient
                                            │
                       테스트: RecordingTransport(가짜 응답)
                                            │
                       실습자가 명시 실행: UrllibJsonTransport
                                            ▼
                         OpenAI 호환 /chat/completions API
                                            │
                                            ▼
                         LlmResponse(텍스트, 모델, 토큰 사용량)
```

## 5. 실습 환경

필요 파일은 다음과 같습니다.

- `src/ai_platform/core/settings.py`: 환경 변수와 Timeout을 읽습니다.
- `src/ai_platform/llm/client.py`: 요청 검증, HTTP 경계, 응답 해석을 제공합니다.
- `examples/volume01/first_call.py`: 명시적으로 실행하는 최초 호출 예제입니다.
- `tests/unit/test_llm_client.py`: 외부 통신 없는 Mock 테스트입니다.

먼저 의존성을 준비합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
conda env update --file environment.yml --prune
```

이 명령은 프로젝트 가상환경과 테스트 도구를 설치합니다. Windows 네이티브에서 작업한다면 Git Bash 또는 PowerShell에서 저장소 경로로 이동하되, 이후 명령을 같은 셸에서 실행합니다.

## 6. 단계별 실습

### 6.1 외부 호출 없는 계약 테스트

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/unit/test_llm_client.py -q
```

이 테스트는 `RecordingTransport`에 요청 URL, 메시지, Timeout을 기록하고 미리 정한 JSON 응답을 돌려줍니다. 따라서 API 키도 인터넷 연결도 필요 없습니다. 정상 결과는 다섯 개 테스트의 통과 표시입니다.

### 6.2 최초 호출 코드 읽기

`examples/volume01/first_call.py`는 설정을 읽은 뒤 `LlmClient.complete()`에 다음 두 메시지를 전달합니다.

```python
response = client.complete(
    [
        ChatMessage(role="system", content="당신은 AI 플랫폼 입문 교재 도우미입니다."),
        ChatMessage(role="user", content="AI 업무 처리 플랫폼을 한 문장으로 설명하세요."),
    ]
)
```

클라이언트는 모델명과 메시지 목록으로 JSON을 만들고, `LLM_BASE_URL/chat/completions`에 `POST`합니다. 성공 응답의 첫 번째 `choices[].message.content`와 `usage.prompt_tokens`, `usage.completion_tokens`를 `LlmResponse`로 정규화합니다. 사용량이 없는 호환 제공자는 토큰 값을 `0`으로 반환합니다.

### 6.3 선택 사항: 자신의 제공자로 실제 한 번 호출

다음은 외부 요청을 발생시키는 선택 실습입니다. API 키가 없거나 외부 전송을 원하지 않으면 실행하지 말고 6.1의 테스트만 실행합니다. `.env`는 Python이 자동으로 읽지 않으므로, 이 예제에서는 현재 셸에 제한적으로 불러옵니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cp .env.example .env
# .env를 편집하여 OPENAI_API_KEY와 LLM_MODEL만 자신의 값으로 설정
set -a
. ./.env
set +a
python examples/volume01/first_call.py
```

정상 응답은 세 줄입니다. 첫 줄은 모델의 한국어 답변, 둘째 줄은 모델명과 입력 토큰, 셋째 줄은 출력 토큰입니다. `LLM_BASE_URL`을 비워 두면 기본 OpenAI 호환 주소를 사용합니다. 다른 호환 제공자를 사용할 때만 해당 제공자의 HTTPS 주소를 넣습니다.

## 7. 코드 설명

`LlmClient` 생성자는 빈 모델명, 없는 키, HTTP(S)가 아닌 URL, 0 이하 Timeout을 즉시 거부합니다. 이 검증은 요청 전에 실패하므로 설정 실수로 네트워크 호출을 만들지 않습니다.

`JsonTransport`는 작은 Protocol입니다. 기본 구현인 `UrllibJsonTransport`만 표준 라이브러리 `urllib`로 HTTP 요청을 보냅니다. 테스트의 `RecordingTransport`는 같은 메서드 형태를 구현하지만 네트워크에 연결하지 않습니다. HTTP 4xx/5xx는 `LlmRemoteError`, 연결 실패는 `LlmNetworkError`, 예상과 다른 성공 JSON은 `LlmResponseError`로 구분됩니다.

## 8. 정상 실행 결과

테스트의 정상 결과 예시는 다음과 같습니다.

```text
5 passed
```

실제 호출은 선택한 모델과 제공자에 따라 문장이 달라집니다. 단, `model=... input_tokens=...` 및 `output_tokens=...` 형식이 뒤따라야 합니다. 모델 출력 자체는 사실과 다를 수 있으므로 다음 장에서 System Prompt와 생성 파라미터를 적용한 뒤에도 검토가 필요합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `OPENAI_API_KEY must be configured` | `.env`를 만들기만 하고 셸로 불러오지 않았거나 키가 비어 있습니다. | 실제 호출이 필요한 경우에만 6.3의 `set -a`부터 다시 실행합니다. 테스트만 할 때는 정상적인 보호 동작입니다. |
| `LLM_MODEL must be configured` | 모델 환경 변수가 비어 있습니다. | 제공자가 허용한 모델 식별자를 `.env`의 `LLM_MODEL`에 설정합니다. |
| `LLM provider could not be reached` | 네트워크, DNS, 방화벽 또는 기본 URL을 확인해야 합니다. | URL에 `https://`가 있는지 확인하고, 조직의 네트워크 정책을 확인합니다. 키를 진단 명령에 넣지 않습니다. |
| `LLM provider rejected the request (401)` | 키, URL 또는 모델 권한이 맞지 않을 수 있습니다. | 공급자 콘솔에서 권한을 확인하고, 유출된 키는 폐기합니다. 오류 문자열에 키를 덧붙이지 않습니다. |
| `LLM response does not contain choices` | 선택한 제공자가 Chat Completions 응답 형식을 지원하지 않을 수 있습니다. | 해당 제공자의 호환성 문서를 확인하거나 이 교재의 Mock 테스트 경로를 사용합니다. |

## 10. 응용 실습

`tests/unit/test_llm_client.py`의 `RecordingTransport` 응답에서 `usage` 필드를 제거한 뒤 테스트를 하나 추가하세요. `LlmResponse.usage`가 두 값 모두 `0`이 되는지 확인합니다. 다음으로 `base_url` 끝에 슬래시가 있어도 최종 요청 URL에 슬래시가 중복되지 않는 테스트를 작성하세요. 이 변경은 실제 API를 호출하지 않아야 합니다.

## 11. 실무 적용

실무에서는 제공자별 모델명, URL, Timeout을 배포 환경의 Secret 및 ConfigMap으로 분리합니다. 이 장의 클라이언트는 재시도하지 않습니다. 재시도는 네트워크 오류와 일시적 상태 코드만 제한 횟수로 다루고, 요청 중복에 따른 비용·부작용을 설계한 뒤 추가해야 합니다. 요청 본문, Authorization 헤더, 사용자 원문을 그대로 로그에 기록하지 않는 것도 기본 원칙입니다.

## 12. 과제

- **기본:** 빈 메시지와 `tool` 역할이 각각 설정 오류가 되는 테스트를 설명합니다.
- **응용:** `LlmResponseError`가 발생하는 JSON 형태를 두 가지 더 만들고 테스트합니다.
- **심화:** 제공자별 모델 별칭을 허용 목록으로 검증하는 설정 계층을 설계합니다. 실제 키나 제공자 호출을 테스트에 추가하지 마세요.

## 13. 완료 체크리스트

- [ ] API 키와 모델명을 코드에 쓰지 않고 환경 변수로 분리했다.
- [ ] `system`, `user`, `assistant` 메시지의 책임을 설명할 수 있다.
- [ ] Timeout의 목적을 설명할 수 있다.
- [ ] Mock 전송 계층 테스트를 외부 호출 없이 실행했다.
- [ ] 실제 호출이 선택 사항이며 비용과 외부 전송을 유발함을 이해한다.
- [ ] 4xx/5xx, 연결 실패, 잘못된 응답의 차이를 설명할 수 있다.

## 14. 핵심 정리

LLM 최초 호출의 핵심은 모델 문자열 하나가 아니라 안전한 경계입니다. 설정은 환경 변수에서 읽고, 전송은 교체 가능하게 만들며, 응답 형식과 오류를 명시적으로 검증합니다. 이 기반 위에 다음 장에서 System Prompt와 생성 파라미터를 추가합니다.
