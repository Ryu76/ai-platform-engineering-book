# FastAPI 요청·응답 어댑터와 승인 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- HTTP 요청·응답 스키마와 Workflow 도메인 상태를 분리한다.
- FastAPI route가 사용할 수 있는 검증된 시작·승인 어댑터를 구성한다.
- 위험 ActionKind의 시작 요청이 `WAITING_FOR_APPROVAL` 응답에서 멈춤을 확인한다.
- 별도의 명시적 승인 요청만 `execute` 시뮬레이션에 도달하게 검증한다.

## 2. 왜 필요한가

웹 API는 신뢰하지 않는 JSON을 Workflow 입력으로 바꾸는 경계입니다. 요청 검증이 느슨하면 예상하지 않은 필드, 빈 run ID, 문자열로 표현된 승인 값이 상태 전이에 들어갈 수 있습니다. 더 위험한 오류는 “배포 요청을 받았다”는 사실을 “사람이 실행을 승인했다”는 사실로 취급하는 것입니다.

이 장의 `WorkflowApiAdapter`는 FastAPI handler가 호출할 수 있는 Pydantic 요청·응답 계약입니다. 서버·네트워크·실제 부작용을 만들지 않고도, `POST /workflows`에 해당하는 시작과 `POST /workflows/{run_id}/approval`에 해당하는 명시적 결정을 분리합니다.

## 3. 핵심 개념

- **Request model**: 외부 JSON의 타입, 길이, 허용 필드를 검증하는 Pydantic 모델입니다.
- **Response model**: 도메인 `WorkflowState`를 HTTP JSON에 안전하게 투영하는 읽기 전용 스냅샷입니다.
- **Adapter**: route 함수와 `DeterministicWorkflow` 사이의 프레임워크 독립 경계입니다.
- **명시적 승인**: 위험 작업을 재개하는 별도 `ApprovalRequest(approved=True)`입니다.
- **엄격한 Boolean**: `StrictBool`은 문자열 `"true"`나 숫자 `1`을 승인으로 변환하지 않습니다.

> [!WARNING]
> 이 장은 FastAPI 서버를 실행하거나 HTTP 요청을 보내지 않습니다. `delete`, `deploy`, `send`은 언제나 오프라인 상태 전이입니다. `approved=True`는 학습용 Boolean일 뿐 운영 승인자가 아니며, 실제 실행 권한을 의미하지 않습니다.

## 4. 동작 구조

```text
POST /workflows
  StartWorkflowRequest
       │ 검증
       ▼
WorkflowApiAdapter.start()
       │
       ▼
DeterministicWorkflow
  plan → approval (WAITING_FOR_APPROVAL)     # risky DEPLOY
       │
       └── POST /workflows/{run_id}/approval
              ApprovalRequest(approved=True)
                        │
                        ▼
                 approval (READY) → execute (COMPLETED)

승인 거절 또는 잘못된 승인 본문 → execute 없음
```

`WorkflowApiAdapter`는 시작 요청의 `run_id`, `task`, `action`을 검증한 뒤 Workflow에 전달합니다. 위험 ActionKind의 첫 응답은 `waiting_for_approval`이고 이벤트는 `plan | approval`에서 끝납니다. 별도 재개 요청이 승인되었을 때만 두 번째 `approval` 뒤에 `execute`가 나타납니다.

## 5. 실습 환경

다음 파일을 사용합니다.

- `src/ai_platform/graph/api.py`
- `src/ai_platform/graph/workflow.py`
- `examples/volume09/fastapi_adapter_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

현재 프로젝트는 `fastapi` 패키지를 선언하지 않았으므로 이 슬라이스는 서버를 가장하지 않습니다. `api.py`의 Pydantic 계약은 별도로 승인된 의존성 변경 뒤 FastAPI route가 호출할 어댑터입니다.

## 6. 단계별 실습

### 6.1 검증된 시작 요청 만들기

```python
from ai_platform.graph import ActionKind, StartWorkflowRequest, WorkflowApiAdapter

adapter = WorkflowApiAdapter()
waiting = adapter.start(
    request=StartWorkflowRequest.model_validate(
        {
            "run_id": "api-demo-001",
            "task": "학습용 배포를 준비한다",
            "action": ActionKind.DEPLOY,
        }
    )
)
assert waiting.status.value == "waiting_for_approval"
assert [event.node for event in waiting.events] == ["plan", "approval"]
```

### 6.2 별도의 사람 승인으로만 재개

```python
from ai_platform.graph import ApprovalRequest

completed = adapter.resume(
    run_id="api-demo-001",
    request=ApprovalRequest(approved=True),
)
assert completed.status.value == "completed"
assert [event.node for event in completed.events] == [
    "plan", "approval", "approval", "execute"
]
```

### 6.3 오프라인 예제와 계약 검사 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run python examples/volume09/fastapi_adapter_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

시작 모델은 예상하지 않은 JSON 필드를 거부하고 텍스트를 정규화합니다.

```python
class StartWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    run_id: str = Field(min_length=1, max_length=128)
    task: str = Field(min_length=1, max_length=1_000)
    action: ActionKind
