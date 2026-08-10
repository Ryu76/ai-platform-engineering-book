# 06. Volume 완료 점검, Volume 07 인계, 용어 정리

## 1. 목적

이 마지막 장은 Volume 06의 local reranker 학습 경로를 검증 가능한 산출물로 닫고, 다음 Volume이 재사용해야 할 입력·출력·관측 contract를 명확히 합니다. 여기서 완료는 fixture의 회귀 검증 완료를 뜻하며 production 품질 승인, 배포, 실제 모델 연결을 뜻하지 않습니다.

## 2. 완료 범위

이 Volume에서 구현하고 검증한 범위는 다음과 같습니다.

- 고정 `Candidate`를 query-document pair로 다시 점수화하는 결정론적 `LexicalCrossEncoder`
- binary 및 graded relevance judgment 기반의 precision@k, recall@k, MRR, nDCG@k
- candidate count와 output `top_k` sweep, pair evaluation 수, monotonic local elapsed 관측
- threshold equality, accepted/no-answer, `selected` fail-closed contract
- 하나의 pair scoring 결과를 재사용하는 threshold-policy sweep
- batch와 전체 timeout budget을 갖는 Cross-Encoder adapter 경계
- timeout, adapter error, malformed score에서 partial score를 폐기하는 no-answer 또는 명시적 retriever fallback

외부 API, API key, secret, 모델 다운로드, GPU, 배포, live corpus는 이 Volume의 범위 밖입니다.

## 3. 최종 로컬 검증

저장소 루트에서 아래 명령을 실행합니다.

```bash
uv run pytest tests/unit/test_volume06_reranker.py -q
uv run ruff check src/ai_platform/reranker examples/volume06 tests/unit/test_volume06_reranker.py
uv run mypy src/ai_platform/reranker examples/volume06
uv run python examples/volume06/rerank_fixture.py
uv run python scripts/validate_links.py
uv run python scripts/validate_docs.py
uv run python scripts/validate_code_blocks.py
```

`elapsed_ns`와 `shared_elapsed_ns`는 host 부하에 따라 달라지는 관측값이므로 정수 자체를 회귀 기준으로 쓰지 않습니다. 반면 고정 fixture의 candidate 수, pair evaluation 수, rank, outcome, fallback reason, binary/graded ranking metric은 회귀 기준입니다.

## 4. 학습자 완료 체크리스트

- [x] retriever score와 pair-based Cross-Encoder score가 다른 신호임을 구분한다.
- [x] candidate count가 retriever recall의 상한을 정하고, `top_k`가 score 작업이 아니라 출력만 제한함을 확인한다.
- [x] binary relevance와 ordinal relevance judgment를 분리하고 graded nDCG를 해석한다.
- [x] `top_score >= min_score` 경계에서만 후보를 `selected`로 승격한다.
- [x] `selected is None`인 `no_answer` 결과를 answer evidence로 사용하지 않는다.
- [x] threshold policy 수와 무관하게 candidate마다 한 번만 pair scoring하는 sweep을 확인한다.
- [x] adapter의 batch 입력 순서, 남은 timeout budget, score cardinality를 검증한다.
- [x] timeout/error 뒤 partial Cross-Encoder score를 폐기하고 fallback의 출처를 보존한다.
- [x] deterministic fixture로 local ranking metric과 pair work를 재측정한다.
- [ ] 사람의 holdout judgment, 승인된 model/version, 운영 corpus로 production threshold를 결정한다.

마지막 항목은 의도적으로 미완료입니다. 이 교육용 fixture는 production threshold·quality·latency·비용을 승인할 근거가 아닙니다.

## 5. 안전한 소비 contract

다음 소비 규칙은 다음 Volume에서도 유지해야 합니다.

| 결과 | downstream 허용 동작 | 반드시 보존할 관측값 |
|---|---|---|
| `RerankDecision.outcome == "accepted"` | `selected` 후보만 answer evidence 후보로 전달 | threshold, top score, candidate ID, outcome |
| `RerankDecision.outcome == "no_answer"` | answer evidence를 전달하지 않고 안전한 no-answer 경로를 선택 | threshold, top score, `top_score_below_threshold` |
| `AdapterRerankResult.outcome == "reranked"` | `rank_source == "cross_encoder"` 결과만 Cross-Encoder rank로 취급 | model ID/version, batch/pair count, elapsed, outcome |
| `AdapterRerankResult.outcome == "retriever_fallback"` | 명시적으로 허용된 retriever 순위만 사용 | `rank_source == "retriever_fallback"`, fallback reason |
| `AdapterRerankResult.outcome == "no_answer"` | 후보를 생성/답변 근거로 승격하지 않음 | fallback reason, batch/pair count, elapsed |

query 원문, candidate 원문, 사용자 식별자, API key나 secret은 이 local event contract에 무단으로 넣지 않습니다. 안정적인 candidate ID와 구조화된 outcome만 사용합니다.

