# 08. 실행 중 검토 결정 계약

## 학습 목표

결정론적 Mock이 아닌 사용자 구현 Agent도 실행 중에는 신뢰할 수 없는 경계임을 이해합니다. 이 장을 마치면 `AgentResponse.review`가 `ReviewDecision` 또는 `None`인지 audit trail에 기록하거나 다음 역할을 호출하기 전에 검사할 수 있습니다.

## 문제

`AgentResponse`는 frozen dataclass이지만 Python 런타임은 type annotation을 강제하지 않습니다. 따라서 외부 구현 Agent가 `review="approve"`, `1`, 또는 임의 객체를 반환할 수 있습니다. 문자열 `"approve"`는 올바른 enum처럼 보이더라도 명시적 정책 결정이 아닙니다.

고정 `DeterministicMockAgent` script는 생성 시 이 값을 거절합니다. 그러나 workflow는 Protocol을 만족하는 다른 local Agent도 받을 수 있으므로 실행 경계에서 같은 계약을 다시 확인해야 합니다.

## 안전 규칙

- 모든 `AgentResponse`의 `content`는 비어 있지 않은 문자열이어야 한다.
- 모든 `AgentResponse.review`는 `ReviewDecision.APPROVE`, `ReviewDecision.REVISE`, 또는 `None`이어야 한다.
- 잘못된 `review`는 `AgentProtocolError`로 즉시 종료한다.
- 오류 응답은 audit message로 추가하지 않으며, Researcher·Reviewer·QA·DevOps 같은 다음 역할을 호출하지 않는다.
- `HumanApproval.APPROVED`도 잘못된 Agent 응답을 승인하거나 QA·DevOps로 진행시키지 않는다.

이 규칙은 `BoundedReviewWorkflow`와 `ApprovalGatedReleaseHandoffWorkflow`에 동일하게 적용됩니다. 사람 승인은 유효한 reviewer 승인 뒤의 다음 단계를 허용할 뿐, Agent protocol 오류를 우회하지 않습니다.

## 오프라인 검증

저장소 루트에서 실행합니다.

```bash
uv run pytest tests/volume07/test_runtime_review_decision_contract.py -q
uv run pytest tests/volume07 -q
```

테스트는 live API, 네트워크, secret, 도구 실행, 배포를 사용하지 않습니다. 첫 검증은 잘못된 문자열 review를 반환하는 신뢰할 수 없는 local test double이 후속 역할을 호출하지 못하게 하는지 확인합니다. 두 번째 검증은 Volume 07 전체 오프라인 계약을 확인합니다.

## 핵심 정리

구성 단계 fixture 검증은 신뢰하는 고정 Mock에 적합하고, 실행 단계 protocol 검증은 신뢰할 수 없는 Agent 구현에 필요합니다. 두 경계를 함께 두면 enum처럼 보이는 문자열이나 다른 잘못된 값이 audit trail, bounded loop, 사람 승인 게이트를 통과하지 못합니다.