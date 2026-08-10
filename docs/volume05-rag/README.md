# Volume 05. RAG

## 목표

문서를 로드·정제·청크·인덱싱하고 검색 근거·출처·No-answer 처리를 갖춘 RAG API를 구현합니다.
첫 번째 실습 슬라이스는 네트워크, API 키, 벡터 DB 없이도 재현 가능한 **로컬 검색 → Mock 생성 → 인용** 경계입니다.

## 현재 실습: 로컬·인용 가능 RAG

`src/ai_platform/rag/`의 로컬 구성 요소는 다음 계약을 제공합니다.

1. `LocalMarkdownLoader`는 허용된 로컬 루트 안의 UTF-8 `.md`/`.markdown` 파일만 읽습니다. 경로 탈출·심볼릭 링크 탈출·빈 파일·NUL·다른 인코딩은 거부하고, BOM·줄 끝·수평 공백·반복 빈 줄을 결정론적으로 정제합니다. 첫 Markdown 제목 또는 파일명으로 제목을 만들고 URI 안전한 로컬 출처를 기록합니다.
2. `LocalPdfLoader`는 명시한 로컬 `.pdf`만 읽고, 호출자가 주입한 `PdfTextExtractor`의 페이지별 텍스트를 다시 검증합니다. 파일 헤더·경로·파일/페이지 크기·페이지 수·NUL·빈 페이지·반환 타입을 제한하며, 각 페이지를 독립 `SourceDocument`와 `#page=N` 출처 URI로 만듭니다. 이 모듈은 PDF 파서 패키지·네트워크 클라이언트를 직접 만들지 않습니다.
3. `load_many()`는 디렉터리를 자동 탐색하지 않고 호출자가 명시한 Markdown 경로만 읽습니다. 빈 배치와 동일 문서로 해석되는 중복 경로를 거부하고, 결과를 문서 ID 순으로 정렬해 재현 가능한 다중 문서 색인을 만듭니다.
4. `SourceDocument`는 문서 ID, 제목, 로컬 출처 URI, 정제 원문을 함께 보관합니다. 중복 ID와 빈 값은 거부합니다.
5. `LocalRagIndex`는 원문 문자 범위를 보존하며 공백 경계 우선 청킹을 수행합니다. 각 `DocumentChunk`에는 재현 가능한 `chunk_id`와 시작/끝 오프셋이 있습니다.
6. `search()`는 로컬 어휘 점수로 근거를 정렬합니다. 한글 질의어는 조사·활용 접미사가 붙은 토큰에도 접두 일치를 허용합니다. 예를 들어 `배송`은 `배송은`, `확인`은 `확인합니다`를 찾습니다. 라틴 문자와 숫자는 의도치 않은 부분 일치를 피하기 위해 정확히 일치해야 합니다.
7. `HybridRagIndex`는 로컬 sparse 결과와 `DenseCandidateRanker`의 Mock 후보를 **Reciprocal Rank Fusion (RRF)** 으로 결합합니다. 제공자별 점수 크기는 섞지 않고 순위만 사용하며, dense 후보는 현재 로컬 인덱스의 중복 없는 청크 ID만 가리켜야 합니다. 이 모듈은 dense 모델·네트워크 클라이언트를 만들지 않습니다.
8. `QueryTransformingIndex`는 주입된 `QueryTransformer`가 원 질문을 첫 번째로 보존하고 정해진 개수 안의 중복 없는 로컬/Mock 확장 질문만 반환하도록 검증합니다. 각 질문의 검색 순위는 RRF로 결합하며, 이 모듈은 변형 모델이나 네트워크 클라이언트를 만들지 않습니다.
9. `RerankingIndex`는 이미 인용 가능한 로컬 `SearchHit`의 제한된 후보만 주입된 `EvidenceReranker`에 전달합니다. `RerankResult`는 후보 청크 ID와 유한한 0~1 관련성 점수만 반환할 수 있고, 새 출처·중복 ID·후보 수 초과·범위 밖 점수는 거부합니다. 동점은 기존 검색 순서를 유지하며 최소 점수 미만의 근거는 제외합니다.
10. `ContextBudgetIndex`는 제한된 로컬 `SearchHit` 후보에서 전체 문자 예산에 맞는 **완전한 청크**만 순서대로 선택합니다. 청크를 자르지 않아 원래 문자 범위와 인용이 보존되며, 남은 예산보다 큰 상위 청크는 건너뛰고 뒤의 더 작은 근거를 선택할 수 있습니다. 이 모듈은 토크나이저·외부 모델·네트워크 클라이언트를 만들지 않습니다.
11. `DocumentDiversityIndex`는 제한된 로컬 `SearchHit` 후보의 원래 순위를 유지하면서 문서별 최대 청크 수를 적용합니다. 상위 문서의 제한 초과 청크를 건너뛰어 다른 문서의 근거를 포함하되, 선택 청크의 점수·텍스트·출처 URI·문자 범위는 바꾸지 않습니다.
12. `RagPipeline`은 검색된 `SearchHit`만 `ContextualGenerator`에 전달합니다. 근거가 없으면 생성기를 호출하지 않고 안전한 No-answer를 반환합니다.
13. 생성된 답변에는 사용자가 원문을 추적할 수 있도록 청크별 `Citation`(출처 URI와 문자 범위 포함)을 붙입니다.

생성기 경계는 `Protocol`이므로 실습과 테스트는 항상 Mock 구현만 사용합니다. 이 슬라이스는 외부 제공자, 라이브 API, 비밀값, 배포를 사용하지 않습니다.

## 실행

저장소 루트에서 다음 명령을 실행합니다.

```bash
uv run python examples/volume05/local_rag.py
uv run pytest tests/unit/test_volume05_rag.py -q
```

예제는 명시한 `handbook.md`·`returns.md`와 `exchange-notice.pdf`만 읽습니다. PDF 파일은 실제 엔진이 아니라 `SamplePdfTextExtractor`가 읽는 고정 로컬 바이트와 Mock 페이지 텍스트를 사용합니다. 이 경계는 실제 파서의 신뢰하지 않는 출력도 검증하도록 설계되어 있으므로, 학습자가 파서를 추가할 때도 네트워크·라이브 API 없이 교체 테스트할 수 있습니다. `SampleQueryTransformer`는 원 질문을 보존한 고정 로컬 확장 질문만, `SampleDenseRanker`는 로컬에 고정한 Mock 청크 ID만 반환합니다. 그 뒤 `SampleEvidenceReranker`는 이미 검색된 제한된 로컬 후보에만 0~1의 고정 점수를 부여하고, `DocumentDiversityIndex`는 문서당 한 청크만 남겨 한 문서에 근거가 집중되지 않게 합니다. 마지막 `ContextBudgetIndex`는 후보 3개와 600문자의 명시적 예산 안에서 청크 일부를 자르지 않고 근거를 선택합니다. 따라서 어휘가 겹치지 않는 도착 예정 질문도 배송 근거와 인용을 출력합니다. 반품과 PDF 교환 질문도 근거와 인용을 출력하고, 샘플 문서에 없는 주차장 할인 질문은 No-answer를 출력합니다. 새 파일을 샘플 디렉터리에 추가해도 명시적 `load_many()` 또는 `load()` 호출에 넣기 전에는 색인되지 않습니다.

## 장 목록

Indexing · Retrieval · Generation · Loader · Chunking · Metadata · Hybrid Search · Query Transformation · Citation · 보안 · FastAPI
