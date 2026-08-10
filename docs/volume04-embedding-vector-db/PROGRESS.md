# Volume 04 작업 진행 기록

## 현재 상태

- 완료 표식: `VOLUME04_COMPLETE` 미설정
- 현재 slice: 04 — 결정적 local mock 삭제·재색인 lifecycle 미니 프로젝트
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

## 다음 slice

실제 vector database DoD는 현재 cron 범위 밖입니다. 별도 허가된 local integration에서 pinned Qdrant의 schema, payload filter, ID upsert/delete, versioned reindex parity를 실행·기록합니다. 그 전에는 `VOLUME04_COMPLETE=true`를 추가하거나 cron을 pause하지 않습니다.
