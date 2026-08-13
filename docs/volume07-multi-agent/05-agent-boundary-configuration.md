# 05. 구성 단계 Agent 경계 검증

## 1. 학습 목표

다중 Agent workflow는 실행 전에 각 역할 경계가 실제로 읽히고 호출 가능한지 확인해야 합니다. 이 장을 마치면 다음을 설명하고 재현할 수 있습니다.

- Python `Protocol` type hint와 실행 시점의 `act(context)` 또는 `propose(context)` 경계 검증의 차이
- 잘못되었거나 접근할 수 없는 역할 객체를 첫 Agent 호출 전에 `WorkflowConfigurationError`로 거절하는 이유
- deterministic Mock의 선언 `role`과 workflow slot을 일치시키는 방법
- 구성 검증, runtime response schema 검증, bounded loop, human approval gate의 책임 분리

> [!WARNING]
> 구성 검증은 Agent를 실행하거나 권한을 부여하지 않습니다. 이 장의 Mock은 network, live API, secret, tool executor, file mutation, deployment capability를 갖지 않습니다.

## 2. 왜 필요한가

`Agent`, `ConflictAgent`, `DelegatedWorker` 같은 `Protocol`은 정적 분석에 도움이 되지만, 실행 중 전달된 객체가 실제로 `act()` 또는 `propose()`를 제공한다는 보장은 하지 않습니다. 예를 들어 `None`, 일반 객체, 문자열, non-callable attribute, 또는 읽는 순간 예외를 내는 property가 역할 자리에 들어올 수 있습니다.

이 오류를 workflow 중간까지 미루면 Planner가 이미 실행된 뒤 Researcher 또는 QA에서 실패할 수 있습니다. audit trail은 부분적으로 남고, 사람은 어느 역할이 실행됐는지와 재실행해도 되는지를 다시 판단해야 합니다. 생성자에서 모든 역할 경계를 검사하면 어떤 Agent call 이전에 문제를 고정된 예외로 알리고, fallback이나 자동 재시도를 하지 않습니다.

## 3. 핵심 개념

- **구성 단계(configuration time):** workflow constructor가 역할 mapping, callable method, immutable allow-list, declared Mock role을 검사하는 시점입니다. Agent method 자체를 호출하지 않습니다.
- **호출 가능 경계(callable boundary):** review/release 역할은 `act(context)`, delegation coordinator와 conflict peer는 `propose(context)`, delegation Worker는 `act(context)`를 제공해야 합니다.
- **접근 불가 경계:** `getattr(boundary, "act")` 또는 `getattr(boundary, "propose")`가 property exception을 발생시키는 경우입니다. 이 경우도 `WorkflowConfigurationError`로 원인을 보존하며 fail-closed합니다.
- **선언 역할 바인딩:** `DeterministicMockAgent`처럼 `role` 속성을 선언하는 local Mock은 구성 slot과 정확히 일치해야 합니다. production-style adapter처럼 `role`을 제공하지 않는 경계는 callable contract만 검사합니다.
- **runtime protocol 검증:** 호출 뒤 반환되는 `AgentResponse`, `WorkerResponse`, `ConflictProposal`의 type과 non-empty field는 별도 책임입니다. 구성 검증이 response 내용을 신뢰하게 만들지 않습니다.
- **사람 승인:** 경계가 유효하더라도 `PENDING`은 QA, Worker, DevOps를 호출하지 않습니다. `APPROVED`와 `REJECTED`는 run 시점의 별도 입력입니다.

## 4. 동작 구조

```text
workflow constructor
        |
        v
validate callable method / declared Mock role / immutable collection
        |
        +-- invalid or inaccessible --> WorkflowConfigurationError
        |                              (zero Agent calls; no fallback)
        v
bounded workflow run
        |
        v
validate runtime response schema
        |
        +-- invalid --> AgentProtocolError
        |               (do not call the next role)
        v
explicit human approval boundary
        |
        +-- PENDING  --> awaiting_human_approval
        +-- REJECTED --> human_rejected before Agent calls
        +-- APPROVED --> only the workflow's bounded local next stage
```

