# 03. 유한 충돌 해결과 사람 승인

## 1. 학습 목표

여러 Agent가 서로 다른 선택지를 제안할 때 Orchestrator가 다수결·추측·fallback으로 승자를 고르지 않게 설계합니다. 이 장을 마치면 다음을 할 수 있습니다.

- 역할별 `ConflictProposal`을 immutable audit trail에 기록할 수 있다.
- `max_agents`와 `max_rounds`로 Agent 수와 proposal 호출 예산을 제한할 수 있다.
- 모든 `option`이 **정확히** 일치할 때만 consensus recommendation을 만들 수 있다.
- `PENDING`, `APPROVED`, `REJECTED` 사람이 승인하는 세 상태의 호출 경계를 구분할 수 있다.
- deterministic local Mock과 fixed tuple script로 network, API key, tool, deployment 없이 충돌 해결을 재현할 수 있다.

## 2. 왜 필요한가

여러 역할이 같은 목표에 다른 제안을 하면, 가장 많이 나온 값을 고르거나 마지막 응답을 채택하는 것은 합의가 아닙니다. 그러한 자동 선택은 소수 의견의 근거를 지우고, 사람이 검토해야 할 trade-off를 Orchestrator가 대신 결정하게 만듭니다.

또한 Agent가 합의하지 못할 때 다시 호출하는 loop에 종료 조건이 없으면 비용과 실행 시간이 계속 늘어납니다. 이 예제는 각 round에 등록된 Agent를 한 번씩만 호출하고, 총 proposal 호출을 `max_rounds * agent_count` 이하로 제한합니다. 합의가 없으면 `conflict_limit_reached`로 멈추며 option을 선택하지 않습니다.

이 장의 `completed`는 사람이 명시적으로 승인한 exact consensus가 local audit result로 기록되었다는 뜻입니다. 파일 변경, tool 실행, live API 호출, message 발송, release 또는 deployment를 뜻하지 않습니다.

## 3. 핵심 개념

- **Conflict proposal(충돌 제안):** 하나의 Agent가 제출하는 `ConflictProposal(option, rationale)`입니다. option과 rationale은 모두 non-empty string이어야 합니다.
- **Exact consensus(정확한 합의):** 한 round의 모든 proposal `option` 값이 같은 경우입니다. rationale이 같아야 한다는 뜻은 아니지만, option의 대소문자·공백·의미를 Orchestrator가 정규화하거나 추측하지 않습니다.
- **ConflictContext:** `objective`, 현재 `round`, 이전 immutable `messages` tuple을 Agent에 전달합니다. 이전 message text 자체가 tool capability, action authority 또는 사람 승인을 전달하지는 않습니다.
- **ConflictMessage:** proposal rationale 또는 policy observation을 role과 round에 연결한 immutable audit record입니다.
- **Bounded loop:** 등록 Agent 수는 2 이상이고 `max_agents` 이하입니다. 각 round의 각 Agent는 한 번만 호출되며 `max_rounds`도 positive integer여야 합니다.
- **Human approval:** `ConflictApproval.PENDING`은 consensus를 보여 주고 `awaiting_human_approval`에서 pause합니다. `APPROVED`일 때만 completed result를 만들고, `REJECTED`는 모든 Agent 호출 전에 종료합니다.
- **Deterministic Mock:** `DeterministicMockConflictAgent`는 immutable non-empty proposal tuple을 호출 순서대로 소비합니다. script가 소진되면 fallback 없이 `AgentProtocolError`를 발생시킵니다.

> [!WARNING]
> `ConflictApproval.APPROVED`는 이 교육용 local run에 전달하는 명시 input입니다. 운영 환경의 승인자 identity, decision scope, proposal hash, timestamp, expiration, revocation 또는 실제 action 권한을 대체하지 않습니다.

## 4. 동작 구조

```text
local objective
      |
      v
round 1..max_rounds
      |
      +--> each configured Agent proposes exactly once
      |          |
      |          +--> validate ConflictProposal before next Agent
      |
      +--> all option values exactly equal?
                   | no
                   +----> next bounded round
                   |          |
                   |          +--> bound reached: conflict_limit_reached
                   |
                   | yes
                   v
          immutable consensus recommendation audit
                   |
      REJECTED ----+----> human_rejected (before every Agent call)
      PENDING -----+----> awaiting_human_approval
      APPROVED ----+----> completed (local result only)
```

