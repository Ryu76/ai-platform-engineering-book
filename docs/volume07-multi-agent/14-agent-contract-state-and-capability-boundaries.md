# 14. Agent 계약, 상태, Memory와 Tool 경계

## 1. 학습 목표

이 장에서는 Multi-Agent를 여러 LLM 호출의 나열이 아니라 **role, goal, input/output schema, state, capability, authority, stop condition, human gate**를 가진 협업 계약으로 설계합니다. 학습 후에는 다음을 할 수 있어야 합니다.

- Planner, Researcher, Developer, Reviewer, QA, DevOps의 책임과 권한을 분리한다.
- `AgentContext`의 실행 state와 장기 memory를 구분한다.
- `AgentResponse` schema와 Reviewer의 `ReviewDecision` authority를 설명한다.
- deterministic Mock, bounded loop, explicit human approval의 독립된 책임을 검증한다.
- message text가 tool, file mutation, deployment capability가 아님을 설명한다.

> [!WARNING]
> Volume 07은 local deterministic Mock만 사용합니다. live API, network agent, secret, tool execution, file mutation, deployment를 수행하거나 설정하지 않습니다.

## 2. 왜 필요한가

단순 LLM 호출은 대개 입력 prompt와 출력 text의 한 쌍입니다.

```text
prompt -> model -> text
```

반면 Agent는 여러 role이 이전 상태를 읽고 다음 판단을 만들 수 있습니다. 계약이 없으면 Planner의 초안이 Reviewer 승인처럼 취급되거나, message의 `배포하라`는 text가 tool 권한으로 오해될 수 있습니다. retry의 stop condition이 없으면 호출도 계속될 수 있습니다.

따라서 Multi-Agent 설계에서는 message, state, memory, tool, approval을 다른 책임으로 모델링해야 합니다. 이 장의 Mock workflow는 해당 분리를 network나 외부 변경 없이 재현합니다.

## 3. 핵심 개념

| 계약 요소 | 설계 질문 | Volume 07의 offline 경계 |
|---|---|---|
| Role | 누가 어떤 판단을 하는가? | `planner`, `researcher`, `developer`, `reviewer`, `qa`, `devops`, `coordinator`, `worker` |
| Goal | 이번 호출이 달성하려는 것은 무엇인가? | non-empty `task` 또는 `objective` |
| Input state | 무엇을 읽는가? | immutable message tuple과 현재 iteration/attempt |
| Output schema | 무엇을 반환해야 하는가? | `AgentResponse`, `DelegationPlan`, `WorkerResponse`, `ConflictProposal` |
| Capability | 무엇을 실제로 바꿀 수 있는가? | Mock은 text/audit만 만들며 network, tool, deployment capability가 없음 |
| Authority | 어떤 결정을 할 수 있는가? | `ReviewDecision`은 Reviewer만 반환 가능 |
| Stop condition | 언제 멈추는가? | positive integer call bound와 fixed script 소진 fail-closed |
| Human gate | 어떤 단계가 사람 결정을 기다리는가? | QA, Worker dispatch, conflict completion, local release handoff |

- **State와 memory:** `AgentContext`와 audit message는 한 bounded run의 state입니다. 장기 memory는 별도 writer, retention, deletion, secret-exclusion 정책이 필요하며 이 Mock에는 없습니다.
- **Schema와 fail-closed:** runtime output이 schema를 충족하지 않으면 audit에 기록하거나 다음 role을 호출하지 않습니다.
- **Explicit approval:** `PENDING`은 pause, `APPROVED`는 해당 workflow의 다음 local 단계만 허용, `REJECTED`는 첫 Agent call 전 종료를 뜻합니다.

## 4. 동작 구조

가장 작은 review workflow의 정보 흐름은 아래와 같습니다.

```text
Task/goal
   |
   v
Planner -> Researcher -> Developer <-> Reviewer --(APPROVE)--> human gate --> QA
                                  ^                |
                                  +--(REVISE)------+
```

- Planner는 goal을 local plan으로 바꾸지만 approval authority는 없습니다.
- Researcher는 external search 없이 fixture가 준 local evidence만 반환합니다.
- Developer는 현재 bounded cycle의 draft를 만듭니다.
- Reviewer만 `APPROVE` 또는 `REVISE`를 포함한 `ReviewDecision`을 반환할 수 있습니다.
- QA는 Reviewer approval만으로 호출되지 않습니다. 명시적인 `HumanApproval.APPROVED`가 추가로 필요합니다.
- release handoff의 DevOps는 QA 뒤 local text note만 만들며 deployment capability는 없습니다.

```text
PENDING  -> recommendation/manifest/review audit -> awaiting_human_approval
APPROVED -> only the workflow's next bounded local stage
REJECTED -> human_rejected before every Agent call
```

## 5. 실습 환경

