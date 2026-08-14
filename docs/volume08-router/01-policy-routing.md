# 정책 기반 Router: 기능·비용·지연 시간으로 안전하게 선택하기

## 1. 학습 목표

이 장을 마치면 정적 정책(Policy)만으로 Agent, Tool, Model 후보를 비교하고, 필요한 기능(capability), 허용 비용, 허용 지연 시간, 허용 대상 목록을 모두 만족하는 대상을 선택할 수 있습니다. 외부 LLM, 임베딩 모델, 실시간 가격표 없이 고정 fixture로 같은 결정을 재현하고 최소 결정 로그를 남기는 방법도 익힙니다.

## 2. 왜 필요한가

요청 문장에 키워드가 포함되었다는 이유만으로 실행 대상을 고르면, 권한이 없는 Tool이나 비용 한도를 넘는 Model을 선택할 수 있습니다. 반대로 모든 요청을 가장 싼 대상에 보내면 필요한 검색·코드·검토 기능이 부족할 수 있습니다.

정책 Router는 모델의 추측보다 먼저 검증 가능한 운영 조건을 적용합니다. 이 장의 정책은 상태가 정상인 후보만 남기고, 기능·권한·비용·지연 시간 조건을 모두 통과한 후보 중 비용, 지연 시간, 이름 순서로 선택합니다. 입력과 대상 fixture가 같으면 결과도 같습니다.

> [!WARNING]
> `estimated_cost`와 `estimated_latency_ms`는 이 실습에서 외부 가격 API나 관측 시스템으로 가져오지 않는 **정적 추정값**입니다. 운영 환경에서는 검증된 가격·관측 데이터의 갱신 주기와 단위를 별도로 관리해야 합니다. 사용자 원문, 인증 헤더, API 키를 결정 로그에 기록하지 마세요.

## 3. 핵심 개념

- **Capability(기능):** 대상이 수행할 수 있다고 선언한 작업입니다. 요청의 필수 기능은 대상 기능의 부분집합이어야 합니다.
- **허용 대상 목록:** 권한 또는 테넌트 정책 때문에 선택해도 되는 대상 이름을 제한합니다. 목록이 있으면 그 밖의 대상은 제외합니다.
- **비용·지연 시간 한도:** 후보의 정적 추정값이 각각 상한 이하일 때만 통과합니다.
- **Fail closed:** 통과 후보가 없으면 임의의 대상을 고르지 않고 `NoEligibleRouteError`를 발생시킵니다. Fallback과 escalation은 다음 실습에서 명시 정책으로 추가합니다.
- **결정론적 동점 해소:** 비용이 같으면 지연 시간이 짧은 대상, 그것도 같으면 이름이 사전순으로 앞선 대상을 고릅니다.

`Decimal`을 사용해 비용을 비교합니다. 부동소수점 오차, 음수, `NaN`, `Infinity`는 설정 오류로 거부합니다.

## 4. 동작 구조

```text
RoutingRequest
  ├── request_id, text
  └── RoutingRequirements
       ├── required_capabilities
       ├── maximum_cost
       ├── maximum_latency_ms
       └── permitted_target_names
                │
                ▼
          PolicyRouter
  정상 상태 ──► 허용 대상 ──► 기능 포함 ──► 비용/지연 한도
                │
                ▼
  (estimated_cost, estimated_latency_ms, target.name) 최소 후보
                │
                ▼
       RouteDecision.as_log_record()
       └── 원문 없이 요청 ID, 정책, 대상, 근거, 추정치
```

## 5. 실습 환경

이번 슬라이스의 파일은 다음과 같습니다.

- `src/ai_platform/router/base.py`: 요청·대상·결정 계약과 입력 검증입니다.
- `src/ai_platform/router/policy.py`: 결정론적 후보 선택 정책입니다.
- `examples/volume08/policy_router.py`: 고정 fixture를 사용하는 실행 예제입니다.
- `tests/unit/test_volume08_policy_router.py`: 외부 호출 없는 계약 테스트입니다.

의존성을 준비합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
conda env update --file environment.yml --prune
```

이 명령은 프로젝트와 검사 도구를 준비합니다. 예제는 네트워크·환경 변수·API 키를 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 고정 fixture 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
python examples/volume08/policy_router.py
```

예제에는 요약 기능을 가진 `general-agent`, 검색·요약 기능을 가진 `research-agent`, 요약 기능을 가진 `offline-summary-model`이 있습니다. 요청은 요약 기능, 비용 `0.005` 이하, 지연 시간 `150ms` 이하를 요구합니다. `general-agent`와 Model은 비용을 통과하지만 Model이 더 짧은 지연 시간을 가지므로 선택됩니다.