```

승인 모델은 문자열의 자동 Boolean 변환을 거부합니다.

```python
class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: StrictBool
```

어댑터는 위험 작업의 Workflow 정책을 우회하지 않습니다.

```python
state = self._workflow.resume(run_id=normalized_run_id, approved=request.approved)
return WorkflowResponse.from_state(run_id=normalized_run_id, state=state)
```

FastAPI를 도입한 뒤 route는 이 어댑터에 검증된 모델을 전달하고, 인증·인가·CSRF 보호·승인자 역할·정확한 대상·영향 범위·정책 버전·만료를 운영 정책으로 추가해야 합니다. route가 `execute_node()`를 직접 호출해서는 안 됩니다.

## 8. 정상 실행 결과

```text
시작 응답: status=waiting_for_approval
events=plan | approval
명시적 승인 응답: status=completed
events=plan | approval | approval | execute
```

첫 응답에 `execute`가 없는 것이 안전 계약입니다. 두 번째 응답은 명시적 승인 입력을 기록한 뒤에도 실제 배포가 아닌 결정론적 문자열 결과만 반환합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `extra_forbidden` 검증 오류 | 요청 본문에 계약 밖 필드가 있습니다. | 문서화한 `run_id`, `task`, `action` 또는 `approved`만 보냅니다. |
| Boolean 검증 오류 | `"true"` 같은 문자열을 승인 본문에 넣었습니다. | JSON Boolean `true` 또는 `false`를 사용하고 운영에서는 인증된 승인자 정책을 추가합니다. |
| `checkpoint not found` | 시작하지 않은 run ID를 승인하려 했습니다. | 먼저 같은 run ID의 시작 요청으로 `waiting_for_approval` 상태를 만듭니다. |
| `waiting state` 오류 | 완료·거절·안전 작업을 재개하려 했습니다. | 응답 status가 `waiting_for_approval`인 위험 작업만 한 번 재개합니다. |
| 실제 FastAPI 앱이 없음 | 의존성 추가가 현재 작업 범위 밖입니다. | 승인된 프로젝트 설정 변경 뒤 route에서 이 어댑터를 호출합니다. |

## 10. 응용 실습

1. 안전 `READ` 시작 요청이 `plan → approval → execute`로 즉시 완료하는 응답 계약을 작성합니다.
2. `JsonFileCheckpointer`를 주입해 새 어댑터 인스턴스도 `waiting_for_approval`을 유지하는 테스트를 작성합니다.
3. 운영용 route에 승인자 ID, 정책 버전, 만료 시간과 idempotency key를 별도 서버 계층에서 검증하는 설계를 작성합니다. 외부 서버는 실행하지 않습니다.

## 11. 실무 적용

실제 FastAPI route는 request ID와 인증된 주체를 관측 로그에 연결하되 토큰, 비밀번호, 개인정보와 원문 민감 입력을 응답·State·감사 이벤트에 기록하지 않아야 합니다. 승인 엔드포인트는 역할 기반 인가, 대상과 영향 범위 재확인, 정책 버전, 만료, 재전송 보호를 적용해야 합니다.

`WorkflowResponse`는 실행 상태를 전달하는 DTO이지 권한 증명이 아닙니다. HTTP 2xx 응답, Reviewer 통과, 큐 등록은 위험 실행 승인과 동의어가 아닙니다. 실제 side effect는 독립된 정책 시행 지점과 감사 가능한 실행기에만 위임해야 합니다.

## 12. 과제

- **기본:** 시작 요청과 승인 요청이 다른 입력 모델인 이유를 설명합니다.
- **응용:** `"true"` 승인 문자열과 추가 JSON 필드를 거부하는 테스트를 작성합니다.
- **심화:** 다중 승인과 만료를 지원하는 서버 계층의 상태·권한·감사 계약을 설계하되, 실제 HTTP 서버나 위험 작업을 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] `StartWorkflowRequest`가 빈 ID·작업과 예상하지 않은 필드를 거부함을 확인했다.
- [ ] `ApprovalRequest`가 엄격한 JSON Boolean을 요구함을 확인했다.
- [ ] 위험 시작 응답이 `waiting_for_approval`에서 멈춤을 확인했다.
- [ ] 첫 응답의 이벤트에 `execute`가 없음을 확인했다.
- [ ] 별도의 `approved=True` 재개 뒤에만 `execute`가 나타남을 확인했다.
- [ ] 거절 요청이 `execute` 없이 종료함을 확인했다.
- [ ] 예제와 테스트가 FastAPI 서버, 네트워크, 실제 위험 작업 없이 동작함을 확인했다.

## 14. 핵심 정리

FastAPI 연동의 첫 단계는 서버를 먼저 켜는 일이 아니라, 신뢰하지 않는 HTTP 입력과 Workflow 정책 사이에 엄격한 계약을 두는 일입니다. `WorkflowApiAdapter`는 시작과 승인을 분리하고, 위험 작업을 별도 명시적 승인 전까지 `WAITING_FOR_APPROVAL` interrupt에 유지합니다. 현재 구현은 오프라인·결정론적 어댑터이며 실제 FastAPI route와 실행기는 승인된 별도 의존성·보안 작업에서 연결해야 합니다.
