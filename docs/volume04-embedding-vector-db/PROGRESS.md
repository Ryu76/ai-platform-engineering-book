# Volume 04 작업 진행 기록

## 현재 상태

- 완료 표식: `VOLUME04_COMPLETE` 미설정
- 현재 slice: 35 — dot product overflow cancellation 보존
- 검증: Volume 04 테스트 81 passed, ruff/mypy 통과, 네 개의 local mock 예제 실행.
- 범위: 외부 API, 다운로드 모델, Docker, Qdrant를 실행하지 않았습니다.



## 2026-08-10 — Slice 01 완료

### 추가한 결과물

- `src/ai_platform/embeddings/embedding_service.py`
  - `EmbeddingModel` Protocol
  - SHA-256 기반 결정적 로컬 dense embedding
  - cosine similarity, dot product, Euclidean distance 및 입력 검증
- `examples/volume04/embedding_similarity.py`
  - 네트워크 없는 문장 비교 예제
- `tests/unit/test_volume04_embedding_service.py`
  - 재현성, 관련 문서 순위, 수학 기준값, 실패 경로 검증
- `01-learning-objectives.md`
  - 장 템플릿의 14개 섹션과 실행·오류 해결·과제 수록

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py -q
# 18 passed in 0.12s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 3 source files
uv run python examples/volume04/embedding_similarity.py
# query_dimensions=64; Python API 오류 처리와 재시도 전략이 1위 (score=0.548)
uv run python examples/volume04/vector_store_search.py
# collection_size=3; retry-guide가 topic=api filter에서 1위 (score=0.548)
```

`uv`는 이 호스트의 PATH에 없어서 절대 경로인 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. 명령 자체의 프로젝트 기준 표기는 `uv`로 유지합니다. 실행 중 Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고만 있었고, uv가 프로젝트 환경을 사용해 검증을 완료했습니다.

## 2026-08-10 — Slice 02 완료

### 추가한 결과물

- `src/ai_platform/embeddings/vector_store.py`
  - 고정 차원의 local collection 생성
  - ID/vector/payload를 갖는 immutable point와 batch-atomic upsert
  - cosine ranking, scalar metadata filter, 안정적인 동점 정렬, 삭제
  - zero vector, 비유한 수, 차원 불일치, 잘못된 payload 계약 검증
- `examples/volume04/vector_store_search.py`
  - 네트워크 없이 collection 크기와 metadata-filter 검색 결과를 출력
- `tests/unit/test_volume04_vector_store.py`
  - 순위·payload·filter·교체·원자성·삭제·오류·동점 정렬을 검증
- `02-local-collection-payload-search.md`
  - collection, point, payload, filter, Qdrant 이행 주의사항을 14개 학습 섹션으로 설명

## 2026-08-10 — Slice 03 완료

### 추가한 결과물

- `src/ai_platform/embeddings/retrieval_evaluation.py`
  - stable point ID 순위용 `precision@k`, `recall@k`, reciprocal rank, `hit@k` 계산
  - 질의별 평균 지표·hit rate 요약과 유한 cosine score 기반 no-answer gate
  - 중복 순위, 빈 정답 판단, 잘못된 k·점수 계약 검증
- `examples/volume04/retrieval_quality.py`
  - local mock 검색 결과를 정답 ID와 비교하고 threshold 결과를 출력
- `tests/unit/test_volume04_retrieval_evaluation.py`
  - top-k 지표, 요약, local store end-to-end 평가, gate 경계 및 오류를 검증
- `03-retrieval-quality-no-answer.md`
  - relevance judgment, 측정 지표, threshold의 한계와 운영 평가 설계를 14개 섹션으로 설명

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py -q
# 29 passed in 0.13s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 4 source files
uv run python examples/volume04/retrieval_quality.py
# ranked_ids=retry-guide,vector-guide
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; hit_at_1=True
# top_score=0.548; minimum_score=0.500; answerable=True
```

외부 API, 모델 다운로드, Docker, Qdrant 또는 비밀값을 사용하지 않았습니다. 이 호스트에서 `uv`는 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고만 있었고 프로젝트 환경으로 검증을 완료했습니다.

## 2026-08-10 — Slice 04 완료

### 추가한 결과물

- `src/ai_platform/embeddings/reindex_lifecycle.py`
  - 고정 문서 collection의 삭제, stable ID 재색인, version metadata와 top-1 품질 회복 workflow
  - 예제와 단위 테스트가 공유하는 immutable `ReindexLifecycleReport`
- `examples/volume04/reindex_lifecycle.py`
  - 삭제 전후 ranked IDs, 실제 삭제 수, 재색인 version과 collection 크기를 출력하는 네트워크 없는 실행 예제
- `tests/unit/test_volume04_reindex_lifecycle.py`
  - stale point 제거, version 2 재색인, metadata filter 검색, lifecycle 재현성을 검증
