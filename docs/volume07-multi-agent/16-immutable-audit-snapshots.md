# 16. 불변 Audit Snapshot과 역할 간 Message Passing

## 1. 학습 목표

이 장을 마치면 각 deterministic Mock Agent가 받는 context가 호출 순간의 불변 audit snapshot임을 설명하고 검증할 수 있습니다.

- 다음 역할은 이전 역할의 검증된 message만 읽는다.
- 이후에 추가된 message, approval 값, mutable script는 과거 context에 섞이지 않는다.
- `PENDING`, `APPROVED`, `REJECTED`는 message text가 아닌 별도 explicit human approval 입력이다.
- review cycle, worker attempt, conflict round는 configured positive bound 안에서만 증가한다.

> [!WARNING]
> Volume 07 audit snapshot은 local deterministic workflow의 학습용 기록입니다. live API, network Agent, secret, tool 실행, 파일 변경, deployment 또는 운영 승인 기록이 아닙니다.

## 2. 왜 불변 snapshot이 필요한가

여러 역할이 하나의 mutable message list를 공유하면, 나중에 실행된 역할의 결과가 이전 역할의 판단 근거처럼 보일 수 있습니다. 그러면 재현 가능한 검토와 사람 승인이 불가능해집니다.

따라서 workflow는 Agent를 호출할 때마다 현재까지의 `tuple` message만 담은 새 context를 전달합니다. `AgentMessage`, `DelegationMessage`, `ConflictMessage`도 frozen dataclass이므로 기록된 role, content, counter를 뒤에서 바꾸지 못합니다.

## 3. 핵심 개념

| 개념 | Volume 07 계약 |
|---|---|
| audit snapshot | 호출 시점까지 검증되어 누적된 immutable message tuple |
| message passing | 이전 role의 data를 다음 role context에 전달하는 일이며 tool capability 전달이 아님 |
| deterministic Mock | 고정 immutable tuple script를 순서대로 소비하는 local test double |
| bounded loop | review cycle, worker attempt, conflict round의 positive integer 상한 |
| explicit human approval | `PENDING`/`APPROVED`/`REJECTED` enum 입력. message content로 추론하지 않음 |

`HumanApproval.APPROVED`와 대응 workflow의 approval enum은 해당 workflow의 다음 **local** stage만 엽니다. `DeterministicMock*` fixture는 그 경계를 재현할 뿐이며, 과거 snapshot을 바꾸거나 다른 workflow의 gate, live API, secret, tool 실행, deployment 권한을 열지 않습니다.

## 4. 동작 구조

```text
Planner message
      |
      v
[Researcher context: (Planner,)]
      |
      v
[Developer context: (Planner, Researcher)]
      |
      v
[Reviewer context: (Planner, Researcher, Developer)]
      |
      +--> PENDING  -> awaiting_human_approval
      +--> REJECTED -> human_rejected before any Agent call
      +--> APPROVED -> [QA context: (..., Reviewer)]

Each arrow creates a new immutable tuple snapshot.
No earlier context receives later QA, Worker, policy, or DevOps messages.
```

Delegation에서는 Coordinator snapshot 뒤에 승인된 Worker attempt가, conflict에서는 먼저 실행된 peer proposal 뒤에 다음 peer가, release handoff에서는 QA message 뒤에 DevOps Mock이 같은 규칙으로 새 snapshot을 받습니다.

## 5. 실습 환경과 실행 위치

저장소 루트의 Git Bash 또는 WSL Bash에서 실행합니다. 이 명령은 local Python test만 실행하고 network, live API, secret, tool executor, deployment를 사용하지 않습니다.

```bash
# 실행 위치: 저장소 루트
cd /e/python/ai-platform-engineering-book-volume-07
uv run pytest tests/volume07/test_immutable_audit_snapshots.py -q
```

