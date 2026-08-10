# Volume 06 작업 진행 기록

## 현재 상태

- 완료 표식: `VOLUME06_COMPLETE=true`
- 현재 slice: 완료 — 후속 cron tick은 self-paused 상태로 새 slice를 시작하지 않습니다.
- 범위: 외부 API, 모델 다운로드, GPU, 비밀값, 배포를 사용하지 않았습니다.

## 2026-08-11 — Slice 06 완료 및 Volume DoD 검증

### 추가한 결과물

- `docs/volume06-reranker/06-completion-handoff-glossary.md`
  - Volume 완료 범위와 재현 가능한 local 검증 명령을 정리했습니다.
  - 학습자 완료 체크리스트, 안전한 `selected`/`no_answer`/fallback 소비 contract, Volume 07 인계 metadata와 재평가 순서를 문서화했습니다.
  - Volume 06-scoped reranker, pair work, threshold, graded judgment, timeout, partial-score discard, rank provenance 주요 용어를 정리했습니다.
- `docs/volume06-reranker/README.md`
  - 완료 점검·인계·용어 장을 학습 경로 여섯 번째 항목으로 연결했습니다.

### 로컬 측정 결과

최종 `uv run python examples/volume06/rerank_fixture.py` 실행에서 고정 두 query × 세 candidate threshold sweep은 shared pair work `6`을 유지했습니다. threshold `303`은 `accepted=2/2`, effective precision/recall `1.000/1.000`; threshold `304`는 `accepted=1/2`, `0.500/0.500`; threshold `305`는 `accepted=0/2`, `0.000/0.000`이었습니다. adapter fixture는 `batch_count=4`, `pair_evaluations=6`, retriever/adapter precision `0.000/1.000`, graded nDCG `0.143/1.000`을 출력했습니다.

local elapsed는 실행 host 부하에 따라 달라져 회귀 기준이 아니며, fixture ranking metric, pair count, threshold outcome, fallback reason만 결정론적 회귀 기준입니다. 이 측정은 production model/corpus의 latency, 비용, 품질 주장이 아닙니다.

### 검증 명령과 실제 결과

```bash
uv run pytest tests/unit/test_volume06_reranker.py -q
# 39 passed in 0.12s
uv run ruff check src/ai_platform/reranker examples/volume06 tests/unit/test_volume06_reranker.py
# All checks passed!
uv run mypy src/ai_platform/reranker examples/volume06
# Success: no issues found in 3 source files
uv run python examples/volume06/rerank_fixture.py
# fixed-fixture candidate/top-k, threshold, adapter, no-answer rows completed
uv run python scripts/validate_links.py
# 링크 검증 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
uv run python scripts/validate_code_blocks.py
# 코드 블록 검증 통과
```

### PRD 완료 조건

- [x] Bi-Encoder와 실제 Cross-Encoder adapter의 경계 및 batch/timeout 정책을 구현·검증한다.
- [x] candidate count, top-k, threshold별 품질·지연시간·비용 trade-off를 고정 evaluation set에서 측정한다.
- [x] 다중 relevance judgment, no-answer/fallback, 실패 관측성을 구현·검증한다.
- [x] 권 단위 체크리스트, 다음 Volume 인계, Volume-scoped 주요 용어를 완료한다.

`VOLUME06_COMPLETE=true`이므로 새로운 작업 slice를 시작하지 않고 self-pause합니다.

## 2026-08-10 — Slice 05 완료

### 추가한 결과물

- `src/ai_platform/reranker/cross_encoder.py`
  - 불변 `ThresholdSweepMeasurement`와 `measure_threshold_sweep`을 추가했습니다.
  - 같은 query/candidate ranking은 `measure_rerank`로 정확히 한 번만 pair scoring하고, 고유한 여러 non-negative threshold에는 그 score를 재사용합니다. 빈 policy, 중복, 음수, bool, 문자열 값은 fail-closed로 거부합니다.
  - `rerank_with_threshold`와 sweep이 같은 `_threshold_decision` 경로를 사용해 boundary acceptance/no-answer 계약을 공유합니다.
- `examples/volume06/rerank_fixture.py`
  - 두 deterministic Korean fixture에서 threshold `1/303/304/305`의 acceptance rate, conditional precision, no-answer를 포함한 effective precision/recall을 출력합니다.
  - 네 threshold 행은 같은 두 rerank 실행을 공유하므로 `shared_pair_evaluations=6`입니다. policy 수로 pair work를 중복 계산하지 않습니다.
- `tests/unit/test_volume06_reranker.py`
  - 2개 candidate를 한 번만 score하는 sweep, threshold별 accepted/no-answer 결과, 빈값/중복/음수/bool/문자열 policy 거부를 추가했습니다.