- `04-reindex-lifecycle-mini-project.md`
  - 삭제와 재색인, version metadata, 운영 이행 주의사항을 14개 학습 섹션으로 설명

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py -q
# 31 passed in 0.17s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/reindex_lifecycle.py
# initial_ranked_ids=retry-guide,docker-guide,vector-guide
# deleted_count=1; collection_size_after_delete=2
# ranked_ids_after_delete=docker-guide,vector-guide
# reindexed_ranked_ids=retry-guide
# reindexed_version=2; collection_size=3; top_1_recovered=True
```

외부 API, 모델 다운로드, Docker, Qdrant 또는 비밀값을 사용하지 않았습니다. 이 호스트에서 `uv`는 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고만 있었고 프로젝트 환경으로 검증을 완료했습니다.

## 남은 PRD 완료 조건

- [x] Volume 문서의 나머지 장과 권 단위 완료·인계 장을 작성한다.
- [ ] Qdrant Docker Compose 실행 및 collection 생성을 문서화·검증한다.
- [x] 결정적 local mock에서 vector와 metadata/payload 저장 및 query 검색을 구현·검증했다.
- [x] 결정적 local mock에서 검색 결과 해석을 실습으로 검증했다.
- [x] 결정적 local mock에서 데이터 삭제와 ID 기반 재색인(upsert)을 구현·검증했다.
- [x] 결정적 local mock에서 정답 ID 기반 top-k 검색 품질과 no-answer gate를 구현·검증했다.
- [x] 결정적 local mock에서 stale point 삭제와 stable ID의 versioned 재색인 lifecycle을 미니 프로젝트로 구현·검증했다.
- [ ] Qdrant용 `docker-compose.yml`, `scripts/index_documents.py`를 추가하고 검증한다. (`vector_store.py`는 완료)
- [x] 권 단위 완료 체크리스트를 작성·검증한다.
- [x] 다음 권(RAG) 인계 결과물을 정리한다.

## 2026-08-10 — Slice 05 완료

### 추가한 결과물

- `05-vector-db-migration-contracts.md`
  - 결정적 local mock이 보존해야 할 collection/table, dimension, cosine metric, stable ID, payload, filter, delete·reindex 계약을 명시
  - Qdrant, pgvector, Chroma의 역할과 database별 검증 포인트를 비교
  - score direction, ANN 동점 정렬, no-answer threshold 재평가, tenant·ACL filter의 이행 함정을 정리
  - 허가된 이후의 local Qdrant Docker integration에서 실행할 schema·fixture·lifecycle parity 순서를 정의
- `README.md`
  - 05장 상태와 이행 계약 결과물을 반영

### 범위 확인

- 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않았습니다.
- root `docker-compose.yml` 또는 `scripts/index_documents.py`는 cron의 허용 경로 밖이므로 만들거나 수정하지 않았습니다.
- 실제 database API field는 pinned client와 공식 문서를 확인하는 후속 local integration에서만 확정합니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py -q
# 31 passed in 0.17s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
uv run python examples/volume04/vector_store_search.py
uv run python examples/volume04/retrieval_quality.py
uv run python examples/volume04/reindex_lifecycle.py
# 각 예제가 네트워크 없이 기대한 결정적 검색·품질·삭제·재색인 결과를 출력
```

또한 Python으로 05장의 `## 1.`부터 `## 14.`까지의 14개 섹션, README의 장 링크, 이 진행 기록의 Slice 05 항목을 검증했습니다. `uv`는 이 호스트의 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고만 있었고, uv가 프로젝트 환경으로 검증을 완료했습니다.

## 2026-08-10 — Slice 06 완료

### 추가한 결과물

- `06-completion-checklist-rag-handoff.md`
  - local mock DoD와 별도 허가가 필요한 실제 Qdrant integration DoD를 명확히 분리
  - 완료 표식과 cron pause의 사전 조건을 기록하고, 현재는 실제 database 증거가 없어 완료하지 않음을 명시
  - Volume 05 RAG의 stable chunk ID, payload/authorization filter, score policy, generation-aware lifecycle 인계 contract 정리
- `tests/unit/test_volume04_learning_materials.py`
  - 01–06장의 14개 학습 섹션, README의 장·예제·Volume 04 테스트 연결, 실제 Qdrant 미검증 상태를 구조적으로 검증
- `README.md`
  - 06장 링크, 학습 자료 검사 명령, RAG 인계 링크 반영

### 범위 확인

- 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않았습니다.
- 허용된 Volume 04 문서·예제·테스트·embeddings source 외의 파일은 변경하지 않았습니다.
- 실제 Qdrant Docker Compose와 `scripts/index_documents.py`는 cron 허용 경로 밖이므로 생성하거나 수정하지 않았습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 34 passed in 0.22s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# query_dimensions=64; retry document score=0.548로 1위
uv run python examples/volume04/vector_store_search.py
# collection_size=3; retry-guide score=0.548 topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; hit_at_1=True; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

