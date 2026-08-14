# 검색 품질: Recall·Precision·Hit Rate·MRR·NDCG

## 1. 학습 목표

이 장을 완료하면 다음을 할 수 있어야 합니다.

- 동일한 고정 골든 데이터와 `k`에서 Recall@k, Precision@k, Hit Rate@k, MRR, NDCG@k의 역할을 구분한다.
- 평균 점수와 사례별 점수를 함께 읽어 누락, 늦은 정답, 불필요한 문서의 실패 원인을 찾는다.
- 정답이 하나인 사례와 여러 개인 사례에서 Recall과 NDCG의 해석 차이를 설명한다.
- `k`를 키울 때 Recall과 Precision, 지연 시간·비용이 함께 바뀔 수 있음을 설명한다.
- `benefits-enrollment`의 완전한 검색 실패와 `expense-receipt`의 2위 정답을 고정 결과에서 재현한다.
- API, 벡터 데이터베이스, 난수, 시계 없이 사례별 검색 평가를 실행한다.

## 2. 왜 필요한가

평균 Recall@3이 0.75라는 사실만으로는 어떤 사용자가 실패했는지 알 수 없습니다. 정답 문서가 한 번도 검색되지 않은 경우와 정답이 2위에 밀린 경우는 모두 개선 대상이지만, 원인과 대응은 다릅니다. 전자는 인덱스·질의 변환·문서 범위를 점검해야 하고, 후자는 재정렬·메타데이터 필터·상위 후보 수를 조정할 수 있습니다.

또한 지표 하나만 최적화하면 제품 품질을 오해할 수 있습니다. `k`를 크게 하면 관련 문서를 놓칠 확률은 낮아질 수 있지만, 불필요한 문맥, LLM 입력 토큰, 지연 시간이 늘어날 수 있습니다. 이 장은 고정된 `volume10-support-policy@1.0.0`의 기록된 Top-3 결과로 지표의 트레이드오프와 실패 사례 해석을 분리합니다.

> [!WARNING]
> 이 실습의 순위는 교육용으로 코드에 고정된 문서 ID입니다. 실제 고객 질의, 문서 본문, API 키, 외부 Retriever나 LLM을 사용하지 않습니다. 운영에서 실제 로그를 분석할 때는 비식별화, 권한, 보존 기간, 라벨 검토 절차를 별도로 승인해야 합니다.

## 3. 핵심 개념

- **Recall@k:** 정답 문서 집합 중 상위 `k`에 들어온 비율입니다. 관련 문서를 놓치지 않았는지 봅니다.
- **Precision@k:** 상위 `k` 중 정답 문서 비율입니다. 이 구현은 짧은 결과도 분모를 `k`로 고정합니다.
- **Hit Rate@k:** 상위 `k`에 정답이 하나라도 있는 사례의 비율입니다. 첫 번째 관련 문서만 있어도 성공으로 셉니다.
- **MRR:** 사례마다 첫 정답의 역순위를 평균낸 값입니다. 1위는 1, 2위는 0.5, 정답이 없으면 0입니다.
- **NDCG@k:** 정답이 앞 순위에 있고 여러 정답을 더 많이 회수할수록 높아지는 0~1의 순위 품질입니다.
- **사례별 지표:** 평균을 만들기 전의 점수와 첫 정답 위치입니다. 회귀를 원인별로 분류하는 근거입니다.
- **절단 순위 `k`:** 사용자에게 넘길 후보 수입니다. 지표 비교에서는 데이터셋 버전과 `k`를 함께 고정합니다.

`answer` 사례만 검색 지표의 분모에 들어갑니다. 관련 문서가 의도적으로 없는 `abstain` 사례를 0 Recall로 넣으면 Retriever가 문서를 놓친 것과 올바른 보류를 혼동합니다. no-answer 보류 품질은 이후 답변 평가에서 별도 측정합니다.

## 4. 동작 구조

