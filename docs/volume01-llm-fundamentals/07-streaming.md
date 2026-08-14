# Streaming: 응답 조각을 안전하게 표시하기

## 1. 학습 목표

이 장을 마치면 스트리밍(Streaming)이 완성된 답변을 한 번에 받는 호출과 어떻게 다른지 설명할 수 있습니다. 또한 Server-Sent Events(SSE)의 `data:` 이벤트에서 텍스트 조각(delta)을 순서대로 처리하고, 네트워크 없는 Mock 테스트로 스트리밍 요청·오류·사용량 계약을 검증할 수 있습니다.

## 2. 왜 필요한가

긴 답변을 모두 생성할 때까지 기다리면 사용자는 서비스가 멈췄다고 느낄 수 있습니다. 스트리밍은 첫 텍스트 조각이 도착하는 즉시 화면에 표시해 이 대기 시간을 줄입니다. AI 업무 처리 플랫폼의 Gateway도 이후 Router, Agent, RAG 결과를 사용자에게 진행 상태와 함께 전달할 수 있어야 합니다.

그러나 화면에 빨리 보인다고 작업이 더 빨리 끝난 것은 아닙니다. 전체 응답 시간, 오류 처리, 비용, 출력 검증은 여전히 관리해야 합니다. 특히 일부 제공자는 스트림 마지막에 사용량을 보내지 않을 수 있으므로, 사용량이 없다는 상태도 정상적으로 다룹니다.

## 3. 핵심 개념

**스트리밍**은 응답 전체 대신 작은 이벤트를 순서대로 전송하는 방식입니다. OpenAI Chat Completions 호환 API에서는 요청에 `stream: true`를 넣고, 응답을 SSE 형식으로 받을 수 있습니다. 한 이벤트의 `choices[0].delta.content`에는 새로 추가할 텍스트만 들어갑니다.

**delta**는 완성 문장이 아닙니다. 예를 들어 `"안녕"`, `"하세요."` 두 조각을 받은 뒤에야 `"안녕하세요."`가 됩니다. 따라서 UI는 조각을 순서대로 덧붙여 표시하고, 저장하거나 JSON으로 검증할 최종 결과는 별도 버퍼에 모아야 합니다.

**종료 이유(finish reason)**는 마지막 선택지에 `stop`, `length` 등으로 올 수 있습니다. `length`는 출력 토큰 상한에 도달해 잘렸을 가능성을 뜻하므로 완성 응답으로 단정하면 안 됩니다. 이 장의 `StreamChunk`는 `delta`, `finish_reason`, 선택적인 `usage`를 분리합니다.

> [!WARNING]
> 스트리밍 조각을 받은 즉시 신뢰하거나 Tool을 실행하지 마세요. 아직 문장이 끝나지 않았고, JSON 구조도 완성되지 않았을 수 있습니다. 권한 검증은 Volume 03, 외부 문서 지시문 분리는 Volume 05에서 별도 경계로 구현합니다.

## 4. 동작 구조

```text
ChatMessage + GenerationParameters
             │
             ▼
LlmClient.stream(..., stream=true)
             │
             ▼
OpenAI 호환 SSE 응답
  data: {"choices":[{"delta":{"content":"안녕"}}]}
  data: {"choices":[{"delta":{"content":"하세요."},"finish_reason":"stop"}]}
  data: [DONE]
             │
             ▼
StreamChunk(delta, finish_reason, usage?)
             │
             ├── 화면: delta를 즉시 출력
             └── 프로그램: 최종 텍스트를 버퍼링·검증

테스트: Mock StreamTransport로 네트워크 없이 이벤트 순서와 오류를 확인
```

## 5. 실습 환경

앞 장의 프로젝트 환경을 그대로 사용합니다.

