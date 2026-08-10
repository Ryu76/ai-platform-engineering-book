# Volume 10 진행 기록

## 현재 상태

- 현재 Phase: **Phase 11 — Volume 10 Evaluation**
- 이번 슬라이스: **고정 골든 데이터셋 기반의 결정론적 RAG 검색 평가 출발점**
- 완료 선언: 아직 하지 않음. Volume 10의 골든 데이터셋 관리, 답변·인용·환각 평가, Router·Agent 평가, Latency·Token·Cost, 회귀 리포트, 미니 프로젝트, 전체 체크리스트가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume10-evaluation/README.md`
  - Volume 10의 목표, 첫 오프라인 실행 경로, 작성 예정 장을 명시했습니다.
- `docs/volume10-evaluation/01-learning-objectives.md`
  - PRD Chapter Definition of Done의 14개 섹션으로 평가의 필요성, 골든 데이터셋, 검색 지표, 결정론적 실행, 오류 해결, 실무 적용과 과제를 작성했습니다.
  - 공개 가능한 고정 데이터만 쓰며 네트워크·API 키·외부 LLM·벡터 데이터베이스를 사용하지 않는 경계를 명시했습니다.
- `src/ai_platform/evaluation/datasets.py`
  - 4개의 고정 질의, 정답 문서 ID, 기록된 Top-3 순위를 정의했습니다.
- `src/ai_platform/evaluation/retrieval_metrics.py`
  - Recall@k, Precision@k, Hit Rate@k, MRR, NDCG@k를 계산하고 누락 사례·중복 문서·잘못된 `k`를 거부하는 순수 함수를 구현했습니다.
- `src/ai_platform/evaluation/__init__.py`
  - Volume 10의 고정 데이터와 검색 평가 공개 인터페이스를 제공합니다.
- `examples/volume10/retrieval_quality.py`
  - 고정 데이터의 평가 결과를 사람이 읽을 수 있는 결정론적 보고서로 출력합니다.
- `tests/evaluation/test_retrieval_metrics.py`
  - 기준 점수, 순위별 지표 해석, 입력 오류 경계를 테스트합니다.
- `tests/evaluation/test_volume10_completion_contract.py`
  - 첫 장의 14개 필수 섹션, 실제 산출물, 오프라인 명령, 결과 예시, README 링크를 계약으로 고정합니다.

이번 변경은 문서·고정 데이터·순수 로컬 계산·테스트만 포함합니다. 실제 LLM API 호출, 외부 데이터 전송, 배포, 비밀값 사용은 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-10`

```text
$ uv run python examples/volume10/retrieval_quality.py
평가 사례: 4
Recall@3: 0.750000
Precision@3: 0.333333
Hit Rate@3: 0.750000
MRR: 0.625000
NDCG@3: 0.657732

$ uv run pytest tests/evaluation/test_retrieval_metrics.py tests/evaluation/test_volume10_completion_contract.py -q
9 passed

$ uv run mypy src/ai_platform/evaluation
Success: no issues found in 3 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개
```

전체 품질 검사와 전체 테스트는 이 기록 이후 수정된 파일까지 포함해 이번 슬라이스 종료 전에 다시 실행합니다.

## 알려진 차단 사항

- Volume 10은 첫 장과 검색 평가 기준선만 완료했습니다. PRD의 Volume Definition of Done을 아직 만족하지 않으므로 `VOLUME10_COMPLETE=true`를 설정하지 않았습니다.
- 고정 Top-3 순위는 평가 계산을 설명하기 위한 기록된 입력입니다. 실제 Retriever에 연결하는 통합 평가와 데이터셋 버전 관리 정책은 후속 장에서 구현합니다.

## 다음 작업

- 골든 데이터셋의 라벨 기준, 대표성, 버전 관리, no-answer 사례 정책을 다루는 두 번째 장과 해당 계약 테스트를 작성합니다.
