# 07. 고정 Mock script 항목 계약

## 1. 학습 목표

결정론적 Mock의 `tuple` 컨테이너뿐 아니라 그 안의 각 항목도 구성 단계에서 검사해야 하는 이유를 이해합니다. 학습 후에는 잘못된 고정 응답, 위임 계획, Worker 결과, 충돌 제안을 첫 Agent 호출 전에 `WorkflowConfigurationError`로 중단할 수 있습니다.

## 2. 왜 필요한가

`tuple`은 호출 순서와 호출 수를 고정하지만, `tuple` 안에 빈 문자열이나 잘못된 타입이 있으면 실행 도중에야 오류가 드러납니다. 그러면 실습의 실패 위치가 Agent 호출 뒤가 되고, 호출 이력과 사람 승인 전 경계를 읽기 어려워집니다.

고정 script는 실행 중 생성되는 외부 결과가 아닙니다. 실습 작성자가 이미 알고 있는 로컬 fixture입니다. 따라서 fixture가 만족해야 하는 기본 형식은 생성자에서 확인하는 편이 더 안전합니다.

## 3. 핵심 개념

구성 단계 검증과 실행 단계 검증은 서로 다른 책임을 가집니다.

- **구성 단계:** immutable non-empty `tuple`, 항목 타입, 필수 문자열, `WorkerResponse.succeeded`의 boolean 여부를 검사한다.
- **실행 단계:** task 수 상한, assignee allow-list, reviewer의 명시적 결정, 사람 승인처럼 현재 workflow 정책과 문맥에 의존하는 규칙을 검사한다.
- **fail-closed:** 검증에 실패하면 fallback 응답, 재시도 추가, 다음 역할 호출 없이 예외로 중단한다.

`DeterministicMockAgent`는 `AgentResponse`, `DeterministicMockCoordinator`는 `DelegationPlan`, `DeterministicMockWorker`는 `WorkerResponse`, `DeterministicMockConflictAgent`는 `ConflictProposal`의 기본 계약을 구성 단계에서 검사합니다.

## 4. 동작 구조

```text
고정 tuple script
      |
      v
생성자 기본 계약 검사
  | 정상                         | 오류
  v                              v
유한 Mock 생성              WorkflowConfigurationError
  |
  v
실행 단계 정책 검사 ----> HumanApproval.APPROVED 후 영향 있는 다음 역할
```

이 경계는 `PENDING`을 `APPROVED`로 바꾸지 않습니다. 유효한 script여도 QA, Worker, DevOps는 각 workflow의 명시적 사람 승인 규칙을 계속 따라야 합니다. `REJECTED`는 Agent 호출 전에 종료하며, malformed fixture의 구성 오류를 approval 값으로 우회할 수도 없습니다.

## 5. 실습 환경

- Python 3.12 이상과 프로젝트의 `uv` 환경이 필요합니다.
- 실행 위치는 저장소 루트입니다.
- 이 실습은 네트워크, live API, secret, 도구 실행, 배포를 사용하지 않습니다.

## 6. 단계별 실습

다음은 비어 있는 고정 Agent 응답을 생성 시점에 거절하는 예입니다.

```python
from ai_platform.agents import (
    AgentResponse,
    DeterministicMockAgent,
    WorkflowConfigurationError,
)

try:
    DeterministicMockAgent(role="planner", responses=(AgentResponse(" "),))
except WorkflowConfigurationError as error:
    print(error)
```

`AgentResponse content must be a non-empty string in a fixed script`가 출력됩니다. Agent의 `act()`는 호출되지 않습니다.

다음 명령으로 계약을 검증합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07/test_immutable_mock_scripts.py -q
```

명령은 고정 script 컨테이너와 항목 계약을 검사합니다.

### 6.2 전체 Volume 07 regression 실행

고정 fixture 계약이 deterministic Mock, bounded loop, explicit human approval의 나머지 local-only 계약과 함께 유지되는지 확인합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07 -q
```

이 명령은 live API, secret, tool 실행, deployment를 호출하지 않습니다. `PENDING`은 안전하게 pause하고, `APPROVED`만 각 workflow에서 이미 검증된 다음 local stage를 열며, `REJECTED`는 pre-call 종료를 유지합니다.

## 7. 코드 설명

각 결정론적 Mock 생성자는 먼저 `validate_fixed_script()`로 `tuple`과 비어 있지 않은 길이를 확인합니다. 이후 role별 검사기가 모든 항목을 순회합니다.

