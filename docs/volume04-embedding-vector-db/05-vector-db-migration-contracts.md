# 05. Local Mock에서 Vector Database로 이행하기

## 1. 학습 목표

이 장을 마치면 Volume 04의 결정적 local mock이 보장하는 ID·vector·payload·filter·삭제·재색인 계약을 실제 vector database 이행 전에 명확히 기록할 수 있습니다. 또한 Qdrant, pgvector, Chroma의 역할 차이를 설명하고, 같은 검색 기능이라도 거리 지표, dimension, filter, ID, lifecycle 계약을 검증하지 않으면 안전하게 교체할 수 없다는 점을 이해합니다.

## 2. 왜 필요한가

`InMemoryVectorStore`는 네트워크 없이 애플리케이션 경계를 검증하기 위한 교육용 구현입니다. 반면 실제 database는 영속성, 동시성, index, 인증, filter 표현식, 장애 복구, 운영 관측을 제공합니다. local mock의 `search`가 통과했다고 해서 Qdrant, PostgreSQL, Chroma에서 동일한 결과나 운영 특성이 자동으로 보장되지는 않습니다.

따라서 database를 고르기 전에 어떤 구현에서도 유지해야 하는 계약을 먼저 고정합니다. 이 장은 서버를 시작하거나 client package를 설치하지 않습니다. 다음 통합 slice가 실행할 실제 Qdrant Docker 검증의 입력·기대 결과·중단 기준을 결정적으로 준비하는 문서 slice입니다.

> [!WARNING]
> 이 장의 JSON은 API 호출이 아니라 **이행 계약을 설명하는 예시**입니다. Qdrant, PostgreSQL, Chroma 서버, Docker, 네트워크, API key, 외부 embedding model을 실행하거나 사용하지 않습니다. 실제 client의 정확한 request field와 지원 버전은 통합을 시작하는 시점에 해당 DB의 공식 문서와 pinned client version으로 다시 확인해야 합니다.

## 3. 핵심 개념

- **port / adapter**: 애플리케이션이 의존하는 저장·검색 인터페이스와 특정 DB client를 연결하는 얇은 경계입니다.
- **collection 또는 table**: 같은 dimension과 distance metric을 공유하는 vector 집합입니다. Qdrant와 Chroma는 collection이라는 이름을 주로 쓰고, pgvector는 PostgreSQL table과 index를 사용합니다.
- **metric contract**: cosine, dot product, Euclidean 거리 중 무엇을 쓰는지와 score 해석을 함께 고정하는 계약입니다.
- **payload contract**: point ID와 vector 옆에 저장하는 `topic`, `version`, `state`, `tenant_id`, `source_uri` 같은 metadata의 타입·필수 여부·filter 규칙입니다.
- **filter-before-use**: tenant와 ACL 조건으로 후보를 제한한 뒤에만 결과를 해석하거나 반환하는 원칙입니다.
- **stable ID**: 문서 또는 chunk의 정체성을 나타내는 변하지 않는 ID입니다. 재색인은 같은 ID의 vector와 payload를 교체합니다.
- **migration parity**: local mock과 실제 adapter가 같은 고정 fixture에 대해 ID, 허용 후보, 삭제·upsert 상태 전이를 만족하는지 확인하는 테스트입니다.

## 4. 이행 구조

```text
                     ┌─────────────────────────────────────────┐
문서 + stable ID ───>│ embedding model / dimension contract    │
                     └─────────────────────────────────────────┘
                                      │
                                      ▼
        ┌──────────────── application vector-store port ────────────────┐
        │ create · upsert · filtered search · delete · reindex · observe │
        └───────────────┬──────────────────┬──────────────────┬──────────┘
                        │                  │                  │
                        ▼                  ▼                  ▼
                 local mock            Qdrant            pgvector / Chroma
                 deterministic       collection          table / collection
                        │                  │                  │
                        └────── fixture parity + integration evidence ───┘
```