- `docs/volume06-reranker/05-threshold-sweep-mini-project.md`
  - threshold policy 평가, acceptance와 conditional/effective quality의 차이, 안전한 `selected` 소비 contract를 14-section 미니 프로젝트로 문서화했습니다.

### 로컬 측정 결과

최종 `uv run python examples/volume06/rerank_fixture.py` 실행의 threshold 행입니다. 두 query × 세 candidate의 score는 threshold와 무관하게 한 번씩만 계산되어 모든 행의 shared pair work는 6입니다.

```text
threshold=1; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=2/2; acceptance_rate=1.000; conditional_precision=1.000; effective_precision=1.000; effective_recall=1.000
threshold=303; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=2/2; acceptance_rate=1.000; conditional_precision=1.000; effective_precision=1.000; effective_recall=1.000
threshold=304; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=1/2; acceptance_rate=0.500; conditional_precision=1.000; effective_precision=0.500; effective_recall=0.500
threshold=305; candidate_count=3; top_k=1; shared_pair_evaluations=6; shared_elapsed_ns=316300; accepted=0/2; acceptance_rate=0.000; conditional_precision=0.000; effective_precision=0.000; effective_recall=0.000
```

`shared_elapsed_ns`는 local host 부하에 따라 달라지며 회귀 기준이 아닙니다. acceptance, 선택 결과의 quality, pair count는 의도적으로 설계한 고정 fixture에서만 결정론적입니다. 이 측정은 production model/corpus의 latency, 비용, 품질 주장이 아닙니다.

### 검증 명령과 실제 결과

```bash
uv run pytest tests/unit/test_volume06_reranker.py -q
# 39 passed in 0.11s
uv run ruff check src/ai_platform/reranker examples/volume06 tests/unit/test_volume06_reranker.py
# All checks passed!
uv run mypy src/ai_platform/reranker examples/volume06
# Success: no issues found in 3 source files
uv run python examples/volume06/rerank_fixture.py
# 6 candidate/top-k rows, 4 shared-work threshold rows, 1 adapter row, 1 no-answer decision completed
uv run python scripts/validate_links.py
# 링크 검증 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
uv run python scripts/validate_code_blocks.py
# 코드 블록 검증 통과
```

## 2026-08-10 — Slice 04 완료

### 추가한 결과물

- `src/ai_platform/reranker/cross_encoder.py`
  - `CrossEncoderModel`/`CrossEncoderScorer` protocol과 `CrossEncoderModelAdapter`를 추가했습니다. model client는 입력 순서와 같은 수의 pair score만 반환하는 명시적 경계를 갖습니다.
  - 불변 `BatchRerankPolicy(max_batch_size, timeout_ns)`와 `rerank_with_adapter`를 추가했습니다. 전체 rerank deadline에서 경과 시간을 빼서 각 batch에 남은 timeout budget만 전달합니다.
  - `AdapterRerankResult`에 candidate/batch/pair 수, local elapsed, outcome, fallback reason을 기록합니다. timeout·adapter exception·score 개수/수치 오류는 성공한 이전 batch를 포함한 모든 partial Cross-Encoder score를 폐기합니다.
  - 기본 `no_answer`는 빈 ranking을 반환합니다. 명시적 `retriever` fallback은 `cross_encoder_score=None`, `rank_source=retriever_fallback`으로 출처를 보존합니다.
- `examples/volume06/rerank_fixture.py`
  - 다운로드 없이 실행되는 `FixtureCrossEncoderModel`을 `CrossEncoderModelAdapter`로 감싸고, 두 고정 Korean fixture에서 batch/pair 수와 binary·graded ranking metric을 local 측정합니다.
- `tests/unit/test_volume06_reranker.py`
  - pair 순서, batch 분할, 100ns→90ns 남은 budget 전달, timeout 후 partial-score 폐기, 명시적 retriever fallback 출처, malformed/non-finite score fail-closed를 추가했습니다.
- `docs/volume06-reranker/04-batched-cross-encoder-adapter-timeout.md`
  - Bi/Cross-Encoder 경계, 전체 deadline batch 정책, sync adapter timeout 한계, fallback 관측과 운영 평가 경계를 문서화했습니다.

### 로컬 측정 결과

`uv run python examples/volume06/rerank_fixture.py`의 실제 1회 실행에서 adapter row는 아래와 같았습니다.

```text
adapter_candidate_count=3; top_k=1; batch_count=4; pair_evaluations=6; elapsed_ns=81200; outcome=reranked; retriever_precision=0.000; adapter_precision=1.000; retriever_graded_ndcg=0.143; adapter_graded_ndcg=1.000
```

