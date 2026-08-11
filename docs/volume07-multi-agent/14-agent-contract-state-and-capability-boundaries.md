# 14. Agent 계약, 상태, Memory와 Tool 경계

## 1. 학습 목표

이 장에서는 Multi-Agent를 단순히 여러 LLM 호출을 연결한 것으로 보지 않고, **역할·목표·입력·출력·상태·권한·종료 조건**을 가진 협업 경계로 설계합니다. 학습을 마치면 다음을 설명할 수 있습니다.

- Agent와 단순 LLM 호출의 차이
- Planner, Researcher, Developer, Reviewer, QA, DevOps의 역할 분리
- 현재 실행의 state/audit와 장기 memory의 분리
- 메시지 전달이 tool 실행 권한이나 사람 승인이 될 수 없는 이유
- deterministic Mock, 유한 호출 예산, 명시적 승인으로 offline 실습을 고정하는 방법

> 이 장의 예제와 연결된 Volume 07 코드는 local deterministic Mock만 사용합니다. live API, network agent, secret, tool execution, file mutation, deployment를 수행하지 않습니다.

## 2. 왜 Agent 계약이 필요한가

단순 LLM 호출은 보통 입력 prompt와 출력 text의 한 쌍입니다.

```text
prompt -> model -> text
```

반면 Agent는 목표를 향해 여러 번 판단할 수 있으므로, 역할과 입력·출력 경계를 지정하지 않으면 다음 문제가 생깁니다.

- Planner의 초안이 Reviewer의 승인처럼 취급될 수 있다.
- 이전 실행의 memory가 다음 실행의 테스트 결과를 바꿀 수 있다.
- 메시지에 `배포하라`는 text가 있다는 이유만으로 tool 실행 권한이 생길 수 있다.
- 재작업이나 retry에 종료 조건이 없어 호출이 계속될 수 있다.
- recommendation과 사람의 실행 승인이 혼동될 수 있다.

따라서 Agent를 다음 계약으로 먼저 표현합니다.

| 계약 요소 | 설계 질문 | Volume 07의 offline 경계 |
|---|---|---|
| Role | 누가 어떤 판단을 하는가? | `planner`, `researcher`, `developer`, `reviewer`, `qa`, `devops`, `coordinator`, `worker` |
| Goal | 이번 호출이 달성하려는 것은 무엇인가? | `AgentContext.task` 또는 `DelegationContext.objective`의 non-empty 문자열 |
| Input state | 무엇을 읽을 수 있는가? | 이전 `messages`의 immutable tuple과 현재 iteration/attempt |
| Output schema | 무엇을 반환해야 하는가? | `AgentResponse`, `DelegationPlan`, `WorkerResponse`, `ConflictProposal` |
| Capability | 무엇을 실제로 바꿀 수 있는가? | Mock은 text/audit만 만들며 tool, network, deployment capability가 없음 |
| Authority | 어떤 결정을 할 수 있는가? | `ReviewDecision`은 Reviewer만 반환 가능 |
| Stop condition | 언제 멈추는가? | review cycle, conflict round, worker attempt의 positive integer bound |
| Human gate | 어떤 다음 단계가 명시적 승인을 기다리는가? | QA, Worker dispatch, conflict completion, local release handoff |

이 표의 모든 항목을 코드, test, 운영 정책에서 같은 의미로 유지해야 합니다. 역할 이름이나 prompt 문장만으로는 계약이 되지 않습니다.

## 3. 역할과 메시지 흐름

가장 작은 review workflow의 정보 흐름은 아래와 같습니다.

```text
Task/goal
   |
   v
Planner -> Researcher -> Developer <-> Reviewer --(APPROVE)--> human gate --> QA
                                  ^                |
                                  +--(REVISE)------+
```

- **Planner**는 목표를 실행 가능한 계획으로 바꿉니다. 승인 권한은 없습니다.
- **Researcher**는 계획을 위한 local evidence를 제공합니다. 이 offline slice에서는 외부 검색을 하지 않습니다.
- **Developer**는 현재 cycle의 draft를 만듭니다.
- **Reviewer**만 `APPROVE` 또는 `REVISE`라는 검토 결정을 낼 수 있습니다.
- **QA**는 Reviewer의 `APPROVE`만으로 호출되지 않습니다. 사람의 명시적 `HumanApproval.APPROVED`가 추가로 필요합니다.
- **DevOps**는 release handoff workflow에서 QA 뒤에 local handoff note만 만듭니다. 배포 권한은 없습니다.

