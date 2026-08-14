# 11. 결정론적 Mock 역할 바인딩

## 1. 학습 목표

이 장에서는 결정론적 Mock Agent의 `role` 선언을 workflow에 연결한 경계와 구성 단계에서 대조합니다. 이 장을 마치면 잘못된 Mock을 Planner, Reviewer, QA, DevOps 또는 위임 Worker 위치에 배치했을 때 첫 Agent 호출 전에 중단해야 하는 이유를 설명할 수 있습니다.

## 2. 왜 필요한가

`act(context)` 또는 `propose(context)` 메서드가 호출 가능하다는 사실만으로는 역할 배선이 올바른지 알 수 없습니다. 예를 들어 `role="developer"`로 만든 고정 Mock을 `planner=`에 전달하면, 응답 형식은 정상이어도 audit trail의 책임자가 실제 fixture 의도와 달라집니다.

결정론적 Mock은 테스트 fixture이면서 학습용 역할 모델입니다. 따라서 Mock이 스스로 role을 선언했다면 workflow가 구성될 때 그 선언과 슬롯 이름을 비교해야 합니다. 이 검사는 runtime 응답 검증이나 사람 승인보다 앞선 구성 안전 경계입니다. role 검사가 통과해도 bounded loop의 호출 상한은 그대로이며, 구성 검사는 loop를 늘리거나 새 capability를 부여하지 않습니다.

## 3. 핵심 개념

- **선언 role:** `DeterministicMockAgent`, `DeterministicMockWorker`, `DeterministicMockConflictAgent`가 생성 시 저장하는 비어 있지 않은 `role` 문자열입니다.
- **구성 role:** workflow 생성자의 `planner`, `reviewer`, `devops`, Worker mapping key, conflict Agent mapping key처럼 workflow가 기대하는 역할입니다.
- **선택적 선언:** 실제 adapter처럼 `role` 속성이 없는 protocol 구현체는 계속 구조적 boundary 검사만 받습니다. 이 장의 추가 검사는 role을 명시한 Mock의 fixture 배선 오류를 잡습니다.
- **fail-closed:** 선언 role이 비어 있거나 구성 role과 다르면 `WorkflowConfigurationError`를 발생시키고 어떤 Agent도 호출하지 않습니다.
- **승인과 분리:** `PENDING`은 안전하게 pause하고, `APPROVED`는 올바르게 구성되고 Reviewer가 승인한 실행의 다음 local 단계를 열 뿐이며, `REJECTED`는 Agent 호출 전에 종료합니다. 어느 값도 구성 오류를 우회하지 않습니다.

## 4. 동작 구조

```text
workflow 생성자
      |
      v
callable act/propose 경계 검사
      |
      v
role 속성이 선언되었는가?
  | 아니오                    | 예
  v                           v
기존 protocol 경계 유지   선언 role == 구성 role ?
                                | 예              | 아니오
                                v                 v
                         workflow 생성 가능  WorkflowConfigurationError
                                                   |
                                                   v
                                         Agent 호출 0회, audit trail 없음
```

## 5. 실습 환경

- Python 3.12 이상과 프로젝트의 `uv` 환경이 필요합니다.
- 명령 실행 위치는 저장소 루트의 bash 또는 WSL 터미널입니다.
- 실습은 repository-local deterministic Mock만 사용합니다. live API, network, secret, tool 실행, 배포는 사용하지 않습니다.

## 6. 단계별 실습

먼저 새 구성 경계를 확인합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07/test_declared_mock_role_binding.py -q
```

이 테스트는 다음 네 경우를 고정합니다.

1. `developer` Mock을 Planner 슬롯에 전달한다.
2. `qa` Mock을 DevOps 슬롯에 전달한다.
3. `reviewer` Worker를 `writer` mapping key에 전달한다.
4. `reviewer` conflict Mock을 `planner` mapping key에 전달한다.

모든 경우 생성자에서 `WorkflowConfigurationError`가 발생하고, coordinator·peer·후속 Agent를 포함한 호출 기록은 비어 있어야 합니다.

이 Chapter의 문서 계약도 실행합니다. 이 테스트는 14개 학습 section, role binding 경계, bounded loop와 명시적 사람 승인의 분리를 계속 확인합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07/test_declared_mock_role_binding_documentation.py -q
```

전체 Volume 07의 offline 계약도 실행합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07 -q
```

## 7. 코드 설명

공통 `validate_declared_role()`은 `role` 속성이 없는 adapter를 거절하지 않습니다. 반대로 Mock처럼 role을 공개하는 boundary는 공백이 아닌 문자열인지 확인하고 기대 역할과 정확히 비교합니다.

```python
if declared_role is None:
    return
if not isinstance(declared_role, str) or not declared_role.strip():
    raise WorkflowConfigurationError("declared role must be a non-empty string")
if declared_role != expected_role:
    raise WorkflowConfigurationError("declared role must match the configured role")
