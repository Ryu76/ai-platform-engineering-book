# 15. Volume 07 학습 체크리스트, 용어집과 Router 인계

## 1. 학습 목표

이 장은 Volume 07의 실습을 처음부터 다시 실행해 Multi-Agent 설계의 핵심 계약을 확인하고, 다음 권인 Router 설계에 넘길 수 있는 결과를 정리합니다. 이 장을 마치면 다음을 할 수 있어야 합니다.

- 역할, 입력·출력 schema, authority, capability를 분리해 설명할 수 있다.
- deterministic Mock과 immutable script로 재현 가능한 role fixture를 구성할 수 있다.
- review cycle, worker attempt, conflict round의 유한 호출 예산을 확인할 수 있다.
- `PENDING`, `APPROVED`, `REJECTED` 사람이 승인하는 범위와 실행하지 않는 역할을 구분할 수 있다.
- 다음 Volume의 Router가 선택할 수 있는 안전한 workflow entry point와 상태를 정리할 수 있다.

> [!WARNING]
> 이 권의 `completed`는 local deterministic workflow가 끝났다는 뜻입니다. 외부 API 호출, network agent, tool 실행, 파일 변경, 배포, release 승인을 뜻하지 않습니다. 실습에 API key나 다른 secret을 추가하지 마십시오.

## 2. 왜 권 단위 점검이 필요한가

장별 예제가 통과하더라도 workflow를 연결할 때 role 권한이나 사람 승인 경계가 흐려질 수 있습니다. 예를 들어 Router가 `APPROVED` 값을 자동으로 만들거나, `awaiting_human_approval` workflow를 다시 실행하면서 다른 Mock script를 사용하면 처음 검토한 audit와 실행이 일치하지 않을 수 있습니다.

따라서 권 단위 점검에서는 다음 세 가지를 분리합니다.

1. **학습 완료:** 학습자가 각 local workflow의 계약을 재현할 수 있는가
2. **workflow 완료:** 하나의 in-memory deterministic run이 정해진 상태에 도달했는가
3. **운영 승인:** 인증된 사람이 대상, 범위, 시각, 만료를 기록하고 외부 변경을 허용했는가

Volume 07은 첫 두 항목만 local Mock으로 다룹니다. 세 번째 항목은 다음 단계에서 설계해야 하는 별도 운영 통제이며, enum 하나나 Agent message로 대체할 수 없습니다.

## 3. 전체 구조와 다음 권 인계

```text
                  local request
                        |
                        v
       +------------------------------------+
       | Volume 07 deterministic workflows  |
       | review / delegation / conflict /    |
       | local release handoff               |
       +------------------------------------+
          |             |              |
          |             |              +--> completed
          |             |                     (local result only)
          |             +--> bounded failure
          |                   (limit reached / protocol error)
          +--> awaiting_human_approval
                        |
                        v
           explicit human decision boundary
                        |
                        v
       Volume 08 Router policy (future, separate scope)
       selects an eligible workflow; it must not invent approval
```

Router는 장차 요청을 적절한 workflow로 보낼 수 있습니다. 하지만 다음 값은 Router의 추론이나 keyword match로 생성하면 안 됩니다.

- `HumanApproval.APPROVED`
- `DelegationApproval.APPROVED`
- `ConflictApproval.APPROVED`
- 실제 tool, deployment, data-access 권한

Router로 넘길 수 있는 것은 구조화된 local request, workflow 종류, bounded status, audit snapshot입니다. Router가 넘겨받아서는 안 되는 것은 secret, unrestricted tool handle, mutable Mock script, 사람 승인자를 가장한 text입니다.

## 4. 실습 환경과 실행 위치

이 장은 저장소 루트에서 실행합니다. Windows에서는 Git Bash 또는 WSL Bash를 사용합니다. 아래 명령은 Python package를 `uv`를 통해 실행하며 network, live API, secret, tool executor, deployment를 사용하지 않습니다.

```bash
# 실행 위치: 저장소 루트
cd /e/python/ai-platform-engineering-book-volume-07
uv run python examples/volume07/offline_multi_agent_mini_project.py
```

이 명령은 네 workflow를 모두 만들지만 승인 flag를 전달하지 않습니다. 따라서 QA, Worker, DevOps는 실행되지 않고 모두 안전한 pause 상태를 출력해야 합니다.

승인 경계를 학습용 local input으로 각각 확인하려면 네 flag를 명시합니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume07/offline_multi_agent_mini_project.py \
  --approve-review \
  --approve-delegation \
  --approve-conflict \
  --approve-release
