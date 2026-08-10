# 04. Batched Cross-Encoder Adapter와 Timeout Fallback

## 1. 학습 목표

이 장을 마치면 Bi-Encoder/Retriever가 만든 `Candidate` 목록과 실제 Cross-Encoder model client의 책임을 분리하고, batch 크기와 전체 deadline을 적용해 rerank할 수 있습니다. 또한 timeout 또는 model 오류 뒤에 부분 score를 답변 근거로 사용하지 않는 fallback 결과를 관측할 수 있습니다.

## 2. 왜 필요한가

Retriever는 넓은 문서 집합에서 후보를 빠르게 찾습니다. Cross-Encoder는 질의와 각 후보를 함께 입력하므로 top-N 품질을 높일 수 있지만, 후보 수만큼 pair inference가 필요합니다. 따라서 다음 문제가 생깁니다.

- model library 또는 HTTP client를 reranker의 `Candidate` 계약에 직접 섞으면 교체와 테스트가 어렵습니다.
- batch가 너무 크면 한 요청의 메모리와 지연 시간이 커질 수 있습니다.
- batch마다 별도 timeout을 주면 전체 rerank 시간이 `batch 수 × timeout`까지 늘어날 수 있습니다.
- 첫 batch가 성공한 뒤 다음 batch가 timeout되어도 부분 Cross-Encoder score만으로 순위를 만들면, 나머지 후보와 공정하게 비교할 수 없습니다.

이 slice는 실제 model client를 연결할 수 있는 adapter 경계와 전체 deadline 정책을 만들고, 외부 모델을 다운로드하거나 호출하지 않는 fixture로 계약을 검증합니다.

## 3. 핵심 개념

- **Bi-Encoder/Retriever 경계**: upstream retrieval은 stable ID, text, original `retriever_score`를 가진 `Candidate`만 전달합니다. reranker는 새 문서를 검색하지 않습니다.
- **Cross-Encoder model 경계**: `CrossEncoderModel.predict(pairs, timeout_ns=...)`는 입력 pair와 같은 순서의 유한 score를 반환합니다. model provider, tokenizer, model loading, HTTP transport는 이 protocol 뒤에 둡니다.
- **`CrossEncoderModelAdapter`**: `(query, candidate.text)` pair를 순서 보존으로 만들고 남은 timeout budget을 model에 전달합니다.
- **`BatchRerankPolicy`**: `max_batch_size`와 전체 `timeout_ns`를 함께 고정합니다. 각 batch의 budget은 `전체 deadline - 이미 경과한 시간`입니다.
- **fail-closed fallback**: timeout, adapter exception, score 개수 불일치, 비유한 score는 부분 score를 폐기합니다. 기본값 `fallback="no_answer"`는 빈 ranking을 반환합니다. 호출자가 명시적으로 `fallback="retriever"`를 허용할 때만 retriever score 순위를 반환하며, 각 결과의 `rank_source="retriever_fallback"`, `cross_encoder_score=None`으로 출처를 표시합니다.

## 4. 동작 구조

```text
Bi-Encoder / Retriever
  └─ Candidate(id, text, retriever_score) × N
                              │
                              ▼
                  BatchRerankPolicy(max_batch_size, deadline)
                              │
              ┌───────────────┴────────────────┐
              ▼                                ▼
CrossEncoderModelAdapter                 remaining timeout budget
  └─ (query, candidate.text) batch ──> CrossEncoderModel.predict(...)
              │                                │
              ▼                                ▼
all batches complete                    timeout / error / malformed score
              │                                │
              ▼                                ▼
rank_source=cross_encoder        partial scores discarded
                                 ├─ default: outcome=no_answer
                                 └─ explicit: outcome=retriever_fallback
```

> [!WARNING]
> 동기 `predict` 호출을 Python 코드만으로 강제 중단할 수는 없습니다. production adapter는 전달받은 `timeout_ns`를 HTTP client timeout, inference server deadline 또는 executor cancellation에 실제로 연결해야 합니다. 호출이 반환된 뒤 deadline을 넘긴 경우에도 이 구현은 score를 채택하지 않지만, 이미 소모된 wall time을 되돌릴 수는 없습니다.

## 5. 실습 환경

