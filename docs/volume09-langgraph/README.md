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
12. [State Reducer와 결정론적 감사 이벤트 병합](12-state-reducer-audit-events.md)
13. [동시 승인 재전송과 단일 오프라인 실행 기록](13-concurrent-approval-single-execution.md)
14. [단일 JSON Checkpointer 인스턴스의 동시 승인 안전성](14-json-checkpoint-concurrent-approval.md)
15. [단일 JSON Checkpointer 인스턴스의 동시 시작 안전성](15-json-checkpoint-concurrent-start.md)
16. [동일 JSON 경로의 독립 Checkpointer 동시 시작 안전성](16-json-shared-path-concurrent-start.md)
17. [동일 JSON 경로의 독립 Checkpointer 동시 승인 안전성](17-json-shared-path-concurrent-approval.md)
18. [동일 JSON 경로의 독립 Checkpointer 동시 거절 안전성](18-json-shared-path-concurrent-rejection.md)
19. [정규화된 JSON 경로 별칭의 동시 승인 안전성](19-json-normalized-path-concurrent-approval.md)
20. [정규화된 JSON 경로 별칭의 동시 거절 안전성](20-json-normalized-path-concurrent-rejection.md)

## 예정 장

이 슬라이스에서는 서로 다른 `Path` 표기(`path-alias/../checkpoints.json`)라도 정규화 뒤 같은 JSON 파일을 가리키면, 독립 Checkpointer 인스턴스의 동시 거절 요청 중 정확히 하나만 위험 작업의 승인 대기 Checkpoint를 `REJECTED`로 소비하도록 경로 단위 Lock과 비교-교체 계약을 검증했습니다. 중복 요청은 기존 Action·거절 상태·감사 이벤트를 바꾸지 않고 충돌로 끝나며, 어떤 요청도 `execute`를 기록하지 않습니다. 이 Lock 보장은 단일 프로세스의 동일 로컬 경로 범위에만 적용되며, FastAPI 의존성 추가와 실제 서버 실행은 승인된 별도 범위에서 다룹니다.

## 이번 기반 결과물

- `src/ai_platform/graph/state.py`: 불변 State와 Reducer 기반 감사 이벤트 병합, 결정론적 재시도 입력, Node별 상태 Streaming 업데이트
- `src/ai_platform/graph/nodes.py`: Plan, Router, 전문 역할, 경로 검토, Approval, Execute, Error Node
- `src/ai_platform/graph/workflow.py`: 승인 흐름, `StreamingWorkflow`의 Checkpoint 우선 상태 출력, `RoutedWorkflow`의 Conditional Edge 참조 흐름, `PlannerDeveloperReviewerWorkflow`의 고정 역할 순서, `SubgraphWorkflow`의 부모 승인 경계, `RetryWorkflow`의 제한된 재시도, 주입 가능한 Checkpointer 경계
- `src/ai_platform/graph/api.py`: FastAPI route가 사용할 Pydantic 시작·승인 요청, 공개 응답 스냅샷, 재전송이 기존 Checkpoint를 덮어쓰지 못하게 하는 프레임워크 독립 오프라인 어댑터와 동시 승인 충돌 경계
- `src/ai_platform/graph/checkpointer.py`: 프로세스 내 메모리 Checkpointer와 공개 State만 원자적으로 저장하는 로컬 JSON Checkpointer, 신규 run ID의 첫 상태만 기록하는 `save_if_absent`, 승인 Checkpoint를 비교·교체하는 `save_if_current`, 같은 프로세스의 동일 정규화 JSON 경로를 여는 인스턴스가 공유하는 Lock 계약

- `examples/volume09/single_node_workflow.py`: 승인 중단 및 재개 데모
- `examples/volume09/router_conditional_workflow.py`: 낮은 신뢰도 Router의 경로 검토와 실행 승인 데모
- `examples/volume09/planner_developer_reviewer_workflow.py`: 검토 통과와 위험 작업의 별도 실행 승인 데모
- `examples/volume09/retry_error_workflow.py`: 제한된 재시도와 Error Node 데모
- `examples/volume09/persistent_checkpoint_workflow.py`: 새 Workflow 인스턴스에서의 안전한 로컬 Checkpoint 복원 데모
- `examples/volume09/streaming_workflow.py`: 승인 전·후 Node 상태 업데이트의 고정 순서 데모
- `examples/volume09/subgraph_workflow.py`: Subgraph 검토 통과 뒤에도 부모 실행 승인에서 멈추는 데모
- `examples/volume09/fastapi_adapter_workflow.py`: HTTP 요청·응답 어댑터의 별도 위험 작업 승인 데모
- `examples/volume09/concurrent_approval_workflow.py`: 동시 승인 재전송 중 정확히 하나만 오프라인 실행 결과를 기록하는 데모
- `examples/volume09/json_concurrent_approval_workflow.py`: 하나의 JSON Checkpointer 인스턴스가 8개 동시 승인 중 하나만 소비하는 데모
- `examples/volume09/json_concurrent_start_workflow.py`: 하나의 JSON Checkpointer 인스턴스가 8개 동시 시작 중 하나만 위험 작업의 승인 대기를 생성하는 데모
- `examples/volume09/json_shared_path_concurrent_start_workflow.py`: 같은 JSON 경로를 여는 독립 Checkpointer 인스턴스 8개가 하나만 위험 작업의 승인 대기를 생성하는 데모
- `examples/volume09/json_shared_path_concurrent_approval_workflow.py`: 같은 JSON 경로를 여는 독립 Checkpointer 인스턴스 8개가 하나만 위험 작업의 승인 대기를 소비하는 데모
- `examples/volume09/json_shared_path_concurrent_rejection_workflow.py`: 같은 JSON 경로를 여는 독립 Checkpointer 인스턴스 8개가 하나만 위험 작업의 승인 대기를 거절하는 데모
- `examples/volume09/json_normalized_path_concurrent_approval_workflow.py`: 서로 다른 경로 표기가 정규화 뒤 같은 JSON 파일을 가리킬 때 독립 Checkpointer 인스턴스 8개가 하나만 위험 작업의 승인 대기를 소비하는 데모
- `examples/volume09/json_normalized_path_concurrent_rejection_workflow.py`: 서로 다른 경로 표기가 정규화 뒤 같은 JSON 파일을 가리킬 때 독립 Checkpointer 인스턴스 8개가 하나만 위험 작업의 승인 대기를 거절하는 데모
- `tests/unit/test_volume09_graph.py`: 오프라인 안전·조건 분기·역할 순서·Subgraph 부모 승인·재시도 상한·영속 Checkpoint·상태 Streaming·API 어댑터·동시 생성·메모리·JSON 단일/공유·정규화 경로 인스턴스 동시 승인·거절·시작 계약 테스트


현재 프로젝트 의존성에는 `langgraph` 패키지가 선언되어 있지 않습니다. 이 Volume의 현재 슬라이스들은 LangGraph API 호출을 가장하지 않고, 해당 API가 모델링하는 상태·Node·Edge·interrupt 경계를 직접 구현한 결정론적 참조 모델입니다. 패키지 추가는 이 작업 범위 밖의 프로젝트 설정 변경이므로, 승인된 별도 변경 후 실제 LangGraph 어댑터 장에서 수행합니다.
