# 영속 Checkpoint와 안전한 작업 재개

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 프로세스 내 메모리 Checkpoint와 로컬 파일 영속 Checkpoint의 차이를 설명한다.
- 동일한 `run_id`로 새 Workflow 인스턴스에서 대기 상태를 복원한다.
- 위험 작업이 재시작 뒤에도 명시적인 사람 승인 전에는 `execute`에 도달하지 않음을 확인한다.
- 저장 파일의 범위, JSON 스키마 검증, 손상 파일 처리, 민감정보 제외 경계를 테스트한다.

## 2. 왜 필요한가

메모리 Checkpointer는 실행 중인 프로세스에서 interrupt를 재개하기에는 충분하지만, 프로세스가 끝나면 승인 대기 상태도 사라집니다. 장시간 작업, 서비스 재시작, 사람이 나중에 승인하는 흐름에서는 상태를 다시 읽을 수 있는 Persistence가 필요합니다.

Persistence는 단순히 Python 객체를 파일에 쓰는 기능이 아닙니다. 어떤 `run_id`의 어떤 상태를 저장할지, 파일이 손상되면 어떻게 실패할지, 민감한 문자열이 저장소로 들어가지 않게 할지를 함께 결정해야 합니다. 특히 재시작 자체가 위험 작업의 승인 경계를 제거해서는 안 됩니다.

## 3. 핵심 개념

- **MemoryCheckpointer**: 현재 프로세스 메모리에 `WorkflowState`를 저장합니다. 프로세스 종료 뒤에는 복원할 수 없습니다.
- **JsonFileCheckpointer**: 호출자가 지정한 기존 로컬 디렉터리의 단일 JSON 파일에 공개적인 State만 저장합니다.
- **run ID**: 한 Workflow 실행을 식별하는 비어 있지 않은 문자열입니다. 파일 이름이나 경로로 사용하지 않고 JSON의 키로만 저장합니다.
- **스키마 버전**: 파일 최상단의 `schema_version`입니다. 지원하지 않는 형식은 추측하여 읽지 않고 명시적으로 거절합니다.
- **원자적 교체(atomic replace)**: 같은 디렉터리의 임시 파일을 완성한 뒤 대상 파일과 교체합니다. 중간에 멈춰 불완전한 대상 파일이 남을 가능성을 줄입니다.
- **공개 State 경계**: 이 학습 구현은 `task`, 결과, 감사 이벤트에 흔한 자격 증명 표식이 있으면 저장을 거절합니다. 실제 서비스에서는 데이터 분류, 암호화, 접근 제어, 보존 기간을 별도로 설계해야 합니다.

> [!WARNING]
> `JsonFileCheckpointer`는 교육용 로컬 JSON 저장소입니다. 암호화, 사용자 인증, 다중 프로세스 잠금, 개인정보 정책, 운영용 키 관리 기능이 없습니다. 실제 자격 증명·개인정보·운영 승인 기록을 이 파일에 저장하지 마십시오. `DELETE`, `DEPLOY`, `SEND`는 저장·복원 뒤에도 `resume(approved=True)`가 오기 전에는 실행 시뮬레이션으로 이동하지 않습니다.

## 4. 동작 구조

```text
프로세스 A
START → plan → approval → WAITING_FOR_APPROVAL
                         │
                         ▼
             JsonFileCheckpointer.save(run_id, state)
                         │
                  로컬 JSON 파일
                         │
                         ▼
프로세스 B / 새 Workflow 인스턴스
JsonFileCheckpointer.load(run_id)
                         │
                         ▼
             WAITING_FOR_APPROVAL
                    │ 사람 승인
                    ▼
             READY → execute → COMPLETED (END)
```

재시작은 Checkpoint를 읽는 동작일 뿐입니다. 사람 승인 이벤트가 파일에 없으면 복원된 State는 계속 `WAITING_FOR_APPROVAL`입니다. 거절 또는 승인 결정은 기존 Workflow의 `resume()` 경로를 통해서만 기록됩니다.

## 5. 실습 환경

다음 파일을 사용합니다.

- `src/ai_platform/graph/checkpointer.py`
- `src/ai_platform/graph/workflow.py`
- `examples/volume09/persistent_checkpoint_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
cd /e/python/ai-platform-engineering-book-volume-09
uv sync --all-groups
```

이 실습은 `langgraph` 패키지, API 키, 네트워크, 데이터베이스, 실제 배포를 요구하지 않습니다. 예제는 운영 디렉터리가 아닌 `TemporaryDirectory`에 JSON 파일을 만들고 종료 시 자동 삭제합니다.

