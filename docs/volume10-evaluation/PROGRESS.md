# Volume 10 진행 기록

## 현재 상태

- 현재 Phase: **Phase 11 — Volume 10 Evaluation**
- 이번 슬라이스: **고정 Router 선택과 Agent Task Success의 결정론적 평가 및 사례별 누락·예상 밖 작업 분석**
- 완료 선언: 아직 하지 않음. Latency·Token·Cost, 회귀 리포트, 미니 프로젝트, 전체 체크리스트가 남아 있습니다.

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

### 검색 품질·실패 분석 슬라이스 (2026-08-10)

- `docs/volume10-evaluation/03-retrieval-quality.md`
  - PRD 장 구조의 14개 섹션으로 Recall·Precision·Hit Rate·MRR·NDCG의 역할, `k` 트레이드오프, 완전 누락과 늦은 정답의 원인 분리를 작성했습니다.
  - `benefits-enrollment`의 Top-3 누락, `expense-receipt`의 2위 정답, `incident-response`의 복수 정답 회수를 고정 출력으로 해석합니다.
- `src/ai_platform/evaluation/retrieval_metrics.py`
  - 평균 점수와 동일한 입력 계약을 공유하는 `RetrievalCaseMetrics` 및 `evaluate_retrieval_cases()`를 추가했습니다.
  - 문자열 하나를 문서 ID 시퀀스로 오해해 문자 단위로 계산하는 입력을 거부합니다.
- `examples/volume10/retrieval_failure_analysis.py`
  - 네 개의 양성 사례를 고정 순서로 출력해 회수된 정답 ID, 첫 정답 순위, 사례별 Recall·Precision·MRR·NDCG를 외부 호출 없이 보여 줍니다.
- `tests/evaluation/test_retrieval_metrics.py`, `tests/evaluation/test_volume10_completion_contract.py`
  - 사례별 순서·누락·복수 회수, 잘못된 문자열 입력, 세 번째 장의 14개 필수 섹션과 실제 산출물 연결을 검증합니다.
- `docs/volume10-evaluation/README.md`
  - 세 번째 장과 사례별 실패 분석 실행 경로를 추가했습니다.

#### 검증 기록

```text
$ uv run python examples/volume10/retrieval_failure_analysis.py
Cutoff: 3
access-reset: retrieved=identity-access; first_rank=1; Recall@3=1.000000; Precision@3=0.333333; MRR=1.000000; NDCG@3=1.000000
expense-receipt: retrieved=finance-expense; first_rank=2; Recall@3=1.000000; Precision@3=0.333333; MRR=0.500000; NDCG@3=0.630930
incident-response: retrieved=operations-runbook, security-incident; first_rank=1; Recall@3=1.000000; Precision@3=0.666667; MRR=1.000000; NDCG@3=1.000000
benefits-enrollment: retrieved=none; first_rank=none; Recall@3=0.000000; Precision@3=0.000000; MRR=0.000000; NDCG@3=0.000000

$ uv run pytest tests/evaluation -q
19 passed

$ uv run ruff check src/ai_platform/evaluation tests/evaluation examples/volume10
All checks passed!

$ uv run mypy src/ai_platform/evaluation
Success: no issues found in 4 source files

$ uv run python scripts/validate_code_blocks.py && uv run python scripts/validate_docs.py
코드 블록 검증 통과
문서 검증 통과: Volume 11개
```

### 답변 정확도·환각·인용 평가 슬라이스 (2026-08-10)

- `docs/volume10-evaluation/04-answer-quality.md`
  - PRD 장 구조의 14개 섹션으로 답변 정확도, 보류 정확도, 환각률, 인용 정확도의 분자·분모, 한계, 사람·LLM-as-a-Judge 보완 경로를 작성했습니다.
  - `office-parking`의 no-answer 위반과 `benefits-enrollment`의 부정확한 인용을 고정 사례로 해석하며, 라이브 API·네트워크·시계·난수를 사용하지 않는 범위를 명시했습니다.
- `src/ai_platform/evaluation/answer_metrics.py`
  - `AnswerCase`, `RecordedAnswer`, 사례별·평균 지표와 완전한 사례 집합, 보류 라벨, 중복 ID, 키/객체 ID 불일치 입력 계약을 구현했습니다.
  - 답변 정확도 0.800000, 보류 정확도 0.000000, 환각률 0.166667, 인용 정확도 0.666667의 결정론적 기준선을 계산합니다.
- `src/ai_platform/evaluation/datasets.py`, `src/ai_platform/evaluation/__init__.py`
  - 기존 `volume10-support-policy@1.0.0`의 다섯 공개 사례에서 유도한 고정 사실·인용 라벨과 의도적인 보류·인용 실패 기록을 공개 인터페이스로 연결했습니다.
- `examples/volume10/answer_quality.py`
  - 고정 기록 답변의 네 지표를 외부 호출 없이 사람이 읽을 수 있는 형식으로 출력합니다.