- `src/ai_platform/llm/client.py`: `LlmClient.stream()`과 SSE 전송·파싱 경계입니다.
- `examples/volume01/streaming.py`: 명시 실행 때만 외부 호출을 하는 콘솔 출력 예제입니다.
- `tests/unit/test_llm_client.py`: Mock 스트림으로 delta, 종료, 사용량, 제공자 오류를 검사합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
conda env update --file environment.yml --prune
```

이 명령은 가상환경과 개발 도구를 동기화합니다. API 키 또는 네트워크 없이도 다음 테스트를 실행할 수 있습니다.

## 6. 단계별 실습

### 6.1 외부 호출 없는 스트림 계약 테스트

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/unit/test_llm_client.py -q
```

테스트는 `stream: true` 요청 필드, `안녕`과 `하세요.` delta의 결합, `stop` 종료 이유, 마지막 사용량 이벤트를 확인합니다. 실제 API 키와 네트워크는 사용하지 않습니다.

### 6.2 delta를 순서대로 출력하기

`examples/volume01/streaming.py`의 핵심 반복문은 다음과 같습니다.

```python
final_usage = None
for chunk in client.stream(messages, generation=GenerationParameters(temperature=0.2)):
    print(chunk.delta, end="", flush=True)
    if chunk.usage is not None:
        final_usage = chunk.usage
```

`flush=True`는 콘솔 버퍼를 기다리지 않고 각 조각을 표시합니다. `chunk.delta`가 빈 문자열인 이벤트도 유효할 수 있습니다. 예를 들어 역할 정보나 종료 정보만 담긴 이벤트입니다. 사용량은 마지막 이벤트에만 올 수 있으므로 `None`을 먼저 허용합니다.

### 6.3 선택 사항: 자신의 제공자로 한 번 실행