```text
고정 GoldenDataset answer 사례             고정 문서 순위
(case_id, 정답 문서 ID)              (case_id -> Top-3 문서 ID)
              │                                  │
              └─────────────┬────────────────────┘
                            ▼
                 입력 계약 검증
      (양의 k, 완전한 case_id, 중복 없는 문서 ID)
                            │
                            ▼
             사례별 RetrievalCaseMetrics
 (회수된 정답 ID, 첫 정답 순위, Recall, Precision, MRR, NDCG)
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
       평균 RetrievalMetrics           실패 사례 보고
              │                           │
              └────────► 고정 버전·k와 함께 회귀 비교
```

`evaluate_retrieval_cases()`는 입력 사례 순서대로 `RetrievalCaseMetrics`를 반환합니다. `evaluate_retrieval()`는 같은 사례별 결과를 산술 평균해 전체 지표를 반환합니다. 따라서 두 보고서는 같은 계약과 같은 입력에 기반하며 네트워크, 시계, 난수, 라이브 모델 상태에 의존하지 않습니다.

## 5. 실습 환경

이 장의 산출물은 다음과 같습니다.

- `src/ai_platform/evaluation/retrieval_metrics.py`: 전체 지표와 사례별 `RetrievalCaseMetrics`를 계산합니다.
- `src/ai_platform/evaluation/datasets.py`: 버전 관리된 고정 정답·Top-3 순위를 제공합니다.
- `examples/volume10/retrieval_quality.py`: 전체 기준선을 출력합니다.
- `examples/volume10/retrieval_failure_analysis.py`: 사례별 회수 문서와 첫 정답 순위를 출력합니다.
- `tests/evaluation/test_retrieval_metrics.py`: 평균 기준선, 사례별 실패, 입력 오류를 검사합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
conda env update --file environment.yml --prune
```

환경 변수, API 키, 모델 서버, 벡터 데이터베이스는 필요하지 않습니다. Windows Git Bash에서도 저장소 루트에서 같은 Conda 환경 명령을 실행할 수 있습니다.

## 6. 단계별 실습

### 6.1 전체 기준선 확인

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
python examples/volume10/retrieval_quality.py
```

전체 평균은 네 개 `answer` 사례를 평가합니다. `abstain`인 `office-parking`은 이 검색 Recall 분모에 포함되지 않습니다.

### 6.2 사례별 실패 분석

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
python examples/volume10/retrieval_failure_analysis.py
```

`expense-receipt`는 정답이 회수됐지만 `first_rank=2`입니다. `benefits-enrollment`는 `retrieved=none`, `first_rank=none`이므로 Top-3 전체에서 정답을 놓친 사례입니다. 반대로 `incident-response`는 두 정답을 모두 회수해 Precision@3이 0.666667입니다.

### 6.3 회귀 계약 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/evaluation/test_retrieval_metrics.py -q
```

테스트는 평균값뿐 아니라 사례 출력 순서, 2위 정답, 두 정답 회수, 완전 누락을 고정합니다. 문자열 하나를 문서 ID 목록으로 잘못 넘기는 입력도 거부하므로 문자 단위로 잘못 계산되는 일을 막습니다.

### 6.4 `k` 변경을 해석하는 순서

새 Retriever를 비교할 때는 먼저 같은 데이터셋 버전과 같은 `k`로 전체·사례별 보고서를 만듭니다. 그 다음 실패 ID와 첫 정답 순위를 비교합니다. 마지막으로 `k`를 변경하려면 Recall/Precision과 함께 후보 수 증가에 따른 문맥 길이, 지연 시간, 비용을 별도 표로 기록합니다. `k`가 다른 두 점수를 직접 "개선"으로 비교하지 않습니다.

## 7. 코드 설명