구성 검증은 human approval보다 앞서지만, approval을 대체하지 않습니다. 유효한 `qa` Mock을 구성했다고 해서 QA 실행 권한이 생기지 않습니다.

## 5. 실습 환경

다음 환경에서 실행합니다.

- Windows 10/11의 Git Bash 또는 WSL Bash
- Python 3.12 이상과 repository의 `uv` environment
- 저장소 루트: `E:\python\ai-platform-engineering-book-volume-07`

이 장에서 참조하는 local 파일은 다음과 같습니다.

```text
src/ai_platform/agents/workflow.py
tests/volume07/test_agent_boundary_configuration.py
tests/volume07/test_inaccessible_agent_boundaries.py
tests/volume07/test_declared_mock_role_binding.py
```

외부 package 설치, API key, `.env`, network connection, Docker, deployment target은 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 정상 local boundary로 approval pause 확인

저장소 루트에서 review example을 승인 없이 실행합니다.

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
cd /e/python/ai-platform-engineering-book-volume-07
uv run python examples/volume07/offline_review_workflow.py
```

이 명령은 valid `act(context)` 경계를 가진 deterministic Mock을 구성합니다. 그러나 `PENDING`이므로 QA는 실행하지 않고 `awaiting_human_approval`에서 멈춰야 합니다.

### 6.2 non-callable role을 구성 시점에 거절하는 test 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run pytest tests/volume07/test_agent_boundary_configuration.py -q
```

이 test는 `act` 또는 `propose`가 없거나 callable이 아닌 역할을 각 workflow constructor가 거절하는지 확인합니다. workflow를 만들지 못했으므로 Planner, Coordinator, Worker, conflict peer, QA, DevOps call history는 모두 비어 있어야 합니다.

### 6.3 접근 불가 property와 role mismatch 확인

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run pytest \
  tests/volume07/test_inaccessible_agent_boundaries.py \
  tests/volume07/test_declared_mock_role_binding.py -q
```

첫 test는 `act`/`propose` property accessor가 예외를 내도 원인(chain)을 유지한 `WorkflowConfigurationError`가 되는지를 확인합니다. 두 번째 test는 `role="qa"` Mock을 `planner=` slot에 배선하는 오류가 첫 Agent call 전에 중단되는지를 확인합니다.

### 6.4 전체 Volume 07 contract 재실행

```bash
# 실행 위치: 저장소 루트의 Git Bash 또는 WSL Bash
uv run pytest tests/volume07 -q
```

이 명령은 boundary configuration 외에도 immutable Mock script, response schema, bounded retry/review/round, explicit human approval을 함께 회귀 검증합니다.

## 7. 코드 설명

공통 helper `validate_callable_boundary()`는 protocol method를 실행하지 않고 먼저 읽습니다.

```python
try:
    method = getattr(boundary, method_name, None)
except Exception as error:
    raise WorkflowConfigurationError(
        f"{name} {method_name} boundary could not be read"
    ) from error
if not callable(method):
    raise WorkflowConfigurationError(
        f"{name} must provide a callable {method_name}(context) method"
    )
