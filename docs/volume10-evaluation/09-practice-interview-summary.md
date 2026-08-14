# 문제 해결·과제·면접 질문·요약·완료 체크리스트

## 1. 학습 목표

이 장을 완료하면 Volume 10의 고정 골든 데이터셋, 검색·답변·워크플로·사용량 지표, 회귀 게이트를 하나의 재현 가능한 평가 흐름으로 설명하고 검증할 수 있습니다. 또한 실패 원인을 지표별로 분리하고, 데이터셋·기준선·후보 비교의 경계를 실무 면접과 과제에서 명확하게 설명할 수 있습니다.

## 2. 왜 필요한가

평가 결과 하나만 좋다고 시스템이 안전하거나 유용하다고 결론 내릴 수는 없습니다. Recall 개선은 환각, 보류 실패, 잘못된 Router 선택, 작업 누락, 지연 시간 또는 비용을 감출 수 있습니다. 반대로 비용이나 P95 개선도 품질 회귀를 상쇄하지 않습니다. 마지막 점검은 같은 버전의 전체 사례와 명시적인 정책으로 각 결론을 다시 연결합니다.

## 3. 핵심 개념

- **고정 골든 계약:** dataset ID, semantic version, 사례 ID 순서, 라벨 근거를 함께 고정한 재현 단위입니다.
- **분모 분리:** `abstain` no-answer 사례는 답변 보류 평가에는 포함하지만 검색 Recall 분모에는 포함하지 않습니다.
- **사례별 진단:** 평균 지표 아래의 완전 누락, 늦은 정답, 지원되지 않은 주장, 잘못된 route, 누락 작업을 확인합니다.
- **회귀 게이트:** 동일 dataset·version·사례 계약의 기준선과 후보를 방향 및 허용 저하 정책으로 비교합니다.
- **결정론적 증거:** 고정 입력과 순수 함수의 출력은 네트워크, 라이브 모델, 시계, 난수 없이 다시 실행할 수 있습니다.

## 4. 동작 구조

```text
versioned golden dataset (5 cases)
        │
        ├── answer cases only (4) ── retrieval metrics
        └── all cases (5) ───────── answer / workflow / usage metrics
        │
        ▼
baseline snapshot + candidate snapshot
        │
        ▼
per-metric policy ── any regression? ──> REJECT

LLM API · Agent 도구 · Vector DB · 네트워크 · 라이브 시계 · 난수 ── 사용하지 않음
```

`office-parking`은 no-answer 사례이므로 전체 답변·워크플로·사용량 계약에는 남지만 검색 Recall의 분모에는 들어가지 않습니다.

## 5. 실습 환경

저장소 루트에서 잠긴 Python 개발 의존성을 사용합니다. 이 장의 재현 경로는 `examples/volume10/offline_evaluation_pipeline.py`, `tests/evaluation/`, `src/ai_platform/evaluation/`의 공개 고정 데이터와 순수 계산만 사용합니다. API 키, 비밀값, 고객 데이터, 배포 권한, 네트워크 연결은 필요하지 않습니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
conda env update --file environment.yml --prune
```

## 6. 단계별 실습

### 6.1 최종 오프라인 리포트 재현

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
python examples/volume10/offline_evaluation_pipeline.py
```

기준선은 Recall@3 `0.750000`, 답변 정확도 `0.800000`, Router 정확도 `0.800000`, Agent 작업 성공률 `0.600000`, P95 `340ms`, 총 비용 `0.005240 USD`를 출력합니다. 후보는 Agent 작업·P95·비용이 좋아져도 Recall@3가 `0.500000`으로 하락하므로 거부됩니다.

