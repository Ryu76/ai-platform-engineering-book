# Volume 08. Router 설계

## 목표

사용자 요청과 현재 정책 상태에 따라 적절한 Agent, Tool, Model을 선택하고, 결정 근거와 품질을 검증 가능한 형태로 남깁니다. 모든 실습은 고정 fixture와 로컬 테스트로 먼저 재현합니다. 실제 LLM·임베딩·외부 API 호출은 이 Volume의 기본 경로에 포함하지 않습니다.

## 학습 순서

1. [정책 기반 Router: 기능·비용·지연 시간으로 안전하게 선택하기](01-policy-routing.md)
2. Rule/Keyword/Semantic/LLM Router, confidence, fallback, escalation (작성 예정)
3. 비용·지연 시간·capability 정책, 다단계 라우팅, 장애 전환 (작성 예정)
4. Router 결정 로그, 평가 dataset, routing accuracy, API (작성 예정)

## 현재 실행 가능한 실습

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume08/policy_router.py
uv run pytest tests/unit/test_volume08_policy_router.py -q
```

두 명령은 외부 서비스, API 키, 네트워크 호출 없이 고정된 정책 Router 결정을 검증합니다.

## 진행 기록

현재 구현 범위와 다음 작업은 [PROGRESS.md](PROGRESS.md)에서 확인합니다.