두 query × 세 candidate를 `max_batch_size=2`로 실행했으므로 batch 4회와 pair 6회가 결정론적입니다. precision·graded nDCG도 fixture/model mapping에서 결정론적입니다. `elapsed_ns`는 host 부하에 따라 변하며 production model latency, 비용, 품질 주장이 아닙니다.

### 검증 명령과 실제 결과

```bash
uv run pytest tests/unit/test_volume06_reranker.py -q
# 33 passed in 0.16s
uv run ruff check src/ai_platform/reranker examples/volume06 tests/unit/test_volume06_reranker.py
# All checks passed!
uv run mypy src/ai_platform/reranker examples/volume06
# Success: no issues found in 3 source files
uv run python examples/volume06/rerank_fixture.py
# 6 lexical sweep rows, 1 adapter measurement row, 1 threshold no-answer decision completed
```

## 2026-08-10 — Slice 03 완료

### 추가한 결과물

- `src/ai_platform/reranker/cross_encoder.py`
  - 불변 `RelevanceJudgment`와 `evaluate_graded_ranking`을 추가했습니다.
  - 0 이상 ordinal grade, label 중복, 평가 rank의 label 누락을 fail-closed로 검증합니다.
  - grade 2 이상을 직접 관련 binary label로 쓰되 nDCG는 `2**grade - 1` gain으로 계산해 강한 관련 문서의 상위 배치를 측정합니다.
  - `rerank_with_threshold`와 불변 `RerankDecision`을 추가했습니다. 최상위 score가 threshold 미만이면 후보를 선택하지 않고 `outcome=no_answer`, `fallback_reason=top_score_below_threshold`를 반환합니다.
- `examples/volume06/rerank_fixture.py`
  - 두 고정 한국어 candidate fixture에 0/1/3 다중 judgment를 추가하고, 기존 sweep에 retriever/reranker graded nDCG를 함께 출력합니다.
  - 무관한 고정 후보를 threshold=1로 실행하는 no-answer fixture를 출력합니다.
- `tests/unit/test_volume06_reranker.py`
  - ordinal grade가 graded nDCG를 바꾸는 회귀, label 누락/중복 거부, threshold 경계 통과와 no-answer 거부, 음수/bool threshold 거부를 추가했습니다.
- `docs/volume06-reranker/03-graded-judgments-threshold-fallback.md`
  - grade 계약, local metric 해석, no-answer/fallback 관측 계약과 운영 평가 경계를 문서화했습니다.

### 로컬 측정 결과

`uv run python examples/volume06/rerank_fixture.py`의 실제 1회 실행에서 `candidate_count=2; top_k=1` 행은 pair 평가 4회, retriever/reranker graded nDCG `0.143/1.000`을 출력했습니다. 같은 실행의 무관한 고정 후보는 아래처럼 fail-closed되었습니다.

```text
threshold=1; outcome=no_answer; top_score=0; fallback_reason=top_score_below_threshold
```

품질 지표, pair 수, threshold decision은 고정 fixture에서 결정론적입니다. `elapsed_ns`만 실행 호스트 부하에 따라 달라집니다. 이 수치는 운영 모델·corpus의 품질, 비용, latency 주장이 아닙니다.

### 검증 명령과 실제 결과

```bash
uv run pytest tests/unit/test_volume06_reranker.py -q
# 25 passed in 0.13s
uv run ruff check src/ai_platform/reranker examples/volume06 tests/unit/test_volume06_reranker.py
# All checks passed!
uv run mypy src/ai_platform/reranker examples/volume06
# Success: no issues found in 3 source files
uv run python examples/volume06/rerank_fixture.py
# 6 sweep rows plus 1 deterministic no-answer decision completed
```

## 2026-08-10 — Slice 02 완료

### 추가한 결과물

- `src/ai_platform/reranker/cross_encoder.py`
  - `measure_rerank`와 불변 `RerankMeasurement`를 추가했습니다.
  - 입력 후보를 모두 pair scoring한 횟수(`pair_evaluations`), candidate count, top-k 적용 뒤 순위, monotonic local elapsed nanoseconds를 함께 기록합니다.
  - 테스트용 주입 clock을 지원하고, callable이 아닌 clock, 음수/문자열 값, 역행 clock을 fail-closed로 거부합니다.
- `examples/volume06/rerank_fixture.py`
  - 기존 두 개의 고정 한국어 fixture를 `candidate_count=1..3`, `top_k=1..candidate_count`로 sweep합니다.
  - 각 행에 retriever/reranker의 precision, recall, MRR, nDCG와 pair 비교 수·실측 local elapsed를 출력합니다.
