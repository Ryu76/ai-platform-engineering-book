# 12. 접근 불가 Agent 경계의 구성 단계 차단

## 1. 학습 목표

이 장에서는 Agent protocol의 `act(context)` 또는 `propose(context)`를 읽는 과정 자체가 실패할 수 있음을 다룹니다. 이 장을 마치면 property·adapter가 accessor 예외를 내더라도 Agent 실행 전 `WorkflowConfigurationError`로 안전하게 종료해야 하는 이유를 설명할 수 있습니다.

## 2. 왜 필요한가

구성 검증은 보통 `callable(getattr(boundary, "act", None))`처럼 보입니다. 하지만 `act`나 `propose`가 property 또는 동적 adapter attribute이면 `getattr()`가 예외를 낼 수 있습니다. 예외를 그대로 내보내면 호출자가 안정적인 workflow 구성 오류와 내부 accessor 오류를 구분할 수 없고, 서로 다른 workflow가 서로 다른 방식으로 실패할 수 있습니다.

Volume 07은 이 읽기 단계도 workflow 실행 전 구성 경계로 취급합니다. `act` 또는 `propose` accessor가 실패하면 원래 예외를 원인으로 보존하면서 `WorkflowConfigurationError`로 변환합니다. 이 정책은 Agent를 호출하거나, audit trail을 추가하거나, 승인 결정을 소비하기 전에 적용됩니다.

## 3. 핵심 개념

- **경계 발견:** workflow 생성자가 protocol method를 읽고 callable인지 검사하는 구성 단계입니다.
- **접근 불가 경계:** `act` 또는 `propose` property 접근이 예외를 내는 local adapter/test double입니다.
- **안정적 fail-closed 오류:** `WorkflowConfigurationError`는 boundary 이름과 method 이름을 포함하며 원래 accessor 예외를 `__cause__`로 연결합니다.
- **호출 0회:** 생성자에서 중단되므로 Planner·Coordinator·peer·Worker·QA·DevOps는 호출되지 않고 audit trail도 생성되지 않습니다.
- **승인과 분리:** 이 검증은 `PENDING`, `APPROVED`, `REJECTED`보다 먼저 일어납니다. 승인 값은 잘못된 구성 경계를 우회하지 못합니다.

## 4. 동작 구조

```text
workflow 생성자
      |
      v
act/propose attribute 읽기
  | 성공                       | accessor 예외
  v                            v
callable 검사              WorkflowConfigurationError
  | 예                         |
  v                            v
role 선언 검사          Agent 호출 0회 / audit trail 없음
  |
  v
workflow 구성 가능
```

`act`를 사용하는 review/release handoff/Worker 경계와 `propose`를 사용하는 delegation Coordinator/conflict Agent 경계는 같은 안전한 발견 규칙을 사용합니다.

## 5. 실습 환경

- Python 3.12 이상과 프로젝트의 `uv` 환경이 필요합니다.
- 명령 실행 위치는 저장소 루트의 bash 또는 WSL 터미널입니다.
- 모든 검증은 repository-local deterministic Mock과 local test double만 사용합니다. live API, network, secret, tool 실행, 배포는 사용하지 않습니다.

## 6. 단계별 실습

새 경계 계약만 실행합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07/test_inaccessible_agent_boundaries.py -q
```

테스트의 local test double은 실제 Agent를 구현하거나 호출하지 않습니다.

```python
class UnreadableActBoundary:
    @property
    def act(self) -> object:
        raise RuntimeError("local test boundary accessor failed")
```

테스트는 다음 네 구성을 고정합니다.

1. review workflow의 Planner `act` accessor
2. release handoff의 DevOps `act` accessor
3. delegation workflow의 Coordinator `propose` accessor
4. conflict workflow의 Planner `propose` accessor

각 경우 생성자는 `WorkflowConfigurationError`를 발생시키며 유효한 peer Mock의 `calls`도 빈 목록으로 유지되어야 합니다.

전체 Volume 07 offline 계약도 실행합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07 -q
```

## 7. 코드 설명

공통 helper는 protocol method의 attribute access를 명시적으로 감쌉니다.

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

이 helper는 `act`/`propose` method를 **호출하지 않습니다**. 오직 구성 단계에서 읽고 callable 여부만 확인합니다. 기존의 role 선언 검사와 runtime response schema 검사는 그 뒤에 별도 경계로 남습니다.

## 8. 정상 실행 결과

두 pytest 명령은 exit code `0`으로 끝나야 합니다. 첫 명령은 네 가지 inaccessible accessor 구성을 확인합니다. 전체 Volume 07 테스트도 local Mock만으로 통과해야 합니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `planner act boundary could not be read` | Planner adapter의 `act` attribute 접근이 예외를 냄 | property 초기화·adapter 구성을 수정하거나 안전한 callable `act(context)`를 제공합니다. |
| `coordinator propose boundary could not be read` | Coordinator의 `propose` accessor가 설정 중 실패함 | 실행 전에 local configuration을 수정하고 재구성합니다. |
| `... must provide a callable ...` | attribute는 읽혔지만 callable이 아님 | 올바른 protocol method를 제공합니다. |
| 승인했는데도 구성 실패 | `APPROVED`는 구성 오류를 해제하지 않음 | 먼저 boundary를 수정한 뒤 새 workflow를 만듭니다. |

> [!WARNING]
> 이 예제는 local adapter의 구성 오류를 안정적으로 보고하는 학습용 경계입니다. production 환경에서는 인증된 identity, schema validation, 권한 정책, 별도 사람 승인 record와 함께 사용해야 하며, accessor를 읽는 과정이 side effect를 만들지 않도록 설계해야 합니다.

## 10. 응용 실습

1. `role` property가 예외를 내는 adapter가 `WorkflowConfigurationError`로 변환되는지 테스트합니다.
2. non-callable `act` property와 accessor 예외의 오류 메시지가 구분되는지 확인합니다.
3. adapter factory가 protocol method를 단순 method로 노출하도록 고쳐 property 기반 discovery를 피합니다.

## 11. 완료 체크리스트

- [ ] protocol method의 attribute access도 구성 단계임을 설명할 수 있다.
- [ ] inaccessible `act`/`propose` 경계가 Agent 호출 전에 중단됨을 확인했다.
- [ ] accessor 예외와 non-callable protocol 오류의 차이를 이해한다.
- [ ] 이 검사가 사람 승인·identity·tool 권한을 대체하지 않음을 설명할 수 있다.
- [ ] Volume 07 offline 테스트를 통과시켰다.

## 12. 핵심 정리

Agent protocol의 method를 읽는 일도 boundary configuration의 일부입니다. 읽기 실패를 안정적인 `WorkflowConfigurationError`로 fail-closed하면 bounded loop, deterministic Mock, runtime schema 검증, 명시적 사람 승인보다 앞서 local wiring 오류를 차단할 수 있습니다.
