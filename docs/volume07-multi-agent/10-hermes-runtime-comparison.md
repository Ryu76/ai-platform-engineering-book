# 10. Hermes Agent Runtime과 직접 구현 비교

## 1. 학습 목표

이 장에서는 Volume 07의 결정론적 로컬 Multi-Agent workflow와 Hermes Agent runtime의 책임을 구분합니다. 이 장을 마치면 다음을 할 수 있어야 합니다.

- `AgentContext`, `AgentResponse`, immutable audit message가 local workflow에서 맡는 역할을 설명할 수 있다.
- `DeterministicMockAgent`와 고정 tuple script가 재현 가능한 학습 fixture인 이유를 설명할 수 있다.
- role 이름, message text, `completed` 상태가 tool·network·deployment 권한이나 운영 승인을 뜻하지 않음을 구분할 수 있다.
- bounded loop, fail-closed protocol 검증, 명시적 `PENDING`/`APPROVED`/`REJECTED` human approval을 runtime 선택과 분리할 수 있다.
- Hermes를 실제로 설정하기 전 확인할 공식 문서와 최소 권한 검토 항목을 식별할 수 있다.

> [!WARNING]
> 이 장의 실습은 Hermes를 실행·설정·수정하지 않습니다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 사용하지 않는 local deterministic Mock만 실행합니다. `completed`는 local workflow 결과일 뿐 운영 승인이나 외부 변경이 아닙니다.

## 2. 왜 필요한가

작은 직접 구현은 Agent 역할 순서, 입력·출력 schema, 종료 조건을 코드와 test에서 확인하기 쉽습니다. 반면 Hermes Agent runtime은 prompt 구성, provider 선택, tool registry, session, memory처럼 더 넓은 실행 환경을 연결할 수 있습니다.

runtime을 도입해도 다음 설계 책임은 자동으로 해결되지 않습니다.

1. 어떤 role이 어떤 판단을 할 수 있는가
2. 어떤 output schema만 다음 role로 전달되는가
3. retry와 반복이 어느 수치 상한에서 끝나는가
4. 어떤 단계가 사람의 명시적 결정을 기다리는가
5. memory와 tool이 읽거나 변경할 수 있는 범위는 무엇인가

따라서 먼저 local Mock으로 안전 계약을 재현하고, Hermes를 도입할 때 같은 계약을 runtime 설정과 운영 정책에서 별도로 확인해야 합니다.

## 3. 핵심 개념

**직접 구현 workflow**는 `src/ai_platform/agents/`의 작은 orchestration code입니다. `AgentContext`는 한 호출의 task, iteration, immutable messages를 전달합니다. `AgentResponse`는 검증된 content와 Reviewer 전용 `ReviewDecision`을 전달합니다. Mock은 fixed tuple script만 소비하며 script가 소진되면 fallback 없이 `AgentProtocolError`로 멈춥니다.

**Hermes Agent runtime**은 Agent 실행을 위한 별도 runtime입니다. prompt, provider, tool, session, persistent memory 같은 기능의 실제 동작과 설정은 릴리스에 따라 달라질 수 있습니다. 실제 적용 전에는 다음 공식 문서를 최신 기준으로 확인해야 합니다.