### 6.2 계약 테스트 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/unit/test_volume08_policy_router.py -q
```

테스트는 비용·지연 시간·이름 동점 해소, 기능·비용·지연 시간·허용 대상 조건, 비정상 대상 제외, 후보 부재 시 안전 실패, 원문을 제외한 로그, 잘못된 설정 거부를 검증합니다.

### 6.3 코드 읽기

`PolicyRouter.route()`는 후보를 먼저 필터링한 뒤 다음 키의 최소값을 사용합니다.

```python
selected = min(
    candidates,
    key=lambda target: (
        target.estimated_cost,
        target.estimated_latency_ms,
        target.name,
    ),
)
```

따라서 목록 작성 순서가 같다는 우연에 의존하지 않습니다. `RouteDecision.as_log_record()`는 `text`를 받지 않으므로 결정 로그에 원문을 넣는 실수를 줄입니다.

## 7. 코드 설명

`RouteTarget`은 이름, 유형(`agent`, `tool`, `model`), 기능 집합, 추정 비용, 추정 지연 시간, 정상 상태를 불변 dataclass로 보관합니다. `RoutingRequirements`는 요청마다 적용할 제약입니다. `PolicyRouter`는 대상 목록에 중복 이름이 있으면 시작 시 거부합니다. 이름이 중복되면 로그와 운영 지표가 어느 대상을 뜻하는지 알 수 없기 때문입니다.

후보 검사는 다음 순서입니다.

1. `healthy`가 `True`인지 확인합니다.
2. 허용 대상 목록이 있으면 대상 이름이 목록에 있는지 확인합니다.
3. 모든 필수 capability가 대상에 있는지 확인합니다.
4. 비용과 지연 시간 상한을 초과하지 않는지 확인합니다.
5. 남은 후보를 명시한 동점 해소 규칙으로 선택합니다.

이 장은 아직 자연어 Intent 분류, semantic 유사도, LLM 분류, 재시도, fallback 실행을 하지 않습니다. 그 기능은 이 안전한 계약 위에 다음 슬라이스에서 추가합니다.

## 8. 정상 실행 결과

검증 시 예제는 다음처럼 JSON 한 줄을 출력했습니다. JSON 키는 보기 좋게 정렬되어 있으며, `target_name`이 `offline-summary-model`인 것을 확인합니다.

```text
{"confidence": "1", "estimated_cost": "0.002", "estimated_latency_ms": "90", "policy_name": "offline-learning-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-policy-001", "target_kind": "model", "target_name": "offline-summary-model"}
```

검증 시 단위 테스트 결과는 다음과 같았습니다.

```text
10 passed
```

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `no healthy target meets the routing requirements` | 모든 대상이 비정상이거나, 기능·비용·지연 시간·허용 목록 중 하나가 후보를 모두 제외했을 수 있습니다. | 대상 fixture와 `RoutingRequirements`를 하나씩 비교합니다. 조건을 몰래 무시하지 말고, 후속 장에서 명시적 fallback 정책을 추가합니다. |
| `target capabilities must not be empty` | 대상이 할 수 있는 기능을 선언하지 않았습니다. | 대상 책임을 나타내는 최소 한 개 이상의 capability를 추가합니다. |
| `estimated_cost must be a finite nonnegative Decimal` | 비용에 `float`, 음수, `NaN`, `Infinity`를 사용했습니다. | `Decimal("0.002")` 형태의 0 이상 유한 값을 사용합니다. |
| 같은 요청이 다른 대상으로 이동함 | fixture의 비용·지연 시간·이름 또는 요구 조건이 변경됐을 수 있습니다. | 테스트 fixture를 고정하고, 정책 변경 시 기대 결정을 테스트에서 명시적으로 갱신합니다. |

## 10. 응용 실습

`examples/volume08/policy_router.py`에 `retrieve` capability를 요구하는 두 번째 요청을 추가하세요. `research-agent`만 `retrieve`를 가지므로, 비용과 지연 시간 한도를 충족하도록 설정하면 이 Agent가 선택되어야 합니다. 이어서 `permitted_target_names`에서 해당 이름을 제거해 `NoEligibleRouteError`가 발생하는 단위 테스트를 작성하세요. 외부 API나 실제 가격표를 사용하지 마세요.

## 11. 실무 적용

운영 Router는 capability를 단순 문자열이 아니라 권한·데이터 경계·테넌트·승인 상태와 연결해야 합니다. 비용은 요청당 추정값과 일·월 예산을 분리하고, latency는 p50만이 아니라 p95/p99와 대기열을 고려합니다. 상태는 health check와 circuit breaker의 결과를 반영합니다. 실패한 후보와 제외 근거를 관측 가능하게 남기되, 사용자 원문과 비밀값은 마스킹하거나 기록하지 않습니다.

정책 변경은 버전 이름, fixture, 회귀 테스트를 함께 커밋해야 합니다. 그래야 비용표 또는 대상 책임 변경이 어떤 요청에 영향을 주는지 비교할 수 있습니다.

## 12. 과제

- **기본:** 같은 비용·지연 시간의 두 대상에 이름만 다르게 주고 사전순 선택을 검증하는 테스트를 작성합니다.
- **응용:** `TOOL` 유형 대상을 추가하고, capability와 허용 대상 목록이 모두 맞을 때만 선택되는 사례를 만듭니다.
- **심화:** fallback을 추가할 때도 권한과 필수 capability를 우회하지 않도록 어떤 추가 계약이 필요한지 설계합니다. 실제 Tool 호출은 추가하지 마세요.

## 13. 완료 체크리스트

- [ ] capability와 비용·지연 시간 한도의 역할을 설명할 수 있다.
- [ ] 허용 대상 목록이 권한 경계가 되는 이유를 설명할 수 있다.
- [ ] 후보가 없을 때 임의 선택 대신 안전 실패가 필요한 이유를 설명할 수 있다.
- [ ] 비용, 지연 시간, 이름의 결정론적 동점 해소 순서를 설명할 수 있다.
- [ ] `pytest tests/unit/test_volume08_policy_router.py -q`를 외부 호출 없이 실행했다.
- [ ] 결정 로그에 사용자 원문과 비밀값을 넣지 않았다.

## 14. 핵심 정리

정책 Router는 자연어 분류보다 먼저 실행 가능한 경계를 정합니다. 정상 상태, 권한, 기능, 비용, 지연 시간 조건을 모두 통과한 후보만 선택하고, 동점 해소 규칙도 코드와 테스트로 고정합니다. 이 기반이 있어야 keyword, semantic, LLM Router가 낸 후보도 비용·권한·장애 정책 안에서 안전하게 사용할 수 있습니다.
