# Conditional Edge와 Router 입력을 사용하는 다중 Node Workflow

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Conditional Edge가 State와 Router 입력에 따라 다음 Node를 선택하는 이유를 설명한다.
- 신뢰도 높은 Router 결정을 `research`, `development`, `review` 전문 Node에 연결한다.
- Router 결과가 없거나 신뢰도가 낮을 때 자동 실행 대신 사람 경로 검토(interrupt)로 전환한다.
- 경로 검토와 위험 작업 실행 승인을 서로 다른 안전 경계로 유지한다.
- 외부 Router, LLM, 네트워크 없이 같은 입력에 같은 이벤트 순서가 나오는 테스트를 실행한다.

## 2. 왜 필요한가

하나의 Agent가 모든 요청을 처리하면 역할과 실패 원인이 섞입니다. Router는 요청을 전문 역할로 보낼 수 있지만, Router의 결과가 항상 신뢰할 수 있는 것은 아닙니다. 빈 결과를 임의의 기본 Agent로 보내거나 낮은 신뢰도의 결정을 그대로 실행하면 잘못된 경로에서 위험 작업까지 이어질 수 있습니다.

Conditional Edge는 이 선택을 코드와 State에 드러냅니다. 이 장의 참조 구현은 Router를 직접 호출하지 않습니다. 이미 계산된 `RouterDecision`만 입력으로 받고, 그 입력이 없거나 임계값보다 낮으면 `WAITING_FOR_ROUTE_REVIEW`에서 멈춥니다. 사람은 `review_route()`로 경로만 선택합니다. `send`, `delete`, `deploy`는 경로가 정해진 뒤에도 별도의 실행 승인을 거쳐야 합니다.

## 3. 핵심 개념

- **RouterDecision**: `route`, `confidence`, `source`를 가진 불변 입력입니다. 외부 호출 결과가 아니라 테스트 가능한 값입니다.
- **Conditional Edge**: `decision is None` 또는 `confidence < threshold`이면 사람 검토 Node로, 그렇지 않으면 선택된 전문 Node로 이동하는 규칙입니다.
- **전문 Node**: `research`, `development`, `review` 역할별 처리 Node입니다. 현재는 외부 도구를 호출하지 않고 감사 이벤트만 남깁니다.
- **경로 검토( route review )**: Router의 불확실성을 사람이 해소하는 interrupt입니다. 실행 권한을 부여하지 않습니다.
- **실행 승인(approval)**: 위험 ActionKind를 실제 실행 경로에 보내기 전 별도로 요구하는 interrupt입니다. 이 프로젝트에서는 실행도 문자열을 만드는 시뮬레이션입니다.
- **신뢰도 임계값**: 기본값 `0.80`입니다. `0.80`은 허용되고 `0.79`는 사람 검토가 필요합니다.

> [!WARNING]
> 경로 선택과 위험 작업 승인은 같은 결정이 아닙니다. 사람이 `review` 경로를 선택해도 `SEND`, `DELETE`, `DEPLOY`는 `approved=True` 없이는 `execute` Node에 도달하지 못합니다. 예제는 전송·삭제·배포·외부 API 호출을 수행하지 않습니다.

## 4. 동작 구조

```text
START
  │
  ▼
plan
  │
  ▼
router Conditional Edge
  ├── Router 없음 또는 confidence < 0.80 ─► WAITING_FOR_ROUTE_REVIEW
  │                                               │ 사람의 경로 선택
  │                                               ▼
  └── confidence >= 0.80 ───────────────────► research / development / review
                                                  │
                                                  ▼
                                               approval Conditional Edge
                                      ┌───────────┴───────────┐
                                      ▼                       ▼
                            read / transform            delete / deploy / send
                                      │                       │
                                      ▼                       ▼
                                  execute → END      WAITING_FOR_APPROVAL
                                                              │ 명시적 승인
                                                              ▼
                                                         execute → END
```

`RoutedWorkflow._continue_after_route()`가 전문 Node 선택 뒤에 기존 approval 조건 Edge를 다시 적용합니다. 따라서 RouteKind가 추가되어도 위험 ActionKind의 승인 정책은 우회되지 않습니다.

## 5. 실습 환경

실습 파일은 다음과 같습니다.