`RetrievalCaseMetrics`는 사례 ID, Top-k 안에서 회수된 정답 문서 ID, 첫 정답 순위, 다섯 지표 중 사례 단위로 정의되는 값을 보관합니다. 회수된 ID는 순위 순서를 유지하므로 복수 정답이 앞에 모였는지 확인할 수 있습니다. 정답이 없으면 `first_relevant_rank`는 숫자 0이 아니라 `None`입니다. 0위라는 존재하지 않는 순위와 실패를 구별하기 위해서입니다.

`evaluate_retrieval_cases()`는 먼저 `k`, 비어 있지 않은 사례, 고유 사례 ID, 결과의 정확한 case ID 집합, 중복 없는 문서 ID를 검증합니다. 그 뒤 각 사례의 Top-k만 잘라 Boolean 관련도 벡터를 만들고, Recall·Precision·Hit·MRR·NDCG를 계산합니다. `evaluate_retrieval()`는 그 결과만 평균내므로 사례 분석과 전체 보고서가 서로 다른 계산 경로로 어긋나지 않습니다.

`retrieval_failure_analysis.py`는 고정 결과를 읽어 각 사례를 한 줄씩 출력합니다. 출력 순서는 사전 순서가 아니라 `FIXED_RETRIEVAL_CASES`의 고정 사례 순서입니다. 파일 조회, 다운로드, 랜덤 샘플링을 하지 않으므로 CI에서도 같은 실패 ID와 수치가 나옵니다.

## 8. 정상 실행 결과

6.2 명령은 다음 출력을 포함해야 합니다.

```text
Cutoff: 3
access-reset: retrieved=identity-access; first_rank=1; Recall@3=1.000000; Precision@3=0.333333; MRR=1.000000; NDCG@3=1.000000
expense-receipt: retrieved=finance-expense; first_rank=2; Recall@3=1.000000; Precision@3=0.333333; MRR=0.500000; NDCG@3=0.630930
incident-response: retrieved=operations-runbook, security-incident; first_rank=1; Recall@3=1.000000; Precision@3=0.666667; MRR=1.000000; NDCG@3=1.000000
benefits-enrollment: retrieved=none; first_rank=none; Recall@3=0.000000; Precision@3=0.000000; MRR=0.000000; NDCG@3=0.000000
```

6.3 명령은 pytest 실행 시간과 무관하게 `passed`로 끝나야 합니다. 수치가 다르면 먼저 데이터셋 ID·버전, `k`, 기록된 순위가 기준선과 같은지 확인합니다. 라이브 검색이나 임의의 기대값 변경으로 해결하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `k must be a positive integer` | `k`가 0, 음수, 불리언, 문자열이다. | Top-k 개수를 나타내는 양의 정수만 전달한다. |
| `missing=` 또는 `unexpected=` | 골든 사례와 결과의 `case_id` 집합이 다르다. | 모든 사례에 정확히 한 결과가 있는지 확인한다. |
| `must be unique` | 같은 문서 ID가 하나의 순위에 반복된다. | Retriever의 중복 제거를 점검하고 기록된 결과를 수정한다. |
| `must be a sequence of strings` | 문서 ID 하나를 목록 대신 문자열로 전달했다. | `("document-a",)`처럼 문자열 시퀀스를 전달한다. |
| `first_rank=none` | Top-k에 정답 문서가 없다. | 라벨·문서 범위를 확인한 뒤 질의 변환, 인덱싱, 후보 생성, 필터를 원인별로 점검한다. |
| Recall은 높지만 MRR/NDCG가 낮다 | 정답은 회수됐지만 뒤 순위에 있다. | reranking, 메타데이터, 후보 점수와 상위 노출 정책을 비교한다. |

## 10. 응용 실습

1. 정답이 두 개인 고정 사례를 만들고, 두 정답이 1·2위일 때와 2·3위일 때의 NDCG@3를 테스트로 비교합니다.
2. 기록된 Retriever A/B 결과를 같은 데이터셋 버전·같은 `k`로 평가합니다. Recall은 같지만 첫 정답 순위가 다른 사례를 찾아 MRR과 NDCG가 필요한 이유를 설명합니다.
3. `k=3`과 `k=5`의 가상 순위를 작성합니다. 각 결과의 Recall·Precision 변화와 함께 후보 두 개 추가가 답변 Prompt 토큰과 지연 시간에 미칠 영향을 표로 설계합니다. 라이브 모델은 호출하지 않습니다.

