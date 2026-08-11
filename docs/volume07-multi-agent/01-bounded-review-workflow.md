# 01. 결정론적 다중 에이전트 검토 워크플로

## 1. 학습 목표

이 장에서는 Planner, Researcher, Developer, Reviewer, QA의 역할을 하나의 자동 권한으로 취급하지 않고, 검증 가능한 순서로 연결합니다. 학습을 마치면 다음을 할 수 있어야 합니다.

- 역할별 입력과 결과를 immutable audit message로 전달할 수 있다.
- Reviewer의 `APPROVE`와 사람의 QA 승인 권한이 서로 다름을 설명할 수 있다.
- `max_review_cycles`로 Developer/Reviewer 재작업 loop를 유한하게 제한할 수 있다.
- `PENDING`, `APPROVED`, `REJECTED`에서 호출되는 역할과 멈추는 상태를 확인할 수 있다.
- 고정 tuple script를 쓰는 deterministic Mock으로 network, API key, tool 없이 workflow를 재현할 수 있다.

## 2. 왜 필요한가

여러 역할이 같은 task를 처리할 때 Reviewer가 초안을 승인했다고 해서 QA를 시작하거나 외부 작업을 진행해도 된다는 뜻은 아닙니다. Reviewer는 품질 판단을 담당하고, 사람은 다음 단계 진행 여부를 판단합니다. 두 결정을 하나의 boolean이나 Agent message로 합치면 권한의 출처를 추적하기 어렵습니다.

또한 Reviewer가 계속 수정을 요청하면 Developer와 Reviewer가 끝없이 왕복할 수 있습니다. 예제는 `max_review_cycles`라는 호출 예산을 두어 이 문제를 막습니다. 예산 안에서 승인되지 않으면 추측한 결과를 만들지 않고 `review_limit_reached`로 종료합니다.

이 장의 workflow는 학습용 local orchestration입니다. QA Mock의 `completed`는 deterministic local QA message가 만들어졌다는 뜻일 뿐이며, API 호출, 파일 변경, tool 실행, message 발송, deployment를 의미하지 않습니다.

## 3. 핵심 개념

- **Agent role(역할):** Planner는 계획, Researcher는 local evidence, Developer는 초안, Reviewer는 `ReviewDecision`, QA는 승인된 초안의 local check를 담당합니다.
- **AgentContext:** 현재 `task`, `iteration`, 이전 `messages`를 immutable 값으로 전달합니다. 이전 역할의 text가 다음 역할에 전달되더라도 tool capability나 사람 승인 권한은 전달되지 않습니다.
- **AgentResponse:** 비어 있지 않은 `content`와 선택적인 `review`로 구성된 role output입니다. runtime output의 type과 content는 audit trail에 추가되기 전에 검사됩니다.
- **Reviewer authority:** `ReviewDecision.APPROVE` 또는 `ReviewDecision.REVISE`는 Reviewer만 반환할 수 있습니다. Reviewer가 아닌 역할의 review 값과 Reviewer의 결정 누락은 `AgentProtocolError`로 fail-closed합니다.
- **Human approval:** `HumanApproval.PENDING`이면 Reviewer 승인 뒤에 pause하고 QA를 호출하지 않습니다. `APPROVED`일 때만 QA가 호출됩니다. `REJECTED`는 모든 역할 호출 전에 종료합니다.
- **Bounded loop:** `max_review_cycles`는 양의 정수입니다. Developer/Reviewer pair는 그 값보다 많이 호출되지 않습니다.
- **Deterministic Mock:** `DeterministicMockAgent`는 immutable non-empty response tuple을 호출 순서대로 한 항목씩 소비합니다. script가 소진되면 fallback 없이 `AgentProtocolError`를 발생시킵니다.

> [!WARNING]
> `HumanApproval.APPROVED`는 이 교육용 local run의 명시 input입니다. 운영 환경의 인증된 승인자 identity, approval scope, timestamp, expiration, immutable approval record 또는 deployment 권한을 대체하지 않습니다.

