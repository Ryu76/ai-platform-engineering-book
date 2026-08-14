# 08. 실행 중 검토 결정 계약

## 1. 학습 목표

결정론적 Mock이 아닌 사용자 구현 Agent도 실행 중에는 신뢰할 수 없는 경계임을 이해합니다. 이 장을 마치면 다음을 할 수 있어야 합니다.

- `AgentResponse.review`가 `ReviewDecision` 또는 `None`인지 audit trail에 기록하기 전에 검사한다.
- 문자열 `"approve"`와 `ReviewDecision.APPROVE`의 차이를 설명한다.
- malformed runtime response가 다음 Agent와 사람 승인 gate를 통과하지 못하게 한다.
- deterministic Mock의 구성 단계 검증과 일반 Agent adapter의 실행 단계 검증을 구분한다.
- live API, secret, tool execution, deployment 없이 local test double로 fail-closed 동작을 재현한다.

> [!WARNING]
> Volume 07은 local deterministic Mock과 local test double만 사용합니다. 이 장의 실습은 live API, network agent, secret, tool execution, file mutation, deployment를 수행하거나 설정하지 않습니다.

## 2. 왜 필요한가

`AgentResponse`는 frozen dataclass이지만 Python 런타임은 type annotation을 강제하지 않습니다. 따라서 외부 adapter나 사용자 구현 Agent가 `review="approve"`, `1`, 또는 임의 객체를 반환할 수 있습니다. 문자열 `"approve"`는 화면에는 올바른 enum처럼 보여도 `ReviewDecision` 객체가 아니며, workflow가 권한 있는 검토 결정으로 해석해서는 안 됩니다.

고정 `DeterministicMockAgent` script는 생성 시 잘못된 값을 거절합니다. 그러나 `BoundedReviewWorkflow`와 `ApprovalGatedReleaseHandoffWorkflow`는 Protocol을 만족하는 다른 local Agent도 받을 수 있습니다. 구성 시 검증을 통과한 뒤에도 각 호출의 응답은 다시 검증해야 audit message, bounded loop, explicit human approval 경계가 보존됩니다.

## 3. 핵심 개념

| 개념 | 책임 | Volume 07 규칙 |
|---|---|---|
| 구성 단계 fixture 검증 | 고정 Mock script의 알려진 값을 검사 | 빈 `tuple`, 빈 content, 문자열 review를 `WorkflowConfigurationError`로 거절 |
| 실행 단계 protocol 검증 | 호출마다 신뢰할 수 없는 Agent output을 검사 | `AgentResponse`, non-empty content, `ReviewDecision` 또는 `None`만 허용 |
| 역할 권한 검증 | 누가 review를 낼 수 있는지 검사 | Reviewer만 `APPROVE` 또는 `REVISE`를 반환 가능 |
| Audit trail | 검증된 결과만 다음 role에 전달 | 잘못된 response는 `AgentMessage`로 추가하지 않음 |
| Human approval | 유효한 reviewer 결과 뒤 다음 local stage를 여는 결정 | `APPROVED`도 malformed response를 승인하지 못함 |

실행 중 안전 규칙은 다음과 같습니다.

- 모든 `AgentResponse.content`는 비어 있지 않은 문자열이어야 합니다.
- 모든 `AgentResponse.review`는 `ReviewDecision.APPROVE`, `ReviewDecision.REVISE`, 또는 `None`이어야 합니다.
- 잘못된 `review`는 `AgentProtocolError`로 즉시 종료합니다.
- 오류 응답은 audit message로 추가하지 않으며 Researcher, Reviewer, QA, DevOps 같은 다음 역할을 호출하지 않습니다.
- `HumanApproval.APPROVED`도 잘못된 Agent 응답을 승인하거나 QA·DevOps로 진행시키지 않습니다.

## 4. 동작 구조

```text
local Agent adapter / deterministic Mock
                |
                v
        AgentResponse runtime output
                |
                v
content non-empty + review enum type check
        | valid                         | invalid
        v                               v
role-scoped review check          AgentProtocolError
        | valid                         |
        v                               +--> no audit message
append immutable audit message          +--> no next Agent call
        |
        v
bounded loop / explicit human gate
        |
        +--> PENDING: awaiting_human_approval
        +--> APPROVED: only next bounded local stage
        +--> REJECTED: pre-call human_rejected
```

`PENDING`, `APPROVED`, `REJECTED`는 human gate의 상태입니다. runtime schema error의 recovery mechanism이 아닙니다. `APPROVED` 경로도 먼저 response와 역할 authority를 검사한 뒤에만 QA 또는 local DevOps handoff로 진행할 수 있습니다.

## 5. 실습 환경

