# Volume 05 RAG 진행 기록

## 2026-08-11 — 주입 가능한 로컬/Mock 임베딩·메모리 벡터 저장소 슬라이스 완료

### 완료

- `TextEmbedder`와 `VectorStore` Protocol, `VectorRecord`·`VectorSearchResult`, 결정론적 `InMemoryVectorStore`, `VectorRagIndex`를 추가했습니다. 임베딩/저장소 SDK·네트워크·파일·라이브 API를 직접 만들지 않고, `LocalRagIndex`의 검증된 청크만 명시적으로 주입한 Mock 경계에 전달합니다.
- 저장소에는 청크 ID와 유한한 비영 벡터만 전달되며 원문·제목·URI·오프셋은 저장하지 않습니다. 검색 결과는 동일한 로컬 청크 ID에만 다시 연결하므로 기존 인용 범위가 보존됩니다.
- Mock 임베더의 반환 수·tuple 벡터·차원·유한성·영 벡터와 저장소의 결과 타입·요청 수·알 수 없는/중복 ID·정렬을 엄격히 검증했습니다. `InMemoryVectorStore`는 같은 차원 벡터의 cosine 유사도를 0~1로 정규화하고 청크 ID로 동점을 결정론적으로 해소합니다.
- 로컬 예제에 고정 4차원 `SampleTextEmbedder`와 `InMemoryVectorStore`를 추가해 배송 의미 검색과 기존 로컬 인용 경계를 확인했습니다. 기존 Hybrid/RRF 평가·승인 기준선은 그대로 유지하며, 라이브 API·비밀값·배포는 사용하지 않았습니다.
- Volume 05 단위 테스트는 정상 의미 검색·원문 비저장 레코드·인용 보존, 메모리 cosine 순위, 신뢰하지 않는 임베더/저장소 출력, 레코드·설정·저장소 상태 거부를 포함합니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 8 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 6 source files
uv run pytest tests/unit/test_volume05_rag.py -q
# 195 passed
uv run python examples/volume05/local_rag.py
# Mock 임베딩·메모리 벡터 검색의 배송 근거/인용 경계, 고정 JSON 평가 Recall@1·Hit rate·MRR 1.00,
# 승인 기준선/기록 회귀 판정, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
git diff --check
# 통과
```

### 다음 슬라이스

- PRD의 남은 RAG 실습 DoD인 프레임워크 독립 `LocalRagApi`를 실제 FastAPI 요청/응답 어댑터로 연결하되, 서버 실행·라이브 API·비밀값·배포 없이 TestClient와 Mock 파이프라인으로 검증합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 승인 기준선 콘텐츠 식별자·평가 기록 참조 무결성 슬라이스 완료

### 완료

- `retrieval_regression_baseline_content_id()`를 추가했습니다. 기준선 사례·집계 지표와 회귀 정책의 의미론적 정규 JSON을 소문자 `sha256:` 식별자로 결정론적으로 고정하므로, 파일 공백이나 JSON 키 순서는 무시하면서 사례·지표·정책 변경은 감지합니다.
- `RetrievalRegressionBaselineAuditMetadata`와 고정 기준선 JSON `audit`에 필수 `content_id`를 추가했습니다. 로더는 감사 ID 형식과 실제 로드한 기준선/정책 콘텐츠의 일치를 확인하며, `RetrievalRegressionChecker`도 외부에서 전달된 감사 메타데이터가 비교 대상 객체와 맞지 않으면 비교 전에 거부합니다.
- `RetrievalEvaluationAuditMetadata`·`RetrievalEvaluationAuditRequirement` 및 로컬 기록 JSON에 `comparison_content_id`를 추가했습니다. 감사된 회귀 비교는 대상 ID·승인 참조·콘텐츠 ID 세 값이 기준선과 승인 평가 기록 모두에 일치할 때만 실행됩니다.
- 샘플 기준선과 로컬 예제는 로드한 기준선 감사의 콘텐츠 ID를 평가 기록과 비교 요구사항에 그대로 연결합니다. 여전히 local/sample data, 임시 로컬 기록과 Mock 제공자 경계만 사용하며 라이브 API·비밀값·배포를 사용하지 않았습니다.
- 기준선 내용을 ID 갱신 없이 편집한 파일 거부와, 승인 평가 기록의 콘텐츠 참조 변경 거부를 Volume 05 단위 테스트로 추가했습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run pytest tests/unit/test_volume05_rag.py -q
# 179 passed
uv run python examples/volume05/local_rag.py
# 고정 JSON 평가 세트 Recall@1·Hit rate·MRR 모두 1.00, 콘텐츠 참조가 연결된 승인 기준선/기록 회귀 판정 통과, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- PRD의 남은 RAG 실습 DoD(주입 가능한 로컬/Mock embedding·벡터 저장소 경계와 FastAPI 어댑터)를 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 승인 기준선·평가 기록 참조 무결성 슬라이스 완료

### 완료

- `RetrievalRegressionBaselineAuditMetadata`를 추가하고 고정 로컬 기준선 파일에 불변 `baseline_id`, 승인 참조, 승인일, 보존 종료일을 엄격히 요구했습니다. 기준선 JSON은 이제 정확한 `baseline`·`policy`·`audit` 루트 구조만 허용합니다.
- 평가 기록의 `RetrievalEvaluationAuditMetadata`와 비교 요청의 `RetrievalEvaluationAuditRequirement`에 대상 기준선 승인 참조를 추가했습니다. 따라서 평가 기록은 단순 대상 ID뿐 아니라 승인된 기준선의 정확한 승인 참조도 명시해야 합니다.
- `RetrievalRegressionChecker.evaluate_record()`는 감사된 기준선 메타데이터 없이 실행되지 않으며, 요청·기준선·평가 기록의 대상 ID와 승인 참조, 승인일·보존 기간을 모두 결정론적으로 검증한 뒤에만 품질 비교를 수행합니다. 대상/승인 참조 변경, 승인 전 기준일, 만료 및 미승인 기록은 비교 전에 거부됩니다.
- 샘플 기준선·예제·문서를 새 계약으로 갱신했습니다. 예제는 local/sample data, 임시 로컬 기록 및 Mock 제공자 경계만 사용하며 라이브 API·비밀값·배포를 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 178 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run python examples/volume05/local_rag.py
# 고정 JSON 평가 세트 Recall@1·Hit rate·MRR 모두 1.00, 승인 기준선/기록 참조 무결성 및 회귀 판정 통과, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 승인된 기준선 파일의 변경 감지용 결정론적 콘텐츠 식별자와 평가 기록의 기준선 콘텐츠 참조를 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 불변 평가 기록 감사 메타데이터 슬라이스 완료

### 완료

- `RetrievalEvaluationAuditMetadata`와 `RetrievalEvaluationAuditRequirement`를 추가했습니다. 고정 로컬 평가 기록은 불변 `record_id`, 명시 비교 대상 ID, 승인 상태·승인 참조·승인 일자·보존 종료일을 함께 기록하며, `pending`·`approved`·`superseded`·`revoked` 수명 상태별 필수 필드 조합을 엄격히 검증합니다.
- `LocalRetrievalEvaluationReportStore.record()`는 감사 메타데이터 없이는 새 파일을 기록하지 않고, `load_record()`는 기존 지표 재계산 검증과 함께 감사 JSON의 정확한 스키마·ISO 날짜·상태 전이를 검증한 `RetrievalEvaluationRecord`를 반환합니다. 기존 `load()`는 보고서만 필요한 호출자를 위해 재검증 결과의 report를 반환합니다.
- `RetrievalRegressionChecker.evaluate_record()`는 명시 `RetrievalEvaluationAuditRequirement`의 비교 대상 ID·기준일을 적용합니다. 승인되지 않은 기록, 대상 변경, 보존 만료는 검색 품질 비교 전에 결정론적으로 거부합니다. 현재 시각·네트워크·제공자 SDK·생성기 호출은 사용하지 않습니다.
- 로컬 예제는 임시 허용 루트에서 승인된 고정 감사 메타데이터를 포함한 보고서를 기록·재로딩하고, 동일 대상/고정 기준일로 파일 기반 기준선과 비교합니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 178 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run python examples/volume05/local_rag.py
# 고정 JSON 평가 세트 Recall@1·Hit rate·MRR 모두 1.00, 승인된 감사 기록·재검증 및 기준선 회귀 판정 통과, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 고정 감사 메타데이터의 승인 기준선 파일과 평가 기록 사이의 참조 무결성(대상 ID 및 승인 참조)을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 고정 로컬 평가 보고서 기록·재검증 슬라이스 완료

### 완료

- `LocalRetrievalEvaluationReportStore`와 `RetrievalEvaluationReportFileConfig`를 추가했습니다. 이 경계는 호출자가 명시한 허용 루트의 UTF-8 `.json` 파일 하나에 검증된 고정 검색 평가 보고서만 기록·재로딩하며, 자동 탐색·검색·생성·네트워크·제공자 SDK를 호출하지 않습니다.
- 기록은 기존 파일을 덮어쓰지 않고, 보고서의 `top_k`·사례 수·집계 지표·사례별 질의·기대/회수 청크 ID·첫 관련 순위·지표를 결정론적으로 저장합니다. 재로딩은 경로/심볼릭 링크 탈출·빈/과대 파일·비 UTF-8·비표준 JSON·중복 키·지원하지 않는 필드를 거부합니다.
- 재검증은 `passed`, 첫 관련 순위, 사례별 Recall@k·MRR, 전체 Recall@k·Hit rate·MRR를 회수 청크 ID에서 다시 계산합니다. 따라서 편집되거나 호환성 정보가 누락된 기록은 파일 기반 기준선과 비교하기 전에 거부됩니다.
- 로컬 예제는 임시 허용 루트에 고정 평가 보고서를 기록·재로딩한 뒤 기존 파일 기반 기준선과 결정론적으로 비교합니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 172 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run python examples/volume05/local_rag.py
# 고정 JSON 평가 세트 Recall@1·Hit rate·MRR 모두 1.00, 임시 로컬 보고서 기록·재검증 및 파일 기반 기준선 회귀 판정 통과, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 고정 로컬 보고서와 기준선의 승인·보존 수명 및 비교 대상 변경을 명시하는 감사 메타데이터 계약을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 파일 기반 고정 회귀 기준선·정책 슬라이스 완료

### 완료

- `LocalRetrievalRegressionBaselineLoader`, `RetrievalRegressionBaselineLoadingConfig`, `RetrievalRegressionBaselineFile`을 추가했습니다. 이 경계는 호출자가 명시한 허용 루트 안의 UTF-8 `.json` 파일 하나만 읽으며 자동 탐색·검색·생성·네트워크·제공자 SDK를 호출하지 않습니다.
- 기준선 파일은 정확한 `{"baseline": {...}, "policy": {...}}` 구조만 허용합니다. 기준선에는 `top_k`, 순서가 보존된 사례 ID·질문·기대 청크 ID, Recall@k·Hit rate·MRR이 필요하며 정책은 세 지표의 최대 하락 폭을 모두 명시해야 합니다.
- 경로/심볼릭 링크 탈출·빈/과대 파일·비 UTF-8·비표준 JSON·중복 JSON 키·지원하지 않는 필드·빈/과대/중복 사례 및 범위를 벗어난 점수를 거부합니다. 로드한 값은 기존 `RetrievalRegressionChecker`에 그대로 전달되어 동일 평가 세트만 비교합니다.
- 로컬 예제는 `sample_data/retrieval-regression-baseline.json`에서 고정 1.00 기준선과 무하락 정책을 읽어 평가 보고서와 비교합니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 162 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run python examples/volume05/local_rag.py
# 고정 JSON 평가 세트 Recall@1·Hit rate·MRR 모두 1.00, 파일 기반 기준선 회귀 판정 통과, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 고정 로컬 평가 보고서를 별도 파일 계약으로 기록·재검증하고, 파일 기반 기준선과 결정론적으로 비교하는 경계를 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 고정 기준선 검색 회귀 판정 슬라이스 완료

### 완료

- `RetrievalEvaluationBaseline`·`RetrievalEvaluationBaselineCase`·`RetrievalRegressionPolicy`·`RetrievalRegressionChecker`와 지표별/전체 판정 payload 계약을 추가했습니다. 이 경계는 이미 계산된 로컬 검색 평가 보고서만 비교하며 검색·생성·파일·네트워크·제공자 SDK를 호출하지 않습니다.
- 기준선과 현재 보고서의 `top_k`, 사례 순서·ID·질문, 기대 청크 ID가 모두 같을 때만 비교합니다. 따라서 서로 다른 데이터셋·관련성 정의·반환 깊이를 품질 변화로 오인하지 않으며, 호환되지 않으면 명시적으로 거부합니다.
- Recall@k·Hit rate·MRR은 각각 0~1의 최대 하락 허용 폭을 갖습니다. 기본 정책은 하락을 허용하지 않고, 호환되는 품질 저하는 숨기지 않은 `passed: false`와 기준선·현재·하락·허용 폭으로 반환합니다.
- 로컬 예제는 고정 JSON 평가 사례 및 각 지표 1.00의 명시적 기준선과 현재 보고서를 비교해 회귀 판정 통과를 출력합니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 147 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run python examples/volume05/local_rag.py
# 고정 JSON 평가 세트 Recall@1·Hit rate·MRR 모두 1.00, 기준선 회귀 판정 통과, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 고정 기준선 및 회귀 판정 payload를 로컬 파일에서 다시 읽고 엄격히 검증하는 경계를 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 파일 기반 고정 로컬 검색 평가 세트 슬라이스 완료

### 완료

- `LocalRetrievalEvaluationSetLoader`와 `RetrievalEvaluationSetLoadingConfig`를 추가했습니다. 이 경계는 호출자가 명시한 허용 루트 안의 UTF-8 `.json` 파일 하나만 읽으며, 자동 탐색·네트워크·제공자 SDK·생성기 호출을 하지 않습니다.
- 평가 세트는 정확한 `{"cases": [...]}` JSON 구조와 사례별 `case_id`·`query`·`expected_chunk_ids` 배열만 허용합니다. 중복 JSON 키·중복 사례 ID·빈/과대 파일·비 UTF-8·비표준 JSON·경로/심볼릭 링크 탈출·지원하지 않는 필드 및 타입을 거부합니다.
- 로컬 예제의 배송·반품·PDF 교환 고정 사례를 `sample_data/retrieval-evaluation.json`으로 옮기고, 검증된 사례를 기존 `RetrievalEvaluator`에 전달하도록 변경했습니다. 예제는 여전히 local/sample data와 Mock 제공자 경계만 사용합니다.
- 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 137 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run python examples/volume05/local_rag.py
# 고정 JSON 평가 세트의 Recall@1·Hit rate·MRR 모두 1.00, 인용 답변 및 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 로컬 검색 평가 보고서의 기준선 비교와 결정론적 회귀 판정 계약을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 고정 로컬 검색 품질 평가 계약 슬라이스 완료

### 완료

- `RetrievalEvaluationCase`, `RetrievalEvaluationConfig`, `RetrievalEvaluator`, 사례 결과·보고서 계약을 추가했습니다. 생성기·네트워크·제공자 SDK·실시간 데이터 없이 호출자가 명시한 고정 질의와 기대 청크 ID만 평가합니다.
- 사례별 기대 근거 회수 비율(Recall@k), 첫 기대 근거의 역순위, hit 여부를 보존하고, 전체 세트에는 마이크로 Recall@k·Hit rate·MRR을 결정론적으로 집계합니다. `to_payload()`는 원문과 생성 답변 없이 사례 ID·청크 ID·순위·지표만 반환합니다.
- 빈/중복 사례, 빈/중복 기대 청크 ID, 범위를 벗어난 설정과 tuple 이외·과다·중복 검색 결과를 거부해 신뢰하지 않는 검색기 출력이 지표를 왜곡하지 못하게 했습니다. 검색 내부 오류는 숨기지 않습니다.
- 로컬 예제는 기존 sample data와 Mock 검색 체인으로 배송·반품·PDF 교환 고정 질의를 Recall@1·Hit rate·MRR로 평가하며, 실행 결과는 모두 1.00입니다.
- 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 117 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 7 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 5 source files
uv run python examples/volume05/local_rag.py
# 고정 샘플 검색 평가 Recall@1·Hit rate·MRR 모두 1.00, 인용 답변 및 No-answer 확인
```