`uv`는 이 호스트의 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고만 있었고 프로젝트 환경으로 검증했습니다. 학습 자료 테스트는 01–06장의 14개 섹션, README 링크, 실제 Qdrant 미검증 상태를 확인했습니다.

## 2026-08-10 — Verification Tick 07 완료

### 재검증 결과

- `tests/unit/test_volume04_embedding_service.py`, `test_volume04_vector_store.py`, `test_volume04_retrieval_evaluation.py`, `test_volume04_reindex_lifecycle.py`, `test_volume04_learning_materials.py`를 함께 실행해 **34 passed in 0.25s**를 확인했습니다.
- `ruff check`는 `src/ai_platform/embeddings`, `examples/volume04`, Volume 04 테스트에서 통과했고, `mypy src/ai_platform/embeddings`도 5개 source file에서 오류 없이 통과했습니다.
- 네 개의 Volume 04 예제를 모두 실행했습니다. embedding 검색의 최상위 score는 `0.548`, payload-filter 검색의 결과는 `retry-guide`, 품질 예제는 `precision_at_1=1.0`/`answerable=True`, lifecycle 예제는 `reindexed_version=2`/`top_1_recovered=True`였습니다.
- `git diff --check`와 작업 트리를 확인해 공백 오류와 미커밋 변경이 없음을 확인했습니다.

### 완료 상태

- 실제 Qdrant service DoD(고정 버전 local-only Compose, schema 조회, payload filter·upsert·delete·reindex parity, cleanup/idempotency)는 아직 미검증입니다.
- 이 cron의 허용 범위는 `docs/volume04-embedding-vector-db/`, `examples/volume04/`, Volume 04 tests, `src/ai_platform/embeddings/`로 한정되어 있으므로 root Compose·script나 실제 service를 만들거나 실행하지 않았습니다.
- 따라서 `VOLUME04_COMPLETE=true`는 계속 설정하지 않았고 cron도 pause하지 않았습니다.

## 2026-08-11 — Verification Tick 08 완료

### 재검증 결과

- 허용된 Volume 04 단위 테스트 5개를 함께 실행해 **34 passed in 0.25s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04`와 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `retry-guide`를 1위에 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`였습니다.
- `git diff --check`와 `git status --short`도 실행했습니다. 검사 시점에 공백 오류와 미커밋 변경은 없었습니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD는 여전히 미검증입니다. 이 job은 Docker 실행과 허용 경로 밖의 root Compose·script 변경을 할 수 없으므로 해당 항목을 완료로 표기하지 않았습니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 위 검증을 완료했습니다.

## 2026-08-11 — Verification Tick 09 완료

### 재검증 결과

- 허용된 Volume 04 단위 테스트 5개를 함께 실행해 **34 passed in 0.23s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04`와 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `retry-guide`를 1위에 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`였습니다.
- `git diff --check`도 통과했습니다. 검증 시작 시 작업 트리는 clean했으며, 이 progress 기록만 이번 tick의 변경입니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD는 여전히 미검증입니다. 이 job은 Docker 실행과 허용 경로 밖의 root Compose·script 변경을 할 수 없으므로 해당 항목을 완료로 표기하지 않았습니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 위 검증을 완료했습니다.

## 2026-08-11 — Verification Tick 10 완료

### 재검증 결과

- 허용된 Volume 04 단위 테스트 5개를 함께 실행해 **34 passed in 0.19s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04`와 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `retry-guide`를 1위에 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`였습니다.
- 검증 명령 마지막의 `git diff --check`도 통과했습니다. 이 기록을 추가하기 전 작업 트리는 clean했습니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD는 여전히 미검증입니다. 이 job은 Docker 실행과 허용 경로 밖의 root Compose·script 변경을 할 수 없으므로 해당 항목을 완료로 표기하지 않았습니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 위 검증을 완료했습니다.

## 2026-08-11 — Verification Tick 11 완료

### 재검증 결과