## 6. 단계별 실습

### 6.1 재시작 전 승인 대기 상태 만들기

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run python examples/volume09/persistent_checkpoint_workflow.py
```

예제의 첫 Workflow 인스턴스는 `DEPLOY`를 계획하지만 승인 전이므로 `waiting_for_approval`에 멈춥니다. JSON 파일에는 `run_id`, State 필드, 순서가 지정된 감사 이벤트만 저장됩니다. 예제는 실제 배포나 네트워크 연결을 수행하지 않습니다.

### 6.2 새 인스턴스에서 동일한 run ID 복원하기

```python
from pathlib import Path

from ai_platform.graph import ActionKind, DeterministicWorkflow, JsonFileCheckpointer

checkpoint_path = Path("/tmp/volume09-checkpoints.json")
waiting = DeterministicWorkflow(
    checkpointer=JsonFileCheckpointer(path=checkpoint_path)
).invoke(
    run_id="persistent-demo-001",
    task="학습용 배포를 준비한다",
    action=ActionKind.DEPLOY,
)

restarted_workflow = DeterministicWorkflow(
    checkpointer=JsonFileCheckpointer(path=checkpoint_path)
)
restored = restarted_workflow.checkpoint(run_id="persistent-demo-001")
assert restored == waiting
assert restored.status == "waiting_for_approval"
```

`JsonFileCheckpointer`의 부모 디렉터리는 호출 전에 존재해야 합니다. 이 제한은 예기치 않은 경로를 새로 만들지 않게 하며, 학습자가 저장 범위를 명시적으로 선택하게 합니다. Windows에서는 `Path`로 만든 임시 디렉터리를 사용하거나 이미 존재하는 프로젝트 밖의 학습용 폴더를 지정합니다.

### 6.3 복원 뒤에도 사람 승인으로만 실행하기

```python
completed = restarted_workflow.resume(
    run_id="persistent-demo-001",
    approved=True,
)
assert completed.status == "completed"
assert [event.node for event in completed.events] == [
    "plan", "approval", "approval", "execute"
]
```

새 인스턴스를 만들었어도 승인 Node가 한 번 더 기록된 뒤에만 `execute`가 실행됩니다. 이 예제의 execute는 여전히 문자열 결과를 만드는 오프라인 시뮬레이션입니다.

### 6.4 계약 테스트와 정적 검사 실행

```bash
# 실행 위치: 저장소 루트의 Git Bash, WSL Ubuntu 또는 Linux 터미널
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

테스트는 새 Workflow 인스턴스에서의 복원, 위험 작업의 승인 대기 유지, 민감정보처럼 보이는 State 텍스트의 저장 거부, 손상 JSON의 명시적 실패를 확인합니다.

## 7. 코드 설명

`JsonFileCheckpointer.save()`는 State를 Python 객체 직렬화나 pickle이 아닌 명시적인 JSON 스키마로 변환합니다. `action`, `status`, `selected_route`는 열거형 문자열로 저장하고, 이벤트는 `sequence`, `node`, `detail`만 저장합니다. 읽을 때는 필드 집합, 타입, 이벤트 순서, 열거형 값을 모두 검사합니다.

```python
payload = {
    "schema_version": 1,
    "checkpoints": {run_id: state_payload},
}
```

저장 전 `_validate_public_state()`가 작업, 결과, 이벤트, 재시도 출처를 검사합니다. 흔한 키 할당·토큰 접두사 표식이 있으면 파일을 만들거나 갱신하지 않고 `ValueError`를 반환합니다. 이 검사는 완전한 비밀 탐지기가 아니라 저장 금지 경계를 보여 주는 보수적인 교육용 보호막입니다.

파일 교체는 완성된 임시 JSON 파일에만 수행합니다. 파일이 깨졌거나 스키마가 다르면 `load()`는 이전 State를 추측해 실행하지 않고 오류를 냅니다. 따라서 호출자는 오류를 사람 검토나 복구 절차로 보내야 합니다.

## 8. 정상 실행 결과

6.1 예제의 출력은 다음과 같습니다.

```text
before_restart=waiting_for_approval
events=plan | approval
after_restart=waiting_for_approval
after_approval=completed
events=plan | approval | approval | execute
```

