# Volume 09. LangGraph

## 목표

상태 기반 Agent Workflow의 State, Node, Edge, 조건 분기, Checkpoint, Interrupt와 사람 승인을 이해하고, 외부 API·배포·파일 변경 없이 재현 가능한 실행 경계로 검증합니다.

> [!WARNING]
> 이 Volume의 모든 기본 실행은 오프라인·결정론적입니다. `delete`, `deploy`, `send` 같은 위험 작업은 학습용 상태 전이로만 표현하며, 명시적인 사람 승인 없이는 `execute` Node로 이동하지 않습니다. 예제는 실제 삭제·배포·전송을 수행하지 않습니다.

## 현재 학습 장

1. [상태형 Workflow의 학습 목표와 안전 경계](01-learning-objectives.md)
2. [Conditional Edge와 Router 입력을 사용하는 다중 Node Workflow](02-conditional-router-workflow.md)
3. [Planner-Developer-Reviewer Workflow와 검토·실행 승인 분리](03-planner-developer-reviewer-workflow.md)
4. [제한된 재시도와 Error Node](04-bounded-retry-error-node.md)
5. [영속 Checkpoint와 안전한 작업 재개](05-persistent-checkpoint-workflow.md)
6. [상태 업데이트 Streaming과 승인 경계](06-streaming-state-updates.md)
7. [부모 Workflow와 Subgraph의 승인 경계](07-parent-subgraph-approval-boundary.md)
8. [FastAPI 요청·응답 어댑터와 승인 경계](08-fastapi-request-response-approval-boundary.md)
9. [run ID 충돌 방지와 재전송 안전성](09-run-id-conflict-approval-safety.md)
10. [원자적 run 생성과 승인 Checkpoint 보존](10-atomic-run-creation.md)
11. [동시 시작 재전송과 승인 대기 상태 보존](11-concurrent-start-approval-safety.md)

## 예정 장

이 슬라이스에서는 같은 메모리 Checkpointer 인스턴스에 대한 동시 재전송도 정확히 하나의 위험 run만 생성하고 승인 대기 Checkpoint를 보존하는 계약을 검증했습니다. FastAPI 의존성 추가와 실제 서버 실행은 승인된 별도 범위에서 다룹니다.

## 이번 기반 결과물

- `src/ai_platform/graph/state.py`: 불변 State와 감사 이벤트, 결정론적 재시도 입력, Node별 상태 Streaming 업데이트
- `src/ai_platform/graph/nodes.py`: Plan, Router, 전문 역할, 경로 검토, Approval, Execute, Error Node
- `src/ai_platform/graph/workflow.py`: 승인 흐름, `StreamingWorkflow`의 Checkpoint 우선 상태 출력, `RoutedWorkflow`의 Conditional Edge 참조 흐름, `PlannerDeveloperReviewerWorkflow`의 고정 역할 순서, `SubgraphWorkflow`의 부모 승인 경계, `RetryWorkflow`의 제한된 재시도, 주입 가능한 Checkpointer 경계
- `src/ai_platform/graph/api.py`: FastAPI route가 사용할 Pydantic 시작·승인 요청, 공개 응답 스냅샷, 재전송이 기존 Checkpoint를 덮어쓰지 못하게 하는 프레임워크 독립 오프라인 어댑터
- `src/ai_platform/graph/checkpointer.py`: 프로세스 내 메모리 Checkpointer와 공개 State만 원자적으로 저장하는 로컬 JSON Checkpointer, 신규 run ID의 첫 상태만 기록하는 `save_if_absent` 계약

- `examples/volume09/single_node_workflow.py`: 승인 중단 및 재개 데모
- `examples/volume09/router_conditional_workflow.py`: 낮은 신뢰도 Router의 경로 검토와 실행 승인 데모
- `examples/volume09/planner_developer_reviewer_workflow.py`: 검토 통과와 위험 작업의 별도 실행 승인 데모
- `examples/volume09/retry_error_workflow.py`: 제한된 재시도와 Error Node 데모
- `examples/volume09/persistent_checkpoint_workflow.py`: 새 Workflow 인스턴스에서의 안전한 로컬 Checkpoint 복원 데모
- `examples/volume09/streaming_workflow.py`: 승인 전·후 Node 상태 업데이트의 고정 순서 데모
- `examples/volume09/subgraph_workflow.py`: Subgraph 검토 통과 뒤에도 부모 실행 승인에서 멈추는 데모
- `examples/volume09/fastapi_adapter_workflow.py`: HTTP 요청·응답 어댑터의 별도 위험 작업 승인 데모
- `tests/unit/test_volume09_graph.py`: 오프라인 안전·조건 분기·역할 순서·Subgraph 부모 승인·재시도 상한·영속 Checkpoint·상태 Streaming·API 어댑터·동시 생성 계약 테스트


현재 프로젝트 의존성에는 `langgraph` 패키지가 선언되어 있지 않습니다. 이 Volume의 현재 슬라이스들은 LangGraph API 호출을 가장하지 않고, 해당 API가 모델링하는 상태·Node·Edge·interrupt 경계를 직접 구현한 결정론적 참조 모델입니다. 패키지 추가는 이 작업 범위 밖의 프로젝트 설정 변경이므로, 승인된 별도 변경 후 실제 LangGraph 어댑터 장에서 수행합니다.
