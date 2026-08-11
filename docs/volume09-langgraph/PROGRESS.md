# Volume 09 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 10 — Volume 09 LangGraph**
- 이번 슬라이스: 같은 `MemoryCheckpointer` 인스턴스를 공유하는 8개의 동시 `DEPLOY` 시작 요청에서도 정확히 하나만 `WAITING_FOR_APPROVAL` Checkpoint를 생성하고, 나머지 7개는 `WorkflowRunConflictError`로 끝나는 계약을 추가했습니다. 성공한 run도 별도의 엄격한 Boolean 승인 요청 뒤에만 오프라인 `execute` 시뮬레이션으로 이동합니다. 서버·네트워크·실제 위험 작업은 실행하지 않았습니다.
- 완료 선언: 아직 하지 않음. FastAPI 패키지가 프로젝트 의존성에 없으므로 실제 서버 연동은 승인된 별도 프로젝트 설정 변경이 필요하며, Volume Definition of Done의 나머지 항목도 남아 있습니다.

## 이번에 완료한 파일

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
