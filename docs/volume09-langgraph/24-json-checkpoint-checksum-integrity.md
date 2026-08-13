# JSON Checkpoint Checksum 무결성 검사

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- JSON 문법이 정상이어도 Checkpoint 내용이 바뀌었는지 checksum으로 검사한다.
- 결정론적 직렬화가 checksum 비교에 필요한 이유를 설명한다.
- checksum 불일치 시 위험 작업의 재개 전에 fail-closed로 중단한다.
- checksum이 인증이나 실제 위험 작업 승인 권한을 제공하지 않음을 구분한다.

## 2. 왜 필요한가

JSON 파일이 파싱된다는 사실만으로 저장한 상태가 그대로라는 뜻은 아닙니다. 편집기, 복사 충돌, 디스크 오류 또는 의도하지 않은 수동 수정으로 `task`, Action, 승인 상태, 감사 이벤트가 바뀔 수 있습니다. 특히 `WAITING_FOR_APPROVAL` Checkpoint를 다시 읽어 승인 결정을 적용하는 흐름은, 읽은 상태가 기록 당시의 상태와 같은지 먼저 확인해야 합니다.

`JsonFileCheckpointer`는 `schema_version`과 `checkpoints`만 정렬된 JSON 바이트로 직렬화해 SHA-256 값을 계산하고, 그 값을 `payload_sha256`에 함께 기록합니다. 읽을 때 다시 계산한 값이 다르면 payload를 `WorkflowState`로 복원하지 않고 명시적으로 실패합니다.

> [!WARNING]
> 이 checksum에는 비밀 키가 없습니다. 따라서 전송 오류나 우발적 변경을 발견하는 무결성 검사일 뿐, 공격자가 checksum까지 다시 계산해 바꾸는 것을 막는 인증 수단이 아닙니다. 실제 승인 기록에는 인증된 저장소, 접근 제어, 감사 로그와 트랜잭션 compare-and-swap이 필요합니다.

## 3. 핵심 개념

- **Checksum:** 데이터에서 계산한 고정 길이 값입니다. 같은 정규화 payload는 같은 SHA-256 값을 가집니다.
- **Canonical serialization:** 키 정렬과 고정 구분자를 사용해 같은 객체를 항상 같은 바이트로 표현하는 방법입니다.
- **Fail closed:** checksum이 없거나 형식이 다르거나 값이 일치하지 않으면 상태를 추측해 재개하지 않는 정책입니다.
- **무결성(integrity)과 인증(authenticity):** checksum은 우발적 변화를 탐지하지만, 키 없는 checksum은 변경 주체를 증명하지 못합니다.

## 4. 동작 구조

```text
WorkflowState
    |
    v
schema_version + checkpoints --canonical JSON--> SHA-256
    |                                         |
    v                                         v
checkpoints.json = { payload_sha256, ... }  저장
    |
    v
load() -> 다시 SHA-256 계산 -> 일치? -- 아니오 --> ValueError, 재개 중단
                                  |
                                 예
                                  v
                         WorkflowState 검증·복원
```

## 5. 실습 환경

```bash
# 실행 위치: Git Bash 또는 WSL의 프로젝트 루트
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_checksum_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 `TemporaryDirectory` 안의 JSON 파일만 기록하고 종료 시 정리합니다. 네트워크, 외부 API, 실제 파일 삭제, 배포, 비밀값을 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 Checkpoint를 checksum과 함께 기록한다

```python
checkpointer.save(
    run_id="json-checksum-guard-demo-001",
    state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
)
```

저장소는 공개 상태를 JSON으로 만들고 `payload_sha256`을 함께 기록합니다.

### 6.2 JSON 문법을 유지한 채 payload를 변경한다

```python
checkpoint_path.write_text(
    checkpoint_path.read_text(encoding="utf-8").replace(
        "로컬 문서를 읽는다", "로컬 문서를 변경한다"
    ),
    encoding="utf-8",
)
```

이 변경은 JSON 파서를 통과하지만 이전 checksum과는 일치하지 않습니다.

### 6.3 복원이 차단되는지 확인한다

```python
with pytest.raises(ValueError, match="checksum does not match"):
    checkpointer.load(run_id="json-checksum-guard-demo-001")
