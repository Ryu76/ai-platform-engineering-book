# 01. 결정론적 Cross-Encoder Rerank와 품질 측정

## 1. 학습 목표

이 장을 마치면 1차 검색 후보의 원래 순위와 질의-후보 쌍을 다시 점수화한 순위를 구분하고, 고정 fixture에서 `precision@k`, `recall@k`, MRR, nDCG@k를 로컬 측정할 수 있습니다.

## 2. 왜 필요한가

Retriever는 많은 문서에서 후보를 빠르게 찾는 대신 질문의 모든 조건을 충분히 비교하지 못할 수 있습니다. Reranker는 이미 좁힌 후보 각각을 질의와 함께 비교해, 사용자가 보는 top-k의 정밀도를 높이는 두 번째 단계입니다.

## 3. 핵심 개념

- **bi-encoder/retriever**: 질의와 문서를 각각 표현해 넓은 후보를 빠르게 찾는 1차 단계입니다.
- **cross-encoder/reranker**: 질의와 후보를 한 쌍으로 평가해 후보별 관련성 점수를 다시 만드는 2차 단계입니다.
- **candidate set**: reranker가 새 문서를 찾지 않고 순서만 바꾸는, retriever가 전달한 제한된 목록입니다.
- **precision@k / recall@k**: 상위 k의 관련 문서 비율과 전체 관련 문서 회수 비율입니다.
- **MRR**: 첫 관련 문서의 역순위 평균입니다.
- **nDCG@k**: 관련 문서가 상위에 있을수록 더 높게 보는 순위 품질 지표입니다.

## 4. 동작 구조

```text
질의 ─> Retriever의 고정 후보·원래 점수 ─> 질의 × 후보 pair scoring ─> 새 top-k
           │                                               │
           └──────── 사람의 relevant ID judgment ──────────┴─> before/after metrics
```

이 slice의 `LexicalCrossEncoder`는 신경망 모델이 아니라 외부 모델 없이 이 경계를 재현하는 결정론적 교육용 구현입니다. 후보마다 질의 용어 coverage를 다시 세고, 같은 점수면 `candidate_id`로 정렬합니다.

## 5. 실습 환경

저장소 루트에서 실행합니다. 이 예제는 고정된 후보 문자열만 사용하며 네트워크, API 키, 모델 다운로드, GPU를 사용하지 않습니다.

```bash
uv run python examples/volume06/rerank_fixture.py
uv run pytest tests/unit/test_volume06_reranker.py -q
```

## 6. 단계별 실습

1. `examples/volume06/rerank_fixture.py`의 두 질의와 relevant ID를 확인합니다.
2. 각 후보의 나열 순서를 1차 retriever 순위로 간주합니다.
3. `LexicalCrossEncoder().rerank(query, candidates)`로 모든 후보를 다시 정렬합니다.
4. 원래 ID와 새 ID를 각각 `evaluate_ranking(..., k=1)`에 전달합니다.
5. `mean_ranking_metrics`로 질의별 결과를 평균 내 before/after를 비교합니다.

## 7. 코드 설명

`Candidate`는 stable ID, 텍스트, 원래 retriever 점수를 보존합니다. reranker는 원래 점수를 재사용하지 않아 두 단계가 섞이지 않게 합니다. coverage를 반복 횟수보다 크게 가중해, 질문의 여러 조건을 만족하는 후보가 한 단어를 여러 번 가진 후보보다 앞서도록 합니다.

`evaluate_ranking`은 중복 ID, 빈 relevance judgment, 0 이하 k를 거부합니다. 후보가 k보다 적어도 precision 분모를 k로 유지합니다. nDCG의 gain은 이 예제에서 binary relevance이며, 실제 등급형 judgment가 필요하면 별도 데이터 계약을 설계해야 합니다.

## 8. 정상 실행 결과

초기 `top_k=1` 비교는 아래처럼 고정 fixture에서 재현됩니다.

```text
candidate_count=2; top_k=1; pair_evaluations=4; ...
retriever_precision=0.000; reranker_precision=1.000; ...
retriever_recall=0.000; reranker_recall=1.000; ...
retriever_mrr=0.500; reranker_mrr=1.000; ...
retriever_ndcg=0.000; reranker_ndcg=1.000
```

`elapsed_ns`는 local host마다 달라서 위 축약 출력의 회귀 값이 아닙니다. 전체 candidate-count/top-k 행과 해석은 [02. 고정 후보 수와 Top-k Sweep](02-local-candidate-top-k-sweep.md)을 따릅니다. 이는 의도적으로 작은 고정 fixture의 측정값이며 실제 corpus, 사람의 judgment, 모델 비용이나 지연시간에 대한 성능 주장이 아닙니다.

## 9. 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `candidate_id values must be unique` | 같은 문서가 후보에 두 번 있음 | retriever adapter에서 stable ID 기준으로 중복을 제거합니다. |
| `query must be a non-empty string` | 빈 질의를 pair scorer로 전달함 | 입력 검증 뒤에 검색·rerank를 실행합니다. |
| 지표가 1.0인데 운영 품질이 낮음 | fixture가 실제 질문 분포를 대표하지 않음 | 사람이 검토한 질의, 관련 문서, 부정 질의를 늘립니다. |
| rerank가 느림 | 후보 수가 너무 많거나 모델이 큼 | retriever top-N을 측정해 제한하고 batch, timeout, 비용 예산을 별도로 검증합니다. |

## 10. 응용 실습

세 번째 질의와 적어도 두 개의 relevant ID를 fixture에 추가합니다. `k=1`, `k=2`, `k=3`에서 지표가 어떻게 달라지는지 테스트하고, candidate count를 늘릴 때 precision·recall·지연시간이 함께 바뀐다는 가설을 기록합니다.

## 11. 실무 적용

운영 Cross-Encoder는 버전이 고정된 모델·tokenizer·hardware·batch size·timeout·최대 후보 수를 기록합니다. 평가 집합은 실제 질의, 동의어, 짧은 질의, 최신성 문제, 권한 필터 뒤의 후보를 포함해야 합니다. reranker는 candidate set 밖 문서를 복구할 수 없으므로 retriever recall도 따로 측정합니다.

## 12. 과제

- **기본:** 첫 관련 문서가 3위인 경우 MRR을 테스트합니다.
- **응용:** 관련 문서가 두 개인 fixture에서 k별 precision, recall, nDCG를 비교합니다.
- **심화:** 실제 모델 adapter에 timeout, batch 상한, fallback 순서를 추가하되, 고정 fixture 회귀 테스트를 유지하는 설계를 작성합니다.

## 13. 완료 체크리스트

- [x] retriever와 reranker의 책임을 구분했다.
- [x] 결정론적 fixture candidate로 before/after 순위를 만들었다.
- [x] precision@k, recall@k, MRR, nDCG@k를 로컬에서 측정했다.
- [x] 중복·빈 입력·잘못된 k를 테스트했다.
- [ ] 대표 운영 corpus와 사람의 relevance judgment로 모델·threshold·candidate count를 결정한다.

## 14. 핵심 정리

Reranker의 가치는 새 문서를 생성하는 데 있지 않고 이미 찾은 후보를 질문에 더 맞게 정렬하는 데 있습니다. 따라서 작은 fixture의 개선을 운영 품질로 일반화하지 않고, stable ID와 명시적 judgment로 before/after 지표를 계속 측정해야 합니다.
