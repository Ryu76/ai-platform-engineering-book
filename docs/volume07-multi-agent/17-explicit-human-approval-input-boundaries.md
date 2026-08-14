# 17. 명시적 사람 승인 입력 경계

## 1. 학습 목표

이 장에서는 Volume 07의 네 local workflow가 사람 승인을 단순 문자열이나 다른 workflow의 값으로 해석하지 않고, 각 workflow 전용 enum으로만 받는 이유를 학습합니다. 학습 뒤에는 `PENDING`, `APPROVED`, `REJECTED`가 Agent의 메시지나 Reviewer 판단과 다른 입력 경계이며, 잘못된 승인 입력은 첫 local Agent 호출 전에 멈춰야 함을 설명할 수 있습니다.

## 2. 왜 필요한가

`"approved"`라는 문자열, 다른 workflow에서 가져온 승인 enum, Agent가 작성한 message는 사람의 명시적 승인 기록이 아닙니다. 이를 느슨하게 변환하면 typo, 잘못 배선된 CLI 값, 또는 untrusted Agent 출력이 QA, Worker, DevOps 같은 gated local 단계를 열 수 있습니다.

따라서 이 volume은 검토/release용 `HumanApproval`, delegation용 `DelegationApproval`, conflict용 `ConflictApproval`을 분리합니다. 각 `run()` 메서드는 해당 enum의 정확한 instance만 허용하고, 그 외 입력은 `WorkflowConfigurationError`로 fail-closed합니다.

## 3. 핵심 개념

- **workflow-scoped approval:** `HumanApproval`은 review와 release handoff의 human gate에만, `DelegationApproval`은 Worker dispatch에만, `ConflictApproval`은 exact consensus completion에만 사용합니다.
- **명시적 입력:** raw string `"approved"`와 Agent response text는 approval 값이 아닙니다. CLI flag도 예제 경계에서 해당 enum으로 변환될 때만 의미가 있습니다.
- **PENDING:** 검토된 local audit 또는 manifest/recommendation을 반환하지만 gated 다음 role을 호출하지 않는 safe pause입니다. 상태는 `awaiting_human_approval`입니다.
- **APPROVED:** 이미 올바르게 구성되고 bounded loop를 통과한 workflow의 다음 local 단계만 허용합니다. tool, network, file, deployment capability를 전달하지 않습니다.
- **REJECTED:** 첫 Agent 호출보다 먼저 종료하는 fail-closed 값입니다.
- **입력 실패:** foreign enum 또는 잘못된 type은 audit trail을 만들거나 deterministic Mock script를 소비하지 않고 `WorkflowConfigurationError`로 끝납니다.

## 4. 동작 구조

```text
human/CLI boundary
       |
       v
workflow-specific enum인가?
  | 아니오                  | 예
  v                         v
WorkflowConfigurationError  PENDING / APPROVED / REJECTED policy
Agent 호출 0회              |        |            |
                            pause    gated local  pre-call stop
                                     next step

Agent message "approved" ──X──> approval capability
foreign approval enum    ──X──> another workflow gate
```

`APPROVED`도 가능한 역할 호출 수를 늘리지 않습니다. review/release의 `max_review_cycles`, delegation의 `max_tasks`와 `max_worker_attempts`, conflict의 `max_agents`와 `max_rounds`는 독립된 bounded loop 상한입니다.

## 5. 실습 환경

- Python 3.12 이상과 프로젝트의 `uv` 환경을 사용합니다.
- 저장소 루트 `E:\python\ai-platform-engineering-book-volume-07`의 bash 또는 WSL 터미널에서 실행합니다.
- local deterministic Mock만 사용합니다. live API, network Agent, secret, tool 실행, 파일 변경, deployment가 필요하거나 실행되지 않습니다.

## 6. 단계별 실습

먼저 잘못된 승인 input이 모든 workflow에서 첫 Agent 호출 전에 차단되는 contract를 실행합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07/test_explicit_human_approval_input_boundaries.py -q
```

이 test는 아래 입력을 local deterministic Mock에 전달합니다.

1. review workflow에는 raw string `"approved"`를 전달합니다.
2. delegation workflow에는 `HumanApproval.APPROVED`를 전달합니다.
3. conflict workflow에는 `DelegationApproval.APPROVED`를 전달합니다.
4. release workflow에는 `ConflictApproval.APPROVED`를 전달합니다.

네 경우 모두 `WorkflowConfigurationError`가 발생하고 Planner, Coordinator, Worker, conflict peer, QA, DevOps의 call history는 비어 있어야 합니다. 문서 contract도 함께 검증합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07/test_explicit_human_approval_input_boundaries_documentation.py -q
```

마지막으로 전체 Volume 07 offline regression을 실행합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07 -q
```

## 7. 코드 설명

각 workflow는 task/objective 유효성 다음에 approval type을 확인하고, 정책 분기보다 먼저 안전하게 종료합니다. review와 release handoff의 핵심 형태는 다음과 같습니다.

```python
if not isinstance(human_approval, HumanApproval):
    raise WorkflowConfigurationError("human_approval must be a HumanApproval value")