### 6.2 Volume 10 계약 테스트 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/evaluation -q
```

테스트는 고정 데이터셋, 각 지표의 수치와 입력 경계, no-answer 분리, 기준선·후보 회귀 거부, 리포트 순서, 모든 장의 실제 산출물 연결을 검사합니다.

### 6.3 문제 해결: 회귀 원인 읽기

다음 순서로 후보 거부를 분석합니다.

1. `retrieval.recall_at_3`의 delta가 `-0.250000`인지 확인합니다.
2. `benefits-enrollment`처럼 정답 문서가 Top-3에 없는 사례와 `expense-receipt`처럼 늦게 회수된 사례를 사례별 검색 분석에서 구분합니다.
3. Agent 작업 성공률·P95·비용 개선을 기록하되, Recall 허용 저하가 0인 정책과 혼합해 평균내지 않습니다.
4. 같은 dataset ID, version, 전체 사례 순서가 유지된 후보만 다시 비교합니다.

## 7. 코드 설명

`GoldenDataset`과 `FIXED_GOLDEN_DATASET`은 라벨·출처·기대 동작을 버전과 함께 고정합니다. `evaluate_retrieval()`은 answer 사례만 받아 Recall·Precision·Hit Rate·MRR·NDCG를 계산합니다. `evaluate_answers()`, `evaluate_workflows()`, `evaluate_usage()`는 전체 다섯 사례를 각각의 계약으로 평가합니다.

`OfflineEvaluationInput`은 answer·workflow·usage 사례 ID와 순서가 전체 계약과 같도록 검증하고, retrieval 사례는 그 부분집합만 허용합니다. `OfflineEvaluationRun.regression_snapshot()`은 동일 계약의 Recall@3, 답변 정확도, Agent Task Success, P95, 비용을 꺼냅니다. `compare_snapshots()`는 한 지표라도 정책을 넘겨 회귀하면 `REJECT`를 반환합니다.

## 8. 정상 실행 결과

6.1 명령은 다음 핵심 줄을 포함해야 합니다.

```text
Dataset: volume10-support-policy@1.0.0
Evaluation cases: 5
Retrieval cases: 4
Baseline:
  Recall@3: 0.750000
  Answer accuracy: 0.800000
  Router accuracy: 0.800000
  Agent task success rate: 0.600000
  P95 latency (ms): 340
  Total tokens: 1240
  Total cost (USD): 0.005240
Candidate:
  Recall@3: 0.500000