## 4. 동작 구조

```text
local task
   |
   v
Planner -> Researcher -> Developer -> Reviewer
                                  |       |
                                  |       +-- REVISE --> cycle < max_review_cycles ?
                                  |                          | yes
                                  |                          +----> Developer
                                  |                          | no
                                  |                          +----> review_limit_reached
                                  |
                                  +-- APPROVE --> human approval gate
                                                       |
                         PENDING ----------------------+--> awaiting_human_approval
                         REJECTED ---------------------> human_rejected (before all roles)
                         APPROVED ---------------------> QA --> completed
```

Planner와 Researcher는 각 run에서 한 번만 호출됩니다. Developer와 Reviewer는 같은 cycle 번호를 공유하며, 최대 `max_review_cycles` pair만 실행합니다. `PENDING` 경로는 Reviewer의 approved audit message까지 보존하므로 사람이 무엇을 승인할지 검토할 수 있지만 QA 호출 권한은 만들지 않습니다.

## 5. 실습 환경

- Python 3.12 이상과 repository의 `uv` environment가 필요합니다.
- 실행 위치는 저장소 루트(`ai-platform-engineering-book-volume-07`)의 Git Bash 또는 WSL Bash입니다.
- 예제 파일은 `examples/volume07/offline_review_workflow.py`입니다.
- 구현 파일은 `src/ai_platform/agents/workflow.py`이며 테스트 파일은 `tests/volume07/test_bounded_review_workflow.py`입니다.
- 이 실습은 standard library와 repository-local package만 사용합니다. live API, network Agent, secret, environment lookup, tool executor, file mutation, deployment를 사용하지 않습니다.

Windows Git Bash에서 repository가 `E:\python\ai-platform-engineering-book-volume-07`에 있다면 다음처럼 이동합니다.

```bash
# 실행 위치: Git Bash 또는 WSL Bash
cd /e/python/ai-platform-engineering-book-volume-07
```

이 명령은 실습의 기준 directory를 설정합니다. `uv run`은 이 위치에서 project package와 example을 실행합니다.

## 6. 단계별 실습

### 6.1 승인 없이 reviewer audit까지 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run python examples/volume07/offline_review_workflow.py
```

이 명령은 Planner, Researcher, Developer, Reviewer의 고정 local response를 한 번씩 기록합니다. `--approve`를 전달하지 않았으므로 QA Mock은 호출되지 않고 workflow는 `awaiting_human_approval`로 멈춥니다.

### 6.2 사람이 QA 진행을 명시적으로 승인한 local demonstration

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run python examples/volume07/offline_review_workflow.py --approve
```

`--approve`는 이 한 번의 교육용 CLI run에 `HumanApproval.APPROVED`를 전달합니다. Reviewer의 품질 승인 뒤에만 QA Mock이 실행되며, external system은 호출하지 않습니다.

