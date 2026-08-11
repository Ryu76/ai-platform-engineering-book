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
12. `ConfidenceThresholdIndex`는 제한된 후보의 점수가 유한한 0~1 정규화 신뢰도인지 검증하고, 명시한 최소 신뢰도보다 낮은 근거를 제외합니다. 이 경계는 점수 척도를 변환하지 않으므로 `RerankingIndex`처럼 정규화 점수를 만드는 단계 뒤에 둡니다. 모든 근거가 임계값 미만이면 빈 결과를 반환해 생성 전 No-answer를 보장하며, 통과한 청크의 인용 경계는 바꾸지 않습니다.
13. `LocalRagApi`는 프레임워크·HTTP 서버 없이 `{"query": string, "top_k"?: 1..20}` 로컬 JSON 요청을 검증합니다. 지원하지 않는 필드·빈 질문·범위 밖/boolean `top_k`는 생성기나 검색기를 호출하지 않고 안정된 `400 {"error": {"code": "invalid_request", "message": ...}}`로 반환합니다. 유효 요청은 `200`과 답변·No-answer·인용 JSON을 반환합니다.
14. `RetrievalEvaluator`는 명시한 고정 로컬 `RetrievalEvaluationCase`만 `SearchableIndex`에 전달해 생성기 호출 없이 Recall@k·Hit rate·MRR을 계산합니다. 각 사례는 하나 이상의 기대 청크 ID를 가져야 하며, 평가기는 tuple 이외 결과·요청 수 초과 결과·중복 청크 ID를 거부해 신뢰할 수 없는 검색기 출력이 지표를 왜곡하지 못하게 합니다.
15. `LocalRetrievalEvaluationSetLoader`는 허용된 로컬 루트 안에서 호출자가 명시한 UTF-8 `.json` 평가 세트 하나만 읽습니다. 경로 탈출·심볼릭 링크 탈출·빈/과대 파일·비 UTF-8·비표준 JSON·중복 JSON 키를 거부하고, 엄격한 `{"cases": [...]}` 스키마를 `RetrievalEvaluationCase` tuple로 변환합니다. 자동 디렉터리 탐색, 네트워크, 제공자 SDK는 사용하지 않습니다.
16. `RetrievalEvaluationBaseline`과 `RetrievalRegressionChecker`는 같은 고정 평가 세트의 이전 집계 기준선과 현재 `RetrievalEvaluationReport`를 결정론적으로 비교합니다. `top_k`, 사례 순서·ID·질문, 기대 청크 ID가 같지 않으면 비교를 거부하며, Recall@k·Hit rate·MRR별 허용 하락 폭을 명시적으로 판정합니다. 이 모듈은 검색·생성·네트워크·제공자 SDK를 호출하지 않습니다.
17. `RagPipeline`은 검색된 `SearchHit`만 `ContextualGenerator`에 전달합니다. 근거가 없으면 생성기를 호출하지 않고 안전한 No-answer를 반환합니다.
18. 생성된 답변에는 사용자가 원문을 추적할 수 있도록 청크별 `Citation`(출처 URI와 문자 범위 포함)을 붙입니다.

생성기 경계는 `Protocol`이므로 실습과 테스트는 항상 Mock 구현만 사용합니다. 이 슬라이스는 외부 제공자, 라이브 API, 비밀값, 배포를 사용하지 않습니다.

## 실행

저장소 루트에서 다음 명령을 실행합니다.

```bash
uv run python examples/volume05/local_rag.py
uv run pytest tests/unit/test_volume05_rag.py -q
```

