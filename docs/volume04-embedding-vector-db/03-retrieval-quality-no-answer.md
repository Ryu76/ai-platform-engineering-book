# 03. 검색 품질 측정과 No-answer Gate

## 1. 학습 목표

이 장을 마치면 검색 결과의 ID 순위를 정답 문서 집합과 비교해 `precision@k`, `recall@k`, reciprocal rank, `hit@k`를 계산할 수 있습니다. 또한 cosine score 임계값이 낮은 신호를 보수적으로 거절하는 no-answer gate임을 이해하고, 점수 하나만으로 사실성을 보장할 수 없다는 점을 설명할 수 있습니다.

## 2. 왜 필요한가

벡터 검색은 언제나 결과를 반환할 수 있습니다. 그러나 반환되었다는 사실은 그 결과가 사용자의 질문에 답할 근거라는 뜻이 아닙니다. 특히 이 권의 해시 기반 local mock은 토큰 충돌과 제한된 표현 때문에 의미적으로 관련 없는 문서에도 점수를 줄 수 있습니다.

따라서 검색 기능을 구현한 뒤에는 대표 질의마다 **어떤 문서가 정답인지** 먼저 기록하고, 실제 반환 ID의 순위를 측정해야 합니다. 이 과정은 다음 권의 RAG가 검색 결과를 답변 근거로 사용하기 전에 필요한 회귀 테스트 경계입니다.

## 3. 핵심 개념

- **relevance judgment(정답 판단)**: 한 질의에 실제로 도움이 되는 문서 ID의 집합입니다. 점수가 아니라 사람이 검토한 기준입니다.
- **top-k**: 상위 `k`개 결과만 평가하는 범위입니다. 사용자에게 세 결과만 보여 준다면 `k=3`이 자연스러운 출발점입니다.
- **precision@k**: 상위 `k`개 중 관련 문서 비율입니다. 불필요한 문서가 적은지 봅니다.
- **recall@k**: 모든 관련 문서 중 상위 `k`개에서 찾은 비율입니다. 필요한 문서를 놓치지 않는지 봅니다.
- **reciprocal rank**: 첫 관련 문서가 `r`번째이면 `1/r`입니다. 여러 질의의 평균은 MRR(mean reciprocal rank)입니다.
- **hit@k**: 상위 `k`개에 관련 문서가 하나라도 있으면 참입니다. 여러 질의에서는 hit rate로 평균을 냅니다.
- **score threshold**: 최상위 cosine score가 최소값보다 낮을 때 답변 근거가 부족하다고 보는 명시적 gate입니다.
- **no-answer**: 근거가 부족할 때 추측 대신 추가 정보 요청, 검색 범위 변경, 또는 답변 보류를 선택하는 정책입니다.

## 4. 흐름

```text
고정 문서 + 정답 ID ─> local embedding + local collection ─> ranked result IDs
                                                            │
                     relevant IDs + k ─────────────────────┘
                                                            ▼
                                  precision@k / recall@k / MRR / hit@k
                                                            │
최상위 cosine score + 검증한 threshold ────────────────────┼─> answerable 또는 no-answer
```

`evaluate_ranking`은 vector score를 다시 계산하지 않습니다. 이미 검색된 **안정적인 point ID의 순서**와 정답 ID를 비교합니다. 이 분리는 임베딩 모델·저장소 구현을 바꿔도 평가 데이터를 유지할 수 있게 합니다.

## 5. 환경과 파일

모든 명령은 저장소 루트에서 실행합니다. Python 3.12 이상과 `uv`가 필요합니다. 이 실습은 네트워크, API 키, 외부 모델, Docker, Qdrant 서버를 사용하지 않습니다.

- `src/ai_platform/embeddings/retrieval_evaluation.py`
- `examples/volume04/retrieval_quality.py`
- `tests/unit/test_volume04_retrieval_evaluation.py`

```bash
uv run python examples/volume04/retrieval_quality.py
uv run pytest tests/unit/test_volume04_retrieval_evaluation.py -q
```

환경이 없으면 저장소 루트에서 `uv sync --group dev`를 실행한 뒤 명령을 다시 실행합니다.

## 6. 단계별 실습

1. 예제는 `DeterministicEmbeddingModel(dimensions=256)`과 `InMemoryVectorStore`로 세 문서를 색인합니다.
2. `Python API 오류 처리 방법`을 같은 모델로 임베딩하고 상위 두 결과를 검색합니다.
3. 결과의 `SearchResult.id`만 순서대로 `evaluate_ranking`에 전달합니다.
4. `retry-guide`를 이 질의의 정답 ID로 기록하고 `k=1`로 평가합니다.
5. `precision_at_k`, `recall_at_k`, `reciprocal_rank`, `hit_at_k`를 함께 해석합니다.
6. 첫 결과 score를 `minimum_score=0.5`와 비교합니다.
7. score가 gate를 통과해도, 실제 운영에서는 출처·권한·문서 최신성까지 확인한 후에만 답변을 생성합니다.