### 다음 슬라이스

- 고정 로컬 평가 세트를 파일 기반으로 로드·검증하는 경계를 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 프레임워크 독립 로컬 RAG API 계약 슬라이스 완료

### 완료

- `RagQueryRequest`, `RagAnswerResponse`, `RagCitationResponse`, `RagErrorResponse`, `RagEndpointResponse`, `LocalRagApi`를 추가했습니다. HTTP 서버·FastAPI·네트워크 클라이언트·제공자 SDK 없이 역직렬화한 로컬 JSON 요청을 명시적인 응답 계약으로 변환합니다.
- 요청은 공백이 아닌 `query`와 선택적 1~20 정수 `top_k`만 허용합니다. 객체가 아닌 입력, 누락·빈 질문, boolean/범위 밖 `top_k`, 지원하지 않는 필드는 검색기나 생성기를 호출하지 않고 안정적인 `400` 및 `invalid_request` JSON 오류로 반환합니다.
- 성공 응답은 답변·`no_answer`·인용 배열을 JSON 호환 값으로 고정합니다. 인용은 label·chunk ID·제목·출처 URI·원문 문자 범위를 보존하며, No-answer에는 빈 인용만 허용합니다. 검색·생성 내부 오류는 요청 오류로 숨기지 않습니다.
- 로컬 예제는 기존의 local/sample data 및 Mock 생성기 체인을 `LocalRagApi.handle()`로 실행하도록 바꿨습니다. 테스트는 인용 JSON, No-answer와 생성기 미호출, 사전 검증 요청, 공개 400 오류 계약을 포함합니다.
- 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 103 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 6 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 4 source files
uv run python examples/volume05/local_rag.py
# 배송·반품·PDF 교환 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 로컬 고정 질의·기대 인용을 이용한 검색 품질 평가 계약을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 정규화 신뢰도 임계값·abstention 슬라이스 완료