- Python 3.12 이상과 repository의 `uv` environment가 필요합니다.
- 명령은 저장소 루트의 Git Bash 또는 WSL Bash에서 실행합니다.
- 관련 구현은 `src/ai_platform/agents/workflow.py`, `src/ai_platform/agents/release_handoff.py`에 있습니다.
- 관련 local test double과 contract test는 `tests/volume07/test_runtime_review_decision_contract.py`에 있습니다.

Windows Git Bash에서는 다음처럼 저장소 루트로 이동합니다.

```bash
# 실행 위치: Git Bash 또는 WSL Bash
cd /e/python/ai-platform-engineering-book-volume-07
```

이 실습에는 API key나 다른 secret을 추가하지 마십시오. examples와 tests에는 live API client, network agent, HTTP client, tool executor, file mutation, deployment client가 없습니다.

## 6. 단계별 실습

### 6.1 Runtime decision contract 실행

먼저 문자열 review를 반환하는 local untrusted test double이 다음 역할을 막는지 확인합니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07/test_runtime_review_decision_contract.py -q
```

이 명령은 `InvalidReviewAgent`가 `AgentResponse("plan", "approve")`를 반환해도 Researcher가 호출되지 않는지, release handoff의 invalid Reviewer response 뒤 QA와 DevOps가 호출되지 않는지 확인합니다.

### 6.2 역할별 review authority 확인

같은 focused test에는 Planner, QA, DevOps가 올바른 enum 값이라도 review authority를 주장하지 못하는 경우가 포함됩니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07/test_runtime_review_decision_contract.py -q \
  -k 'non_reviewer or qa_cannot or devops_cannot'
```

이 명령은 Reviewer 외 role의 `ReviewDecision`이 audit trail에 추가되기 전에 `AgentProtocolError`가 되는지를 확인합니다. 사람 approval flag나 production action은 사용하지 않습니다.

### 6.3 전체 Volume 07 regression 실행

마지막으로 runtime contract가 immutable Mock, bounded loop, independent approval gate의 다른 계약과 함께 유지되는지 확인합니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07 -q
```

## 7. 코드 설명

`BoundedReviewWorkflow._validate_response()`와 `ApprovalGatedReleaseHandoffWorkflow._validate_response()`는 Agent 호출 직후 다음을 검사합니다.

```python
if not isinstance(response, AgentResponse):
    raise AgentProtocolError("agent response must be an AgentResponse")
if not isinstance(response.content, str) or not response.content.strip():
    raise AgentProtocolError("agent response content must be a non-empty string")
if response.review is not None and not isinstance(response.review, ReviewDecision):
    raise AgentProtocolError("agent response review must be a ReviewDecision or None")
```

검토 결정의 type이 유효한 뒤에는 `_validate_role_response()`가 authority를 검사합니다.

```python
if role != "reviewer" and response.review is not None:
    raise AgentProtocolError(f"{role} response must not include a review decision")
if role == "reviewer" and response.review not in (
    ReviewDecision.APPROVE,
    ReviewDecision.REVISE,
):
    raise AgentProtocolError("reviewer response must include an explicit review decision")