실제 전달되는 상태는 immutable audit message입니다.

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

다음 역할은 `context.messages`에서 이전 역할이 남긴 내용을 읽을 수 있지만, `tuple`과 frozen dataclass를 통해 과거 audit record를 정상적인 Python assignment로 변경할 수 없습니다. 새 응답은 orchestrator가 검증한 뒤에만 다음 `AgentMessage`로 추가합니다.

## 4. State와 Memory를 분리하기

### 4.1 실행 state

Volume 07의 state는 한 번의 run에서만 의미가 있습니다.

- `task` 또는 `objective`
- `iteration`, `round`, `attempt`
- 이전 역할의 immutable `messages`
- workflow result의 status와 bounded counter

이 state는 다음 역할에 무엇을 보냈는지 audit하는 데 사용됩니다. 실행이 끝나면 `WorkflowResult`, `DelegationResult`, `ConflictResolutionResult`, `ReleaseHandoffResult`가 그 실행의 snapshot입니다.

### 4.2 장기 memory

장기 memory는 다른 session이나 실행에도 남을 수 있는 정보입니다. 사용자 선호, 프로젝트 지식, 이전 결론은 유용할 수 있지만 deterministic test fixture나 이번 실행의 approval record와 같은 저장소가 아닙니다.

| 구분 | 실행 state/audit | 장기 memory |
|---|---|---|
| 수명 | 단일 bounded run | 여러 session 또는 workflow |
| writer | orchestrator가 검증한 역할 결과 | 명시적으로 권한을 받은 memory writer |
| 테스트 영향 | 고정 fixture로 재현 가능 | 비활성화하거나 별도 fixture로 격리해야 함 |
| 승인 기록 | 사람 승인 시스템의 immutable record가 필요 | 일반 memory text로 저장하지 않음 |

이 권의 Mock은 장기 memory를 읽거나 쓰지 않습니다. Hermes runtime이나 다른 agent framework에서 memory를 켤 때는 profile scope, owner, writer, retention, 민감 정보 금지 규칙을 별도로 정해야 합니다. runtime의 memory 기능은 Reviewer 권한이나 사람 승인을 대체하지 않습니다.

## 5. Tool과 메시지를 분리하기

메시지는 정보이고 tool은 영향을 줄 수 있는 capability입니다. 다음 두 문장은 전혀 다릅니다.

```text
Developer message: "A release candidate is ready."
DevOps capability: "A deployment client may call a production endpoint."
```

첫 문장은 audit trail에 기록될 text입니다. 두 번째는 별도 allow-list, identity, policy enforcement, approval record, timeout, rollback 계획을 필요로 하는 권한입니다. Volume 07의 `DeterministicMockAgent`, `DeterministicMockWorker`, `DeterministicMockCoordinator`, `DeterministicMockConflictAgent`에는 tool executor와 network client가 없습니다. 따라서 다음 code path도 없습니다.

```python
# Volume 07에는 의도적으로 이런 capability가 없다.
# deploy_client.deploy(...)
# subprocess.run(...)
# http_client.post(...)
```

운영 환경에서 tool을 추가해야 한다면 role별 최소 권한 allow-list를 먼저 정의합니다. 예를 들어 Reviewer는 read-only evidence inspection, QA는 deterministic local verification, DevOps는 handoff record 준비까지만 허용할 수 있습니다. 외부 변경은 이 allow-list와 업무 사람 승인 모두를 통과해야 합니다.

## 6. 유한 반복과 명시적 사람 승인

Agent가 재작업하거나 conflict를 해결할 때, `while True`나 성공할 때까지의 implicit retry는 안전한 종료 조건이 아닙니다. Volume 07은 수치 상한과 fail-closed 결과를 사용합니다.

| Workflow | 상한 | 정상 pause | 상한 도달/실패 |
|---|---|---|---|
| review | `max_review_cycles` | Reviewer approve 뒤 QA gate | `review_limit_reached` |
| delegation | `max_tasks`, `max_worker_attempts` | coordinator manifest 뒤 Worker gate | `worker_retry_limit_reached` |
| conflict | `max_agents`, `max_rounds` | exact consensus 뒤 completion gate | `conflict_limit_reached` |
| release handoff | `max_review_cycles` | Reviewer approve 뒤 QA/DevOps gate | `review_limit_reached` |

