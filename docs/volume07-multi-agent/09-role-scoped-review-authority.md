# 09. 역할 범위 검토 권한

## 1. 학습 목표

검토 결정은 어떤 역할도 표현할 수 있는 일반 메시지가 아니라 Reviewer에게만 부여된 권한임을 이해합니다. 이 장을 마치면 Reviewer 외 역할이 `ReviewDecision`을 반환할 때 audit trail과 후속 역할 호출 전에 안전하게 중단되는 이유를 설명할 수 있습니다.

## 2. 왜 필요한가

`AgentResponse.review`는 Python의 type annotation만으로 역할 권한을 표현할 수 없습니다. Planner가 `ReviewDecision.APPROVE`를 반환해도 enum의 형식 자체는 올바릅니다. 그러나 Planner의 계획은 검토 승인과 다른 책임입니다.

권한을 역할과 분리하면 audit trail에 누가 어떤 결정을 했는지가 흐려집니다. 특히 QA의 응답에 review 결정이 포함되면 DevOps handoff 직전에 잘못된 권한 주장이 기록될 수 있습니다. 따라서 workflow는 값의 형식뿐 아니라 해당 역할이 그 값을 낼 수 있는지도 확인해야 합니다.

## 3. 핵심 개념

- **형식 계약:** `review` 값은 `ReviewDecision` 또는 `None`이어야 합니다.
- **역할 권한 계약:** `ReviewDecision.APPROVE`와 `ReviewDecision.REVISE`는 Reviewer만 반환할 수 있습니다.
- **Reviewer 결정:** Reviewer는 `APPROVE` 또는 `REVISE` 중 하나를 반드시 명시해야 합니다. `None`은 유효한 검토 결과가 아닙니다.
- **fail-closed:** 권한 위반 또는 결정 누락은 `AgentProtocolError`로 즉시 종료합니다. fallback, 추가 반복, 다음 역할 호출은 하지 않습니다.
- **사람 승인:** `HumanApproval.APPROVED`는 유효한 Reviewer 승인 뒤 QA와 로컬 handoff를 허용할 뿐, 역할 권한을 부여하지 않습니다.

## 4. 동작 구조

```text
각 role의 AgentResponse
          |
          v
content / review 형식 검사
          |
          v
role별 review 권한 검사
  | Reviewer                         | Planner / Researcher / Developer / QA / DevOps
  v                                  v
APPROVE 또는 REVISE 확인        review는 반드시 None
  |                                  |
  +------------- 정상 ---------------+
                  |
                  v
            audit trail 추가
                  |
                  v
          bounded loop 또는 승인 게이트

권한 위반 / Reviewer 결정 누락
          |
          v
AgentProtocolError (후속 역할 호출 없음)
```

## 5. 실습 환경

- Python 3.12 이상과 프로젝트의 `uv` 환경이 필요합니다.
- 명령 실행 위치는 저장소 루트의 bash 또는 WSL 터미널입니다.
- 실습은 결정론적 local Mock만 사용합니다. live API, 네트워크, secret, 도구 실행, 배포는 사용하지 않습니다.

## 6. 단계별 실습

먼저 역할 권한 계약을 검증합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07/test_runtime_review_decision_contract.py -q
```

이 테스트는 고정 Mock 생성자 검증을 통과하지 않는 local test double을 사용해 runtime 경계를 확인합니다. Planner가 `ReviewDecision.APPROVE`를 반환하면 Researcher는 호출되지 않습니다. Release handoff에서 QA가 같은 결정을 반환하면 DevOps는 호출되지 않습니다.

전체 Volume 07 오프라인 계약도 확인합니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run pytest tests/volume07 -q
```

## 7. 코드 설명

두 workflow의 `_validate_role_response()`는 먼저 기존 `_validate_response()`로 `AgentResponse`, 비어 있지 않은 `content`, `review` enum 형식을 검사합니다. 그 뒤 역할별 정책을 적용합니다.

```python
if role != "reviewer" and response.review is not None:
    raise AgentProtocolError(f"{role} response must not include a review decision")
if role == "reviewer" and response.review not in (
    ReviewDecision.APPROVE,
    ReviewDecision.REVISE,
):
    raise AgentProtocolError("reviewer response must include an explicit review decision")
```

