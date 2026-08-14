# 미니 프로젝트: 오프라인 평가 파이프라인

## 1. 학습 목표

이 미니 프로젝트를 완료하면 하나의 버전 관리 골든 계약에서 검색, 답변, Router·Agent, 사용량을 함께 실행하고 기준선·후보 회귀 결정을 재현할 수 있습니다.

## 2. 왜 필요한가

각 지표를 따로 실행하면 일부 사례를 빼거나 다른 데이터셋 버전을 섞을 수 있습니다. 파이프라인은 전체 사례 계약과 no-answer 분리를 먼저 확인한 뒤 모든 순수 지표를 실행해 이런 비교 오류를 줄입니다.

## 3. 핵심 개념

- **OfflineEvaluationInput:** 데이터셋 ID·버전·안정된 사례 순서와 모든 고정 입력을 묶습니다.
- **OfflineEvaluationRun:** 검색, 답변, 워크플로, 사용량의 집계 결과입니다.
- **회귀 스냅샷:** 현재 승인 게이트가 비교하는 다섯 지표만 같은 사례 계약으로 추출합니다.
- **텍스트 리포트:** 기준선과 후보의 지표, 회귀 상태, 최종 결정을 안정된 줄 순서로 제공합니다.

## 4. 동작 구조

```text
고정 골든 사례·기록 결과
        │
        ├── 검색 (answer 사례만) ── Recall@3
        ├── 답변 (전체 5 사례) ── 정확도·보류·환각·인용
        ├── Workflow (전체 5 사례) ── Router·Task Success
        └── Usage (전체 5 사례) ── latency·token·cost
        │
        ▼
기준선/후보 OfflineEvaluationRun → 동일 계약 회귀 게이트 → 텍스트 리포트

LLM API · Agent 도구 · Vector DB · 네트워크 · 라이브 시계 · 난수 ── 사용하지 않음
```

## 5. 실습 환경

저장소 루트에서 Python과 프로젝트 의존성을 사용합니다. 산출물은 `src/ai_platform/evaluation/offline_pipeline.py`, `examples/volume10/offline_evaluation_pipeline.py`, `tests/evaluation/test_offline_pipeline.py`입니다. API 키, 고객 데이터, 네트워크는 필요하지 않습니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
conda env update --file environment.yml --prune
```

이 명령은 잠긴 로컬 개발 의존성을 준비합니다.

## 6. 단계별 실습

### 6.1 전체 고정 파이프라인 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
python examples/volume10/offline_evaluation_pipeline.py
```

명령은 `volume10-support-policy@1.0.0`의 고정 다섯 사례를 기준선과 후보에 모두 사용합니다. 검색은 네 개의 answer 사례만 평가하므로 no-answer `office-parking`이 Recall 분모에 들어가지 않습니다.

### 6.2 계약 테스트 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/evaluation/test_offline_pipeline.py -q
```

테스트는 고정 수치, 출력 순서, 후보 회귀 거부, 전체 사례 순서, 검색 부분집합과 보고서 계약을 검사합니다.

## 7. 코드 설명

`OfflineEvaluationInput`은 answer·workflow·usage가 전체 사례 ID와 순서를 정확히 공유하게 합니다. retrieval은 no-answer와 분리해야 하므로 전체 사례의 중복 없는 부분집합만 허용합니다.

`run_offline_evaluation()`은 기존의 순수 평가 함수를 호출하고 `OfflineEvaluationRun`으로 묶습니다. `regression_snapshot()`은 Recall@3, 답변 정확도, Agent Task Success, P95 latency, 총 비용을 회귀 정책 순서와 같은 이름으로 제공합니다.

`format_offline_evaluation_report()`는 파일을 쓰거나 외부로 전송하지 않습니다. 세 입력이 동일한 dataset ID·version·사례 수를 가리킬 때만 결정론적 텍스트를 반환합니다.

## 8. 정상 실행 결과

6.1 명령은 다음 출력을 포함해야 합니다.

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
  Answer accuracy: 0.800000
  Router accuracy: 0.800000
  Agent task success rate: 0.800000
  P95 latency (ms): 300
  Total tokens: 1220
  Total cost (USD): 0.005080
Regression decision: REJECT
retrieval.recall_at_3: status=regression; delta=-0.250000
```

