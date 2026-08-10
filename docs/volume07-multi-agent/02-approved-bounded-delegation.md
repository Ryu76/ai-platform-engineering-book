# 02. 승인 게이트가 있는 유한 위임

## 학습 목표

Coordinator가 제안하는 위임 계획과 실제 Worker 실행을 분리합니다. 이 장에서는 계획을 감사 가능한 유한 manifest로 남긴 뒤, 사람이 명시적으로 승인할 때만 Worker를 호출합니다. Worker 실패 재시도와 작업 수에도 상한을 두고, 상한 초과 시 아직 시작하지 않은 위임을 실행하지 않습니다.

## 안전 경계

- `DeterministicMockCoordinator`와 `DeterministicMockWorker`는 고정된 로컬 script만 소비합니다. 네트워크, 라이브 API, 환경 변수 또는 도구 실행이 없습니다.
- `DelegationPlan`은 비어 있지 않아야 하며 `max_tasks`를 넘을 수 없습니다. task ID 중복, 빈 지시문, allow-list 밖의 담당자는 Worker 호출 전에 거절됩니다.
- 기본 `DelegationApproval.PENDING` 실행은 Coordinator의 계획 메시지만 남기고 `awaiting_human_approval`에서 멈춥니다.
- Worker 호출은 `DelegationApproval.APPROVED` 뒤에만 가능합니다. `REJECTED`는 Coordinator와 모든 Worker 호출 전에 `human_rejected`로 종료합니다.
- 각 task는 `max_worker_attempts` 양의 정수만큼만 시도합니다. 모두 실패하면 `worker_retry_limit_reached`로 fail-closed하며 뒤 task를 dispatch하지 않습니다.
- Mock script가 소진되면 fallback하거나 반복하지 않고 `AgentProtocolError`를 발생시킵니다.

## 오프라인 실행

저장소 루트에서 승인 전 manifest만 확인합니다.

```bash
uv run python examples/volume07/offline_approved_delegation.py
```

첫 줄은 다음이며, `writer` 또는 `checker` Worker 메시지는 출력되지 않습니다.

```text
status=awaiting_human_approval
```

계획을 사람이 검토한 뒤에만 다음 명령으로 Worker 실행을 시연합니다.

```bash
uv run python examples/volume07/offline_approved_delegation.py --approve
```

승인된 로컬 Mock 실행의 마지막 Worker 메시지는 `checker`이고 완료 task ID는 `draft,verify`입니다.

## 검증

```bash
uv run pytest tests/volume07/test_approval_gated_delegation.py -q
```

테스트는 승인 대기 중 Worker 미호출, 명시 승인 후 manifest 순서 실행, 유한 재시도, 재시도 실패 뒤 task 미실행, 사람 거절, 안전하지 않은 manifest, script 소진을 네트워크 없이 검증합니다.

## 코드 읽기 순서

1. `DelegationTask`와 `DelegationPlan`으로 Coordinator가 제안할 수 있는 작업 표면을 확인합니다.
2. `ApprovalGatedDelegationWorkflow._validate_plan()`에서 task 수, 고유 ID, 담당자 allow-list를 실행 전에 검사하는 점을 확인합니다.
3. `run()`의 승인 대기 return이 Worker loop보다 앞에 있다는 점을 확인합니다.
4. 중첩된 Worker retry loop가 `max_worker_attempts`까지만 실행되고 실패 시 다음 manifest task를 실행하지 않는 점을 확인합니다.
5. `DelegationMessage`와 Worker `DelegationContext.messages`로 이전 계획과 시도 결과가 immutable audit trail로 전달되는 점을 확인합니다.

## 완료 기준

- [ ] 기본 오프라인 예제에서 manifest만 출력되고 Worker가 실행되지 않음을 확인했다.
- [ ] `--approve` 없이는 위임 Worker가 호출되지 않는 이유를 설명할 수 있다.
- [ ] 재시도 상한 뒤에 이후 task를 중단하는 fail-closed 동작을 설명할 수 있다.
- [ ] Volume 07 테스트를 실행했다.

다음 slice에서는 이 manifest와 audit trail을 바탕으로 충돌 해결 정책 및 장기 메모리의 명시적 범위를 확장합니다.