## 7. 코드 설명

`evaluate_ranking(ranked_ids, relevant_ids, k=...)`는 중복 ID, 빈 정답 집합, 빈 문자열 ID, 0 이하의 `k`를 거부합니다. 중복은 한 문서가 순위에서 두 번 나타난 버그를 높은 품질로 오인하지 않게 합니다.

검색 결과가 `k`보다 적어도 precision의 분모는 `k`입니다. 예를 들어 `k=3`인데 결과가 하나이고 그 하나가 관련 문서여도 precision@3은 `1/3`입니다. 후보 부족을 숨기지 않는 보수적인 정의입니다. 반면 reciprocal rank는 top-k로 자르지 않은 전체 순위에서 첫 관련 결과를 찾습니다. top-k 품질과 첫 정답의 위치를 별도로 볼 수 있습니다.

`RetrievalMetrics`와 `RetrievalSummary`는 public immutable record이므로 수동으로 만들더라도 모든 수치가 bool이 아닌 유한한 `[0.0, 1.0]` 값인지 확인합니다. 따라서 잘못된 fixture의 `NaN`, 무한대, 범위 밖 비율이 평균으로 전파되지 않습니다. 또한 `precision_at_k`와 `recall_at_k`가 0보다 큰지 여부와 `hit_at_k`는 반드시 일치해야 합니다. 즉 top-k에 관련 결과가 없으면 둘 다 0이고 `hit_at_k=False`이며, 관련 결과가 있으면 둘 다 양수이고 `hit_at_k=True`입니다. `hit_at_k=True`인 record는 첫 관련 결과가 top-k 안에 존재하므로 `reciprocal_rank`도 반드시 양수여야 합니다. 반대로 top-k 밖에서 처음 관련 결과를 찾는 경우에는 `hit_at_k=False`여도 양수 reciprocal rank가 허용됩니다. `mean_retrieval_metrics`는 비어 있지 않은 `RetrievalMetrics` sequence만 받아 평균 precision, 평균 recall, MRR, hit rate로 요약합니다. 문자열·bytes·generator 같은 일회성 입력은 거부하므로 `len()` 실패나 소진된 iterator가 보고서로 섞이지 않습니다. `meets_score_threshold`는 score와 임계값 모두가 유한한 cosine 범위 `[-1.0, 1.0]` 안에 있을 때만 받고, `score >= minimum_score`일 때만 참을 반환합니다. 따라서 다른 metric의 거리나 잘못 변환된 `1.1` 같은 값을 cosine score로 오인해 gate를 통과시키지 않습니다.

## 8. 정상 실행 결과와 해석

고정 입력의 예제는 다음을 출력합니다.

```text
ranked_ids=retry-guide,vector-guide
precision_at_1=1.0; recall_at_1=1.0; mrr=1.0; hit_at_1=True
top_score=0.548; minimum_score=0.500; answerable=True
```

첫 결과가 정답인 하나의 작은 예제이므로 모든 top-1 지표가 1.0입니다. 이것은 local mock과 이 고정 문서 세트에 대한 계약일 뿐, 실제 검색 품질의 증명은 아닙니다. 운영 임계값 `0.500`도 이 값만 보고 채택하면 안 됩니다. 다양한 긍정·부정 질의를 모아 precision/recall과 false-answer 비용을 검토해 정합니다.

## 9. 문제 해결

