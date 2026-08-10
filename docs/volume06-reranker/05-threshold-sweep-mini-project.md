# 05. Threshold Sweep와 안전한 Rerank 미니 프로젝트

## 1. 학습 목표

고정 relevance judgment가 있는 evaluation set에서 여러 threshold를 비교하고, acceptance/no-answer 비율과 선택 결과의 품질을 함께 해석합니다. 또한 retriever 후보를 받아 local Cross-Encoder rerank, threshold 결정, 구조화된 결과를 만드는 최소 end-to-end 경계를 구현합니다.

## 2. 왜 필요한가

낮은 threshold는 더 많은 후보를 답변 근거로 통과시켜 recall을 지킬 수 있지만, 약한 근거도 통과시킬 위험이 있습니다. 높은 threshold는 약한 결과를 거부하지만 유효한 결과까지 no-answer로 만들 수 있습니다. 한 threshold마다 pair scoring을 다시 실행하면 비교 대상 정책마다 비용과 latency가 중복되어 policy 차이와 실행 비용이 섞입니다.

이 장은 하나의 rerank 결과에 여러 threshold만 적용하는 offline sweep으로 이 문제를 분리합니다. fixture의 lexical score는 교육용 값이므로 운영 threshold로 복사하지 않습니다.

## 3. 핵심 개념

- **threshold sweep**: 같은 query, candidate, pair score에서 최소 score 정책만 바꾸어 결과를 비교하는 offline evaluation입니다.
- **acceptance rate**: 전체 query 중 `outcome="accepted"`인 비율입니다. 나머지는 `no_answer`입니다.
- **conditional precision**: 선택된 query만 분모로 삼은 precision입니다. 거부된 query를 숨길 수 있으므로 acceptance rate와 함께 봐야 합니다.
- **effective precision/recall**: no-answer query는 선택 결과가 없는 것으로 0을 부여해 전체 query 기준으로 계산한 @1 지표입니다.
- **shared pair work**: `measure_threshold_sweep`은 후보마다 한 번만 pair scoring합니다. threshold 개수는 `pair_evaluations`를 늘리지 않습니다.

> [!WARNING]
> 이 fixture에서 threshold를 바꿔도 이미 계산한 pair score의 latency와 비용은 줄지 않습니다. 실제 비용을 줄이려면 candidate count, model, batch size 또는 model call 자체를 바꾸어야 합니다. threshold가 실행 전에 model inference를 생략하게 하는 별도 cascade 정책은 이 장의 범위가 아닙니다.

## 4. 동작 구조

```text
Retriever candidates + human judgments
                 │
                 ▼
      LexicalCrossEncoder pair scoring × N
                 │  (한 query에 한 번)
                 ▼
          ranked candidates / top score
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
 threshold=303 threshold=304 threshold=305
       │         │         │
    accepted  partial no-answer  all no-answer
       └─────────┴─────────┴─────────┘
                 │
                 ▼
acceptance + conditional/effective quality + shared pair work
```

## 5. 실습 환경

- 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
- 구현: `src/ai_platform/reranker/cross_encoder.py`
- 고정 fixture: `examples/volume06/rerank_fixture.py`
- 검증: `tests/unit/test_volume06_reranker.py`
- 필요 도구: 프로젝트에 설치된 `uv`

외부 API, API key, secrets, 모델 다운로드, GPU, 배포는 사용하지 않습니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume06/rerank_fixture.py
uv run pytest tests/unit/test_volume06_reranker.py -q
```

첫 명령은 candidate/top-k sweep, threshold sweep, adapter fixture와 no-answer fixture를 실행합니다. 두 번째 명령은 threshold sweep이 candidate를 한 번만 score하고 policy별 결과를 보존하는지 확인합니다.

## 6. 단계별 실습

### 6.1 score 한 번으로 정책을 비교한다

```python
from ai_platform.reranker import Candidate, measure_threshold_sweep

sweep = measure_threshold_sweep(
    "비밀번호 재설정 방법",
    (
        Candidate("policy", "비밀번호 정책", 0.99),
        Candidate("recovery", "비밀번호 재설정 방법", 0.71),
    ),
    min_scores=(303, 304),
    top_k=1,
)

assert sweep.rerank_measurement.pair_evaluations == 2
assert [decision.outcome for decision in sweep.decisions] == ["accepted", "no_answer"]
```

`min_scores`는 비어 있으면 안 되고, bool이 아닌 0 이상의 서로 다른 정수여야 합니다. 중복 policy는 측정에 정보를 더하지 않고 결과 해석을 혼동시키므로 fail-closed로 거부합니다.

### 6.2 선택과 거부를 구분한다

각 `RerankDecision`은 원래 `ranked`를 관측용으로 보존하지만, `selected is None`이면 downstream이 어떤 후보도 답변 근거로 사용하면 안 됩니다.

```python
for decision in sweep.decisions:
    if decision.selected is None:
        assert decision.outcome == "no_answer"
        assert decision.fallback_reason == "top_score_below_threshold"
    else:
        candidate_id = decision.selected.candidate.candidate_id
        print(candidate_id)
