# 05. 구성 단계 Agent 경계 검증

## 학습 목표

다중 Agent 워크플로는 실행 전에 각 역할 경계가 실제로 호출 가능한지 확인해야 합니다. 타입 힌트의 `Agent`, `ConflictAgent`, `DelegatedWorker` Protocol만으로는 런타임 객체가 `act()` 또는 `propose()`를 제공한다는 보장이 없습니다. 이 장은 잘못된 역할 객체를 첫 workflow 실행이나 후속 역할 호출까지 미루지 않고 구성 단계에서 fail-closed로 거절하는 방법을 다룹니다.

## 안전 경계

- `BoundedReviewWorkflow`와 `ApprovalGatedReleaseHandoffWorkflow`는 Planner·Researcher·Developer·Reviewer·QA·DevOps 역할마다 호출 가능한 `act(context)` 경계를 요구합니다.
- `ApprovalGatedDelegationWorkflow`는 호출 가능한 Coordinator `propose(context)`와 assignee별 Worker `act(context)`를 요구합니다. `workers`는 mapping이어야 하며 allow-list는 실행 중 변경될 수 없는 non-empty `frozenset`입니다.
- `BoundedConflictResolutionWorkflow`는 role-to-agent mapping과 역할별 호출 가능한 `propose(context)` 경계를 요구합니다.
- 구성 검증은 Agent를 호출하지 않습니다. 잘못된 역할 객체는 `WorkflowConfigurationError`가 되고, 계획·Worker·peer Agent·QA·DevOps는 실행되지 않습니다.
- 이 검증은 인터페이스 존재와 호출 가능성만 확인합니다. 응답의 `AgentResponse`, `WorkerResponse`, `ConflictProposal` 형식과 비어 있지 않은 내용은 기존 실행 시점 protocol 검증이 계속 담당합니다.

## 왜 구성 단계에서 중단하는가

Agent 인스턴스 대신 `None`, 일반 객체, 또는 `act`/`propose`가 아닌 속성이 전달되면 나중에 `AttributeError`가 발생할 수 있습니다. 그 시점까지 앞선 역할이 이미 실행됐다면 audit trail은 부분적으로만 남고 다음 실행을 사람이 판단하기 어렵습니다. 생성자에서 경계를 확인하면 workflow가 아직 어떤 역할도 호출하지 않은 상태에서 원인을 명확히 알리고, 재시도 또는 fallback을 암묵적으로 수행하지 않습니다.

## 오프라인 검증

저장소 루트에서 다음을 실행합니다.

```bash
uv run pytest tests/volume07/test_agent_boundary_configuration.py -q
```

이 테스트는 네 workflow가 non-callable 역할 경계를 거절하고, 유효한 결정론적 Mock 경계는 approval 대기까지 정상적으로 구성·실행되는지 확인합니다. 네트워크, API key, secret, 도구 실행, 배포는 사용하지 않습니다.

전체 Volume 07 계약 검증은 다음과 같습니다.

```bash
uv run pytest tests/volume07 -q
```

## 핵심 정리

구성 검증은 사람 승인을 대체하지 않습니다. 안전한 순서는 (1) 호출 가능한 로컬 역할 경계 구성, (2) bounded loop와 response protocol 검증, (3) 영향 있는 다음 단계 전에 명시적 사람 승인입니다. 구성 오류는 어떤 Agent 호출보다 먼저 종료하고, 승인 없는 실행은 QA·Worker·DevOps 같은 다음 단계를 호출하지 않습니다.