- 허용된 Volume 04 단위 테스트 5개를 함께 실행해 **34 passed in 0.26s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04`와 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `retry-guide`를 1위에 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `recall_at_1=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`였습니다.
- 변경 전 작업 트리는 clean했고, 검증 명령의 `git diff --check`도 통과했습니다. 이번 tick의 변경은 이 진행 기록뿐입니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD는 여전히 미검증입니다. 이 job은 Docker 실행과 허용 경로 밖의 root Compose·script 변경을 할 수 없으므로 해당 항목을 완료로 표기하지 않았습니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 위 검증을 완료했습니다.

## 2026-08-11 — Verification Tick 12 완료

### 재검증 결과

- 허용된 Volume 04 단위 테스트 5개를 함께 실행해 **34 passed in 0.18s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04`와 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `retry-guide`를 1위에 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `recall_at_1=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`였습니다.
- 검증 명령 마지막의 `git diff --check`도 통과했습니다. 이 기록을 추가하기 전 작업 트리는 clean했습니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD는 여전히 미검증입니다. 이 job은 Docker 실행과 허용 경로 밖의 root Compose·script 변경을 할 수 없으므로 해당 항목을 완료로 표기하지 않았습니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 위 검증을 완료했습니다.

## 2026-08-11 — Verification Tick 13 완료

### 재검증 결과

- 허용된 Volume 04 단위 테스트 5개를 함께 실행해 **34 passed in 0.17s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04`와 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `retry-guide`를 1위에 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `recall_at_1=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`였습니다.
- 검증 명령 마지막의 `git diff --check`도 통과했습니다. 이 기록을 추가하기 전 작업 트리는 clean했습니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD는 여전히 미검증입니다. 이 job은 Docker 실행과 허용 경로 밖의 root Compose·script 변경을 할 수 없으므로 해당 항목을 완료로 표기하지 않았습니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 위 검증을 완료했습니다.

## 2026-08-11 — Verification Tick 14 완료

### 재검증 결과

- Volume 04 전용 단위 테스트 5개(총 25개 test function)를 함께 실행해 **34 passed in 0.23s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04`와 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `retry-guide`를 1위에 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`였습니다.
- 기록 전 `git status --short --branch`는 `volume-04` branch의 clean 작업 트리를 보였고, 검증 명령 마지막의 `git diff --check`도 통과했습니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, PostgreSQL, Chroma, 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD(고정 버전 local-only Compose, schema 조회, payload filter·upsert·delete·reindex parity, cleanup/idempotency)는 cron의 허용 경로 및 실행 범위 밖이어서 여전히 미검증입니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 위 검증을 완료했습니다.

## 2026-08-11 — Slice 15 완료: vector math 입력 계약 강화

### 추가한 결과물

- `embedding_service.py`의 cosine, dot product, Euclidean distance 공통 입력 검증이 문자열 container와 bool·`NaN`·무한대를 포함한 비유한 값을 일관된 `VectorDimensionError`로 거부하도록 강화했습니다.
- `test_volume04_embedding_service.py`에 세 연산 모두의 문자열, bool, `NaN` 거부 회귀 테스트를 추가했습니다.
- 01장 코드 설명과 오류 해결 표에 유한 수치 vector 계약을 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 37 passed in 0.18s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# retry 문서 score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `feat(volume04): validate vector math inputs`

## 2026-08-11 — Slice 16 완료: type-safe payload equality filter

### 추가한 결과물

- `vector_store.py`의 scalar equality filter가 payload key의 실제 존재와 value의 정확한 scalar type까지 확인하도록 강화했습니다.
  - 누락된 key는 `None` filter와 일치하지 않습니다.
  - Python의 `True == 1` 동치가 boolean/integer metadata filter 경계를 우회하지 않습니다.
- `test_volume04_vector_store.py`에 missing-key/`None` 및 bool/int filter 회귀 테스트를 추가했습니다.
- 02장과 05장에 local mock filter의 exact key/value/type 계약과 실제 backend 이행 시 확인할 의미를 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 38 passed in 0.19s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# retry 문서 score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): enforce typed payload filters`

## 다음 slice

실제 vector database DoD는 현재 cron 범위 밖입니다. 별도 허가된 local integration에서 pinned Qdrant의 schema, payload filter, ID upsert/delete, versioned reindex parity를 실행·기록합니다. 그 전에는 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않습니다.

## 2026-08-11 — Slice 17 완료: retrieval metric record 입력 계약 강화

### 추가한 결과물

- `retrieval_evaluation.py`의 public immutable `RetrievalMetrics`와 `RetrievalSummary`가 생성 시 모든 수치 지표를 bool이 아닌 유한한 `[0.0, 1.0]` 범위로 검증하도록 강화했습니다.
  - 잘못 만든 fixture의 `NaN`, 무한대, 범위 밖 precision/recall/MRR/hit rate가 평균 또는 보고 결과로 전파되지 않습니다.
  - `hit_at_k`는 Python의 `1`/`True` 동치에 의존하지 않고 실제 boolean만 허용합니다.
- `test_volume04_retrieval_evaluation.py`에 public metric record의 비유한 값, 범위 밖 값, int boolean, 비유한 summary 거부 회귀 테스트를 추가했습니다.
- 03장에 metric record의 유한 단위 구간 계약을 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 42 passed in 0.39s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# retry 문서 score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-11 — Slice 18 완료: embedding batch 입력 계약 강화