```

이 미니 프로젝트의 output contract는 `selected` 여부, `outcome`, `fallback_reason`, candidate ID, threshold, model/fixture version을 분리해 보존하는 것입니다. query text, candidate 원문, API key 같은 민감 값을 무단으로 log에 넣지 않습니다.

### 6.3 fixture 지표를 해석한다

예제는 두 query × 세 candidate에서 `1`, `303`, `304`, `305`를 비교합니다. `303`은 두 fixture의 최고 score를 통과시키고, `304`는 score 304인 한 query만 통과시키며, `305`는 모두 거부합니다. score와 pair count는 fixture에서 결정론적이고 `shared_elapsed_ns`만 실행 host에 따라 달라집니다.

## 7. 코드 설명

`measure_threshold_sweep`은 먼저 `min_scores` 계약을 검증하고 `measure_rerank`를 정확히 한 번 호출합니다. 그 결과 `RerankMeasurement`는 candidate 수, pair 수, local elapsed와 top-k ranking을 보존합니다. 이후 각 threshold는 `_threshold_decision`에 같은 ranking을 전달합니다.

따라서 네 정책을 비교해도 두 query × 세 candidate의 shared pair work는 6입니다. `RerankDecision`을 새로 만들 때만 policy가 달라지고 model score나 순위는 다시 계산하지 않습니다. 이 경계는 offline policy evaluation에 적합하며 실제 model의 provider 비용이나 p95 latency를 대신하지 않습니다.

## 8. 정상 실행 결과

2026-08-10에 실제 실행한 fixture는 다음 threshold 행을 출력했습니다. `shared_elapsed_ns`는 host-dependent 관측값입니다.

```text
threshold=1; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=2/2; acceptance_rate=1.000; conditional_precision=1.000; effective_precision=1.000; effective_recall=1.000
threshold=303; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=2/2; acceptance_rate=1.000; conditional_precision=1.000; effective_precision=1.000; effective_recall=1.000
threshold=304; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=1/2; acceptance_rate=0.500; conditional_precision=1.000; effective_precision=0.500; effective_recall=0.500
threshold=305; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=0/2; acceptance_rate=0.000; conditional_precision=0.000; effective_precision=0.000; effective_recall=0.000
```

`conditional_precision=1.000`만 보면 threshold 304가 좋아 보일 수 있습니다. 하지만 전체 query 중 절반이 no-answer가 되어 effective recall도 0.500입니다. 이 때문에 production policy는 acceptance와 전체 품질을 함께 비교해야 합니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `min_scores must not be empty` | 비교할 policy가 없음 | 0 이상의 threshold를 하나 이상 전달합니다. |
| `min_scores must not contain duplicates` | 같은 policy가 반복됨 | 고유 threshold만 남깁니다. |
| `min_scores must be a non-negative integer` | 음수, bool, 문자열 threshold | score domain에 맞는 정수를 전달합니다. |
| `outcome=no_answer` | top score가 policy를 통과하지 못함 | `selected`를 사용하지 말고 `fallback_reason`을 관측합니다. holdout judgment에서 threshold를 재검토합니다. |
| `shared_elapsed_ns`가 실행마다 다름 | local clock은 host 부하 영향을 받음 | pair count와 fixture quality만 회귀 기준으로 사용합니다. |

## 10. 응용 실습

1. 세 번째 고정 query와 0/1/3 relevance judgment를 추가하고, threshold별 acceptance 및 effective recall이 어떻게 바뀌는지 테스트합니다.
2. score 302와 303이 혼재한 fixture를 만들어 boundary equality(`top_score >= min_score`)가 accepted인지 확인합니다.
3. `AdapterRerankResult.outcome`까지 포함한 순수 local event formatter를 작성합니다. query와 candidate 원문 대신 stable ID, outcome, fallback reason, pair count만 출력합니다.

## 11. 실무 적용

운영 threshold는 fixture의 303/304를 사용하지 않습니다. model ID/version, tokenizer, candidate count, batch size, timeout, retriever version을 고정한 holdout set에서 policy 후보를 평가해야 합니다. 각 policy마다 precision@k, recall@k, graded nDCG@k, acceptance/no-answer rate, timeout/error/fallback rate, p50/p95/p99 latency와 비용을 함께 기록합니다.

Conditional precision이 좋아도 no-answer가 과도하면 사용자 가치가 낮아질 수 있습니다. 반대로 acceptance가 높아도 weak evidence가 통과하면 안전하지 않습니다. fallback은 Cross-Encoder 통과 결과와 같은 출처로 표시하면 안 되며, adapter 실패에는 기본 no-answer 또는 명시적 retriever fallback 계약을 유지합니다.

## 12. 과제

- **기본:** `min_scores=(303, 304)`의 sweep에서 pair evaluations가 2이고 결과가 accepted/no-answer인지 테스트합니다.
- **응용:** 두 query의 selected/no-answer 결과에서 effective precision과 effective recall을 계산하고 acceptance rate와 비교합니다.
- **심화:** 사람의 holdout judgment를 준비한 뒤 model version별 threshold 후보를 비교하는 offline report schema를 설계합니다. 외부 model call은 mock만 사용하고 실제 API key나 배포는 사용하지 않습니다.

## 13. 완료 체크리스트

- [x] 같은 pair ranking에 여러 threshold를 적용한다.
- [x] threshold 개수와 무관하게 candidate당 한 번만 pair scoring한다.
- [x] acceptance/no-answer와 conditional/effective quality를 분리해 측정한다.
- [x] 빈값, 중복, 음수, bool, 문자열 threshold를 fail-closed로 검증한다.
- [x] 선택되지 않은 후보를 answer evidence로 쓰지 않는 contract를 확인한다.
- [ ] 사람의 holdout judgment와 실제 model latency/cost로 production threshold를 결정한다.

## 14. 핵심 정리

Threshold는 reranking 이후의 선택 정책입니다. policy sweep은 같은 score를 재사용해 pair work를 중복하지 않고 acceptance와 no-answer의 품질 trade-off를 보여 줍니다. 전체 query 기준 지표, conditional precision, fallback 출처를 함께 기록해야 안전한 rerank 경로를 설계할 수 있습니다.
