# 03. 다중 Relevance Judgment와 Threshold No-answer

## 학습 목표

실제 검색 평가는 관련/비관련 둘만으로 충분하지 않은 경우가 많습니다. 이 실습은 사람이 검토한 고정 후보에 `0`(비관련), `1`(부분 관련), `3`(강한 관련) grade를 부여하고, reranker가 강한 관련 문서를 위로 올렸는지 **graded nDCG@k**로 확인합니다. 같은 fixture에서 pair score threshold를 적용해 근거가 약한 후보를 답변에 사용하지 않는 no-answer/fallback 계약도 확인합니다.

## 실행

저장소 루트에서 실행합니다.

```bash
uv run python examples/volume06/rerank_fixture.py
uv run pytest tests/unit/test_volume06_reranker.py -q
```

두 명령 모두 고정 한국어 후보와 local lexical scorer만 사용합니다. 네트워크, API 키, 모델 다운로드, GPU, 생성 모델 fallback은 호출하지 않습니다.

## Ordinal judgment와 graded nDCG

`RelevanceJudgment(candidate_id, relevance_grade)`는 다음 계약을 강제합니다.

- `candidate_id`는 비어 있지 않아야 합니다.
- `relevance_grade`는 bool이 아닌 0 이상의 정수여야 합니다.
- 한 evaluation set 안에서 candidate ID는 한 번만 label할 수 있습니다.
- 평가할 `ranked_ids`의 모든 ID에는 명시적 judgment가 있어야 합니다. 누락 judgment를 0으로 조용히 추정하지 않습니다.

`evaluate_graded_ranking(..., k=...)`에서 grade 2 이상은 precision@k, recall@k, MRR의 직접 관련 문서로 취급합니다. grade 1은 문맥상 부분 관련이지만 답변 근거로는 부족한 label입니다. nDCG@k는 `2**grade - 1` gain으로 계산하므로, 부분 관련(1) 문서를 먼저 두는 것보다 강한 관련(3) 문서를 먼저 둘 때 더 높은 값이 나옵니다.

고정 fixture의 첫 두 후보는 retriever 순서에서 `1 → 3`입니다. candidate count가 2 이상이면 lexical reranker는 `3 → 1`로 재정렬합니다. 실제 `candidate_count=2; top_k=1` 행의 strict binary precision은 retriever/reranker `0.000/1.000`이고, 부분 관련과 강한 관련의 차이를 반영하는 평균 graded nDCG도 `0.143/1.000`으로 개선됩니다. 이는 의도적으로 설계한 두 fixture의 local 결과일 뿐, 운영 corpus나 모델의 품질 주장이 아닙니다.

## Threshold와 fail-closed fallback

`rerank_with_threshold(query, candidates, min_score=..., top_k=...)`는 전체 rerank 이후 최상위 `cross_encoder_score`를 `min_score`와 비교합니다.

| 조건 | `outcome` | `selected` | `fallback_reason` |
|---|---|---|---|
| `top_score >= min_score` | `accepted` | 최상위 후보 | `None` |
| `top_score < min_score` | `no_answer` | `None` | `top_score_below_threshold` |

`RerankDecision`은 `ranked`, `top_score`, `min_score`, `outcome`, `fallback_reason`을 보존합니다. 따라서 호출자는 거부된 후보를 답변 근거로 승격하지 않고, local 로그에 실패 이유를 남긴 뒤 안전한 no-answer 메시지 또는 별도 승인된 fallback으로 넘길 수 있습니다. 이 교육용 함수는 fallback 자체를 실행하지 않으므로 외부 호출이나 숨은 답변 생성을 하지 않습니다.

예제의 no-answer fixture는 `휴가 신청 방법` 질의와 무관한 `장애 대응 절차와 연락망입니다.` 후보 하나를 `min_score=1`로 평가합니다. 실제 실행은 다음의 결정론적 decision 값을 출력합니다.

```text
threshold=1; outcome=no_answer; top_score=0; fallback_reason=top_score_below_threshold
```

## 운영으로 확장할 때

threshold는 fixture 숫자를 그대로 복사하지 않습니다. 사람의 relevance judgment가 있는 holdout set에서 candidate count, `top_k`, model version, batch size, timeout, abstention/no-answer 비율, precision·recall·graded nDCG, latency percentile을 함께 기록하고 선택합니다. 불완전한 label, timeout, adapter 오류도 답변 근거를 만들지 않는 fallback 경로로 관측해야 합니다.
