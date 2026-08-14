# Volume 09 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 10 — Volume 09 LangGraph**
- 이번 슬라이스: 같은 Python 프로세스에서 `checkpoints.json`과 `path-alias/../checkpoints.json`처럼 **서로 다른 Path 표기**로 같은 파일을 여는 8개의 독립 `JsonFileCheckpointer` 인스턴스가 동시 `DEPLOY` 시작을 재전송해도, `Path.resolve()` 기반 경로 단위 Lock이 정확히 하나의 `WAITING_FOR_APPROVAL` Checkpoint만 생성함을 검증했습니다. 나머지 7개는 `WorkflowRunConflictError`로 끝나며, 중복 요청은 기존 Action·승인 대기 상태·감사 이벤트를 바꾸지 않고 어떤 요청도 `execute`를 기록하지 않습니다. 보장은 하나의 프로세스와 정규화 뒤 같은 로컬 경로로 한정되고, 위험 작업은 별도의 엄격한 Boolean 승인 전에는 계속 `WAITING_FOR_APPROVAL`에 머뭅니다.
- 이번 검증: `json_normalized_path_concurrent_start_workflow.py`는 `waiting_for_approval=1`, `conflicts=7`, `plan | approval`를 출력했습니다. 새 경로 별칭 동시 시작 계약 테스트는 10회 반복 모두 통과했고, Volume 09 단위 테스트는 `44 passed`, 전체 테스트는 `105 passed`였습니다. Ruff, mypy, 문서·링크·코드 블록·비밀값 검사와 `git diff --check`도 통과했습니다.
- 완료 선언: 아직 하지 않음. FastAPI 패키지가 프로젝트 의존성에 없으므로 실제 서버 연동은 승인된 별도 프로젝트 설정 변경이 필요하며, Volume Definition of Done의 나머지 항목도 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume09-langgraph/19-json-normalized-path-concurrent-approval.md`
  - `..`를 포함한 서로 다른 경로 표기가 `Path.resolve()` 뒤 같은 파일을 가리킬 때 독립 Checkpointer 인스턴스가 Lock을 공유하고 하나만 승인 대기를 소비하는 계약·운영 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 열아홉 번째 경로 별칭 동시 승인 안전성 장과 오프라인 예제 범위를 추가했습니다.
- `examples/volume09/json_normalized_path_concurrent_approval_workflow.py`
  - 원래 경로와 `path-alias/..` 별칭을 번갈아 쓰는 8개 독립 인스턴스가 `completed=1`, `conflicts=7`, 단일 `execute`만 출력하는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 서로 다른 `Path` 객체가 정규화 뒤 같은 JSON 파일을 가리킬 때, 독립 인스턴스 8개가 하나의 위험 run만 완료하고 충돌 요청이 완료 Checkpoint·감사 이벤트를 보존함을 검증하는 계약을 추가했습니다.
- `docs/volume09-langgraph/20-json-normalized-path-concurrent-rejection.md`
  - `..`를 포함한 서로 다른 경로 표기가 `Path.resolve()` 뒤 같은 파일을 가리킬 때 독립 Checkpointer 인스턴스가 Lock을 공유하고 하나만 승인 대기를 거절하는 계약·운영 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 스무 번째 경로 별칭 동시 거절 안전성 장과 오프라인 예제 범위를 추가했습니다.
- `examples/volume09/json_normalized_path_concurrent_rejection_workflow.py`
  - 원래 경로와 `path-alias/..` 별칭을 번갈아 쓰는 8개 독립 인스턴스가 `rejected=1`, `conflicts=7`, `execute` 없는 단일 거절 감사 순서를 출력하는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 서로 다른 `Path` 객체가 정규화 뒤 같은 JSON 파일을 가리킬 때, 독립 인스턴스 8개가 하나의 위험 run만 거절하고 충돌 요청이 거절 Checkpoint·감사 이벤트를 보존하며 `execute`를 추가하지 않음을 검증하는 계약을 추가했습니다.

## 기존 완료 파일

- `docs/volume09-langgraph/README.md`
  - Volume 목표, 위험 작업의 승인 경계, 현재 출고 장과 후속 학습 범위를 정리했습니다.
  - 현재 프로젝트 의존성에 `langgraph`가 없음을 명시하고, 범위 밖의 프로젝트 설정을 바꾸지 않은 이유를 기록했습니다.
- `docs/volume09-langgraph/01-learning-objectives.md`
  - PRD Chapter Definition of Done의 14개 섹션(목표부터 핵심 정리까지)을 한국어로 작성했습니다.
  - State, Node, Edge, Conditional Edge, START/END, Interrupt, 사람 승인, Checkpoint와 오프라인 검증 경계를 설명했습니다.
- `src/ai_platform/graph/state.py`
  - 불변 `WorkflowState`, 위험 ActionKind, 상태 열거형과 순서가 보장된 감사 이벤트를 구현했습니다.
- `src/ai_platform/graph/nodes.py`
  - Plan, Approval, 승인 결정, Execute Node를 구현했습니다. `delete`, `deploy`, `send`은 명시적 승인 전 중단되고 실제 부작용 없이 시뮬레이션 결과만 만듭니다.
- `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/checkpointer.py`, `src/ai_platform/graph/__init__.py`
  - `START → plan → approval → execute → END` 경로와 프로세스 내 메모리 Checkpoint 재개 경계를 구현했습니다.
- `examples/volume09/single_node_workflow.py`
  - 배포 작업이 승인 전 `waiting_for_approval`에 멈추고 승인 뒤 `completed`가 되는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 안전 작업 완료, 위험 작업 interrupt/승인 재개, 거절 미실행, 잘못된 재개, 빈 작업 거부와 Router 조건 분기 계약을 추가했습니다.
- `docs/volume09-langgraph/02-conditional-router-workflow.md`
  - Conditional Edge, RouterDecision 입력 계약, 낮은 신뢰도 fallback, 경로 검토와 위험 작업 승인의 분리를 14개 장 템플릿으로 문서화했습니다.
- `src/ai_platform/graph/state.py`, `src/ai_platform/graph/nodes.py`, `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/__init__.py`
  - `RouterDecision`, `RouteKind`, `RoutedWorkflow`와 `plan → router → specialist → approval → execute` 오프라인 경로를 구현했습니다.
- `examples/volume09/router_conditional_workflow.py`
  - 낮은 신뢰도의 `SEND` 요청이 경로 검토, 별도 실행 승인, 거절 종료를 순서대로 거치는 데모를 추가했습니다.
- `docs/volume09-langgraph/03-planner-developer-reviewer-workflow.md`
  - Planner-Developer-Reviewer의 역할 경계, 검토 거절 END, 위험 작업의 별도 사람 실행 승인을 14개 장 템플릿으로 문서화했습니다.
- `src/ai_platform/graph/state.py`, `src/ai_platform/graph/nodes.py`, `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/__init__.py`
  - `ReviewDecision`, `REVIEW_REJECTED`, Developer·Reviewer Node와 `PlannerDeveloperReviewerWorkflow`를 추가했습니다. Reviewer 통과는 실행 권한을 부여하지 않습니다.
- `examples/volume09/planner_developer_reviewer_workflow.py`
  - 검토 통과 뒤 `DEPLOY`가 실행 승인 대기에서 멈추고, 명시적 승인 뒤에만 오프라인 시뮬레이션을 완료하는 데모를 추가했습니다.
- `docs/volume09-langgraph/04-bounded-retry-error-node.md`
  - 제한된 재시도, Error Node, 최종 실패 END, 위험 작업의 승인 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 네 번째 장 링크와 재시도·Error Node 출고 범위를 반영했습니다.
- `src/ai_platform/graph/state.py`, `src/ai_platform/graph/nodes.py`, `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/__init__.py`
  - `RetryPlan`, `ERROR`·`FAILED`, 시도 횟수, Error Node와 `RetryWorkflow`를 추가했습니다. 실패 여부는 입력으로 고정하며, 상한 소진 뒤 추가 시도는 없습니다.
- `examples/volume09/retry_error_workflow.py`
  - 첫 번째 오프라인 실패 뒤 한 번 재시도하여 완료하는 이벤트 순서를 출력합니다.
- `tests/unit/test_volume09_graph.py`
  - 회복 성공, 상한 소진 최종 실패, 위험 작업의 승인 전 시도 금지, 잘못된 재시도 입력 거부 계약을 추가했습니다.
- `docs/volume09-langgraph/05-persistent-checkpoint-workflow.md`
  - 영속 Checkpoint의 저장 범위, run ID, JSON 스키마, 원자적 교체, 손상 파일 거부, 민감정보 제외와 재시작 뒤 승인 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 다섯 번째 장 링크와 영속 Checkpoint 출고 범위를 반영했습니다.
- `src/ai_platform/graph/checkpointer.py`, `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/__init__.py`
  - 주입 가능한 `Checkpointer` 계약과 `JsonFileCheckpointer`를 추가했습니다. 파일 저장은 로컬·결정론적이며, 공개 State만 저장하고 읽을 때도 스키마와 이벤트 순서를 검증합니다.
- `examples/volume09/persistent_checkpoint_workflow.py`
  - 임시 디렉터리에서 새 Workflow 인스턴스가 `DEPLOY` 승인 대기 상태를 복원한 뒤 명시적 승인으로만 오프라인 완료하는 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 새 인스턴스 복원, 승인 경계 유지, 민감정보 표식 거부, 손상 JSON 거부 계약을 추가했습니다.
- `docs/volume09-langgraph/06-streaming-state-updates.md`
  - 상태 Streaming, Checkpoint-before-yield, 위험 작업의 승인 전 `execute` 부재를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 여섯 번째 장 링크와 상태 Streaming 출고 범위를 반영했습니다.
- `src/ai_platform/graph/state.py`, `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/__init__.py`
  - 마지막 감사 이벤트와 불변 State를 함께 전달하는 `StreamUpdate`, 저장 뒤 출력하는 `StreamingWorkflow`, 승인 뒤 재개 스트림을 추가했습니다.
- `examples/volume09/streaming_workflow.py`
  - `DEPLOY`의 초기 상태 스트림이 승인 대기에서 멈추고, 명시적 승인 뒤에만 `execute`를 출력하는 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 안전 작업의 고정 상태 순서, 위험 작업 승인 전 `execute` 부재, 승인·거절 재개 계약을 추가했습니다.
- `docs/volume09-langgraph/07-parent-subgraph-approval-boundary.md`
  - 부모와 Subgraph의 책임 분리, Reviewer 판정과 실행 승인 분리, Subgraph 완료 뒤에도 유지되는 위험 작업 interrupt를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 일곱 번째 장 링크와 부모 Subgraph 승인 경계 출고 범위를 반영했습니다.
- `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/__init__.py`
  - 재사용 가능한 `PlannerDeveloperReviewerSubgraph`와 이를 호출하는 `SubgraphWorkflow`를 추가했습니다. Subgraph는 실행 권한이 없고, 부모만 Approval·Execute Node를 적용합니다.
- `examples/volume09/subgraph_workflow.py`
  - `DEPLOY`의 Subgraph 검토 통과 뒤에도 부모 승인 대기에서 멈추고, 명시적 승인 뒤에만 오프라인 완료하는 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 위험 작업의 Subgraph 통과 뒤 부모 Approval interrupt 유지, 승인 전 `execute` 부재, Reviewer 거절 시 부모 Approval·Execute 생략 계약을 추가했습니다.
- `docs/volume09-langgraph/08-fastapi-request-response-approval-boundary.md`
  - FastAPI route가 사용할 요청·응답 어댑터, Pydantic 입력 검증, 별도 승인 요청과 실제 서버를 실행하지 않는 안전 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 여덟 번째 장 링크와 FastAPI 어댑터 출고 범위를 반영했습니다.
- `src/ai_platform/graph/api.py`, `src/ai_platform/graph/__init__.py`
  - `StartWorkflowRequest`, 엄격한 `ApprovalRequest`, `WorkflowResponse`와 프레임워크 독립 `WorkflowApiAdapter`를 추가했습니다. 어댑터는 `DeterministicWorkflow`만 호출하며 위험 작업을 별도의 승인 전에는 재개하지 않습니다.
- `examples/volume09/fastapi_adapter_workflow.py`
  - `DEPLOY` 시작 응답이 승인 대기에서 멈추고 별도 명시적 승인 뒤에만 오프라인 완료하는 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 위험 시작 요청의 `execute` 부재, 문자열 승인 거부·명시적 거절의 비실행, 추가 필드·빈 경로 run ID 거부 계약을 추가했습니다.
- `docs/volume09-langgraph/09-run-id-conflict-approval-safety.md`
  - 재전송이 기존 승인 대기 Checkpoint를 교체하지 않는 run ID 충돌 계약과 운영 HTTP 409 매핑 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 아홉 번째 장 링크와 run ID 충돌 방지 출고 범위를 반영했습니다.
- `src/ai_platform/graph/api.py`, `src/ai_platform/graph/__init__.py`
  - `WorkflowRunConflictError`와 기존 run ID 사전 검사를 추가했습니다. 충돌 시작은 `invoke()` 전에 거부되어 기존 action·감사 이벤트·승인 대기 상태가 보존됩니다.
- `examples/volume09/fastapi_adapter_workflow.py`
  - 위험 작업 시작 뒤 동일 run ID의 안전 작업 재시작이 거부되고 원래 작업만 명시적 승인으로 완료하는 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 중복 시작이 위험 작업 Checkpoint를 덮어쓰지 않고 원래 `DEPLOY`만 승인 재개되는 계약을 추가했습니다.

- `docs/volume09-langgraph/10-atomic-run-creation.md`
  - `load()` 뒤 `save()`를 호출하는 run ID 중복 검사에 생기는 경쟁 조건, 원자적 생성 계약, Checkpointer별 보장 범위와 운영 저장소 요구사항을 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 열 번째 장 링크와 `save_if_absent()` 출고 범위를 반영했습니다.
- `src/ai_platform/graph/checkpointer.py`, `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/api.py`, `src/ai_platform/graph/__init__.py`
  - `Checkpointer.save_if_absent()`와 메모리·로컬 JSON 구현을 추가했습니다. API 시작은 분리된 사전 조회를 하지 않고 `invoke_new()`의 원자적 생성 결과로 충돌을 판정합니다. JSON의 원자성은 동일 Checkpointer 인스턴스의 스레드 범위임을 명시했습니다.
- `tests/unit/test_volume09_graph.py`
  - 메모리·로컬 JSON Checkpointer의 첫 생성 성공, 중복 생성 거부, 기존 위험 Action 상태 보존 계약을 추가했습니다.
- `docs/volume09-langgraph/11-concurrent-start-approval-safety.md`
  - 로컬 스레드 동시 재전송의 단일 생성자 계약, 승인 대기 Checkpoint 보존, Checkpointer별 보장 범위와 운영 저장소 요구사항을 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 열한 번째 장 링크와 동시 시작 안전성 출고 범위를 반영했습니다.
- `tests/unit/test_volume09_graph.py`
  - 같은 메모리 Checkpointer를 공유하는 8개 동시 위험 시작에서 정확히 하나만 승인 대기에 남고, 승인 전 `execute`가 없으며 명시적 승인 뒤에만 완료되는 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/planner_developer_reviewer_workflow.py
검토 통과 후: status=waiting_for_approval
events=plan | developer | reviewer | approval
사람 실행 승인 후: status=completed
events=plan | developer | reviewer | approval | approval | execute

$ uv run pytest tests/unit/test_volume09_graph.py -q
13 passed in 0.06s

$ uv run pytest -q
74 passed in 0.71s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 5 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)

$ uv run python examples/volume09/retry_error_workflow.py
status=completed
attempts=2
events=plan | approval | execute | error | execute

$ uv run pytest tests/unit/test_volume09_graph.py -q
17 passed in 0.12s

$ uv run pytest -q
78 passed in 1.10s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 5 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)

$ uv run python examples/volume09/persistent_checkpoint_workflow.py
before_restart=waiting_for_approval
events=plan | approval
after_restart=waiting_for_approval
after_approval=completed
events=plan | approval | approval | execute

$ uv run pytest tests/unit/test_volume09_graph.py -q
20 passed in 0.13s

$ uv run pytest -q
81 passed in 0.80s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 5 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ uv run python examples/volume09/streaming_workflow.py
initial_stream
1:plan status=planned detail='학습용 배포를 준비한다' 작업에 대한 오프라인 계획을 만들었습니다.
2:approval status=waiting_for_approval detail=deploy 작업은 사람 승인을 기다립니다.
checkpoint=waiting_for_approval
approved_resume_stream
3:approval status=ready detail=사람 승인을 받았습니다. 실행 시뮬레이션으로 이동합니다.
4:execute status=completed detail=외부 시스템을 변경하지 않는 결정론적 실행 결과를 만들었습니다.

$ uv run pytest tests/unit/test_volume09_graph.py -q
23 passed in 0.21s

$ uv run pytest -q
84 passed in 0.76s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 5 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)

$ uv run python examples/volume09/subgraph_workflow.py
Subgraph 검토 통과 후: status=waiting_for_approval
events=plan | developer | reviewer | approval
부모 Workflow의 사람 실행 승인 후: status=completed
events=plan | developer | reviewer | approval | approval | execute

$ uv run pytest tests/unit/test_volume09_graph.py -q
25 passed in 0.25s

$ uv run pytest -q
86 passed in 0.81s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 5 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)

$ uv run python examples/volume09/fastapi_adapter_workflow.py
시작 응답: status=waiting_for_approval
events=plan | approval
명시적 승인 응답: status=completed
events=plan | approval | approval | execute

$ uv run pytest tests/unit/test_volume09_graph.py -q
28 passed in 1.00s

$ uv run pytest -q
89 passed in 0.99s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)

$ uv run python examples/volume09/fastapi_adapter_workflow.py
시작 응답: status=waiting_for_approval
events=plan | approval
중복 시작 거부: run_id already exists: api-demo-001
명시적 승인 응답: status=completed
events=plan | approval | approval | execute

$ uv run pytest tests/unit/test_volume09_graph.py -q
29 passed in 0.60s

$ uv run pytest -q
90 passed in 0.99s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 검증 경로는 외부 API와 네트워크를 사용하지 않았습니다.

## 최신 검증 기록

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/fastapi_adapter_workflow.py
시작 응답: status=waiting_for_approval
events=plan | approval
중복 시작 거부: run_id already exists: api-demo-001
명시적 승인 응답: status=completed
events=plan | approval | approval | execute

$ uv run pytest tests/unit/test_volume09_graph.py -q
31 passed in 0.33s

$ uv run pytest -q
92 passed in 1.05s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

## 최신 검증 기록 — 동시 시작 안전성 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run pytest tests/unit/test_volume09_graph.py -q
32 passed in 0.96s

$ uv run pytest tests/unit/test_volume09_graph.py::test_concurrent_api_starts_create_one_risky_run_and_preserve_approval_gate -q  # 10회 반복
각 반복: 1 passed (0.26s~0.32s), 총 10/10 통과

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

## 알려진 차단 사항

- `pyproject.toml`에는 `langgraph`와 `fastapi` 의존성이 없습니다. 이번 작업의 수정 허용 범위는 Volume 09 문서·예제·테스트와 `src/ai_platform/graph/`이므로 프로젝트 의존성을 임의로 추가하지 않았습니다. 따라서 이번 구현은 LangGraph API·FastAPI 서버 실행이 아니라 개념·안전 계약을 검증하는 직접 구현 참조 모델입니다.
- Volume 09의 전체 PRD DoD가 충족되지 않았습니다. `VOLUME09_COMPLETE=true`를 추가하거나 작업을 self-pause하지 않았습니다.

## 다음 작업

- 별도 승인된 프로젝트 의존성 변경이 있을 때 FastAPI를 추가하고, 이 어댑터를 실제 route·TestClient에 연결합니다. 그 전까지 HTTP 서버·네트워크 실행은 하지 않습니다.

## 최신 슬라이스 — State Reducer와 감사 이벤트 병합

- `docs/volume09-langgraph/12-state-reducer-audit-events.md`
  - PRD의 Reducer 필수 내용을 14개 장 템플릿으로 문서화했습니다. 로컬 Node 이벤트와 전역 감사 sequence의 차이, 결정론성 전제, 병렬 도착 순서의 한계, Approval 경계를 설명했습니다.
- `docs/volume09-langgraph/README.md`
  - 열두 번째 장 링크와 Reducer 기반 감사 이벤트 병합 범위를 추가했습니다.
- `src/ai_platform/graph/state.py`, `src/ai_platform/graph/__init__.py`
  - `reduce_events()`를 추가하고 `WorkflowState.record()`가 이 Reducer를 거치도록 변경했습니다. 기존·로컬 이벤트는 각각 1부터 연속된 sequence여야 하며, 병합 결과만 전역 연속 sequence를 갖습니다.
- `examples/volume09/reducer_workflow.py`
  - `plan | approval | execute` 로컬 이벤트가 `1 | 2 | 3` 감사 순서로 병합되는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 정상 병합과 손상된 기존/로컬 sequence 거부 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 Reducer와 별개로 엄격한 별도 승인 전에는 `execute` Node로 이동하지 않습니다.

## 최신 검증 기록 — Reducer 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/reducer_workflow.py
events=plan | approval | execute
sequences=1 | 2 | 3

$ uv run pytest tests/unit/test_volume09_graph.py -q
34 passed in 0.33s

$ uv run pytest -q
95 passed in 1.12s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.

## 다음 작업

- 별도 승인된 의존성·프로젝트 설정 변경이 있을 때에만 실제 `langgraph`와 FastAPI `TestClient` 통합을 추가합니다. 그 전까지는 외부 서버·네트워크·위험 작업을 실행하지 않습니다.

## 최신 슬라이스 — 동시 승인 재전송의 단일 소비

- `docs/volume09-langgraph/13-concurrent-approval-single-execution.md`
  - 동시 승인 재전송, 비교-교체 Checkpoint, 충돌 처리 및 실제 위험 실행과의 운영상 차이를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 열세 번째 장 링크, 비교-교체 Checkpointer 계약 및 동시 승인 예제를 반영했습니다.
- `src/ai_platform/graph/checkpointer.py`, `src/ai_platform/graph/workflow.py`, `src/ai_platform/graph/api.py`
  - `save_if_current()` 비교·교체 계약을 메모리·로컬 JSON Checkpointer에 추가하고, `DeterministicWorkflow.resume()`이 후보 상태를 하나만 원자적으로 기록하게 했습니다. API 어댑터는 이미 소비된 승인 대기를 충돌로 공개합니다.
- `examples/volume09/concurrent_approval_workflow.py`
  - 같은 승인 대기 `DEPLOY` run에 대한 8개 동시 승인에서 `completed=1`, `conflicts=7`과 단일 감사 순서를 출력하는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 동시 승인 요청의 단일 완료·7개 충돌·단일 `execute` 이벤트와 메모리·JSON Checkpointer의 비교-교체 보존 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 모든 위험 ActionKind는 엄격한 별도 Boolean 승인 전에는 `WAITING_FOR_APPROVAL`을 벗어나지 않습니다.

## 최신 슬라이스 — JSON 동시 시작 단일 생성

- `docs/volume09-langgraph/15-json-checkpoint-concurrent-start.md`
  - 같은 `JsonFileCheckpointer` 인스턴스에서 `save_if_absent()`가 동시 run 생성 하나만 허용하는 계약, 인스턴스 Lock의 범위, 운영용 조건부 삽입·멱등성 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 열다섯 번째 장 링크와 JSON 동시 시작 단일 생성 출고 범위를 추가했습니다.
- `examples/volume09/json_concurrent_start_workflow.py`
  - 8개의 동시 `DEPLOY` 시작 재전송에서 `waiting_for_approval=1`, `conflicts=7`, `plan | approval`만 출력하는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 같은 JSON Checkpointer 인스턴스의 8개 동시 시작에서 하나의 위험 Action·승인 대기만 보존하고 `execute`가 없음을 검증하는 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 별도의 엄격한 Boolean 승인 전에는 계속 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 최신 검증 기록 — JSON 동시 시작 단일 생성 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/json_concurrent_start_workflow.py
waiting_for_approval=1
conflicts=7
checkpoint=waiting_for_approval
events=plan | approval

$ uv run pytest tests/unit/test_volume09_graph.py::test_concurrent_json_checkpoint_starts_create_one_pending_risky_run -q  # 10회 반복
각 반복: 1 passed (0.27s~0.90s), 총 10/10 통과

$ uv run pytest tests/unit/test_volume09_graph.py -q
38 passed in 0.65s

$ uv run pytest -q
99 passed in 1.78s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 최신 슬라이스 — 동일 JSON 경로 독립 인스턴스 동시 시작

- `docs/volume09-langgraph/16-json-shared-path-concurrent-start.md`
  - 같은 Python 프로세스에서 동일한 정규화 JSON 경로를 여는 독립 Checkpointer 인스턴스의 동시 시작 경쟁, 경로 단위 Lock 범위와 프로세스 간 운영 저장소 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 열여섯 번째 장 링크, 경로 단위 공유 Lock 보장 범위와 새 예제·테스트를 반영했습니다.
- `src/ai_platform/graph/checkpointer.py`
  - `JsonFileCheckpointer`가 `path.resolve()`를 기준으로 같은 프로세스 안의 동일 경로 인스턴스와 Lock을 공유하도록 변경했습니다. `save_if_absent()`와 `save_if_current()`은 이 범위에서만 원자성을 보장하며, 프로세스·호스트·네트워크 파일 시스템 간 보장은 주장하지 않습니다.
- `examples/volume09/json_shared_path_concurrent_start_workflow.py`
  - 동일 JSON 경로를 여는 8개 독립 Checkpointer 인스턴스의 동시 `DEPLOY` 시작에서 `waiting_for_approval=1`, `conflicts=7`, `plan | approval`만 출력하는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 같은 경로의 독립 JSON Checkpointer 인스턴스 8개가 위험 run 하나만 생성하고, 충돌 요청이 `execute` 없이 기존 승인 대기 상태를 보존하는 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 엄격한 별도 Boolean 승인 전에는 계속 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 최신 검증 기록 — 동일 JSON 경로 독립 인스턴스 동시 시작 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/json_shared_path_concurrent_start_workflow.py
waiting_for_approval=1
conflicts=7
checkpoint=waiting_for_approval
events=plan | approval

$ uv run pytest tests/unit/test_volume09_graph.py::test_concurrent_json_checkpoint_instances_share_a_path_lock_for_risky_starts -q  # 10회 반복
각 반복: 1 passed (0.29s~0.36s), 총 10/10 통과

$ uv run pytest tests/unit/test_volume09_graph.py -q
39 passed in 0.50s

$ uv run pytest -q
100 passed in 1.17s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 최신 검증 기록 — 동시 승인 단일 소비 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/concurrent_approval_workflow.py
completed=1
conflicts=7
checkpoint=completed
events=plan | approval | approval | execute

$ uv run pytest tests/unit/test_volume09_graph.py::test_concurrent_api_approvals_record_one_decision_and_one_offline_execution -q  # 20회 반복
각 반복: 1 passed (0.24s~0.28s), 총 20/20 통과

$ uv run pytest -q
97 passed in 1.30s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.

## 다음 작업

- 별도 승인된 의존성·프로젝트 설정 변경이 있을 때에만 실제 `langgraph`와 FastAPI `TestClient` 통합을 추가합니다. 그 전까지는 외부 서버·네트워크·위험 작업을 실행하지 않습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.

## 최신 슬라이스 — 정규화된 JSON 경로 별칭의 동시 상반 승인 결정

- `docs/volume09-langgraph/22-json-normalized-path-concurrent-mixed-decision.md`
  - `checkpoints.json`과 `path-alias/../checkpoints.json`을 번갈아 쓰는 독립 Checkpointer 인스턴스의 동시 `approved=True`·`approved=False` 재전송에서, 하나의 종료 결정만 기록되는 비교·교체 계약과 단일 프로세스 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 스물두 번째 상반 승인 결정 장과 관련 오프라인 예제·테스트 범위를 추가했습니다.
- `examples/volume09/json_normalized_path_concurrent_mixed_decision_workflow.py`
  - 원래 경로와 `path-alias/..` 별칭을 번갈아 쓰는 8개 독립 인스턴스가 동시 승인·거절 요청에서 `completed + rejected = 1`, `conflicts=7`을 출력하는 오프라인 데모를 추가했습니다. 최종 결정은 스레드 일정에 따라 달라지지만 실제 위험 작업은 수행하지 않습니다.
- `tests/unit/test_volume09_graph.py`
  - 정규화 뒤 같은 JSON 파일을 가리키는 독립 인스턴스의 혼합 결정 경쟁에서 단 하나의 `COMPLETED` 또는 `REJECTED` 상태만 남고, 나머지 7개 요청이 충돌하며, 거절에는 `execute`가 없고 완료에는 단 하나의 `execute`만 남는 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 엄격한 별도 Boolean 승인 요청에서 승리한 하나의 상태 전이로만 종료하며, `COMPLETED`도 오프라인 시뮬레이션입니다.

## 최신 검증 기록 — 정규화된 JSON 경로 별칭의 동시 상반 승인 결정 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run pytest tests/unit/test_volume09_graph.py::test_json_checkpoint_path_aliases_consume_one_mixed_approval_decision -q  # 10회 반복
각 반복: 1 passed (0.30s~1.30s), 총 10/10 통과

$ uv run python examples/volume09/json_normalized_path_concurrent_mixed_decision_workflow.py
completed=0
rejected=1
conflicts=7
checkpoint=rejected
approval_granted=False
events=plan | approval | approval
# Lock 획득 순서에 따라 completed=1 / rejected=0도 유효하다.

$ uv run pytest tests/unit/test_volume09_graph.py -q
45 passed in 1.29s

$ uv run pytest -q
106 passed in 3.30s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.


## 최신 슬라이스 — JSON Checkpoint hard link 별칭 차단

- `docs/volume09-langgraph/23-json-hard-link-alias-guard.md`: `Path.resolve()`로 통합되지 않는 hard link 별칭, 원자적 `replace()`로 인한 Checkpoint 분리 위험, fail-closed 경계와 승인 보존 조건을 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`: 스물세 번째 hard link 별칭 차단 장과 오프라인 예제를 추가했습니다.
- `src/ai_platform/graph/checkpointer.py`: 생성 시 및 모든 JSON 읽기 전 `st_nlink > 1`인 기존 파일을 거부합니다. 생성 뒤 추가된 hard link도 다음 load/save/compare-and-swap 전에 차단되어 원자적 교체가 별칭을 분리하지 못합니다.
- `examples/volume09/json_hard_link_guard_workflow.py`: 임시 디렉터리에서 안전 작업 Checkpoint 뒤 hard link 별칭을 만들고 거부 결과를 출력하는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`: 기존 Checkpoint의 hard link 별칭 생성과 생성 뒤 원래 인스턴스 load 모두가 명시적 오류로 실패하는 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 별도의 엄격한 Boolean 승인 전에는 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 최신 검증 기록 — JSON Checkpoint hard link 별칭 차단 슬라이스

```text
$ uv run python examples/volume09/json_hard_link_guard_workflow.py
hard_link_rejected=checkpoint file must not have multiple hard links