```

각 flag는 다른 stage의 gate를 열지 않습니다. 예를 들어 `--approve-review`만 전달하면 review QA만 실행할 수 있고, delegated Worker와 release QA/DevOps는 계속 `awaiting_human_approval`에 남아야 합니다.

## 5. 단계별 권 단위 검증

### 5.1 기본 pause 확인

기본 명령의 핵심 출력은 아래와 같아야 합니다.

```text
review_status=awaiting_human_approval
delegation_status=awaiting_human_approval
delegation_completed_task_ids=-
conflict_status=awaiting_human_approval
conflict_consensus_option=offline tutorial
release_status=awaiting_human_approval
release_handoff_note=-
```

여기서 conflict consensus는 사람이 검토할 **recommendation**입니다. `conflict_status`가 pause이므로 그 recommendation은 아직 workflow completion이 아닙니다.

### 5.2 명시 승인 경로 확인

네 approval flag를 모두 전달했을 때 핵심 출력은 아래와 같아야 합니다.

```text
review_status=completed
delegation_status=completed
delegation_completed_task_ids=draft,verify
conflict_status=completed
conflict_consensus_option=offline tutorial
release_status=completed
release_handoff_note=Handoff: local release note ready; no deployment ran.
```

`release_handoff_note`의 마지막 문장은 이 예제의 capability 경계를 보여 줍니다. DevOps Mock은 text note를 반환할 뿐 deployment client, subprocess, network client를 갖지 않습니다.

### 5.3 Volume 07 regression test 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07 -q
```

이 test suite는 다음을 local Mock으로 검증합니다.

- fixed response, plan, proposal script가 immutable tuple이고 소진되면 fallback 없이 실패한다.
- malformed role boundary 또는 declared Mock role mismatch가 첫 Agent 호출 전에 fail-closed한다.
- review, delegation, conflict, release의 반복 횟수가 각각 설정된 상한을 넘지 않는다.
- `PENDING`에서는 QA, Worker, DevOps가 호출되지 않는다.
- `REJECTED`에서는 모든 Agent 호출 전에 종료한다.
- Reviewer 이외 역할은 `ReviewDecision` authority를 주장할 수 없다.
- offline mini project CLI의 기본 pause와 독립 approval flag 결과가 고정된다.

## 6. 코드와 결과물 인계표

| 결과물 | 현재 책임 | Router로 넘길 수 있는 정보 | Router가 해서는 안 되는 일 |
|---|---|---|---|
| `BoundedReviewWorkflow` | Planner → Researcher → Developer/Reviewer → QA의 유한 검토 | task, status, immutable messages, review cycle 수 | Reviewer 승인 또는 QA approval 생성 |
| `ApprovalGatedDelegationWorkflow` | manifest 검토 뒤 bounded Worker dispatch | objective, manifest audit, completed task ID, status | allow-list 밖 assignee 선택, Worker 승인 생성 |
| `BoundedConflictResolutionWorkflow` | exact consensus만 recommendation으로 생성 | objective, consensus option, round, status | 다수결 fallback, conflict winner 추측, completion approval 생성 |
| `ApprovalGatedReleaseHandoffWorkflow` | QA 뒤 local handoff note 작성 | task, audit messages, handoff note, status | handoff note를 deployment로 해석하거나 deployment 실행 |
| `DeterministicMock*` | local test fixture와 call history | explicit fixture contract와 bounded call budget | production identity, memory, network, tool capability로 사용 |

다음 Volume의 설계 입력은 이 표처럼 data와 policy를 구분해야 합니다. 특히 `status=awaiting_human_approval`은 Router가 자동 재시도할 신호가 아니라, 사람 결정을 기다리는 stop condition입니다.

## 7. Volume 07 용어집

| 용어 | 설명 |
|---|---|
| Agent | role, goal, input/output schema, state, capability, authority, stop condition을 가진 협업 경계입니다. 단순 text completion과 다릅니다. |
| Role | Planner, Reviewer처럼 어떤 판단을 맡는지를 나타내는 이름입니다. 이름만으로 tool 또는 approval 권한이 생기지 않습니다. |
| Goal | 현재 호출이 달성하려는 bounded 목적입니다. 이 권에서는 non-empty `task` 또는 `objective`로 전달합니다. |
| State | 한 run에만 유효한 task/objective, counter, immutable audit message입니다. |
| Memory | 여러 run 또는 session에 남을 수 있는 정보입니다. 이 권의 deterministic Mock은 memory를 읽거나 쓰지 않습니다. |
| Message passing | 검증된 role output을 다음 role context에 immutable message로 넣는 방식입니다. capability 전달이 아닙니다. |
| Deterministic Mock | 고정된 immutable script를 호출 순서대로 소비하는 local test double입니다. network, secret, tool, fallback이 없습니다. |
| Bounded loop | review cycle, worker attempt, conflict round처럼 positive integer 상한으로 제한한 반복입니다. |
| Fail-closed | schema, role, approval, call budget 계약이 맞지 않으면 다음 역할이나 fallback을 실행하지 않고 중단하는 정책입니다. |
| Human-in-the-loop | risk가 있는 다음 local stage 전에 명시적인 사람 결정을 요구하는 경계입니다. 운영의 인증·기록·만료 정책과는 별도로 설계해야 합니다. |
| Exact consensus | 모든 conflict proposal의 option이 정확히 같은 경우만 recommendation을 만드는 규칙입니다. |
| Local handoff | QA 이후 DevOps Mock이 만드는 text note입니다. release 또는 deployment가 아닙니다. |
| Router handoff | 다음 Volume에서 정책 기반 선택을 위해 workflow request/result를 구조화해 넘기는 일입니다. approval 또는 capability 위임이 아닙니다. |

