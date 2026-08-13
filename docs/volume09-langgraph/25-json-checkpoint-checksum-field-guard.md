# JSON Checkpoint Checksum 필드 변조 차단

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- payload를 바꾸지 않고 checksum 필드만 바꾼 JSON도 거부한다.
- digest의 문자열 형식 검사와 payload 비교 검사가 다른 책임임을 설명한다.
- 잘못된 checksum을 승인 재개 전에 fail-closed로 처리한다.
- 키 없는 checksum이 변경 주체를 인증하지 못함을 구분한다.

## 2. 왜 필요한가

JSON Checkpoint의 `payload_sha256`은 저장 당시 `schema_version`과 `checkpoints`에서 계산한 값입니다. payload가 그대로여도 이 필드를 다른 64자리 hex 문자열로 교체하면 기록과 검증 기준의 연결이 깨집니다. 복원 코드가 단지 digest 형식만 확인하면 이런 파일을 신뢰할 수 있으므로, 형식을 확인한 뒤 payload에서 재계산한 값과도 반드시 비교해야 합니다.

`JsonFileCheckpointer`는 `payload_sha256`의 소문자 64자리 hex 형식을 검사하고, canonical JSON payload로 다시 계산한 SHA-256과 일정 시간 비교합니다. 값이 다르면 `WorkflowState` 복원과 위험 작업의 승인 재개보다 먼저 실패합니다.

> [!WARNING]
> 이 예제는 임시 디렉터리의 로컬 JSON 파일만 수정합니다. 외부 API, 네트워크, 실제 배포·삭제·전송, 비밀값을 사용하지 않습니다. checksum은 우발 변경 탐지일 뿐 서명이나 승인 권한이 아니며, `DEPLOY`, `DELETE`, `SEND`은 계속 별도의 엄격한 Boolean 승인이 필요합니다.

## 3. 핵심 개념

- **digest 형식 검사:** 값이 SHA-256 hex처럼 보이는지 확인하는 첫 경계입니다.
- **digest 비교:** 현재 payload를 다시 계산해 기록된 값과 같은지 확인하는 무결성 경계입니다.
- **canonical payload:** 키 정렬과 고정 구분자로 같은 상태를 같은 바이트로 만드는 직렬화입니다.
- **fail closed:** 검사에 실패한 파일을 이전 상태나 추정 상태로 재개하지 않는 정책입니다.

## 4. 동작 구조

```text
JSON { schema_version, checkpoints, payload_sha256 }
                         |
                         v
          64자리 소문자 hex 형식인가?
                         |
                         v
canonical(schema_version + checkpoints) -> SHA-256 -> 기록값과 일치?
                                                        |          |
                                                      아니오       예
                                                        |          |
                                                   ValueError    State 복원
```

## 5. 실습 환경

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_checksum_field_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 `TemporaryDirectory`에서 생성한 파일을 종료 시 정리합니다.

## 6. 단계별 실습

### 6.1 Checkpoint를 기록한다

```python
checkpointer.save(
    run_id="checksum-field-guard-001",
    state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
)
```

### 6.2 payload는 유지하고 checksum 필드만 바꾼다

```python
payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
payload["payload_sha256"] = "0" * 64
checkpoint_path.write_text(json.dumps(payload), encoding="utf-8")
```

`"0" * 64`는 형식은 유효하지만 현재 payload에서 계산한 digest가 아닙니다.

### 6.3 복원이 중단되는지 확인한다

```python
with pytest.raises(ValueError, match="checksum does not match"):
    checkpointer.load(run_id="checksum-field-guard-001")
```

## 7. 코드 설명

`_constant_time_digest_matches()`는 정규식으로 digest 형식을 확인한 뒤 `hmac.compare_digest()`로 기대값과 비교합니다. 형식이 정상인 잘못된 값도 비교 결과가 `False`이므로 `_read_checkpoints()`는 `ValueError("checkpoint file checksum does not match its payload")`를 발생시킵니다.

이 검사는 `_payload_to_state()`보다 먼저 실행됩니다. 따라서 교체된 checksum 파일은 task, 승인 상태, 이벤트를 복원하거나 `resume()`의 후보 상태로 쓰지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_checksum_field_guard_workflow.py
checksum_field_rejected=checkpoint file checksum does not match its payload
```

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `checksum does not match its payload` | checksum 필드가 payload에서 재계산한 값과 다릅니다. | 파일을 수동 보정하지 말고 신뢰할 수 있는 저장소에서 복구합니다. |
| `payload_sha256 string` | checksum 필드가 없거나 문자열이 아닙니다. | 지원되는 Checkpointer로 새 Checkpoint를 만듭니다. |
| checksum을 다시 계산하면 통과함 | 키 없는 checksum이라 공격자가 새 값을 만들 수 있습니다. | 인증된 저장소·서명·접근 제어를 별도로 적용합니다. |

## 10. 응용 실습

1. checksum을 대문자 hex 또는 짧은 문자열로 바꿨을 때의 실패 계약을 작성합니다.
2. checksum, HMAC, 디지털 서명의 위협 모델 차이를 표로 정리합니다.
3. 승인 소비를 version 기반 compare-and-swap으로 처리하는 운영 저장소 설계를 작성합니다.

## 11. 실무 적용

운영 Checkpoint는 checksum만으로 신뢰하지 않습니다. 인증·인가된 저장소, 승인자 식별, 변경 불가능한 감사 로그, 버전 기반 트랜잭션과 실제 위험 실행을 위한 멱등 outbox가 필요합니다. 이 로컬 파일 구현은 같은 프로세스에서의 오프라인 학습 계약만 보입니다.

## 12. 과제

- **기본:** payload 변경과 checksum 필드 변경이 모두 왜 불일치가 되는지 설명합니다.
- **응용:** digest 형식 검사만으로는 부족한 반례를 만듭니다.
- **심화:** 키 순환을 포함한 서명된 Checkpoint 포맷을 설계합니다.

## 13. 완료 체크리스트

- [ ] payload를 유지한 채 잘못된 64자리 checksum을 기록했다.
- [ ] load가 State 복원 전에 fail-closed 됨을 확인했다.
- [ ] checksum 형식 검사와 재계산 비교의 차이를 설명할 수 있다.
- [ ] 예제와 테스트를 외부 API·실제 위험 작업 없이 통과시켰다.

## 14. 핵심 정리

형식이 맞는 checksum 문자열도 현재 canonical payload와 다시 비교해야 Checkpoint 무결성 검사가 됩니다. 비교가 실패하면 상태를 복원하지 않아 위험 작업 승인 재개 전에 변경된 파일을 차단할 수 있습니다. 다만 키 없는 checksum은 인증이나 실행 권한을 제공하지 않으며, 위험 ActionKind에는 계속 별도 엄격한 Boolean 승인이 필요합니다.