```

오류가 발생한 뒤에는 상태를 재구성하거나 승인 재개를 시도하지 않습니다.

## 7. 코드 설명

`_checkpoint_payload_digest()`는 `schema_version`과 `checkpoints`를 키 정렬(`sort_keys=True`) 및 고정 구분자(`separators=(",", ":")`)로 직렬화한 뒤 SHA-256 hex digest를 만듭니다. 표시용 들여쓰기나 마지막 줄바꿈은 checksum 대상이 아니므로 파일 표현 형식이 아닌 의미 있는 payload를 검사합니다.

`_read_checkpoints()`는 먼저 정확한 최상위 스키마와 64자리 소문자 hex digest 형식을 확인합니다. 이어서 재계산한 값과 비교해 불일치하면 `ValueError("checkpoint file checksum does not match its payload")`를 발생시킵니다. 이 검사는 JSON 상태 검증과 `WorkflowState` 복원보다 먼저 실행됩니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_checksum_guard_workflow.py
checksum_mismatch_rejected=checkpoint file checksum does not match its payload
```

이 출력은 변경된 JSON이 실행 후보 상태로 사용되지 않았음을 뜻합니다.

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `checksum does not match its payload` | 파일 내용과 기록된 checksum이 다릅니다. | 파일을 수동 수정하지 말고, 신뢰 가능한 원본이나 운영 저장소에서 상태를 복구합니다. |
| `payload_sha256 string` | 구형 또는 불완전한 JSON 파일에 checksum 필드가 없습니다. | 이 스키마 버전의 Checkpointer로 새 Checkpoint를 생성합니다. 기존 파일을 임의로 재개하지 않습니다. |
| `unsupported checkpoint schema version` | 다른 Checkpointer 스키마의 파일을 열었습니다. | 호환되는 마이그레이션을 별도로 설계·검증하거나 새 파일을 사용합니다. |

## 10. 응용 실습

1. `payload_sha256`만 변경했을 때도 fail-closed 되는 단위 테스트를 작성합니다.
2. key rotation과 서명 검증이 필요한 운영 Checkpoint 저장소의 설계를 작성합니다.
3. 승인 결정과 실제 위험 실행을 outbox로 분리할 때 checksum이 담당하는 범위와 담당하지 않는 범위를 표로 정리합니다.

## 11. 실무 적용

운영 환경에서는 checksum만으로 승인 Checkpoint를 신뢰하면 안 됩니다. 인증·인가된 트랜잭션 저장소에 상태 버전과 승인자 정보를 보관하고, 승인 소비는 compare-and-swap으로 처리해야 합니다. 실제 배포·삭제·전송은 승인 상태 변경과 별도 멱등 작업자로 실행하며, 실패·재시도·감사 보존 정책도 함께 설계합니다.

## 12. 과제

- **기본:** JSON 문법 오류와 checksum 불일치의 차이를 설명합니다.
- **응용:** 동일한 Python 객체가 결정론적 JSON 직렬화에서 같은 digest를 얻는 이유를 검증합니다.
- **심화:** 키 관리와 감사 보존을 포함한 서명된 Checkpoint 포맷을 설계합니다.

## 13. 완료 체크리스트

- [ ] 정상 JSON이라도 checksum 불일치 시 복원되지 않음을 확인했다.
- [ ] checksum 대상이 `schema_version`과 `checkpoints`임을 확인했다.
- [ ] 키 없는 checksum이 인증 수단이 아님을 설명할 수 있다.
- [ ] 예제와 테스트를 외부 API·실제 위험 작업 없이 통과시켰다.

## 14. 핵심 정리

JSON 파싱 성공은 Checkpoint 무결성을 보장하지 않습니다. 결정론적 payload checksum을 기록하고 읽기 전에 재계산하면 우발적으로 변경된 상태를 위험 작업 승인 재개 전에 차단할 수 있습니다. 다만 checksum은 인증을 대신하지 않으며, 실제 위험 작업에는 별도의 엄격한 Boolean 승인과 운영 저장소의 인증·트랜잭션 경계가 계속 필요합니다.
