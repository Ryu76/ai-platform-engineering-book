# 06. 결정론적 Mock script 불변성

## 1. 학습 목표

결정론적 Mock은 편의용 fallback 생성기가 아니라 호출 순서와 최대 호출 수를 드러내는 **고정된 유한 script**여야 합니다. 이 장을 마치면 `DeterministicMockAgent`, `DeterministicMockCoordinator`, `DeterministicMockWorker`, `DeterministicMockConflictAgent`에 mutable `list` 대신 immutable `tuple`을 제공하고, script 소진을 다음 호출·fallback 없이 `AgentProtocolError`로 fail-closed하는 이유를 설명할 수 있습니다.

또한 script 불변성은 사람 승인을 대체하지 않음을 확인합니다. 유효한 deterministic Mock도 `PENDING`에서는 QA·Worker·DevOps 같은 gated role을 실행할 수 없고, 각 workflow의 명시적 `APPROVED` 입력이 있어야만 다음 로컬 단계를 진행할 수 있습니다.

## 2. 왜 필요한가

가변 `list`를 script로 허용하면 workflow가 구성된 뒤 외부 코드가 응답을 append하거나 순서를 바꿀 수 있습니다. 그러면 review cycle, Worker retry, conflict round의 호출 예산이 실행 중 달라지고, audit trail이 가리키는 실행 경계도 재현할 수 없습니다.

고정 tuple은 모든 위험을 해결하는 권한 체계가 아닙니다. 그러나 local 교육 fixture의 입력 순서와 길이를 생성 시점에 고정하므로, 의도하지 않은 추가 Agent 호출을 숨기지 않습니다. script가 부족할 때 그럴듯한 응답을 생성하지 않고 오류를 내는 것이 bounded loop와 explicit human approval을 함께 검증하는 방법입니다.

## 3. 핵심 개념

- **결정론적 Mock:** live API, network Agent, tool executor, secret, 환경 조회 없이 미리 정한 local 결과만 순서대로 반환하는 역할 경계입니다.
- **고정 script:** `responses`, `plans`, `proposals`에 전달하는 비어 있지 않은 immutable `tuple`입니다. tuple의 길이가 해당 Mock의 최대 성공 호출 수를 정합니다.
- **구성 단계 검증:** `validate_fixed_script()`가 mutable container 또는 빈 tuple을 `WorkflowConfigurationError`로 첫 Agent 호출 전에 거절합니다.
- **script 소진:** 호출 횟수가 tuple 길이를 넘으면 `AgentProtocolError`가 발생합니다. fallback, 자동 재생성, 무한 재시도는 하지 않습니다.
- **실행 정책과의 분리:** tuple 컨테이너 불변성은 fixture 경계입니다. `max_review_cycles`, `max_worker_attempts`, `max_rounds`, role authority, response schema, 사람 approval은 각 workflow가 별도로 검사합니다.
- **사람 승인:** `PENDING`은 안전한 pause이고 `APPROVED`는 유효하게 검토된 다음 로컬 단계만 엽니다. `REJECTED`는 workflow별로 role 호출 전에 종료합니다.

## 4. 동작 구조

```text
immutable local tuple script
          |
          v
Mock 생성자 + validate_fixed_script()
  | 정상                                  | list / 빈 tuple
  v                                       v
고정된 호출 예산                    WorkflowConfigurationError
  |
  v
bounded workflow run
  | PENDING                              | APPROVED
  v                                      v
approval 대기                    제한된 다음 local role만 호출
  |                                      |
  +--------------------------------------+
                 |
                 v
script 소진 -> AgentProtocolError
(no fallback, no extra loop, no live API or deployment)
```

예를 들어 review workflow의 Developer script 길이가 2이고 `max_review_cycles=2`이면 Developer는 최대 두 번만 응답할 수 있습니다. Reviewer가 세 번째 재작업을 요구하는 설계는 loop 상한에서 멈추거나, 이미 호출한 script가 부족하면 명시적으로 오류를 냅니다. 둘 다 보이지 않는 추가 작업을 하지 않습니다.

## 5. 실습 환경

