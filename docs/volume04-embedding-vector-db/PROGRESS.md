# Volume 04 작업 진행 기록

## 현재 상태

- 완료 표식: `VOLUME04_COMPLETE` 미설정
- 현재 slice: 02 — 결정적 로컬 collection, payload, upsert와 검색
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

## 남은 PRD 완료 조건

- [ ] Volume 문서의 나머지 장을 작성한다.
- [ ] Qdrant Docker Compose 실행 및 collection 생성을 문서화·검증한다.
- [x] 결정적 local mock에서 vector와 metadata/payload 저장 및 query 검색을 구현·검증했다.
- [x] 결정적 local mock에서 검색 결과 해석을 실습으로 검증했다.
- [x] 결정적 local mock에서 데이터 삭제와 ID 기반 재색인(upsert)을 구현·검증했다.
- [ ] Qdrant용 `docker-compose.yml`, `scripts/index_documents.py`를 추가하고 검증한다. (`vector_store.py`는 완료)
- [ ] 미니 프로젝트와 권 단위 완료 체크리스트를 검증한다.
- [ ] 다음 권(RAG) 인계 결과물을 정리한다.

## 다음 slice

Qdrant를 실제로 Docker에서 실행하는 별도 로컬 integration slice를 작성합니다. 이 slice도 외부 API·비밀값·배포 없이 수행하고, 현재 검증된 `VectorPoint` 및 payload 계약을 연결에 사용합니다.