- `tests/unit/test_volume06_reranker.py`
  - 주입 clock의 재현 가능한 elapsed 계약, pair 수, candidate-count가 recall 상한을 정하는 경우, 깨진 clock 오류 경로를 추가했습니다.
- `02-local-candidate-top-k-sweep.md`
  - candidate count와 output top-k의 경계, deterministic 품질 지표와 host-dependent latency의 구분, fixture에서 관찰되는 trade-off를 문서화했습니다.

### 로컬 측정 결과

`uv run python examples/volume06/rerank_fixture.py`의 실제 1회 실행에서 다음 deterministic 품질·pair count를 확인했습니다. `elapsed_ns`는 같은 명령에서도 호스트 부하에 따라 달라지는 관측값입니다.

```text
candidate_count=1; top_k=1; pair_evaluations=2
retriever/reranker precision=0.000/0.000; recall=0.000/0.000; mrr=0.000/0.000; ndcg=0.000/0.000

candidate_count=2; top_k=1; pair_evaluations=4
retriever/reranker precision=0.000/1.000; recall=0.000/1.000; mrr=0.500/1.000; ndcg=0.000/1.000

candidate_count=2; top_k=2; pair_evaluations=4
retriever/reranker precision=0.500/0.500; recall=1.000/1.000; mrr=0.500/1.000; ndcg=0.631/1.000

candidate_count=3; top_k=1; pair_evaluations=6
retriever/reranker precision=0.000/1.000; recall=0.000/1.000; mrr=0.500/1.000; ndcg=0.000/1.000

candidate_count=3; top_k=2; pair_evaluations=6
retriever/reranker precision=0.500/0.500; recall=1.000/1.000; mrr=0.500/1.000; ndcg=0.631/1.000

candidate_count=3; top_k=3; pair_evaluations=6
retriever/reranker precision=0.333/0.333; recall=1.000/1.000; mrr=0.500/1.000; ndcg=0.631/1.000
```

이 값은 두 고정 fixture에서만 재현되는 교육용 결과이며, 실제 모델·운영 corpus의 품질, latency, 비용 주장이 아닙니다.

### 검증 명령과 실제 결과

```bash
uv run pytest tests/unit/test_volume06_reranker.py -q
# 19 passed in 0.09s
uv run ruff check src/ai_platform/reranker examples/volume06 tests/unit/test_volume06_reranker.py
# All checks passed!
uv run mypy src/ai_platform/reranker
# Success: no issues found in 2 source files
uv run python examples/volume06/rerank_fixture.py
# 6 sweep rows completed; candidate_count=1..3, top_k=1..candidate_count
```

`uv`는 Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고를 냈지만 프로젝트 환경에서 검증을 완료했습니다.

## 2026-08-10 — Slice 01 완료

### 추가한 결과물

- `src/ai_platform/reranker/cross_encoder.py`
  - stable candidate ID와 원래 retriever score를 갖는 불변 후보 계약
  - 질의-후보 쌍을 독립적으로 평가하는 결정론적 lexical Cross-Encoder 교육용 구현
  - `precision@k`, `recall@k`, MRR, nDCG@k 및 질의별 평균 계산
  - 빈 입력, 중복 후보·순위 ID, 비유한 점수, 잘못된 k의 fail-closed 검증
- `examples/volume06/rerank_fixture.py`
  - 고정 한국어 후보 fixture로 retriever/reranker 순위 및 metrics를 출력하는 오프라인 예제
- `tests/unit/test_volume06_reranker.py`
  - promotion, 입력 순서 독립성, 동점 정렬, top-k, 네 metrics, fixture 회귀, 오류 경로 테스트
- `01-deterministic-cross-encoder.md`
  - reranker 역할·품질 지표·고정 fixture 한계·실무 평가 경계를 학습 섹션으로 문서화

## 남은 PRD 완료 조건

- [x] Bi-Encoder와 실제 Cross-Encoder adapter의 경계 및 batch/timeout 정책을 구현·검증한다.
- [x] candidate count, top-k, threshold별 품질·지연시간·비용 trade-off를 고정 evaluation set에서 측정한다.
- [x] 다중 relevance judgment, no-answer/fallback, 실패 관측성을 구현·검증한다.
- [ ] 권 단위 체크리스트, 다음 Volume 인계, Volume-scoped 주요 용어 정리를 완료한다.

## 다음 slice

권 단위 학습자 체크리스트와 Volume 07로 넘길 rerank result/observability contract를 문서화하고, Volume 06-scoped 주요 용어를 정리한 뒤 전체 DoD를 재검증합니다.