모델이 바뀌면 vector space도 바뀔 수 있습니다. 그러므로 기존 collection에 새 dimension 또는 새 model의 vector를 섞지 않습니다. 새 collection 또는 새 table에 전체 재색인하고, 품질·filter·삭제 검증이 끝난 뒤에만 읽기 대상을 전환합니다.

## 5. 환경과 범위

이 장의 현재 slice는 문서와 기존 local mock 테스트만 사용합니다.

- local contract 구현: `src/ai_platform/embeddings/vector_store.py`
- 검색 품질 계약: `src/ai_platform/embeddings/retrieval_evaluation.py`
- 삭제·재색인 계약: `src/ai_platform/embeddings/reindex_lifecycle.py`
- 검증 fixture: `tests/unit/test_volume04_vector_store.py`, `tests/unit/test_volume04_retrieval_evaluation.py`, `tests/unit/test_volume04_reindex_lifecycle.py`

```bash
# 저장소 루트에서 기존 결정적 계약을 확인한다.
uv run pytest tests/unit/test_volume04_vector_store.py tests/unit/test_volume04_retrieval_evaluation.py tests/unit/test_volume04_reindex_lifecycle.py -q
```

이 명령은 외부 service를 연결하지 않습니다. Qdrant Docker Compose, database 생성, client package 추가, 환경 변수 설정은 다음의 명시적 local integration slice까지 범위 밖입니다.

## 6. 이행 전 contract checklist

실제 database adapter를 작성하기 전에 아래 항목을 manifest 또는 설정으로 명시합니다.

1. **collection name**: 예를 들어 `platform_docs_v2`처럼 목적과 schema generation을 구분합니다.
2. **embedding identity**: model 이름 또는 버전, dimension, normalization 정책, document/query prefix를 기록합니다.
3. **metric**: local mock이 cosine을 쓰므로 실제 collection도 cosine으로 만들거나, metric 변경이 의도된 경우 score와 threshold를 다시 평가합니다.
4. **point ID**: source document ID와 chunk ordinal에서 결정적으로 만들고, 재실행해도 같은 원문은 같은 ID가 되게 합니다.
5. **payload schema**: `tenant_id`, `state`, `version`, `source_uri`, `content_hash`, `embedding_model_version`의 타입, 필수 여부, 민감도, filter 가능 여부를 정의합니다.
6. **authorization filter**: 요청자의 tenant와 ACL을 서버측 filter로 강제할 수 있는지 확인합니다. client가 결과를 받은 뒤 제거하는 방식은 허용하지 않습니다.
7. **write lifecycle**: batch upsert의 재시도 키, delete 대상, 실패 기록, idempotency, collection 교체 또는 alias 전환 기준을 적습니다.
8. **evaluation fixture**: 고정 문서·질의·정답 ID·예상 filter 결과를 보관하고 adapter와 local mock 양쪽에서 실행합니다.

다음은 payload 값의 형태를 보여 주는 예시입니다. 비밀값, 원문 전체, 사용자 access token을 payload에 넣지 않습니다.

```json
{
  "id": "handbook:retry:0003",
  "payload": {
    "tenant_id": "training",
    "state": "published",
    "version": 2,
    "source_uri": "docs://handbook/retry",
    "content_hash": "<content-hash>",
    "embedding_model_version": "<pinned-model-version>"
  }
}
```

## 7. Qdrant, pgvector, Chroma의 역할

| 선택지 | 주된 형태 | 적합한 출발점 | 이행 때 반드시 확인할 계약 |
|---|---|---|---|
| Qdrant | vector collection과 payload filter 중심의 전용 database | vector search와 payload 조건을 독립 service로 운영할 때 | collection vector size·distance, point ID, payload index, filter semantics, upsert/delete wait·retry 정책 |
| pgvector | PostgreSQL column과 SQL query/index | 이미 PostgreSQL 운영·transaction·관계형 metadata 조회가 중심일 때 | vector type dimension, cosine operator와 sort 방향, SQL `WHERE` ACL/tenant 조건, ANN index 및 transaction 경계 |
| Chroma | application-friendly collection API | 작은 local prototype 또는 제품의 지원 범위에 맞는 실험을 할 때 | embedding function ownership, ID overwrite semantics, metadata filter 표현, persistence path와 deployment mode |

