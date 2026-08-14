# 거절된 JSON Checkpoint의 execute 감사 이벤트 차단

## 1. 학습 목표

- 위험 Action의 거절 State가 `execute` 경로를 열지 않는다는 의미를 이해한다.
- 정상 승인 대기·거절 감사 이력과 재계산 checksum만으로는 위조 실행 기록을 정당화할 수 없음을 확인한다.
- 이 구조 검증과 실제 실행 증명·승인자 인증을 구분한다.

## 2. 문제

`REJECTED` State는 결과가 없고 실행하지 않은 종료를 뜻합니다. 그러나 JSON을 수정할 수 있는 주체는 정상 `대기 -> 거절` 승인 이벤트를 남긴 후 `execute` 이벤트를 덧붙이고 checksum을 다시 계산할 수 있습니다. 승인 감사 순서만 검사하면 이 모순된 감사 로그는 복원될 수 있으며, 감사 소비자는 거절 뒤 실행이 일어났다고 잘못 해석할 수 있습니다.

## 3. 안전 계약

`JsonFileCheckpointer`는 위험 Action의 `REJECTED` State에 `node="execute"` 이벤트가 하나라도 있으면 거부합니다.

- 정상 거절은 `대기 -> 거절` approval 이벤트로 끝난다.
- 거절 State는 결과가 없고 `execute` 감사 이벤트도 없다.
- 거절 뒤에 덧붙인 `execute` 이벤트는 checksum이 맞아도 복원 전에 fail-closed 한다.
- 이 계약은 실제 외부 실행을 수행하거나 증명하지 않는 오프라인 참조 모델의 상태 의미 검증이다.

## 4. 흐름

```text
JSON 읽기
  -> 중복 키 검사
  -> schema + checksum 검사
  -> ActionKind 승인 정책 + 정확한 approval 전이 검사
  -> REJECTED 상태의 execute 감사 이벤트 부재 검사
  -> 복원 또는 거부
```

## 5. 오프라인 실습

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_rejected_execute_audit_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 임시 JSON Checkpoint에 정상 위험 `DEPLOY` 거절을 기록한 뒤 execute 이벤트를 추가하고 SHA-256 checksum을 다시 계산합니다. 네트워크, API, 실제 배포·삭제·전송, 비밀값은 사용하지 않습니다.

## 6. 기대 결과

```text
rejected_execute_audit_rejected=checkpoint rejected state must not contain an execute audit event
```

거부는 `execute` Node를 호출하지 않습니다. JSON에 든 execute 문자열은 위조된 감사 값일 뿐 실제 작업이나 부작용을 뜻하지 않습니다.

## 7. 구현 경계

검사는 `JsonFileCheckpointer`의 저장·복원 State 불변식 경계에 적용됩니다. 파일의 어느 위험 run이든 거절 State와 execute 이벤트를 함께 가지면 전체 파일을 읽기 전에 거부하여 후속 저장으로 덮어쓰지 않습니다. `MemoryCheckpointer`는 신뢰된 프로세스 내 불변 State 전이를 보관하는 별도 학습 경계입니다.

## 8. 승인 경계

위험 Action은 엄격한 별도 Boolean 승인 없이는 `WAITING_FOR_APPROVAL`에서 `execute` Node로 이동하지 않습니다. 명시적 `False` 결정은 `REJECTED`에서 끝나며, 이 감사 불변식도 그 비실행 경계를 보존합니다. 모든 실행 경로는 외부 시스템을 바꾸지 않는 결정론적 시뮬레이션입니다.

## 9. checksum과 감사 문자열의 한계

SHA-256 checksum은 키가 없는 무결성 검사일 뿐 인증 수단이 아닙니다. JSON 쓰기 권한자가 모든 값을 다시 쓸 수 있다면 이 검사는 어떤 실행이 실제로 일어났는지 증명하지 못합니다. 운영 환경에는 서명된 append-only 감사 저장소, 실행 권한 분리, 승인자 신원·권한·만료 검증이 필요합니다.

## 10. 동시성의 한계

이 검증은 한 로컬 JSON 파일의 의미를 다룹니다. JSON 경로 Lock과 CAS는 동일 Python 프로세스의 정규화된 로컬 경로를 여는 스레드 범위에만 적용됩니다. 여러 프로세스·호스트·네트워크 파일 시스템의 경쟁에는 트랜잭션 저장소와 분산 멱등성 제어가 필요합니다.

## 11. 실패 처리

모순된 거절·실행 감사 로그에서 Checkpointer는 이벤트를 자동 제거하거나 거절을 실행으로 바꾸지 않습니다. 호출자는 오류를 조사하고 신뢰 가능한 입력으로 Checkpoint를 다시 생성해야 합니다. 복구도 사람 승인 결정을 대체하지 않습니다.

## 12. 테스트 계약

회귀 테스트는 정상 `DEPLOY` 거절 Checkpoint에 연속 sequence의 execute 이벤트를 추가하고 checksum을 다시 계산합니다. 정확한 `대기 -> 거절` approval 이력이 남아 있어도 `load()`가 `rejected state must not contain an execute` 오류로 거부하는지 확인합니다.

## 13. 운영 전환 시 고려 사항

실제 시스템에는 승인 요청 ID, 승인자 역할과 신원, 정책 버전, 만료 시간, 서명된 불변 감사 이벤트, 외부 실행 결과의 독립 증명, 멱등성 키와 트랜잭션 경계가 필요합니다. 이 참조 모델은 이러한 운영 제어를 구현하거나 검증하지 않습니다.

## 14. 핵심 정리

- 위험 거절 State에는 execute 감사 이벤트가 존재할 수 없다.
- 정상 거절 이력과 재계산 checksum은 거절 뒤 위조 실행 기록을 정당화하지 못한다.
- 검증과 예제는 오프라인·결정론적이며 실제 위험 작업을 수행하지 않는다.