$ uv run pytest tests/unit/test_volume09_graph.py -q
46 passed in 1.58s

$ uv run pytest -q
107 passed in 2.48s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과

$ git diff --check
(exit 0)
```

## 최신 슬라이스 — JSON Checkpoint checksum 무결성 검사

- `docs/volume09-langgraph/24-json-checkpoint-checksum-integrity.md`
  - 정상 JSON이라도 payload가 저장 후 바뀌면 상태 복원·승인 재개 전에 fail-closed로 차단하는 SHA-256 checksum 계약, 인증과의 차이, 운영 저장소 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 스물네 번째 checksum 무결성 검사 장과 오프라인 예제·검증 범위를 추가했습니다.
- `src/ai_platform/graph/checkpointer.py`
  - JSON schema version을 2로 올리고, `schema_version`과 `checkpoints`의 canonical JSON SHA-256을 `payload_sha256`으로 기록·검증하게 했습니다. checksum 누락·형식 오류·불일치는 `WorkflowState` 복원 전 거부됩니다. 키 없는 checksum은 우발 변경 탐지일 뿐 인증이나 다중 프로세스 원자성을 제공하지 않습니다.
- `examples/volume09/json_checksum_guard_workflow.py`
  - 임시 JSON Checkpoint의 task만 바꿔 JSON 문법은 유지하면서 checksum 불일치가 명시적으로 거부됨을 출력하는 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - 유효 JSON payload를 변경해도 stale checksum이면 load가 실패하는 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 checksum 검증과 별개로 별도의 엄격한 Boolean 승인 전에는 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 최신 검증 기록 — JSON Checkpoint checksum 무결성 검사 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/json_checksum_guard_workflow.py
checksum_mismatch_rejected=checkpoint file checksum does not match its payload

$ uv run pytest tests/unit/test_volume09_graph.py -q
47 passed in 1.53s

$ uv run pytest -q
108 passed in 4.29s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.

## 최신 슬라이스 — JSON Checkpoint checksum 필드 변조 차단

- `docs/volume09-langgraph/25-json-checkpoint-checksum-field-guard.md`
  - payload를 유지한 채 형식은 정상인 64자리 `payload_sha256` 값만 교체해도, canonical payload 재계산 비교가 State 복원과 승인 재개 전에 fail-closed로 거부하는 계약·인증 한계·운영 경계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 스물다섯 번째 checksum 필드 변조 차단 장과 오프라인 예제를 출고 목록에 추가했습니다.
- `examples/volume09/json_checksum_field_guard_workflow.py`
  - 임시 JSON Checkpoint의 payload는 그대로 두고 `payload_sha256`을 `"0" * 64`로 바꿔 명시적인 거부 결과를 출력하는 결정론적 오프라인 데모를 추가했습니다.
- `tests/unit/test_volume09_graph.py`
  - checksum 필드만 교체한 유효 JSON을 `JsonFileCheckpointer.load()`가 `WorkflowState` 복원 전에 거부하는 회귀 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 checksum 검사와 별개로 별도의 엄격한 Boolean 승인 전에는 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 최신 검증 기록 — JSON Checkpoint checksum 필드 변조 차단 슬라이스

실행 위치: `E:\python\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/json_checksum_field_guard_workflow.py
checksum_field_rejected=checkpoint file checksum does not match its payload

