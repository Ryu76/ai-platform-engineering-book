# Tool 감사 로그: 최소 데이터로 실행 경계 추적하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- Tool 실행의 성공·거부·handler 실패를 구조화된 이벤트로 구분한다.
- 요청 ID, Tool 이름, 위험도, 승인 ID, 결과만 기록하고 원문 인자·결과·예외는 남기지 않는다.
- 감사 로깅이 allowlist, JSON Schema, 위험도 및 승인 검증을 대체하지 않게 한다.
- 교육용 in-memory sink와 운영용 변경 불가능 감사 저장소의 차이를 설명한다.

## 2. 감사는 권한을 주지 않는다

`execute_audited()`는 검증을 다시 구현하거나 handler를 직접 부르지 않습니다. 항상 기존 `execute_authorized()` 하나를 호출합니다. 따라서 감사 이벤트를 남긴다는 이유로 미등록 Tool 또는 Schema 밖 인자가 실행될 수 없습니다.

```text
신뢰되지 않은 Tool 요청 + 승인 기록 + in-memory audit sink
                         │
                         ▼
                 execute_authorized()
                 │       │
                 │       ├── allowlist / Schema / 정책 / 승인 거부
                 │       │                   │
                 ▼       ▼                   ▼
           순수 handler 성공              DENIED 이벤트
                 │
                 ├── 예외 ───────────────► FAILED 이벤트
                 ▼
           SUCCEEDED 이벤트
```

각 `ToolAuditEvent`는 아래 다섯 필드만 가집니다.

| 필드 | 목적 | 의도적으로 제외한 것 |
|---|---|---|
| `request_id` | 요청과 감사 기록의 상관관계 | 사용자 프롬프트 |
| `tool_name` | 어느 allowlisted Tool인지 식별 | Tool 설명, handler 코드 |
| `risk` | 선언된 `LOW`/`HIGH` 위험도 확인 | 자동 위험도 추론 |
| `approval_id` | 고위험 승인 기록 상관관계 | 승인 토큰·서명·승인자 개인정보 |
| `outcome` | `succeeded`, `denied`, `failed` 구분 | 원문 예외와 stack trace |

특히 `arguments`, Tool `output`, 예외 메시지는 이벤트 모델에 필드 자체가 없습니다. 이 예제에서 `approval_id`는 인증 정보가 아니라 상관관계용 식별자입니다. 실제 비밀이나 bearer token을 그 이름에 넣어서는 안 됩니다.

## 3. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/audited_tool_execution.py
pytest tests/volume03/test_tool_audit.py -q
```

예제는 `safe_text_case` 하나만 allowlist에 넣고, 고정된 교육용 승인 기록으로 문자열을 대문자로 바꿉니다. 생성되는 감사 이벤트에는 인자 `AI Platform` 또는 Tool 결과가 없고, 파일·셸·네트워크·환경 변수·외부 서비스에 접근하지 않습니다.

```text
safe_text_case: AI PLATFORM
audit: request_id=audit-demo-request-001, tool=safe_text_case, risk=high, approval_id=audit-demo-approval-001, outcome=succeeded
```

테스트는 다음을 확인합니다.

1. 성공 이벤트가 다섯 최소 필드를 정확히 남기고 원문 인자와 결과를 보관하지 않습니다.
2. 승인 없는 고위험 요청은 handler 전에 거부되고 `DENIED`로 기록됩니다.
3. handler의 예상 밖 오류는 권한 거부와 혼동하지 않고 `FAILED`로 기록합니다.
4. `events`는 tuple 스냅샷이므로 호출자가 기존 감사 기록을 수정할 수 없습니다.

## 4. 코드 읽기 순서

1. `ToolAuditEvent`가 감사 데이터 모델을 다섯 최소 필드로 고정합니다.
2. `InMemoryToolAuditSink.record()`는 교육용 메모리에 이벤트 하나만 append합니다.
3. `execute_audited()`가 `execute_authorized()`를 호출합니다.
4. `ToolRegistryError` 계열의 경계 거부는 `DENIED`, 다른 handler 예외는 `FAILED`, 정상 반환은 `SUCCEEDED`로 한 번 기록합니다.

`FAILED`가 있어도 원문 예외를 감사 이벤트에 복사하지 않습니다. 호출 경로는 원래 예외를 그대로 받아 적절한 사용자 안전 오류 처리 또는 운영 관찰 경로로 넘길 수 있습니다.

## 5. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `human approval is required`와 `DENIED` | `HIGH` Tool에 일치하는 승인이 없습니다. | 자동 승인하지 말고 검증 가능한 승인 워크플로로 보냅니다. |
| `tool is not allowlisted`와 `DENIED` | 모델 요청 Tool이 registry에 없습니다. | 로그를 근거로 Tool을 자동 등록하지 않습니다. |
| `FAILED` | handler가 검증 뒤 실패했습니다. | 성공으로 기록하거나 timeout 뒤 재실행하지 말고 원인과 멱등성을 별도로 검토합니다. |
| 감사 이벤트에 민감 데이터가 필요해 보임 | 원문을 보관하면 로그가 새 데이터 유출 경로가 됩니다. | 별도 접근 제어 저장소의 안전한 지문·정책화된 요약을 설계합니다. |

## 6. 운영 적용 시 추가할 것

이 sink는 프로세스 메모리에만 있고 재시작하면 사라지며, 동시성·내구성·접근 제어·위변조 방지 기능이 없습니다. 운영에서는 승인 시스템과 분리된 변경 불가능 저장소, 인증된 작성자, tenant/리소스 범위, 정책 버전, 시간·만료·단회 사용, 보존 기간, 접근 감사와 무결성 검증을 적용해야 합니다.

민감 인자는 일반 로그, tracing attribute, 예외 문자열, metric label에도 넣지 마세요. 꼭 상관관계가 필요하다면 정규화 규칙·키 관리·접근 정책을 명시한 안전한 지문을 별도 위협 모델 아래 설계합니다. 감사 로그 자체도 실행 권한이 아니므로 allowlist, Schema, 최소 권한 자격 증명, 승인과 실제 리소스 상태 재검증을 계속 유지합니다.

## 7. 완료 체크리스트

- [ ] 감사 이벤트에 원문 인자·결과·예외가 없는 이유를 설명할 수 있다.
- [ ] 승인 없는 `HIGH` 요청이 handler 전에 `DENIED`로 기록됨을 확인했다.
- [ ] 감사 wrapper가 `execute_authorized()`를 통해서만 실행함을 확인했다.
- [ ] 교육용 sink가 내구성 있는 운영 감사 로그가 아님을 설명할 수 있다.
- [ ] 예제와 테스트를 네트워크·실제 부작용 없이 실행했다.
