# JSON Checkpoint execute 감사 이벤트의 명시적 승인 선행 검증

## 1. 학습 목표

- 위험 Action의 `execute` 감사 이벤트가 명시적 승인 결정 뒤에만 올 수 있음을 이해한다.
- 재계산 checksum과 정상 승인 이벤트만으로 승인 전 실행 기록을 정당화할 수 없음을 확인한다.
- 감사 순서 구조 검증과 실제 실행·승인자 인증을 구분한다.

## 2. 문제

위험 `COMPLETED` JSON이 `대기 -> 승인` approval 이벤트와 결과를 모두 가져도, `execute` 이벤트가 승인보다 먼저 기록됐다면 승인 경계를 우회한 이력입니다. 기존 승인 이벤트 포함·순서 검사는 approval 이벤트끼리의 순서만 보므로, JSON 쓰기 권한자가 execute를 sequence 3에 두고 승인 이벤트를 sequence 4에 둔 뒤 checksum을 다시 계산할 수 있습니다.

## 3. 안전 계약

`JsonFileCheckpointer`는 위험 Action의 execute 감사 순서를 추가로 검증합니다.

- `REJECTED`에는 execute 이벤트가 하나도 있을 수 없다.
- 위험 `COMPLETED`에는 execute 이벤트가 하나 이상 있어야 한다.
- 위험 execute 이벤트는 명시적 `대기 -> 승인`의 승인 이벤트보다 반드시 뒤의 sequence를 가져야 한다.
- 승인 이벤트가 없는 상태에 execute 이벤트가 있거나, execute가 승인보다 앞서면 checksum이 맞아도 복원 전에 fail-closed 한다.

## 4. 흐름

```text
JSON 읽기
  -> 중복 키 검사
  -> schema + checksum 검사
  -> ActionKind 승인 정책 + 정확한 approval 전이 검사
  -> execute 이벤트 존재·승인 후 sequence 검사
  -> 복원 또는 거부
```

## 5. 오프라인 실습

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_execute_after_approval_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 임시 JSON Checkpoint에 위험 `DEPLOY` 승인 대기를 만든 뒤, execute 이벤트를 sequence 3에 먼저 넣고 승인 이벤트를 sequence 4에 추가합니다. payload SHA-256도 다시 계산하지만 네트워크, API, 실제 배포·삭제·전송, 비밀값은 사용하지 않습니다.

## 6. 기대 결과

```text
execute_before_approval_rejected=checkpoint execute audit event must follow explicit approval
```

거부는 `execute` Node를 호출하지 않습니다. JSON 안의 execute 문자열과 `COMPLETED` 값은 위조된 감사 데이터일 뿐 실제 작업이나 부작용을 뜻하지 않습니다.

## 7. 구현 경계

검사는 `JsonFileCheckpointer`의 저장·복원 State 불변식 경계에 적용됩니다. 파일의 위험 run 하나라도 승인보다 이른 execute 이벤트를 가지면 전체 파일은 읽기 단계에서 거부되어 후속 저장으로 덮어쓰지 않습니다. `MemoryCheckpointer`는 신뢰된 프로세스 내 불변 State 전이를 보관하는 별도 학습 경계입니다.

## 8. 승인 경계

위험 Action은 별도의 엄격한 Boolean `True` 결정 전에는 `WAITING_FOR_APPROVAL`에서 `execute` Node로 이동하지 않습니다. 이 감사 순서 검사는 저장된 JSON이 그 경계와 모순되지 않도록 하지만, 모든 execute 경로는 여전히 외부 시스템을 변경하지 않는 결정론적 시뮬레이션입니다.

## 9. checksum과 감사 문자열의 한계

SHA-256 checksum은 키 없는 우발 변경 탐지이고 감사 이벤트는 일반 텍스트입니다. 이 검사는 구조적으로 모순된 순서를 차단하지만, 쓰기 권한자가 그럴듯한 승인 후 이벤트와 checksum을 함께 작성하는 것을 인증하거나 실제 실행 시점을 증명하지 못합니다. 운영 환경에는 서명된 append-only 감사 저장소, 승인자 신원·권한·만료 검증, 실행 권한 분리가 필요합니다.

## 10. 동시성의 한계

이 검증은 단일 로컬 JSON 파일의 State 의미를 다룹니다. JSON 경로 Lock과 CAS 보장은 같은 Python 프로세스의 같은 정규화 경로를 여는 스레드 범위에 한정됩니다. 여러 프로세스·호스트·네트워크 파일 시스템의 승인 경쟁에는 트랜잭션 저장소와 분산 멱등성 제어가 필요합니다.

## 11. 실패 처리

승인보다 앞선 execute 감사 이벤트는 자동으로 재정렬하거나 삭제하지 않습니다. 호출자는 오류를 조사하고 신뢰 가능한 입력으로 Checkpoint를 다시 생성해야 하며, 복구 과정도 사람 승인 결정을 대체하지 않습니다.

## 12. 테스트 계약

회귀 테스트는 정상 위험 `DEPLOY` 승인 대기를 `COMPLETED`, `approval_granted=True`, 결과로 바꾸고 sequence 3 execute·sequence 4 승인 이벤트를 추가한 뒤 checksum을 다시 계산합니다. `load()`가 `execute audit event must follow explicit approval` 오류로 복원 전에 거부하는지 확인합니다.

## 13. 운영 전환 시 고려 사항

실제 시스템에는 승인 요청 ID, 승인자 역할과 신원, 정책 버전, 만료 시간, 서명된 불변 감사 이벤트, 독립적인 외부 실행 결과 증명, 멱등성 키와 트랜잭션 경계가 필요합니다. 이 참조 모델은 이런 운영 제어를 구현하거나 검증하지 않습니다.

## 14. 핵심 정리

- 위험 execute 감사 이벤트는 명시적 승인보다 반드시 뒤에 기록돼야 한다.
- 재계산 checksum과 승인 이력은 승인 전 execute 기록을 정당화하지 못한다.
- 검증과 예제는 오프라인·결정론적이며 실제 위험 작업을 수행하지 않는다.