### 완료

- `ConfidenceThresholdConfig`와 `ConfidenceThresholdIndex`를 추가했습니다. 이 경계는 이미 검색된 제한 후보만 받고, 근거 점수가 유한한 0~1 정규화 신뢰도인지 검증한 뒤 명시한 최소 신뢰도 이상인 청크만 원래 순서대로 전달합니다.
- 점수 척도를 변환하거나 새 근거를 만들지 않으며, 통과한 `SearchHit`를 그대로 반환해 점수·텍스트·매칭 용어·출처 URI·문자 범위와 인용 경계를 보존합니다. 정규화되지 않은 점수, tuple 이외 값, 요청보다 많은 후보, 중복 청크 ID는 거부합니다.
- 모든 후보가 임계값 미만이면 빈 결과를 반환합니다. 따라서 `RagPipeline`은 생성기를 호출하지 않고 결정론적 No-answer를 반환합니다.
- 예제의 로컬 Mock Hybrid/RRF·질의 변형·재순위화·문서 다양성·컨텍스트 예산 체인 끝에 후보 3개·최소 신뢰도 0.8 `ConfidenceThresholdIndex`를 연결했습니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.
- 임계값 경계값 포함 필터링, 인용 보존, 모든 근거의 abstention과 생성기 미호출, 비신뢰 검색 후보, 설정 범위를 Volume 05 단위 테스트에 추가했습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 94 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 배송·반품·PDF 교환 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 로컬 RAG API 경계를 입력·출력 계약과 Mock 생성기로 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 결정론적 문서 수준 검색 다양성 슬라이스 완료

