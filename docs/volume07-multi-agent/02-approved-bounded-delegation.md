# 02. 승인 게이트가 있는 유한 위임

## 1. 학습 목표

이 장에서는 Coordinator가 작업 계획을 제안하는 일과 Worker가 그 계획을 실행하는 일을 분리합니다. 학습을 마치면 다음을 할 수 있어야 합니다.

- `DelegationPlan`과 immutable `DelegationTask` tuple로 검토 가능한 유한 manifest를 구성할 수 있다.
- Coordinator의 계획 제안과 Worker 실행 사이에 명시적인 사람 승인 gate를 둘 수 있다.
- `max_tasks`와 `max_worker_attempts`로 작업 수와 retry 호출 예산을 제한할 수 있다.
- `PENDING`, `APPROVED`, `REJECTED`에서 Coordinator와 Worker의 호출 여부를 구분할 수 있다.
- deterministic Mock의 고정 tuple script로 network, API key, tool, deployment 없이 위임 workflow를 재현할 수 있다.

## 2. 왜 필요한가

한 Agent가 여러 하위 작업을 제안했다고 해서 그 작업을 바로 실행해도 된다는 뜻은 아닙니다. 예를 들어 Coordinator가 `writer`와 `checker`에게 일을 나누더라도, 사람은 작업 지시문, 담당자, 실행 개수, 예상 영향 범위를 먼저 검토할 수 있어야 합니다. 계획 생성과 실행을 같은 호출에 섞으면 무엇을 승인했는지 audit trail에서 알기 어렵습니다.

또한 실패한 Worker를 제한 없이 재시도하면 비용과 실행 시간이 계속 증가할 수 있습니다. 이 예제는 작업 개수를 `max_tasks`로, task별 시도를 `max_worker_attempts`로 제한합니다. 한 task가 모든 시도에서 실패하면 다음 task를 추측해서 실행하지 않고 `worker_retry_limit_reached`로 fail-closed합니다.

이 장의 `completed`는 deterministic local Worker의 고정 응답이 모두 audit trail에 기록되었다는 뜻입니다. 파일 변경, tool 실행, API 호출, message 발송, release 또는 deployment를 뜻하지 않습니다.

## 3. 핵심 개념

- **Task delegation(작업 위임):** Coordinator가 목적을 작은 `DelegationTask` 집합으로 나누고, allow-list에 있는 Worker에게만 담당을 제안하는 방식입니다.
- **DelegationPlan:** 비어 있지 않은 `summary`와 immutable non-empty `tasks` tuple을 가진 검토 대상 manifest입니다. plan의 생성은 Worker 실행 권한이 아닙니다.
- **DelegationTask:** `task_id`, `assignee`, `instruction`을 가진 하나의 bounded assignment입니다. task ID는 manifest 안에서 고유해야 합니다.
- **DelegationContext:** `objective`, 앞선 immutable `messages`, 현재 `task`, `attempt`를 Coordinator 또는 Worker에 전달합니다. 이전 message text가 tool capability나 사람 승인 권한을 전달하지는 않습니다.
- **Human approval:** `DelegationApproval.PENDING`은 Coordinator audit만 남기고 pause합니다. `APPROVED`일 때만 manifest에 있는 Worker가 순서대로 호출됩니다. `REJECTED`는 모든 Agent 호출 전에 종료합니다.
- **Bounded retry:** task 하나는 `max_worker_attempts` 양의 정수만큼만 시도합니다. 실패 응답도 audit에 기록되지만, 한도를 소진하면 이후 task는 dispatch하지 않습니다.
- **Deterministic Mock:** `DeterministicMockCoordinator`와 `DeterministicMockWorker`는 immutable non-empty plan/response tuple을 호출 순서대로 소비합니다. script가 소진되면 fallback 없이 `AgentProtocolError`를 발생시킵니다.

> [!WARNING]
> `DelegationApproval.APPROVED`는 교육용 local run의 명시 input입니다. 운영 환경의 승인자 identity, 업무 범위, artifact version, timestamp, expiration, immutable approval record 또는 실제 Worker/tool 권한을 대체하지 않습니다.

## 4. 동작 구조

