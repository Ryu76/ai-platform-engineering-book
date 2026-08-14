# Keyword Router: confidence threshold와 정책 경계를 함께 적용하기

## 1. 학습 목표

이 장에서는 외부 LLM·임베딩·API 호출 없이 고정 keyword fixture로 intent를 분류하고, 명시적인 confidence threshold를 통과한 결과만 정책 Router에 전달합니다. Keyword가 발견됐다는 사실만으로 Agent나 Tool을 실행하지 않습니다. 선택된 intent의 필수 capability를 기존 요청 제약과 합친 뒤, `PolicyRouter`가 상태·허용 대상·비용·지연 시간을 다시 검증합니다.

## 2. 왜 두 Router를 분리하는가

Keyword는 빠르고 재현 가능하지만, 키워드가 있다고 권한이나 예산을 보장하지는 않습니다. 예를 들어 `refund` keyword가 `refund_request` intent에 일치해도, 환불 capability를 지닌 대상이 허용 목록 밖에 있거나 비용 한도를 넘으면 선택하면 안 됩니다.

이 실습의 경계는 다음과 같습니다.

```text
RoutingRequest.text
       │
       ▼
KeywordRouter
  ├── Unicode token case-folding
  ├── 고정 keyword rule 일치
  ├── confidence threshold
  └── (confidence, 일치 수, intent 이름) 결정론적 선택
       │
       ▼
RoutingRequirements + intent.required_capabilities
       │
       ▼
PolicyRouter
  ├── healthy
  ├── permitted_target_names
  ├── required_capabilities
  ├── maximum_cost
  └── maximum_latency_ms
       │
       ▼
KeywordRouteDecision.as_log_record()
```

`KeywordRouter`는 단일 token keyword만 허용합니다. `refund`는 `refund.`와 대소문자 차이를 무시하고 일치하지만, `refunding`처럼 부분 문자열만 겹치는 단어에는 일치하지 않습니다. 다중 단어 구문, semantic 유사도, LLM intent 분류는 후속 슬라이스의 별도 정책으로 다룹니다.

## 3. 고정 fixture 실행

```bash
# 실행 위치: 저장소 루트
python examples/volume08/keyword_router.py
pytest tests/unit/test_volume08_keyword_router.py -q
```

예제의 `order_tracking` rule은 `order`, `tracking` keyword와 confidence `0.90`을 사용합니다. Router의 최소 confidence는 `0.80`입니다. `order-support-agent`만 `lookup_order`와 `respond_support` capability를 모두 제공하고, 요청의 비용·지연 시간·허용 대상 제한도 통과하므로 선택됩니다.

검증 시 예제는 다음 JSON 한 줄을 출력합니다. `text`와 API 키 같은 비밀값은 포함하지 않습니다.

```text
{"classifier_confidence": "0.90", "classifier_name": "offline-keyword-intent-router", "confidence": "1", "estimated_cost": "0.003", "estimated_latency_ms": "80", "intent": "order_tracking", "matched_keywords": ["order", "tracking"], "policy_name": "offline-support-policy", "reason": "healthy-capability-cost-latency-policy", "request_id": "lesson-08-keyword-001", "target_kind": "agent", "target_name": "order-support-agent"}
```

## 4. Rule과 threshold 정의

`KeywordRoute`에는 intent, keyword 집합, 해당 intent가 반드시 요구하는 capability, 고정 confidence를 선언합니다. `KeywordRouter`에는 `minimum_confidence`를 반드시 선언합니다.

```python
KeywordRoute(
    intent="order_tracking",
    keywords=frozenset({"order", "tracking"}),
    required_capabilities=frozenset({"lookup_order", "respond_support"}),
    confidence=Decimal("0.90"),
)
```

confidence와 threshold는 모두 `Decimal`의 유한한 `0` 이상 `1` 이하 값이어야 합니다. 실습에서는 모델 확률을 추정하지 않습니다. fixture에 명시한 confidence가 threshold를 통과하는지를 검증할 뿐입니다. 따라서 다른 사람이 같은 fixture와 입력을 실행하면 결과도 같습니다.