Regression decision: REJECT
retrieval.recall_at_3: status=regression; delta=-0.250000
```

6.2 명령은 전체 `tests/evaluation` 스위트가 통과했다고 보고해야 합니다. 테스트 수는 향후 Volume 10 범위 안에서 추가될 수 있으므로, 특정 개수보다 `passed`와 실패 없음이 정상 조건입니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `retrieval case ids must be a subset of case ids` | 검색에 골든 계약 밖의 사례를 넣었다. | 같은 버전의 answer 사례만 검색 입력에 넣습니다. |
| `answer case ids and order must match case ids` | 전체 사례를 빼거나 순서를 바꾸었다. | answer·workflow·usage에 완전한 사례 ID·순서를 사용합니다. |
| `recorded answers must cover exactly the case ids` | 기록 답변 키가 전체 라벨과 다르다. | 누락·추가 키를 제거하고 각 사례에 하나의 기록을 둡니다. |
| `report dataset versions must match` | 기준선·후보·리포트의 version을 섞었다. | 같은 데이터셋 version만 직접 비교합니다. |
| `Regression decision: REJECT` | 하나 이상의 품질 또는 비용 정책이 회귀다. | 실패 지표와 사례를 분석하고 정책·기준선을 숨기지 않습니다. |

## 10. 응용 실습

1. `office-parking`과 같은 no-answer 사례를 하나 더 설계하고, retrieval 입력에는 넣지 않되 보류 정확도 계약에는 넣는 테스트를 작성합니다.
2. `benefits-enrollment`의 Top-3 누락을 수정한 후보를 가정하고 Recall 개선과 비용 증가를 서로 다른 허용치로 정책화합니다.
3. 사람 검토 대기 사례를 표현하는 고정 메타데이터를 설계합니다. PII·원문 고객 데이터·외부 judge 호출 없이 라벨 근거 ID만 유지합니다.
4. JSON 리포트를 추가한다면 dataset ID·version·사례 순서·단위·정렬된 metric ID를 고정하는 테스트를 작성합니다.

## 11. 실무 적용

실무에서는 평가 스냅샷에 코드 커밋, 프롬프트, 모델, 인덱스, 가격표, 라벨 승인 기록의 버전을 연결합니다. 골든 데이터셋이 바뀌면 semantic version을 올리고 새 기준선을 사람이 승인합니다. 낮은 표본 수, 임계값 근처 변화, 지원 근거가 불명확한 답변은 사람 검토 큐로 분리합니다.

이 권의 고정 데이터는 운영 품질의 대체물이 아닙니다. 실제 운영 도입에는 익명화된 승인 데이터, 접근 제어, 변경 승인, 실패 사례 보존, 롤백 기준, CI의 오프라인 게이트가 필요합니다. 그 과정에서도 API 키를 리포트에 넣거나, 고객 데이터를 예제·테스트에 복사하거나, 라이브 서비스에 시험 요청을 보내서는 안 됩니다.

## 12. 과제

- **문제 해결:** 후보의 Recall@3가 하락했는데 Agent Task Success가 올랐을 때 왜 `REJECT`인지, 정책과 사례별 증거를 사용해 설명합니다.
- **기본 과제:** Recall@k와 answer accuracy의 분모가 다른 이유, 특히 no-answer 사례의 위치를 표로 작성합니다.
- **응용 과제:** latency·token·cost의 단위와 P95 nearest-rank 계산이 평균 latency만 보는 것보다 유용한 상황을 설명합니다.
- **심화 과제:** 데이터셋 version 변경, 사람 승인, 회귀 정책, 비밀값 마스킹, 롤백을 포함하는 오프라인 CI 설계를 작성합니다. 라이브 API 호출은 포함하지 않습니다.

### 면접 질문

1. Recall@k, MRR, NDCG가 각각 어떤 검색 실패를 더 잘 드러내나요?
2. no-answer 사례를 검색 Recall에 섞으면 어떤 잘못된 결론이 생기나요?
3. answer accuracy, hallucination rate, citation accuracy를 하나의 수치로 합치지 않는 이유는 무엇인가요?
4. Router accuracy와 Agent Task Success를 분리해야 하는 실제 실패 예는 무엇인가요?
5. P95를 평균 latency와 함께 보는 이유와 nearest-rank의 장점은 무엇인가요?
6. 기준선과 후보가 같은 dataset version과 사례 순서를 공유해야 하는 이유는 무엇인가요?
7. 비용 개선이 품질 회귀를 상쇄할 수 있는지, 정책을 어떻게 명시하겠습니까?
8. 고정 오프라인 평가는 어떤 한계를 가지며 사람 검토는 어디에 추가하겠습니까?

## 13. 완료 체크리스트

- [x] 공개 가능한 고정 골든 데이터셋에 dataset ID, version, 고유 사례 ID, 라벨 근거, no-answer를 기록했다.
- [x] answer 사례만으로 Recall·Precision·Hit Rate·MRR·NDCG를 계산하고 no-answer를 검색 분모에서 분리했다.
- [x] 답변 정확도·보류 정확도·환각률·인용 정확도를 고정 기록으로 계산했다.
- [x] Router 정확도와 Agent Task Success를 별도 고정 기록으로 계산했다.
- [x] latency·token·cost와 nearest-rank P95를 고정 단위로 계산했다.
- [x] 동일 dataset·version·사례 계약의 기준선과 후보를 회귀 정책으로 비교했다.
- [x] 품질 회귀가 하나라도 있으면 다른 개선과 상관없이 `REJECT`되는 것을 검증했다.
- [x] 전체 파이프라인 예제와 Volume 10 테스트를 API 키·네트워크·라이브 서비스 없이 재현했다.
- [x] 문제 해결, 과제, 면접 질문, 핵심 정리, 오류 해결을 문서화했다.

## 14. 핵심 정리

신뢰할 수 있는 평가는 좋은 평균 하나가 아니라, 버전 관리되는 고정 라벨·명시적인 분모·사례별 진단·독립 지표·동일 계약의 회귀 정책으로 구성됩니다. Volume 10의 오프라인 파이프라인은 no-answer를 검색 Recall에서 분리한 상태로 검색, 답변, Router·Agent, 사용량을 재현 가능하게 측정합니다. 후보는 비용이나 속도가 개선되어도 정해진 품질 정책을 넘겨 회귀하면 거부해야 합니다.
