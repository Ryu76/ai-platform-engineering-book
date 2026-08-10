# Volume 05. RAG

## 목표

문서를 로드·정제·청크·인덱싱하고 검색 근거·출처·No-answer 처리를 갖춘 RAG API를 구현합니다.
첫 번째 실습 슬라이스는 네트워크, API 키, 벡터 DB 없이도 재현 가능한 **로컬 검색 → Mock 생성 → 인용** 경계입니다.

## 현재 실습: 로컬·인용 가능 RAG

`src/ai_platform/rag/`의 로컬 구성 요소는 다음 계약을 제공합니다.

1. `LocalMarkdownLoader`는 허용된 로컬 루트 안의 UTF-8 `.md`/`.markdown` 파일만 읽습니다. 경로 탈출·심볼릭 링크 탈출·빈 파일·NUL·다른 인코딩은 거부하고, BOM·줄 끝·수평 공백·반복 빈 줄을 결정론적으로 정제합니다. 첫 Markdown 제목 또는 파일명으로 제목을 만들고 URI 안전한 로컬 출처를 기록합니다.
2. `SourceDocument`는 문서 ID, 제목, 로컬 출처 URI, 정제 원문을 함께 보관합니다. 중복 ID와 빈 값은 거부합니다.
3. `LocalRagIndex`는 원문 문자 범위를 보존하며 공백 경계 우선 청킹을 수행합니다. 각 `DocumentChunk`에는 재현 가능한 `chunk_id`와 시작/끝 오프셋이 있습니다.
4. `search()`는 로컬 어휘 점수로 근거를 정렬합니다. 한글 질의어는 조사·활용 접미사가 붙은 토큰에도 접두 일치를 허용합니다. 예를 들어 `배송`은 `배송은`, `확인`은 `확인합니다`를 찾습니다. 라틴 문자와 숫자는 의도치 않은 부분 일치를 피하기 위해 정확히 일치해야 합니다.
5. `RagPipeline`은 검색된 `SearchHit`만 `ContextualGenerator`에 전달합니다. 근거가 없으면 생성기를 호출하지 않고 안전한 No-answer를 반환합니다.
6. 생성된 답변에는 사용자가 원문을 추적할 수 있도록 청크별 `Citation`(출처 URI와 문자 범위 포함)을 붙입니다.

생성기 경계는 `Protocol`이므로 실습과 테스트는 항상 Mock 구현만 사용합니다. 이 슬라이스는 외부 제공자, 라이브 API, 비밀값, 배포를 사용하지 않습니다.

## 실행

저장소 루트에서 다음 명령을 실행합니다.

```bash
uv run python examples/volume05/local_rag.py
uv run pytest tests/unit/test_volume05_rag.py -q
```

예제는 `examples/volume05/sample_data/handbook.md`만 읽습니다. 첫 질문은 근거와 인용을 출력하고, 샘플 문서에 없는 주차장 할인 질문은 No-answer를 출력합니다.

## 장 목록

Indexing · Retrieval · Generation · Loader · Chunking · Metadata · Hybrid Search · Query Transformation · Citation · 보안 · FastAPI
