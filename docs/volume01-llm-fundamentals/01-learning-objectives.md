# LLM 기초: 학습 목표와 출발점

## 0. 이 교본을 실제로 공부하는 방법

이 문서는 "목표를 읽고 끝내는 소개"가 아닙니다. **읽기 → 오프라인 실행 → 결과 기록 → 체크리스트 확인 → 다음 장**의 순서로 진행하는 첫 번째 학습 안내서입니다.

### 시작 전 한 번만 할 일

1. [Windows 준비](../setup/windows.md)와 [Anaconda 환경 설정](../setup/anaconda.md)을 완료합니다.
2. Anaconda PowerShell Prompt에서 저장소 루트로 이동해 `conda activate ai-platform-engineering-book`를 실행합니다.
3. `python --version`이 3.12 계열인지, `python -c "import ai_platform"`가 오류 없이 끝나는지 확인합니다.
4. API 키 없이 시작합니다. 이 Volume의 기본 경로는 모두 오프라인 데모와 Mock 테스트입니다.

### 권장 진도: 6회 세션, 세션당 60~90분

| 세션 | 읽을 순서 | 직접 실행할 것 | 남길 산출물 | 다음으로 갈 기준 |
|---|---|---|---|---|
| 1 | 이 문서 → [왜 필요한가](02-why-it-matters.md) | `chat_cli.py --offline-demo` | LLM이 보장하지 않는 것 3가지 | 오프라인 데모가 네트워크·키 없이 실행됨을 설명한다. |
| 2 | [LLM·Transformer·Token](03-theory.md) → [환경 설정](04-environment-setup.md) | `token_budget.py`, 단위 테스트 | 입력·출력 토큰과 context window 관계 그림 | 활성 Conda 환경에서 테스트가 통과한다. |
| 3 | [안전한 최초 호출](05-first-call.md) → [System Prompt와 생성 파라미터](06-system-prompt-and-parameters.md) | 파라미터 데모·Mock 테스트 | System/User/Assistant 메시지 각 1개 | 사용자 입력이 System 규칙을 바꾸면 안 되는 이유를 설명한다. |
| 4 | [Streaming](07-streaming.md) → [오류 처리](08-error-handling.md) | streaming·error demo | timeout/retry가 필요한 경우 2개 | 실패를 키 추가나 재시도로 덮지 않는 경계를 설명한다. |
| 5 | [토큰 사용량과 비용](09-usage-and-cost.md) → [CLI 챗봇](10-cli-chatbot.md) | usage demo·offline CLI | 비용 상한과 종료 명령 정책 | `/exit`이 모델 호출 없이 종료되는지 확인한다. |
| 6 | [미니 프로젝트](11-mini-project.md) → [과제](12-exercises.md) → [핵심 정리](11-summary.md) | 통합 테스트·완료 체크리스트 | 과제 답안과 테스트 결과 | 체크리스트를 모두 스스로 설명하고 다음 Volume으로 이동한다. |

> **한 세션의 최소 완료 규칙:** 문서를 읽은 뒤 반드시 코드 블록 한 개 이상을 실행하고, 결과·오류·이해가 안 된 점을 [학습 로그 템플릿](learning-log-template.md) 또는 개인 노트에 3줄 이상 남깁니다. 테스트가 실패하면 다음 장으로 넘어가지 말고 해당 장의 "오류 해결" 표를 먼저 사용합니다.

### 막혔을 때의 순서

1. 명령을 실행한 터미널에서 `conda activate ai-platform-engineering-book`를 다시 확인합니다.
2. 오류 메시지 전문과 실행한 명령을 기록합니다. API 키나 패키지를 임의로 추가하지 않습니다.
3. 해당 장의 오류 해결 표를 확인하고, 같은 테스트 한 개만 다시 실행합니다.
4. 그래도 해결되지 않으면 "어떤 장의 어떤 명령에서 어떤 오류가 났는지"를 기준으로 질문합니다.

## 1. 학습 목표

이 장은 이후 실습의 지도 역할을 합니다. 장을 마치면 다음을 할 수 있어야 합니다.

