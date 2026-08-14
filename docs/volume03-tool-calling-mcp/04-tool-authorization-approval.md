# Tool 권한: 위험도와 사람 승인

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- allowlist된 Tool마다 위험도를 **명시적으로** 정한다.
- 고위험 요청을 사람 승인 기록 없이는 handler에 전달하지 않는다.
- 승인 기록을 `request_id`, Tool 이름, JSON 인자 전체에 묶어 재사용·인자 바꿔치기를 거부한다.
- 승인 기록이 allowlist와 JSON Schema 검증을 대체하지 않는다는 점을 설명한다.

## 2. 승인도 실행 권한이 아니다

`execute_authorized()`의 순서는 의도적으로 고정되어 있습니다.

```text
신뢰되지 않은 모델 Tool 요청 + (선택) 승인 기록
                    │
                    ▼
      ToolRegistry.validate_request()
       │                 │
       │                 ├── 미등록 / Schema 실패 ──► 즉시 거부
       ▼
ToolAuthorizationPolicy 위험도 조회
       │
       ├── 정책 누락 ───────────────────────────────► 즉시 거부
       ├── LOW ────────────────────────────────────► ToolRegistry.execute()
       ▼
HIGH + request_id·Tool·인자가 모두 일치한 승인
                    │
                    ▼
          ToolRegistry.execute() ──► 순수 handler
```

`ApprovalGrant`는 `approval_id`, `request_id`, `tool_name`, 정규화된 JSON 인자를 보관합니다. 따라서 `request-1`의 `{"text":"approved"}` 승인 기록을 `request-2` 또는 `{"text":"changed"}` 요청에 붙이면 거부됩니다. 인자의 키 순서·공백에는 영향을 받지 않습니다.

중요하게도 승인 확인보다 먼저 `ToolRegistry.validate_request()`를 호출하고, 최종 실행은 다시 `ToolRegistry.execute()`를 통과합니다. 그러므로 승인 기록을 제시해도 미등록 `delete_file`, 누락 필드, 추가 `path` 필드는 handler에 도달할 수 없습니다.

> [!WARNING]
> `ApprovalGrant.for_request()`는 이 장에서 **신뢰된 승인 워크플로가 발행한 기록을 모사**하는 순수 교육용 생성자입니다. 호출자가 임의로 생성할 수 있는 Python 객체는 사람 신원, 서명, 만료, 단회 사용을 증명하지 않습니다. 운영에서는 인증된 승인 UI/워크플로가 서버 측 불변 저장소에 승인자·사유·시각·만료·단회 사용 상태를 기록하고, 서명 또는 검증 가능한 참조를 실행 서비스가 확인해야 합니다.

## 3. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/approved_tool_execution.py
pytest tests/volume03/test_tool_authorization.py -q
```

예제는 `SAFE_TEXT_CASE` 하나를 registry allowlist에 등록하고, 교육 목적상 `HIGH`로 분류합니다. 승인 뒤 실행하는 handler는 고정 문자열의 소문자 변환만 수행합니다. 파일 삭제·쓰기, 셸, 네트워크, 환경 변수, 실제 결제·배포·권한 변경은 전혀 수행하지 않습니다.

```text
safe_text_case: ai platform (approved demo)
```

테스트는 다음을 확인합니다.

1. 고위험 Tool은 정확히 일치하는 승인 기록이 있을 때만 한 번 실행됩니다.
2. 승인 누락, 다른 요청 ID, 바뀐 인자는 handler 호출 전 거부됩니다.
3. 승인 기록이 있어도 allowlist와 추가 인자 검증을 우회하지 못합니다.
4. `LOW`도 명시적 위험도 정책이 있어야 하며, 정책이 누락된 Tool은 거부됩니다.

## 4. 코드 읽기 순서

1. `ToolAuthorizationPolicy`는 Tool 이름마다 `ToolRisk.LOW` 또는 `ToolRisk.HIGH`만 받습니다. 기본값이나 자동 위험도 추정은 없습니다.
2. `ApprovalGrant.for_request()`는 승인 시점의 요청 전체를 안정된 JSON 문자열에 바인딩합니다.
3. `execute_authorized()`는 registry 검증 → 위험도 → 승인 일치 → 기존 registry 실행 순서를 강제합니다.
4. `ToolRegistry.validate_request()`는 실행하지 않는 검증 API입니다. 다른 보안 경계가 handler 전에 같은 allowlist와 Schema 계약을 재사용하도록 추가했습니다.

승인 ID는 감사 상관관계에 쓰는 식별자일 뿐, 이 예제에서 비밀 토큰이나 인증 수단이 아닙니다. 로그에 원문 인자가 민감할 수 있는 실제 시스템은 최소화된 요청 요약 또는 안전한 지문만 보관하고, 접근 제어와 보존 기한을 적용합니다.

## 5. 오류 해결

| 증상 | 원인 | 안전한 처리 |
|---|---|---|
| `human approval is required` | `HIGH` Tool에 승인 기록이 없습니다. | 자동 승인하거나 위험도를 낮추지 말고, 검증 가능한 사람 승인 워크플로로 보냅니다. |
| `approval grant does not match` | 승인 뒤 요청 ID, Tool 이름 또는 인자가 달라졌습니다. | 기존 승인을 재사용하지 말고, 변경된 요청 전체를 다시 검토·승인합니다. |
| `tool is not allowlisted` | 승인된 것으로 보이는 Tool도 registry에 없습니다. | Tool을 자동 등록하지 않습니다. 코드 검토를 거친 allowlist 변경을 별도 배포합니다. |
| `unexpected argument` | 요청이 승인된 Schema 범위를 벗어났습니다. | 인자를 조용히 제거하지 말고 요청을 다시 만들고 필요한 경우 다시 승인합니다. |
| `tool has no authorization policy` | allowlisted Tool에 위험도 선언이 없습니다. | 편의상 LOW 기본값을 두지 말고 소유자가 위험도를 명시합니다. |

## 6. 운영 적용 시 추가할 것

실제 위험 작업에는 Tool별 호출자 권한, 테넌트·리소스 범위, 승인자와 요청자의 분리, 승인 사유, 정책 버전, 만료, 단회 사용, 취소, 변경 불가능한 감사 로그가 필요합니다. 승인 시점과 실행 시점에 대상 리소스와 비용 한도를 다시 확인하고, timeout 뒤 상태가 불명확하면 자동 재시도하지 않습니다. 승인만으로 파일·셸·네트워크 접근을 허용하지 말고, 각각의 좁은 Tool 구현과 최소 권한 자격 증명을 별도로 적용합니다.

## 7. 완료 체크리스트

- [ ] 위험도 정책에 없는 Tool이 기본 허용되지 않음을 확인했다.
- [ ] `HIGH` Tool의 승인 누락·요청 ID 불일치·인자 불일치가 handler 전에 거부됨을 확인했다.
- [ ] 승인 기록이 allowlist와 JSON Schema를 우회하지 못함을 확인했다.
- [ ] 교육용 승인 객체가 실제 신원 증명이 아니라는 한계를 설명할 수 있다.
- [ ] 예제와 테스트를 네트워크·실제 부작용 없이 실행했다.