```

두 검사는 순서가 중요합니다. 첫 검사는 `"approve"` 같은 위조된 enum-like 값을 거절합니다. 둘째 검사는 유효한 enum을 반환했더라도 Reviewer가 아닌 role의 권한 주장을 거절합니다. 둘 다 `AgentMessage` append와 다음 role 호출보다 먼저 수행됩니다.

## 8. 정상 실행 결과

focused runtime contract command의 정상 결과는 exit code `0`과 모든 test 통과입니다. 현재 local run의 출력 형태는 다음과 같습니다.

```text
.....                                                                    [100%]
5 passed
```

테스트 수는 이후 안전 계약 추가에 따라 달라질 수 있습니다. 중요한 관찰 결과는 다음입니다.

- invalid Planner string review 뒤 Researcher, Developer, Reviewer, QA의 call history는 비어 있습니다.
- invalid release Reviewer string review 뒤 QA와 DevOps의 call history는 비어 있습니다.
- QA 또는 DevOps의 review authority 위반 뒤 DevOps handoff note는 생성되지 않습니다.
- `HumanApproval.APPROVED`를 전달해도 malformed response가 `completed`가 되지 않습니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `agent response review must be a ReviewDecision or None` | 문자열 `"approve"`, `1`, 다른 객체를 review로 반환함 | `ReviewDecision.APPROVE`, `ReviewDecision.REVISE`, `None`만 반환하도록 adapter를 수정합니다. |
| `planner response must not include a review decision` | Planner가 Reviewer authority를 주장함 | Planner response의 `review`를 제거하거나 `None`으로 둡니다. |
| `qa response must not include a review decision` | QA가 DevOps handoff 직전에 review 결정를 반환함 | QA는 검사 결과를 `content`에만 기록하고 review authority를 사용하지 않습니다. |
| `reviewer response must include an explicit review decision` | Reviewer가 `review=None`을 반환함 | Reviewer adapter가 `APPROVE` 또는 `REVISE`를 명시적으로 반환하게 합니다. |
| approval을 전달해도 completion되지 않음 | approval을 schema validation 우회 수단으로 오해함 | 먼저 runtime output과 role authority 오류를 해결합니다. `APPROVED`는 유효한 reviewer 결과 뒤의 local stage만 허용합니다. |

> [!WARNING]
> malformed response를 숨기기 위해 fallback review를 만들거나 exception을 문자열 audit message로 바꾸지 마십시오. 그러면 call budget과 approval 전에 검토한 audit trail이 달라집니다. 이 workflow는 다음 role 호출 없이 fail-closed해야 합니다.

## 10. 응용 실습

1. Researcher가 `ReviewDecision.REVISE`를 반환하는 local test double을 만들고 Developer가 호출되지 않는 assertion을 작성합니다.
2. `review=object()`를 반환하는 Reviewer adapter를 만들고 QA와 DevOps가 호출되지 않는지 확인합니다.
3. Reviewer가 `None`을 반환하는 test에서 reviewer response가 audit message에 추가되지 않는지 확인합니다.
4. `PENDING`, `APPROVED`, `REJECTED`를 table-driven test로 작성합니다. 각 row에서 runtime schema error가 human decision보다 우선하는지 설명합니다.

## 11. 실무 적용

production Agent adapter에서는 model, tool, user input에서 온 결과를 모두 untrusted input으로 처리해야 합니다. local test double의 `calls` list는 교육용 audit 도구일 뿐 production authorization system이 아닙니다. 실제 시스템은 다음 책임을 별도로 구현해야 합니다.

1. schema validator가 runtime response를 구조적으로 검사합니다.
2. role identity와 authorization policy가 Reviewer authority를 인증합니다.
3. bounded retry policy가 protocol error를 새로운 Agent 호출로 숨기지 않도록 합니다.
4. approval system이 approver identity, scope, timestamp, expiration, immutable record를 검증합니다.
5. tool executor와 deployment control plane이 별도 allow-list와 least-privilege policy를 적용합니다.

이 Volume의 `completed`는 deterministic local workflow completion일 뿐 external deployment, tool call, file mutation, live API success를 의미하지 않습니다.

## 12. 과제

### 기본

- `ReviewDecision.APPROVE`와 문자열 `"approve"`가 다른 이유를 작성합니다.
- malformed Planner output 뒤 호출되지 않아야 하는 role을 순서대로 적습니다.

### 응용

- non-empty content와 review enum type 검증을 별도 test case로 나눕니다.
- Release handoff에서 invalid QA response가 local handoff note를 막는 assertion을 작성합니다.

### 심화

- runtime schema policy와 role authorization policy를 별도 immutable configuration으로 설계합니다.
- production approval record의 scope, approver identity, timestamp, expiration, immutable audit location을 정의합니다. deterministic Mock에는 production approval backend를 import하지 마십시오.

## 13. 완료 체크리스트

- [ ] 구성 단계 fixed script 검증과 실행 중 response 검증을 구분할 수 있다.
- [ ] `AgentResponse.review`에 문자열이 아닌 `ReviewDecision` 또는 `None`만 허용됨을 확인했다.
- [ ] malformed response가 audit trail과 다음 Agent 호출 전에 fail-closed됨을 확인했다.
- [ ] Reviewer 외 role의 review authority 주장이 fail-closed됨을 확인했다.
- [ ] `APPROVED`가 protocol error를 우회하지 않음을 설명할 수 있다.
- [ ] `uv run pytest tests/volume07/test_runtime_review_decision_contract.py -q`를 통과시켰다.
- [ ] `uv run pytest tests/volume07 -q`를 통과시켰다.

## 14. 핵심 정리

결정론적 Mock의 생성자 검증만으로는 일반 Agent adapter의 runtime 출력을 신뢰할 수 없습니다. 모든 response는 audit trail과 다음 role 호출 전에 schema를 검증해야 하며, review decision은 Reviewer에게만 허용해야 합니다. deterministic Mock, bounded loop, explicit human approval을 함께 사용해도 malformed response를 자동 복구하거나 approval로 승인해서는 안 됩니다. Volume 07은 이 fail-closed 계약을 local-only test로 검증하며 live API, secret, tool execution, deployment를 사용하지 않습니다.