이 표는 제품의 우열을 정하지 않습니다. 선택은 corpus 규모, filter 복잡성, 트랜잭션 요구, 운영 역량, backup/restore, latency와 비용 목표에 맞춰야 합니다. 어떤 선택이든 application은 `VectorPoint`의 stable ID와 payload schema를 소유하고, database별 score를 절대 품질값으로 취급하지 않아야 합니다.

## 8. Local Mock 계약을 실제 DB에 대응하기

| local mock 계약 | 실제 DB adapter에서 보존할 동작 | 통합 검증 증거 |
|---|---|---|
| `create_collection(name, vector_size=256)` | 명시한 name, vector size, cosine metric으로 collection/table 생성 | schema 조회로 name·dimension·metric 확인 |
| `upsert(points)` | 같은 ID는 새 vector와 payload로 교체; batch 실패 처리를 관측 가능하게 기록 | 같은 ID를 두 번 기록한 뒤 최신 version 하나만 조회 |
| `search(query, limit, metadata_filter)` | 요청 tenant/state 등 filter를 database query에 포함하고 상위 limit를 반환 | 허용 point만 반환되고 고정 fixture의 정답 ID가 top-k에 포함 |
| deterministic tie ordering | 동점 순서는 DB가 보장하지 않을 수 있으므로 application에서 stable secondary sort 또는 허용 규칙을 명시 | 동점 fixture에서 ID 순서 보장 여부 또는 unordered assertion 기록 |
| `delete(ids)` | stale ID가 후속 검색과 direct lookup에서 사라짐 | 삭제 수/성공 응답과 검색 부재를 함께 확인 |
| versioned reindex | same stable ID에 version 2·새 content hash·새 vector를 기록 | `version=2` filter와 top-1 품질 회복 확인 |

local mock의 scalar equality filter는 의도적으로 작습니다. 운영 DB의 range, nested object, full-text, geo filter는 local mock에 없는 기능입니다. 그런 기능을 adapter에 도입하면 DB별 query를 직접 테스트하고, local mock이 기능을 흉내 낸다고 주장하지 않습니다.

## 9. Score와 정렬의 함정

cosine similarity는 일반적으로 클수록 가깝지만, database와 library는 score를 유사도 또는 거리를 서로 다른 방향과 범위로 노출할 수 있습니다. pgvector의 cosine distance처럼 작은 값이 더 가까운 operator를 사용한다면, SQL 정렬 방향과 application의 `score >= threshold` gate를 그대로 복사하면 안 됩니다.

이행 테스트는 rounded decimal score가 아니라 다음을 우선 검증합니다.

1. 올바른 dimension과 metric의 collection/table이 만들어진다.
2. tenant·ACL·state filter 밖의 ID는 절대 반환되지 않는다.
3. 관련 fixture ID가 정의한 top-k 안에 있다.
4. stable ID upsert 뒤 최신 payload가 반환된다.
5. delete 뒤 stale ID가 반환되지 않는다.
6. 새 backend의 score distribution으로 no-answer threshold를 별도 평가한다.

동점 순서도 backend 차이입니다. local mock은 재현성을 위해 ID 오름차순 tie-breaker를 사용하지만, 실제 ANN index는 동일 score나 근접 score에서 다른 순서를 낼 수 있습니다. 제품 요구가 strict order라면 database 보장 범위와 secondary ordering의 성능 비용을 명시하고 테스트합니다.

## 10. 실제 Qdrant 통합 slice의 실행 순서

현재 cron 범위에서는 아래 작업을 실행하지 않습니다. 별도로 허가된 local integration에서만 Docker와 Qdrant를 사용합니다.