`PENDING`은 recommendation, manifest 또는 approved review를 기록할 수 있지만 gated 역할을 실행하지 않습니다. `REJECTED`는 Agent를 호출하기 전에 종료합니다. `APPROVED`는 해당 workflow의 다음 local 단계만 허용합니다. 이 enum은 교육용 local input일 뿐이며, 운영의 인증된 승인자, scope, timestamp, expiration, immutable approval record를 대체하지 않습니다.

## 7. 실습: 계약을 코드와 test로 확인하기

저장소 루트의 bash 또는 WSL terminal에서 다음 명령을 실행합니다.

```bash
uv run python examples/volume07/offline_review_workflow.py
uv run python examples/volume07/offline_approved_delegation.py
uv run python examples/volume07/offline_conflict_resolution.py
uv run python examples/volume07/offline_release_handoff.py
uv run pytest tests/volume07 -q
```

각 예제의 기본 실행은 `awaiting_human_approval`에서 멈춰야 합니다. 마지막 test command는 다음 계약을 local Mock으로 확인합니다.

1. 역할별 output schema가 다음 역할 호출 전에 검사된다.
2. Reviewer 외 역할의 review decision은 audit trail에 들어가기 전에 거절된다.
3. fixed script가 소진되면 fallback이나 무한 호출 없이 실패한다.
4. bounded retry/round/cycle가 다음 역할의 실행을 제한한다.
5. `PENDING`에서 QA, Worker, DevOps가 호출되지 않는다.
6. local handoff note가 deployment를 뜻하지 않는다.

## 8. 오류 해결

| 증상 | 가능한 원인 | 해결 |
|---|---|---|
| `WorkflowConfigurationError` | role, callable boundary, script, bound가 구성 계약을 위반함 | role label, immutable tuple script, positive integer bound를 확인합니다. |
| `AgentProtocolError` | 실행 Agent가 schema를 만족하지 않거나 script가 소진됨 | 다음 역할을 호출하지 말고 output type/content/review와 call budget을 수정합니다. |
| Reviewer가 approve했는데 QA가 실행되지 않음 | 사람 승인이 `PENDING`임 | 교육용 예제에서는 명시적 `APPROVED`를 전달해 별도 gate를 엽니다. |
| `completed`가 deployment를 뜻한다고 해석됨 | workflow status와 external side effect를 혼동함 | Volume 07의 completed는 local deterministic workflow 완료이며 handoff note 외 external action이 없음을 확인합니다. |

## 9. 적용 과제

1. Planner가 `review=ReviewDecision.APPROVE`를 반환하면 Reviewer가 아닌 역할의 권한 위반으로 fail-closed되는 test를 읽고 설명합니다.
2. `max_review_cycles=1`에서 Reviewer가 `REVISE`를 반환하는 deterministic Mock을 만들고 QA가 0회 호출되는지 확인합니다.
3. 장기 memory가 필요한 운영 사례를 하나 고르고, 실행 state와 분리할 owner, writer, retention, 삭제 정책을 표로 작성합니다.
4. DevOps에 실제 tool을 추가하는 대신, 어떤 allow-list와 사람 승인 scope가 먼저 필요한지 설계합니다. 이 offline example에는 tool을 추가하지 않습니다.

## 10. 완료 체크리스트

- [ ] Agent 계약에 role, goal, input/output schema, capability, authority, stop condition, human gate를 포함했다.
- [ ] 현재 실행 state와 장기 memory의 수명·writer·승인 기록 책임을 구분했다.
- [ ] 메시지 전달이 tool permission이나 deployment approval이 아님을 설명할 수 있다.
- [ ] 모든 재작업과 retry에 유한한 수치 상한과 fail-closed 결과가 있음을 확인했다.
- [ ] `PENDING`과 `REJECTED`가 gated role을 실행하지 않는 test를 통과시켰다.

## 11. 핵심 정리

Multi-Agent의 핵심은 Agent 수가 아니라 계약입니다. 역할별 목표와 output authority를 분리하고, 메시지는 immutable state로 전달하며, memory와 tool capability는 별도 경계로 모델링해야 합니다. 여기에 bounded loop와 명시적 사람 승인을 더하면 deterministic local Mock으로도 운영 설계의 중요한 안전 계약을 먼저 검증할 수 있습니다.