- `AgentResponse.content`는 비어 있지 않은 문자열이어야 하며, `review`는 `ReviewDecision` 또는 `None`이어야 합니다.
- `DelegationPlan`은 비어 있지 않은 summary와 immutable non-empty task tuple을 가져야 합니다. task ID는 script 안에서 중복될 수 없습니다.
- `WorkerResponse.content`는 비어 있지 않아야 하고 `succeeded`는 정확히 boolean이어야 합니다.
- `ConflictProposal.option`과 `rationale`은 모두 비어 있지 않은 문자열이어야 합니다.

allow-list와 최대 task 수는 coordinator Mock이 아니라 `ApprovalGatedDelegationWorkflow`의 정책이므로 실행 시점에 검사합니다.

## 8. 정상 실행 결과

검증 명령의 정상 결과 예시는 다음과 같습니다.

```text
....                                                                     [100%]
4 passed
```

실제 테스트 수는 이후 추가 계약에 따라 달라질 수 있습니다. 핵심 확인 기준은 exit code `0`과 모든 test 통과입니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `responses must contain only AgentResponse values` | tuple에 잘못된 객체를 넣음 | `AgentResponse(...)`로 고정 응답을 만든다. |
| `DelegationPlan tasks must be ... tuple` | 위임 task를 list로 작성함 | task 목록을 `(...)` tuple로 바꾼다. |
| `WorkerResponse succeeded must be a boolean` | `"true"` 또는 `1`을 사용함 | `True` 또는 `False`만 사용한다. |
| `... fixed script` 구성 오류 | 빈 문자열 또는 중복 task ID가 있음 | script fixture를 수정하고 workflow를 다시 생성한다. |

> [!WARNING]
> 구성 오류를 피하려고 빈 fallback 응답을 추가하지 마십시오. fallback은 호출 예산과 audit trail을 바꾸므로 고정 Mock의 목적에 맞지 않습니다.

## 10. 응용 실습

1. `AgentResponse.review`에 문자열 `"approve"`를 넣고 구성 오류를 확인합니다.
2. 두 개의 같은 `task_id`를 포함한 `DelegationPlan`을 만들고 구성 오류를 확인합니다.
3. 유효한 tuple script로 바꾼 뒤, workflow가 여전히 `PENDING`에서 QA 또는 Worker를 호출하지 않는지 기존 테스트로 확인합니다.

## 11. 실무 적용

고정 Mock fixture 검증은 테스트 데이터가 실제 Agent 출력처럼 보이게 만드는 장치가 아닙니다. 재현 가능한 로컬 경계를 만드는 장치입니다. 실제 모델 또는 도구 경계에서 들어오는 값은 신뢰할 수 없으므로 workflow 실행 단계의 protocol 검증도 유지해야 합니다.

> [!TIP]
> 안전 정책을 수정할 때는 먼저 "고정 fixture의 기본 계약"인지 "실행 중 정책"인지 구분하십시오. 전자는 생성자 테스트, 후자는 workflow의 사람 승인·상한·권한 테스트에 둡니다.

## 12. 과제

- **기본:** 각 네 Mock에 잘못된 항목 타입을 넣는 단위 테스트를 작성합니다.
- **응용:** 잘못된 `review` 값과 중복 `task_id`가 구성 전에 중단되는 테스트를 추가합니다.
- **심화:** 신뢰할 수 없는 사용자 구현 Agent가 실행 시점 protocol 검증에서 중단되는 별도 test double을 작성합니다. 승인 게이트를 우회하지 않아야 합니다.

## 13. 완료 체크리스트

- [ ] 고정 script 컨테이너와 항목 계약의 차이를 설명할 수 있다.
- [ ] 네 결정론적 Mock의 항목 타입을 구분할 수 있다.
- [ ] 빈 문자열, 잘못된 boolean, 중복 task ID가 생성자에서 중단되는 것을 확인했다.
- [ ] `PENDING`이 승인으로 바뀌지 않는다는 것을 확인했다.
- [ ] `APPROVED`가 fixture 구성 오류를 우회하지 않고, `REJECTED`가 Agent 호출 전에 종료됨을 확인했다.
- [ ] Volume 07 오프라인 테스트를 통과시켰다.

## 14. 핵심 정리

결정론성은 immutable tuple만으로 완성되지 않습니다. tuple 내부의 고정 fixture도 기본 계약을 만족해야 합니다. 기본 계약은 구성 단계에서 fail-closed하고, 사람 승인과 역할별 정책은 실행 단계에서 계속 검사하면 호출 예산, audit trail, 승인 경계를 함께 보존할 수 있습니다.
