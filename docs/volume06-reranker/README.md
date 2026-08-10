# Volume 06. Reranker

## 목표
검색 후보를 Cross-Encoder 방식으로 재정렬하고 Recall·Precision·지연시간의 균형을 측정합니다.

## 학습 경로

1. [결정론적 Cross-Encoder Rerank와 품질 측정](01-deterministic-cross-encoder.md) — 고정 후보에서 retriever/reranker before·after 지표를 재현합니다.

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