- Python 3.12 이상과 repository의 `uv` environment가 필요합니다.
- 저장소 루트의 bash 또는 WSL terminal에서 명령을 실행합니다.
- 실습 대상은 `examples/volume07/`, `src/ai_platform/agents/`, `tests/volume07/`의 repository-local code입니다.
- `DeterministicMockAgent`, `DeterministicMockCoordinator`, `DeterministicMockWorker`, `DeterministicMockConflictAgent`는 fixed immutable tuple script만 소비합니다.

API key나 다른 secret을 추가하지 마십시오. 이 examples와 tests에는 live API client, network agent, tool executor, file mutation, deployment client가 없습니다.

## 6. 단계별 실습

먼저 approval 없이 네 local workflow의 pause 경계를 확인합니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume07/offline_review_workflow.py
uv run python examples/volume07/offline_approved_delegation.py
uv run python examples/volume07/offline_conflict_resolution.py
uv run python examples/volume07/offline_release_handoff.py
```

각 example은 `awaiting_human_approval`에서 멈춰야 합니다. review와 release의 QA, delegation의 Worker, release의 DevOps는 호출되지 않습니다.

그 다음 mini project로 stage별 local approval gate가 독립적인지 확인합니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume07/offline_multi_agent_mini_project.py
uv run python examples/volume07/offline_multi_agent_mini_project.py \
  --approve-review \
  --approve-delegation \
  --approve-conflict \
  --approve-release
```

마지막으로 Volume 07 regression을 실행합니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07 -q
```

이 test suite는 response schema, role-scoped review authority, immutable fixed script, bounded retry/round/cycle, `PENDING` gate, `REJECTED` pre-call termination을 local Mock으로 검증합니다.

## 7. 코드 설명

### 7.1 Immutable execution state

`AgentContext`는 task, iteration, immutable message tuple을 한 role에 전달합니다.

```python
from ai_platform.agents import AgentContext, AgentMessage