일치한 rule이 없거나 모든 일치 rule이 threshold 미만이면 `NoConfidentKeywordRouteError`로 안전하게 실패합니다. 이 오류는 fallback 대상을 임의로 실행하지 않습니다. fallback·재시도·escalation은 별도의 명시 정책과 테스트가 갖춰진 후에만 추가합니다.

## 5. 결정론적 rule 선택

여러 rule이 threshold를 통과하면 아래 순서대로 하나를 고릅니다.

1. 더 높은 `confidence`
2. 더 많은 일치 keyword 수
3. 사전순으로 앞선 `intent` 이름

이 순서는 rule 선언 순서에 의존하지 않습니다. 같은 입력의 처리 결과가 fixture 배열의 우연한 순서에 따라 달라지는 문제를 피합니다.

선택 후 Router는 원래 `required_capabilities`와 rule의 `required_capabilities`를 합집합으로 만들어 `PolicyRouter`에 전달합니다. 따라서 keyword intent는 기존 요청의 capability, 허용 대상, 예산, latency 제한을 약화시키지 못합니다. 후보가 없으면 `NoEligibleRouteError`가 발생합니다.

## 6. 계약 테스트가 검증하는 내용

`tests/unit/test_volume08_keyword_router.py`는 고정 fixture만 사용해 다음을 확인합니다.

- 대소문자·문장부호 차이를 제거한 token 일치와 intent별 capability 결합
- confidence·일치 keyword 수·intent 이름의 결정론적 rule 선택
- threshold 미달 및 부분 문자열만 겹치는 입력의 안전 실패
- `permitted_target_names`와 capability 정책을 keyword가 우회하지 못함
- JSON 직렬화 가능한 결정 로그와 사용자 원문 누락
- 다중 token keyword, 범위를 벗어난 confidence, `NaN` threshold 같은 잘못된 fixture 거부

## 7. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `no keyword route meets the configured confidence threshold` | 일치 rule이 없거나 일치 rule의 confidence가 threshold보다 낮습니다. | 입력 token, 고정 rule, threshold를 비교합니다. 임의 fallback을 추가하지 마세요. |
| `no healthy target meets the routing requirements` | intent capability와 요청 정책을 모두 만족하는 대상이 없습니다. | 대상 capability, 허용 목록, 비용, latency, 상태를 확인합니다. Keyword rule의 capability를 제거해 우회하지 마세요. |
| `each keyword must contain exactly one nonempty token` | phrase keyword를 넣었습니다. | 이 슬라이스에서는 단일 token으로 고정하거나, phrase 정책을 별도 계약과 테스트로 설계합니다. |
| 같은 입력이 다른 intent로 이동함 | rule confidence, keyword 집합, intent 이름이 바뀌었습니다. | fixture와 기대 결과를 함께 검토하고 회귀 테스트를 갱신합니다. |

## 8. 완료 체크리스트

- [ ] 고정 keyword rule과 confidence threshold가 왜 명시적으로 필요한지 설명할 수 있다.
- [ ] token 일치와 부분 문자열 일치의 차이를 설명할 수 있다.
- [ ] intent가 capability·허용 대상·예산·latency 정책을 우회하면 안 되는 이유를 설명할 수 있다.
- [ ] threshold 미달 시 `NoConfidentKeywordRouteError`로 안전 실패하는 것을 확인했다.
- [ ] `pytest tests/unit/test_volume08_keyword_router.py -q`를 외부 호출 없이 실행했다.
- [ ] 결정 로그에 사용자 원문과 비밀값을 넣지 않았다.

## 9. 핵심 정리

Keyword Router는 빠른 intent 후보 선택기이지 실행 권한자가 아닙니다. 고정 token fixture와 explicit threshold로 선택을 재현하고, intent capability를 원래 요청 제약에 더한 뒤 PolicyRouter의 안전 경계를 다시 통과시킵니다. 이 구조가 있어야 이후 semantic·LLM 분류와 fallback도 권한·비용·장애 정책 안에서 추가할 수 있습니다.