전체 Volume 07 회귀 검증은 다음과 같습니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07 -q
```

## 6. 단계별 실습

1. focused test를 실행합니다. review, delegation, conflict, release 네 workflow의 approved local 경로를 검사합니다.
2. review test에서 Researcher context가 Planner message 하나만 갖고, QA context가 Reviewer까지의 message를 갖는지 확인합니다.
3. delegation test에서 Coordinator context는 비어 있고, 첫 Worker는 manifest message만, 다음 Worker는 완료된 앞 Worker message까지 받는지 확인합니다.
4. conflict test에서 Reviewer peer가 Planner proposal은 읽되 consensus policy message는 읽지 않는지 확인합니다.
5. release test에서 DevOps Mock이 QA까지의 snapshot만 읽는지 확인합니다.
6. `PENDING` 기본 실행과 `REJECTED` pre-call 종료는 기존 workflow contract test로도 재확인합니다. `APPROVED`는 human gate를 자동 생성하지 않는 명시적 local test input입니다.

## 7. 코드 설명

`src/ai_platform/agents/workflow.py`의 `_call()`은 `tuple(messages)`로 `AgentContext`를 생성합니다. `BoundedReviewWorkflow`와 `ApprovalGatedReleaseHandoffWorkflow`는 output을 schema와 role authority로 검증한 뒤에만 `AgentMessage`를 append합니다.

`delegation.py`는 `DelegationContext(objective, tuple(messages), task, attempt)`를 Worker에 전달합니다. `conflict.py`도 `ConflictContext(objective, round_number, tuple(messages))`를 peer마다 새로 만듭니다. 이 때문에 다음 역할은 앞선 validated data는 읽지만, 자신의 output이나 미래의 policy message를 미리 읽지 못합니다.

새 `test_immutable_audit_snapshots.py`는 네 deterministic Mock workflow의 call history를 검사합니다. result의 최종 tuple이 더 길어져도 earlier context tuple의 길이와 role 순서가 변하지 않는지를 고정합니다.

## 8. 정상 실행 결과

focused test의 정상 결과는 다음과 같습니다.

```text
4 passed
```

성공은 네 workflow에서 local audit snapshot 순서가 고정되었다는 뜻입니다. 이는 live API 호출, tool 실행, deployment 또는 운영 action이 발생했다는 뜻이 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| early context에 나중 role이 보임 | shared mutable list를 직접 전달했을 가능성 | workflow boundary에서 `tuple(messages)`를 새로 만들고 focused test를 실행합니다. |
| `AgentProtocolError` | Agent output schema 또는 Reviewer review authority가 맞지 않음 | 다음 role을 호출하지 말고 response type, non-empty content, `ReviewDecision`을 확인합니다. |
| `awaiting_human_approval` | 기본 `PENDING`이 정상적으로 safe pause함 | 학습용 completed path만 명시적인 `APPROVED` input으로 확인합니다. |
| Worker/QA/DevOps가 예상보다 일찍 호출됨 | human gate보다 앞서 dispatch를 구현함 | approval branch와 call history를 검사합니다. `PENDING`에서는 gated role을 호출하지 않아야 합니다. |
| script 소진 | configured bounded loop보다 fixed tuple script가 짧음 | fallback을 추가하지 말고 fixture와 positive call budget을 맞춥니다. |

## 10. 응용 실습

1. review workflow에 `REVISE` 한 번과 `APPROVE` 한 번을 넣고, 두 번째 Developer context가 첫 Reviewer message까지만 받는지 test로 작성합니다.
2. delegation Worker를 한 번 실패시킨 뒤 재시도하고, second attempt snapshot에 first attempt message가 있는지 확인합니다.
3. conflict peer의 option을 다르게 구성해 `conflict_limit_reached`가 snapshot을 보존하면서 winner를 추측하지 않는지 확인합니다.
4. snapshot을 Router에 전달하는 schema를 설계합니다. status와 immutable audit data만 포함하고 approval, secret, tool object, mutable script는 포함하지 마십시오.

## 11. 실무 적용

운영 환경에서는 이 local model에 별도 persistence, retention, redaction, access control을 추가해야 합니다. audit record writer는 approval authority와 분리하고, viewer는 immutable event data만 읽도록 설계합니다.

> [!TIP]
> message text에 `approved`라는 문자열이 있어도 사람 승인이 아닙니다. 인증된 approver identity, scope, timestamp, expiry를 검증하는 별도 approval record가 필요합니다.

Router는 immutable status/audit snapshot을 기준으로 eligible workflow를 선택할 수 있습니다. 하지만 Router가 `APPROVED`를 만들거나, secret, tool handle, mutable Mock script, deployment capability를 전달해서는 안 됩니다.

## 12. 과제

### 기본

- review와 release workflow에서 QA가 받는 마지막 message role을 각각 적습니다.
- `PENDING`과 `REJECTED`가 snapshot 및 Agent call에 미치는 차이를 설명합니다.

### 응용

- 네 workflow의 context type, counter, 다음 role을 표로 정리합니다.
- 이전 context tuple이 이후 result message에 의해 변경되지 않음을 검증하는 test를 하나 추가합니다.

### 심화

- append-only external audit store의 event schema를 설계합니다. secret redaction, retention, reader permission, approval record 분리를 포함합니다.
- Router handoff schema에 immutable audit snapshot의 digest를 추가하는 방법을 설계하되, approval이나 capability를 직렬화하지 마십시오.

## 13. 완료 체크리스트

- [ ] `test_immutable_audit_snapshots.py`가 네 local workflow의 context 순서를 통과했다.
- [ ] early context가 이후 role, policy, QA, DevOps message를 포함하지 않음을 설명할 수 있다.
- [ ] deterministic Mock script와 audit snapshot이 모두 immutable tuple 계약을 사용함을 확인했다.
- [ ] review cycle, Worker attempt, conflict round의 bounded loop를 구분할 수 있다.
- [ ] `PENDING`, `APPROVED`, `REJECTED`가 explicit human approval input임을 설명할 수 있다.
- [ ] `completed`가 local-only result이며 live API, secret, tool 실행, deployment가 아님을 확인했다.

## 14. 핵심 정리

Volume 07의 message passing은 mutable shared state가 아니라 호출 시점의 immutable audit snapshot을 전달합니다. deterministic Mock, bounded loop, schema validation, Reviewer-only review authority, explicit human approval은 서로 대체할 수 없는 별도 안전 계약입니다. 이 계약은 다음 Router Volume이 status와 data를 읽을 수 있게 하지만 approval과 capability를 부여하지는 않습니다.
