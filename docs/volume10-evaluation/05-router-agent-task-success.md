# Router·Agent Task Success 평가

## 1. 학습 목표

이 장을 완료하면 다음을 할 수 있어야 합니다.

- Router의 선택 정확도와 Agent의 작업 성공률이 다른 실패를 측정함을 설명한다.
- 같은 버전의 골든 사례에 기대 라우트, 기대 응답, 필수 작업 ID를 추가해 평가 계약을 만든다.
- no-answer 사례가 `abstain` 라우트·응답을 사용하고 부수 작업을 수행하지 않는지 검증한다.
- 사례별 누락 작업과 예상 밖 작업을 확인해 평균 점수의 원인을 분리한다.
- 라이브 Router, Agent, 도구 호출 없이 고정 기록만으로 회귀 기준선을 재현한다.

## 2. 왜 필요한가

Router가 올바른 팀이나 도구를 선택해도 Agent가 필수 작업을 빠뜨리면 사용자의 목표는 달성되지 않습니다. 반대로 Agent가 우연히 필요한 작업을 완료했더라도 잘못된 라우트를 선택했다면 권한, 비용, 관측성, 정책 경계에서 위험 신호일 수 있습니다. 따라서 라우팅과 작업 성공을 하나의 점수로 합치지 않고 각각 관찰합니다.

이 장은 자연어 분류기나 실제 Agent를 실행하지 않습니다. 사람이 검토한 고정 사례와 기록된 선택·행동·작업 ID를 비교합니다. 입력이 같으면 결과도 같으므로 Router 프롬프트, 도구 정책, Agent 계획을 바꾸기 전후의 빠른 오프라인 회귀 기준선이 됩니다.

> [!WARNING]
> 고정 작업 ID는 교육용 계약이며 실제 계정 복구, 비용 제출, 보안 신고를 실행하지 않습니다. 고객 데이터, 도구 자격 증명, API 키, 외부 시스템, 라이브 LLM을 사용하지 않습니다. 운영 평가에서는 승인된 비식별 데이터와 별도의 권한·부작용 통제가 필요합니다.

## 3. 핵심 개념

- **Router Accuracy:** 모든 사례 중 `selected_route`가 `expected_route`와 일치한 비율입니다.
- **Agent Task Success Rate:** 기대 응답과 일치하고, 필수 작업을 모두 완료하며, 예상 밖 작업이 없는 사례 비율입니다.
- **필수 작업 ID:** 사람 검토로 정의한 최소 완료 조건입니다. 순서가 아니라 포함 여부를 비교하지만 결과에는 안정된 사례 순서로 남깁니다.
- **예상 밖 작업:** 해당 사례에 허용되지 않은 완료 작업입니다. 특히 no-answer 사례의 부수 작업은 성공으로 처리하지 않습니다.
- **no-answer 계약:** `abstain` 사례는 라우트도 `abstain`이어야 하고 필수 작업이 없어야 합니다. 기록된 보류 응답은 어떤 작업도 완료할 수 없습니다.
- **기록 워크플로:** 라이브 호출의 대체물인 `case_id`, `selected_route`, `response_mode`, `completed_task_ids`입니다.

`benefits-enrollment`는 `people` 라우트를 정확히 선택하지만 필수 작업을 하나도 완료하지 않아 Task Success에는 실패합니다. `office-parking`는 카탈로그에 없는 요청임에도 `facilities`로 보내고 주차권 발급 작업을 기록했으므로 Router와 Agent 양쪽에서 실패합니다. 이처럼 지표를 분리하면 무엇을 고칠지 알 수 있습니다.

## 4. 동작 구조

```text
버전 관리 GoldenDataset             고정 WorkflowCase / RecordedWorkflow
(case_id · answer/abstain)          (라우트 · 응답 · 필수/완료 작업 ID)
              │                                    │
              └────────────────┬───────────────────┘
                               ▼
                     입력 계약 검증
      (완전한 case_id · 중복 없는 작업 · no-answer 부수 작업 금지)
                               ▼
                  사례별 WorkflowCaseMetrics
     (라우트 일치 · 응답 일치 · 누락 작업 · 예상 밖 작업 · 성공)
                               ▼
             Router Accuracy · Agent Task Success Rate
                               ▼
                  고정 데이터셋 버전과 함께 회귀 비교

LLM API · Agent 도구 · Vector DB · 네트워크 · 시계 · 난수 ── 사용하지 않음
```

`evaluate_workflow_cases()`는 입력 사례 순서대로 진단 결과를 반환합니다. `evaluate_workflows()`는 같은 결과를 집계합니다. 일부 성공 사례만 제출해 점수를 높이지 못하도록 모든 고정 사례의 기록을 요구하며, 사전 키와 내부 `case_id`가 다르면 실패합니다.

## 5. 실습 환경

이 장에서 사용할 산출물은 다음과 같습니다.

