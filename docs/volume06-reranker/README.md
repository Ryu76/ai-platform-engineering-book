# Volume 06. Reranker

## 목표
검색 후보를 Cross-Encoder 방식으로 재정렬하고 Recall·Precision·지연시간의 균형을 측정합니다.

## 학습 경로

1. [결정론적 Cross-Encoder Rerank와 품질 측정](01-deterministic-cross-encoder.md) — 고정 후보에서 retriever/reranker before·after 지표를 재현합니다.
2. [고정 후보 수와 Top-k Sweep](02-local-candidate-top-k-sweep.md) — candidate count, output top-k, pair 비교 수와 local latency 계약을 함께 확인합니다.
3. [다중 Relevance Judgment와 Threshold No-answer](03-graded-judgments-threshold-fallback.md) — ordinal graded nDCG와 fail-closed fallback 결정을 고정 fixture로 검증합니다.
4. [Batched Cross-Encoder Adapter와 Timeout Fallback](04-batched-cross-encoder-adapter-timeout.md) — 실제 model adapter 경계, 전체 deadline batch 정책, partial-score 폐기를 고정 fixture로 검증합니다.
5. [Threshold Sweep와 안전한 Rerank 미니 프로젝트](05-threshold-sweep-mini-project.md) — score를 한 번만 계산해 acceptance/no-answer와 전체 품질 trade-off를 측정합니다.
6. [Volume 완료 점검, Volume 07 인계, 용어 정리](06-completion-handoff-glossary.md) — 검증 범위, 안전한 소비 contract, 다음 Volume 인계와 용어를 확인합니다.

## 로컬 실행

```bash
uv run python examples/volume06/rerank_fixture.py
uv run pytest tests/unit/test_volume06_reranker.py -q
```

위 경로는 네트워크, API 키, 다운로드 모델을 사용하지 않습니다. `LexicalCrossEncoder`는 실제 모델이 아닌 교육용 결정론적 pair scorer입니다. 운영 모델 성능은 사람의 relevance judgment가 있는 별도 평가 집합에서 검증해야 합니다.

## 장 목록
Retriever/Reranker · Bi/Cross Encoder · Top-k · Threshold · 후보 수 · 품질 지표 · Latency · 비용 최적화

## 진행 기록

- [Volume 06 진행 기록](PROGRESS.md)