```

`getattr()`의 accessor failure를 잡는 이유는 property도 local adapter의 configuration boundary이기 때문입니다. `from error`를 사용하면 caller가 stable public exception을 처리하면서 원래 adapter 오류도 조사할 수 있습니다. `callable()` 검사는 method signature를 호출해 추측하지 않으므로 구성 중 side effect를 만들지 않습니다.

Review와 release workflow는 `validate_agent_boundary(role, agent)`를 사용합니다. 이 helper는 `act` callable을 검사한 뒤 optional `role` declaration을 검사합니다. Delegation과 conflict workflow는 method 이름이 다르므로 다음처럼 명시적으로 적용합니다.

```python
validate_callable_boundary("coordinator", "propose", coordinator)
validate_callable_boundary(f"worker for {assignee}", "act", worker)
validate_declared_role(assignee, f"worker for {assignee}", worker)
```

`DeterministicMock*`은 non-empty immutable tuple script를 소비할 뿐이며, 여기서 읽는 `role`은 local fixture wiring check입니다. 이 label은 production identity, tool capability, approval authority가 아닙니다.

## 8. 정상 실행 결과

6.1의 승인 없는 review example은 다음 형태로 출력됩니다.

```text
status=awaiting_human_approval
review_cycles=1
0:planner: Plan: define the offline acceptance criteria.
0:researcher: Evidence: use only repository-local fixtures.
1:developer: Draft: bounded workflow implementation.
1:reviewer: Review: acceptance criteria are met.
```

출력에 `qa:`가 없다는 점이 중요합니다. 구성 검증을 통과한 valid QA boundary가 있어도 explicit `HumanApproval.APPROVED`가 없으면 QA는 실행되지 않습니다.

6.2와 6.3의 test는 pytest summary에서 pass해야 합니다. 해당 cases에서 기대하는 안정적인 구성 오류의 예는 다음과 같습니다.

```text
WorkflowConfigurationError: planner must provide a callable act(context) method
WorkflowConfigurationError: agent for reviewer propose boundary could not be read
WorkflowConfigurationError: qa declared role must match 'planner'
```

오류는 workflow constructor에서 발생하므로 계획, proposal, worker result, audit message가 생성되기 전입니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `WorkflowConfigurationError: ... callable act(context)` | 역할 객체에 `act`가 없거나 callable이 아닙니다. | 해당 slot에 local Mock 또는 `act(context)` adapter를 전달합니다. `act`를 호출해 값을 미리 만들지 마십시오. |
| `... propose boundary could not be read` | adapter property가 method lookup 시 예외를 냈습니다. | property의 local configuration 오류를 고친 뒤 새 workflow를 구성합니다. exception을 숨기거나 다른 Agent로 fallback하지 마십시오. |
| `declared role must match` | deterministic Mock의 `role`과 workflow slot/mapping key가 다릅니다. | Mock role label 또는 slot을 정확히 맞춥니다. production identity 검증으로 오해하지 마십시오. |
| 구성은 성공했지만 `AgentProtocolError` 발생 | 호출 뒤 반환된 response type, content, review field, script budget이 runtime contract를 위반했습니다. | 다음 역할을 호출하지 말고 response schema와 immutable script를 수정합니다. |
| valid boundary인데 QA/Worker/DevOps가 실행되지 않음 | `PENDING`은 정상 pause입니다. | audit trail을 검토한 뒤 해당 workflow에만 explicit `APPROVED`를 전달합니다. |
| `ModuleNotFoundError: ai_platform` | repository root 밖에서 직접 Python을 실행했을 수 있습니다. | root에서 `uv run ...` 명령을 사용합니다. |

## 10. 응용 실습

1. `act` property를 읽을 때 `RuntimeError`를 내는 local test double을 만들고, Review workflow constructor가 `WorkflowConfigurationError`를 raise하며 다른 local Mock의 `calls`가 빈 list인지 확인합니다.
2. Delegation workflow에서 `workers` mapping key와 `DeterministicMockWorker.role`을 일부러 다르게 하고, Coordinator의 `calls`가 비어 있는지 test로 고정합니다.
3. `role` 속성이 없는 minimal adapter를 작성해 callable boundary만으로 구성할 수 있음을 확인합니다. 반환 response는 deterministic local fixture로 고정하고 network/tool을 추가하지 마십시오.
4. 잘못된 runtime response와 잘못된 configuration boundary를 각각 만들어 `WorkflowConfigurationError`와 `AgentProtocolError`가 발생하는 시점 차이를 표로 비교합니다.

## 11. 실무 적용

운영 adapter도 구성 단계에서 endpoint allow-list, authentication configuration presence, timeout policy, capability declaration을 검증할 수 있습니다. 그러나 이 chapter의 `callable()` 검사는 그런 운영 통제를 구현하지 않습니다. 특히 object에 `act`라는 이름이 있다는 사실은 network access, data access, filesystem mutation, deployment permission을 뜻하지 않습니다.

실무에서는 다음을 별도 경계로 둡니다.

1. workflow configuration은 role-to-adapter wiring과 bounded limit을 검사합니다.
2. runtime schema validation은 untrusted response가 다음 role로 전파되지 않게 합니다.
3. approval system은 approver identity, scope, timestamp, expiration, immutable record를 검증합니다.
4. tool executor는 최소 권한과 allow-list를 다시 검사합니다.
5. observability는 secret을 제외한 audit event를 기록합니다.

> [!TIP]
> property accessor에서 발생한 원인을 `WorkflowConfigurationError`의 cause로 보존하면 adapter owner가 문제를 조사할 수 있습니다. 다만 production exception message에 secret이나 credential을 포함하지 않도록 adapter 자체에서 주의해야 합니다.

## 12. 과제

### 기본

- Review, delegation, conflict, release workflow 각각의 constructor가 요구하는 method 이름을 적습니다.
- `PENDING` review run에서 QA boundary가 valid해도 호출되지 않는 이유를 설명합니다.

### 응용

- non-callable `act` attribute와 response validation failure를 각각 재현하는 local test를 작성하고, 어느 failure가 첫 Agent call 전에 발생하는지 assertion으로 고정합니다.
- declared Mock role mismatch가 있을 때 valid peer/worker의 `calls`가 비어 있는지 네 workflow 중 두 개에서 확인합니다.

### 심화

- production adapter configuration schema를 설계합니다. endpoint allow-list reference, timeout, role, permitted capability ID를 포함하되 secret value, unrestricted tool handle, approval decision은 포함하지 마십시오.
- human approval record schema를 별도로 설계합니다. approver identity, scope, issued time, expiration, immutable audit reference를 포함하고, callable boundary validation과 왜 다른 책임인지 설명합니다.

## 13. 완료 체크리스트

- [ ] `act(context)`와 `propose(context)`가 각 workflow에서 요구되는 역할을 구분했다.
- [ ] non-callable 또는 inaccessible boundary가 첫 Agent call 전에 `WorkflowConfigurationError`가 됨을 확인했다.
- [ ] deterministic Mock의 declared role과 workflow slot이 일치해야 함을 확인했다.
- [ ] 구성 검증과 runtime `AgentProtocolError`의 발생 시점 및 책임을 구분했다.
- [ ] `PENDING`에서 QA, Worker, DevOps가 실행되지 않음을 확인했다.
- [ ] `uv run pytest tests/volume07/test_agent_boundary_configuration.py -q`를 통과시켰다.
- [ ] `uv run pytest tests/volume07 -q`로 Volume 07 regression suite를 통과시켰다.
- [ ] local Mock에 network, secret, tool execution, file mutation, deployment를 추가하지 않았다.

## 14. 핵심 정리

안전한 Multi-Agent workflow는 역할 객체가 실패하기 쉬운 runtime path에 들어가기 전에 boundary를 검사합니다. 구성 단계에서는 callable method, inaccessible accessor, deterministic Mock role wiring 같은 배선 오류를 fail-closed로 중단합니다. 실행 단계에서는 response schema와 bounded loop를 검사하고, 사람 승인은 그 이후에도 독립적으로 next stage를 제어합니다. 따라서 valid adapter는 실행 허가가 아니며, `completed`는 이 Volume에서만 local deterministic workflow completion을 뜻합니다.