- `src/ai_platform/evaluation/workflow_metrics.py`: Router·Agent 입력 계약과 결정론적 집계를 정의합니다.
- `src/ai_platform/evaluation/datasets.py`: 기존 골든 사례와 같은 ID의 기대 워크플로 및 의도적인 실패 기록을 정의합니다.
- `examples/volume10/workflow_quality.py`: 전체 기준선을 출력합니다.
- `tests/evaluation/test_workflow_metrics.py`: 기준 수치, 사례별 실패, 완전성, 모순 계약을 검사합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv sync --all-groups
```

환경 변수, API 키, 모델 서버, 네트워크 연결은 필요하지 않습니다. Windows Git Bash에서도 저장소 루트에서 같은 `uv` 명령을 실행할 수 있습니다.

## 6. 단계별 실습

### 6.1 고정 Router·Agent 기준선 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume10/workflow_quality.py
```

다섯 고정 사례의 Router 정확도와 Agent Task Success를 출력합니다. `benefits-enrollment`는 올바른 `people` 라우트지만 작업이 누락됩니다. `office-parking`는 `abstain` 대신 `facilities`로 보내고 주차권 발급을 기록합니다.

### 6.2 계약 테스트 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/evaluation/test_workflow_metrics.py -q
```

테스트는 기준 수치, 골든 데이터셋과의 동일한 사례 ID, 누락·예상 밖 작업, 누락 결과, 키/객체 ID 불일치, no-answer 모순을 검사합니다.

### 6.3 사례별 실패를 확인하는 방법

`evaluate_workflow_cases()`의 `missing_task_ids`와 `unexpected_task_ids`를 확인합니다. 기준선에서 `benefits-enrollment`는 `provide-enrollment-window-and-application-flow`가 누락됩니다. `office-parking`는 `issue-parking-pass`가 예상 밖 작업이고 응답도 기대한 보류와 다릅니다. 라우트 정답 여부와 작업 성공은 의도적으로 독립 필드입니다.

### 6.4 비교 조건 고정

Router 또는 Agent 후보를 비교할 때는 `volume10-support-policy@1.0.0`, 같은 사례 ID, 같은 라우트 목록, 같은 필수 작업 정의를 유지합니다. 사례·작업 라벨을 수정하면 데이터셋 버전과 변경 근거를 먼저 기록합니다. 다른 기준에서 나온 0.8 Router Accuracy는 직접 비교하지 않습니다.

## 7. 코드 설명

`WorkflowCase`는 기대 라우트, 응답 행동, 필수 작업을 고정합니다. `answer` 사례는 `abstain` 라우트를 쓸 수 없고 하나 이상의 필수 작업이 필요합니다. `abstain` 사례는 `abstain` 라우트와 빈 작업 목록만 가질 수 있습니다. 이 규칙은 관련 근거가 없는 질의에서 라우팅과 실행을 중단해야 한다는 정책을 계약으로 만듭니다.

`RecordedWorkflow`는 실제 도구 호출 결과 대신 검토 가능한 기록을 받습니다. 보류 기록에는 완료 작업을 넣을 수 없습니다. `evaluate_workflow_cases()`는 필수 작업에 없는 완료 ID를 예상 밖 작업으로, 완료 목록에 없는 필수 ID를 누락 작업으로 남깁니다. 응답이 일치하고 두 목록이 비어야 Task Success입니다.

`evaluate_workflows()`는 사례별 결과의 평균을 계산합니다. 기준선의 Router 정확도는 다섯 사례 중 네 개가 맞아 0.800000입니다. Agent Task Success는 앞의 세 사례만 성공해 0.600000입니다. 현재 Task Success는 필수 작업 기준의 엄격한 이진 지표이므로 작업의 순서, 자연어 품질, 지연 시간, 도구 반환값의 의미는 별도로 평가해야 합니다.

## 8. 정상 실행 결과

6.1 명령은 다음 출력을 포함해야 합니다.

```text
Evaluation cases: 5
Router accuracy: 0.800000
Agent task success rate: 0.600000
```

Router Accuracy가 0.8인 이유는 `office-parking`만 기대한 `abstain` 라우트와 다르기 때문입니다. Agent Task Success가 0.6인 이유는 `benefits-enrollment`의 필수 작업 누락과 `office-parking`의 잘못된 응답·예상 밖 작업 때문입니다.

6.2 pytest 명령은 실행 시간과 무관하게 `passed`로 끝나야 합니다. 값이 다르면 라이브 실행이나 기대값 변경으로 맞추지 말고, 데이터셋 버전, 라우트 라벨, 필수 작업, 기록 워크플로가 기준선과 일치하는지 확인합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `recorded workflows must match case ids` | 일부 결과가 빠졌거나 예상 밖 ID가 있다. | 모든 `WorkflowCase`에 정확히 하나의 기록을 제공한다. |
| `key and case_id must match` | 결과 사전 키와 내부 ID가 다르다. | 동일한 안정된 `case_id`를 키와 객체에 사용한다. |
| `answer cases must define at least one required task` | 답변 가능한 사례의 성공 기준이 비어 있다. | 검토 가능한 최소 작업 ID를 추가한다. |
| `abstain cases must use the abstain route` | no-answer 라벨과 라우트가 모순된다. | 보류 사례의 기대 라우트를 `abstain`으로 고정한다. |
| `abstain workflows must not complete tasks` | 보류하면서 도구 작업을 기록했다. | 부작용을 차단하고 완료 작업 목록을 비운다. |
| Router Accuracy는 높지만 Task Success가 낮다 | 올바른 담당으로 보냈지만 필수 작업을 누락했다. | 계획·도구 결과·완료 판정을 사례별 누락 작업과 함께 점검한다. |

## 10. 응용 실습

1. 고정 `answer` 사례에 필수 작업 두 개를 정의하고 하나가 빠진 기록이 실패하는 테스트를 작성합니다.
2. `office-parking` 기록을 올바른 `abstain` 라우트·응답과 빈 작업으로 바꿨다고 가정하고 두 지표의 새 분자와 분모를 계산합니다.
3. Router는 같고 필수 작업의 완료 순서만 다른 두 기록을 만들고, 이 구현이 순서를 평가하지 않는 이유를 설명합니다.
4. 실제 Agent 작업 평가의 완료 증거(도구 반환값, 승인 상태, 멱등성 키, 감사 로그)를 설계하되 실제 도구를 호출하지 않습니다.

## 11. 실무 적용

운영 평가에서는 각 라우트에 소유 팀·허용 도구·권한 범위·비용 한도를 연결하고, 각 작업 ID에 검증 가능한 완료 증거를 연결합니다. Task Success 판정에는 도구 호출 성공 코드만이 아니라 최종 상태, 사용자 승인, 취소·재시도·보상 처리, 부작용의 멱등성을 포함해야 합니다.

고위험 라우트는 false positive와 false negative를 별도 비용으로 보고, no-answer 또는 사람 승계가 올바른 결과일 수 있음을 라벨에 반영합니다. 회귀 리포트에는 코드 커밋, 골든 데이터셋 ID·버전, 사례 수, 라우트 혼동 행렬, 작업 누락/예상 밖 작업 ID, 정책 예외를 함께 남깁니다. 실사용 로그는 비식별화·최소 수집·보존 정책·접근 통제를 거친 승인 표본만 사용합니다.

## 12. 과제

- **기본:** Router Accuracy와 Agent Task Success를 하나의 점수로 합치지 않는 이유를 설명합니다.
- **응용:** `benefits-enrollment`의 라우트는 맞지만 작업이 실패한 원인을 사례별 필드로 설명합니다.
- **심화:** 실제 Agent 도구가 부분 성공·재시도·사람 승인·보상 작업을 가질 때의 Task Success 라벨 정책을 설계합니다. 부작용 격리, 감사 증거, 개인정보 보호, 데이터셋 버전, 실패 비용을 포함하며 라이브 API는 호출하지 않습니다.

## 13. 완료 체크리스트

- [ ] Router 선택과 Agent 작업 성공이 다른 실패를 측정함을 설명할 수 있다.
- [ ] `answer`와 `abstain`의 라우트·작업 계약을 구분할 수 있다.
- [ ] Router Accuracy와 Agent Task Success의 분자와 분모를 설명할 수 있다.
- [ ] `benefits-enrollment`의 누락 작업을 찾을 수 있다.
- [ ] `office-parking`의 no-answer 라우팅·행동·부수 작업 실패를 찾을 수 있다.
- [ ] `uv run python examples/volume10/workflow_quality.py`를 실행했다.
- [ ] `uv run pytest tests/evaluation/test_workflow_metrics.py -q`를 통과시켰다.
- [ ] API 키, 고객 데이터, 도구 실행, 외부 서비스 없이 기준선을 재현했다.
- [ ] 다음 장의 Latency·Token·Cost 측정으로 연결할 준비가 되었다.

## 14. 핵심 정리

Router가 올바른 곳을 선택하는 일과 Agent가 사용자의 작업을 안전하게 완료하는 일은 별개입니다. 고정 사례에 기대 라우트·응답·필수 작업을 명시하고 기록 워크플로와 비교하면, 잘못된 라우팅, 누락 작업, 예상 밖 작업, no-answer 위반을 재현 가능한 기준선에서 분리할 수 있습니다. 이 장의 이진 ID 계약은 빠른 회귀 차단에 유용하지만 자연어 품질, 실제 도구 상태, 시간·비용, 부분 성공을 충분히 평가하지는 않습니다. 다음 장에서 같은 고정 기록을 사용해 지연 시간, 토큰, 비용을 별도로 측정합니다.
