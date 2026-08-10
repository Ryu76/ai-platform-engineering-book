# Volume 06 작업 진행 기록

## 현재 상태

- 완료 표식: `VOLUME06_COMPLETE` 미설정
- 현재 slice: 02 — 결정론적 candidate-count/top-k sweep과 local latency 계약
- 범위: 외부 API, 모델 다운로드, GPU, 비밀값, 배포를 사용하지 않았습니다.

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

- [ ] Bi-Encoder와 실제 Cross-Encoder adapter의 경계 및 batch/timeout 정책을 구현·검증한다.
- [ ] candidate count, top-k, threshold별 품질·지연시간·비용 trade-off를 고정 evaluation set에서 측정한다.
- [ ] 다중 relevance judgment, no-answer/fallback, 실패 관측성을 구현·검증한다.
- [ ] 미니 프로젝트, 권 단위 체크리스트, 다음 Volume 인계를 완료한다.

## 다음 slice

고정 fixture와 local adapter만 사용해 다중 relevance judgment 및 no-answer/fallback의 fail-closed 계약을 추가합니다.
