# 02. 고정 후보 수와 Top-k Sweep

## 학습 목표

이 실습은 같은 두 개의 결정론적 한국어 fixture를 `candidate_count=1..3`, `top_k=1..candidate_count`로 잘라서, retriever와 reranker의 `precision@k`, `recall@k`, MRR, nDCG@k를 로컬에서 함께 비교합니다. 각 행은 rerank에 실제로 투입한 pair 수와 local elapsed nanoseconds도 출력합니다.

## 실행

저장소 루트에서 다음을 실행합니다.

```bash
uv run python examples/volume06/rerank_fixture.py
```

네트워크, API 키, 다운로드 모델, GPU를 사용하지 않습니다. `elapsed_ns`는 실행 호스트의 부하·CPU·Python 환경에 따라 달라지므로 fixture의 회귀 기준이 아닙니다. 품질 지표와 `pair_evaluations`만 결정론적인 회귀 값입니다.

## 후보 수와 출력 수의 경계

- `candidate_count`: 1차 retriever가 reranker에 넘긴 앞쪽 후보 수입니다. 이 수만큼 query-candidate pair를 모두 평가합니다.
- `top_k`: 전체 후보의 pair scoring과 정렬이 끝난 뒤 호출자에게 돌려줄 결과 수입니다.
- `pair_evaluations`: 이 교육용 lexical scorer가 비교한 pair 수입니다. 이 예제에서는 한 질의에 `candidate_count`와 같고, 두 fixture의 합계가 행에 출력됩니다. 실제 모델의 비용·금액·처리량 측정값은 아닙니다.

따라서 `top_k`를 3에서 1로 줄여도 이 구현의 pair 비교 수는 줄지 않습니다. 실제 latency나 비용을 낮추려면 reranker 입력인 `candidate_count`를 줄여야 하지만, retriever가 관련 문서를 그 범위 안에 넣지 못하면 reranker는 복구할 수 없습니다.

## `measure_rerank` 계약

`measure_rerank(query, candidates, top_k=...)`는 후보 유효성 검사를 마친 뒤 `perf_counter_ns`로 **rerank 본문만** 감쌉니다. 결과 `RerankMeasurement`는 다음을 보존합니다.

- `ranked`: top-k 적용 뒤 순위
- `candidate_count`: 입력 후보 수
- `pair_evaluations`: 실제 pair scoring 수
- `elapsed_ns`: local monotonic clock의 종료값 - 시작값

테스트는 주입 가능한 clock으로 `elapsed_ns=45` 같은 재현 가능한 계약을 확인합니다. 음수 clock 값, 문자열 clock 값, callable이 아닌 clock, 뒤로 가는 clock은 fail-closed로 거부합니다. 실제 wall-clock 수치를 테스트에서 고정하지 않으므로 다른 개발 환경의 일시적 변동을 성능 회귀로 오인하지 않습니다.

## 고정 fixture에서 읽는 trade-off

두 fixture 모두 첫 후보는 관련 문서가 아니고 두 번째 후보가 관련 문서입니다.

| 후보 수 | 관찰 |
|---:|---|
| 1 | 관련 문서가 candidate set 밖에 있어 retriever와 reranker 모두 recall·MRR·nDCG가 0입니다. pair 평가 합계는 2입니다. |
| 2 | 관련 문서가 set에 들어옵니다. `top_k=1`에서 reranker가 이를 1위로 올려 모든 품질 지표가 1.0이지만 retriever는 0입니다. pair 평가 합계는 4입니다. |
| 3 | 세 번째 비관련 후보가 늘어 pair 평가 합계는 6입니다. `top_k=2` 또는 `3`에서는 recall은 이미 1.0이고 precision 분모만 커집니다. reranker의 MRR/nDCG는 관련 문서를 1위에 두므로 retriever보다 높습니다. |

이 표는 의도적으로 설계한 작은 fixture의 설명이며, 운영 corpus나 특정 모델의 지연시간·비용·품질에 대한 주장이 아닙니다.

## 다음 실험의 안전한 확장

대표 운영 평가를 하기 전에도 고정 fixture로 다중 relevance judgment, no-answer/fallback, threshold 거부, batch 상한과 timeout fallback의 계약을 추가할 수 있습니다. 운영 평가에서는 모델 버전, tokenizer, hardware, batch size, candidate count, timeout, 측정 반복 수와 percentile latency를 함께 기록하고 사람이 검토한 relevance judgment로 판단해야 합니다.