- Python 3.12 이상과 프로젝트의 `uv` 환경이 필요합니다.
- 실행 위치는 저장소 루트 `E:\python\ai-platform-engineering-book-volume-07`의 bash 또는 WSL 터미널입니다.
- 관련 구현은 `src/ai_platform/agents/workflow.py`, `delegation.py`, `conflict.py`에 있습니다.
- 관련 계약 테스트는 `tests/volume07/test_immutable_mock_scripts.py`와 `tests/volume07/test_immutable_mock_scripts_documentation.py`입니다.
- 이 실습은 repository-local deterministic Mock만 사용합니다. API key, `.env`, live API, network, secret, tool 실행, 파일 변경, deployment 대상이 필요하지 않습니다.

## 6. 단계별 실습

먼저 focused contract를 실행합니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07/test_immutable_mock_scripts.py -q
```

이 테스트는 네 Mock이 mutable script와 잘못된 role을 workflow 실행 전에 거절하고, 정상 tuple script가 소진되면 fallback 없이 멈추는지 확인합니다.

다음으로 문서가 실행 가능한 PRD 학습 형식과 safety scope를 계속 설명하는지 확인합니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07/test_immutable_mock_scripts_documentation.py -q
```

마지막으로 Volume 07 전체 오프라인 회귀 계약을 실행합니다.

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/volume07 -q
```

검증 뒤에는 유효한 fixed script라도 승인 gate를 통과하지 않는다는 것을 기존 예제로 확인할 수 있습니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume07/offline_review_workflow.py
```

기본 실행은 `status=awaiting_human_approval`에서 멈추고 QA를 호출하지 않습니다. 사람 검토 뒤에만 명시적 로컬 flag를 전달합니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume07/offline_review_workflow.py --approve
```

이 completed 경로도 local QA audit만 생성하며 live API, tool 실행, deployment는 수행하지 않습니다.

## 7. 코드 설명

공통 helper는 script가 정확히 비어 있지 않은 tuple인지 확인합니다.

```python
def validate_fixed_script(name: str, script: object) -> None:
    if not isinstance(script, tuple) or not script:
        raise WorkflowConfigurationError(f"{name} must be a non-empty immutable tuple")
