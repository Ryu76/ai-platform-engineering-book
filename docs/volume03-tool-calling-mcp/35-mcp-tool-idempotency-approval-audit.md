# MCP Tool idempotency·approval·audit: durable store 전에 exact binding을 좁게 모델링하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- allowlisted Tool의 `idempotency_key`를 request ID·Tool name·canonical JSON argument digest에 정확히 묶는다.
- expiry가 있는 typed approval을 한 번만 소비하고, 만료·replay를 Tool 실행 전에 막는다.
- pre-execution audit append 실패에서는 key/approval을 소비하지 않고 실행을 막는다.
- Tool 결과 또는 completion audit가 모호하면 blind retry 대신 caller-owned reconciliation signal을 남긴다.

## 2. execution과 durable ownership을 섞지 않기

`InMemoryMcpToolExecutionLedger`는 Tool handler, registry, clock API, database를 직접 호출하지 않습니다. Caller가 이미 allowlisted·schema 검증한 request로 `McpToolExecutionBinding`을 만들고, trusted approval workflow가 만든 `McpTimedToolApproval` 및 injected `now` 값으로 reserve합니다.

```text
validated allowlisted request ──> immutable digest binding ──> one-time approval reserve
                                                              │
                                      pre-execution audit <───┤── failure: no Tool execution
                                                              │
caller-owned Tool execution <── claim ──> result resolution ─┴── ambiguous/audit failure:
                                                                     reconciliation required
```

Binding은 raw JSON arguments 대신 canonical finite JSON의 SHA-256 digest만 보관합니다. 같은 idempotency key가 같은 binding으로 다시 들어오면 duplicate, 다른 binding으로 들어오면 conflict로 실행 전에 멈춥니다. `approval_id`도 ledger lifetime 안에서 한 번만 사용됩니다.

## 3. 좁은 API 계약

- `McpToolExecutionBinding.for_request(...)`는 non-empty one-line key/request/tool ID와 finite JSON object를 immutable binding으로 바꾼다.
- `McpTimedToolApproval(approval_id, binding, expires_at)`은 request binding을 바꾸지 못하는 typed grant다. `now >= expires_at`이면 reserve 전에 거부한다.
- `reserve(approval, now=...)`는 duplicate/collision/expiry/replay를 검사한 다음 `AUTHORIZED` audit event를 먼저 append한다. append가 실패하면 key와 approval은 소비하지 않고 caller가 Tool을 실행해서는 안 된다.
- `resolve(claim, outcome=SUCCEEDED)`는 completion audit이 성공해야 `COMPLETED`가 된다. completion audit failure는 result가 이미 발생했을 수 있으므로 `reconciliation_required=True` error와 latch state를 반환한다.
- `resolve(claim, outcome=AMBIGUOUS)`는 raw Tool result, exception detail, blind retry 없이 `RECONCILIATION_REQUIRED` state를 반환한다. 같은 key의 새 reservation은 계속 거부된다.

이 fixture는 concurrent lock, durable transaction, real monotonic/wall clock, approval issuance, Tool invocation, retry, external audit store, network, process, shell 또는 destructive action을 수행하지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_tool_idempotency_approval_audit.py
uv run pytest tests/volume03/test_tool_idempotency.py -q
```

예상 출력입니다.

```text
idempotency_key: idem-demo-001
audit_phases: authorized,succeeded
state: completed
reconciliation_required: False
```

예제는 `safe_calculator`라는 allowlisted pure-Tool **intent**와 fixed in-memory approval/audit/ledger만 만듭니다. handler를 실행하지 않으며 actual database, filesystem, process, shell, network, MCP server, approval service, Tool 또는 destructive action을 수행하지 않습니다.

## 5. 검증 경계

`tests/volume03/test_tool_idempotency.py`는 fake memory seam으로 다음을 검증합니다.

1. raw secret-like argument 없이 exact digest binding의 authorization audit을 append한다.
2. duplicate idempotency key와 다른 request binding의 key conflict가 execution 전에 멈춘다.
3. expired approval 및 replayed approval ID가 audit/reservation 전에 거부된다.
4. pre-execution audit append failure는 private adapter detail을 숨기고 key/approval을 소비하지 않는다.
5. confirmed success는 authorization/completion audit을 남기고 key를 `COMPLETED`로 닫는다.
6. ambiguous result와 completion audit failure는 key를 `RECONCILIATION_REQUIRED`로 latch하고 caller-owned signal을 반환한다.
7. forged/stale claim, invalid injected time이 completion/audit 전에 거부된다.

## 6. production에 그대로 연결하지 않기

이 in-memory class는 exactly-once execution 또는 durable audit을 제공하지 않습니다. Production에서는 tenant-scoped durable idempotency table의 atomic compare-and-set, approval issuer identity/signature/revocation, transaction/outbox 또는 write-ahead audit, reliable clock/time source, lease recovery, concurrent worker fencing, result receipt, retry/reconciliation queue, retention/privacy policy, quota와 operator tooling을 설계해야 합니다.

MCP disconnect, child restart, timeout 또는 client retry 뒤에도 destructive Tool을 자동 재호출하지 마세요. Receiver acknowledgement와 durable side-effect identity를 확인할 수 없으면 result를 `AMBIGUOUS`로 보수적으로 처리하고 별도 reconciliation workflow로 넘겨야 합니다.

## 7. 완료 체크리스트

- [ ] idempotency key가 Tool name·request ID·canonical argument digest와 exact binding인지 확인했다.
- [ ] approval expiry 및 one-time replay rejection이 handler 전인지 확인했다.
- [ ] pre-execution audit failure가 Tool 실행과 key/approval 소비를 막는지 확인했다.
- [ ] completion audit failure와 ambiguous result가 blind retry 대신 reconciliation signal을 내는지 확인했다.
- [ ] example/test가 actual Tool, database, process, network, destructive action 없이 실행됐는지 확인했다.
- [ ] durable transaction/outbox, issuer verification, concurrent lease/recovery가 별도 production 작업임을 확인했다.
