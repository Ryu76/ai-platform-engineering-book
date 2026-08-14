# 재계산된 JSON Checkpoint도 승인 정책으로 검증하기

## 1. 학습 목표

- checksum이 맞는 JSON도 ActionKind별 승인 정책을 위반하면 복원하지 않는다.
- 위험 작업의 `READY`·`COMPLETED` 상태에는 명시적 승인 기록이 필요함을 확인한다.
- 이 검사가 인증이나 운영용 변조 방지를 대체하지 않음을 구분한다.

## 2. 문제

`payload_sha256`은 키 없는 SHA-256 checksum입니다. 따라서 우발적인 디스크 변경은 발견하지만, JSON을 수정할 수 있는 주체는 checksum도 다시 계산할 수 있습니다. checksum이 일치한다는 사실만으로 `DEPLOY`가 승인 없이 실행 가능한 상태가 되었다고 신뢰하면 안 됩니다.

## 3. 안전 계약

`JsonFileCheckpointer`는 checksum과 JSON 스키마를 확인한 다음 각 저장 State를 복원합니다. 복원 State는 다음 계약을 만족해야 합니다.

- `DELETE`, `DEPLOY`, `SEND`만 `approval_required=True`이다.
- 위험 작업의 `WAITING_FOR_APPROVAL`은 아직 결정이 없어야 한다.
- 위험 작업의 `READY`, `COMPLETED`, `ERROR`, `FAILED`는 `approval_granted=True`여야 한다.
- `REJECTED`는 위험 작업의 `approval_granted=False` 상태여야 하며 결과가 없어야 한다.
- `COMPLETED`만 비어 있지 않은 결과를 가질 수 있다.

위반하면 모든 State 복원 전에 `ValueError`로 fail-closed 합니다.

## 4. 흐름

```text
JSON 읽기
  -> 중복 키 검사
  -> schema + checksum 검사
  -> State 구조 검사
  -> ActionKind 승인 정책 불변식 검사
  -> 복원 또는 거부
```

## 5. 오프라인 실습

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_approval_policy_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 임시 파일에 `DEPLOY` Checkpoint를 만들고, `READY`·`approval_required=False`·`approval_granted=True`로 바꾼 뒤 checksum을 다시 계산합니다. 네트워크, API, 실제 배포, 파일 삭제, 비밀값은 사용하지 않습니다.

## 6. 기대 결과

```text
approval_policy_bypass_rejected=checkpoint state violates the action approval policy
```

이는 재계산된 checksum 자체가 승인 권한을 만들지 못함을 뜻합니다. `execute` Node는 호출되지 않습니다.

## 7. 구현 경계

검사는 JSON Checkpointer의 저장 및 복원 경계에 적용됩니다. 기존 Checkpoint 안의 어느 한 State라도 계약을 위반하면 후속 저장이 그 파일을 다시 쓰지 않도록 읽기 단계에서 거부합니다.

## 8. 승인 경계

위험 ActionKind는 이 검사를 통과하더라도 사람이 별도의 엄격한 Boolean 승인 결정을 기록하기 전에는 `WAITING_FOR_APPROVAL`에 머뭅니다. `COMPLETED`는 여전히 외부 부작용이 없는 결정론적 시뮬레이션입니다.

## 9. checksum의 한계

키 없는 checksum은 인증 코드가 아닙니다. 공격자를 포함한 쓰기 권한자가 checksum을 다시 계산하는 상황의 방어에는 서명, 접근 제어, 신뢰 가능한 감사 저장소가 필요합니다.

## 10. 동시성의 한계

이 장은 상태 의미 검증을 다룹니다. JSON 경로 Lock의 원자성 보장은 같은 Python 프로세스의 동일 정규화 경로 스레드에만 적용되며, 여러 프로세스·호스트·네트워크 파일 시스템에는 운영용 트랜잭션 저장소가 필요합니다.

## 11. 실패 처리

승인 정책 위반은 자동 수정하거나 안전 상태로 추정하지 않습니다. 호출자는 오류를 조사하고, 신뢰 가능한 입력으로 Checkpoint를 재생성해야 합니다.

## 12. 테스트 계약

회귀 테스트는 위험 `DEPLOY` State를 실행 가능해 보이도록 변조하고 checksum을 새로 계산한 뒤에도 `load()`가 `action approval policy` 오류로 거부하는지 확인합니다.

## 13. 운영 전환 시 고려 사항

실제 시스템에서는 승인자 신원, 권한, 만료, 서명된 감사 이벤트, 분산 멱등성 키와 트랜잭션 실행 권한을 별도로 설계해야 합니다. 이 참조 모델은 그런 운영 제어를 구현하지 않습니다.

## 14. 핵심 정리

- checksum 검증 뒤에도 State 의미를 검증한다.
- 위험 Action의 승인 필요 여부는 payload가 임의로 정하지 않는다.
- 이 예제는 오프라인·결정론적이며 실제 위험 작업을 수행하지 않는다.