| 증상 | 가능한 원인 | 확인 및 해결 |
|---|---|---|
| `ranked_ids must not contain duplicates` | 검색 어댑터가 같은 point를 중복 반환함 | point ID를 기준으로 결과 생성 경로를 조사하고 중복을 제거합니다. |
| `relevant_ids must not be empty` | 평가할 정답 판단을 기록하지 않음 | 질의마다 검토한 관련 문서 ID를 최소 하나 지정합니다. 정답이 없는 질의는 별도 no-answer 평가 집합으로 관리합니다. |
| `metrics must be a non-empty sequence ...` | 평균에 빈 목록 또는 generator를 전달함 | 먼저 질의별 `RetrievalMetrics`를 list 또는 tuple에 수집한 뒤 한 번에 전달합니다. |
| `precision_at_k, recall_at_k, and hit_at_k must agree` | 수동 fixture에서 top-k 관련 결과의 비율과 hit flag가 모순됨 | 관련 결과가 없으면 precision·recall을 모두 `0.0`, `hit_at_k=False`로 설정하고, 있으면 두 비율을 양수, `hit_at_k=True`로 설정합니다. |
| `reciprocal_rank must be positive when hit_at_k is true` | 수동 fixture가 top-k hit을 주장하면서 첫 관련 결과 순위를 `0.0`으로 기록함 | `hit_at_k=True`이면 실제 첫 관련 결과 rank `r`에 대해 `1/r`을 기록합니다. top-k 밖의 첫 관련 결과만 `hit_at_k=False`와 양수 reciprocal rank를 함께 가질 수 있습니다. |
| `k must be a positive integer` | `0`, 음수 또는 불리언을 전달함 | 사용자 노출 개수에 맞는 양의 정수를 사용합니다. |
| `score must be between ...` 또는 `minimum_score must be between ...` | cosine 범위 밖 score 또는 임계값을 사용함 | cosine 기반 store에서는 score와 임계값 모두 -1.0부터 1.0까지의 유한한 값을 사용합니다. 다른 metric 값은 adapter에서 의미와 방향을 명시적으로 변환한 뒤 평가합니다. |
| 기대 문서가 1위가 아님 | 해시 mock은 의미를 학습하지 않음 | 공유 토큰을 점검하고, 실무에서는 별도 평가로 검증한 임베딩 모델과 corpus를 사용합니다. |

## 10. 응용 실습

두 번째 질의와 정답 ID를 추가합니다. 첫 질의가 `retry-guide`, 두 번째 질의가 `vector-guide`를 정답으로 갖게 한 뒤 각각 top-1 결과를 평가합니다. `mean_retrieval_metrics`로 평균 precision, 평균 recall, MRR, hit rate를 출력합니다.

그 다음 관련 없는 질의를 하나 만들고 최상위 score를 기록합니다. 양성 질의의 score와 비교해 임계값 후보를 정하되, 임의의 소수점 한 자리로 고정하지 않습니다. 임계값을 높일수록 잘못된 답변은 줄 수 있지만 유용한 답변도 거절할 수 있다는 trade-off를 기록합니다.

## 11. 실무 적용

평가 집합에는 실제 사용 질의, 동의어, 오탈자, 짧은 질의, 오래된 문서, 권한이 다른 문서를 포함합니다. 각 judgment는 문서 버전·평가자·판단 기준과 함께 검토 가능하게 관리합니다. 모델, chunking, vector dimension, distance metric, filter 정책, corpus가 바뀌면 같은 집합을 다시 평가합니다.

No-answer gate는 score만의 문제가 아닙니다. 테넌트·ACL filter를 먼저 적용하고, 반환 문서가 최신인지, 질문과 직접 관련되는지, 충분한 출처가 있는지 확인해야 합니다. 점수와 원문, 사용자 질의, API 키 같은 민감한 데이터를 불필요하게 로그에 남기지 않습니다.

## 12. 과제

- **기본**: 첫 정답이 세 번째인 순위에서 reciprocal rank가 무엇인지 계산하고 테스트로 확인합니다.
- **응용**: 관련 문서가 두 개일 때 `k=1`과 `k=2`의 precision·recall 차이를 테스트합니다.
- **심화**: 정답이 없는 질의만 모은 no-answer 평가 데이터를 정의하고, false answer와 false rejection을 각각 어떻게 측정할지 설계합니다.

## 13. 완료 체크리스트

- [x] 정답 판단이 score와 다른 데이터임을 설명할 수 있다.
- [x] precision@k, recall@k, reciprocal rank, hit@k를 계산했다.
- [x] 여러 질의를 평균 지표와 hit rate로 요약했다.
- [x] 중복 결과와 잘못된 평가 입력을 테스트했다.
- [x] 결정적 local mock으로 검색-평가 흐름을 실행했다.
- [x] score threshold가 답변 사실성 보장이 아니라 보수적 gate임을 확인했다.
- [ ] 대표 운영 corpus와 사람이 검토한 judgment로 임계값을 결정한다.

## 14. 핵심 정리

벡터 검색 품질은 “결과가 반환되었는가”가 아니라 정답 문서가 사용자가 보는 상위 결과에 얼마나 자주, 얼마나 빨리 들어오는가로 측정합니다. 안정적인 point ID 기반 평가는 local mock, Qdrant, 다음 권의 RAG retrieval 구현에 공통으로 적용됩니다. No-answer gate는 낮은 신호를 거절하는 시작점이며, 출처·권한·최신성 검증을 대체하지 않습니다.