prior_messages = (
    AgentMessage(role="planner", content="Plan: keep the example offline.", iteration=0),
)
context = AgentContext(
    task="Write an offline tutorial.",
    iteration=1,
    messages=prior_messages,
)
```

다음 role은 `context.messages`를 읽을 수 있지만 `tuple`과 frozen dataclass 때문에 과거 audit record를 assignment로 변경할 수 없습니다. orchestrator는 검증한 새 output만 새 `AgentMessage`로 append한 snapshot을 다음 role에 전달합니다.

### 7.2 Output schema와 role authority

`AgentResponse`는 non-empty `content`와 선택적인 `review`를 가집니다. runtime response가 `AgentResponse`가 아니거나 content가 비어 있거나 enum 이외 review를 가지면 `AgentProtocolError`가 발생합니다. Reviewer가 아닌 role의 review 값도 audit trail에 들어가기 전에 fail-closed됩니다.

```python
AgentResponse(content="Draft is ready.")
AgentResponse(content="Approved local draft.", review=ReviewDecision.APPROVE)
```

둘째 response는 Reviewer boundary에서만 유효합니다. Planner, Researcher, Developer, QA, DevOps가 같은 값을 반환해도 사람 승인이 생성되지 않으며 protocol error입니다.

### 7.3 State와 장기 memory

Volume 07의 단일 run state는 task/objective, iteration/round/attempt, immutable messages, result status와 bounded counter입니다. `WorkflowResult`, `DelegationResult`, `ConflictResolutionResult`, `ReleaseHandoffResult`는 run이 끝난 뒤의 snapshot입니다.

장기 memory는 다른 session에도 남을 수 있으므로 profile scope, owner, writer, retention, deletion 정책이 필요합니다. 일반 memory text는 authenticated approval record가 아니며 deterministic fixture도 아닙니다. 이 권의 deterministic Mock은 memory를 읽거나 쓰지 않습니다.

### 7.4 Tool, bounded loop, human gate

message는 정보이고 tool은 영향을 줄 수 있는 capability입니다. `Developer message: "A release candidate is ready."`라는 text는 `deploy_client.deploy(...)` 권한을 만들지 않습니다. Volume 07에는 의도적으로 deployment client, `subprocess.run(...)`, HTTP client가 없습니다.

| Workflow | finite bound | `PENDING` pause | fail-closed result |
|---|---|---|---|
| review | `max_review_cycles` | Reviewer approve 뒤 QA gate | `review_limit_reached` |
| delegation | `max_tasks`, `max_worker_attempts` | coordinator manifest 뒤 Worker gate | `worker_retry_limit_reached` |
| conflict | `max_agents`, `max_rounds` | exact consensus 뒤 completion gate | `conflict_limit_reached` |
| release handoff | `max_review_cycles` | Reviewer approve 뒤 QA/DevOps gate | `review_limit_reached` |

Fixed tuple script가 소진되면 fallback 없이 `AgentProtocolError`가 발생합니다. `APPROVED`도 그 workflow의 next local stage만 열고, tool 또는 deployment scope를 확장하지 않습니다.

## 8. 정상 실행 결과

approval 없이 mini project를 실행하면 핵심 output은 다음과 같습니다.

```text
review_status=awaiting_human_approval
delegation_status=awaiting_human_approval
delegation_completed_task_ids=-
conflict_status=awaiting_human_approval
conflict_consensus_option=offline tutorial
release_status=awaiting_human_approval
release_handoff_note=-
```

모든 explicit approval flag를 전달한 교육용 local run에서는 각 workflow가 `completed`가 될 수 있습니다. `release_handoff_note`는 `no deployment ran.`으로 끝나는 local text note입니다. 이는 release, external API call, file mutation, tool execution, deployment 성공을 뜻하지 않습니다.

## 9. 오류 해결

| 증상 | 가능한 원인 | 해결 |
|---|---|---|
| `WorkflowConfigurationError` | role, callable boundary, tuple script 또는 positive bound가 구성 계약을 위반함 | role label, immutable tuple, required field, context-compatible method signature를 확인합니다. |
| `AgentProtocolError` | runtime output schema가 맞지 않거나 fixed script가 소진됨 | 다음 role을 호출하지 말고 output type/content/review와 configured call budget을 수정합니다. |
| Reviewer가 approve했는데 QA가 실행되지 않음 | human approval이 `PENDING`임 | explicit `APPROVED`를 해당 local workflow에만 전달합니다. |
| `completed`를 deployment로 해석함 | workflow status와 external side effect를 혼동함 | local completion, handoff note, production change를 별도로 다룹니다. |
| memory text를 approval record로 사용함 | memory와 approval authority를 혼동함 | identity, scope, timestamp, expiration, immutable record를 가진 별도 approval system을 설계합니다. |

## 10. 응용 실습

1. `AgentContext.messages`의 tuple item assignment가 실패하는 이유를 설명하고, 새 message가 새 snapshot에만 추가되는 흐름을 그립니다.
2. Planner local test double이 `review=ReviewDecision.APPROVE`를 반환하도록 만들고 Reviewer authority 위반이 audit 전 `AgentProtocolError`가 되는 test를 읽습니다.
3. `PENDING`, `APPROVED`, `REJECTED`를 각각 전달하는 table-driven test를 설계합니다. 각 row에 호출 가능한 gated role을 적습니다.
4. 장기 memory가 필요한 사례 하나를 골라 state와 분리할 writer, retention, deletion policy를 작성합니다. deterministic Mock에는 memory backend를 연결하지 않습니다.

## 11. 실무 적용

운영 Multi-Agent에서 local Mock을 실제 adapter로 교체하더라도 계약 순서는 바꾸지 않습니다.

1. role별 goal, input/output schema, authority, bounded stop condition을 code와 test로 정의합니다.
2. memory를 owner, authorized writer, retention, deletion, secret exclusion policy를 가진 별도 storage boundary에 둡니다.
3. approval system이 approver identity, scope, timestamp, expiration, immutable record를 검증하게 합니다. Agent message나 enum text만으로 approval을 만들지 않습니다.
4. tool executor가 별도 allow-list와 최소 권한을 재검증하게 합니다. human approval이 있어도 tool scope 밖 action을 허용하지 않습니다.
5. deployment와 external mutation은 offline workflow의 `completed`와 분리된 운영 control plane에서만 처리합니다.

## 12. 과제

### 기본

- Role, capability, authority의 차이를 Planner, Reviewer, DevOps를 예로 들어 설명합니다.
- 한 run state와 장기 memory의 수명 및 writer 차이를 표로 작성합니다.

### 응용

- 네 workflow의 bound와 `PENDING`에서 실행하지 않는 role을 한 표로 작성합니다.
- Reviewer 이외 role의 review decision이 fail-closed되는 assertion을 `tests/volume07/`에서 찾습니다.

### 심화

- production approval record의 scope, approver identity, timestamp, expiration, immutable audit location을 설계합니다.
- production tool adapter를 별도 package로 두고 deterministic Mock package가 이를 import하지 않도록 dependency boundary를 제안합니다.

## 13. 완료 체크리스트

- [ ] Agent 계약에 role, goal, input/output schema, capability, authority, stop condition, human gate를 포함했다.
- [ ] `AgentContext` state와 장기 memory의 lifetime, writer, approval record 책임을 구분했다.
- [ ] message 전달이 tool permission이나 deployment approval이 아님을 설명할 수 있다.
- [ ] 모든 retry와 rework에 finite positive bound와 fail-closed 결과가 있음을 확인했다.
- [ ] `PENDING`에서 QA, Worker, DevOps가 호출되지 않음을 확인했다.
- [ ] `REJECTED`가 모든 Agent call 전에 종료함을 확인했다.
- [ ] `uv run pytest tests/volume07 -q`를 통과시켰다.

## 14. 핵심 정리

Multi-Agent의 핵심은 Agent 수가 아니라 계약입니다. role별 goal과 output authority를 분리하고, message는 immutable execution state로 전달하며, long-term memory와 tool capability는 별도 boundary로 모델링해야 합니다. 여기에 deterministic Mock, bounded loop, explicit human approval을 더하면 live API, secret, deployment 없이도 중요한 안전 계약을 재현하고 검증할 수 있습니다.
