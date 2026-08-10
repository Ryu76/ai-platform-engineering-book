# Volume 09 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 10 — Volume 09 LangGraph**
- 이번 슬라이스: 제한된 재시도와 Error Node를 추가했습니다. 결정론적 실패 계획이 상한 안에서는 실행 시뮬레이션으로 한 번씩만 되돌아가고, 상한 소진 시 별도 `FAILED` END로 종료됩니다. 위험 작업은 재시도 계획이 있어도 사람 실행 승인 전 시도 0회로 중단됩니다.
- 완료 선언: 아직 하지 않음. PRD의 Volume 09 필수 실습(영속 Checkpoint, Streaming, Subgraph, FastAPI 연동)과 Volume Definition of Done의 나머지 항목이 남아 있습니다.

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
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 검증 경로는 외부 API와 네트워크를 사용하지 않았습니다.

## 알려진 차단 사항

- `pyproject.toml`에는 `langgraph` 의존성이 없습니다. 이번 작업의 수정 허용 범위는 Volume 09 문서·예제·테스트와 `src/ai_platform/graph/`이므로 프로젝트 의존성을 임의로 추가하지 않았습니다. 따라서 이번 구현은 LangGraph API 실행이 아니라 개념·안전 계약을 검증하는 직접 구현 참조 모델입니다.
- Volume 09의 전체 PRD DoD가 충족되지 않았습니다. `VOLUME09_COMPLETE=true`를 추가하거나 작업을 self-pause하지 않았습니다.

## 다음 작업

- 다음 장에서 프로세스 종료 뒤에도 재개 가능한 영속 Checkpoint를 추가하고, 저장 범위·run ID·민감정보 제외·위험 ActionKind의 별도 사람 승인 경계를 오프라인 테스트로 고정합니다.