- `src/ai_platform/graph/state.py`
- `src/ai_platform/graph/nodes.py`
- `src/ai_platform/graph/workflow.py`
- `examples/volume09/router_conditional_workflow.py`
- `tests/unit/test_volume09_graph.py`

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
uv sync --all-groups
```

이 장에는 `langgraph`, 외부 Router 패키지, API 키가 필요하지 않습니다. 프로젝트의 의존성 설정을 변경하지 마십시오. `RouterDecision`은 Volume 08에서 만들 수 있는 Router 결과를 연결하는 최소 입력 계약이며, 여기서는 손으로 만든 결정론적 값으로 검증합니다.

## 6. 단계별 실습

### 6.1 낮은 신뢰도의 Router 결정 확인

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume09/router_conditional_workflow.py
```

예제는 `review` 경로와 `0.55` 신뢰도를 전달합니다. 임계값 `0.80`보다 낮으므로 `research`, `development`, `review`, `execute` 어느 Node도 처음에는 실행하지 않습니다. `review_route()`가 사람이 선택한 경로를 기록한 뒤 `SEND`가 위험 작업이므로 다시 실행 승인 대기에 멈춥니다. 마지막 단계는 `approved=False`로 거절하며 끝납니다.

### 6.2 높은 신뢰도의 안전 작업 경로 확인

```python
from ai_platform.graph import ActionKind, RouteKind, RoutedWorkflow, RouterDecision

workflow = RoutedWorkflow(confidence_threshold=0.80)
state = workflow.invoke(
    run_id="route-001",
    task="로컬 문자열을 정규화한다",
    action=ActionKind.TRANSFORM,
    router_decision=RouterDecision(route=RouteKind.DEVELOPMENT, confidence=0.92),
)
assert [event.node for event in state.events] == [
    "plan", "router", "development", "approval", "execute"
]
```

`TRANSFORM`은 위험 ActionKind가 아니므로 Router 조건 Edge와 전문 Node를 지난 뒤 완료합니다. 이 코드는 로컬 문자열도 실제로 수정하지 않고 상태 결과만 만듭니다.

### 6.3 계약 테스트와 정적 검사 실행

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/unit/test_volume09_graph.py -q
uv run ruff check src/ai_platform/graph tests/unit/test_volume09_graph.py examples/volume09
uv run mypy src/ai_platform/graph
```

테스트는 높은 신뢰도의 개발 경로, Router 결과 누락 시 사람 검토, 낮은 신뢰도의 위험 작업에서 경로 검토와 실행 승인이 모두 필요한지를 확인합니다.

## 7. 코드 설명

`RouterDecision.__post_init__()`는 신뢰도를 `0.0`부터 `1.0` 범위로 제한하고 빈 출처를 거부합니다. 이 검증은 불완전한 Router 결과가 Node까지 전달되는 것을 막습니다.

```python
if decision is None:
    return waiting_for_route_review
if decision.confidence < confidence_threshold:
    return waiting_for_route_review