1. pinned Qdrant image와 client version을 문서화하고, 로컬 전용 endpoint·volume·health check를 포함한 Compose 설정을 검토합니다.
2. secret 없는 local configuration으로 service readiness를 확인합니다. host port 충돌이 있으면 다른 local port를 사용하고 공개 endpoint를 만들지 않습니다.
3. manifest에 있는 dimension과 cosine metric으로 새 collection을 만듭니다.
4. local mock과 같은 고정 fixture를 upsert하고, payload field 중 filter에 사용할 field의 index/지원 조건을 확인합니다.
5. tenant/state/version filter가 포함된 search, ID replacement, delete, versioned reindex를 실행합니다.
6. stable ID와 top-k judgment로 parity를 평가하되, floating score 및 ANN tie 순서의 허용 차이를 기록합니다.
7. service 종료와 local volume 정리 방법을 문서화합니다. 실제 corpus, live API, API key, production credential은 사용하지 않습니다.

실제 요청을 작성할 때는 collection create, point upsert, filter search, delete request마다 client pinned version의 공식 API를 사용합니다. 이 문서의 예시 객체를 복사해 검증하지 않은 API call로 사용하지 않습니다.

## 11. 운영 이행과 lifecycle

새 embedding model이나 dimension으로 전환할 때 in-place 혼합은 금지합니다. 새 generation(`platform_docs_v3` 등)에 전체 fixture와 corpus를 색인하고, payload에 model/version과 content hash를 기록합니다. 품질, filter, count, stale ID 제거, rollback 경로를 검증한 뒤에만 application의 read target을 전환합니다.

대량 삭제와 재색인은 재시도 가능해야 합니다. 작업 manifest에는 실행 ID, 입력 문서 ID, content hash, target generation, 성공/실패 상태, 재시도 횟수를 최소한으로 남깁니다. 원문, 사용자 질의, credential, 민감 payload를 작업 로그에 출력하지 않습니다. backup, restore, alias/route 전환, retention은 선택한 database의 운영 문서와 실제 복구 연습으로 검증합니다.

## 12. 과제

- **기본**: 현재 `VectorPoint`의 `topic`, `version`, `state`를 포함한 payload schema 표를 만들고 각 값의 type과 required 여부를 표시합니다.
- **응용**: 두 tenant의 동일한 topic 문서를 fixture로 설계하고, tenant filter가 누락되었을 때 어떤 데이터 노출이 생기는지 테스트 시나리오를 작성합니다.
- **심화**: cosine score threshold를 새 backend로 그대로 복사하지 않는 이유를 설명하고, positive·negative 질의와 no-answer 질의로 threshold 재평가 계획을 작성합니다.

## 13. 완료 체크리스트

- [x] local mock이 실제 database의 대체품이 아니라 contract test 경계임을 구분했다.
- [x] collection/table name, dimension, metric, stable ID, payload schema를 이행 전 고정했다.
- [x] Qdrant, pgvector, Chroma의 주된 운영 형태와 검증 포인트를 비교했다.
- [x] tenant·ACL filter를 결과 사용 전에 database query에 포함해야 함을 확인했다.
- [x] upsert, delete, versioned reindex, top-k fixture의 parity 기준을 정의했다.
- [x] score direction, threshold 재평가, ANN tie ordering의 차이를 기록했다.
- [x] 현재 slice가 Docker, live service, API key, 외부 model 없이 기존 결정적 테스트만 사용함을 확인했다.
- [ ] 별도 허가된 local integration에서 pinned Qdrant로 schema·filter·lifecycle parity를 실행한다.

## 14. 핵심 정리

local mock은 database를 흉내 내는 목적이 아니라, application이 요구하는 ID·vector·payload·filter·lifecycle 계약을 빠르고 결정적으로 검증하는 목적입니다. 실제 backend를 선택할 때는 제품 이름보다 dimension과 metric, authorization filter, stable ID upsert, stale point delete, 평가 fixture, 장애 복구가 보존되는지를 먼저 확인합니다. 이 기준을 갖추면 다음 Qdrant 통합 slice와 Volume 05 RAG가 database 구현 세부 사항에 덜 묶입니다.