## 6. Volume 07 인계

Volume 07이 rerank 결과를 downstream answer-generation 또는 orchestration 경계에 연결할 때, 다음 입력을 명시적으로 받습니다.

```python
from ai_platform.reranker import RerankDecision


def evidence_candidate_id(decision: RerankDecision) -> str | None:
    if decision.selected is None:
        return None
    return decision.selected.candidate.candidate_id
```

다음 Volume은 `None`을 빈 문자열, 임의의 top-ranked candidate, 또는 Cross-Encoder 성공으로 바꾸면 안 됩니다. 필요하다면 별도 no-answer UX나 명시적 retriever fallback policy를 설계하되, fallback 결과를 `cross_encoder` 출처로 표기하지 않습니다.

인계 시 고정해야 할 evaluation metadata는 다음과 같습니다.

1. retriever/model/tokenizer의 식별 가능한 version
2. candidate count, output `top_k`, batch size, timeout, threshold
3. relevance judgment schema와 relevant grade cutoff
4. accepted/no-answer/fallback count 및 fallback reason
5. pair evaluations와 local elapsed의 측정 정의

## 7. 재평가 순서

실제 모델이나 corpus로 확장하는 작업은 다음 순서로 진행합니다.

1. 사람 검토 relevance judgment가 있는 holdout set을 versioned fixture로 고정합니다.
2. retriever와 reranker의 model/version, candidate count, `top_k`, batch size, timeout을 기록합니다.
3. threshold 후보마다 같은 precomputed score 또는 동일 실행 조건에서 precision@k, recall@k, MRR, graded nDCG, acceptance/no-answer/fallback rate를 비교합니다.
4. latency는 p50/p95/p99, 비용은 model call과 pair work의 실제 정의로 별도 수집합니다.
5. 안전성·품질·운영 소유자가 holdout 결과를 검토한 뒤에만 policy를 승인합니다.

이 단계는 live API call, secret 또는 배포를 요구할 수 있으므로 본 Volume의 offline fixture 검증과 분리합니다.

## 8. Volume 06 용어

| 용어 | 이 Volume에서의 의미 |
|---|---|
| Retriever | 많은 문서에서 후보를 1차로 찾고 원래 score를 제공하는 단계입니다. |
| Candidate | stable ID, text, retriever score를 가진 불변 1차 검색 후보입니다. |
| Bi-Encoder | query와 document를 독립 encoding해 빠르게 후보를 찾는 일반적 retriever 방식입니다. |
| Cross-Encoder | query-document pair를 함께 평가해 후보별 relevance score를 다시 계산하는 방식입니다. |
| Pair evaluation | query 하나와 candidate 하나를 scorer에 전달한 한 번의 비교입니다. |
| Candidate count | reranker가 실제 pair scoring에 받은 후보 수입니다. 이 범위 밖 relevant document는 reranker가 회복할 수 없습니다. |
| Top-k | 전체 rerank 뒤 consumer에 반환할 상위 결과 수입니다. 이 구현에서 pair work를 줄이지 않습니다. |
| Relevance judgment | 사람이 부여한 candidate별 평가 label입니다. reranker score와 다른 근거입니다. |
| Graded relevance | 0 이상의 ordinal relevance grade입니다. grade 2 이상은 binary 직접 관련으로 사용합니다. |
| nDCG | 높은 grade의 relevant candidate를 상위에 둘수록 높아지는 ranking metric입니다. |
| Threshold | 최상위 rerank score가 후보 선택을 통과해야 하는 최소값입니다. |
| No-answer | 충분한 근거 후보를 선택하지 않는 fail-closed outcome입니다. |
| Fallback | reranker 실패 뒤 적용하는 명시적 대체 경로입니다. retriever fallback은 Cross-Encoder 결과가 아닙니다. |
| Acceptance rate | 전체 query 가운데 threshold를 통과해 `accepted`가 된 비율입니다. |
| Conditional precision | accepted query만 분모로 하는 precision입니다. no-answer 비율을 숨길 수 있습니다. |
| Effective precision/recall | no-answer를 0으로 포함한 전체 query 기준 품질입니다. |
| Timeout budget | 전체 rerank deadline에서 각 adapter batch가 사용할 수 있는 남은 시간입니다. |
| Partial-score discard | timeout/error 후 성공한 이전 batch를 포함한 Cross-Encoder score를 ranking evidence로 쓰지 않는 규칙입니다. |
| Rank source | 순위가 `cross_encoder`인지 `retriever_fallback`인지 구별하는 provenance field입니다. |

## 9. 핵심 정리

Volume 06은 deterministic fixture에서 reranking의 품질·비용 대용 지표·지연시간 관측·threshold·fallback 경계를 분리해 검증했습니다. 다음 단계는 이 contract를 유지한 채, 사람 judgment가 있는 holdout evaluation으로 실제 model policy를 검증하는 것입니다.
