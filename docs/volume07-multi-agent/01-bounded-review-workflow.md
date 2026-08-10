# 01. 결정론적 다중 에이전트 검토 워크플로

## 학습 목표

Planner, Researcher, Developer, Reviewer, QA를 하나의 자동 권한으로 취급하지 않습니다. 이 장의 예제는 각 역할의 메시지를 남기고, Reviewer 재작업을 유한하게 제한하며, QA 전에는 반드시 명시적 사람 승인을 요구합니다.

## 안전 경계

- `DeterministicMockAgent`는 고정된 응답만 반환합니다. 네트워크, API 키, 라이브 도구 호출이 없습니다.
- `max_review_cycles`는 양의 정수여야 합니다. Reviewer가 계속 `revise`를 반환해도 무한 반복하지 않습니다.
- Reviewer의 `approve`는 배포나 QA 승인이 아닙니다. 기본 실행은 `awaiting_human_approval`에서 멈춥니다.
- 사람 승인은 코드 안의 암묵적 기본값이 아닙니다. `HumanApproval.APPROVED` 또는 예제의 `--approve`가 있어야 QA가 실행됩니다.
- 사람 거절은 역할을 호출하기 전에 `human_rejected`로 종료합니다.

## 오프라인 실행

저장소 루트에서 다음을 실행합니다.

```bash
uv run python examples/volume07/offline_review_workflow.py
```

예상되는 첫 줄은 다음이며 QA 메시지는 출력되지 않습니다.

```text
status=awaiting_human_approval
```

검토 결과를 사람이 확인하고 QA 진행을 명시적으로 승인하는 시연만 다음 명령으로 실행합니다.

```bash
uv run python examples/volume07/offline_review_workflow.py --approve
```

이 실행도 고정 Mock만 사용하며, 출력의 마지막 역할은 `qa`입니다.

## 검증

```bash
uv run pytest tests/volume07/test_bounded_review_workflow.py -q
```

테스트는 승인 대기, 명시 승인 후 QA, 재작업 한도, 사람 거절의 fail-closed 동작, Reviewer 결정 누락을 네트워크 없이 검증합니다.

## 코드 읽기 순서

1. `src/ai_platform/agents/workflow.py`의 `AgentContext`, `AgentMessage`로 역할별 입력·출력 감사 경계를 확인합니다.
2. `DeterministicMockAgent`가 스크립트 소진 시 실패하여 예기치 않은 추가 작업을 숨기지 않는다는 점을 확인합니다.
3. `BoundedReviewWorkflow.run()`에서 Planner와 Researcher는 한 번만, Developer와 Reviewer는 최대 `max_review_cycles`만 호출됨을 확인합니다.
4. QA 호출이 `HumanApproval.APPROVED` 뒤에만 있다는 점을 확인합니다.

## 완료 기준

- [ ] 기본 오프라인 예제를 실행해 `awaiting_human_approval`을 확인했다.
- [ ] `--approve`가 없는 실행에서 QA가 호출되지 않음을 설명할 수 있다.
- [ ] 재작업 상한이 무한 loop를 막는 이유를 설명할 수 있다.
- [ ] Volume 07 테스트를 실행했다.

다음 장에서는 이 감사 가능한 메시지 경계를 바탕으로 역할별 상태와 위임 정책을 확장합니다.