```text
local objective
      |
      v
Coordinator -> validate immutable DelegationPlan -> manifest audit
                                                  |
                         REJECTED ---------------> human_rejected
                         PENDING ----------------> awaiting_human_approval
                         APPROVED ---------------> task 1 Worker attempt 1
                                                           |
                                      succeeded -----------+--> next manifest task
                                      failed -------------> attempt < max_worker_attempts ?
                                                               | yes
                                                               +----> same Worker, next attempt
                                                               | no
                                                               +----> worker_retry_limit_reached
                                                                              |
                                                                              +--> later tasks do not run
```

`max_tasks`는 Coordinator가 제안할 수 있는 task 수의 상한입니다. `max_worker_attempts`는 **각** manifest task의 호출 상한입니다. `PENDING`에서는 manifest가 audit message로 남아 사람이 검토할 수 있지만 Worker loop는 시작하지 않습니다. `REJECTED`에서는 Coordinator도 호출하지 않으므로 검토할 새 manifest도 만들지 않습니다.

## 5. 실습 환경

- Python 3.12 이상과 repository의 `uv` environment가 필요합니다.
- 실행 위치는 저장소 루트(`ai-platform-engineering-book-volume-07`)의 Git Bash 또는 WSL Bash입니다.
- 예제 파일은 `examples/volume07/offline_approved_delegation.py`입니다.
- 구현 파일은 `src/ai_platform/agents/delegation.py`이며 테스트 파일은 `tests/volume07/test_approval_gated_delegation.py`입니다.
- 이 실습은 repository-local package와 deterministic Mock만 사용합니다. live API, network Agent, secret, environment lookup, tool executor, file mutation, deployment를 사용하지 않습니다.

Windows Git Bash에서 repository가 `E:\python\ai-platform-engineering-book-volume-07`에 있다면 다음처럼 이동합니다.

```bash
# 실행 위치: Git Bash 또는 WSL Bash
cd /e/python/ai-platform-engineering-book-volume-07
```

이 명령은 실습의 기준 directory를 설정합니다. 이후 `uv run` 명령은 project package와 example을 이 위치에서 실행합니다.

## 6. 단계별 실습

### 6.1 승인 없이 검토용 manifest 만들기

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run python examples/volume07/offline_approved_delegation.py
```

이 명령은 Coordinator의 한 번의 local plan 제안만 실행합니다. `--approve`가 없으므로 `writer`와 `checker` Worker는 호출되지 않고, workflow는 `awaiting_human_approval`에서 멈춥니다. 출력의 assignment를 보고 사람은 task ID, 담당자, 지시문 범위를 검토할 수 있습니다.

### 6.2 manifest를 명시적으로 승인한 local demonstration

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run python examples/volume07/offline_approved_delegation.py --approve
```

`--approve`는 이 한 번의 교육용 CLI run에 `DelegationApproval.APPROVED`를 전달합니다. 이 예제의 immutable manifest에는 `draft->writer`, `verify->checker`만 있으므로 그 두 local Worker만 manifest 순서로 한 번씩 실행됩니다. API, subprocess, file writer, deployment client는 호출하지 않습니다.