### 완료

- `DocumentDiversityConfig`와 `DocumentDiversityIndex`를 추가했습니다. 이 경계는 이미 검색된 제한 후보만 받고, 원래 순위를 유지하면서 문서별로 선택할 수 있는 전체 청크 수를 명시적으로 제한합니다.
- 제한에 도달한 상위 문서의 후속 청크는 건너뛰어 다음 문서의 근거를 선택합니다. 선택된 `SearchHit`를 그대로 반환하므로 점수·텍스트·매칭 용어·출처 URI·문자 범위와 인용 경계가 변하지 않습니다.
- 후보 수와 문서당 청크 수는 각각 1~20으로 제한했습니다. 기반 인덱스가 tuple 이외 값, 요청보다 많은 후보, 중복 청크 ID, `SearchHit` 이외 값을 반환하면 거부합니다.
- 예제의 로컬 Mock Hybrid/RRF·질의 변형·재순위화 체인과 전체 청크 컨텍스트 예산 사이에 후보 3개·문서당 1개 `DocumentDiversityIndex`를 연결했습니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.
- 문서당 제한으로 다음 문서 근거 선택, 구성 가능한 다중 청크 순서, 인용 보존, 비신뢰 검색 후보와 설정 범위를 Volume 05 단위 테스트에 추가했습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 86 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 배송·반품·PDF 교환 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 로컬 검색 근거의 신뢰도 임계값과 abstention 계약을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 결정론적 전체 청크 컨텍스트 예산 슬라이스 완료