- 실행 위치: 저장소 루트의 bash/WSL 터미널
- 파일: `src/ai_platform/reranker/cross_encoder.py`, `examples/volume06/rerank_fixture.py`
- 필요한 명령: 프로젝트에 이미 설치된 `uv`
- 외부 API, API key, model download, GPU는 사용하지 않습니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume06/rerank_fixture.py
uv run pytest tests/unit/test_volume06_reranker.py -q
```

첫 명령은 고정된 두 한국어 candidate fixture의 lexical sweep, adapter batch 측정, threshold no-answer 결과를 출력합니다. 두 번째 명령은 adapter batch, 남은 timeout budget, timeout의 partial-score 폐기, retriever fallback 출처를 검증합니다.

## 6. 단계별 실습

### 6.1 실제 model client를 adapter로 감싼다

아래처럼 model client는 `predict`만 제공하면 됩니다. 이 장의 example은 `FixtureCrossEncoderModel`을 쓰므로 다운로드 없이 실행됩니다.

```python
from collections.abc import Sequence

from ai_platform.reranker import (
    BatchRerankPolicy,
    Candidate,
    CrossEncoderModelAdapter,
    rerank_with_adapter,
)


class LocalOrRemoteModel:
    def predict(
        self, pairs: Sequence[tuple[str, str]], *, timeout_ns: int
    ) -> Sequence[float]:
        # 실제 구현에서는 timeout_ns를 provider deadline으로 전달한다.
        return [0.95 for _ in pairs]


adapter = CrossEncoderModelAdapter("cross-encoder-model-id", LocalOrRemoteModel())
result = rerank_with_adapter(
    "비밀번호 재설정 방법",
    (Candidate("recovery", "계정 설정에서 재설정합니다.", 0.71),),
    adapter,
    BatchRerankPolicy(max_batch_size=8, timeout_ns=1_000_000_000),
)
```

`CrossEncoderModelAdapter`는 pair의 순서를 바꾸지 않습니다. model output score의 개수도 입력 batch와 정확히 같아야 합니다. score가 많거나 적으면 adapter error fallback이 됩니다.

### 6.2 batch와 전체 deadline을 읽는다

`candidate_count=3`, `max_batch_size=2`이면 한 질의는 2개 batch(`2 + 1`)로 나뉩니다. 두 fixed fixture의 합계는 `batch_count=4`, `pair_evaluations=6`입니다. 첫 batch가 10ns를 썼다면 100ns 정책의 두 번째 batch에는 90ns만 전달됩니다. 각 batch에 다시 100ns를 주지 않습니다.

### 6.3 timeout 결과를 답변 근거와 분리한다

기본 `no_answer` 정책에서 timeout 결과의 `ranked`는 비어 있습니다. 따라서 호출자는 부분 Cross-Encoder score를 citation이나 answer evidence로 승격할 수 없습니다. retriever fallback을 정책상 허용해야 한다면 다음처럼 명시하며, 호출자는 `rank_source`를 반드시 보존합니다.

```python
result = rerank_with_adapter(
    query,
    candidates,
    adapter,
    BatchRerankPolicy(max_batch_size=8, timeout_ns=1_000_000_000),
    fallback="retriever",
)

if result.outcome == "retriever_fallback":
    assert all(item.cross_encoder_score is None for item in result.ranked)
    assert all(item.rank_source == "retriever_fallback" for item in result.ranked)
