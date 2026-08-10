# Volume 10. Evaluation

## 목표

고정된 골든 데이터셋(Golden Dataset)과 재현 가능한 측정으로 RAG·Router·Agent·LLM 응답의 품질, 지연 시간, 토큰 사용량, 비용을 평가합니다. 기본 실습은 네트워크·API 키·외부 서비스 없이 실행됩니다.

## 장 목록

1. [학습 목표와 결정론적 평가 출발점](01-learning-objectives.md)
2. [골든 데이터셋 설계와 버전 관리](02-golden-dataset.md)
3. [검색 품질: Recall·Precision·Hit Rate·MRR·NDCG](03-retrieval-quality.md)
4. [응답 정확도·환각·인용 평가](04-answer-quality.md)
5. [Router·Agent Task Success 평가](05-router-agent-task-success.md)
6. [Latency·Token·Cost 측정](06-latency-token-cost.md)
7. 회귀 비교와 평가 리포트 *(작성 예정)*
8. 미니 프로젝트: 오프라인 평가 파이프라인 *(작성 예정)*
9. 문제 해결·과제·면접 질문·요약·체크리스트 *(작성 예정)*

## 이번 권의 오프라인 실행 경로

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume10/golden_dataset_audit.py
uv run python examples/volume10/retrieval_quality.py
uv run python examples/volume10/retrieval_failure_analysis.py
uv run python examples/volume10/answer_quality.py
uv run python examples/volume10/workflow_quality.py
uv run python examples/volume10/usage_quality.py
uv run pytest tests/evaluation/test_golden_dataset.py tests/evaluation/test_retrieval_metrics.py tests/evaluation/test_answer_metrics.py tests/evaluation/test_workflow_metrics.py tests/evaluation/test_usage_metrics.py -q
```

일곱 명령은 `src/ai_platform/evaluation/datasets.py`의 공개 가능한 고정 질의·라벨·정답·순위·기록 답변·워크플로·사용량만 읽습니다. LLM, Agent 도구, 벡터 데이터베이스, 네트워크, API 키, 라이브 시계를 사용하지 않습니다. `abstain` no-answer 사례는 검색 Recall과 분리되어 있으며, 답변 보류·환각·인용 품질, Router·Agent 작업 품질, Latency·Token·Cost는 별도 결정론적 지표로 평가합니다.

[진행 기록](PROGRESS.md)
