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


class UnreadableProposeBoundary:
    @property
    def propose(self) -> object:
        raise RuntimeError("local test boundary accessor failed")
```

두 local test double 모두 protocol method를 **호출하지 않습니다**. 첫 class는 review/release의 `act(context)` 경계를, 두 번째 class는 delegation/conflict의 `propose(context)` 경계를 구성 단계에서 실패하게 합니다.

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

## 11. 실무 적용

운영 adapter는 `act` 또는 `propose` 속성을 읽는 동안 network 연결, secret 조회, tool 초기화, 파일 변경을 해서는 안 됩니다. workflow 구성은 **발견과 검증**만 수행하고, 실제 capability 획득과 외부 작업은 별도 실행 경계로 미룹니다. 그러면 구성 오류를 live API 호출이나 deployment 전에 재현할 수 있습니다.

구체적인 운영 설계에서는 다음 책임을 분리합니다.

1. adapter factory는 side-effect 없는 callable protocol method를 노출합니다.
2. workflow는 callable signature, role, input/output schema, bounded loop를 검증합니다.
3. 승인 서비스는 `PENDING`/`APPROVED`/`REJECTED` 결정의 승인자, scope, 시각, 만료를 별도 immutable record로 검증합니다.
4. tool executor는 approval text가 아니라 allow-list와 최소 권한 policy를 다시 검사합니다.

> [!WARNING]
> `WorkflowConfigurationError`가 없다는 사실은 adapter가 안전하다는 증명도, 사람 승인이 유효하다는 증명도 아닙니다. 이는 local workflow가 호출할 수 있는 형태의 boundary를 발견했다는 뜻뿐입니다.

## 12. 과제

### 기본

- `act` property가 `RuntimeError`를 내는 local boundary를 만들고, `WorkflowConfigurationError`의 `__cause__`가 원래 예외인지 확인합니다.
- non-callable `propose` attribute와 accessor 예외가 서로 다른 안정적인 오류 메시지를 내는 test를 작성합니다.

### 응용

- `role` property가 예외를 내는 local adapter가 첫 Agent call 전에 fail-closed하는지 확인합니다.
- `validate_callable_boundary()`가 context-compatible signature를 검사하지만 protocol method 자체는 호출하지 않는 이유를 설명합니다.

### 심화

- production adapter factory의 구성 단계와 실행 단계의 dependency graph를 그립니다. configuration 단계에는 live API client, secret, tool executor, deployment client를 넣지 마십시오.
- 사람 승인 record와 agent boundary configuration을 서로 다른 immutable schema로 설계합니다. `APPROVED` 값 하나가 capability object를 전달하지 못하게 해야 합니다.

## 13. 완료 체크리스트

- [ ] protocol method의 attribute access도 구성 단계임을 설명할 수 있다.
- [ ] inaccessible `act`/`propose` 경계가 Agent 호출 전에 중단됨을 확인했다.
- [ ] accessor 예외와 non-callable protocol 오류의 차이를 이해한다.
- [ ] `PENDING`, `APPROVED`, `REJECTED`가 잘못된 boundary configuration을 우회하지 못함을 설명할 수 있다.
- [ ] adapter discovery가 live API, secret, tool 실행, 파일 변경, deployment를 수행하지 않아야 함을 확인했다.
- [ ] `tests/volume07/test_inaccessible_agent_boundaries.py`와 Volume 07 offline test를 통과시켰다.

## 14. 핵심 정리

Agent protocol의 method를 읽는 일도 boundary configuration의 일부입니다. 읽기 실패를 안정적인 `WorkflowConfigurationError`로 fail-closed하면 bounded loop, deterministic Mock, runtime schema 검증, 명시적 사람 승인보다 앞서 local wiring 오류를 차단할 수 있습니다. 이 구성 경계는 실행 권한이나 운영 승인을 만들지 않으며, `PENDING`/`APPROVED`/`REJECTED` 사람 결정과 tool capability는 별도 정책으로 유지해야 합니다.