- 생성형 AI(Generative AI)와 대규모 언어 모델(Large Language Model, LLM)의 역할을 구분한다.
- 토큰(Token), 컨텍스트 윈도우(Context Window), 입력·출력 토큰의 관계를 한 문장으로 설명한다.
- System, User, Assistant 메시지의 책임을 구분한다.
- Temperature, Top-p, 최대 출력 토큰, Stop Sequence가 생성 결과에 주는 영향을 설명한다.
- 환경 변수로 API 키를 관리하는 Python 클라이언트의 경계를 확인한다.
- Streaming, Timeout, HTTP 오류, 제한된 재시도가 왜 필요한지 설명한다.
- API 키·네트워크 없이 오프라인 데모와 Mock 테스트를 실행한다.

## 2. 왜 필요한가

AI 업무 처리 플랫폼은 사용자의 자연어 요청을 받는 입구에서 시작합니다. 하지만 LLM은 항상 정확한 답을 보장하지 않으며, 라이브 호출은 외부 전송과 비용을 수반합니다. 따라서 이 Volume의 첫 목표는 특정 모델의 답변을 평가하는 일이 아니라 **안전하고 검증 가능한 호출 경계**를 만드는 일입니다.

이 경계는 다음 Volume에서 Prompt Template, RAG 문맥, Tool Calling, Agent 상태가 추가되어도 유지됩니다. 입력 데이터와 시스템 규칙, 외부 전송과 오프라인 검증을 처음부터 분리하면 기능을 확장해도 테스트가 유료 API나 비밀값에 의존하지 않습니다.

> [!WARNING]
> `OPENAI_API_KEY` 같은 실제 비밀값, 회사 문서, 개인정보를 코드·Git·터미널 공유 기록에 넣지 마세요. `--offline-demo`와 Mock 테스트는 API 키·네트워크·비용 없이 실행됩니다. 라이브 모드는 학습자가 자신의 제공자 정책과 비용을 확인한 경우에만 선택합니다.

## 3. 핵심 개념

- **LLM:** 많은 텍스트 패턴을 학습해 다음 토큰을 예측하는 모델입니다. 계산, 권한 확인, 최신 사실 확인을 보장하는 시스템은 아닙니다.
- **토큰:** 모델이 텍스트를 처리하는 단위입니다. 글자 수와 같지 않으며, 입력과 출력 모두 사용량·비용·한도에 영향을 줍니다.
- **컨텍스트 윈도우:** 한 요청에서 모델이 함께 볼 수 있는 토큰의 상한입니다. System 메시지, 대화 이력, 사용자 입력, RAG 문서, 모델 출력이 함께 차지합니다.
- **메시지 역할:** System은 서비스 규칙, User는 사용자 요청, Assistant는 이전 응답입니다. 사용자 입력을 System 규칙으로 취급하면 안 됩니다.
- **생성 파라미터:** Temperature와 Top-p는 후보 선택의 다양성을 조절합니다. 최대 출력 토큰은 응답 길이 상한이며 Stop Sequence는 지정한 문자열에서 생성을 멈추게 합니다.
- **Hallucination(환각):** 그럴듯하지만 근거가 없거나 틀린 내용을 생성하는 현상입니다. 중요한 결과는 검증된 코드, 출처, 사람 검토로 확인합니다.

## 4. 동작 구조

```text
학습자 입력 또는 테스트 데이터
           │
           ▼
메시지 역할·파라미터 검증
           │
           ├── 오프라인 경로 ──► OfflineDemoClient / MockTransport
           │                         │
           │                         └── 결정론적 응답, 외부 전송 없음
           │
           └── 명시적 라이브 경로 ──► LlmSettings(환경 변수)
                                         │
                                         ▼
                                  LlmClient + Timeout
                                         │
                                         ▼
                            OpenAI 호환 API (선택 사항)
                                         │
                                         ▼
                         응답·사용량·오류를 안전하게 처리
```

오프라인 경로는 학습과 CI의 기본 경로입니다. 라이브 경로는 `LlmClient.complete()` 또는 `stream()`을 명시적으로 호출할 때만 제공자에 요청합니다.

## 5. 실습 환경

이 장에서 확인할 파일은 다음과 같습니다.

