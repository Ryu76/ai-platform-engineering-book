# 13. 결정론적 Offline Multi-Agent 미니 프로젝트

## 1. 학습 목표

이 장에서는 Planner, Researcher, Developer, Reviewer, QA, Coordinator, Worker, DevOps 역할을 하나의 **offline 미니 프로젝트**로 조합합니다. 학습을 마치면 단계별로 독립된 사람 승인(Human Approval)을 전달하고, 승인되지 않은 작업은 recommendation 또는 manifest에서 멈추는 이유를 설명할 수 있습니다.

## 2. 왜 필요한가

각 workflow를 따로 실행하면 역할, bounded loop, approval gate를 이해하기 쉽습니다. 그러나 실제 설계에서는 여러 workflow가 같은 목표를 지원할 수 있습니다. 이때 한 단계의 승인을 다른 단계의 승인으로 오해하거나, recommendation을 실행 완료로 표시하면 안 됩니다.

미니 프로젝트는 네 가지 local workflow를 한 번씩 실행합니다. Review, delegation, conflict consensus, release handoff는 각각 독립된 승인 flag를 받습니다. 한 flag가 다른 단계의 권한이 되지 않습니다.

## 3. 핵심 개념

- **결정론적 Mock Agent:** 고정 tuple script만 소비하며 network, API, tool, secret을 사용하지 않습니다.
- **역할 분리:** Review는 Planner/Researcher/Developer/Reviewer/QA를, delegation은 Coordinator/Worker를, release handoff는 DevOps를 사용합니다.
- **유한 반복:** review cycle은 1, conflict round는 1, delegation의 task 수는 2, Worker attempt는 1로 고정합니다.
- **독립된 승인:** `--approve-review`, `--approve-delegation`, `--approve-conflict`, `--approve-release`는 각자 하나의 gate만 엽니다.
- **로컬 handoff:** 완료된 release stage도 local handoff note만 생성하며 deploy를 실행하지 않습니다.

## 4. 동작 구조

```text
                         사람의 명시적 flag
                                  |
                                  v
+----------------+       +------------------------+
| deterministic  | ----> | four isolated workflows |
| local Mock     |       +------------------------+
+----------------+          |       |       |       |
                             v       v       v       v
                         review  delegation conflict release
                          QA       workers  complete QA/DevOps
                          gate      gate     gate     gate
                             |       |       |       |
           flag 없음 --------+-------+-------+-------+----> awaiting_human_approval
           해당 flag 있음 --------------------------------> 해당 local stage만 completed
```

`PENDING` 상태에서 review의 QA, delegation의 Worker, release의 QA/DevOps는 호출되지 않습니다. Conflict는 exact consensus recommendation을 기록하지만 `APPROVED`가 아니면 완료되지 않습니다.

## 5. 실습 환경

- Python 3.12 이상과 repository의 `uv` environment가 필요합니다.
- 실행 위치는 저장소 루트의 bash 또는 WSL terminal입니다.
- 파일 경로는 `examples/volume07/offline_multi_agent_mini_project.py`입니다.
- 이 예제는 standard library와 repository-local `ai_platform.agents`만 사용합니다. live API, network agent, tool execution, secret, deployment는 사용하지 않습니다.

## 6. 단계별 실습

먼저 어떤 승인도 전달하지 않고 실행합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL terminal
uv run python examples/volume07/offline_multi_agent_mini_project.py
```

이 명령은 네 stage의 audit-ready recommendation 또는 manifest를 만들지만 각 결과를 `awaiting_human_approval`에서 멈춥니다. Worker, review QA, release QA/DevOps의 실행 권한은 생기지 않습니다.

각 gate를 명시적으로 승인한 local demonstration을 실행합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL terminal
uv run python examples/volume07/offline_multi_agent_mini_project.py \
  --approve-review \
  --approve-delegation \
  --approve-conflict \
  --approve-release
```

각 flag는 예제 실행의 해당 stage에만 `APPROVED` enum을 전달합니다. 실제 사람 승인 record, identity, deployment 권한을 대체하지 않습니다.

