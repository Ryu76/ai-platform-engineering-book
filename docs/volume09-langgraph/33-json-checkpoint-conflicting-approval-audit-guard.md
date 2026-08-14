# JSON Checkpoint의 상반된 승인 감사 결정 차단

## 1. 학습 목표

- 위험 Action의 승인 감사 이벤트가 단순 포함 관계가 아니라 상태별 정확한 전이 순서여야 함을 이해한다.
- 거절과 승인이 함께 있는 재계산 checksum JSON이 완료 상태로 복원되지 않음을 확인한다.
- 이 구조 검증과 실제 승인자 인증·권한 부여를 구분한다.

## 2. 문제

승인 대기 이벤트 뒤 승인 이벤트가 *어딘가에* 있다는 검사만으로는 충분하지 않습니다. JSON을 수정할 수 있는 주체가 먼저 `사람이 작업을 거절했습니다.` 이벤트를 넣고, 뒤에 승인 이벤트와 `COMPLETED` 값·결과·새 checksum을 추가할 수 있습니다. 최종 Boolean이 `True`여도 상반된 결정을 하나의 실행 이력으로 해석해서는 안 됩니다.

## 3. 안전 계약

`JsonFileCheckpointer`는 위험 Action의 `approval` 이벤트 상세 순서를 현재 상태와 정확히 일치시킵니다.

- `PENDING`, `PLANNED`, 경로 검토 대기, 검토 거절에는 위험 승인 이벤트가 없다.
- `WAITING_FOR_APPROVAL`에는 승인 대기 이벤트가 정확히 하나 있다.
- `READY`, `COMPLETED`, `ERROR`, `FAILED`에는 `대기 -> 승인` 이벤트가 각각 정확히 하나씩 있다.
- `REJECTED`에는 `대기 -> 거절` 이벤트가 각각 정확히 하나씩 있다.
- 중복 대기, 중복 결정, 승인 뒤 거절, 거절 뒤 승인은 checksum이 맞아도 복원 전에 fail-closed 한다.

## 4. 흐름

```text
JSON 읽기
  -> 중복 키 검사
  -> schema + checksum 검사
  -> State 구조 + ActionKind 승인 정책 검사
  -> 상태별 정확한 위험 승인 감사 전이 검사
  -> 복원 또는 거부
```

## 5. 오프라인 실습

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_approval_audit_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 임시 JSON Checkpoint에 정상 `DEPLOY` 승인 대기를 만든 뒤, 거절 이벤트와 승인 이벤트를 모두 추가하고 `COMPLETED` 값·결과·checksum을 다시 씁니다. 네트워크, API, 실제 배포·삭제·전송, 비밀값은 사용하지 않습니다.

## 6. 기대 결과

```text
conflicting_approval_audit_rejected=checkpoint state has an invalid approval audit trail
```

거부는 `execute` Node를 호출하지 않습니다. JSON 안의 `COMPLETED`와 execute 이벤트는 변조된 값일 뿐 실제 작업의 성공이나 외부 부작용을 뜻하지 않습니다.

## 7. 구현 경계

검사는 `JsonFileCheckpointer`의 저장·복원 State 불변식 경계에 적용됩니다. 파일에 상반된 위험 승인 이력이 있는 run이 하나라도 있으면 전체 파일은 읽기 단계에서 거부되어 후속 저장으로 덮어쓰지 않습니다. `MemoryCheckpointer`는 신뢰된 프로세스 내 불변 State 전이를 보관하는 별도 학습 경계입니다.

## 8. 승인 경계

위험 Action은 승인 이벤트 텍스트만으로 실행되지 않습니다. 별도 엄격한 Boolean 승인 결정과 정확한 감사 전이가 함께 남아야 `READY`가 가능하며, 이 참조 모델의 `execute`는 외부 시스템을 변경하지 않는 결정론적 시뮬레이션입니다. 거절은 `REJECTED`에서 끝나고 실행 경로를 열지 않습니다.

## 9. checksum과 감사 문자열의 한계

SHA-256 checksum은 키가 없고 감사 이벤트는 로컬 JSON 일반 텍스트입니다. 쓰기 권한자가 Boolean, 모든 이벤트, checksum을 일관되게 다시 쓰는 공격을 막지 못합니다. 운영 환경에는 승인자 신원·권한·만료 검증, 서명된 append-only 감사 저장소, 접근 제어가 필요합니다.

## 10. 동시성의 한계

이 검증은 단일 파일의 상태 의미를 다룹니다. JSON 경로 Lock과 CAS 보장은 같은 Python 프로세스의 같은 정규화 로컬 경로 스레드 범위에 한정됩니다. 여러 프로세스·호스트·네트워크 파일 시스템의 승인 경쟁에는 트랜잭션 저장소와 분산 멱등성 제어가 필요합니다.

## 11. 실패 처리

상반된 승인 감사 이력은 자동으로 어느 한 결정을 선택하거나 수정하지 않습니다. 호출자는 오류를 조사하고 신뢰 가능한 입력으로 Checkpoint를 다시 생성해야 합니다. 복구 과정은 사람 승인 결정을 대체하지 않습니다.

## 12. 테스트 계약

회귀 테스트는 정상 `DEPLOY` 승인 대기를 `COMPLETED`, `approval_granted=True`, 결과로 바꾼 뒤 거절·승인 이벤트를 순서대로 추가하고 checksum을 다시 계산합니다. 승인 이벤트가 존재해도 `load()`가 `approval audit trail` 오류로 거부하는지 확인합니다.

## 13. 운영 전환 시 고려 사항

실제 시스템에는 승인 요청 ID, 승인자 정체성과 역할, 정책 버전, 만료 시간, 서명된 불변 감사 이벤트, 외부 실행 권한 분리, 멱등성 키와 트랜잭션 경계가 필요합니다. 이 참조 모델은 이런 운영 제어를 구현하거나 검증하지 않습니다.

## 14. 핵심 정리

- 위험 승인 이력은 필요한 이벤트의 존재뿐 아니라 상태별 정확한 전이 순서를 요구한다.
- 상반된 거절·승인 이벤트와 재계산 checksum은 위험 완료 State를 정당화하지 못한다.
- 검증과 예제는 오프라인·결정론적이며 실제 위험 작업을 수행하지 않는다.
