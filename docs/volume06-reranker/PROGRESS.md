# Volume 06 작업 진행 기록

## 현재 상태

- 완료 표식: `VOLUME06_COMPLETE` 미설정
- 현재 slice: 01 — 결정론적 Cross-Encoder rerank와 로컬 ranking metrics
- 범위: 외부 API, 모델 다운로드, GPU, 비밀값, 배포를 사용하지 않았습니다.

## 2026-08-10 — Slice 01 완료

### 추가한 결과물

- `src/ai_platform/reranker/cross_encoder.py`
  - stable candidate ID와 원래 retriever score를 갖는 불변 후보 계약
  - 질의-후보 쌍을 독립적으로 평가하는 결정론적 lexical Cross-Encoder 교육용 구현
  - `precision@k`, `recall@k`, MRR, nDCG@k 및 질의별 평균 계산
  - 빈 입력, 중복 후보·순위 ID, 비유한 점수, 잘못된 k의 fail-closed 검증
- `examples/volume06/rerank_fixture.py`
  - 두 개의 고정 한국어 후보 fixture로 before/after top-1 순위와 metrics를 출력하는 오프라인 예제
- `tests/unit/test_volume06_reranker.py`
  - promotion, 입력 순서 독립성, 동점 정렬, top-k, 네 metrics, fixture 회귀, 오류 경로 테스트
- `01-deterministic-cross-encoder.md`
  - reranker 역할·품질 지표·고정 fixture 한계·실무 평가 경계를 14개 학습 섹션으로 문서화

### 로컬 측정 및 검증 결과

```text
retriever_mean@1=precision=0.000; recall=0.000; mrr=0.500; ndcg=0.000
reranker_mean@1=precision=1.000; recall=1.000; mrr=1.000; ndcg=1.000
```

위 값은 `examples/volume06/rerank_fixture.py`의 두 고정 fixture에서만 재현되는 결과입니다. 실제 모델 또는 운영 corpus의 성능 주장이 아닙니다.

검증 명령과 실제 결과:

```bash
uv run pytest tests/unit/test_volume06_reranker.py -q
# 13 passed in 0.09s
uv run ruff check src/ai_platform/reranker examples/volume06 tests/unit/test_volume06_reranker.py
# All checks passed!
uv run mypy src/ai_platform/reranker
# Success: no issues found in 2 source files
uv run python examples/volume06/rerank_fixture.py
# query=비밀번호 재설정 방법
# retriever_top1=password-policy
# reranker_top1=account-recovery; cross_encoder_score=304
# query=장애 대응 연락처
# retriever_top1=infra-overview
# reranker_top1=incident-contacts; cross_encoder_score=303
# retriever_mean@1=precision=0.000; recall=0.000; mrr=0.500; ndcg=0.000
# reranker_mean@1=precision=1.000; recall=1.000; mrr=1.000; ndcg=1.000
```

`uv`는 Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고를 냈지만 프로젝트 환경에서 검증을 완료했습니다.

## 남은 PRD 완료 조건

- [ ] Bi-Encoder와 실제 Cross-Encoder adapter의 경계 및 batch/timeout 정책을 구현·검증한다.
- [ ] candidate count, top-k, threshold별 품질·지연시간·비용 trade-off를 고정 evaluation set에서 측정한다.
- [ ] 다중 relevance judgment, no-answer/fallback, 실패 관측성을 구현·검증한다.
- [ ] 미니 프로젝트, 권 단위 체크리스트, 다음 Volume 인계를 완료한다.

## 다음 slice

고정 fixture와 local adapter만 사용해 candidate-count 및 top-k sweep의 ranking metrics와 측정 가능한 local latency 계약을 추가합니다.