후보의 작업 성공·P95·비용은 개선되지만 Recall@3 하락이 있으므로 최종 결정은 `REJECT`입니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `answer case ids and order must match case ids` | 전체 답변 사례의 누락 또는 순서 변경 | 골든 데이터셋의 전체 사례 ID·순서를 사용합니다. |
| `retrieval case ids must be a subset of case ids` | 검색 입력에 알려지지 않은 사례가 있다. | 같은 데이터셋의 answer 사례만 사용합니다. |
| `ranked results must match case ids` | 검색 결과 키가 검색 사례와 다르다. | 각 retrieval 사례에 정확히 하나의 순위 결과를 기록합니다. |
| `report dataset versions must match` | 기준선·후보·회귀 리포트 버전을 섞었다. | 같은 라벨 버전만 직접 비교합니다. |
| `Regression decision: REJECT` | 허용치를 넘는 회귀가 있다. | 실패 사례와 변경을 분석하고 수치를 숨기지 않습니다. |

## 10. 응용 실습

1. 새 answer 사례를 추가한다고 가정하고 데이터셋 버전을 올린 뒤 이전 스냅샷과 직접 비교하지 않는 테스트를 작성합니다.
2. 후보 답변 기록의 인용을 수정하고 답변·인용 지표와 회귀 정책을 어떻게 구분할지 설계합니다.
3. JSON 직렬화 리포트를 추가하되 필드 순서, 단위, 데이터셋 버전을 테스트로 고정합니다.
4. 사람이 검토할 사례별 실패 링크를 모델·고객 데이터 없이 리포트 스키마에 추가합니다.

## 11. 실무 적용

운영에서는 평가 입력과 출력에 코드 커밋, 프롬프트·모델·인덱스·가격 버전, 라벨 승인 기록을 연결합니다. 데이터셋이 바뀌면 새 기준선을 승인하고, 작은 표본 또는 임계값 근처 결과는 사람이 검토합니다. 이 교육용 파이프라인은 배포, 알림, 라이브 모델 호출을 하지 않습니다.

## 12. 과제

- **기본:** retrieval만 전체 사례의 부분집합인 이유와 no-answer 분리 원칙을 설명합니다.
- **응용:** P95 25ms 허용치와 Recall@3 0 허용치를 다른 단위로 정책화합니다.
- **심화:** CI에서 고정 스냅샷, 사람 승인, 실패 사례 보존, 비밀값 마스킹, 롤백 기준을 포함한 평가 단계를 설계합니다. 외부 API 호출은 포함하지 않습니다.

## 13. 완료 체크리스트

- [ ] 전체 answer·workflow·usage 사례가 같은 ID·순서를 공유함을 확인했다.
- [ ] no-answer를 검색 Recall 분모에서 분리했다.
- [ ] `python examples/volume10/offline_evaluation_pipeline.py`를 실행했다.
- [ ] `pytest tests/evaluation/test_offline_pipeline.py -q`를 통과시켰다.
- [ ] 비용·latency 개선이 Recall 회귀를 상쇄하지 않음을 확인했다.
- [ ] API 키, 고객 데이터, 외부 서비스, 라이브 시계 없이 리포트를 재현했다.

## 14. 핵심 정리

오프라인 평가 파이프라인은 하나의 고정 골든 계약에서 모든 평가 영역을 함께 실행합니다. 전체 사례 계약을 보호하면서 no-answer를 검색 품질에서 분리하고, 동일한 기준선·후보의 회귀 지표를 비교해야 재현 가능한 품질 결정을 만들 수 있습니다.
