# Volume 05 RAG 진행 기록

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