예제는 명시한 `handbook.md`·`returns.md`와 `exchange-notice.pdf`만 읽습니다. PDF 파일은 실제 엔진이 아니라 `SamplePdfTextExtractor`가 읽는 고정 로컬 바이트와 Mock 페이지 텍스트를 사용합니다. 이 경계는 실제 파서의 신뢰하지 않는 출력도 검증하도록 설계되어 있으므로, 학습자가 파서를 추가할 때도 네트워크·라이브 API 없이 교체 테스트할 수 있습니다. `SampleQueryTransformer`는 원 질문을 보존한 고정 로컬 확장 질문만, `SampleDenseRanker`는 로컬에 고정한 Mock 청크 ID만 반환합니다. 그 뒤 `SampleEvidenceReranker`는 이미 검색된 제한된 로컬 후보에만 0~1의 고정 점수를 부여하고, `DocumentDiversityIndex`는 문서당 한 청크만 남겨 한 문서에 근거가 집중되지 않게 합니다. `ContextBudgetIndex`는 후보 3개와 600문자의 명시적 예산 안에서 청크 일부를 자르지 않고 근거를 선택합니다. 마지막 `ConfidenceThresholdIndex`는 정규화된 재순위화 점수가 0.8 이상인 근거만 생성기에 전달해 낮은 신뢰도의 응답을 No-answer로 바꿉니다. 예제는 배송·반품·PDF 교환의 고정 질의와 기대 청크 ID를 `sample_data/retrieval-evaluation.json`에서 명시적으로 읽어 `RetrievalEvaluator`를 실행하고 Recall@1·Hit rate·MRR을 출력합니다. 이어서 동일 사례 순서·질문·기대 청크 ID·`top_k=1` 및 각 지표 1.00을 명시한 `RetrievalEvaluationBaseline`과 비교합니다. `RetrievalRegressionChecker`는 지표 하락이 없을 때만 통과를 출력하며, 데이터셋·관련성 정의·반환 깊이가 바뀐 보고서는 품질 비교 대신 거부합니다. 이 JSON 파일은 루트 객체의 `cases` 배열만 허용하며, 각 사례는 `case_id`·`query`·`expected_chunk_ids` 배열을 정확히 한 번씩 가져야 합니다. `LocalRetrievalEvaluationSetLoader`는 자동으로 디렉터리를 탐색하지 않고, UTF-8·파일 크기·경로·중복 키·사례 ID를 검증합니다. 이 파이프라인은 `LocalRagApi.handle()`에 고정 로컬 요청 객체로 전달되며, API 응답도 네트워크 서버 없이 출력됩니다. 따라서 어휘가 겹치지 않는 도착 예정 질문도 배송 근거와 인용을 출력합니다. 반품과 PDF 교환 질문도 근거와 인용을 출력하고, 샘플 문서에 없는 주차장 할인 질문은 No-answer를 출력합니다. 새 파일을 샘플 디렉터리에 추가해도 명시적 `load_many()`·`load()` 또는 평가 세트 로더 호출에 넣기 전에는 색인·평가되지 않습니다.

## 프레임워크 독립 API 계약

`LocalRagApi`는 웹 프레임워크 어댑터가 사용할 수 있는 작은 로컬 경계입니다. 서버를 실행하거나 FastAPI 의존성을 추가하지 않으며, JSON을 역직렬화한 값만 받습니다.

```python
from ai_platform.rag import LocalRagApi, RagPipeline

api = LocalRagApi(pipeline=RagPipeline(index=index, generator=mock_generator))
response = api.handle({"query": "배송 상태는 어떻게 확인하나요?", "top_k": 1})

assert response.status_code == 200
payload = response.to_payload()
# {"answer": "...", "no_answer": False,
#  "citations": [{"label": 1, "chunk_id": "...", "source_uri": "...",
#                 "start_offset": 0, "end_offset": 54, "title": "..."}]}
```

`query`는 공백이 아닌 문자열이어야 하고 `top_k`는 선택적 1~20 정수입니다. 입력 객체는 이 두 필드만 허용합니다. 잘못된 요청은 `400` 및 공개 `invalid_request` 오류가 되며, 검색기·Mock 생성기는 호출되지 않습니다. 성공한 No-answer는 여전히 `200`이고 `citations: []`, `no_answer: true`를 반환합니다. 검색·생성의 내부 구성 오류는 요청 오류로 위장하지 않고 호출자에게 전파됩니다.

## 고정 검색 품질 평가 계약