### 완료

- `ContextBudgetConfig`와 `ContextBudgetIndex`를 추가했습니다. 이 경계는 이미 검색된 제한 후보만 받고, 생성기에 전달할 근거의 텍스트 합계를 명시적인 문자 예산 안으로 제한합니다.
- 청크를 절단하거나 새 메타데이터를 만들지 않습니다. 원래 순위를 유지하면서 전체 청크만 선택하므로 출처 URI·문자 범위·매칭 용어·점수와 인용 경계가 그대로 보존됩니다. 남은 예산에 맞지 않는 상위 청크는 건너뛰고 뒤의 더 작은 근거를 결정론적으로 선택할 수 있습니다.
- 후보 수는 1~20, 문자 예산은 1~20,000으로 제한했습니다. 기반 인덱스가 tuple 이외 값, 요청보다 많은 후보, 중복 청크 ID, `SearchHit` 이외 값을 반환하면 거부합니다.
- 예제의 로컬 Mock Hybrid/RRF·재순위화 체인 뒤에 후보 3개·600문자 `ContextBudgetIndex`를 연결했습니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.
- 전체 청크 선택·예산 내 문자 합계·상위 초과 청크 건너뛰기·인용 보존·초과 청크에서의 No-answer와 생성기 미호출·비신뢰 검색 후보·설정 범위를 Volume 05 단위 테스트에 추가했습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 78 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 배송·반품·PDF 교환 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 로컬 검색 근거의 문서 수준 다양성을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 제한 후보·정규화 점수 재순위화 슬라이스 완료