CLI contract를 테스트합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL terminal
uv run pytest tests/volume07/test_offline_multi_agent_mini_project.py -q
```

## 7. 코드 설명

`build_review_workflow()`, `build_delegation_workflow()`, `build_conflict_workflow()`, `build_release_workflow()`는 새 호출마다 새 deterministic Mock을 구성합니다. 그래서 한 stage의 script 소비가 다른 stage에 영향을 주지 않습니다.

```python
review_approval = HumanApproval.APPROVED if arguments.approve_review else HumanApproval.PENDING
result = build_review_workflow().run(task="...", human_approval=review_approval)
```

이 선택은 review workflow의 QA gate에만 적용됩니다. Delegation, conflict, release는 서로 다른 enum과 별도 flag를 사용합니다. 모든 Mock script는 정확히 한 번의 bounded 경로에 필요한 response만 갖습니다. 예상보다 많은 호출은 fallback 없이 `AgentProtocolError`로 종료됩니다.

## 8. 정상 실행 결과

승인 없이 실행하면 다음 상태를 확인합니다.

```text
review_status=awaiting_human_approval
delegation_status=awaiting_human_approval
delegation_completed_task_ids=-
conflict_status=awaiting_human_approval
conflict_consensus_option=offline tutorial
release_status=awaiting_human_approval
release_handoff_note=-
```

네 flag를 모두 전달하면 status는 각각 `completed`가 됩니다. `release_handoff_note`에는 `no deployment ran.`이 포함됩니다. 이는 local note가 생성되었다는 뜻일 뿐, 배포 결과가 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `ModuleNotFoundError: ai_platform` | repository root 밖에서 Python을 직접 실행했거나 source path가 없음 | 저장소 루트에서 `uv run python examples/volume07/offline_multi_agent_mini_project.py`를 사용합니다. |
| 모든 status가 `awaiting_human_approval` | 명시적 approval flag가 없음 | 필요한 local stage의 `--approve-*` flag만 전달합니다. |
| `review_status=completed`인데 다른 stage는 pending | review flag만 전달됨 | 이것은 정상입니다. 다른 stage는 별도의 approval이 필요합니다. |
| `AgentProtocolError` | Mock script보다 많은 호출을 요구하도록 예제를 변경함 | loop/task/attempt bound와 immutable response tuple 길이를 함께 조정합니다. |

## 10. 응용 실습

1. `--approve-delegation`만 전달하여 Worker stage만 완료되는지 확인합니다.
2. Reviewer response를 `REVISE`로 바꾸고 `max_review_cycles=1`에서 QA가 호출되지 않는지 test로 고정합니다.
3. Conflict peer의 option을 다르게 설정하고 `conflict_limit_reached`가 되는 bounded 경로를 만듭니다.
4. release handoff에 deployment client를 추가하지 말고, local note에 approval ID placeholder를 표현하는 방법을 설계합니다.

## 11. 실무 적용

이 예제의 CLI flag는 교육용 local 입력입니다. 운영 환경에서는 단계별 승인을 인증된 사람의 identity, immutable approval record, scope, timestamp, expiration과 연결해야 합니다. Coordinator, Worker, DevOps에는 최소 권한을 부여하고, external tool 또는 deployment가 필요한 경로는 별도 policy enforcement point에서 다시 검증해야 합니다.

> [!WARNING]
> `completed`는 이 예제에서 deterministic local workflow가 완료되었다는 뜻입니다. API 호출, 파일 변경, tool execution, message sending, deployment가 성공했다는 의미가 아닙니다.

## 12. 과제

- **기본:** 네 stage 중 하나만 승인했을 때의 정확한 CLI output을 테스트로 추가합니다.
- **응용:** `REJECTED` approval enum을 전달하는 별도 local test helper를 만들고 Agent call이 0회인지 확인합니다.
- **심화:** approval decision의 scope가 review, delegation, conflict, release 중 하나와만 일치하도록 immutable data model을 설계합니다. live identity provider나 deployment는 연결하지 않습니다.

## 13. 완료 체크리스트

- [ ] 네 workflow가 모두 local deterministic Mock만 사용함을 확인했다.
- [ ] 각 stage가 bounded loop 또는 bounded task/attempt를 가짐을 확인했다.
- [ ] approval flag가 해당 stage에만 적용됨을 설명할 수 있다.
- [ ] 승인 없는 실행에서 gated 역할이 실행되지 않음을 확인했다.
- [ ] local handoff note가 deployment가 아님을 설명할 수 있다.
- [ ] `tests/volume07/test_offline_multi_agent_mini_project.py`를 통과시켰다.

## 14. 핵심 정리

Multi-Agent 시스템은 역할을 많이 연결하는 것만으로 안전해지지 않습니다. 역할별 deterministic Mock, 유한한 호출 예산, stage별 명시적 사람 승인, audit 가능한 local 결과를 함께 사용해야 합니다. 이 미니 프로젝트는 그 네 경계를 live API나 deployment 없이 재현합니다.