- `tests/evaluation/test_answer_metrics.py`, `tests/evaluation/test_volume10_completion_contract.py`
  - 기준 수치, 사례별 지원되지 않은 주장·인용, 불완전 결과와 모순 라벨, 네 번째 장의 14개 섹션과 실제 산출물 연결을 검증합니다.
- `docs/volume10-evaluation/README.md`
  - 네 번째 장 링크와 전체 오프라인 실행 경로를 추가했습니다.

#### 검증 기록

```text
$ uv run python examples/volume10/answer_quality.py
Evaluation cases: 5
Answer accuracy: 0.800000
Abstention accuracy: 0.000000
Hallucination rate: 0.166667
Citation accuracy: 0.666667

$ uv run pytest tests/evaluation -q
28 passed

$ uv run ruff check src/ai_platform/evaluation tests/evaluation examples/volume10
All checks passed!

$ uv run mypy src/ai_platform/evaluation
Success: no issues found in 5 source files

$ uv run python scripts/validate_code_blocks.py && uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py
코드 블록 검증 통과
문서 검증 통과: Volume 11개
링크 검증 통과
```

### Router·Agent Task Success 슬라이스 (2026-08-11)

- `docs/volume10-evaluation/05-router-agent-task-success.md`
  - PRD 장 구조의 14개 섹션으로 Router Accuracy와 Agent Task Success를 분리하는 이유, no-answer 라우트·부수 작업 차단, 사례별 누락·예상 밖 작업 분석을 작성했습니다.
  - 실제 Router·Agent·도구·LLM API·네트워크·시계·난수를 쓰지 않고 고정 기록만 읽는 실행 경계를 명시했습니다.
- `src/ai_platform/evaluation/workflow_metrics.py`
  - `WorkflowCase`, `RecordedWorkflow`, 사례별·평균 지표와 완전한 사례 집합, 중복 작업 ID, 보류 계약, 키/객체 ID 불일치 입력 계약을 구현했습니다.
  - Router Accuracy 0.800000, Agent Task Success Rate 0.600000의 결정론적 기준선을 계산합니다.
- `src/ai_platform/evaluation/datasets.py`, `src/ai_platform/evaluation/__init__.py`
  - `volume10-support-policy@1.0.0`의 다섯 골든 사례 ID와 일치하는 고정 라우트·필수 작업 라벨 및 의도적인 누락·no-answer 실패 기록을 공개 인터페이스로 연결했습니다.
- `examples/volume10/workflow_quality.py`
  - 고정 워크플로의 Router 정확도와 Agent 작업 성공률을 외부 호출 없이 출력합니다.
- `tests/evaluation/test_workflow_metrics.py`, `tests/evaluation/test_volume10_completion_contract.py`
  - 기준 수치, 사례 ID 일치, 누락/예상 밖 작업, 불완전 결과, 모순된 no-answer 계약, 다섯 번째 장의 14개 필수 섹션과 실제 산출물 연결을 검증합니다.
- `docs/volume10-evaluation/README.md`
  - 다섯 번째 장 링크와 Router·Agent 오프라인 실행 경로를 추가했습니다.

#### 검증 기록

```text
$ uv run python examples/volume10/workflow_quality.py
Evaluation cases: 5
Router accuracy: 0.800000
Agent task success rate: 0.600000

$ uv run pytest tests/evaluation -q
39 passed

$ uv run ruff check src/ai_platform/evaluation tests/evaluation examples/volume10
All checks passed!

$ uv run mypy src/ai_platform/evaluation
Success: no issues found in 6 source files

$ uv run python scripts/validate_code_blocks.py && uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py
코드 블록 검증 통과
문서 검증 통과: Volume 11개
링크 검증 통과
```

## 알려진 차단 사항

- Volume 10은 다섯 장, 버전 관리되는 골든 데이터셋, 검색 평균·사례별 실패 분석, 답변·보류·환각·인용 기준선, Router·Agent 기준선만 완료했습니다. PRD의 Volume Definition of Done을 아직 만족하지 않으므로 `VOLUME10_COMPLETE=true`를 설정하지 않았습니다.
- 고정 사실 ID 비교는 자연어 주장 의미, 인용 문서의 정확한 구간, 필수 인용의 완전성을 판정하지 않습니다. 사람 검토와 LLM-as-a-Judge는 후속 운영 평가 설계에서 라벨 지침·익명화·판정 변동 통제와 함께 보완해야 합니다.
- 고정 Top-3 순위와 기록 답변은 평가 계산을 설명하기 위한 입력입니다. 실제 Retriever·LLM·Router·Agent에 연결하는 통합 평가와 데이터셋 변경 승인 정책은 후속 장에서 구현합니다.

## 다음 작업

- 고정 기록을 기준으로 Latency·Token·Cost를 위한 결정론적 측정 계약을 작성합니다.