## 11. 실무 적용

배포 후보를 비교할 때는 전체 평균만 승인 기준으로 삼지 않습니다. 코드 버전, 데이터셋 ID·버전, `k`, 사례 수, 지표, 구간별 점수, 실패 사례 ID, 제외 규칙을 하나의 리포트에 남깁니다. 중요 정책·안전·고빈도 의도에는 평균과 별도로 최소 Recall 또는 반드시 1위여야 하는 사례 기준을 둘 수 있습니다.

검색 실패는 라벨 오류, 문서 누락, 청킹, 색인, 쿼리 분석, 필터, 검색기, 재정렬 중 어디에서 생겼는지 분해해야 합니다. 먼저 고정 입력으로 재현한 다음 하나의 가설만 바꾸고 같은 평가를 실행합니다. `k` 확대는 품질 개선처럼 보일 수 있으나 더 많은 문맥으로 답변 정확성·환각·지연·토큰·비용을 악화시킬 수 있으므로 후속 지표와 함께 검토합니다.

> [!TIP]
> `first_rank=none` 사례와 `first_rank=2` 이상 사례를 별도 목록으로 보관하세요. 전자는 후보 생성 실패, 후자는 순위 품질 문제일 가능성이 있어 같은 개선책을 적용하면 원인이 가려질 수 있습니다.

## 12. 과제

- **기본:** Recall@3이 1이고 MRR이 0.5일 수 있는 이유를 한 사례의 문서 순위로 설명합니다.
- **응용:** `benefits-enrollment`의 0점과 `expense-receipt`의 NDCG@3 0.630930을 각각 어떤 실패로 분류할지 작성합니다.
- **심화:** 제품의 검색 회귀 승인 정책을 설계합니다. 데이터셋 버전, `k`, 전체 평균, 중요 사례, 실패 분석, 답변 지연·토큰·비용의 연결 조건을 포함하고 실제 고객 데이터나 외부 API를 사용하지 않습니다.

## 13. 완료 체크리스트

- [ ] Recall@k, Precision@k, Hit Rate@k, MRR, NDCG@k가 답하는 질문을 구분할 수 있다.
- [ ] 평균 지표와 사례별 지표를 함께 봐야 하는 이유를 설명할 수 있다.
- [ ] `first_rank=none`과 2위 이후 정답의 차이를 구분할 수 있다.
- [ ] 복수 정답 사례에서 Recall과 NDCG의 역할을 설명할 수 있다.
- [ ] `k`를 바꾸면 비교 조건과 지연·토큰·비용도 바뀐다는 점을 이해했다.
- [ ] `python examples/volume10/retrieval_failure_analysis.py`를 실행했다.
- [ ] `pytest tests/evaluation/test_retrieval_metrics.py -q`를 통과시켰다.
- [ ] API 키, 고객 데이터, 외부 서비스 없이 고정 실패 분석을 재현했다.
- [ ] 다음 장의 답변 정확도·환각·인용 평가로 검색 결과를 연결할 준비가 되었다.

## 14. 핵심 정리

검색 평가는 하나의 평균 점수가 아니라 고정 기준 위의 여러 관점입니다. Recall은 정답 회수, Precision은 후보의 밀도, Hit Rate는 최소 성공, MRR은 첫 정답의 빠르기, NDCG는 전체 순위 품질을 보여 줍니다. 사례별 회수 문서와 첫 정답 순위를 함께 기록하면 완전 누락과 늦은 정답을 분리해 개선할 수 있습니다. 모든 비교에는 동일한 데이터셋 버전과 `k`를 고정하고, 후보 수 변경의 지연·토큰·비용 효과는 별도로 검증해야 합니다.
