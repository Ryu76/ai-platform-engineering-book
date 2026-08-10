# 06. Volume 04 완료 기준과 Volume 05 RAG 인계

## 1. 학습 목표

이 장을 마치면 Volume 04에서 이미 **결정적으로 검증한 local mock 계약**과 아직 실행하지 않은 실제 database 통합 항목을 구분할 수 있습니다. 또한 Volume 05 RAG가 어떤 입력·출력·안전 경계를 그대로 이어받아야 하는지 확인할 수 있습니다.

## 2. 이 장의 범위

이 문서는 권 단위의 완료 체크리스트와 다음 권 인계 manifest입니다. 새 vector database client, Docker, 외부 embedding model, API, credential, 실제 corpus를 실행하거나 설정하지 않습니다. 모든 완료 증거는 이 권의 `src/ai_platform/embeddings/`, `examples/volume04/`, `tests/unit/test_volume04_*.py`에 있는 결정적 local mock과 문서 구조 검사에 한정됩니다.

> [!WARNING]
> `VOLUME04_COMPLETE=true`는 아래의 **모든** DoD가 테스트 또는 별도 허가된 local integration 증거로 충족된 뒤에만 기록합니다. 문서에 실행 계획이 있다는 사실은 Qdrant service, Docker Compose, 실제 persistence, database filter parity가 검증되었다는 증거가 아닙니다.

## 3. 검증 가능한 결과물 지도

| 경계 | 결과물 | 현재 검증 방식 |
|---|---|---|
| 임베딩 | `embedding_service.py` | 같은 텍스트의 재현성, L2 정규화, vector 수학, 입력 오류 |
| vector store | `vector_store.py` | dimension, immutable point/payload, atomic upsert, cosine search, filter, delete |
| 품질 평가 | `retrieval_evaluation.py` | stable ID의 precision/recall/MRR/hit@k 및 no-answer gate |
| lifecycle | `reindex_lifecycle.py` | stale ID delete, same ID version 2 upsert, top-1 회복 |
| 실행 예제 | `examples/volume04/*.py` | 네트워크 없는 deterministic stdout 실행 |
| 학습 자료 | 01–06장과 `PROGRESS.md` | 장 번호·링크·완료/미완료 상태의 구조 검사 |

## 4. 실행 기준선

저장소 루트에서 다음 명령을 실행합니다.

```bash
uv run pytest tests/unit/test_volume04_embedding_service.py \
  tests/unit/test_volume04_vector_store.py \
  tests/unit/test_volume04_retrieval_evaluation.py \
  tests/unit/test_volume04_reindex_lifecycle.py \
  tests/unit/test_volume04_learning_materials.py -q
uv run ruff check src/ai_platform/embeddings examples/volume04 \
  tests/unit/test_volume04_embedding_service.py \
  tests/unit/test_volume04_vector_store.py \
  tests/unit/test_volume04_retrieval_evaluation.py \
  tests/unit/test_volume04_reindex_lifecycle.py \
  tests/unit/test_volume04_learning_materials.py
uv run mypy src/ai_platform/embeddings
uv run python examples/volume04/embedding_similarity.py
uv run python examples/volume04/vector_store_search.py
uv run python examples/volume04/retrieval_quality.py
uv run python examples/volume04/reindex_lifecycle.py
```

이 명령들은 local process 안의 고정 SHA-256 token projection과 in-memory store만 사용합니다. 예제와 테스트가 성공해도 production 의미 품질, durability, concurrency, ANN recall을 주장하지 않습니다.

## 5. 결정적 local mock DoD

다음 항목은 이 권에서 테스트로 확인합니다.

- [x] 문서와 질의가 같은 고정-dimension vector 공간을 사용한다.
- [x] cosine similarity, dot product, Euclidean distance와 zero/dimension 오류가 명시적이다.
- [x] collection은 고정 dimension을 갖고, vector와 scalar payload를 immutable snapshot으로 저장한다.
- [x] upsert는 같은 stable ID를 교체하고 invalid batch가 기존 collection을 바꾸지 않는다.
- [x] scalar equality metadata filter가 후보에 적용되고 동점은 stable ID로 정렬된다.
- [x] delete는 중복 요청을 한 번만 세고 stale point를 검색 결과에서 제거한다.
- [x] stable ID ranking으로 top-k 품질을 측정하고 finite cosine score의 no-answer gate를 적용한다.
- [x] 삭제 뒤 같은 stable ID의 version 2 vector/payload를 재색인하고 품질 회복을 확인한다.

## 6. 실제 vector database DoD 상태

다음은 설계·이행 계약은 문서화했지만 이 cron의 허용 경로와 외부 service 금지 조건 때문에 실행하지 않은 항목입니다.

- [ ] pinned Qdrant image와 client version을 사용한 local-only Docker Compose를 생성·기동한다.
- [ ] 실제 Qdrant collection의 name, dimension, cosine metric을 schema 조회로 확인한다.
- [ ] 고정 fixture의 payload filter, ID overwrite, delete, versioned reindex를 실제 service에서 확인한다.
- [ ] local mock과 실제 backend의 top-k/filter/lifecycle parity 및 허용 가능한 score·tie 차이를 기록한다.
- [ ] service 종료, local volume cleanup, 재실행 idempotency를 검증한다.

이 항목은 [05. 이행 계약](05-vector-db-migration-contracts.md)의 실행 순서를 따른 별도 허가된 local integration slice에서만 체크합니다.

## 7. 완료 표식 규칙