### 완료

- `EvidenceReranker` Protocol, `RerankingConfig`, `RerankResult`, `RerankingIndex`를 추가했습니다. 재순위기는 이미 검색된 인용 가능한 로컬 `SearchHit`만 받고, 외부 모델·네트워크 클라이언트를 만들지 않습니다.
- 후보 수는 1~20으로 제한하고, 재순위 결과는 전달한 후보의 중복 없는 청크 ID 및 유한한 0~1 관련성 점수만 반환하도록 검증합니다. 새 출처 ID, tuple 이외 반환, 과다 결과, 중복 결과는 거부합니다.
- 최소 관련성 점수로 약한 근거를 제외하며, 동점은 기반 검색 순서를 유지합니다. 선택된 청크의 원래 출처 URI·문자 범위·매칭 용어는 그대로 보존해 인용 경계가 변하지 않습니다.
- 로컬 `SampleEvidenceReranker` Mock을 예제의 Hybrid/RRF 질의 변형 뒤에 연결했습니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.
- 후보 제한·점수 재정렬·동점·최소 점수·인용 보존·비신뢰 재순위기 출력·점수 범위 계약을 포함해 Volume 05 단위 테스트를 70개로 확장했습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 70 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 배송·반품·PDF 교환 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 로컬 검색 근거의 문서 수준 다양성 또는 결정론적 컨텍스트 예산 계약을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-11 — 로컬 Mock PDF 입력·페이지 인용 경계 슬라이스 완료

### 완료

- `PdfTextExtractor` Protocol과 `LocalPdfLoader`를 추가했습니다. PDF 엔진·네트워크 클라이언트는 생성하지 않고, 호출자가 주입한 로컬/Mock 파서만 사용합니다.
- PDF 입력은 허용 루트 안의 명시 `.pdf`만 읽으며, 경로 탈출·존재하지 않는 파일·빈 파일·헤더 누락·파일 크기 초과를 차단합니다. 파서 결과도 tuple 타입, 페이지 수, 페이지 문자 수, 빈 페이지, NUL, 비문자 값을 검증합니다.
- 정제된 각 페이지는 독립 `SourceDocument`가 되며 `local:path.pdf#page=N` ID 및 URL 인코딩된 `#page=N` 출처 URI를 갖습니다. 따라서 기존 청킹·검색·인용 경계가 페이지 원문 범위를 그대로 유지합니다.
- 실제 PDF 라이브러리 없이 `%PDF-` 고정 로컬 샘플과 `SamplePdfTextExtractor` Mock을 예제에 추가했습니다. PDF 교환 질문은 페이지 출처 인용을 출력하고, 기존 배송·반품·No-answer 흐름도 유지합니다.
- 정상·정제·메타데이터와 파일/파서 출력의 신뢰 경계를 포함해 Volume 05 단위 테스트를 57개로 확장했습니다. 라이브 API, 비밀값, 배포는 사용하지 않았습니다.