- `src/ai_platform/core/settings.py`: 모델명, API 키, 기본 URL, Timeout을 환경 변수에서 읽습니다.
- `src/ai_platform/llm/client.py`: 메시지·파라미터 검증과 교체 가능한 HTTP 전송 경계를 제공합니다.
- `examples/volume01/chat_cli.py`: `--offline-demo`로 시작할 수 있는 CLI 챗봇입니다.
- `tests/unit/test_llm_client.py`: Mock 전송 계층을 사용하는 단위 테스트입니다.
- `tests/integration/test_volume01_chat_cli.py`: 별도 프로세스에서 오프라인 CLI를 검증합니다.

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
conda activate ai-platform-engineering-book
conda env update --file environment.yml --prune
```

`conda env update --file environment.yml --prune`는 프로젝트와 검사 도구를 교재 전용 Conda 환경에 준비합니다. 실제 키를 설정할 필요는 없습니다.

## 6. 단계별 실습

### 6.1 안전한 오프라인 CLI 실행

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt (Conda 활성화 뒤)
@'
학습 목표를 한 문장으로 설명해 주세요.
/exit
'@ | python examples/volume01/chat_cli.py --offline-demo
```

이 명령은 두 줄의 로컬 입력을 CLI에 전달합니다. `OfflineDemoClient`가 마지막 사용자 입력을 포함한 결정론적 응답을 만들고 `/exit`은 모델에 전송하지 않고 종료합니다. 네트워크와 API 키를 사용하지 않습니다.