if human_approval is HumanApproval.REJECTED:
    return rejected_result_before_any_agent_call()
```

Delegation과 conflict workflow도 같은 위치에서 각각 `DelegationApproval`과 `ConflictApproval`을 요구합니다. 이 검사는 enum의 `.value` 문자열이 같아 보여도 다른 enum instance를 자동 변환하지 않습니다. 이후의 `PENDING`/`APPROVED` 분기는 valid input에만 도달하며 deterministic Mock의 fixed script와 bounded loop 정책은 변경하지 않습니다.

## 8. 정상 실행 결과

focused contract와 documentation contract는 각각 exit code `0`으로 끝납니다. 정상 예제의 기본 실행은 여전히 명시 승인 전 pause합니다.

```bash
uv run python examples/volume07/offline_multi_agent_mini_project.py
```

출력에는 다음 상태가 포함됩니다.

```text
review_status=awaiting_human_approval
delegation_status=awaiting_human_approval
conflict_status=awaiting_human_approval
release_status=awaiting_human_approval
```

각 `--approve-*` flag는 예제 안에서 대응하는 전용 enum으로 변환되어 그 stage만 local `completed`로 만듭니다. 이는 local audit 또는 handoff note 결과이지 live API 호출, secret 사용, tool 실행, deployment가 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `human_approval must be a HumanApproval value` | review/release에 문자열이나 다른 enum을 전달함 | `HumanApproval.PENDING`, `HumanApproval.APPROVED`, `HumanApproval.REJECTED` 중 하나를 명시합니다. |
| `human_approval must be a DelegationApproval value` | Worker gate에 review/release enum을 전달함 | delegation 호출에는 `DelegationApproval`만 전달합니다. |
| `human_approval must be a ConflictApproval value` | consensus gate에 다른 workflow enum을 전달함 | conflict 호출에는 `ConflictApproval`만 전달합니다. |
| 기대와 달리 `awaiting_human_approval` | valid `PENDING` 값은 정상적인 safe pause임 | audit trail을 사람 검토한 후 workflow-specific `APPROVED` 값을 새 실행에 명시합니다. |
| `completed`가 안 됨 | Reviewer revision 또는 conflict/worker loop bound가 남아 있음 | approval type을 우회 수단으로 쓰지 말고 bounded loop 결과와 audit을 검토합니다. |

## 10. 응용 실습

1. `object()`와 `True`를 각 workflow의 approval input으로 전달해 같은 pre-call configuration failure인지 확인합니다.
2. 작은 CLI adapter를 만들고 `--approve` 문자열을 workflow 바깥에서 전용 enum으로 변환한 뒤, 알 수 없는 flag value는 변환 전에 거절합니다.
3. `PENDING` audit을 사람이 별도로 검토했다고 가정하는 test fixture를 만들되, Agent message content로 `APPROVED` enum을 생성하지 않음을 검증합니다.

## 11. 실무 적용

실제 시스템에서는 typed enum만으로 사람 신원을 증명하지 않습니다. 승인자는 인증된 identity, 변경 대상, 시간, 사유, 승인 정책 버전이 포함된 별도 immutable approval record를 남겨야 합니다. workflow는 그 record를 검증하는 adapter 뒤에서 제한된 다음 단계를 열어야 하며, Agent output 또는 prompt가 approval authority가 되어서는 안 됩니다.

이 Volume 07 implementation은 그 운영 adapter를 구현하지 않습니다. deterministic Mock과 explicit human approval input은 학습용 local boundary입니다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않습니다.

## 12. 과제

- **기본:** review workflow에 `"APPROVED"`와 `"approved"`를 각각 전달하는 pre-call failure test를 작성합니다.
- **응용:** 모든 mini-project approval flag가 다른 stage의 status를 `awaiting_human_approval`로 유지하는지 subprocess test로 확인합니다.
- **심화:** immutable external approval record의 schema를 설계하되, record의 검증과 tool/deployment authorization을 별도 policy boundary로 분리합니다.

## 13. 완료 체크리스트

- [ ] `HumanApproval`, `DelegationApproval`, `ConflictApproval`의 적용 범위를 구분할 수 있다.
- [ ] raw string과 foreign enum이 Agent 호출 전에 `WorkflowConfigurationError`가 되는 것을 확인했다.
- [ ] `PENDING`, `APPROVED`, `REJECTED`가 deterministic Mock script와 bounded loop 상한을 바꾸지 않음을 설명할 수 있다.
- [ ] approval 값이 identity, secret, tool capability, deployment 권한을 뜻하지 않음을 설명할 수 있다.
- [ ] focused 및 전체 Volume 07 offline regression을 통과시켰다.

## 14. 핵심 정리

명시적 사람 승인은 message text나 범용 문자열이 아니라 workflow-specific typed input이어야 합니다. Volume 07의 네 workflow는 잘못된 approval type을 pre-call `WorkflowConfigurationError`로 거절하고, valid `PENDING`/`APPROVED`/`REJECTED`만 bounded local policy에 전달합니다. 이 분리는 deterministic Mock, immutable audit snapshot, finite loop, local-only safety 경계를 유지합니다.