아래 명령은 외부 요청과 비용을 발생시킵니다. 외부 전송을 원하지 않거나 키가 없다면 실행하지 말고 6.1 테스트만 실행합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cp .env.example .env
# .env에 OPENAI_API_KEY와 LLM_MODEL을 자신의 값으로만 설정
set -a
. ./.env
set +a
python examples/volume01/streaming.py
```

정상 실행이면 답변 글자가 순서대로 출력된 뒤 사용량 또는 사용량 미반환 안내가 출력됩니다. `.env`는 Git에 추가하지 않습니다.

## 7. 코드 설명

`LlmClient.stream()`은 `complete()`와 같은 메시지·생성 파라미터 계약을 사용하되 payload에 `stream: true`를 추가합니다. `StreamTransport`는 `HttpResponse` iterator를 반환하는 테스트 경계입니다. 단위 테스트의 `RecordingStreamTransport`가 네트워크 없이 같은 경계를 구현하므로 요청과 이벤트 순서를 재현할 수 있습니다.

기본 `UrllibJsonTransport.post_stream()`은 SSE의 단일 `data:` 행만 읽습니다. `[DONE]` 표식을 받으면 반복을 종료하고, JSON 이벤트는 `StreamChunk`로 변환합니다. 이 기초 구현은 텍스트 delta에 한정합니다. Tool call delta, 여러 선택지, 제공자별 SSE 확장은 다음 Volume의 Tool 계약에서 명시적으로 다룹니다.

## 8. 정상 실행 결과

Mock 테스트의 정상 결과에는 다음과 같은 통과 수가 표시됩니다.

```text
17 passed
```

전체 테스트 수는 이후 장에서 추가될 수 있습니다. 선택 실행의 답변 텍스트는 모델마다 다르지만, 답변 뒤에 아래 둘 중 하나가 나타납니다.

```text
사용량: input_tokens=... output_tokens=...
사용량: 제공자가 스트림 사용량을 반환하지 않았습니다.
```

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `LLM stream response does not contain choices` | 제공자가 OpenAI 호환 이벤트 형식을 보내지 않았거나 프록시가 응답을 바꿨습니다. | 제공자 문서에서 스트리밍 형식을 확인하고, 원문 이벤트는 비밀값을 제외해 점검합니다. |
| `LLM stream response has neither choices nor usage` | 빈 이벤트를 JSON 이벤트로 전달했습니다. | SSE 제어 행은 건너뛰고 유효한 `data:` JSON만 전송 계층에서 반환하는지 확인합니다. |
| 글자가 한 번에 보임 | 터미널 또는 프록시가 버퍼링하고 있습니다. | 예제처럼 `flush=True`를 쓰고, Gateway·프록시의 응답 버퍼링 설정을 운영 환경에서 점검합니다. |
| 사용량이 없음 | 제공자가 스트림 사용량 이벤트를 지원하지 않습니다. | `usage is None`을 정상 상태로 처리하고, 제공자별 계측 정책을 문서화합니다. |
| 응답이 중간에 끝남 | `max_output_tokens` 상한 또는 네트워크 단절일 수 있습니다. | `finish_reason`을 기록하고, `length`이면 상한·프롬프트 길이·재시도 정책을 검토합니다. |
| 401·429·503 응답 | 키, 할당량 또는 제공자 장애입니다. | 키를 로그에 넣지 말고 설정·할당량·상태 페이지를 확인합니다. 재시도는 이후 장의 제한된 정책으로 구현합니다. |

## 10. 응용 실습

1. Mock 스트림에 빈 delta와 `finish_reason="length"` 이벤트를 추가하고, 최종 텍스트와 종료 이유를 검사하는 테스트를 작성합니다.
2. 스트림 조각을 리스트에 모은 뒤 한 번만 JSON 검증하는 함수를 설계합니다. 조각마다 JSON을 파싱하면 왜 실패하는지 기록합니다.
3. 사용자 취소를 가정해 iterator 소비를 중단할 때 UI, 로그, 비용 측정에 남겨야 할 정보를 설계합니다.

## 11. 실무 적용

운영 Gateway는 클라이언트 연결이 끊겼을 때 제공자 스트림을 계속 소비할지, 취소할지 명확한 정책이 필요합니다. 각 선택은 비용과 관찰 가능성에 영향을 줍니다. 첫 delta 시간, 전체 완료 시간, 종료 이유, 제공자 오류 종류를 비밀값과 사용자 원문 없이 측정하면 지연 문제를 구분하는 데 도움이 됩니다.

스트리밍 응답도 최종 검증 대상입니다. UI에 보이는 중간 텍스트와 저장·Tool 실행에 사용할 완성 텍스트를 구분합니다. 이 플랫폼은 다음 오류 처리 장에서 시간 초과, 제공자 오류, 재시도 가능한 오류를 안전한 한도 안에서 더 구체화합니다.

## 12. 과제

- **기본:** delta와 완성 응답의 차이를 두 문장으로 설명합니다.
- **응용:** `finish_reason="length"`일 때 사용자에게 표시할 안내와 내부 로그 항목을 설계합니다.
- **심화:** 여러 제공자의 서로 다른 스트리밍 형식을 `StreamChunk` 계약으로 변환하는 어댑터 경계를 설계하고 Mock 테스트 사례를 작성합니다.

## 13. 완료 체크리스트

- [ ] 스트리밍이 첫 응답 표시 시간을 줄이는 이유를 설명할 수 있다.
- [ ] delta를 순서대로 결합해야 하는 이유를 설명할 수 있다.
- [ ] `finish_reason`과 사용량 미반환을 구분해 처리할 수 있다.
- [ ] Mock 스트림 테스트를 외부 호출 없이 실행했다.
- [ ] 스트림 조각을 즉시 신뢰하거나 Tool을 실행하면 안 됨을 이해한다.
- [ ] 선택 실습이 외부 전송·비용을 발생시킬 수 있음을 확인했다.

## 14. 핵심 정리

`LlmClient.stream()`은 기존 메시지·생성 파라미터 계약에 `stream: true`만 추가하고 `StreamChunk` iterator를 제공합니다. SSE delta는 표시에는 즉시 사용하되, 최종 저장·검증·위험 작업에는 완성된 결과와 별도 권한 경계를 사용해야 합니다.
