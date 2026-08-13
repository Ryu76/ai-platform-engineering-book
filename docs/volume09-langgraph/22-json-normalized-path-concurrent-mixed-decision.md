# 정규화된 JSON 경로 별칭의 동시 상반 승인 결정 안전성

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 같은 위험 run에 대한 동시 승인과 거절 재전송의 경쟁을 설명한다.
- `Path.resolve()` 뒤 같은 JSON 파일을 여는 독립 Checkpointer 인스턴스가 하나의 비교·교체 Lock을 공유함을 검증한다.
- 상반된 엄격한 Boolean 결정 중 정확히 하나만 최종 Checkpoint를 바꿈을 확인한다.
- 완료와 거절 어느 결과도 실제 배포를 의미하지 않음을 구분한다.

## 2. 왜 필요한가

한 위험 작업의 승인 대기에 서로 다른 호출자가 거의 동시에 `approved=True`와 `approved=False`를 제출할 수 있습니다. 게다가 호출자는 `checkpoints.json`과 `path-alias/../checkpoints.json`처럼 같은 파일의 서로 다른 표기를 사용할 수 있습니다.

표기마다 Lock이 다르면 두 결정이 같은 대기 Checkpoint를 각각 읽고 독립적으로 덮어쓸 수 있습니다. `JsonFileCheckpointer`는 생성 시 `Path.resolve()` 결과를 파일 경로와 Lock 키로 사용하고, `save_if_current()`는 그 공유 Lock 안에서 기대 상태 비교와 교체를 수행합니다. 따라서 하나의 결정만 기록되고 나머지 재전송은 충돌로 끝납니다.

> [!WARNING]
> 이 장의 `DEPLOY`는 외부 시스템을 변경하지 않는 결정론적 상태 전이입니다. 승인 승자는 `execute`라는 감사 이벤트와 시뮬레이션 결과만 남기며, 거절 승자는 `REJECTED`로 끝납니다. 실제 배포·네트워크·비밀값은 사용하지 않습니다.

## 3. 핵심 개념

- **상반 결정 경쟁:** 같은 승인 대기에 `True`와 `False`가 동시에 도착하는 경우입니다.
- **정규화 경로:** `Path.resolve()`로 별칭을 제거한 하나의 로컬 파일 식별자입니다.
- **비교·교체:** 현재 Checkpoint가 읽었던 기대 상태와 같을 때만 새 상태를 저장하는 `save_if_current()` 계약입니다.
- **결정 소비:** 승인 대기를 완료 또는 거절이라는 하나의 종료 상태로 전이하는 일입니다.
- **충돌:** 이미 다른 결정이 대기 상태를 소비해 후속 요청이 종료 상태를 바꾸지 못하는 결과입니다.

## 4. 동작 구조

```text
True  ─┐
False ─┼─ 8개 독립 인스턴스 ─ Path.resolve() ─ 하나의 path Lock
True  ─┘                                      |
                                               v
                                  save_if_current(expected=waiting)
                                      |                         |
                                      v                         v
                    1개: COMPLETED 또는 REJECTED       7개: WorkflowRunConflictError
                    approval | execute (완료일 때만)       종료 checkpoint 보존
```

Lock 획득 순서는 고정하지 않습니다. 그러므로 최종 상태는 `COMPLETED` 또는 `REJECTED` 어느 하나일 수 있지만, 종료 결과 수는 정확히 하나이고 충돌 수는 일곱입니다.

## 5. 실습 환경

사용 파일은 다음과 같습니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `src/ai_platform/graph/api.py`
- `examples/volume09/json_normalized_path_concurrent_mixed_decision_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

예제는 `TemporaryDirectory`, 로컬 스레드와 결정론적 메모리 계산만 사용합니다. HTTP 서버, 외부 API, 실제 위험 작업, 비밀값은 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 경로 별칭과 대기 상태를 준비한다

```python
checkpoint_path = Path(directory) / "checkpoints.json"
alias_path = Path(directory) / "path-alias" / ".." / checkpoint_path.name
```

독립 인스턴스에 원래 경로와 별칭을 번갈아 전달합니다. 먼저 하나의 `DEPLOY`를 시작하면 `plan | approval`만 기록한 `WAITING_FOR_APPROVAL` Checkpoint가 생성됩니다.

### 6.2 상반된 엄격한 Boolean 결정을 동시에 보낸다

```python
decisions = (True, False, True, False, True, False, True, False)
request = ApprovalRequest(approved=decisions[index])
```

각 요청은 `StrictBool` 계약을 만족하는 실제 Python Boolean만 전달합니다. 문자열이나 숫자를 승인으로 바꾸지 않으며, 시작 요청과 승인 요청은 계속 분리됩니다.

### 6.3 오프라인 경쟁 계약을 실행한다

```bash
uv run python examples/volume09/json_normalized_path_concurrent_mixed_decision_workflow.py
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

## 7. 코드 설명

각 스레드는 같은 대기 Checkpoint를 읽고 자신의 승인 또는 거절 후보 상태를 계산합니다. `DeterministicWorkflow.resume()`은 후보를 만든 뒤 `save_if_current()`를 호출합니다. 정규화된 동일 경로의 공유 Lock 안에서 첫 호출만 기대 상태와 일치하므로 저장에 성공합니다.

