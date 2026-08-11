# 회귀 비교와 평가 리포트

## 1. 학습 목표

이 장을 완료하면 다음을 할 수 있어야 합니다.

- 같은 골든 데이터셋·버전·사례 순서에서만 기준선과 후보를 비교한다.
- 높을수록 좋은 품질 지표와 낮을수록 좋은 latency·비용 지표의 방향을 명시한다.
- 절대 허용 저하량과 회귀·개선·허용 범위 상태를 결정론적으로 판정한다.
- 비용·latency 개선이 품질 회귀를 상쇄하지 못하게 하는 승인 결정을 읽는다.
- 네트워크나 라이브 모델 없이 고정 후보 리포트를 재현한다.

## 2. 왜 필요한가

후보 프롬프트·검색·Router·Agent 변경은 한 지표를 개선하면서 다른 지표를 악화시킬 수 있습니다. 비용이 줄었다는 사실만으로 검색 Recall 하락을 승인하면 사용자 경험과 정답 근거를 잃을 수 있습니다. 따라서 동일한 평가 계약의 기준선과 후보를 한 리포트에 두고, 지표별 방향과 허용치를 먼저 고정합니다.

이 장의 `REJECT`는 배포를 수행하지 않는 교육용 판정입니다. 고정된 다섯 사례에서 `access-reset` 검색 정답이 사라져 Recall@3가 0.750000에서 0.500000으로 하락하므로, 다른 운영 지표의 개선과 무관하게 후보를 거부합니다.

## 3. 핵심 개념

- **EvaluationSnapshot:** 데이터셋 ID·버전, 안정된 사례 ID 순서, 이름 있는 수치 지표를 묶은 불변 스냅샷입니다.
- **RegressionPolicy:** 지표가 `higher_is_better`인지 `lower_is_better`인지와 절대 허용 저하량을 고정합니다.
- **delta:** `candidate - baseline`입니다. 양수·음수 자체에는 좋고 나쁨의 의미가 없으며 정책 방향과 함께 읽습니다.
- **deterioration:** 높은 값이 좋으면 `baseline - candidate`, 낮은 값이 좋으면 `candidate - baseline`입니다.
- **within_tolerance:** 저하가 허용치 이하인 상태입니다. 허용치 경계와 동일한 값은 통과합니다.
- **regression:** 저하가 허용치를 초과한 상태입니다. 하나라도 있으면 전체 후보는 승인되지 않습니다.

허용치는 비율로 환산하지 않는 원래 단위의 절대값입니다. Recall의 0.01 허용치는 `0.01`이고, 비용 100 micro USD 허용치는 `100`입니다. 이 실습의 정책은 모두 0이므로 어떤 저하도 허용하지 않습니다.

## 4. 동작 구조

```text
고정 기준선 결과                 고정 후보 결과
(같은 dataset/version/case IDs)   (같은 dataset/version/case IDs)
             │                              │
             └───────────────┬──────────────┘
                             ▼
          데이터셋·버전·사례 순서·지표 이름 완전 일치 검사
                             ▼
      방향·절대 허용 저하 정책별 delta / deterioration 계산
                             ▼
        improved · within_tolerance · regression 결과
                             ▼
      하나라도 regression이면 REJECT, 아니면 APPROVE

LLM API · Agent 도구 · Vector DB · 네트워크 · 라이브 시계 · 난수 ── 사용하지 않음
```

`compare_snapshots()`는 정책에 적힌 순서대로 결과를 반환합니다. 사례 ID를 집합으로만 비교하지 않고 순서도 비교하므로, 리포트의 사례 계약이 조용히 바뀌는 것을 막습니다. `NaN`, 무한대, 불리언 수치도 거부합니다.

## 5. 실습 환경

이 장에서 사용할 산출물은 다음과 같습니다.

- `src/ai_platform/evaluation/regression_report.py`: 스냅샷·정책·비교·거부 계약을 정의합니다.
- `src/ai_platform/evaluation/datasets.py`: 기존 고정 기준선과 의도적인 후보 회귀·개선 기록을 순수 함수로 계산합니다.
- `examples/volume10/regression_report.py`: 결정론적 리포트를 출력합니다.
- `tests/evaluation/test_regression_report.py`: 방향, 경계 허용치, 계약 불일치, 고정 후보 결정을 검사합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv sync --all-groups
```

환경 변수, API 키, 고객 데이터, 라이브 LLM·Router·Agent, 네트워크 연결은 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 고정 리포트 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume10/regression_report.py
```

