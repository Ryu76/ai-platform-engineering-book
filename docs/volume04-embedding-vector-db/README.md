# Volume 04. Embedding & Vector Database

텍스트를 고정 길이 벡터로 바꾸고, 벡터 간 거리를 이용해 관련 문서를 찾는 방법을 다룹니다. 이 권은 다음 권의 RAG 검색 파이프라인에 사용할 임베딩과 저장소 경계를 만듭니다.

> [!WARNING]
> 이 권의 첫 실습은 네트워크·API 키·외부 모델 다운로드를 사용하지 않는 결정적 로컬 mock 모델입니다. 학습과 테스트를 재현하기 위한 도구이며, 실제 의미 검색 품질을 보장하는 운영용 임베딩 모델은 아닙니다.

## 학습 목표

- 벡터, 차원, dense vector와 sparse vector의 차이를 설명한다.
- cosine similarity, dot product, Euclidean distance를 직접 비교한다.
- 문서 임베딩과 질의 임베딩이 같은 벡터 공간을 사용해야 하는 이유를 설명한다.
- collection, payload, metadata, index의 역할을 구분한다.
- Qdrant에 저장·검색·삭제·재색인하는 다음 실습을 준비한다.

## 현재 작성된 장

| 장 | 주제 | 상태 |
|---|---|---|
| [01](01-learning-objectives.md) | 벡터와 결정적 로컬 임베딩 시작하기 | 완료 |
| [02](02-local-collection-payload-search.md) | 결정적 로컬 collection·payload·검색 | 완료 |
| [03](03-retrieval-quality-no-answer.md) | 검색 품질 측정과 no-answer gate | 완료 |
| [04](04-reindex-lifecycle-mini-project.md) | 결정적 local mock 삭제·재색인 미니 프로젝트 | 완료 |
| 05 | Qdrant collection·payload 저장과 검색 | 예정 |
| 06 | Qdrant 운영 이행과 lifecycle 검증 | 예정 |

진행 기록과 남은 완료 조건은 [PROGRESS.md](PROGRESS.md)에서 확인합니다.

## 빠른 시작

```bash
# 실행 위치: 저장소 루트의 Windows PowerShell, Git Bash 또는 WSL 터미널
uv run python examples/volume04/embedding_similarity.py
uv run python examples/volume04/vector_store_search.py
uv run python examples/volume04/retrieval_quality.py
uv run python examples/volume04/reindex_lifecycle.py
uv run pytest tests/unit/test_volume04_embedding_service.py -q
uv run pytest tests/unit/test_volume04_vector_store.py -q
uv run pytest tests/unit/test_volume04_retrieval_evaluation.py -q
uv run pytest tests/unit/test_volume04_reindex_lifecycle.py -q
```

첫 명령은 로컬 mock 임베딩으로 세 문서를 점수순으로 출력합니다. 두 번째 명령은 같은 벡터를 collection과 payload에 저장하고 metadata filter 검색을 수행합니다. 세 번째 명령은 안정적인 point ID로 top-k 검색 품질과 보수적인 score gate를 출력합니다. 네 번째 명령은 오래된 point를 삭제하고 같은 ID의 version 2 vector를 재색인합니다. 테스트 명령은 외부 서비스 없이 구현 계약을 검증합니다.

## 결과물 로드맵

- `src/ai_platform/embeddings/embedding_service.py`: 결정적 교육용 임베딩과 벡터 수학
- `src/ai_platform/embeddings/vector_store.py`: 결정적 in-memory collection, payload, upsert, 검색, 삭제 경계
- `src/ai_platform/embeddings/retrieval_evaluation.py`: stable ID 기반 top-k 검색 품질 및 no-answer score gate
- `src/ai_platform/embeddings/reindex_lifecycle.py`: 삭제, stable ID 재색인, version metadata를 검증하는 local lifecycle
- `examples/volume04/`: 네트워크 없는 실행 예제
- `tests/unit/test_volume04_*.py`: Volume 04 전용 단위 테스트
- `docker-compose.yml`, `scripts/index_documents.py`: Qdrant 실습 slice에서 추가 예정

## 다음 권으로의 인계

Volume 05 RAG는 이 권에서 검증한 `EmbeddingModel`, `VectorPoint`, 검색 결과의 metadata와 삭제·재색인 lifecycle 경계를 이용해 최신 chunk를 색인하고 검색합니다. 운영용 모델 또는 Qdrant 연결은 명시적으로 설정한 뒤에만 추가합니다.