```

각 Mock 생성자는 이 helper 뒤에 역할별 기본 항목 계약을 확인합니다.

- `DeterministicMockAgent`는 `AgentResponse`의 비어 있지 않은 `content`와 `ReviewDecision | None` review를 검사합니다.
- `DeterministicMockCoordinator`는 `DelegationPlan`의 summary, immutable task tuple, task ID 고유성을 검사합니다.
- `DeterministicMockWorker`는 `WorkerResponse`의 비어 있지 않은 content와 정확한 boolean `succeeded`를 검사합니다.
- `DeterministicMockConflictAgent`는 `ConflictProposal`의 option과 rationale이 비어 있지 않은 문자열인지 검사합니다.

호출 시 Mock은 `len(calls)`를 script index로 사용합니다. index가 script 길이 이상이면 `AgentProtocolError`를 내므로, hidden retry나 live model fallback이 생기지 않습니다. workflow는 이 결과를 별도로 schema·role authority·bounded-loop 정책으로 검증하며, valid script라는 이유만으로 `PENDING`을 `APPROVED`로 바꾸지 않습니다.

## 8. 정상 실행 결과

focused contract의 실제 test 수는 이후 추가 계약에 따라 달라질 수 있지만, 정상 기준은 exit code `0`과 모든 test 통과입니다. 출력 형태는 다음과 같습니다.

```text
....                                                                     [100%]
4 passed
```

승인 없는 review 예제는 다음처럼 안전하게 멈춥니다.

```text
status=awaiting_human_approval
```

`--approve`를 사람이 명시적으로 선택한 경우에만 다음 형태의 local-only 완료가 나옵니다.

```text
status=completed
1:qa: QA: deterministic checks passed.
```

이 출력은 local audit message일 뿐입니다. deployment 로그, 외부 API 결과, secret, live tool 결과는 존재하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `responses must be a non-empty immutable tuple` | response script에 list 또는 빈 tuple을 전달함 | `responses=(AgentResponse("local response"),)`처럼 non-empty tuple을 전달합니다. |
| `plans must be a non-empty immutable tuple` | Coordinator plan script가 가변이거나 비어 있음 | `plans=(DelegationPlan(...),)`으로 고정하고 생성자를 다시 호출합니다. |
| `proposals must be a non-empty immutable tuple` | conflict proposal script를 list로 작성함 | proposal을 immutable tuple로 바꿉니다. |
| `... mock has no response for call ...` | bounded 호출 수보다 fixed script가 짧음 | loop bound를 무단으로 늘리지 말고, 의도한 유한 호출 예산과 필요한 local fixture 수를 테스트에서 명시합니다. |
| 기본 예제에 QA가 없음 | `PENDING`은 사람 approval 대기 상태임 | audit trail을 검토한 뒤에만 `--approve`를 전달합니다. |

> [!WARNING]
> script 소진을 피하려고 외부 API 호출, fallback response, mutable append, 자동 approval을 추가하지 마십시오. 그런 우회는 deterministic Mock, bounded loop, explicit human approval의 교육 경계를 모두 약화합니다.

## 10. 응용 실습

1. `DeterministicMockWorker`에 `list[WorkerResponse]`를 전달하는 test를 작성하고 Worker 호출 전에 `WorkflowConfigurationError`가 발생하는지 확인합니다.
2. 두 번의 `REVISE`와 길이 2의 Developer tuple을 사용해 `max_review_cycles=2`에서 QA가 호출되지 않는지 확인합니다.
3. valid tuple script로 구성한 delegation workflow를 `PENDING`으로 실행해 Coordinator manifest만 남고 Worker calls가 비어 있는지 확인합니다.
4. script 소진 test에서 exception 뒤에 다른 Agent call, network 요청, tool 실행, deployment가 없음을 call history로 검증합니다.

## 11. 실무 적용

고정 Mock은 교육과 단위 테스트를 위한 local fixture 경계입니다. 실제 Agent runtime의 identity, tool capability, queue, retry policy, persistent memory, deployment authority를 제공하지 않으며 이를 대체하지도 않습니다.

실무에서는 deterministic test fixture를 immutable하게 유지하는 한편, 외부 입력에는 별도 schema validation과 authentication·authorization을 적용해야 합니다. retry와 circuit breaker도 명시적 상한을 가져야 하며, 운영 변경은 test script나 text message가 아니라 별도의 검증 가능한 human approval record와 최소 권한 실행 경계로 보호해야 합니다.

이 Volume 07 slice는 live APIs, secrets, network Agent, tool execution, file mutation, deployments를 사용하거나 구현하지 않습니다.

## 12. 과제

- **기본:** 네 deterministic Mock 각각에 mutable script를 전달해 생성자에서 실패하는 unit test를 작성합니다.
- **응용:** 유효한 tuple script가 소진될 때 동일 역할이 fallback 응답을 만들지 않는지 call history와 `AgentProtocolError`로 고정합니다.
- **심화:** workflow별 최대 loop/attempt 수와 각 Mock script 길이를 표로 문서화하고, `PENDING`이 어떤 gated role도 실행하지 않는 회귀 test를 추가합니다. 실제 API, secret, network, tool, deployment는 추가하지 않습니다.

## 13. 완료 체크리스트

- [ ] immutable tuple과 mutable list가 호출 예산에 미치는 차이를 설명할 수 있다.
- [ ] 네 deterministic Mock이 각각 어떤 fixed script 항목을 받는지 구분할 수 있다.
- [ ] script 소진이 fallback 없이 `AgentProtocolError`가 되는 것을 확인했다.
- [ ] 유효한 fixed script도 `PENDING` approval gate를 우회하지 못함을 확인했다.
- [ ] focused 및 전체 `tests/volume07` 검증을 exit code `0`으로 실행했다.
- [ ] 이 slice가 live API, secret, network Agent, tool 실행, file mutation, deployment를 하지 않음을 확인했다.

## 14. 핵심 정리

결정론적 multi-agent 실습은 "그럴듯한 다음 응답"을 만드는 것이 아니라, 알려진 local script와 유한 호출 예산을 그대로 드러내는 것입니다. immutable non-empty tuple을 구성 단계에서 요구하고 script 소진을 fail-closed하면 bounded loop와 immutable audit trail이 재현 가능합니다. 이 경계는 명시적 human approval과 별개이며, `APPROVED`가 있을 때도 local-only로 제한된 다음 역할만 실행합니다.