검증은 `AgentMessage`를 추가하기 전에 수행됩니다. 따라서 권한 위반 응답은 audit trail에 남지 않고, 다음 Agent가 이전 응답을 context로 받지 않습니다.

## 8. 정상 실행 결과

정상 환경에서는 첫 명령이 exit code `0`으로 종료합니다. 출력의 테스트 수는 이후 계약 추가에 따라 달라질 수 있습니다. 확인 기준은 모든 테스트 통과와 다음 두 경계입니다.

- Planner의 review 권한 주장 뒤 Researcher·Developer·Reviewer·QA 호출 수는 모두 `0`입니다.
- QA의 review 권한 주장 뒤 DevOps 호출 수는 `0`입니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `planner response must not include a review decision` | Planner가 `review=ReviewDecision.APPROVE` 또는 `REVISE`를 반환함 | Planner 응답에서 `review`를 제거하거나 `None`으로 둡니다. |
| `qa response must not include a review decision` | QA가 Reviewer 권한을 주장함 | QA 결과는 검사 내용만 `content`에 기록하고 review 결정은 넣지 않습니다. |
| `reviewer response must include an explicit review decision` | Reviewer가 `review=None`을 반환함 | Reviewer script 또는 구현이 `APPROVE` 또는 `REVISE`를 반환하게 합니다. |
| `agent response review must be a ReviewDecision or None` | 문자열 `"approve"` 같은 runtime 값 사용 | `ReviewDecision.APPROVE` 또는 `ReviewDecision.REVISE` enum을 사용합니다. |

> [!WARNING]
> 승인 플래그를 전달했다고 해서 Agent 출력의 형식이나 역할 권한 검증을 생략하면 안 됩니다. 사람 승인은 영향 있는 다음 단계의 게이트이며, 손상된 Agent protocol을 복구하는 수단이 아닙니다.

## 10. 응용 실습

1. Researcher가 `ReviewDecision.REVISE`를 반환하는 local test double을 만들고 Developer가 호출되지 않는지 확인합니다.
2. DevOps가 review 결정을 포함하는 경우 local handoff note가 생성되지 않는 테스트를 작성합니다.
3. Reviewer가 `None`을 반환하는 기존 테스트에서 audit message 수가 reviewer 응답 전까지로 유지되는지 확인합니다.

## 11. 실무 적용

실제 시스템에서는 역할 이름만 신뢰하지 말고 인증된 identity와 정책을 함께 사용해야 합니다. 이 교재의 offline Mock은 권한 모델의 최소 형태입니다. production 환경에서는 역할별 입력 schema, identity binding, 권한 변경 audit, 그리고 영향 있는 작업 전 사람 승인까지 확장해야 합니다.

> [!TIP]
> 결과 형식 검증과 권한 검증을 별도 단계로 유지하십시오. 형식이 올바른 값도 잘못된 주체가 반환하면 거절해야 하며, 권한이 있는 주체도 잘못된 형식을 반환하면 거절해야 합니다.

## 12. 과제

- **기본:** Developer가 review 결정을 반환할 때 Reviewer가 호출되지 않는 test를 작성합니다.
- **응용:** Release handoff의 DevOps가 review 결정을 반환할 때 `handoff_note`가 생성되지 않는 test를 작성합니다.
- **심화:** 역할 권한 정책을 별도 immutable mapping으로 모델링하고, mapping 자체가 변경 불가능한지 구성 단계 테스트를 추가합니다.

## 13. 완료 체크리스트

- [ ] `ReviewDecision`의 형식 계약과 역할 권한 계약을 구분할 수 있다.
- [ ] Reviewer만 `APPROVE` 또는 `REVISE`를 반환해야 함을 설명할 수 있다.
- [ ] Planner 또는 QA의 review 결정이 audit trail과 후속 역할 전에 중단됨을 확인했다.
- [ ] `HumanApproval.APPROVED`가 protocol 오류를 우회하지 않음을 확인했다.
- [ ] Volume 07 오프라인 테스트를 통과시켰다.

## 14. 핵심 정리

검토 결정은 값의 enum 여부만으로 안전하지 않습니다. 해당 결정을 낼 수 있는 역할도 함께 검증해야 합니다. runtime에서 형식과 역할 권한을 audit 기록 전에 fail-closed하면 bounded loop, 메시지 전달, 사람 승인 게이트의 책임 경계를 명확하게 유지할 수 있습니다.