### 추가한 결과물

- `embedding_service.py`의 `DeterministicEmbeddingModel.embed`가 단일 `str`/`bytes`를 문자별 batch로 오해하거나 빈·비-sequence batch를 조용히 성공시키지 않도록, 비어 있지 않은 문자열 sequence만 받게 했습니다.
- `test_volume04_embedding_service.py`에 단일 문자열, bytes, 빈 목록, `None`, 비문자열 항목 거부와 유효 batch의 입력 순서·출력 대응 회귀 테스트를 추가했습니다.
- 01장에 `embed_one(text)`와 `embed(texts)`의 경계 및 새 오류 해결 항목을 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 48 passed in 0.27s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# retry 문서 score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): validate embedding batch inputs`

## 다음 slice

실제 vector database DoD는 현재 cron 범위 밖입니다. 별도 허가된 local integration에서 pinned Qdrant의 schema, payload filter, ID upsert/delete, versioned reindex parity를 실행·기록합니다. 그 전에는 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않습니다.

## 2026-08-11 — Slice 19 완료: indexed point의 caller mutation 격리

### 추가한 결과물

- `test_volume04_vector_store.py`에 upsert 뒤 원본 mutable vector와 payload를 바꿔도 indexed point의 vector, metadata, score가 바뀌지 않는 회귀 테스트를 추가했습니다.
- 검색 결과 payload가 불변 mapping으로 반환되어 결과를 통해 저장된 metadata를 수정할 수 없음을 검증했습니다.
- 02장에 defensive-copy 저장 경계의 검증 범위와 caller mutation 오류 해결 항목을 보강했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 49 passed in 0.31s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# retry 문서 score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# collection_size=3; retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경을 사용해 검증을 완료했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `test(volume04): isolate indexed point inputs`.

## 2026-08-11 — Slice 20 완료: immutable reindex lifecycle report 입력 계약 강화

### 추가한 결과물

- `reindex_lifecycle.py`의 public `ReindexLifecycleReport`가 mutable list 대신 중복 없는 tuple 순위만 받고, 두 metric field가 `RetrievalMetrics`인지 검증하도록 강화했습니다.
- delete count와 collection size는 bool이 아닌 0 이상의 정수, reindexed version은 양의 정수로 제한하고 위반 시 `ReindexLifecycleError`를 반환합니다.
- `test_volume04_reindex_lifecycle.py`에 mutable rank, duplicate ID, 잘못된 metric, bool count, 0 version 거부 회귀 테스트를 추가했습니다.
- 04장에 보고서 경계와 새 오류 해결 방법을 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 50 passed in 0.20s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# retry 문서 score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# collection_size=3; retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): validate reindex lifecycle reports`.

## 2026-08-11 — Slice 21 완료: delete ID batch 입력 계약 강화

### 추가한 결과물

- `vector_store.py`의 `delete`가 빈 ID batch, 단일 문자열/bytes, 비-sequence 입력을 명시적으로 거부하도록 강화했습니다. 빈 삭제 요청을 성공한 no-op로 처리하거나 문자열을 문자 ID 목록으로 해석하지 않습니다.
- `test_volume04_vector_store.py`에 빈 list/tuple, 문자열, bytes, `None` delete 입력 거부 회귀 테스트를 추가했습니다.
- 02장 코드 설명과 오류 해결 표에 non-empty delete batch 계약과 올바른 호출 형태를 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 55 passed in 0.23s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
uv run python examples/volume04/vector_store_search.py
uv run python examples/volume04/retrieval_quality.py
uv run python examples/volume04/reindex_lifecycle.py
# 결정적 local mock 예제 네 개가 기대한 검색·품질·삭제·재색인 결과를 출력
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): validate delete id batches`

## 2026-08-11 — Slice 22 완료: upsert point batch 입력 계약 강화

### 추가한 결과물

- `vector_store.py`의 `upsert`가 빈 batch, 단일 문자열/bytes, 비-sequence 값을 point batch로 해석하지 않고 명시적으로 거부하도록 강화했습니다.
- `test_volume04_vector_store.py`에 빈 list/tuple, 문자열, bytes, `None` point batch 거부 회귀 테스트를 추가했습니다.
- 02장에 `upsert`의 non-empty `VectorPoint` sequence 계약과 오류 해결 방법을 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 60 passed in 0.35s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# query_dimensions=64; retry 문서 score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# collection_size=3; retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): validate upsert point batches`

## 2026-08-11 — Verification Tick 23 완료

### 재검증 결과

