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
21. [정규화된 JSON 경로 별칭의 동시 시작 안전성](21-json-normalized-path-concurrent-start.md)
22. [정규화된 JSON 경로 별칭의 동시 상반 승인 결정 안전성](22-json-normalized-path-concurrent-mixed-decision.md)
23. [JSON Checkpoint hard link 별칭 차단](23-json-hard-link-alias-guard.md)
24. [JSON Checkpoint checksum 무결성 검사](24-json-checkpoint-checksum-integrity.md)
25. [JSON Checkpoint checksum 필드 변조 차단](25-json-checkpoint-checksum-field-guard.md)
26. [JSON Checkpoint 중복 키 모호성 차단](26-json-checkpoint-duplicate-key-guard.md)
27. [중첩 감사 이벤트 JSON 키 모호성 차단](27-json-checkpoint-nested-event-duplicate-key-guard.md)
28. [동시 Streaming 승인과 단일 오프라인 실행 기록](28-streaming-concurrent-approval-cas.md)
29. [동시 Streaming 거절과 단일 종료 기록](29-streaming-concurrent-rejection-cas.md)

## 예정 장

이 슬라이스에서는 `checkpoints.json`과 `path-alias/../checkpoints.json`처럼 서로 다른 `Path` 표기가 정규화 뒤 같은 JSON 파일을 가리킬 때, 독립 Checkpointer 인스턴스의 동시 `approved=True`·`approved=False` 재전송 중 정확히 하나만 대기 Checkpoint를 소비하도록 경로 단위 Lock과 비교·교체 계약을 검증했습니다. 승자는 `COMPLETED` 또는 `REJECTED` 중 하나로 끝나며 나머지 7개 요청은 종료 Checkpoint·감사 이벤트를 바꾸지 않는 충돌입니다. `COMPLETED`도 오프라인 시뮬레이션일 뿐 실제 위험 실행이 아니고, 이 Lock 보장은 단일 프로세스의 동일 로컬 경로 범위에만 적용됩니다. FastAPI 의존성 추가와 실제 서버 실행은 승인된 별도 범위에서 다룹니다.

현재 슬라이스는 `Path.resolve()`만으로 통합되지 않는 기존 hard link 별칭도 다룹니다. 원자적 `replace()`가 같은 inode의 별칭을 분리하기 전에 link count가 2 이상인 JSON Checkpoint를 fail-closed로 거부합니다. 또한 `schema_version`과 `checkpoints`의 결정론적 SHA-256 checksum을 기록하고, 유효한 JSON이라도 payload 또는 64자리 checksum 필드가 맞지 않으면 상태 복원·승인 재개 전에 거부합니다. 중복 JSON 키도 마지막 값만 조용히 채택하지 않고 모든 중첩 객체에서 거부해 파서·감사 도구 간 해석 모호성을 막습니다. 특히 중첩 `events` 객체의 중복 `sequence`도 checksum 또는 `WorkflowState`의 연속 순서 검증 전에 차단합니다. Streaming 재개는 승인·실행 각 전이를 `save_if_current()`으로 기록해 동시 승인 재전송 중 하나만 `approval | execute` update를 내보내며, 후발 요청은 update를 내보내기 전에 충돌로 끝납니다. 같은 CAS 경계는 동시 거절 재전송에도 적용되어 하나만 `REJECTED`와 `approval` update를 기록하고, 나머지는 update 없이 충돌하며 `execute` 경로는 열리지 않습니다. 이 checksum은 키 없는 우발 변경 탐지일 뿐 인증이나 다중 프로세스 원자성을 제공하지 않으며, 위험 ActionKind는 계속 별도 엄격한 Boolean 승인 전에는 실행되지 않습니다.

## 이번 기반 결과물