```

## 7. 코드 설명

`rerank_with_adapter`는 시작 시각에서 하나의 deadline을 만들고, 매 batch 직전에 남은 budget을 계산합니다. `pair_evaluations`는 adapter에 제출한 pair 수이며, timeout된 batch도 이미 제출되었으므로 포함됩니다. `batch_count`, `elapsed_ns`, `outcome`, `fallback_reason`은 `AdapterRerankResult`에 보존됩니다.

성공한 경우에만 모든 batch score를 합쳐 score 내림차순, `candidate_id` 오름차순으로 정렬합니다. 실패한 경우에는 `_adapter_fallback_result`이 성공한 이전 batch score까지 버립니다. 이 규칙은 partial ranking이 완전 ranking처럼 보이는 문제를 막습니다.

## 8. 정상 실행 결과

2026-08-10에 실제로 실행한 `uv run python examples/volume06/rerank_fixture.py`에는 다음 adapter 행이 포함되었습니다. `elapsed_ns`는 host 부하에 따라 바뀌며 회귀 기준이 아닙니다.

```text
adapter_candidate_count=3; top_k=1; batch_count=4; pair_evaluations=6; elapsed_ns=81200; outcome=reranked; retriever_precision=0.000; adapter_precision=1.000; retriever_graded_ndcg=0.143; adapter_graded_ndcg=1.000
```

이 결과는 `FixtureCrossEncoderModel`과 의도적으로 설계한 두 fixed fixture에서만 재현되는 local 교육 측정입니다. 특정 production model의 품질, 비용 또는 latency 주장이 아닙니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `adapter must provide a callable score_pairs method` | adapter를 직접 전달했지만 `score_pairs`가 없음 | model client는 `CrossEncoderModelAdapter`로 감싸거나 adapter protocol을 구현합니다. |
| `model must provide a callable predict method` | model client에 `predict`가 없음 | model provider wrapper에 batch pair predict 메서드를 구현합니다. |
| `outcome=no_answer; fallback_reason=adapter_timeout` | deadline 전/후 또는 model timeout이 발생함 | candidate count, batch size, model latency를 측정하고 provider timeout이 `timeout_ns`를 실제로 따르는지 확인합니다. score를 재사용하지 않습니다. |
| `outcome=no_answer; fallback_reason=adapter_error` | adapter exception, score 수 불일치, NaN/Infinity score | model response shape, score serialization, adapter 로그를 확인합니다. |
| `outcome=retriever_fallback` | 호출자가 fallback을 명시적으로 허용함 | downstream에서 `rank_source`와 `cross_encoder_score=None`을 보존하고 별도 threshold/citation 정책을 적용합니다. |

## 10. 응용 실습

1. `FixtureCrossEncoderModel`에 세 번째 질의를 추가하고 `max_batch_size=1`, `2`, `3`에서 `batch_count`와 `pair_evaluations`를 비교합니다.
2. test fake model이 두 번째 batch에서 `TimeoutError`를 내도록 만든 뒤, 첫 batch의 높은 score가 결과에 남지 않는지 확인합니다.
3. adapter result의 `outcome`과 `fallback_reason`을 구조화된 local log event로 변환하는 순수 함수를 작성합니다. log에 query text나 비밀 값을 무단으로 넣지 않습니다.

## 11. 실무 적용

실제 adapter에는 model ID/version, tokenizer version, maximum sequence length, batch size, candidate count, timeout, hardware/provider, retry 횟수, timeout·error·fallback 비율을 함께 기록합니다. retry를 쓴다면 전체 deadline 안의 남은 budget을 공유하고 무한 retry를 하지 않습니다.

`retriever_fallback`은 Cross-Encoder 검증을 통과한 결과가 아닙니다. 권한 필터, threshold, citation 정책이 필요한 서비스에서는 default `no_answer`가 더 안전할 수 있습니다. production threshold와 batch 크기는 사람이 검토한 holdout relevance judgment에서 precision, recall, graded nDCG, p50/p95/p99 latency, 비용, abstention 비율을 함께 보고 선택합니다.

## 12. 과제

- **기본:** 5개 고정 candidate를 `max_batch_size=2`로 실행하고 예상 batch 수 3을 테스트합니다.
- **응용:** model output에 `math.nan`을 넣고 `adapter_error` no-answer가 되는 회귀 테스트를 작성합니다.
- **심화:** provider별 HTTP/model client adapter를 설계하되, deadline propagation, bounded retry, model-version 관측, partial-score 폐기 계약을 유지합니다. 외부 호출은 mock으로만 테스트합니다.

## 13. 완료 체크리스트

- [x] Retriever/Bi-Encoder candidate contract와 Cross-Encoder model adapter를 분리했다.
- [x] 고정 fixture에서 batch size, pair 수, local elapsed를 측정했다.
- [x] 각 batch에 전체 timeout이 아닌 남은 budget을 전달한다.
- [x] timeout, adapter error, score shape 오류에서 partial score를 폐기한다.
- [x] 기본 no-answer와 명시적 retriever fallback의 출처를 구분한다.
- [ ] 사람의 holdout judgment와 실제 model client로 latency percentile·비용·threshold를 결정한다.

## 14. 핵심 정리

Cross-Encoder는 candidate를 더 정교하게 비교하지만 batch와 deadline 정책 없이는 RAG 경로를 불안정하게 만들 수 있습니다. adapter 경계로 provider를 분리하고, 전체 timeout을 batch가 공유하게 하며, 실패 후에는 partial score를 버려야 ranking 출처와 답변 근거를 정직하게 유지할 수 있습니다.