- 허용된 Volume 04 단위 테스트 5개를 함께 실행해 **60 passed in 0.28s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04` 및 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files**에서 오류 없이 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 예제는 API retry 문서를 `score=0.548`로 1위에, payload-filter 예제는 `collection_size=3`과 `retry-guide`를 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`였고 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`였습니다.
- 검증 마지막의 `git diff --check`도 통과했습니다. 기록 전 작업 트리는 clean했습니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, database 또는 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD(고정 버전 local-only Compose, schema 조회, payload filter·upsert·delete·reindex parity, cleanup/idempotency)는 cron의 허용 경로와 실행 제한 밖이어서 여전히 미검증입니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경으로 위 검증을 완료했습니다.

## 2026-08-11 — Slice 24 완료: retrieval metric batch 입력 계약 강화

### 추가한 결과물

- `retrieval_evaluation.py`의 `mean_retrieval_metrics`가 비어 있지 않은 `RetrievalMetrics` sequence만 받도록 강화했습니다.
  - 문자열·bytes가 metric sequence처럼 해석되는 것을 막고, generator 같은 일회성 iterable은 `len()` 호출 중 `TypeError`가 나기 전에 domain error로 거부합니다.
  - 유효한 list/tuple 입력의 평균 precision, recall, MRR, hit rate 계산은 유지됩니다.
- `test_volume04_retrieval_evaluation.py`에 빈 list/tuple, 문자열, bytes, `None`, one-shot generator의 거부 회귀 테스트를 추가했습니다.
- 03장에 metric batch의 materialized sequence 계약과 오류 해결 방법을 기록했습니다.

### 검증 결과

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py -q
# 66 passed in 0.30s
uv run ruff check src/ai_platform/embeddings examples/volume04 tests/unit/test_volume04_embedding_service.py tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py tests/unit/test_volume04_learning_materials.py
# All checks passed!
uv run mypy src/ai_platform/embeddings
# Success: no issues found in 5 source files
uv run python examples/volume04/embedding_similarity.py
# query_dimensions=64; retry document score=0.548, 1위
uv run python examples/volume04/vector_store_search.py
# collection_size=3; retry-guide score=0.548, topic=api
uv run python examples/volume04/retrieval_quality.py
# precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; answerable=True
uv run python examples/volume04/reindex_lifecycle.py
# deleted_count=1; reindexed_version=2; collection_size=3; top_1_recovered=True
git diff --check
# 공백 오류 없음
```

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-13 — Slice 26 완료: cosine roundoff score 범위 보장 [LATEST]

### 추가한 결과물

- `embedding_service.py`의 `cosine_similarity`가 수학적 cosine의 닫힌 범위 `[-1.0, 1.0]`를 반환하도록 보장했습니다. 동일한 L2 정규화 vector의 IEEE-754 반올림 오차 `1.0000000000000002`는 `1.0`으로 제한합니다.
- 따라서 `InMemoryVectorStore.search`의 `SearchResult.score`가 no-answer gate의 cosine score 입력 계약을 위반하지 않습니다.
- `test_volume04_embedding_service.py`에 결정적 256차원 embedding을 자기 자신과 비교해 score가 정확히 `1.0`인지 확인하는 회귀 테스트를 추가했고, 01장과 02장에 score 범위 보장 및 retrieval gate 경계를 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **70 passed in 0.60s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`.
- `git diff --check`를 통과했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): clamp cosine roundoff scores`.

## 2026-08-13 — Slice 27 완료: payload scalar subclass 계약 고정

### 추가한 결과물

- `vector_store.py`가 payload 값을 정확한 built-in JSON scalar(`str`, `int`, `float`, `bool`, `None`)로만 허용하도록 강화했습니다.
  - `IntEnum`처럼 `int`의 subclass인 값은 Python의 `isinstance` 검사에서는 통과하지만, 저장·filter 타입 계약은 불명확하므로 명시적으로 거부합니다.
  - 실제 `float`의 `NaN`/무한대 거부는 유지합니다.
- `test_volume04_vector_store.py`에 `IntEnum` metadata가 `upsert`에서 거부되는 회귀 테스트를 추가했습니다.
- 02장에 built-in scalar payload 규칙과 enum/custom scalar 변환 오류 해결을 추가했습니다.

### 검증 결과

- Volume 04 테스트 5개: **71 passed in 2.02s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `top_1_recovered=True`.
- `git diff --check`를 통과했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-13 — Slice 28 완료: retrieval metric 의미 일관성 고정

### 추가한 결과물

- `retrieval_evaluation.py`의 public `RetrievalMetrics` 생성 계약을 강화했습니다.
  - top-k에 관련 결과가 없으면 `precision_at_k=0.0`, `recall_at_k=0.0`, `hit_at_k=False`여야 합니다.
  - 관련 결과가 있으면 precision·recall은 양수이고 `hit_at_k=True`여야 합니다.
  - 따라서 수동 fixture가 수치상 범위에는 맞지만 hit 결과와 모순되는 상태로 평균 품질 보고서에 섞이는 것을 막습니다.