$ uv run pytest tests/unit/test_volume09_graph.py::test_json_file_checkpoint_rejects_a_replaced_checksum_field -q
1 passed in 0.50s

$ uv run pytest tests/unit/test_volume09_graph.py -q
48 passed in 0.97s

$ uv run pytest -q
109 passed in 1.76s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.

## 최신 슬라이스 — JSON Checkpoint 중복 키 모호성 차단

- `src/ai_platform/graph/checkpointer.py`
  - `json.loads()`의 `object_pairs_hook`이 최상위·중첩 JSON 객체의 중복 키를 사전 축약 전에 fail-closed로 거부하도록 했습니다. 기본 parser의 마지막 키 채택 때문에 Checkpoint·감사 도구마다 해석이 달라지는 경로를 State 복원·checksum 검증·승인 재개 전에 차단합니다.
- `tests/unit/test_volume09_graph.py`
  - 유효한 Checkpoint의 최상위 `schema_version` 키를 중복해도 `JsonFileCheckpointer.load()`가 `WorkflowState` 복원 전에 명시적 오류로 거부하는 회귀 계약을 추가했습니다.
- `examples/volume09/json_duplicate_key_guard_workflow.py`
  - 임시 디렉터리에 만든 정상 Checkpoint에 중복 `schema_version` 키를 삽입하고 fail-closed 결과를 출력하는 결정론적 오프라인 데모를 추가했습니다.
