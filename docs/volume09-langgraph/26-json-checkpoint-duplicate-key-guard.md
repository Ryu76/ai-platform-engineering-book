# JSON Checkpoint 중복 키 모호성 차단

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- JSON 객체의 중복 키가 Checkpoint 해석을 모호하게 만드는 이유를 설명한다.
- 마지막 중복 키를 조용히 채택하지 않고 fail-closed로 거부한다.
- 중복 키 검사가 checksum 검증보다 먼저 필요한 경계를 설명한다.
- 위험 작업 재개가 별도 엄격한 Boolean 승인에 계속 묶임을 확인한다.

## 2. 왜 필요한가

일부 JSON 파서는 중복 키를 만나면 마지막 값을 채택하고, 다른 도구는 첫 값을 보거나 오류를 냅니다. 예를 들어 `schema_version` 또는 `payload_sha256`가 두 번 있으면 저장소, 감사 도구, 복구 도구가 같은 파일을 다르게 해석할 수 있습니다. JSON 문법이 유효하다는 사실만으로 Checkpoint 포맷이 명확하다는 뜻은 아닙니다.

`JsonFileCheckpointer`는 `object_pairs_hook`으로 최상위·Checkpoint·이벤트를 포함한 모든 JSON 객체의 키를 검사합니다. 같은 객체에 키가 두 번 나오면 checksum 계산이나 `WorkflowState` 복원 전에 `ValueError`로 중단합니다.

> [!WARNING]
> 이 예제는 임시 디렉터리의 로컬 JSON 파일만 수정합니다. 외부 API, 네트워크, 실제 배포·삭제·전송, 비밀값을 사용하지 않습니다. `DEPLOY`, `DELETE`, `SEND`은 중복 키 검사와 별개로 계속 별도의 엄격한 Boolean 승인이 필요합니다.

## 3. 핵심 개념

- **중복 키:** 한 JSON 객체 안에 같은 이름이 두 번 나타나는 형식상 허용될 수 있는 모호한 표현입니다.
- **객체 쌍 hook:** JSON 파서가 사전으로 축약하기 전 원래 키·값 쌍을 검사하는 경계입니다.
- **fail closed:** 모호한 파일을 마지막 값으로 추측해 재개하지 않고 거부하는 정책입니다.
- **checksum 선행 조건:** 고유한 구조가 확정된 뒤에만 canonical payload의 checksum 의미가 명확합니다.

## 4. 동작 구조

```text
JSON 텍스트
    |
    v
모든 객체의 key가 정확히 한 번인가?
    | 아니오                         | 예
    v                                v
ValueError                schema + checksum + State 검증
```

## 5. 실습 환경

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_duplicate_key_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 `TemporaryDirectory`에서 생성한 파일을 종료 시 정리합니다.

## 6. 단계별 실습

### 6.1 정상 Checkpoint를 기록한다

```python
checkpointer.save(
    run_id="duplicate-key-demo-001",
    state=WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ),
)
```

### 6.2 `schema_version` 키를 한 번 더 넣는다

```python
duplicate = valid_payload.replace(
    '  "schema_version": 2\n}',
    '  "schema_version": 2,\n  "schema_version": 2\n}',
)
checkpoint_path.write_text(duplicate, encoding="utf-8")
```

두 값이 같아도 표현 자체가 모호하므로 허용하지 않습니다.

### 6.3 복원이 중단되는지 확인한다

```python
with pytest.raises(ValueError, match="duplicate object keys"):
    checkpointer.load(run_id="duplicate-key-demo-001")
```

## 7. 코드 설명

`_json_object_without_duplicate_keys()`는 키·값 쌍을 순서대로 받아 이미 본 키를 다시 만나면 오류를 냅니다. 이 hook은 중첩 객체에도 적용되므로 Checkpoint state 또는 감사 event 안의 중복 필드도 같은 경계에서 거부합니다.

검사는 JSON 파싱 중에 끝납니다. 따라서 마지막 키를 채택한 사전, checksum 재계산 결과, 복원된 승인 상태 어느 것도 생성하지 않습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_duplicate_key_guard_workflow.py
duplicate_key_rejected=checkpoint file must not contain duplicate object keys
```

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `duplicate object keys` | 파일 객체에 같은 키가 둘 이상 있습니다. | 수동으로 하나를 선택하지 말고 신뢰할 수 있는 Checkpoint를 복구합니다. |
| checksum 불일치 | 구조 검사 뒤 payload가 저장 checksum과 다릅니다. | 새 Checkpoint를 만들거나 인증된 저장소에서 복구합니다. |
| 다른 파서에서는 읽힘 | 해당 파서가 마지막 키를 선택했을 수 있습니다. | 이 Checkpointer의 엄격한 포맷을 기준으로 파일을 다시 생성합니다. |

## 10. 응용 실습

1. `payload_sha256` 키를 중복해도 같은 오류가 나는 테스트를 작성합니다.
2. 중첩된 `events` 객체의 `sequence` 키 중복을 차단하는 테스트를 작성합니다.
3. 운영용 Checkpoint 포맷에서 서명 대상 canonicalization 규칙을 설계합니다.

## 11. 실무 적용

운영 저장소에서는 엄격한 parser 외에도 인증·인가, 서명 또는 HMAC, 버전 기반 compare-and-swap, 변경 불가능한 감사 로그가 필요합니다. 이 로컬 파일 참조 구현은 단일 프로세스의 오프라인 학습 경계이며 다중 프로세스 안전성이나 변경 주체 인증을 제공하지 않습니다.

## 12. 과제

- **기본:** 중복 키의 첫 값·마지막 값 선택이 왜 감사에 위험한지 설명합니다.
- **응용:** 중복 키 거부와 checksum 검증의 순서를 테스트합니다.
- **심화:** 스키마 진화 중에도 고유 키를 강제하는 signed envelope를 설계합니다.

## 13. 완료 체크리스트

- [ ] 유효한 JSON Checkpoint에 중복 키를 넣었다.
- [ ] State 복원 전에 fail-closed 됨을 확인했다.
- [ ] 중복 키와 checksum 불일치의 차이를 설명할 수 있다.
- [ ] 예제와 테스트를 외부 API·실제 위험 작업 없이 통과시켰다.

## 14. 핵심 정리

중복 키는 JSON 문법을 통과해도 Checkpoint 의미를 모호하게 만듭니다. 모든 객체에서 중복을 먼저 차단하면 parser마다 다른 값 선택이 승인 재개나 감사 판단에 들어오는 것을 막을 수 있습니다. 이 구조 검사는 인증을 대체하지 않으며, 위험 ActionKind에는 계속 별도의 엄격한 Boolean 승인이 필요합니다.
