# Volume 08 Router 설계 학습자 체크리스트

이 체크리스트는 Volume 08의 고정 fixture 실습을 처음부터 다시 실행한 뒤 학습자가 직접 표시하는 항목입니다. 모든 기본 경로는 로컬 Python 코드와 테스트만 사용하며, 실제 LLM·embedding·HTTP API·Agent·Tool·Model 실행은 하지 않습니다.

## 환경과 실행

- [ ] 저장소 루트에서 `uv run pytest tests/unit/test_volume08_policy_router.py -q`를 실행했다.
- [ ] `examples/volume08/`의 Policy, Rule, Keyword, 평가, fallback, Semantic, LLM, escalation, API, 미니 프로젝트 예제를 실행했다.
- [ ] 각 예제가 API 키, 환경 변수, 네트워크 연결 없이 실행됨을 확인했다.
- [ ] `uv run pytest -q`로 전체 로컬 회귀를 실행했다.

## 정책과 결정론성

- [ ] `RouteTarget`, `RoutingRequest`, `RoutingRequirements`, `RouteDecision`의 역할을 설명할 수 있다.
- [ ] Rule Router가 검증된 request capability를 명시적 rule로 판정하고, 추가 capability를 policy에 재검증함을 설명할 수 있다.
- [ ] capability, allowlist, 비용, 지연 시간, health가 `PolicyRouter` 선택에 미치는 영향을 설명할 수 있다.
- [ ] 비용 → 지연 시간 → 이름 순 동점 해소가 왜 필요한지 설명할 수 있다.
- [ ] 정책상 대상이 없을 때 임의 target 대신 `NoEligibleRouteError`로 실패해야 함을 이해한다.

## intent Router와 평가

- [ ] Keyword Router의 token match, confidence threshold, intent capability 추가 과정을 설명할 수 있다.
- [ ] Semantic Router가 실제 embedding 대신 request ID별 고정 score fixture를 사용하는 이유를 설명할 수 있다.
- [ ] LLM Router가 prompt나 raw response 없이 검토된 intent·confidence fixture만 보관하는 이유를 설명할 수 있다.
- [ ] 모든 classifier 결과가 `PolicyRouter`를 다시 통과해야 함을 확인했다.
- [ ] 고정 평가 dataset의 routing accuracy와 safety failure 결과를 해석할 수 있다.

## 복구와 다단계 전환

- [ ] fallback이 같은 요청 정책으로 primary 뒤의 제한된 Router만 시도함을 확인했다.
- [ ] retry budget이 0이면 fallback이 실행되지 않고 fail closed 함을 설명할 수 있다.
- [ ] escalation이 Agent·Tool·Model stage를 고정 fixture 순서와 budget 안에서만 시도함을 확인했다.
- [ ] escalation 중에도 request allowlist, capability, 비용, 지연 시간, health 제약이 유지됨을 확인했다.

## API, 로그, 미니 프로젝트

- [ ] Router API가 strict JSON body를 검증하고 `400 INVALID_ROUTING_REQUEST`와 `422 NO_ELIGIBLE_ROUTE`를 구분함을 확인했다.
- [ ] API layer가 Router 정책을 재구현하거나 임의 fallback을 추가하지 않음을 설명할 수 있다.
- [ ] 모든 decision 및 안전 실패 로그가 strict JSON 직렬화 가능하며 `NaN`/`Infinity`를 포함하지 않음을 확인했다.
- [ ] `render_audit_report()`가 export 직전에 audit report를 다시 검증하고 key 정렬 compact JSON을 결정론적으로 출력함을 확인했다.
- [ ] 미니 프로젝트 audit report가 고정된 여덟 경로를 빠짐없이 포함하고, 각 경로가 자기 Router의 고정 field schema와 allowlist만 사용하며 해당 request 원문의 부분 문자열을 포함하지 않음을 확인했다.
- [ ] audit report의 decision 값은 비어 있지 않은 문자열이고, 순서 field는 비어 있지 않은 문자열 `list`, retry·escalation counter는 부울이 아닌 0 이상의 정수, API status code는 `100`~`599` 정수임을 확인했다.
- [ ] 로그와 API body에 사용자 원문, prompt, raw classifier output, API 키가 없어야 함을 확인했다.
- [ ] `router_mini_project.py`가 Policy, Keyword, Semantic, LLM, fallback, escalation, API를 하나의 고정 request ID 집합으로 조합함을 확인했다.
- [ ] Volume 09 workflow에는 `request_id`, target 정보, 원문 없는 audit record, 안전 실패 계약만 인계해야 함을 확인했다.

## 완료 확인 명령

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume08/router_mini_project.py
uv run pytest tests/unit/test_volume08_router_mini_project.py -q
uv run pytest tests/unit/test_volume08_router_audit.py -q
uv run pytest -q
```

> [!NOTE]
> PRD의 공유 Glossary 항목은 `docs/glossary.md`에 추가해야 합니다. 이 branch의 허용 변경 범위에는 공유 문서 수정이 포함되지 않으므로, Volume 08 완료 표시는 해당 항목을 별도 승인 범위에서 처리한 뒤에만 추가합니다.