return selected_specialist_route
```

`route_node()`는 위 규칙의 감사 이벤트를 남깁니다. 낮은 신뢰도에서는 Router가 제안한 RouteKind를 State에 기록하지 않습니다. `resolve_route_review_node()`만 사람 선택을 `selected_route`에 기록할 수 있습니다. `specialist_node()`는 선택된 RouteKind가 없으면 예외를 내므로, 검토 interrupt를 건너뛸 수 없습니다.

그 후 `approval_node()`는 기존 ActionKind 정책을 사용합니다. 즉, Router 신뢰도가 높아도 위험한 ActionKind에는 승인 대기가 남습니다. 이는 라우팅 정확도와 권한 부여를 분리하는 경계입니다.

## 8. 정상 실행 결과

6.1의 출력은 다음 구조여야 합니다.

```text
Router 검토 전: status=waiting_for_route_review
events=plan | router
경로 검토 후: status=waiting_for_approval
events=plan | router | route_review | review | approval
실행 거절 후: status=rejected
events=plan | router | route_review | review | approval | approval
```

`execute`가 어느 줄에도 나타나지 않는 것이 핵심입니다. 6.3 테스트는 통과한 테스트 수를 출력하고 종료 코드 0으로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `router confidence must be between 0.0 and 1.0` | Router 입력의 신뢰도가 범위를 벗어났습니다. | Router 어댑터에서 정규화하고, 불명확하면 `None` 또는 사람 검토 경로를 사용합니다. |
| `resolve_route_review_node requires a route-review waiting state` | 높은 신뢰도 경로 또는 이미 검토한 run ID에 다시 경로 검토를 요청했습니다. | `WAITING_FOR_ROUTE_REVIEW` Checkpoint에만 `review_route()`를 한 번 호출합니다. |
| `resolve_approval_node requires a waiting state` | 아직 경로 검토 중이거나 안전 작업을 승인 재개하려 했습니다. | 먼저 경로 검토를 끝내고, 위험 작업의 `WAITING_FOR_APPROVAL`에만 `resume()`을 호출합니다. |
| `execute` 이벤트가 너무 일찍 나타남 | 전문 Node 뒤의 approval 조건 Edge를 제거했을 수 있습니다. | `_continue_after_route()`가 `approval_node()`를 거치도록 복원하고 위험 작업 테스트를 실행합니다. |

## 10. 응용 실습

1. `RouteKind`에 `qa`를 추가하고, 해당 Node의 이벤트와 높은 신뢰도 테스트를 먼저 작성합니다.
2. 임계값을 `0.90`으로 올렸을 때 `0.85` 입력이 사람 검토로 이동하는 테스트를 작성합니다.
3. Router 입력의 `source`별로 감사 이벤트를 집계하는 순수 함수를 설계합니다. 실제 로그 전송은 하지 않습니다.

## 11. 실무 적용

실무 Router의 confidence는 모델마다 보정 방식이 달라 단순 숫자 비교만으로 안전을 보장하지 않습니다. 운영 전에는 의도별 평가 데이터로 임계값을 정하고, 낮은 신뢰도의 요청이 어떤 사람 검토 큐로 가는지 정의해야 합니다. 사람 검토 화면에는 원문 전체나 비밀값 대신 최소한의 작업 요약과 제안 경로, 이유, 대상 범위를 표시해야 합니다.

경로 검토자는 권한 승인자가 아닐 수 있습니다. 특히 배포·삭제·외부 전송은 대상, 영향, 롤백, 승인 만료, 승인자 역할을 별도 정책으로 확인해야 합니다. 이 참조 구현은 그러한 부작용을 일절 수행하지 않습니다.

## 12. 과제

- **기본:** `RouterDecision`의 세 필드가 왜 필요한지 한 문장씩 설명합니다.
- **응용:** Router 결과 누락, 낮은 신뢰도, 높은 신뢰도 세 경우의 다음 Node를 표로 작성합니다.
- **심화:** 경로 검토와 실행 승인이 서로 다른 사용자·만료 시간·감사 이벤트를 가져야 하는 이유를 설계 문서로 작성합니다. 실제 인증 또는 전송은 구현하지 않습니다.

## 13. 완료 체크리스트

- [ ] Conditional Edge가 Router 입력에 따라 전문 Node 또는 사람 검토로 분기함을 설명할 수 있다.
- [ ] Router가 없거나 신뢰도가 낮을 때 `WAITING_FOR_ROUTE_REVIEW`에 멈춤을 확인했다.
- [ ] 사람이 선택한 경로만 `selected_route`에 기록됨을 확인했다.
- [ ] 위험 작업이 경로 검토 뒤에도 별도 실행 승인을 요구함을 확인했다.
- [ ] 모든 예제와 테스트가 외부 Router, LLM API, 네트워크, 실제 전송 없이 실행됨을 확인했다.
- [ ] `uv run pytest tests/unit/test_volume09_graph.py -q`를 통과했다.

## 14. 핵심 정리

Conditional Edge는 Router 결과를 맹신해 자동 실행하는 장치가 아니라, 확실한 결정만 다음 Node로 보내고 불확실한 결정은 검토 가능한 interrupt로 전환하는 경계입니다. 이 장의 다중 Node 참조 Workflow는 Router의 경로 선택과 위험 작업의 실행 승인을 분리합니다. 따라서 잘못되거나 누락된 Router 입력이 위험 작업을 승인 없이 통과시키지 못합니다.