`max_agents`는 workflow 구성에 허용되는 role 수의 상한이고, `max_rounds`는 objective 하나에 허용되는 round 수의 상한입니다. 실제 total call budget은 `configured agent count * max_rounds` 이하입니다. `PENDING`은 consensus 후 pause하므로 새 Agent round나 외부 action을 열지 않습니다. `REJECTED`는 proposal audit도 만들지 않습니다.

## 5. 실습 환경

- Python 3.12 이상과 repository의 `uv` environment가 필요합니다.
- 실행 위치는 저장소 루트(`ai-platform-engineering-book-volume-07`)의 Git Bash 또는 WSL Bash입니다.
- 예제 파일은 `examples/volume07/offline_conflict_resolution.py`입니다.
- 구현 파일은 `src/ai_platform/agents/conflict.py`이고, 계약 테스트는 `tests/volume07/test_bounded_conflict_resolution.py`입니다.
- 실습은 repository-local package와 deterministic Mock만 사용합니다. live API, network Agent, secret, environment lookup, tool executor, file mutation, deployment를 사용하지 않습니다.

Windows Git Bash에서 repository가 `E:\python\ai-platform-engineering-book-volume-07`에 있다면 다음처럼 이동합니다.

```bash
# 실행 위치: Git Bash 또는 WSL Bash
cd /e/python/ai-platform-engineering-book-volume-07
```

## 6. 단계별 실습

### 6.1 승인 없이 consensus recommendation 검토하기

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run python examples/volume07/offline_conflict_resolution.py
```

예제의 planner와 reviewer는 모두 `offline tutorial` option을 제안합니다. `--approve`가 없으므로 exact consensus policy message까지 기록한 뒤 `awaiting_human_approval`에서 멈춥니다. `completed`가 아니므로 출력은 변경 또는 다음 작업을 허용하지 않습니다.

### 6.2 명시 승인 뒤 local completion 보기

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run python examples/volume07/offline_conflict_resolution.py --approve
```

`--approve`는 이 한 번의 education CLI run에 `ConflictApproval.APPROVED`를 전달합니다. 같은 fixed proposal script가 소비되어 `completed`를 출력하지만, Agent는 text를 반환하는 local Mock일 뿐입니다. network request, subprocess, file writer, tool executor, deployment client는 호출되지 않습니다.