### 검증

저장소 루트에서 2026-08-11에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 57 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 배송·반품·PDF 교환 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 로컬 검색 근거를 점수 계약과 후보 제한으로 재순위화하는 RAG reranking 경계를 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-10 — 로컬 Mock Query Transformation·RRF 검색 슬라이스 완료

### 완료

- `QueryTransformer` Protocol, `QueryTransformationConfig`, `QueryTransformingIndex`를 추가했습니다. 변형기는 원 질문을 첫 번째로 보존한 `tuple`만 반환할 수 있고, 빈 값·정규화 중복·과다 확장·원 질문 누락을 즉시 거부합니다.
- 각 원/확장 질문의 검색 결과는 제공자 점수 크기를 섞지 않고 Reciprocal Rank Fusion(RRF) 순위로 결합합니다. 결합된 근거는 기존 청크·인용 경계를 유지하며 생성기에는 항상 사용자의 원 질문을 전달합니다.
- 예제를 고정 로컬 확장 규칙 `SampleQueryTransformer`와 기존 Mock dense 랭커 조합으로 확장했습니다. 네트워크, 라이브 API, 비밀값, 배포는 사용하지 않았습니다.
- RRF 점수·용어 병합, 원 질문 보존, 신뢰할 수 없는 변형기 출력 거부, 설정 검증을 포함해 Volume 05 단위 테스트를 42개로 확장했습니다.

### 검증

저장소 루트에서 2026-08-10에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 42 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 도착 예정·반품 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 외부 라이브 서비스 없이 PDF 입력을 파싱·검증하는 경계, 또는 로컬 검색 근거의 재순위화 계약을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-10 — Mock dense 후보와 RRF 하이브리드 검색 슬라이스 완료

### 완료

- `DenseCandidateRanker` Protocol과 `HybridRagIndex`를 추가해 로컬 sparse 검색 결과와 주입 가능한 Mock dense 후보를 Reciprocal Rank Fusion(RRF)으로 결합했습니다. dense 모델, 네트워크 클라이언트, 제공자 호출은 만들지 않았습니다.
- dense 후보는 현재 로컬 인덱스에 존재하는 청크 ID만 한 번씩 가리키도록 검증했습니다. 알 수 없는 ID·중복 ID·요청 수 초과 후보는 거부합니다.
- 파이프라인 검색 경계를 `SearchableIndex` Protocol로 일반화해 하이브리드 근거도 기존 Mock 생성기·인용·No-answer 흐름으로 전달합니다.
- 로컬 샘플 예제를 어휘가 겹치지 않는 도착 예정 질문, 반품 질문, No-answer 질문으로 확장했습니다. `SampleDenseRanker`는 고정된 로컬 청크 ID만 반환합니다.
- RRF 순위 결합, sparse 용어가 없는 Mock dense 근거의 인용, 신뢰할 수 없는 후보 거부, 설정 검증을 포함해 Volume 05 단위 테스트를 32개로 확장했습니다.

### 검증

저장소 루트에서 2026-08-10에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 32 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 도착 예정·반품 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
git diff --check
# 통과
```

### 다음 슬라이스

- 외부 라이브 서비스 없이 PDF 입력을 파싱·검증하는 경계, 또는 로컬 Query Transformation 계약을 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.

## 2026-08-10 — 명시적 다중 Markdown 문서 색인 슬라이스 완료

### 완료

- `LocalMarkdownLoader.load_many()`를 추가해 자동 디렉터리 탐색 없이 호출자가 명시한 로컬 Markdown 문서만 배치로 읽도록 했습니다.
- 빈 배치와 같은 정규화 경로를 가리키는 중복 입력을 거부하고, 반환 문서를 문서 ID 순으로 정렬해 다중 문서 색인 순서를 재현 가능하게 했습니다.
- 로컬 반품 샘플을 추가하고 예제를 배송·반품·No-answer 질문으로 확장했습니다. 외부 제공자, 라이브 API, 비밀값, 배포는 사용하지 않았습니다.
- 명시적 배치의 정렬·메타데이터와 빈/중복 배치 거부를 Volume 05 단위 테스트로 추가했습니다.

### 검증

저장소 루트에서 2026-08-10에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 24 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# 5 files already formatted
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
# All checks passed!
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 배송·반품 근거와 인용, 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
```