### 6.3 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run pytest tests/volume07/test_bounded_review_workflow.py -q
```

이 명령은 approval gate, rejection, review-cycle bound, malformed input/output, script exhaustion을 local Mock으로 검증합니다. 정상적으로 끝나면 pytest가 passed test 수를 출력합니다.

## 7. 코드 설명

예제의 `build_workflow()`는 각각 한 role label과 immutable response tuple을 가진 Mock을 구성합니다.

```python
reviewer=mock_agent(
    "reviewer",
    AgentResponse("Review: acceptance criteria are met.", ReviewDecision.APPROVE),
),
qa=mock_agent("qa", AgentResponse("QA: deterministic checks passed.")),
max_review_cycles=2,
```

`DeterministicMockAgent`는 response tuple을 바꾸지 않고 call index로 다음 응답을 선택합니다. 예상보다 많은 호출은 응답을 추측하지 않고 오류를 발생시키므로, test가 의도하지 않은 loop를 숨기지 않습니다.

`BoundedReviewWorkflow.run()`의 핵심 순서는 다음과 같습니다.

1. `task`와 `human_approval` type을 검사합니다. `REJECTED`이면 즉시 `human_rejected` result를 반환합니다.
2. Planner와 Researcher output을 검사한 뒤 immutable `AgentMessage`로 audit trail에 추가합니다.
3. cycle마다 Developer output과 Reviewer output을 검사합니다. Reviewer만 명시적인 `APPROVE` 또는 `REVISE`를 반환할 수 있습니다.
4. `REVISE`면 남은 review budget 안에서 다음 cycle을 시작합니다. budget을 모두 사용하면 QA 없이 `review_limit_reached`를 반환합니다.
5. Reviewer가 `APPROVE`했지만 approval이 `PENDING`이면 QA보다 먼저 `awaiting_human_approval` result를 반환합니다.
6. approval이 `APPROVED`인 경우에만 QA output을 검사하고 `completed`를 반환합니다.

`AgentContext.messages`는 tuple입니다. 따라서 한 role이 받은 과거 audit history를 local Mock이 수정해 다음 role의 context를 바꾸는 경로가 없습니다.

## 8. 정상 실행 결과

승인 없이 실행한 실제 예제의 출력 형태는 다음과 같습니다.

```text
status=awaiting_human_approval
review_cycles=1
0:planner: Plan: define the offline acceptance criteria.
0:researcher: Evidence: use only repository-local fixtures.
1:developer: Draft: bounded workflow implementation.
1:reviewer: Review: acceptance criteria are met.
```

QA line이 없다는 점이 중요합니다. Reviewer의 `APPROVE`가 있어도 `PENDING`에서는 QA가 호출되지 않습니다.

`--approve`를 전달하면 첫 두 줄과 앞의 four audit messages는 같고 마지막에 다음 line이 추가됩니다.

```text
status=completed
1:qa: QA: deterministic checks passed.
```

`completed`는 local QA Mock 응답이 audit trail에 추가되었다는 결과입니다. deployment 또는 external release success가 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `ModuleNotFoundError: ai_platform` | 저장소 root 밖에서 Python을 직접 실행했거나 source package가 path에 없음 | 저장소 root로 이동한 뒤 `uv run python examples/volume07/offline_review_workflow.py`를 실행합니다. |
| `status=awaiting_human_approval` | `--approve`가 없어서 정상적으로 QA gate에 pause함 | Reviewer audit를 확인한 뒤 교육용 completed 경로가 필요할 때만 `--approve`를 전달합니다. |
| `review_limit_reached` | Reviewer가 모든 configured cycle에서 `REVISE`를 반환함 | `max_review_cycles`와 response script 길이를 함께 점검합니다. QA를 자동 fallback으로 호출하지 않습니다. |
| `WorkflowConfigurationError` | empty task, non-positive cycle bound, non-callable boundary, mutable/invalid Mock script를 구성함 | task, positive integer, role boundary, immutable tuple과 response field를 확인합니다. |
| `AgentProtocolError` | runtime response가 `AgentResponse` contract를 위반했거나 script가 소진됨 | content, review enum, role authority, configured call budget을 수정합니다. 다음 role이나 fallback을 호출하지 마십시오. |
| QA가 예상보다 일찍 실행됨 | orchestrator가 human gate보다 앞서 QA를 호출하도록 변경됨 | `PENDING` return이 QA call보다 앞에 있는지 확인하고 `test_approved_review_pauses_for_human_approval_without_running_qa`를 실행합니다. |

## 10. 응용 실습

1. Reviewer script를 `REVISE`, `APPROVE` 두 응답으로 구성하고 `max_review_cycles=2`에서 Developer/Reviewer가 두 번, QA가 승인 뒤 한 번 호출되는 test를 작성합니다.
2. Reviewer가 아닌 Planner Mock에 `ReviewDecision.APPROVE`를 넣고, Researcher가 호출되기 전에 `AgentProtocolError`가 발생하는지 확인합니다.
3. QA Mock script를 한 response만 가진 상태에서 workflow를 두 번 실행하지 말고, run마다 새 Mock을 만드는 이유를 설명합니다.
4. `REJECTED` local input을 전달하고 모든 role의 `calls` list가 빈 상태인지 test로 고정합니다.

이 실습도 deterministic local fixture만 사용해야 합니다. API client, subprocess tool, file writer, deployment adapter를 추가하지 마십시오.

## 11. 실무 적용

운영 workflow에서는 Reviewer 판단과 사람 승인을 서로 다른 책임으로 유지해야 합니다.

- Reviewer output은 schema와 role authority를 검증하고 immutable audit event로 남깁니다.
- approval service는 approver identity, request scope, artifact version, timestamp, expiration, revocation을 별도로 확인합니다.
- QA 또는 tool executor는 approval record와 현재 artifact가 일치하는지 다시 확인합니다.
- retry policy는 role별 call budget, timeout, retryable failure를 명시하고 무한 retry를 허용하지 않습니다.
- audit log에는 approval decision과 bounded status를 남기되 API key, secret, 개인정보, unrestricted tool handle을 기록하지 않습니다.

> [!TIP]
> approval이 필요한 상태는 자동 retry 또는 Router fallback의 대상이 아닙니다. `awaiting_human_approval`은 사람이 별도 결정할 때까지의 stop condition입니다.

## 12. 과제

### 기본

- `PENDING`, `APPROVED`, `REJECTED` 각각에서 호출되는 role 목록과 terminal status를 표로 정리합니다.
- `ReviewDecision.APPROVE`와 `HumanApproval.APPROVED`가 다른 이유를 설명합니다.

### 응용

- `max_review_cycles=2`와 두 번의 `REVISE` script로 `review_limit_reached`를 재현하는 test를 작성합니다.
- empty task가 Planner 호출 전에 거절됨을 call history assertion으로 보입니다.

### 심화

- 운영용 immutable approval record schema를 설계합니다. request/artifact identifier, scope, approver identity reference, issued timestamp, expiration, decision을 포함하되 actual identity provider나 external deployment는 연결하지 않습니다.
- role output schema failure와 human rejection을 서로 다른 observability event로 남기는 설계를 제안합니다. secret 또는 raw credential은 event에 포함하지 않습니다.

## 13. 완료 체크리스트

- [ ] Planner, Researcher, Developer, Reviewer, QA의 역할과 순서를 설명할 수 있다.
- [ ] `AgentContext`와 immutable audit message가 message passing에 쓰이는 이유를 설명할 수 있다.
- [ ] Reviewer의 approval이 QA 사람 승인이 아님을 설명할 수 있다.
- [ ] 기본 실행에서 QA가 호출되지 않고 `awaiting_human_approval`으로 멈춘 것을 확인했다.
- [ ] `--approve`가 있는 local run에서만 QA가 호출되는 것을 확인했다.
- [ ] `max_review_cycles`가 무한 loop를 막고 limit 도달 시 fail-closed한다는 것을 확인했다.
- [ ] `uv run pytest tests/volume07/test_bounded_review_workflow.py -q`를 통과시켰다.
- [ ] 이 예제에 live API, secret, tool execution, file mutation, deployment가 없음을 확인했다.

## 14. 핵심 정리

안전한 Multi-Agent review workflow는 역할을 순서대로 호출하는 것만으로 완성되지 않습니다. 각 role output을 검증하고 immutable audit message로 전달해야 하며, loop에는 명시적인 상한이 필요합니다. Reviewer의 품질 판단 뒤에도 QA 같은 다음 단계는 별도의 사람 승인 gate로 분리해야 합니다. 이 장의 deterministic Mock 예제는 그 계약을 외부 capability 없이 재현하고, 입력 또는 protocol이 맞지 않으면 fallback 없이 fail-closed합니다.