`after_restart`가 여전히 `waiting_for_approval`인 것이 핵심입니다. 재시작은 승인이 아닙니다. `uv run pytest tests/unit/test_volume09_graph.py -q`는 통과 테스트 수와 종료 코드 0을, Ruff와 mypy는 오류 없는 종료를 반환해야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `checkpoint parent directory must already exist` | 지정한 파일의 부모 디렉터리가 없습니다. | 먼저 존재하는 학습용 디렉터리 또는 `TemporaryDirectory` 경로를 전달합니다. |
| `checkpoint not found` | 다른 `run_id`를 사용했거나 아직 저장하지 않았습니다. | 저장과 복원에 정확히 같은 공개 `run_id`를 사용합니다. |
| `checkpoint file is not valid JSON` | 파일이 부분 기록되었거나 수동으로 변경되었습니다. | 자동 복구를 시도하지 말고 파일을 격리한 뒤 사람이 검토합니다. |
| `unsupported checkpoint schema version` | 현재 코드가 모르는 파일 형식입니다. | 마이그레이션 절차를 명시적으로 작성하거나 해당 버전의 코드로 읽습니다. |
| `must not contain suspected sensitive data` | State 또는 run ID에 자격 증명 표식이 있습니다. | 자격 증명을 State에 넣지 말고, 공개적인 작업 설명과 별도 보안 저장소를 사용합니다. |
| 재시작 직후 `execute`가 보임 | 승인 대기 State를 건너뛰는 별도 경로가 추가됐습니다. | `resume(approved=True)`만 READY로 전이시키는지와 이벤트 순서를 테스트합니다. |

## 10. 응용 실습

1. `JsonFileCheckpointer`가 저장한 JSON의 `schema_version`을 읽기 전용 검사 함수로 표시합니다. 지원하지 않는 버전은 절대 자동 변환하지 않습니다.
2. 종료된 `COMPLETED`, `REJECTED`, `FAILED` State의 보존 기간을 설계하고, 실제 삭제 대신 보존 대상 목록을 반환하는 순수 함수를 작성합니다.
3. `RetryWorkflow`에 같은 파일 Checkpointer를 주입해 승인 대기 상태를 새 인스턴스에서 복원하는 테스트를 만듭니다.

## 11. 실무 적용

운영 Persistence에는 데이터 분류, 테넌트 분리, 암호화 키 관리, 접근 제어, 감사 로그 무결성, 백업, 보존·파기 정책, 동시 쓰기 제어, 스키마 마이그레이션이 필요합니다. JSON 파일의 단일 프로세스 Lock은 여러 프로세스나 여러 서버 간 잠금을 제공하지 않습니다.

위험 작업의 승인에는 승인자, 대상, 영향 범위, 만료 시간, 정책 버전, idempotency key를 별도 검증 가능한 기록으로 연결해야 합니다. Checkpoint를 복원했다는 사실과 실행 권한을 얻었다는 사실은 서로 다른 이벤트여야 합니다. 운영 환경에서 이 예제의 문자열 기반 민감정보 탐지만으로 비밀값 보호를 주장해서는 안 됩니다.

## 12. 과제

- **기본:** 메모리 Checkpointer와 JSON 파일 Checkpointer가 각각 언제 State를 잃는지 설명합니다.
- **응용:** JSON 스키마에 새 필드를 추가할 때 구버전 파일을 안전하게 처리하는 마이그레이션 계획을 작성합니다.
- **심화:** 다중 테넌트 환경에서 run ID 충돌, 파일 권한, 승인 만료, 감사 로그 위변조를 다루는 영속 저장소 인터페이스를 설계합니다. 실제 데이터베이스나 배포는 사용하지 않습니다.

## 13. 완료 체크리스트

- [ ] 메모리와 파일 Checkpoint의 프로세스 재시작 동작 차이를 설명할 수 있다.
- [ ] 같은 `run_id`를 새 Workflow 인스턴스에서 복원했다.
- [ ] 위험 작업이 복원 뒤에도 승인 대기임을 이벤트로 확인했다.
- [ ] JSON 스키마와 손상 파일 거부 경계를 확인했다.
- [ ] 민감정보처럼 보이는 텍스트가 파일에 저장되지 않음을 테스트했다.
- [ ] 예제와 테스트가 API, 네트워크, 실제 배포 없이 동작함을 확인했다.
- [ ] `uv run pytest tests/unit/test_volume09_graph.py -q`를 통과했다.

## 14. 핵심 정리

영속 Checkpoint는 재시작을 가능하게 하지만 승인 권한을 만들지 않습니다. 이 장의 `JsonFileCheckpointer`는 명시한 로컬 파일, `run_id`별 State, 엄격한 JSON 스키마, 원자적 교체, 손상 파일 거부, 민감정보 표식 거부를 사용해 오프라인 학습 경계를 제공합니다. 위험 작업은 파일에서 복원한 뒤에도 사람의 명시적 승인 전에는 실행되지 않습니다.