### 다음 슬라이스

- PDF 입력을 외부 라이브 서비스 없이 파싱·검증하는 경계, 또는 sparse/dense 후보를 결합하는 하이브리드 검색 계약을 별도 테스트 가능한 단계로 확장합니다.

## 2026-08-10 — 로컬 검색·인용 경계 슬라이스 완료

### 완료

- 로컬 `SourceDocument`를 원문 문자 범위가 보존되는 `DocumentChunk`로 나누는 `LocalRagIndex`를 추가했습니다.
- 외부 형태소 분석기나 제공자 호출 없이, 한글 조사·활용 접미사에 대한 접두 일치 검색을 추가했습니다. 라틴 문자와 숫자는 정확 일치만 허용합니다.
- `RagPipeline`이 검색 근거가 없을 때 Mock 생성기를 호출하지 않고 No-answer를 반환하도록 했습니다.
- Mock 생성 결과에 출처 URI와 오프셋을 포함한 인용을 부여했습니다.
- 로컬 샘플 문서와 실행 예제, 14개 단위 테스트, 사용·안전 경계를 문서화했습니다.

### 검증

저장소 루트에서 2026-08-10에 다음을 모두 통과했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 14 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
uv run mypy src/ai_platform/rag
# Success: no issues found in 2 source files
uv run python examples/volume05/local_rag.py
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
```

예제는 샘플 배송 질문에서 인용을 출력하고, 샘플에 없는 주차장 할인 질문에서는 No-answer를 출력했습니다. 라이브 API, 시크릿, 배포를 사용하지 않았습니다.

### 다음 슬라이스

- Markdown loader의 입력 경계와 메타데이터 정제를 별도 테스트 가능한 단계로 확장합니다.

## 2026-08-10 — 안전한 로컬 Markdown loader 슬라이스 완료

### 완료

- `LocalMarkdownLoader`를 추가해 명시한 로컬 root 하위의 UTF-8 Markdown만 `SourceDocument`로 변환하도록 했습니다. 절대 경로·경로 탈출·root 밖 심볼릭 링크·지원하지 않는 확장자·누락 파일을 거부합니다.
- 로더는 BOM, CRLF, 수평 공백, 반복 빈 줄을 결정론적으로 정제하고 NUL·빈 콘텐츠·비 UTF-8 입력을 거부합니다.
- 첫 ATX 제목을 정제된 문서 제목으로 사용하고, 제목이 없으면 파일명에서 안전한 제목을 유도합니다. 문서 ID와 URI는 root 상대 경로에서 결정론적으로 생성하며 URI 경로는 인코딩합니다.
- 기존 로컬 Mock 생성 예제를 Markdown 샘플과 loader 경계로 전환했습니다. 외부 제공자·라이브 API·비밀값·배포는 사용하지 않았습니다.
- loader 성공·제목 fallback·경로 탈출·확장자·빈 파일·NUL·UTF-8 경계를 포함해 Volume 05 단위 테스트를 21개로 확장했습니다.

### 검증

저장소 루트에서 2026-08-10에 다음을 실행했습니다.

```text
uv run pytest tests/unit/test_volume05_rag.py -q
# 21 passed
uv run ruff format --check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
uv run ruff check src/ai_platform/rag tests/unit/test_volume05_rag.py examples/volume05/local_rag.py
uv run mypy src/ai_platform/rag
# Success: no issues found in 3 source files
uv run python examples/volume05/local_rag.py
# 인용 가능한 배송 답변 및 주차장 할인 No-answer 확인
uv run python -m compileall -q src/ai_platform/rag examples/volume05
uv run python scripts/check_secrets.py docs/volume05-rag examples/volume05 src/ai_platform/rag tests/unit/test_volume05_rag.py
# 비밀값 검사 통과
uv run python scripts/validate_docs.py
# 문서 검증 통과: Volume 11개
```

### 다음 슬라이스

- PDF 입력을 외부 라이브 서비스 없이 파싱·검증하는 경계, 또는 정제된 Markdown 다중 문서 색인을 별도 계약으로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.