기준선과 후보는 모두 `volume10-support-policy@1.0.0`의 같은 다섯 사례를 사용합니다. 후보는 Agent 작업 성공률, P95, 비용을 개선하지만 `access-reset` 정답 문서를 회수하지 않아 전체 결정은 `REJECT`입니다.

### 6.2 계약 테스트 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/evaluation/test_regression_report.py -q
```

테스트는 품질 저하가 비용 개선으로 상쇄되지 않는지, 허용치 경계가 승인되는지, 데이터셋 ID·버전·사례 순서·지표 집합·정책 집합 불일치를 거부하는지 검사합니다.

### 6.3 정책을 설계하는 방법

품질·안전 핵심 지표에는 0 허용치를 둘 수 있습니다. 측정 오차가 있는 운영 지표에 허용치를 쓸 경우, 단위와 근거를 명시합니다. 예를 들어 P95에 25ms를 허용한다면 `lower_is_better`, `allowed_degradation=25`라고 기록합니다. 기준선이나 데이터셋·가격 버전이 바뀌면 직접 비교하지 않고 별도 기준선을 승인합니다.

## 7. 코드 설명

`MetricValue`는 지표 이름과 유한 숫자만 받습니다. `EvaluationSnapshot`은 비어 있지 않고 중복 없는 사례·지표 ID를 요구합니다. `RegressionPolicy`는 유효한 방향과 0 이상 유한 허용치를 요구합니다.

`compare_snapshots()`는 먼저 dataset ID, dataset version, 사례 ID와 순서, 지표 ID가 완전히 같은지 확인합니다. 그 뒤 정책이 모든 지표를 정확히 한 번 다루는지 확인하고, 각 지표의 `delta`와 정책 방향의 `deterioration`을 계산합니다. 부동 소수 표현 때문에 경계값이 우연히 회귀가 되지 않도록 1e-12 수준의 비교 오차만 경계 동치로 처리합니다.

고정 예제의 다섯 정책은 검색 Recall@3, 답변 정확도, Agent Task Success Rate, P95 latency(ms), 총 cost(micro USD)입니다. 후보 Recall은 0.500000으로 0.250000 하락해 회귀입니다. 반면 Agent Task Success는 0.600000에서 0.800000, P95는 340에서 300ms, 비용은 5,240에서 5,080 micro USD로 개선됩니다.

## 8. 정상 실행 결과

6.1 명령은 다음 출력을 포함해야 합니다.

```text
Dataset: volume10-support-policy@1.0.0
Evaluation cases: 5
Decision: REJECT
retrieval.recall_at_3: baseline=0.750000; candidate=0.500000; delta=-0.250000; allowed_degradation=0.000000; status=regression
answer.answer_accuracy: baseline=0.800000; candidate=0.800000; delta=+0.000000; allowed_degradation=0.000000; status=within_tolerance
workflow.agent_task_success_rate: baseline=0.600000; candidate=0.800000; delta=+0.200000; allowed_degradation=0.000000; status=improved
usage.p95_latency_ms: baseline=340.000000; candidate=300.000000; delta=-40.000000; allowed_degradation=0.000000; status=improved
usage.total_cost_micro_usd: baseline=5240.000000; candidate=5080.000000; delta=-160.000000; allowed_degradation=0.000000; status=improved
```

`REJECT`는 지표 다섯 개 중 하나라도 회귀이기 때문입니다. 지표를 평균 내거나 비용 개선으로 Recall 저하를 보상하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `dataset ids must match` | 서로 다른 평가 데이터셋을 비교했다. | 동일한 dataset ID의 스냅샷만 비교한다. |
| `dataset versions must match` | 라벨·사례가 달라질 수 있는 버전을 섞었다. | 같은 버전만 직접 비교하고, 변경 시 새 기준선을 승인한다. |
| `case ids and order must match` | 일부 사례를 빼거나 순서를 바꿨다. | 동일한 전체 사례 ID와 안정된 순서를 사용한다. |
| `snapshot metric ids must match` | 후보에 지표가 빠졌거나 예상 밖 지표가 있다. | 기준선·후보에 같은 완전한 지표 집합을 기록한다. |
| `regression policies must match` | 정책이 일부 지표를 빠뜨리거나 중복했다. | 모든 지표에 하나의 방향·허용치 정책을 둔다. |
| `Decision: REJECT` | 허용치를 초과한 회귀가 하나 이상 있다. | 실패 사례와 후보 변경을 조사하고, 숫자를 숨기거나 배포하지 않는다. |

## 10. 응용 실습

1. `answer.answer_accuracy`에 0.05의 허용 저하를 두었을 때 승인 경계가 어떻게 변하는지 단위와 함께 테스트로 고정합니다.
2. `usage.total_cost_micro_usd`에만 100 micro USD 허용치를 설계하고, 품질 지표와 다른 방향임을 설명합니다.
3. 여섯 번째 고정 사례를 추가한다고 가정하고 새 데이터셋 버전이 이전 버전과 직접 비교되면 안 되는 이유를 설명합니다.
4. 실패 지표에 사례별 원인 링크와 담당 검토자를 연결하는 리포트 스키마를 설계하되 실제 티켓·API는 호출하지 않습니다.

## 11. 실무 적용

운영 리포트에는 코드 커밋, 데이터셋 ID·버전, 라벨 승인 기록, 사례 수, 프롬프트·모델·인덱스·가격 버전, 측정 시점의 환경 정의를 함께 보관합니다. 변경이 다른 평가 계약을 만들면 독립된 기준선을 만들고 사람이 비교 가능성을 검토합니다.

승인 정책은 단일 평균 점수보다 안전·정확도·보류·인용·작업 성공·latency 분포·비용을 분리해야 합니다. 임계값 근처나 사례 수가 작은 결과는 자동 배포가 아니라 사람 검토로 보내고, 실패 사례를 숨기지 않습니다. 이 예제는 배포·알림·외부 전송을 수행하지 않습니다.

## 12. 과제

- **기본:** 높은 값이 좋은 Recall과 낮은 값이 좋은 P95에 서로 다른 deterioration 공식을 적용하는 이유를 설명합니다.
- **응용:** 절대 허용치 0.01 Recall과 25ms P95의 의미·한계를 비교합니다.
- **심화:** 실제 CI에서 평가 스냅샷, 라벨·가격 버전, 사람 승인, 비밀값 마스킹, 롤백 기준을 포함한 회귀 게이트를 설계합니다. 외부 서비스·라이브 API 호출은 포함하지 않습니다.

## 13. 완료 체크리스트

- [ ] 같은 dataset ID·version·사례 순서가 비교 전제임을 설명할 수 있다.
- [ ] higher/lower 방향과 원래 단위의 절대 허용 저하량을 구분할 수 있다.
- [ ] 하나의 품질 회귀가 비용·latency 개선으로 상쇄되지 않음을 설명할 수 있다.
- [ ] `uv run python examples/volume10/regression_report.py`를 실행했다.
- [ ] `uv run pytest tests/evaluation/test_regression_report.py -q`를 통과시켰다.
- [ ] API 키, 고객 데이터, 외부 서비스, 라이브 시계 없이 고정 리포트를 재현했다.
- [ ] 다음 장의 오프라인 평가 파이프라인으로 연결할 준비가 되었다.

## 14. 핵심 정리

회귀 리포트는 같은 평가 계약의 기준선과 후보를 정책 방향·허용치와 함께 비교합니다. 사례·버전·지표 집합을 완전하게 고정하고, 하나라도 허용치를 초과한 회귀가 있으면 후보를 거부하면 비용이나 latency 개선에 품질 하락이 가려지지 않습니다. 이 장의 결과는 다섯 고정 사례의 교육용 결정이며 실제 배포 판단에는 더 큰 검토된 데이터셋, 운영 계측, 보안·개인정보 정책, 사람 승인이 필요합니다.