- `docs/volume09-langgraph/26-json-checkpoint-duplicate-key-guard.md`, `README.md`
  - 중복 키의 parser·감사 모호성, checksum과의 순서, 운영 인증 한계, 오프라인 안전 경계를 문서화하고 출고 목록을 갱신했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 중복 키 검사와 별개로 엄격한 별도 Boolean 승인 전에는 계속 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 최신 검증 기록 — JSON Checkpoint 중복 키 모호성 차단 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run pytest tests/unit/test_volume09_graph.py::test_json_file_checkpoint_rejects_duplicate_json_keys_before_state_restore -q
1 passed in 0.45s

$ uv run python examples/volume09/json_duplicate_key_guard_workflow.py
duplicate_key_rejected=checkpoint file must not contain duplicate object keys

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run pytest tests/unit/test_volume09_graph.py -q
49 passed in 1.03s

$ uv run pytest -q
110 passed in 4.64s

$ uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.

## 최신 슬라이스 — 중첩 감사 이벤트 JSON 키 모호성 차단

- `docs/volume09-langgraph/27-json-checkpoint-nested-event-duplicate-key-guard.md`
  - Checkpoint의 중첩 `events` 객체에 있는 중복 `sequence`가 parser의 값 선택·checksum 비교·State 복원 전에 fail-closed 되는 경계와 인증 한계를 14개 장 템플릿으로 문서화했습니다.
