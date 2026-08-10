# Volume 05 RAG 진행 기록

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

- 로컬 파일 loader의 입력 경계와 메타데이터 정제를 별도 테스트 가능한 단계로 확장합니다.

> 현재는 Volume 05 전체 PRD DoD 완료 상태가 아니므로 `VOLUME05_COMPLETE=true`는 설정하지 않았습니다.