- [Hermes Agent Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
- [Hermes Agent Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
- [Hermes Agent Tools and Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)
- [Hermes Agent Persistent Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [Hermes Agent Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)

**authority와 capability**는 다릅니다. `reviewer`라는 role label은 review decision의 schema authority를 나타낼 뿐, terminal·browser·deployment capability를 주지 않습니다. 반대로 toolset이 있다고 해서 업무상 release approval을 얻는 것도 아닙니다.

**human approval**도 두 층으로 나뉩니다. Volume 07의 enum은 학습용 local gate입니다. 운영 환경에서는 approver identity, 대상과 scope, timestamp, expiration, immutable audit record를 별도 승인 시스템에서 확인해야 합니다.

## 4. 동작 구조

```text
local request
    |
    v
+-----------------------------------------------+
| Volume 07 direct implementation               |
| AgentContext -> deterministic role boundary   |
| AgentResponse -> schema/role validation       |
| bounded loop -> immutable audit messages      |
+-----------------------------------------------+
    |                    |                  |
    |                    |                  +--> protocol/limit failure
    |                    |                        (fail closed)
    |                    +--> awaiting_human_approval
    |                              |
    |                              v
    |                    explicit local human decision
    v
completed (local result only)

Hermes runtime, when separately adopted
    |
    +--> prompt / provider / session / memory / tool policy
              each requires its own least-privilege and approval review
```

위 구조에서 local message는 data입니다. message text가 Hermes tool handle, API key, mutable script, deployment 권한을 전달하지는 않습니다. Hermes runtime을 사용하더라도 workflow의 stop condition과 human gate는 명시적으로 유지해야 합니다.

## 5. 실습 환경

이 장의 명령은 저장소 루트에서 Git Bash 또는 WSL Bash로 실행합니다. Windows 경로의 예시는 `E:\python\ai-platform-engineering-book-volume-07`이고 Git Bash에서는 `/e/python/ai-platform-engineering-book-volume-07`입니다.

필요한 것은 이 저장소의 Python 환경과 `uv`뿐입니다. Hermes profile, `~/.hermes/`, provider credential, API key는 읽거나 변경하지 않습니다.

```bash
# 실행 위치: Git Bash 또는 WSL Bash, 저장소 루트
cd /e/python/ai-platform-engineering-book-volume-07
uv run python examples/volume07/offline_multi_agent_mini_project.py
```

명령은 네 local workflow를 구성하고 approval flag 없이 실행합니다. 따라서 gated QA, Worker, DevOps는 호출되지 않습니다.

## 6. 단계별 실습

### 6.1 기본 pause를 실행한다

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume07/offline_multi_agent_mini_project.py
```

이 명령의 목적은 review, delegation, conflict, release가 각자의 `PENDING` gate에서 멈추는지 확인하는 것입니다. Hermes command, live API, network endpoint는 호출하지 않습니다.

### 6.2 local approval 경로를 분리해 실행한다

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume07/offline_multi_agent_mini_project.py \
  --approve-review \
  --approve-delegation \
  --approve-conflict \
  --approve-release
```

각 flag는 해당 stage의 학습용 local gate만 엽니다. 이 명령은 local QA message, bounded Worker result, exact consensus completion, local handoff note만 만들며 deployment를 실행하지 않습니다.

### 6.3 workflow contract와 문서 contract를 검증한다

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07/test_offline_multi_agent_mini_project.py \
  tests/volume07/test_hermes_runtime_comparison_documentation.py -q
uv run pytest tests/volume07 -q
```

첫 명령은 CLI의 independent approval flags와 이 장의 PRD section을 빠르게 검증합니다. 두 번째 명령은 Volume 07의 deterministic Mock, bounded loop, role authority, approval-gate regression을 함께 확인합니다.

### 6.4 Hermes 적용 검토를 문서로만 준비한다

실제 Hermes runtime을 이 실습에서 실행하지 마십시오. 운영 적용이 필요한 별도 작업에서 공식 문서를 기준으로 role identity, provider, memory scope, tool allow-list, timeout/retry bound, human approval record를 검토합니다. 이 단계는 설정 변경이나 tool 실행이 아니라 설계 검토입니다.

## 7. 코드 설명

`examples/volume07/offline_multi_agent_mini_project.py`의 builder 함수는 네 workflow에 non-empty immutable tuple script를 주입합니다. `build_review_workflow()`와 `build_release_workflow()`는 `HumanApproval`을, `build_delegation_workflow()`는 `DelegationApproval`을, `build_conflict_workflow()`는 `ConflictApproval`을 각각 사용합니다. enum을 공유 text로 대체하지 않기 때문에 stage 간 approval authority가 섞이지 않습니다.

`BoundedReviewWorkflow`와 `ApprovalGatedReleaseHandoffWorkflow`는 `max_review_cycles`만큼만 Developer/Reviewer pair를 호출합니다. Reviewer 외 role이 review decision을 반환하거나 response schema가 틀리면 audit trail에 추가하기 전에 `AgentProtocolError`로 중단합니다.

`ApprovalGatedDelegationWorkflow`는 Coordinator manifest를 먼저 검증하고 `PENDING`에서는 Worker를 호출하지 않습니다. `APPROVED` 뒤에도 task 수와 `max_worker_attempts`가 call budget을 제한합니다. `BoundedConflictResolutionWorkflow`는 모든 option의 exact equality만 consensus recommendation으로 받아들이고, 다수결이나 fallback으로 winner를 고르지 않습니다.

이 local code는 Hermes adapter가 아닙니다. `DeterministicMock*`에는 provider client, persistent memory writer, tool executor, subprocess, network, deployment capability가 없습니다. Hermes runtime을 연결한다면 별도의 adapter와 separate policy review가 필요합니다.

## 8. 정상 실행 결과

기본 실행의 핵심 출력은 다음과 같습니다.

```text
review_status=awaiting_human_approval
delegation_status=awaiting_human_approval
delegation_completed_task_ids=-
conflict_status=awaiting_human_approval
conflict_consensus_option=offline tutorial
release_status=awaiting_human_approval
release_handoff_note=-
```

네 approval flag를 모두 명시한 local 학습 경로의 핵심 출력은 다음과 같습니다.

```text
review_status=completed
delegation_status=completed
delegation_completed_task_ids=draft,verify
conflict_status=completed
conflict_consensus_option=offline tutorial
release_status=completed
release_handoff_note=Handoff: local release note ready; no deployment ran.
```

여기서 `completed`와 handoff note는 deterministic local result입니다. Hermes provider 호출, tool 실행, 파일 변경, deployment가 발생했다는 증거가 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| 기본 실행이 `completed`가 아님 | approval flag 없이 실행했음 | 정상입니다. `PENDING`은 QA, Worker, DevOps 전에 pause해야 합니다. local completion을 확인할 때만 해당 `--approve-*` flag를 명시합니다. |
| `WorkflowConfigurationError` | role boundary, declared role, fixed tuple script 또는 positive bound가 구성 계약을 위반함 | role label, callable signature, tuple container, non-empty field, positive integer를 확인합니다. Agent를 호출해 우회하지 않습니다. |
| `AgentProtocolError` | runtime response schema가 틀리거나 script가 소진됨 | content, `ReviewDecision`, fixed script call budget을 수정합니다. 다음 role이나 fallback을 호출하지 않아야 합니다. |
| Hermes tool approval을 release approval로 해석함 | command security boundary와 업무 승인 record를 혼동함 | tool permission, business approval, deployment authorization을 서로 다른 policy와 record로 설계합니다. |
| memory 때문에 test 결과가 달라짐 | persistent state와 deterministic fixture를 섞음 | Volume 07 test에는 persistent memory를 연결하지 않습니다. 운영 memory는 scope, writer, retention을 별도 정의합니다. |

## 10. 응용 실습

1. `--approve-review` 하나만 실행하고 review만 `completed`이며 delegation, conflict, release는 `awaiting_human_approval`인지 확인합니다.
2. Reviewer가 두 번 `REVISE`를 반환하는 local tuple fixture를 만들고, configured review bound 뒤 QA와 DevOps가 호출되지 않는 test를 작성합니다.
3. Hermes 적용 전 검토표를 작성합니다. role마다 input/output schema, tool allow-list, timeout, retry limit, stop condition, human approval scope를 한 행에 기록합니다.
4. `completed` local result를 external release permission으로 변환하지 못하도록, approval record에 필요한 identity·scope·expiration field를 별도 data model로 설계합니다.

## 11. 실무 적용

실제 Hermes 기반 workflow에는 다음 순서를 적용합니다.

1. role identity, goal, input/output schema, authority를 정의한다.
2. local deterministic test로 bounded loop와 fail-closed path를 먼저 고정한다.
3. provider와 toolset을 role별 최소 권한 allow-list로 연결한다.
4. provider, tool, session 실패가 implicit retry, fallback, privilege escalation으로 이어지지 않도록 independent upper bound를 둔다.
5. 업무 approval을 authenticated approver, scope, timestamp, expiration, immutable audit record로 검증한다.
6. secret을 prompt, message, memory, audit log에 기록하지 않는다.

> [!TIP]
> Runtime 설정은 구현 세부 사항이고, workflow authority는 설계 계약입니다. Hermes의 feature를 켠 뒤에도 Reviewer가 아닌 role의 review decision, Router의 자동 approval, `PENDING` 상태의 automatic resume은 계속 금지해야 합니다.

## 12. 과제

### 기본

- `AgentContext.messages`가 immutable tuple인 이유와 message text가 capability가 아닌 이유를 설명합니다.
- 네 workflow에서 `PENDING`일 때 호출되지 않는 gated role을 표로 정리합니다.

### 응용

- `APPROVED` enum과 운영 approval record가 다른 이유를 approver identity, scope, expiration 관점에서 작성합니다.
- `max_review_cycles`, `max_worker_attempts`, `max_rounds`의 최대 Agent 호출 횟수를 각 workflow별로 계산해 기록합니다.

### 심화

- Hermes runtime adapter를 별도 package로 설계합니다. deterministic Mock module에 provider client나 tool executor를 import하지 않는 dependency rule을 포함합니다.
- tool-enabled DevOps role의 최소 권한 allow-list와 별도 human approval workflow를 설계합니다. 이 과제에서는 실제 tool, API, deployment를 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] local mini project 기본 실행에서 네 stage가 `awaiting_human_approval`임을 확인했다.
- [ ] stage별 `APPROVED`가 다른 stage의 QA, Worker, DevOps를 열지 않음을 확인했다.
- [ ] fixed tuple script와 bounded loop가 deterministic test fixture를 만드는 이유를 설명할 수 있다.
- [ ] role label과 message text가 tool capability 또는 운영 authority가 아님을 설명할 수 있다.
- [ ] Hermes runtime 적용 전에 최신 공식 Architecture, Configuration, Tools, Memory, Security 문서를 확인할 위치를 안다.
- [ ] human approval enum과 authenticated 운영 approval record를 분리했다.
- [ ] `uv run pytest tests/volume07 -q`를 실행해 Volume 07 regression을 통과했다.
- [ ] live API, secret, network Agent, tool 실행, 파일 변경, deployment를 이 실습에 추가하지 않았다.

## 14. 핵심 정리

Volume 07의 직접 구현은 Hermes runtime을 대체하려는 것이 아닙니다. role boundary, immutable message passing, deterministic Mock, bounded loop, fail-closed validation, explicit human approval을 학습하고 test하는 최소 모델입니다. Hermes를 실제로 사용할 때는 prompt, provider, memory, tool, session의 더 넓은 capability를 별도 정책으로 검토해야 합니다. 어떤 runtime을 사용하더라도 `PENDING`을 자동 승인으로 바꾸지 않고, local `completed`를 external action으로 해석하지 않으며, 권한과 approval을 명시적으로 검증해야 합니다.