- `docs/volume09-langgraph/README.md`
  - 스물일곱 번째 중첩 감사 이벤트 키 모호성 차단 장과 해당 오프라인 검증 범위를 추가했습니다.
- `examples/volume09/json_duplicate_key_guard_workflow.py`
  - 감사 event가 있는 임시 Checkpoint에 중복 `sequence`를 삽입해 중첩 객체도 명시적으로 거부됨을 출력하도록 확장했습니다.
- `tests/unit/test_volume09_graph.py`
  - 중첩 event의 중복 `sequence`가 checksum과 `WorkflowState` 복원 전에 거부되는 회귀 계약을 추가했습니다.

실제 LLM API 호출, 네트워크 전송, 파일 삭제, 배포, 비밀값 사용은 수행하지 않았습니다. 위험 ActionKind는 JSON 구조 검사와 별개로 계속 별도의 엄격한 Boolean 승인 전에는 `WAITING_FOR_APPROVAL`에 머뭅니다.

## 최신 검증 기록 — 중첩 감사 이벤트 JSON 키 모호성 차단 슬라이스

실행 위치: `E:\\python\\ai-platform-engineering-book-volume-09`

```text
$ uv run python examples/volume09/json_duplicate_key_guard_workflow.py
nested_duplicate_key_rejected=checkpoint file must not contain duplicate object keys

$ uv run pytest tests/unit/test_volume09_graph.py::test_json_file_checkpoint_rejects_a_duplicate_nested_event_key_before_checksum -q
1 passed in 0.54s

$ uv run pytest tests/unit/test_volume09_graph.py -q
50 passed in 0.96s

$ uv run pytest -q
111 passed in 1.58s

$ uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
All checks passed!

$ uv run mypy src/ai_platform/graph
Success: no issues found in 6 source files

$ uv run python scripts/validate_docs.py && uv run python scripts/validate_links.py && uv run python scripts/validate_code_blocks.py && uv run python scripts/check_secrets.py
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과

$ git diff --check
(exit 0)
```

`uv run`은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 모든 검증 명령이 정상 종료했습니다.

## 완료 상태

- Volume 09 전체 PRD DoD는 아직 충족되지 않았습니다. `langgraph`와 `fastapi` 의존성 추가 및 실제 LangGraph·FastAPI 통합은 허용된 수정 범위 밖의 프로젝트 설정 변경을 요구합니다.
- 따라서 `VOLUME09_COMPLETE=true`를 추가하거나 self-pause하지 않았습니다.