- `src/ai_platform/graph/state.py`: 불변 State와 Reducer 기반 감사 이벤트 병합, 결정론적 재시도 입력, Node별 상태 Streaming 업데이트
- `src/ai_platform/graph/nodes.py`: Plan, Router, 전문 역할, 경로 검토, Approval, Execute, Error Node
- `src/ai_platform/graph/workflow.py`: 승인 흐름, `StreamingWorkflow`의 Checkpoint 우선 상태 출력, `RoutedWorkflow`의 Conditional Edge 참조 흐름, `PlannerDeveloperReviewerWorkflow`의 고정 역할 순서, `SubgraphWorkflow`의 부모 승인 경계, `RetryWorkflow`의 제한된 재시도, 주입 가능한 Checkpointer 경계
- `src/ai_platform/graph/api.py`: FastAPI route가 사용할 Pydantic 시작·승인 요청, 공개 응답 스냅샷, 재전송이 기존 Checkpoint를 덮어쓰지 못하게 하는 프레임워크 독립 오프라인 어댑터와 동시 승인 충돌 경계
- `src/ai_platform/graph/checkpointer.py`: 프로세스 내 메모리 Checkpointer와 공개 State만 원자적으로 저장하는 로컬 JSON Checkpointer, 신규 run ID의 첫 상태만 기록하는 `save_if_absent`, 승인 Checkpoint를 비교·교체하는 `save_if_current`, 같은 프로세스의 동일 정규화 JSON 경로를 여는 인스턴스가 공유하는 Lock 계약, 우발적 payload 변경을 복원 전에 차단하는 결정론적 SHA-256 checksum

- `examples/volume09/single_node_workflow.py`: 승인 중단 및 재개 데모
- `examples/volume09/router_conditional_workflow.py`: 낮은 신뢰도 Router의 경로 검토와 실행 승인 데모
- `examples/volume09/planner_developer_reviewer_workflow.py`: 검토 통과와 위험 작업의 별도 실행 승인 데모
- `examples/volume09/retry_error_workflow.py`: 제한된 재시도와 Error Node 데모
- `examples/volume09/persistent_checkpoint_workflow.py`: 새 Workflow 인스턴스에서의 안전한 로컬 Checkpoint 복원 데모
- `examples/volume09/streaming_workflow.py`: 승인 전·후 Node 상태 업데이트의 고정 순서 데모
- `examples/volume09/streaming_concurrent_approval_workflow.py`: 8개 동시 Streaming 승인 중 하나만 오프라인 실행 update를 기록하는 데모
- `examples/volume09/streaming_concurrent_rejection_workflow.py`: 8개 동시 Streaming 거절 중 하나만 종료 update를 기록하고 execute를 생략하는 데모
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
- `examples/volume09/json_normalized_path_concurrent_start_workflow.py`: 서로 다른 경로 표기가 정규화 뒤 같은 JSON 파일을 가리킬 때 독립 Checkpointer 인스턴스 8개가 하나만 위험 작업의 승인 대기를 생성하는 데모
- `examples/volume09/json_normalized_path_concurrent_mixed_decision_workflow.py`: 서로 다른 경로 표기가 정규화 뒤 같은 JSON 파일을 가리킬 때 독립 Checkpointer 인스턴스의 동시 승인·거절 재전송 중 하나만 종료 결정을 기록하는 데모
- `examples/volume09/json_hard_link_guard_workflow.py`: 기존 hard link 별칭이 있는 JSON Checkpoint를 분리 저장 전에 명시적으로 거부하는 데모
- `examples/volume09/json_checksum_guard_workflow.py`: 정상 JSON의 payload가 기록된 SHA-256 checksum과 다르면 상태 복원 전에 거부하는 데모
- `examples/volume09/json_checksum_field_guard_workflow.py`: payload를 그대로 둔 채 교체된 checksum 필드도 상태 복원 전에 거부하는 데모
- `examples/volume09/json_duplicate_key_guard_workflow.py`: 중첩 감사 이벤트의 중복 JSON 키가 있는 Checkpoint를 상태 복원 전에 거부하는 데모
- `tests/unit/test_volume09_graph.py`: 오프라인 안전·조건 분기·역할 순서·Subgraph 부모 승인·재시도 상한·영속 Checkpoint·상태 Streaming·Streaming 동시 승인·거절 CAS·API 어댑터·동시 생성·메모리·JSON 단일/공유·정규화 경로 인스턴스 동시 승인·거절·시작·상반 결정·payload·checksum 필드 불일치·최상위·중첩 중복 키 차단 계약 테스트

현재 프로젝트 의존성에는 `langgraph` 패키지가 선언되어 있지 않습니다. 이 Volume의 현재 슬라이스들은 LangGraph API 호출을 가장하지 않고, 해당 API가 모델링하는 상태·Node·Edge·interrupt 경계를 직접 구현한 결정론적 참조 모델입니다. 패키지 추가는 이 작업 범위 밖의 프로젝트 설정 변경이므로, 승인된 별도 변경 후 실제 LangGraph 어댑터 장에서 수행합니다.
