# 재계산된 JSON Checkpoint의 승인 감사 순서 검증

## 1. 학습 목표

- 위험 Action의 `approval_granted` Boolean만으로 실행 상태를 복원하면 안 되는 이유를 이해한다.
- JSON Checkpoint가 최초 승인 대기와 뒤이은 명시적 결정의 감사 순서를 함께 요구하게 한다.
- 이 구조 검증이 승인자 인증이나 변조 방지를 대체하지 않음을 구분한다.

## 2. 문제

이전 checksum·ActionKind 정책 검증은 위험 `DEPLOY`의 `approval_required=False` 같은 명백한 우회를 막습니다. 그러나 JSON을 쓸 수 있는 주체가 `approval_granted=True`, `status="completed"`, 결과와 checksum을 함께 다시 쓸 수 있다면 Boolean만 맞는 실행 완료 State처럼 보이게 만들 수 있습니다. `True` 필드가 실제 승인 경로를 지났다는 기록을 뜻하지는 않습니다.

## 3. 안전 계약

`JsonFileCheckpointer`는 위험 Action을 복원할 때 다음의 결정론적 감사 순서를 추가로 확인합니다.

- `WAITING_FOR_APPROVAL`에는 `<action> 작업은 사람 승인을 기다립니다.` 승인 대기 이벤트가 있어야 하고, 승인·거절 결정 이벤트가 있으면 안 된다.
- `READY`, `COMPLETED`, `ERROR`, `FAILED`의 `approval_granted=True`에는 대기 이벤트 뒤 `사람 승인을 받았습니다. 실행 시뮬레이션으로 이동합니다.` 이벤트가 있어야 한다.
- `REJECTED`의 `approval_granted=False`에는 대기 이벤트 뒤 `사람이 작업을 거절했습니다. 실행하지 않습니다.` 이벤트가 있어야 한다.
- 누락되거나 순서가 뒤집힌 기록은 checksum이 맞아도 State 복원 전에 `ValueError`로 fail-closed 한다.

## 4. 흐름

```text
JSON 읽기
  -> 중복 키 검사
  -> schema + checksum 검사
  -> State 구조 + ActionKind 승인 정책 검사
  -> 위험 Action 승인 대기/결정 감사 순서 검사
  -> 복원 또는 거부
```

## 5. 오프라인 실습

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_approval_audit_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 임시 JSON Checkpoint의 위험 `DEPLOY`를 `COMPLETED`, `approval_granted=True`와 결과로 바꾸고 checksum을 다시 계산합니다. 하지만 `plan` 이벤트만 남기며 승인 대기·결정 감사 이벤트를 만들지 않으므로 복원은 거부됩니다. 네트워크, API, 실제 배포·삭제·전송, 비밀값은 사용하지 않습니다.

## 6. 기대 결과

```text
approval_audit_bypass_rejected=checkpoint state has an invalid approval audit trail
```

거부는 `execute` Node를 호출하지 않습니다. 이 예제의 `COMPLETED` 표기는 변조된 JSON 값일 뿐 실제 작업의 성공이나 외부 부작용을 뜻하지 않습니다.

## 7. 구현 경계

검사는 `JsonFileCheckpointer`의 저장·복원 State 불변식 경계에 적용됩니다. 파일의 어느 run이라도 불완전한 위험 승인 이력을 가지면 전체 파일은 읽기 단계에서 거부되어 이후 저장으로 덮어쓰지 않습니다. `MemoryCheckpointer`는 신뢰된 프로세스 내 불변 State 전이만 보관하는 별도 학습용 경계입니다.

## 8. 승인 경계

위험 Action은 승인 대기 이벤트만으로 실행되지 않습니다. 별도 엄격한 Boolean 승인 결정이 감사 기록으로 남은 뒤에만 `READY`가 가능하며, 이 참조 모델의 `execute`도 외부 시스템을 변경하지 않는 결정론적 시뮬레이션입니다. 거절 기록은 `REJECTED`에서 끝나며 `execute`를 열지 않습니다.

## 9. checksum과 감사 문자열의 한계

SHA-256 checksum은 키가 없으므로 인증 코드가 아닙니다. 이 장의 감사 이벤트도 로컬 JSON의 일반 텍스트입니다. 쓰기 권한자가 checksum, Boolean, 이벤트를 모두 일관되게 다시 작성하는 공격을 막지 못합니다. 운영 환경은 서명된 불변 감사 저장소, 승인자 신원·권한·만료 검증, 접근 제어를 사용해야 합니다.

## 10. 동시성의 한계

이 검증은 단일 파일의 상태 의미를 다룹니다. JSON 경로 Lock과 CAS 보장은 같은 Python 프로세스의 같은 정규화 로컬 경로 스레드 범위에 한정됩니다. 여러 프로세스·호스트·네트워크 파일 시스템의 승인 경쟁에는 트랜잭션 저장소와 분산 멱등성 제어가 필요합니다.

## 11. 실패 처리

감사 순서가 맞지 않으면 추정으로 승인 이벤트를 추가하거나 State를 자동 수정하지 않습니다. 호출자는 오류를 조사하고 신뢰 가능한 입력으로 Checkpoint를 다시 생성해야 합니다. 복구 과정도 별도의 사람 승인 결정을 대체하지 않습니다.

## 12. 테스트 계약

회귀 테스트는 `DEPLOY`의 계획 Checkpoint를 승인된 완료 상태처럼 바꾸고 checksum을 다시 계산합니다. `approval_required=True`, `approval_granted=True`, 비어 있지 않은 결과가 있어도 승인 대기·승인 결정 이벤트가 없으면 `load()`가 `approval audit trail` 오류를 내는지 확인합니다.

## 13. 운영 전환 시 고려 사항

실제 시스템에는 승인 요청 ID, 승인자 정체성과 역할, 정책 버전, 만료 시간, 서명된 append-only 감사 이벤트, 외부 실행 권한 분리, 멱등성 키와 트랜잭션 경계가 필요합니다. 이 참조 모델은 그런 운영 제어를 구현하거나 검증하지 않습니다.

## 14. 핵심 정리

- 위험 완료 상태의 Boolean만 신뢰하지 않고 승인 대기·결정 감사 순서를 함께 검증한다.
- 재계산된 checksum은 누락된 승인 이력을 정당화하지 못한다.
- 검증은 오프라인·결정론적이며 실제 위험 작업을 수행하지 않는다.