승인 요청이 이기면 최종 이벤트는 `plan | approval | approval | execute`이며 결과는 오프라인 시뮬레이션입니다. 거절 요청이 이기면 이벤트는 `plan | approval | approval`이고 `execute`와 결과가 없습니다. 두 경우 모두 다른 일곱 요청은 `WorkflowRunConflictError`가 되어 종료 Checkpoint를 바꾸지 못합니다.

## 8. 정상 실행 결과

스레드 일정에 따라 두 안전한 출력 중 하나가 나옵니다.

```text
$ uv run python examples/volume09/json_normalized_path_concurrent_mixed_decision_workflow.py
completed=0
rejected=1
conflicts=7
checkpoint=rejected
approval_granted=False
events=plan | approval | approval
```

또는 승인 요청이 먼저 Lock을 얻으면 `completed=1`, `rejected=0`, `checkpoint=completed`, `approval_granted=True`, `events=plan | approval | approval | execute`가 출력됩니다. 어느 경우에도 둘 이상의 종료 결정이나 여덟 번째 `execute`는 허용되지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `completed=1`와 `rejected=1`이 함께 출력됨 | 비교·교체 또는 공유 Lock 경계가 빠졌을 수 있습니다. | 동일 정규화 경로 Lock 안에서 `save_if_current()`를 사용합니다. |
| `conflicts=0` | 대기 상태를 먼저 만들지 않았거나 동시 시작 Barrier가 없을 수 있습니다. | 하나의 위험 run을 시작한 뒤 `Barrier(8)`로 재개합니다. |
| 거절인데 `execute`가 있음 | 거절 경로가 승인 경로와 섞였을 수 있습니다. | `approved=False`가 `REJECTED`에서 종료하는지 확인합니다. |
| 결과가 항상 같아야 한다고 가정함 | 스레드 Lock 획득 순서는 비결정적입니다. | 결과 값이 아니라 단일 종료 상태·7개 충돌·감사 불변식을 검사합니다. |

## 10. 응용 실습

1. 원래 경로와 별칭 경로로 각각 승인 요청을 보낼 때 하나만 완료되는 이유를 설명합니다.
2. 시작, 승인, 거절을 모두 경쟁시키는 경우에도 위험 실행을 별도 outbox로 분리해야 하는 이유를 설계합니다.
3. 다중 프로세스에서 이 계약을 데이터베이스 compare-and-swap으로 옮길 때 필요한 버전 필드를 작성합니다.

## 11. 실무 적용

이 예제는 하나의 Python 프로세스에서 같은 정규화 로컬 파일을 사용하는 스레드의 상태 전이만 보호합니다. 심볼릭 링크 정책, 파일 교체, 프로세스 간 Lock, 네트워크 파일 시스템, 인증된 승인자나 실제 대상 시스템의 부작용을 보호하지 않습니다.

운영 환경은 승인 요청의 신원·근거·만료·감사 보존을 검증하고, 데이터베이스의 버전 기반 조건부 갱신으로 결정 소비를 처리해야 합니다. 실제 위험 작업은 승인 소비 트랜잭션과 분리된 멱등 실행 워커 및 outbox를 통해 수행해야 하며, 결과적으로 승인 결정이 곧바로 실제 배포 권한이 되지 않게 해야 합니다.

## 12. 과제

- **기본:** `COMPLETED`와 `REJECTED` 중 하나만 남는 비교·교체 순서를 설명합니다.
- **응용:** 경로 별칭 독립 인스턴스의 혼합 결정을 10회 반복 검증하는 테스트를 작성합니다.
- **심화:** 요청 ID, 승인자 ID, 상태 버전, outbox 이벤트를 포함한 다중 프로세스 승인 소비 스키마를 설계합니다. 외부 저장소나 배포는 실행하지 않습니다.

## 13. 완료 체크리스트

- [ ] `True`와 `False`의 동시 요청이 상반된 후보 상태를 만든다는 점을 이해했다.
- [ ] 별칭 경로가 정규화 뒤 하나의 Lock을 공유함을 확인했다.
- [ ] 종료 상태가 `COMPLETED` 또는 `REJECTED` 중 하나임을 확인했다.
- [ ] 나머지 일곱 요청이 종료 Checkpoint를 바꾸지 않는 충돌임을 확인했다.
- [ ] 거절 종료에 `execute`와 결과가 없음을 확인했다.
- [ ] 예제와 테스트를 외부 API·실제 위험 작업 없이 통과시켰다.

## 14. 핵심 정리

`Path.resolve()` 기반 경로 Lock과 `save_if_current()` 비교·교체를 함께 사용하면, 하나의 Python 프로세스에서 같은 JSON 파일의 별칭 경로를 쓰는 독립 Checkpointer 인스턴스도 상반된 승인·거절 재전송 중 하나만 기록할 수 있습니다. 승자 자체는 스레드 일정에 따라 달라질 수 있지만, 단일 종료 상태와 종료 뒤 충돌 보존은 고정됩니다. 이 오프라인 참조 모델은 실제 위험 실행이나 다중 프로세스 exactly-once 보장을 제공하지 않으므로 운영에는 인증·트랜잭션·outbox·멱등성 경계가 필요합니다.
