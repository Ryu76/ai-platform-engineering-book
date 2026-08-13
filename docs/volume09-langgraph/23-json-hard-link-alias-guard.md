# JSON Checkpoint Hard Link 별칭 차단

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- hard link가 `Path.resolve()`로 제거되지 않는 파일 별칭임을 설명한다.
- 원자적 파일 교체와 hard link의 결합이 Checkpoint 사본을 분리할 수 있음을 식별한다.
- 다중 hard link를 명시적으로 거부해 로컬 Checkpointer의 단일 파일 전제를 보존한다.
- 위험 작업은 별도의 엄격한 Boolean 승인 전까지 실행하지 않는 경계를 확인한다.

## 2. 왜 필요한가

`Path.resolve()`는 `.`·`..`와 심볼릭 링크를 정규화하지만, 같은 inode를 가리키는 hard link 경로를 하나로 바꾸지 않습니다. JSON Checkpointer는 임시 파일을 만든 뒤 `replace()`로 원자적 저장을 수행합니다. 두 hard link 중 한 경로를 교체하면 다른 경로는 이전 inode를 계속 가리켜, 별칭마다 서로 다른 Checkpoint 파일처럼 분리될 수 있습니다.

따라서 이 참조 구현은 기존 JSON 파일의 link count가 2 이상이면 생성과 모든 읽기·쓰기 경로를 거부합니다. 이는 hard link 동시성을 지원한다는 주장이 아니라, 단일 정규화 경로 Lock 계약 밖의 별칭을 안전하게 차단하는 fail-closed 경계입니다.

> [!WARNING]
> 예제는 임시 디렉터리에 로컬 JSON 파일과 hard link만 만들고 삭제합니다. 외부 API, 네트워크, 실제 배포, 실제 파일 삭제, 비밀값은 사용하지 않습니다. `DEPLOY`, `DELETE`, `SEND`은 별도의 엄격한 Boolean 승인 없이는 계속 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 3. 핵심 개념

- **hard link:** 같은 파일 데이터를 가리키는 별도 디렉터리 항목입니다.
- **원자적 교체:** 임시 파일을 `replace()`해 한 경로의 파일 항목을 교체하는 저장 방식입니다.
- **link count:** 파일을 참조하는 hard link 수입니다. 2 이상이면 단일 파일 별칭 전제가 깨집니다.
- **fail closed:** 지원하지 않는 저장소 형태를 조용히 처리하지 않고 명시적으로 거부하는 정책입니다.

## 4. 동작 구조

```text
checkpoints.json ──┐
                   ├─ 같은 inode, link count=2
checkpoints-alt.json ┘
             |
             v
JsonFileCheckpointer -> ValueError("multiple hard links")
             |
             v
저장·재개 중단, Checkpoint 분리 방지
```

## 5. 실습 환경

```bash
cd /e/python/ai-platform-engineering-book-volume-09
uv run python examples/volume09/json_hard_link_guard_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
```

예제는 `TemporaryDirectory` 안에서만 실행됩니다. hard link 생성이 정책 또는 파일 시스템상 허용되지 않는 운영 환경에서는 이 예제를 실행하지 말고 지원되는 영속 저장소를 사용합니다.

## 6. 단계별 실습

### 6.1 단일 JSON Checkpoint를 기록한다

```python
checkpointer = JsonFileCheckpointer(path=checkpoint_path)
checkpointer.save(run_id="hard-link-guard-001", state=state)
```

### 6.2 기존 파일에 hard link 별칭을 만든다

```python
os.link(checkpoint_path, hard_link_path)
```

### 6.3 별칭을 열면 명시적으로 거부되는지 확인한다

```python
with pytest.raises(ValueError, match="multiple hard links"):
    JsonFileCheckpointer(path=hard_link_path)
```

## 7. 코드 설명

`JsonFileCheckpointer`는 경로를 `resolve()`한 뒤 `stat().st_nlink`를 확인합니다. 파일이 존재하고 link count가 1보다 크면 `ValueError`를 발생시킵니다. 이 검사는 생성 시와 `_read_checkpoints()` 시작 시에 모두 수행하므로, Checkpointer를 생성한 뒤 hard link가 추가돼도 다음 load/save/compare-and-swap 요청이 분리 저장 전에 실패합니다.

## 8. 정상 실행 결과

```text
$ uv run python examples/volume09/json_hard_link_guard_workflow.py
hard_link_rejected=checkpoint file must not have multiple hard links
```

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `multiple hard links` | Checkpoint 파일에 hard link 별칭이 있습니다. | 별칭을 제거하고 하나의 파일 경로만 사용하거나 운영 저장소로 옮깁니다. |
| 별칭마다 다른 상태가 보임 | 기존 구현이 hard link 뒤 한 경로를 원자적으로 교체했을 수 있습니다. | 두 파일을 신뢰하지 말고 감사 가능한 저장소에서 상태를 복구합니다. |
| hard link 생성이 실패함 | 파일 시스템 또는 보안 정책이 hard link를 금지합니다. | 예제 대신 단위 테스트를 해당 플랫폼 정책에 맞게 실행합니다. |

## 10. 응용 실습

1. `Path.resolve()`가 hard link 별칭을 통합하지 못하는 이유를 설명합니다.
2. 운영 데이터베이스에서 경로 별칭 대신 run ID와 버전 기반 compare-and-swap을 사용하는 설계를 작성합니다.
3. 승인 소비와 실제 위험 실행을 outbox로 분리하는 이유를 설명합니다.

## 11. 실무 적용

이 방어는 단일 로컬 파일 Checkpointer의 학습용 전제만 지킵니다. 다중 프로세스, 네트워크 파일 시스템, inode 교체 경쟁, 인증된 승인자, 실제 실행의 exactly-once를 제공하지 않습니다. 운영 환경은 트랜잭션 저장소, 버전 필드, 인증·감사, outbox와 멱등 작업자를 사용해야 합니다.

## 12. 과제

- **기본:** hard link 2개와 원자적 `replace()`가 상태 분리를 만드는 과정을 그립니다.
- **응용:** link count 검사를 생성 후 읽기에도 수행해야 하는 이유를 테스트로 보입니다.
- **심화:** 다중 프로세스 승인 소비를 위한 버전 기반 스키마를 설계합니다.

## 13. 완료 체크리스트

- [ ] hard link가 정규화 경로 Lock의 동일성 기준이 아님을 확인했다.
- [ ] 다중 hard link가 명시적으로 거부됨을 확인했다.
- [ ] 생성 뒤 추가된 hard link도 다음 저장소 작업에서 거부됨을 확인했다.
- [ ] 예제와 테스트를 외부 API·실제 위험 작업 없이 통과시켰다.

## 14. 핵심 정리

hard link는 `Path.resolve()` 기반 경로 Lock이 안전하게 통합할 수 없는 파일 별칭입니다. 원자적 `replace()`가 별칭을 분리하기 전에 link count 2 이상을 fail-closed로 거부하면, JSON Checkpointer가 지원하지 않는 별칭에서 위험 작업의 승인 Checkpoint를 조용히 분기시키지 않습니다. 이 방어는 실제 배포 권한이나 다중 프로세스 원자성을 제공하지 않으며, 위험 작업에는 계속 별도 승인이 필요합니다.