### 6.3 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run pytest tests/volume07/test_approval_gated_delegation.py -q
```

이 명령은 승인 gate, rejection, manifest validation, bounded retry, retry limit 뒤의 task 중단, malformed input/output, script exhaustion을 local Mock으로 검증합니다. 정상적으로 끝나면 pytest가 passed test 수를 출력합니다.

## 7. 코드 설명

예제의 `build_workflow()`는 Coordinator에 한 개의 immutable plan tuple을, 각 Worker에 한 개의 immutable response tuple을 전달합니다.

```python
coordinator = DeterministicMockCoordinator(
    plans=(
        DelegationPlan(
            "Prepare the tutorial with a bounded local handoff.",
            (
                DelegationTask("draft", "writer", "Write the deterministic example."),
                DelegationTask("verify", "checker", "Check the example output."),
            ),
        ),
    )
)
```

`ApprovalGatedDelegationWorkflow` 생성자는 Coordinator의 `propose(context)`와 Worker의 `act(context)`가 callable인지 먼저 확인합니다. `allowed_assignees`는 mutable set이 아닌 non-empty `frozenset`이어야 하며, `workers` mapping은 allow-list의 각 assignee에 정확히 하나의 Worker를 가져야 합니다. role을 선언하는 deterministic Worker는 mapping key와 같은 role이어야 합니다.

`run()`의 핵심 순서는 다음과 같습니다.

1. `objective`와 `human_approval` type을 검사합니다. `REJECTED`이면 Coordinator와 Worker를 호출하지 않고 `human_rejected` result를 반환합니다.
2. Coordinator가 반환한 plan의 type, summary, immutable task tuple, task count, 고유 ID, instruction, assignee allow-list를 검사합니다.
3. 검증한 manifest만 `DelegationMessage("coordinator", ...)`로 audit trail에 추가합니다.
4. approval이 `PENDING`이면 Worker loop보다 먼저 `awaiting_human_approval` result를 반환합니다.
5. approval이 `APPROVED`이면 manifest 순서대로 Worker를 호출하고, 매 response의 non-empty content와 boolean `succeeded`를 audit 기록 전에 검사합니다.
6. 성공한 task ID만 `completed_task_ids`에 추가합니다. task가 모든 retry를 실패하면 `worker_retry_limit_reached`를 반환하고 이후 task에는 진행하지 않습니다.

`DelegationContext.messages`와 `DelegationPlan.tasks`는 tuple입니다. 따라서 이전 audit history나 승인 전 manifest의 task 목록을 local Worker가 수정해 실행 범위를 바꾸는 경로가 없습니다.

## 8. 정상 실행 결과

승인 없이 실행한 실제 예제의 출력 형태는 다음과 같습니다.

```text
status=awaiting_human_approval
completed_task_ids=-
0:coordinator:-: Prepare the tutorial with a bounded local handoff. Assignments: draft->writer, verify->checker.
```

`writer` 또는 `checker` message가 없다는 점이 중요합니다. Coordinator가 두 assignment를 제안했더라도 `PENDING`에서는 Worker가 호출되지 않습니다.

`--approve`를 전달하면 다음처럼 local Worker message가 manifest 순서로 추가됩니다.

```text
status=completed
completed_task_ids=draft,verify
0:coordinator:-: Prepare the tutorial with a bounded local handoff. Assignments: draft->writer, verify->checker.
1:writer:draft: Draft is ready.
1:checker:verify: Checks passed.
```

여기서 `completed`는 두 고정 Worker response가 audit trail에 기록되었다는 결과일 뿐입니다. `writer`와 `checker`는 text를 반환하는 local Mock이며 실제 문서 작성, test 실행, release, deployment를 수행하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `ModuleNotFoundError: ai_platform` | 저장소 root 밖에서 Python을 직접 실행했거나 source package가 path에 없음 | 저장소 root로 이동한 뒤 `uv run python examples/volume07/offline_approved_delegation.py`를 실행합니다. |
| `status=awaiting_human_approval` | `--approve`가 없어서 정상적으로 manifest gate에 pause함 | Coordinator audit를 검토합니다. 교육용 completed 경로가 필요할 때만 `--approve`를 전달합니다. |
| `worker_retry_limit_reached` | 하나의 Worker가 configured attempts 안에서 모두 `succeeded=False`를 반환함 | `max_worker_attempts`와 response script 길이를 함께 점검합니다. 이후 task를 자동 실행하거나 성공으로 추측하지 않습니다. |
| `WorkflowConfigurationError` | empty objective, non-positive bound, mutable allow-list, malformed fixed plan/response script 또는 non-callable boundary를 구성함 | objective, positive integer, `frozenset`, immutable tuple, required fields, role binding을 확인합니다. |
| `AgentProtocolError` | runtime plan/Worker output이 contract를 위반했거나 fixed script가 소진됨 | plan type/task fields와 Worker `content`/`succeeded`, configured call budget을 수정합니다. 다음 Worker나 fallback을 호출하지 마십시오. |
| pending 상태에서 Worker가 실행됨 | orchestrator가 human gate보다 먼저 Worker loop에 진입하도록 변경됨 | `PENDING` return이 Worker loop보다 앞에 있는지 확인하고 `test_pending_approval_records_a_manifest_but_never_calls_workers`를 실행합니다. |

## 10. 응용 실습

1. `writer` response를 첫 번째 `succeeded=False`, 두 번째 `succeeded=True`로 구성하고 `max_worker_attempts=2`에서 retry context의 `attempt`가 `1`, `2`인지 test로 확인합니다.
2. 두 번 모두 실패하는 `writer` script를 구성하고 `checker.calls == []`인지 확인합니다. 실패한 앞 task가 뒤 task를 열지 않는 이유를 설명합니다.
3. Coordinator가 allow-list 밖 assignee를 포함한 plan을 반환하는 local adapter를 만들고, 어떤 Worker도 호출되기 전에 `AgentProtocolError`가 나는지 test로 고정합니다.
4. 동일 task ID가 두 번 있는 fixed plan이 Mock 구성 단계에서 거절되는지 확인합니다.

이 실습도 deterministic local fixture만 사용해야 합니다. API client, subprocess tool, file writer, deployment adapter를 추가하지 마십시오.

## 11. 실무 적용

운영 위임 시스템에서는 계획 검토와 실제 권한 행사를 별도 통제로 유지해야 합니다.

- Coordinator는 구조화된 manifest를 만들지만 tool handle이나 Worker credential을 받지 않습니다.
- approval service는 approver identity, request scope, task manifest hash, timestamp, expiration, revocation을 별도 record로 검증합니다.
- dispatcher는 승인 record의 manifest와 현재 실행 manifest가 같은지, assignee가 policy allow-list에 있는지 다시 확인합니다.
- Worker retry policy는 task별 budget, timeout, retryable failure 조건, cancellation을 명시하고 무한 retry를 허용하지 않습니다.
- audit log에는 task ID, role, attempt, bounded status를 기록하되 API key, secret, 개인정보, unrestricted tool handle을 기록하지 않습니다.

> [!TIP]
> `awaiting_human_approval`은 Router의 자동 retry 또는 다른 Worker로의 자동 fallback 신호가 아닙니다. 사람이 별도 결정을 제공할 때까지 실행을 멈추는 stop condition입니다.

## 12. 과제

### 기본

- `PENDING`, `APPROVED`, `REJECTED` 각각에서 Coordinator와 Worker가 호출되는지, result status가 무엇인지 표로 정리합니다.
- plan proposal과 Worker execution을 분리해야 하는 이유를 설명합니다.

### 응용

- `max_worker_attempts=2`와 두 번의 failed response로 `worker_retry_limit_reached`를 재현하는 test를 작성합니다.
- empty objective가 Coordinator 호출 전에 거절됨을 call history assertion으로 보입니다.

### 심화

- 운영용 immutable delegation approval record schema를 설계합니다. request ID, manifest hash, scope, approver identity reference, issued timestamp, expiration, decision을 포함하되 실제 identity provider 또는 tool executor는 연결하지 않습니다.
- manifest validation failure, Worker protocol failure, retry-limit result를 서로 다른 observability event로 남기는 설계를 제안합니다. secret 또는 raw credential은 event에 포함하지 않습니다.

## 13. 완료 체크리스트

- [ ] Coordinator, manifest, Worker의 역할과 호출 순서를 설명할 수 있다.
- [ ] `DelegationPlan.tasks`와 `DelegationContext.messages`가 immutable tuple인 이유를 설명할 수 있다.
- [ ] `PENDING` 기본 실행에서 Coordinator만 호출되고 Worker가 호출되지 않았음을 확인했다.
- [ ] `--approve` local run에서 manifest 안의 Worker만 순서대로 호출되는 것을 확인했다.
- [ ] `max_tasks`와 `max_worker_attempts`가 각각 다른 호출 상한임을 설명할 수 있다.
- [ ] retry 한도에 도달하면 이후 task를 실행하지 않고 fail-closed한다는 것을 확인했다.
- [ ] `uv run pytest tests/volume07/test_approval_gated_delegation.py -q`를 통과시켰다.
- [ ] 이 예제에 live API, secret, tool execution, file mutation, deployment가 없음을 확인했다.

## 14. 핵심 정리

안전한 Multi-Agent delegation workflow는 Coordinator가 task를 나누는 것만으로 완성되지 않습니다. 계획은 immutable manifest로 검증하고 audit에 남겨야 하며, 실제 Worker dispatch는 명시적인 사람 승인 뒤에만 시작해야 합니다. 작업 수와 retry에는 독립적인 유한 상한이 필요하고, 한 task가 실패하면 이후 task의 성공을 추측하거나 fallback Worker를 실행해서는 안 됩니다. 이 장의 deterministic Mock 예제는 이러한 계약을 외부 capability 없이 재현하고, input 또는 protocol이 맞지 않으면 다음 역할 호출 전에 fail-closed합니다.