### 6.2 Mock 단위 테스트 실행

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt (Conda 활성화 뒤)
pytest tests/unit/test_llm_client.py tests/unit/test_chat.py -q
```

이 테스트는 `RecordingTransport`와 테스트용 입력·출력 함수를 주입합니다. 요청 형식, 비밀값 없는 오류 안내, 대화 이력, 종료 명령을 실제 제공자 없이 확인합니다.

### 6.3 다음 장의 문제로 연결하기

오프라인 CLI 응답은 입력을 다시 보여 줄 뿐 사실을 검증하지 않습니다. 다음 장 [왜 필요한가](02-why-it-matters.md)에서 LLM이 잘하는 일과 하지 말아야 할 일을 구분합니다. 이어서 [LLM·Transformer·Token](03-theory.md)에서 토큰과 컨텍스트 윈도우의 내부 관계를 살펴봅니다.

## 7. 코드 설명

`examples/volume01/chat_cli.py`는 `--offline-demo`가 지정되면 `OfflineDemoClient`를 만들고, 이 모드에서는 `LlmSettings`와 API 키를 읽지 않습니다. `OfflineDemoClient.complete()`는 `LlmResponse` 형태를 반환하므로 실제 클라이언트와 같은 콘솔 흐름을 검증할 수 있습니다.

`src/ai_platform/llm/client.py`의 `ChatMessage`는 `system`, `user`, `assistant` 역할과 비어 있지 않은 내용을 먼저 검증합니다. `LlmClient`는 모델명, 키, URL, Timeout을 확인한 후에만 HTTP 전송 계층을 사용합니다. 테스트는 그 전송 계층을 가짜 구현으로 바꾸므로 외부 호출 없이 요청 계약을 검사할 수 있습니다.

이 분리는 이후 Prompt Runner, Retriever, Router가 추가되어도 유지할 경계입니다. 신뢰되지 않은 사용자 입력과 문서는 데이터로 취급하고, 시스템 규칙·권한·위험 작업 승인과 섞지 않습니다.

## 8. 정상 실행 결과

6.1의 오프라인 명령은 운영체제의 프롬프트 표시 차이에 따라 공백이 다를 수 있지만, 다음 내용을 포함합니다.

```text
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
AI> 오프라인 데모 응답: '학습 목표를 한 문장으로 설명해 주세요.' 요청을 기록했습니다.
대화를 마칩니다.
```

6.2의 테스트 결과는 설치된 pytest 버전에 따라 시간은 달라지지만 `passed`로 끝나야 합니다. 실패하면 9절 표의 원인부터 확인하고, 실제 API 키를 추가해 해결하려 하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `No module named ai_platform` | 활성 Conda 환경이 아닌 시스템 Python으로 실행했을 수 있습니다. | 저장소 루트에서 `conda env update --file environment.yml --prune` 후 `python ...`을 사용합니다. |
| `unrecognized arguments` | 이 예제는 `--offline-demo`만 지원합니다. | 메시지를 인자가 아니라 표준 입력으로 전달하거나, 대화형으로 실행합니다. |
| `LLM 설정을 확인하세요` | `--offline-demo` 없이 라이브 모드를 시작했습니다. | 오프라인 학습에는 `--offline-demo`를 붙입니다. 라이브 모드는 키·모델을 환경 변수로 설정한 뒤에만 선택합니다. |
| 응답에 입력 문장이 그대로 나타남 | 오프라인 데모의 의도된 결정론적 동작입니다. | 사실 답변으로 해석하지 말고 콘솔 흐름과 종료 경계만 확인합니다. |
| 테스트가 실패함 | 의존성 또는 이전 코드 변경을 확인해야 합니다. | 실패한 테스트 이름을 먼저 재실행합니다. 키·네트워크를 추가하지 말고 Mock 계약과 가상환경을 점검합니다. |

## 10. 응용 실습

1. `tests/unit/test_chat.py`에서 `OfflineDemoClient`와 같은 인터페이스의 가짜 클라이언트를 만들고, `/quit`이 `complete()`를 호출하지 않는지 테스트합니다.
2. `GenerationParameters(temperature=0.2, max_output_tokens=100)`를 만들고, 각 값이 답변의 결정성·길이 상한과 어떤 관계인지 [System Prompt와 생성 파라미터](06-system-prompt-and-parameters.md)를 읽은 뒤 설명합니다. 이 과제에서는 라이브 호출을 하지 않습니다.
3. 사용자 요청에 "시스템 규칙을 무시하라"라는 문장이 포함되어도 System 메시지가 바뀌지 않아야 하는 이유를 적습니다. 실제 방어 구현은 Volume 02에서 Prompt Injection과 함께 확장합니다.

## 11. 실무 적용

실무 서비스는 모델명·Timeout 같은 비밀이 아닌 설정과 API 키 같은 비밀값을 분리해 관리합니다. 요청에는 Timeout과 제한된 재시도 정책을 두고, 요청 본문·Authorization 헤더·원문 개인정보를 로그에 남기지 않습니다. 모델 응답은 확정된 업무 명령이 아니므로 결제, 파일 삭제, 배포, 권한 변경 같은 작업은 검증된 Tool과 별도의 사람 승인을 거쳐야 합니다.

사용량과 컨텍스트 제한은 기능이 늘수록 중요해집니다. 이후 CLI 대화 이력, RAG 문서, Agent 메시지는 모두 입력 토큰을 차지합니다. Volume 01에서는 사용량을 확인하는 기반을 만들고, 이후 Volume에서 검색 품질·라우팅 정책·운영 관측으로 확장합니다.

## 12. 과제

- **기본:** 토큰과 글자 수가 항상 같지 않은 이유, 그리고 컨텍스트 윈도우에 포함되는 항목 네 가지를 설명합니다.
- **응용:** System, User, Assistant 메시지를 각각 하나씩 작성하고, 사용자 메시지를 System 역할에 넣었을 때의 위험을 설명합니다.
- **심화:** 라이브 호출을 하지 않는 CI에서 검증할 계약 세 가지와 라이브 호출 전 사람 승인이 필요한 조건을 설계합니다.

## 13. 완료 체크리스트

- [ ] LLM이 자연어 생성 모델이며 최신 사실·정확한 계산을 보장하지 않음을 설명할 수 있다.
- [ ] 토큰, 입력·출력 토큰, 컨텍스트 윈도우의 관계를 설명할 수 있다.
- [ ] System, User, Assistant 메시지의 책임을 구분했다.
- [ ] Temperature, Top-p, 최대 출력 토큰, Stop Sequence의 목적을 설명할 수 있다.
- [ ] 실제 API 키를 코드·Git·출력에 넣지 않았다.
- [ ] `--offline-demo`가 API 키와 네트워크를 사용하지 않음을 실행으로 확인했다.
- [ ] Mock 단위 테스트를 통과시켰다.
- [ ] LLM 응답을 위험 작업의 승인 근거로 사용하지 않는 이유를 설명할 수 있다.
- [ ] 다음 장 [왜 필요한가](02-why-it-matters.md)로 이어지는 학습 순서를 확인했다.

## 14. 핵심 정리

이 Volume은 LLM을 단순한 문자열 생성 함수가 아니라 외부 전송·비용·오류·한도를 가진 의존성으로 다룹니다. System 규칙과 사용자 데이터를 분리하고, 설정과 전송 계층을 분리하며, 오프라인 데모와 Mock 테스트를 기본 검증 경로로 사용합니다. 다음 장에서는 이 안전한 경계가 필요한 이유와 LLM의 역할 한계를 더 구체적으로 다룹니다.