`RetrievalEvaluator`는 생성 품질이나 라이브 제공자 호출을 측정하지 않습니다. 명시한 로컬 질의와 기대 청크 ID만 사용해 검색 회귀를 검출하는 경계입니다. 사례별 `recall_at_k`는 기대 청크 중 상위 k에서 회수한 비율이고, `passed`와 `reciprocal_rank`는 첫 기대 청크가 상위 k에 나타났는지와 그 역순위를 나타냅니다. 보고서의 `recall_at_k`는 모든 기대 청크의 마이크로 평균, `hit_rate`는 하나 이상 회수한 사례 비율, `mean_reciprocal_rank`는 사례별 역순위 평균입니다.

```python
from pathlib import Path

from ai_platform.rag import (
    LocalRetrievalEvaluationSetLoader,
    RetrievalEvaluationConfig,
    RetrievalEvaluator,
)

cases = LocalRetrievalEvaluationSetLoader(root=Path("examples/volume05/sample_data")).load(
    Path("retrieval-evaluation.json")
)
report = RetrievalEvaluator(
    index=index, config=RetrievalEvaluationConfig(top_k=1)
).evaluate(cases)

assert report.recall_at_k == 1.0
assert report.hit_rate == 1.0
assert report.mean_reciprocal_rank == 1.0
```

파일 루트는 정확히 `{"cases": [...]}`여야 하고 각 사례 객체는 `case_id` 문자열, `query` 문자열, 비어 있지 않고 중복 없는 문자열 `expected_chunk_ids` 배열만 포함합니다. 로더는 명시한 상대 `.json` 파일만 읽으며 절대 경로·경로/심볼릭 링크 탈출·자동 탐색·빈/과대 파일·비 UTF-8·잘못된 JSON·중복 JSON 키를 거부합니다. `RetrievalEvaluationCase`로 변환된 뒤 빈 사례 세트·중복 사례 ID·구성한 최대 사례 수 초과는 거부합니다. 평가기는 검색기의 tuple 반환, 최대 `top_k`개 결과, `SearchHit` 타입 및 중복 없는 청크 ID를 확인합니다. 보고서의 `to_payload()`는 원문이나 생성 답변 없이 사례 ID·기대/회수 청크 ID·순위·지표만 포함한 JSON 호환 값입니다.

## 고정 기준선 회귀 판정 계약

`RetrievalEvaluationBaseline`은 이전에 승인한 같은 평가 세트의 `top_k`, 사례 순서, 사례 ID, 질문, 기대 청크 ID와 Recall@k·Hit rate·MRR을 보관합니다. `RetrievalRegressionChecker`는 현재 보고서가 이 호환성 조건을 모두 만족할 때만 비교합니다. 그러므로 사례를 추가하거나 기대 근거를 바꾸거나 반환 깊이를 바꾼 결과를 이전 기준선과 비교해 잘못된 개선 또는 회귀로 기록하지 않습니다.

정책 기본값은 각 지표의 하락을 `0.0`만큼만 허용합니다. 실험에서 제한된 하락을 허용해야 하면 `RetrievalRegressionPolicy`에 지표별 0~1의 최대 하락 폭을 명시합니다. 판정은 예외로 품질 실패를 숨기지 않습니다. 호환되는 보고서의 품질 하락은 `RetrievalRegressionDecision.passed == false` 및 기준선 점수·현재 점수·하락 폭·허용 폭을 포함한 payload로 반환합니다. 호환되지 않는 보고서는 `RagConfigurationError`로 거부합니다.

```python
from ai_platform.rag import (
    RetrievalEvaluationBaseline,
    RetrievalRegressionChecker,
    RetrievalRegressionPolicy,
)

baseline = RetrievalEvaluationBaseline.from_report(approved_report)
decision = RetrievalRegressionChecker(
    baseline=baseline,
    policy=RetrievalRegressionPolicy(maximum_mean_reciprocal_rank_drop=0.05),
).evaluate(current_report)

assert decision.passed
```

이 비교 경계는 파일을 읽거나, 검색기·생성기·제공자 SDK·네트워크를 호출하지 않습니다. 기준선과 판정 payload에는 질의 원문, 문서 원문, 생성 답변을 넣지 않습니다.

## 장 목록

Indexing · Retrieval · Retrieval Evaluation · Retrieval Regression · Generation · Loader · Chunking · Metadata · Hybrid Search · Query Transformation · Citation · 보안 · FastAPI
