# 03. 유한 충돌 해결과 사람 승인

## 학습 목표

여러 Agent가 서로 다른 선택지를 제안할 때 Orchestrator가 임의로 승자를 고르지 않도록 설계합니다. 이 장의 예제는 역할별 제안을 감사 trail에 남기고, 정확히 같은 선택지에 도달한 경우에도 사람이 명시적으로 승인할 때만 `completed`가 되게 합니다. 합의하지 못하면 제한된 round 뒤에 안전하게 중단합니다.

## 안전 경계

- `DeterministicMockConflictAgent`는 고정된 로컬 proposal script만 소비합니다. 네트워크, 라이브 API, 환경 변수, 도구 실행, 장기 메모리 쓰기가 없습니다.
- Agent 수는 최소 둘이고 `max_agents`를 넘을 수 없습니다. 각 round에서 각 Agent는 한 번만 호출되므로 총 호출 수는 `max_rounds * max_agents` 이하입니다.
- 정책은 모든 Agent의 `ConflictProposal.option`이 정확히 일치할 때만 consensus recommendation을 만듭니다. 다르면 다수결, 신뢰도 추측, fallback 선택을 하지 않습니다.
- 기본 `ConflictApproval.PENDING`은 `awaiting_human_approval`에서 멈춥니다. consensus는 사람이 검토할 제안이며 자동 실행 권한이 아닙니다.
- `ConflictApproval.APPROVED`가 있을 때만 exact consensus가 `completed`가 됩니다. `REJECTED`는 모든 Agent 호출 전에 `human_rejected`로 종료합니다.
- 합의하지 못하면 `conflict_limit_reached`로 fail-closed합니다. 그 결과에는 선택된 option이 없으며, 상한 뒤의 Agent 호출도 없습니다.
- `objective`는 비어 있지 않은 문자열이어야 하며, 잘못된 입력은 어떤 Agent도 호출하지 않고 `WorkflowConfigurationError`로 중단합니다.
- 모든 Agent 출력은 `ConflictProposal`이어야 하고 option·근거는 비어 있지 않은 문자열이어야 합니다. 잘못된 출력, 빈 option·근거 또는 script 소진은 `AgentProtocolError`로 중단합니다. 다음 Agent, 다음 round, 외부 fallback으로 진행하지 않습니다.

## 오프라인 실행

저장소 루트에서 consensus recommendation만 확인합니다.

```bash
uv run python examples/volume07/offline_conflict_resolution.py
```

첫 줄은 다음입니다. `completed`가 아니므로 이 출력은 변경이나 후속 실행을 승인하지 않습니다.

```text
status=awaiting_human_approval
```

사람이 audit trail과 `consensus_option`을 검토한 뒤에만 다음 시연을 실행합니다.

```bash
uv run python examples/volume07/offline_conflict_resolution.py --approve
```

승인된 로컬 Mock 실행의 첫 줄은 `status=completed`입니다. 두 실행 모두 API 키나 라이브 서비스를 사용하지 않습니다.

## 검증

```bash
uv run pytest tests/volume07/test_bounded_conflict_resolution.py -q
```

테스트는 승인 대기, 명시 승인, 서로 다른 선택지에서의 round 상한, 사람 거절, 잘못된 objective·proposal 경계, script 소진을 네트워크 없이 검증합니다.

## 코드 읽기 순서

1. `ConflictProposal`과 `ConflictMessage`에서 선택지와 근거가 어떤 immutable 감사 기록으로 남는지 확인합니다.
2. `DeterministicMockConflictAgent`가 정해진 proposal 수만 소비하고 script 소진에서 중단하는 점을 확인합니다.
3. `BoundedConflictResolutionWorkflow.run()`의 이중 loop가 `max_rounds`와 `max_agents`로 호출 수를 제한하는 점을 확인합니다.
4. `len(options) != 1`일 때 자동 선택 없이 다음 제한된 round로만 진행하고, 상한 뒤 `conflict_limit_reached`를 반환하는 점을 확인합니다.
5. `ConflictApproval.PENDING`과 `ConflictApproval.APPROVED`의 분기가 recommendation과 completion을 분리하는 점을 확인합니다.

## 장기 메모리 범위

이 slice는 장기 메모리를 구현하거나 기록하지 않습니다. 과거 proposal을 자동으로 다음 objective에 주입하면 오래된 결정·민감 데이터·승인되지 않은 선택지가 재사용될 수 있기 때문입니다. 메모리를 도입하는 후속 설계에는 최소한 다음을 별도 경계로 둡니다.

- 명시적 write 승인과 목적별 retention 기간
- tenant·project·task 범위가 있는 read filter
- immutable audit ID와 원문/요약 구분
- human review 없이 action 권한이나 approval을 복원하지 않는 규칙

## 완료 기준

- [ ] 기본 오프라인 예제에서 `awaiting_human_approval`과 consensus audit trail을 확인했다.
- [ ] `--approve` 없이는 consensus가 `completed`가 되지 않는 이유를 설명할 수 있다.
- [ ] 서로 다른 option이 있을 때 다수결 fallback 대신 round 상한에서 멈추는 이유를 설명할 수 있다.
- [ ] Volume 07 테스트를 실행했다.
