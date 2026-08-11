# Volume 08. Router 설계

## 목표

사용자 요청과 현재 정책 상태에 따라 적절한 Agent, Tool, Model을 선택하고, 결정 근거와 품질을 검증 가능한 형태로 남깁니다. 모든 실습은 고정 fixture와 로컬 테스트로 먼저 재현합니다. 실제 LLM·임베딩·외부 API 호출은 이 Volume의 기본 경로에 포함하지 않습니다.

## 학습 순서

1. [정책 기반 Router: 기능·비용·지연 시간으로 안전하게 선택하기](01-policy-routing.md)
2. [Keyword Router: confidence threshold와 정책 경계를 함께 적용하기](02-keyword-routing.md)
3. [Keyword Router 평가: 고정 dataset과 accuracy gate](03-keyword-router-evaluation.md)
4. [Policy fallback: retry budget 안에서 fail closed 하기](04-policy-fallback.md)
5. [Semantic Router: 고정 score fixture와 정책 경계](05-semantic-routing.md)
6. [LLM Router: 고정 classifier response와 정책 경계](06-llm-routing.md)
7. [Multi-stage Router: 고정 escalation fixture로 Agent·Tool·Model을 안전하게 전환하기](07-multi-stage-escalation.md)
8. [Router API: 고정 PolicyRouter를 안전한 HTTP 계약으로 노출하기](08-router-api.md)
9. [Router 미니 프로젝트: 고정 fixture로 지원 요청 제어면 조합하기](09-router-mini-project.md)

## 현재 실행 가능한 실습

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume08/policy_router.py
uv run pytest tests/unit/test_volume08_policy_router.py -q
uv run python examples/volume08/keyword_router.py
uv run pytest tests/unit/test_volume08_keyword_router.py -q
uv run python examples/volume08/keyword_router_evaluation.py
uv run pytest tests/unit/test_volume08_router_evaluation.py -q
uv run python examples/volume08/policy_fallback_router.py
uv run pytest tests/unit/test_volume08_policy_fallback_router.py -q
uv run python examples/volume08/semantic_router.py
uv run pytest tests/unit/test_volume08_semantic_router.py -q
uv run python examples/volume08/llm_router.py
uv run pytest tests/unit/test_volume08_llm_router.py -q
uv run python examples/volume08/multi_stage_escalation_router.py
uv run pytest tests/unit/test_volume08_multi_stage_escalation_router.py -q
uv run python examples/volume08/router_api.py
uv run pytest tests/unit/test_volume08_router_api.py -q
uv run python examples/volume08/router_mini_project.py
uv run pytest tests/unit/test_volume08_router_mini_project.py -q
```

열여덟 개 명령은 외부 서비스, API 키, 네트워크 호출 없이 고정된 정책·keyword·semantic·LLM Router 결정, 평가 accuracy gate, 제한된 policy fallback, Agent·Tool·Model 다단계 escalation, 원문 없는 Router API HTTP 계약과 전체 Router 미니 프로젝트 조합을 검증합니다.

## 학습자 체크리스트

Volume 전체 실습 재실행과 학습 목표 확인은 [checklist.md](checklist.md)에서 수행합니다.

## 진행 기록

현재 구현 범위와 다음 작업은 [PROGRESS.md](PROGRESS.md)에서 확인합니다.
