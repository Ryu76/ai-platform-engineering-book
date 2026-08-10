# Volume 09. LangGraph

## 목표

상태 기반 Agent Workflow의 State, Node, Edge, 조건 분기, Checkpoint, Interrupt와 사람 승인을 이해하고, 외부 API·배포·파일 변경 없이 재현 가능한 실행 경계로 검증합니다.

> [!WARNING]
> 이 Volume의 모든 기본 실행은 오프라인·결정론적입니다. `delete`, `deploy`, `send` 같은 위험 작업은 학습용 상태 전이로만 표현하며, 명시적인 사람 승인 없이는 `execute` Node로 이동하지 않습니다. 예제는 실제 삭제·배포·전송을 수행하지 않습니다.

## 현재 학습 장

1. [상태형 Workflow의 학습 목표와 안전 경계](01-learning-objectives.md)
2. [Conditional Edge와 Router 입력을 사용하는 다중 Node Workflow](02-conditional-router-workflow.md)

## 예정 장

이 슬라이스에서는 첫 두 장과 Conditional Edge·Router 검토 기반을 출고했습니다. 이후 장은 Planner-Developer-Reviewer, 제한된 재시도와 Error Node, 영속 Checkpoint, Streaming, Subgraph, FastAPI 연동을 다룹니다.

## 이번 기반 결과물

- `src/ai_platform/graph/state.py`: 불변 State와 감사 이벤트
- `src/ai_platform/graph/nodes.py`: Plan, Router, 전문 역할, 경로 검토, Approval, Execute Node
- `src/ai_platform/graph/workflow.py`: 승인 흐름과 `RoutedWorkflow`의 Conditional Edge 참조 흐름
- `src/ai_platform/graph/checkpointer.py`: 프로세스 내 메모리 Checkpointer

- `examples/volume09/single_node_workflow.py`: 승인 중단 및 재개 데모
- `examples/volume09/router_conditional_workflow.py`: 낮은 신뢰도 Router의 경로 검토와 실행 승인 데모
- `tests/unit/test_volume09_graph.py`: 오프라인 안전·조건 분기 계약 테스트


현재 프로젝트 의존성에는 `langgraph` 패키지가 선언되어 있지 않습니다. 이 Volume의 현재 슬라이스들은 LangGraph API 호출을 가장하지 않고, 해당 API가 모델링하는 상태·Node·Edge·interrupt 경계를 직접 구현한 결정론적 참조 모델입니다. 패키지 추가는 이 작업 범위 밖의 프로젝트 설정 변경이므로, 승인된 별도 변경 후 실제 LangGraph 어댑터 장에서 수행합니다.