- `test_volume04_retrieval_evaluation.py`에 false hit, false non-hit, precision/recall positivity 불일치의 세 회귀 테스트를 추가했습니다.
- 03장 코드 설명과 문제 해결 표에 이 public metric record의 의미 계약을 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **74 passed in 0.37s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-14 — Slice 29 완료: top-k hit와 reciprocal rank 의미 일관성 고정

### 추가한 결과물

- `retrieval_evaluation.py`의 public `RetrievalMetrics` 생성 계약을 강화했습니다.
  - `hit_at_k=True`이면 첫 관련 결과가 반드시 존재하므로 `reciprocal_rank`가 `0.0`일 수 없습니다.
  - top-k 밖에서 첫 관련 결과를 찾은 `hit_at_k=False`와 양수 reciprocal rank의 기존 의미는 유지합니다.
- `test_volume04_retrieval_evaluation.py`에 top-k hit인데 `reciprocal_rank=0.0`인 수동 fixture 거부 회귀 테스트를 추가했습니다.
- 03장 코드 설명과 오류 해결 표에 reciprocal rank/hit@k 관계와 올바른 fixture 작성 방법을 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **75 passed in 0.45s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.
- `git diff --check`를 통과했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-14 — Slice 30 완료: top-k miss reciprocal-rank 상한 보장

### 추가한 결과물

- `retrieval_evaluation.py`의 public `RetrievalMetrics` 생성 계약을 강화했습니다.
  - `hit_at_k=False`인데 양수 reciprocal rank를 가진 경우, 첫 관련 결과는 top-k 밖이면서 적어도 2위여야 합니다.
  - 따라서 reciprocal rank가 `0.5`를 초과하는 수동 fixture(예: `1.0`, 즉 1위 관련 결과)가 top-k miss라는 모순된 상태로 평균 품질 보고서에 섞이지 않습니다.
- `test_volume04_retrieval_evaluation.py`에 `hit_at_k=False`와 `reciprocal_rank=1.0`의 거부 회귀 테스트를 추가했습니다.
- 03장에 top-k miss의 reciprocal-rank 상한과 오류 해결 방법을 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **76 passed in 0.42s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.
- `git diff --check`를 통과했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-14 — Slice 31 완료: reciprocal-rank 이산 순위 의미 보장

### 추가한 결과물

- `retrieval_evaluation.py`의 public `RetrievalMetrics` 생성 계약을 강화했습니다.
  - `reciprocal_rank`는 `0.0` 또는 실제 1-indexed 정수 순위의 역수여야 합니다.
  - 따라서 수치 범위에는 맞지만 실제 rank에서 나올 수 없는 `0.6` 같은 수동 fixture가 평균 MRR 보고서에 섞이지 않습니다.
  - IEEE-754 반올림 오차를 고려해 결정적인 `1 / n` 결과는 허용합니다.
- `test_volume04_retrieval_evaluation.py`에 `reciprocal_rank=0.6` 수동 metric record 거부 회귀 테스트를 추가했습니다.
- 03장에 reciprocal-rank의 이산 rank 계약과 새 오류 해결 항목을 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **77 passed in 0.33s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-14 — Slice 32 완료: large finite vector cosine overflow 방지

### 추가한 결과물

- `embedding_service.py`의 `cosine_similarity`가 각 vector를 최대 절댓값으로 먼저 scale하고 compensated sum으로 norm·score를 계산하게 했습니다.
  - `1e308`처럼 각 component는 유한하지만 squared norm 또는 dot product가 overflow하던 입력도 cosine 방향 score를 계산합니다.
  - zero vector 거부와 `[-1.0, 1.0]` score 범위 보장은 유지합니다.
- `test_volume04_embedding_service.py`에 같은 방향 및 직교하는 large finite vector의 overflow 회귀 테스트를 추가했습니다.
- 01장과 02장에 large finite component의 intermediate overflow 방지 계약을 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **78 passed in 0.42s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.
- `git diff --check`를 통과했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-14 — Slice 33 완료: large finite Euclidean distance overflow 방지

### 추가한 결과물

- `embedding_service.py`의 `euclidean_distance`가 위치별 차이를 제곱해 합산하는 대신 `math.hypot`의 내부 scaling을 사용하도록 변경했습니다.
  - `[1e308, 1e308]`와 zero vector의 거리는 수학적으로 표현 가능한 유한값이지만, 이전 `sqrt(sum(delta ** 2))` 구현은 중간 제곱에서 overflow했습니다.
  - 입력 차원·유한성 검증과 실제 결과가 표현 범위를 넘을 때의 IEEE-754 overflow 의미는 유지합니다.