### 6.3 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run pytest tests/volume07/test_bounded_conflict_resolution.py -q
```

이 명령은 pending/approved/rejected approval 경계, exact consensus, conflicting option의 round 상한, malformed objective/proposal, fixed-script configuration, script exhaustion을 local Mock으로 검증합니다.

## 7. 코드 설명

예제의 `build_workflow()`는 두 deterministic Mock에 각각 하나의 immutable proposal tuple을 제공합니다.

```python
planner = DeterministicMockConflictAgent(
    role="planner",
    proposals=(
        ConflictProposal(
            "offline tutorial",
            "Use a tutorial that never sends data to a live service.",
        ),
    ),
)
reviewer = DeterministicMockConflictAgent(
    role="reviewer",
    proposals=(
        ConflictProposal(
            "offline tutorial",
            "The proposed tutorial has a reviewable local boundary.",
        ),
    ),
)
```

`BoundedConflictResolutionWorkflow` 생성자는 `agents`가 mapping인지, role 수가 2 이상 `max_agents` 이하인지, role key가 non-empty string인지, 각 boundary에 callable `propose(context)`가 있는지 검사합니다. role을 선언하는 deterministic Mock은 mapping key와 같은 role이어야 합니다. 접근 불가 accessor, non-callable boundary, mutable script 또는 malformed fixed proposal은 첫 proposal 호출 전에 `WorkflowConfigurationError`로 fail-closed합니다.

`run()`의 핵심 순서는 다음과 같습니다.

1. `objective`와 `human_approval` type을 검사합니다. `REJECTED`이면 모든 Agent 호출 전에 empty audit trail의 `human_rejected` result를 반환합니다.
2. `range(1, max_rounds + 1)`에서 configured mapping 순서대로 각 Agent를 한 번 호출합니다.
3. 각 반환값이 `ConflictProposal`인지와 `option`/`rationale`이 non-empty string인지 **다음 Agent 호출 전** 검사합니다. 위반이면 audit에 기록하거나 fallback하지 않고 `AgentProtocolError`를 냅니다.
4. 유효 proposal의 rationale만 role/round와 함께 `ConflictMessage`에 기록하고, option 집합의 크기가 1인지 확인합니다.
5. option이 다르면 어떤 winner도 선택하지 않고 다음 bounded round로만 진행합니다. 마지막 round에서도 다르면 `conflict_limit_reached`와 `consensus_option=None`을 반환합니다.
6. exact consensus면 policy message를 기록합니다. `PENDING`은 pause result를 반환하고, `APPROVED`만 동일 audit trail로 local `completed` result를 반환합니다.

`ConflictContext.messages`와 result messages는 tuple입니다. 따라서 다음 proposal을 받는 Agent는 이전 audit history를 읽을 수는 있어도 workflow의 기록 또는 approval 상태를 수정할 수 없습니다.

## 8. 정상 실행 결과

승인 없이 실제 예제를 실행하면 다음 output이 나옵니다.

```text
status=awaiting_human_approval
consensus_option=offline tutorial
1:planner: Use a tutorial that never sends data to a live service.
1:reviewer: The proposed tutorial has a reviewable local boundary.
1:policy: Exact consensus proposed: offline tutorial
```

`policy` message는 exact consensus가 관찰되었다는 audit record이지, 자동 action 명령이 아닙니다. approval이 없어 `completed`가 아니며 다음 Agent도 호출되지 않습니다.

`--approve`를 전달하면 status만 다음처럼 바뀌고 동일한 local audit이 출력됩니다.

```text
status=completed
consensus_option=offline tutorial
1:planner: Use a tutorial that never sends data to a live service.
1:reviewer: The proposed tutorial has a reviewable local boundary.
1:policy: Exact consensus proposed: offline tutorial
```

여기서 `completed`는 사람이 승인한 exact consensus result일 뿐입니다. 예제에는 command execution, write operation, external API result, deployment log가 없습니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `ModuleNotFoundError: ai_platform` | repository root 밖에서 Python을 직접 실행했거나 source package가 path에 없음 | root로 이동한 뒤 `uv run python examples/volume07/offline_conflict_resolution.py`를 실행합니다. |
| `status=awaiting_human_approval` | `--approve`가 없어서 consensus gate에 정상 pause함 | planner/reviewer/policy audit과 `consensus_option`을 검토합니다. 교육용 completed 경로가 필요할 때만 `--approve`를 전달합니다. |
| `conflict_limit_reached` | 각 제한된 round에서 option 값이 정확히 같지 않음 | 다수결이나 string normalization으로 winner를 만들지 마십시오. audit을 검토하고 새 bounded request를 별도로 시작합니다. |
| `WorkflowConfigurationError` | empty objective, non-positive bound, role 수/label 오류, inaccessible/non-callable boundary, mutable 또는 malformed fixed script | objective, positive bounds, mapping role, immutable tuple 및 proposal fields를 수정합니다. |
| `AgentProtocolError` | runtime proposal이 contract를 위반했거나 fixed script가 소진됨 | proposal type과 non-empty option/rationale, configured round budget과 각 script 길이를 함께 점검합니다. 다음 Agent·round·fallback을 호출하지 마십시오. |
| approval 전 결과가 action처럼 보임 | policy recommendation과 action authority를 혼동함 | `PENDING`은 stop condition입니다. 별도의 scoped human approval record 없이 external action을 연결하지 않습니다. |

## 10. 응용 실습

1. planner는 첫 round에 `option-a`, reviewer는 `option-b`를 제안하고 두 번째 round에는 동일 option을 제안하도록 script를 만듭니다. `max_rounds=2`에서 approved run이 두 번째 round에만 completed인지 test로 확인합니다.
2. 두 role이 모든 round에서 다른 option을 반환하도록 구성하고, `consensus_option is None`과 호출 수가 정확히 `2 * max_rounds`인지 확인합니다.
3. non-empty지만 allow되지 않은 semantic alias를 자동으로 같은 option으로 바꾸지 않는 local test를 작성합니다. 이 workflow는 exact string equality만 사용함을 설명합니다.
4. `ConflictProposal("", "reason")` 또는 mutable proposal list가 Mock 생성 단계에서 거절되는지 확인하고, runtime test double의 malformed response가 다음 Agent 전에 중단되는지도 고정합니다.

이 실습도 deterministic local fixture만 사용해야 합니다. API client, subprocess tool, file writer, deployment adapter를 추가하지 마십시오.

## 11. 실무 적용

운영 conflict-resolution 시스템에서는 recommendation과 authority를 명확히 분리해야 합니다.

- 각 proposal은 request ID, role identity reference, input version, rationale, timestamp를 immutable audit record에 연결합니다. secret, raw credential, unrestricted tool handle은 기록하지 않습니다.
- consensus policy는 option canonicalization의 소유자와 version을 명시합니다. 이 예제처럼 exact equality만 사용할지, 별도 검증된 canonicalizer를 사용할지 결정하지 않은 채 문자열을 추측해 합치지 않습니다.
- approval service는 approver identity, request scope, proposal set hash, policy version, issued timestamp, expiration, revocation을 별도로 검증합니다.
- action dispatcher는 approved record와 현재 proposal set이 일치하는지 재확인하고, approval이 없거나 만료되면 dispatch하지 않습니다.
- timeout, cancellation, maximum agent count, maximum round count, protocol failure를 관측하되 external capability를 conflict-agent message text로 위임하지 않습니다.

> [!TIP]
> `awaiting_human_approval`과 `conflict_limit_reached`는 Router의 자동 retry, 다수결 fallback 또는 다른 Agent 추가 신호가 아닙니다. 각각 approval을 기다리는 stop condition과 bounded disagreement 결과입니다.

## 12. 과제

### 기본

- `PENDING`, `APPROVED`, `REJECTED` 각각에서 Agent call 수, policy message, result status가 무엇인지 표로 정리합니다.
- option이 모두 동일할 때도 사람 승인이 필요한 이유를 설명합니다.

### 응용

- `max_rounds=2`에서 첫 round disagreement, 두 번째 round exact consensus를 재현하는 test를 작성합니다.
- empty objective가 첫 planner 호출 전에 거절됨을 call-history assertion으로 보입니다.

### 심화

- 운영용 immutable conflict approval record schema를 설계합니다. request ID, objective hash, proposal-set hash, consensus policy version, approver identity reference, issued timestamp, expiration, decision을 포함하되 실제 identity provider나 action executor는 연결하지 않습니다.
- no-consensus, malformed proposal, inaccessible agent boundary, approval expiration을 서로 다른 observability event로 표현하는 설계를 제안합니다. event에 secret 또는 raw credential을 넣지 마십시오.

## 13. 완료 체크리스트

- [ ] `ConflictProposal`, `ConflictContext`, `ConflictMessage`가 각각 어떤 정보를 보존하는지 설명할 수 있다.
- [ ] `max_agents`와 `max_rounds`로 total proposal call budget을 계산할 수 있다.
- [ ] 기본 실행에서 `awaiting_human_approval`과 policy audit을 확인했다.
- [ ] `--approve`가 local result만 completed로 만들고 external action을 하지 않음을 확인했다.
- [ ] disagreement가 다수결/추측 없이 `conflict_limit_reached`로 종료됨을 설명할 수 있다.
- [ ] malformed input/proposal과 fixed script exhaustion이 다음 Agent 호출 전에 fail-closed함을 확인했다.
- [ ] `uv run pytest tests/volume07/test_bounded_conflict_resolution.py -q`를 통과시켰다.
- [ ] 이 예제에 live API, secret, tool execution, file mutation, deployment가 없음을 확인했다.

## 14. 핵심 정리

안전한 Multi-Agent conflict resolution은 여러 답 중 하나를 자동으로 고르는 기술이 아닙니다. 역할별 제안과 근거를 immutable audit trail로 남기고, Agent 수와 round를 유한하게 제한하며, 모든 option이 정확히 일치하는 경우에만 recommendation을 만듭니다. 그 recommendation도 명시적인 사람 승인 전에는 action authority가 아닙니다. deterministic Mock 예제는 이 계약을 외부 capability 없이 재현하며, input·boundary·proposal contract가 맞지 않거나 합의가 없으면 다음 Agent, 다음 round, fallback selection 없이 fail-closed합니다.