```

`BoundedReviewWorkflow`와 release handoff는 `validate_agent_boundary()` 내부에서 이 검사를 사용합니다. 위임 workflow는 Worker mapping의 assignee, conflict workflow는 Agent mapping의 role을 expected role로 전달합니다. Coordinator는 역할별 실행자가 아니라 manifest 생성 boundary이므로 이 slice에서는 별도 role label을 요구하지 않습니다.

## 8. 정상 실행 결과

첫 명령은 exit code `0`으로 끝납니다. 검사 항목은 네 개이며, 각 항목은 잘못된 구성 때문에 실행이 멈췄음을 검증합니다. 전체 Volume 07 테스트도 exit code `0`이어야 합니다.

정상으로 배선된 기존 예제는 그대로 실행할 수 있습니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run python examples/volume07/offline_review_workflow.py
```

기본 실행은 role 검증 뒤에도 `status=awaiting_human_approval`에서 멈춥니다. 이 결과는 role 일치가 QA 승인이나 완료를 자동으로 허용하지 않음을 보여 줍니다. `PENDING`은 pause, `APPROVED`는 gated local QA만 허용, `REJECTED`는 첫 Agent 호출 전에 종료한다는 explicit human approval 경계도 독립적으로 유지됩니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `planner declared role must match 'planner'` | Planner 슬롯에 다른 role의 Mock을 전달함 | `DeterministicMockAgent(role="planner", ...)`를 전달합니다. |
| `worker for writer declared role must match 'writer'` | Worker의 `role`과 `workers` mapping key가 다름 | Worker role과 assignee key를 같은 값으로 맞춥니다. |
| `agent for planner declared role must match 'planner'` | conflict Agent의 fixture role과 mapping key가 다름 | proposal Mock의 role과 `agents` key를 맞춥니다. |
| `... declared role must be a non-empty string` | custom boundary가 공백 또는 문자열이 아닌 `role` 속성을 노출함 | `role` 속성을 제거해 adapter로 사용하거나 올바른 role 문자열로 고칩니다. |

> [!WARNING]
> 이 검사는 identity 인증 체계가 아닙니다. local deterministic Mock의 fixture 배선 오류를 fail-closed하는 학습용 경계입니다. 실제 runtime에서는 인증된 identity, 권한 정책, 입력·출력 schema, 별도 approval record를 함께 사용해야 합니다.

## 10. 응용 실습

1. `role="researcher"` Mock을 Developer 슬롯에 전달하는 테스트를 작성하고 Reviewer가 호출되지 않는지 확인합니다.
2. `role` 속성이 없는 작은 adapter test double이 기존 `act(context)` protocol로 workflow를 구성할 수 있는지 확인합니다.
3. role-to-agent mapping을 immutable fixture factory로 만들고 key와 Mock role을 동시에 생성하도록 개선합니다.

## 11. 실무 적용

실제 Agent runtime에서 단순 문자열 role은 신뢰할 수 있는 identity가 아닙니다. service account, signed workload identity 또는 정책 엔진에서 부여한 principal과 권한을 사용해야 합니다. 또한 role 검증은 tool 권한, release 승인, 사람 검토의 대체물이 아닙니다. 이 예제처럼 각 경계를 분리하고, 구성 오류는 외부 호출 전에 중단하는 원칙만 유지합니다.

Volume 07의 이 lesson은 deterministic local Mock만 다룹니다. live API, network Agent, secret 조회, tool 실행, 파일 변경, deployment는 구현하거나 실행하지 않습니다. `completed`는 외부 변경이 아니라 명시적으로 승인된 local audit 결과일 뿐입니다.

## 12. 과제

- **기본:** Release handoff에서 `developer` Mock을 QA 슬롯에 배치하는 구성 실패 테스트를 작성합니다.
- **응용:** Worker role과 allow-list key의 불일치가 coordinator 호출 전 중단되는지 테스트합니다.
- **심화:** role declaration이 property 접근 중 예외를 내는 boundary를 만들고 configuration error로 안전하게 변환되는지 검증합니다.

## 13. 완료 체크리스트

- [ ] 선언 role과 구성 role의 차이를 설명할 수 있다.
- [ ] 결정론적 Mock의 잘못된 역할 배선이 첫 호출 전에 거절됨을 확인했다.
- [ ] role 없는 protocol adapter가 구조적 boundary 검사를 계속 사용할 수 있음을 이해한다.
- [ ] role 일치가 사람 승인, tool 권한, production identity를 대체하지 않음을 설명할 수 있다.
- [ ] Volume 07 offline 테스트를 통과시켰다.

## 14. 핵심 정리

결정론적 Mock이 role을 선언했다면 workflow는 그 label과 구성 슬롯을 대조해야 합니다. 이 작은 구성 단계 검사는 역할 책임이 잘못된 fixture 배선으로 바뀌는 일을 막고, bounded loop·runtime response 검증·명시적 사람 승인보다 앞선 fail-closed 경계를 제공합니다.