- `test_volume04_embedding_service.py`에 큰 유한 component의 Euclidean distance가 유한한 `math.hypot` 기준값과 일치하는 회귀 테스트를 추가했습니다.
- 01장과 02장에 cosine과 Euclidean distance의 intermediate-overflow 방지 경계를 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **79 passed in 0.42s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.

## 2026-08-14 — Slice 34 완료: dot product cancellation residual 보존

### 추가한 결과물

- `embedding_service.py`의 `dot_product`가 일반 순차 `sum` 대신 보상 합산 `math.fsum`을 사용하도록 변경했습니다.
  - `[1e16, 1, -1e16] · [1, 1, 1]`처럼 큰 양·음 항 사이에 작은 유한 잔차가 있을 때, 순차 반올림으로 `1.0`을 `0.0`으로 잃지 않습니다.
  - public 입력 차원·유한성 검증 및 결과의 IEEE-754 범위 의미는 유지합니다.
- `test_volume04_embedding_service.py`에 위 cancellation residual의 회귀 테스트를 추가했습니다.
- 01장과 02장에 `math.fsum` 보상 합산의 수치 안정성 경계를 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **80 passed in 0.53s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.
- `git diff --check`를 통과했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): stabilize dot product summation`

## 2026-08-14 — Slice 35 완료: dot product overflow cancellation 보존

### 추가한 결과물

- `embedding_service.py`의 `dot_product`가 유한 input vector를 최대 절댓값으로 먼저 scale한 뒤 `math.fsum`으로 합산하도록 변경했습니다.
  - `[1e308, 1e308] · [1e308, -1e308]`처럼 실제 내적은 `0.0`이지만 항별 곱셈이 `+/-inf`가 되는 입력도 `math.fsum` 오류 없이 계산합니다.
  - 기존의 작은 cancellation residual 보존과 입력 차원·유한성 계약은 유지합니다.
- `test_volume04_embedding_service.py`에 large finite term cancellation의 `0.0` 회귀 테스트를 추가했습니다.
- 01장에 scale-first dot-product 경계와 대형 상쇄 예시를 기록했습니다.

### 검증 결과

- Volume 04 테스트 5개: **81 passed in 0.50s**.
- `ruff check`: **All checks passed!**; `mypy src/ai_platform/embeddings`: **5 source files, no issues**.
- 네 개의 결정적 local mock 예제를 실행했습니다: embedding/search top score `0.548`; retrieval `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`; lifecycle `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`.
- `git diff --check`를 통과했습니다.

### 범위 및 완료 상태

- 이 slice는 결정적 local mock만 사용했으며 외부 API, 모델 다운로드, Docker, Qdrant, database, 비밀값을 사용하지 않았습니다.
- 실제 Qdrant service DoD는 허용 범위와 실행 금지 조건 밖이므로 여전히 미검증입니다. 따라서 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않았습니다.
- Commit: `fix(volume04): stabilize overflow cancellation`.

## 2026-08-14 — Verification Tick 36 완료

### 재검증 결과

- Volume 04 전용 단위 테스트 5개를 함께 실행해 **81 passed in 0.26s**를 확인했습니다.
- `ruff check src/ai_platform/embeddings examples/volume04` 및 Volume 04 테스트 대상은 통과했고, `mypy src/ai_platform/embeddings`도 **5 source files, no issues**로 통과했습니다.
- 네 개의 결정적 local mock 예제를 모두 실행했습니다. embedding 검색은 API retry 문서를 `score=0.548`로 1위에 반환했고, payload-filter 검색은 `collection_size=3`, `retry-guide`, `topic=api`를 반환했습니다. 품질 예제는 `precision_at_1=1.0`, `recall_at_1=1.0`, `mrr=1.0`, `answerable=True`였으며 lifecycle 예제는 `deleted_count=1`, `reindexed_version=2`, `collection_size=3`, `top_1_recovered=True`였습니다.
- 기록 전 `git status --short --branch`는 `volume-04` branch의 clean 작업 트리를 보였고, `git diff --check`도 통과했습니다.

### 범위 및 완료 상태

- 이번 tick은 외부 API, 모델 다운로드, Docker, Qdrant, database 또는 비밀값을 사용하지 않은 결정적 local mock 재검증입니다.
- 실제 Qdrant service DoD(고정 버전 local-only Compose, schema 조회, payload filter·upsert·delete·reindex parity, cleanup/idempotency)는 cron의 허용 경로와 실행 제한 밖이어서 여전히 미검증입니다.
- 따라서 `VOLUME04_COMPLETE=true`를 추가하지 않았고 cron pause도 실행하지 않았습니다.

`uv`는 PATH에 없어서 `/c/Users/HODI/.local/bin/uv`로 실행했습니다. Hermes 가상환경과 프로젝트 `.venv`가 다르다는 경고가 있었지만, uv가 프로젝트 환경으로 위 검증을 완료했습니다.
