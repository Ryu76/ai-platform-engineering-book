# Volume 10 진행 기록

## 현재 상태

- 현재 Phase: **Phase 11 — Volume 10 Evaluation**
- 이번 슬라이스: **버전 관리되는 고정 골든 데이터셋과 no-answer 라벨 계약**
- 완료 선언: 아직 하지 않음. Volume 10의 답변·인용·환각 평가, Router·Agent 평가, Latency·Token·Cost, 회귀 리포트, 미니 프로젝트, 전체 체크리스트가 남아 있습니다.

## 이번 슬라이스 (2026-08-10)

- `docs/volume10-evaluation/02-golden-dataset.md`
  - PRD 장 구조의 14개 섹션으로 골든 데이터셋의 라벨 근거·출처 참조·대표성·버전 정책·no-answer 분리 원칙을 작성했습니다.
  - 실제 고객 데이터·API 키·네트워크·라이브 모델을 사용하지 않는 고정 데이터 경계를 명시했습니다.
- `src/ai_platform/evaluation/golden_dataset.py`
  - `GoldenCase`, `GoldenDataset`, 결정론적 구성 요약과 answer/abstain·고유 ID·시맨틱 버전 입력 계약을 구현했습니다.
- `src/ai_platform/evaluation/datasets.py`
  - `volume10-support-policy@1.0.0`의 고정 다섯 사례(답변 4, no-answer 1), 라벨 근거, 출처 참조를 정의했습니다.
  - 기존 검색 지표에는 양성 answer 사례만 전달하여 no-answer를 Recall 분모에 섞지 않게 했습니다.
- `examples/volume10/golden_dataset_audit.py`
  - 데이터셋 ID·버전·사례 수·기대 동작 수·정렬된 카테고리를 외부 호출 없이 출력합니다.
- `tests/evaluation/test_golden_dataset.py`
  - 고정 매니페스트, no-answer 분리, 모순된 라벨, 중복 사례 ID, 잘못된 버전을 검증합니다.
- `tests/evaluation/test_volume10_completion_contract.py`, `docs/volume10-evaluation/README.md`
  - 두 번째 장의 14개 필수 섹션, 실제 산출물, 오프라인 실행 경로와 README 링크를 계약으로 연결했습니다.

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

### 골든 데이터셋 슬라이스 검증 (2026-08-10)

```text
$ uv run python examples/volume10/golden_dataset_audit.py
Dataset: volume10-support-policy
Version: 1.0.0
Cases: 5
Answer cases: 4
Abstain cases: 1
Categories: facilities=1, finance=1, identity=1, people=1, security=1

$ uv run pytest tests/evaluation -q
16 passed

$ uv run ruff check src/ai_platform/evaluation tests/evaluation examples/volume10
All checks passed!

$ uv run mypy src/ai_platform/evaluation
Success: no issues found in 4 source files

$ uv run python scripts/validate_code_blocks.py && uv run python scripts/validate_docs.py
코드 블록 검증 통과
문서 검증 통과: Volume 11개
```

## 알려진 차단 사항

- Volume 10은 두 장, 버전 관리되는 골든 데이터셋, 검색 평가 기준선만 완료했습니다. PRD의 Volume Definition of Done을 아직 만족하지 않으므로 `VOLUME10_COMPLETE=true`를 설정하지 않았습니다.
- `abstain` no-answer 사례는 고정·검증됐지만, 답변 보류 정확도·환각·인용 평가는 후속 장에서 별도 결정론적 지표로 구현해야 합니다.
- 고정 Top-3 순위는 평가 계산을 설명하기 위한 기록된 입력입니다. 실제 Retriever에 연결하는 통합 평가와 데이터셋 변경 승인 정책은 후속 장에서 구현합니다.

## 다음 작업

- 고정 골든 데이터셋을 기준으로 Recall·Precision·Hit Rate·MRR·NDCG의 트레이드오프와 실패 사례 해석을 다루는 세 번째 장을 작성합니다.
