# Tool 실행: timeout과 제한된 retry

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- Tool의 **한 번의 시도**에 timeout을 적용한다.
- 명시적으로 `RetryableToolError`를 낸 순수 Tool만 작은 횟수로 재시도한다.
- timeout, retry가 allowlist와 JSON Schema 검증을 우회하지 못하게 한다.
- Python thread timeout이 실행을 강제 취소하지 못한다는 한계를 설명한다.

## 2. 실행 경계

`execute_with_policy()`는 매 시도마다 기존 `ToolRegistry.execute()`를 호출합니다. 따라서 재시도 경로를 추가해도 미등록 Tool, 누락·추가 인자, enum 위반은 handler 전에 거부됩니다.

```text
신뢰되지 않은 Tool 요청
        │
        ▼
각 시도: ToolRegistry.execute()
   │         │
   │         ├── allowlist / Schema 실패 ──► 즉시 거부, 재시도 없음
   ▼
순수 handler의 RetryableToolError ──► 최대 3회까지 재시도
   │
   ├── 다른 예외 ──► 즉시 실패
   ├── timeout ────► 즉시 실패, 재시도 없음
   ▼
ToolResult
```

`ToolExecutionPolicy`는 양의 유한 `timeout_seconds`와 총 `max_attempts` 1~3만 허용합니다. 무한 대기와 무제한 재시도를 코드 수준에서 만들지 않습니다. retry 대상은 네트워크 오류처럼 넓은 예외 분류가 아니라 Tool handler가 의도적으로 올린 `RetryableToolError` 하나입니다.

> [!WARNING]
> 이 구현의 Python thread timeout은 호출자가 기다리기를 멈추게 할 뿐, 이미 시작한 handler를 안전하게 강제 종료하지 못합니다. timeout 뒤 worker가 계속 실행될 수 있으므로 이 예제처럼 부작용 없는 handler에만 사용합니다. 파일 삭제, 결제, 배포, 권한 변경에는 이 패턴을 적용하지 마세요. 운영 환경에서는 취소 가능한 원격 작업 ID, 멱등성 키, 트랜잭션 경계, 사람 승인이 별도로 필요합니다.

## 3. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/controlled_tool_execution.py
```

예제는 등록된 `retryable_upper` 하나만 사용합니다. 첫 호출은 코드에 고정된 테스트용 `RetryableToolError`이고, 두 번째 호출은 문자열 대문자 변환만 합니다. API 키, 네트워크, 파일·셸·환경 변수 접근은 없습니다.

```text
retryable_upper: AI PLATFORM (2 attempts)
```

회귀 테스트도 실행합니다.

```bash
pytest tests/volume03/test_tool_execution.py -q
```

테스트는 성공 전 두 번의 재시도, allowlist/추가 인자 실패의 **미재시도**, timeout의 즉시 반환, retry 횟수 소진과 정책 상한을 검증합니다. timeout 테스트의 worker는 `Event`로 해제해 테스트 뒤에도 남지 않게 합니다.

## 4. 코드 읽기 순서

1. `ToolExecutionPolicy`가 timeout과 총 시도를 검증합니다.
2. `_execute_once()`가 daemon worker에서 **기존** `registry.execute()`의 결과 또는 예외를 받습니다.
3. `execute_with_policy()`는 `RetryableToolError`만 다음 시도로 넘깁니다.
4. `ToolExecutionTimeoutError`, `ToolArgumentsError`, `ToolNotAllowedError` 및 다른 오류는 재시도하지 않습니다.

`daemon=True`는 교육용 timeout 뒤 완료되지 않은 순수 worker가 프로세스 종료를 막지 않게 할 뿐, 취소 기능이나 안전성을 보장하지 않습니다.

## 5. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `tool execution timed out` | handler가 정책 시간 안에 완료되지 않았습니다. | 결과를 성공으로 취급하지 말고 실패를 기록합니다. 작업을 강제 재호출하지 않습니다. |
| `retryable tool failure after ...` | 모든 제한된 시도가 일시 실패했습니다. | 모델에 안전한 오류 요약을 돌리고 상위 워크플로가 중단·대체·승인을 결정하게 합니다. |
| `tool is not allowlisted` | 모델이 등록되지 않은 이름을 제안했습니다. | retry로 이름을 바꾸거나 자동 등록하지 않습니다. |
| `unexpected argument` | Schema 밖 인자가 들어왔습니다. | 인자를 무시하지 말고 거부합니다. |

## 6. 운영 적용 시 추가할 것

실제 I/O Tool은 timeout 전에 실행할 수 있는지부터 검토해야 합니다. 재시도한다면 호출마다 멱등성 키, 요청 ID, 최대 비용, backoff, 분산 rate limit을 둡니다. timeout 뒤 상태를 조회할 수 없는 작업은 자동 재시도하지 않고 사람 또는 내구성 있는 작업 큐가 처리합니다. 위험 작업에는 allowlist와 Schema 외에도 호출자 권한, 승인 기록, 감사 로그가 필요합니다.

## 7. 완료 체크리스트

- [ ] 재시도가 실행 권한을 추가하지 않는다는 점을 설명할 수 있다.
- [ ] allowlist와 Schema 오류가 handler 및 retry에 도달하지 않음을 확인했다.
- [ ] `RetryableToolError`만 최대 세 번 시도됨을 확인했다.
- [ ] timeout이 worker 강제 취소가 아님을 설명할 수 있다.
- [ ] 예제와 테스트를 네트워크·실제 부작용 없이 실행했다.