## 8. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| 기본 실행인데 `completed`가 기대됨 | approval flag가 없으면 정상적으로 pause함 | 이 장의 기본 출력과 비교합니다. 학습용 completed 경로는 필요한 stage flag를 명시합니다. |
| `WorkflowConfigurationError` | role, callable boundary, immutable script 또는 positive bound가 구성 계약을 위반함 | role label, tuple container, required field, positive integer를 확인합니다. |
| `AgentProtocolError` | runtime output schema가 맞지 않거나 fixed script가 소진됨 | 다음 역할을 호출하지 말고 output type/content/review와 configured call budget을 수정합니다. |
| Worker 또는 DevOps가 pending 상태에서 호출됨 | orchestrator가 human gate보다 앞서 side-effecting role을 호출함 | test의 call history를 확인하고 gate 이전 호출을 제거합니다. 이 권의 code path는 이를 허용하지 않습니다. |
| Router가 `APPROVED`를 만들도록 설계됨 | selection policy와 human approval authority를 혼동함 | Router 결과와 사람 승인 record를 별도 type과 storage boundary로 분리합니다. 이 offline slice에는 Router를 추가하지 않습니다. |
| handoff note를 release로 해석함 | local audit output과 external action을 혼동함 | `completed`와 deployment를 분리합니다. deployment capability는 이 권에 존재하지 않습니다. |

## 9. 응용 실습

1. `offline_multi_agent_mini_project.py`를 복사하지 말고, 기존 builder의 `max_review_cycles`, `max_rounds`, `max_worker_attempts`가 모두 양수인지 찾아 call budget을 표로 작성합니다.
2. Reviewer가 `REVISE`만 반환하는 tuple script를 구성하고, review/release에서 QA와 DevOps call history가 빈 list인지 test로 확인합니다.
3. Conflict peer 두 개가 서로 다른 option을 반환하도록 수정한 local fixture를 만들고, `conflict_limit_reached`가 다수결 선택 없이 반환되는지 확인합니다.
4. 다음 Volume에서 사용할 Router request schema를 설계합니다. `workflow_kind`, `objective`, `status`는 포함하되 `approval`, tool object, secret, mutable script는 포함하지 마십시오.

## 10. 실무 적용

운영 Multi-Agent 시스템에 Router나 tool을 더할 때도 이 권의 계약 순서를 유지합니다.

1. workflow가 role, schema, authority, bounded stop condition을 정의합니다.
2. Router는 capability policy를 검사해 적격 workflow만 선택합니다.
3. 별도 승인 시스템이 승인자 identity, scope, timestamp, expiration, immutable record를 검증합니다.
4. tool executor는 allow-list와 최소 권한을 다시 검사합니다.
5. observability는 secret을 기록하지 않는 audit event를 남깁니다.

> [!TIP]
> Router의 fallback은 `PENDING`, protocol error, review limit을 무시하도록 만들면 안 됩니다. fallback target에도 독립적인 capability 및 approval policy가 있어야 합니다.

## 11. 과제

### 기본

- 네 workflow의 `PENDING` 결과에서 아직 호출되지 않은 역할을 각각 적습니다.
- 이 장의 용어집에서 state와 memory의 차이를 자신의 말로 설명합니다.

### 응용

- role별 allow-list, maximum call budget, human gate를 한 장의 표로 작성합니다.
- `REJECTED`가 첫 Agent call 이전에 종료되는 test assertion을 각 workflow에서 찾습니다.

### 심화

- Router가 workflow를 선택한 뒤 사람 승인 record를 참조하는 운영 설계를 작성합니다. record의 approval scope, approver identity, expiration, immutable audit location을 포함해야 합니다.
- production tool을 별도 adapter로 설계하되, deterministic Mock package에는 import하지 않도록 dependency boundary를 제안합니다.

## 12. 완료 체크리스트

- [ ] 기본 mini project 실행에서 네 workflow가 `awaiting_human_approval`로 멈췄다.
- [ ] 네 explicit approval flag가 서로 독립된 stage만 열었음을 확인했다.
- [ ] 전체 approval flag 실행의 `completed`가 local-only completion임을 설명할 수 있다.
- [ ] `uv run pytest tests/volume07 -q`를 실행해 Volume 07 regression test를 통과했다.
- [ ] deterministic Mock, bounded loop, fail-closed, human approval을 구분할 수 있다.
- [ ] Router가 workflow selector이지 승인자나 tool executor가 아님을 설명할 수 있다.
- [ ] Router Volume으로 넘길 request/result와 넘기면 안 되는 capability를 구분했다.

## 13. 핵심 정리

Volume 07의 결과물은 여러 Agent를 무제한 연결하는 framework가 아닙니다. local deterministic Mock으로 role boundary와 message passing을 재현하고, 모든 loop를 bounded하게 만들며, 다음 stage는 명시적인 사람 승인 뒤에만 진행하는 workflow 계약입니다. 다음 Volume의 Router는 이 계약 위에서 선택 정책을 추가할 수 있지만, authority, approval, capability 경계를 대신할 수 없습니다.