`docs/volume04-embedding-vector-db/PROGRESS.md`의 `VOLUME04_COMPLETE=true`는 다음 조건을 모두 만족할 때만 추가합니다.

1. 5절의 local mock DoD가 해당 Volume 04 단위 테스트로 통과한다.
2. 6절의 실제 database DoD가 pinned, local-only integration 증거로 모두 통과한다.
3. 예제, lint, type check가 해당 revision에서 통과한다.
4. `PROGRESS.md`에 명령, 결과, 제한 사항, commit을 기록한다.
5. 완료 표식을 추가한 동일 작업에서 cron 목록으로 이 job을 pause한다.

현재는 6절이 미완료이므로 완료 표식을 추가하거나 cron을 pause하지 않습니다.

## 8. Volume 05가 받는 public contract

Volume 05 RAG는 database product 이름이 아니라 다음 Python 경계를 소비합니다.

```text
EmbeddingModel.embed(texts) -> list[list[float]]
VectorPoint(id, vector, payload)
InMemoryVectorStore.create_collection(name, vector_size)
InMemoryVectorStore.upsert(collection_name, points)
InMemoryVectorStore.search(collection_name, query_vector, limit, metadata_filter)
InMemoryVectorStore.delete(collection_name, point_ids)
SearchResult(id, score, payload)
```

RAG 구현은 production adapter가 생기기 전까지 이 port의 local mock을 test double로 사용합니다. production adapter는 같은 stable ID, vector dimension, payload/filter, delete/upsert 의미를 보존해야 합니다.

## 9. Chunk와 stable ID 인계

RAG chunker는 source identity와 ordinal에서 stable ID를 결정적으로 만들어야 합니다. 권장 형식은 예를 들어 `source:<source-id>:chunk:<zero-padded-ordinal>`입니다. chunk text가 바뀌더라도 identity가 같은 논리 chunk이면 같은 ID를 upsert하고 `content_hash`, `version`, `embedding_model_version`을 payload에 갱신합니다.

새 chunk boundary 전략으로 ordinal의 의미가 달라지면 old/new generation을 혼합하지 않습니다. 새 collection generation을 만들고, 최신 manifest와 judgement fixture로 검증한 뒤 read target을 전환합니다.

## 10. Payload와 authorization 인계

Volume 05는 최소한 다음 metadata를 명시적으로 소유합니다.

| Field | 타입 | RAG 사용 규칙 |
|---|---|---|
| `tenant_id` | string | 검색 요청 전에 server-side filter에 포함 |
| `state` | string | `published` 등 허용 상태만 filter |
| `version` | integer | 재색인 freshness와 fixture 검증 |
| `source_uri` | string | citation source; credential이나 signed URL을 저장하지 않음 |
| `content_hash` | string | stale content 감지; 원문 자체를 log하지 않음 |
| `embedding_model_version` | string | vector space generation 추적 |

ACL이나 tenant 조건을 RAG가 결과를 받은 뒤 제거하는 방식은 허용하지 않습니다. backend adapter query의 filter로 후보를 먼저 제한하고, 해당 동작을 fixture로 검증합니다.

## 11. Retrieval와 answer policy 인계

`SearchResult.score`는 backend-independent truth score가 아닙니다. Volume 05는 다음을 분리합니다.

1. adapter가 metric 방향을 일관된 application score 또는 rank로 변환한다.
2. evaluation fixture에서 relevant ID의 top-k hit, recall, MRR를 계산한다.
3. no-answer threshold는 production embedding model과 backend score distribution에서 별도로 결정한다.
4. 검색 score가 충분해도 LLM의 사실성이나 citation 정확성은 별도 RAG 평가로 검증한다.

local mock의 `meets_score_threshold`는 score gate의 제어 흐름을 가르치는 도구일 뿐, production threshold의 기본값이 아닙니다.

## 12. Lifecycle와 observability 인계

RAG indexing 작업은 `run_id`, target collection generation, input stable ID, content hash, model version, 성공/실패, retry count를 최소 manifest에 기록해야 합니다. 민감 원문, 사용자 query, access token, database credential은 log나 vector payload에 넣지 않습니다.

재색인 중에는 새 generation에서 count, filter, stale ID 제거, fixed-query quality를 확인합니다. 읽기 전환 전 rollback target을 보존하고, 실제 database의 backup/restore 및 alias/route 전환은 선택한 backend의 운영 절차로 연습·검증합니다.

## 13. 후속 작업자 checklist

- [ ] pinned local Qdrant integration을 별도 허가된 경로와 환경에서 구현한다.
- [ ] 05장의 fixture로 schema/filter/upsert/delete/reindex parity를 실행한다.
- [ ] backend의 metric direction과 score distribution으로 no-answer threshold를 재평가한다.
- [ ] Volume 05 chunk ID, payload schema, authorization filter를 이 장의 contract와 연결하는 테스트를 만든다.
- [ ] 모든 실제 database DoD와 권 단위 검증이 통과한 뒤에만 `VOLUME04_COMPLETE=true`를 기록하고 job을 pause한다.

## 14. 핵심 정리

Volume 04는 외부 service 없이 embedding, vector storage, filtered retrieval, retrieval evaluation, stale deletion, versioned reindex를 결정적으로 검증하는 학습·contract-test 기반을 제공합니다. 실제 Qdrant 통합은 명시적으로 미완료이며, 이를 통과하기 전에는 권 완료 표식이나 cron pause를 수행하지 않습니다. Volume 05 RAG는 stable ID, fixed vector space, server-side authorization filter, backend별 score 재평가, generation-aware lifecycle이라는 경계를 이어받아야 합니다.
