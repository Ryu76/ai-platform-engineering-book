# 중첩 감사 이벤트 JSON 키 모호성 차단

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 중첩된 감사 이벤트 객체도 JSON 키 중복 검사 대상이어야 하는 이유를 설명한다.
- `events` 안의 중복 `sequence`를 checksum과 State 복원 전에 fail-closed로 차단한다.
- parser의 마지막 키 선택이 감사 순서를 왜곡할 수 있음을 설명한다.
- 위험 작업 재개가 별도 엄격한 Boolean 승인에 계속 묶임을 확인한다.

## 2. 왜 필요한가

최상위 JSON 키만 검사하면 Checkpoint 내부의 `events` 객체는 여전히 모호할 수 있습니다. 예를 들어 하나의 event에 `"sequence": 1`과 `"sequence": 999`가 함께 있으면 parser마다 첫 값·마지막 값·오류 중 다른 결과를 낼 수 있습니다. 감사 순서가 승인 판단의 근거라면 이 차이는 안전 문제가 됩니다.

`JsonFileCheckpointer`는 `json.loads(..., object_pairs_hook=...)`를 사용하므로 중첩 `events` 객체도 사전으로 축약되기 전에 검사합니다. 따라서 중복 `sequence`는 checksum 비교나 `WorkflowState`의 연속 sequence 검증보다 먼저 `ValueError`로 중단합니다.

> [!WARNING]
> 이 예제는 임시 디렉터리의 로컬 JSON 파일만 수정합니다. 외부 API, 네트워크, 실제 배포·삭제·전송, 비밀값을 사용하지 않습니다. `DEPLOY`, `DELETE`, `SEND`은 중복 키 검사와 별개로 계속 별도의 엄격한 Boolean 승인이 필요합니다.

## 3. 핵심 개념

- **중첩 객체:** Checkpoint envelope 안의 상태, 이벤트처럼 다른 JSON 객체 안에 들어 있는 객체입니다.
- **감사 sequence:** 이벤트의 생성 순서를 나타내는 1부터 연속된 정수입니다.
- **객체 쌍 hook:** parser가 중복 키를 사전 하나로 축약하기 전에 모든 객체의 키·값 쌍을 검사하는 경계입니다.
- **fail closed:** 모호한 감사 로그를 추측해 복원하지 않고 즉시 거부하는 정책입니다.

## 4. 동작 구조

```text
JSON 텍스트
    |
    v
모든 객체(최상위·state·events)의 key가 정확히 한 번인가?
    | 아니오                                      | 예
    v                                             v
ValueError                         checksum + schema + State 검증
```

## 5. 실습 환경

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_duplicate_key_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 `TemporaryDirectory`에서 생성한 파일을 종료 시 정리합니다.

## 6. 단계별 실습

### 6.1 감사 이벤트가 있는 정상 Checkpoint를 기록한다

```python
state = WorkflowState.start(task="로컬 문서를 읽는다", action=ActionKind.READ).record(
    node="plan",
    detail="오프라인 계획을 만듭니다.",
    status=WorkflowStatus.PLANNED,
)
checkpointer.save(run_id="duplicate-nested-key-demo-001", state=state)
```

### 6.2 event의 `sequence` 키를 한 번 더 넣는다

```python
duplicate = valid_payload.replace(
    '          "sequence": 1\n',
    '          "sequence": 1,\n          "sequence": 1\n',
)
checkpoint_path.write_text(duplicate, encoding="utf-8")
```

값이 같아도 JSON 표현과 감사 해석이 모호하므로 허용하지 않습니다.

### 6.3 checksum보다 먼저 복원이 중단되는지 확인한다

```python
with pytest.raises(ValueError, match="duplicate object keys"):
    checkpointer.load(run_id="duplicate-nested-key-demo-001")
```

## 7. 코드 설명

`_json_object_without_duplicate_keys()`는 `object_pairs_hook`으로 호출됩니다. JSON decoder는 event 객체를 처리할 때도 이 hook을 사용하므로, 중복 `sequence`는 Python `dict`나 `WorkflowEvent`가 만들어지기 전에 거부됩니다.

파일의 checksum은 이 검사 뒤에야 비교됩니다. 따라서 중복된 event가 마지막 값으로 축약되어 checksum 또는 contiguous sequence 검사에 전달되는 경로가 없습니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_duplicate_key_guard_workflow.py
nested_duplicate_key_rejected=checkpoint file must not contain duplicate object keys
```

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `duplicate object keys` | event 객체에 `sequence` 같은 키가 둘 이상 있습니다. | 값을 수동으로 고르지 말고 신뢰할 수 있는 Checkpoint를 복구합니다. |
| `checkpoint event sequence must be contiguous` | 키는 고유하지만 감사 순서가 1부터 연속되지 않습니다. | 생성 로직과 저장 파일을 검토해 연속된 순서를 다시 만듭니다. |
| checksum 불일치 | 구조 검사는 통과했지만 payload가 기록 후 변경되었습니다. | 새 Checkpoint를 만들거나 인증된 저장소에서 복구합니다. |

## 10. 응용 실습

1. 중첩 state 객체의 `action` 키 중복도 같은 오류가 나는 테스트를 작성합니다.
2. 서로 다른 `sequence` 값의 중복이 마지막 값 선택보다 먼저 거부되는지 확인합니다.
3. 운영 감사 로그에서 서명 대상 canonicalization과 고유 키 검사를 함께 설계합니다.

## 11. 실무 적용

중복 키 거부는 parser 간 모호성을 줄이지만, 파일을 누가 수정했는지는 증명하지 않습니다. 운영 감사 로그에는 인증·인가, 서명 또는 HMAC, append-only 보관, 버전 기반 compare-and-swap가 추가로 필요합니다. 이 로컬 파일 참조 구현은 단일 프로세스의 오프라인 학습 경계이며 다중 프로세스 안전성이나 변경 주체 인증을 제공하지 않습니다.

## 12. 과제

- **기본:** event의 `sequence`가 중복되면 감사 해석이 왜 달라질 수 있는지 설명합니다.
- **응용:** 중복 키 검사와 contiguous sequence 검증의 순서를 테스트합니다.
- **심화:** 중첩 이벤트를 포함하는 signed envelope의 canonical JSON 규칙을 설계합니다.

## 13. 완료 체크리스트

- [ ] 감사 이벤트가 있는 JSON Checkpoint를 만들었다.
- [ ] event의 `sequence` 키를 중복했다.
- [ ] checksum·State 복원 전에 fail-closed 됨을 확인했다.
- [ ] 예제와 테스트를 외부 API·실제 위험 작업 없이 통과시켰다.

## 14. 핵심 정리

중복 키 검사는 최상위 envelope만의 규칙이 아닙니다. 중첩 감사 event의 `sequence`도 사전 축약 전에 유일해야 parser·검증기·감사 도구가 같은 기록을 해석할 수 있습니다. 이 구조 검사는 인증을 대체하지 않으며, 위험 ActionKind에는 계속 별도의 엄격한 Boolean 승인이 필요합니다.
