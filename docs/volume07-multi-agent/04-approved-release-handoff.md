# 04. 승인 게이트가 있는 로컬 Release Handoff

## 1. 학습 목표

Planner, Developer, Reviewer, QA, DevOps의 역할을 하나의 자동 권한으로 합치지 않고, 검토가 끝난 release candidate를 사람 승인 뒤에만 QA와 DevOps handoff로 넘기는 구조를 구현합니다. 여기서 `completed`는 **로컬 handoff note가 준비되었음**만 뜻하며 배포·네트워크 요청·도구 실행을 뜻하지 않습니다.

## 2. 왜 필요한가

Reviewer의 `approve`를 배포 권한으로 해석하면 잘못된 후보가 운영 변경으로 이어질 수 있습니다. 역할을 나누어도 메시지와 결과가 다음 역할로 어떻게 전달되는지, 재작업이 언제 끝나는지, 누가 다음 단계를 허용하는지가 명시되지 않으면 안전하지 않습니다. 이 slice는 QA와 DevOps가 소비하는 결과를 immutable audit trail로 한정하고 사람의 명시 승인을 별도 경계로 둡니다.

## 3. 핵심 개념

- **Agent role**: Planner는 범위를 제안하고, Developer는 후보를 만들고, Reviewer는 `approve` 또는 `revise`만 결정합니다. QA는 검증 결과를, DevOps는 실행하지 않는 handoff note를 남깁니다.
- **State와 message passing**: 각 호출은 이전 `AgentMessage`의 tuple만 읽습니다. Agent가 공유 전역 상태나 장기 메모리를 수정하지 않습니다.
- **작업 결과 공유**: Reviewer는 Developer 메시지를, QA는 Reviewer 메시지를, DevOps는 QA 메시지를 읽습니다. 이는 순서와 근거를 재현할 수 있게 합니다.
- **종료 조건**: Developer/Reviewer 쌍은 `max_review_cycles`까지만 반복합니다. 상한에 도달하면 `review_limit_reached`로 멈춥니다.
- **Human-in-the-loop**: `HumanApproval.PENDING`은 QA와 DevOps를 호출하지 않습니다. `APPROVED`만 해당 역할을 허용하고, `REJECTED`는 모든 역할보다 먼저 종료합니다.

## 4. 동작 구조

```text
local task
  │
  ▼
Planner ──► Developer ◄──── Reviewer: revise
              │                  │
              └──────────────────┘  (max_review_cycles)
                                 │ Reviewer: approve
                                 ▼
                    awaiting_human_approval
                     │                 │
             REJECTED│                 │APPROVED
                     ▼                 ▼
              human_rejected       QA ──► DevOps handoff note
                                        (no deployment or tool execution)
```

## 5. 실습 환경

Windows 10/11, Python 3.12 이상과 `uv`를 사용합니다. 저장소 루트 `E:\python\ai-platform-engineering-book-volume-07`에서 실행합니다. 필요한 파일은 다음과 같으며 API key, `.env`, 네트워크 연결, Docker, 배포 대상이 필요하지 않습니다.

```text
src/ai_platform/agents/release_handoff.py
examples/volume07/offline_release_handoff.py
tests/volume07/test_approval_gated_release_handoff.py
```

## 6. 단계별 실습

먼저 승인 없이 audit trail만 봅니다.

```bash
uv run python examples/volume07/offline_release_handoff.py
```

첫 줄은 다음과 같고 `qa:` 또는 `devops:` 줄은 출력되지 않아야 합니다.

```text
status=awaiting_human_approval
```

사람이 Planner, Developer, Reviewer 메시지를 검토한 뒤에만 아래 명령을 실행합니다.

```bash
uv run python examples/volume07/offline_release_handoff.py --approve
```

`--approve`는 예제 실행자가 제공하는 명시적인 로컬 승인 입력입니다. 그래도 실제 배포는 수행하지 않습니다.

계약 테스트도 실행합니다.

```bash
uv run pytest tests/volume07/test_approval_gated_release_handoff.py -q
```

## 7. 코드 설명

`ApprovalGatedReleaseHandoffWorkflow.run()`은 먼저 Planner를 한 번 호출하고, Developer/Reviewer를 `range(1, max_review_cycles + 1)`로 제한합니다. Reviewer가 `REVISE`면 다음 cycle만 허용하고, 그 외 누락된 결정은 `AgentProtocolError`로 fail-closed합니다.

Reviewer가 승인해도 기본값 `PENDING`이면 즉시 결과를 반환합니다. 따라서 QA/DevOps 호출 코드는 `APPROVED` 분기 안에만 있습니다. 각 호출은 `AgentContext(..., tuple(messages))`를 받아 읽기 전용 audit trail만 볼 수 있고, `_validate_response()`는 빈 내용이나 다른 응답 타입을 다음 역할 전에 거절합니다.

## 8. 정상 실행 결과

승인된 실행은 아래와 같은 순서를 보입니다.

```text
status=completed
handoff_note=Handoff: local release notes are ready; no deployment ran.
0:planner: Plan: prepare a local release candidate.
1:developer: Draft: bounded handoff implementation.
1:reviewer: Review: the candidate is ready for QA.
1:qa: QA: deterministic checks passed.
1:devops: Handoff: local release notes are ready; no deployment ran.
```

`completed`와 마지막 `devops` 줄은 handoff 문서가 준비되었다는 확인입니다. 배포 로그, 외부 API 결과, secret, live tool 결과는 이 예제에 존재하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `ModuleNotFoundError: ai_platform` | 저장소 루트가 아닌 위치에서 실행했을 수 있습니다. | 루트로 이동한 뒤 `uv run ...`을 사용합니다. |
| `review_limit_reached` | 모든 제한된 cycle에서 Reviewer가 `revise`를 반환했습니다. | 자동으로 cycle을 늘리지 말고 audit trail을 사람이 검토합니다. |
| `AgentProtocolError` | Mock script가 소진됐거나 빈/잘못된 응답이 반환됐습니다. | 필요한 고정 응답 수와 response contract를 테스트에서 명시합니다. |
| QA/DevOps 줄이 없음 | `--approve`가 없거나 사람이 거절했습니다. | 검토 후에만 명시 승인하고, 거절이면 새 후보를 만듭니다. |

## 10. 응용 실습

1. Developer의 첫 후보를 `revise`, 두 번째 후보를 `approve`하도록 fixed script를 바꾸고 정확히 두 cycle에서 끝나는지 테스트하세요.
2. DevOps handoff note에 ticket ID 같은 로컬 식별자를 추가하되 비밀값이나 실제 실행 명령은 포함하지 마세요.
3. 빈 QA 응답을 반환하는 test double을 만들고 DevOps가 호출되지 않는 계약 테스트를 추가하세요.

## 11. 실무 적용

직접 구현은 role, message schema, retry/loop bound, approval 입력, fail-closed 상태를 코드에서 작게 드러내므로 학습과 단위 테스트에 적합합니다. Hermes 같은 Agent runtime을 사용할 때도 같은 책임은 사라지지 않습니다. 역할 정의, 허용 도구, 실행 상한, audit 저장 위치, 사람 승인 정책을 runtime 설정과 운영 절차로 각각 확인해야 합니다.

이 예제는 Hermes를 호출하거나 설정을 변경하지 않습니다. 따라서 실제 Hermes 구성과 비교할 때는 이 코드의 `AgentContext`, `max_review_cycles`, `HumanApproval`, immutable audit trail을 비교 기준으로 사용하고, 현재 runtime 기능과 설정 방법은 해당 환경의 최신 공식 문서에서 확인해야 합니다. 배포 권한은 handoff note와 별도 승인·최소 권한 실행 경계에 둡니다.

## 12. 과제

- **기본**: PENDING 실행에서 QA와 DevOps call history가 빈 이유를 설명하세요.
- **응용**: Reviewer가 계속 `revise`할 때 총 Developer/Reviewer 호출 수가 어떤 상한을 갖는지 테스트로 고정하세요.
- **심화**: 사람 승인을 단순 boolean으로 우회하지 않는 별도 승인 레코드 모델을 설계하세요. 단, 실제 API, secret, 배포, 외부 데이터 전송은 추가하지 마세요.

## 13. 완료 체크리스트

- [ ] `uv run python examples/volume07/offline_release_handoff.py`에서 approval 대기와 QA/DevOps 미호출을 확인했다.
- [ ] `--approve`가 local handoff note만 만들고 배포하지 않는다는 점을 설명할 수 있다.
- [ ] 재작업 상한과 `review_limit_reached` fail-closed 동작을 확인했다.
- [ ] QA와 DevOps가 이전 역할의 immutable 메시지를 읽는 순서를 확인했다.
- [ ] `uv run pytest tests/volume07/test_approval_gated_release_handoff.py -q`를 실행했다.

## 14. 핵심 정리

Multi-Agent 설계에서 역할 분리만으로 안전해지지 않습니다. 결과 공유 범위, 유한 반복, 명시적 승인, 오류 시 중단을 함께 설계해야 합니다. 이 slice의 DevOps 역할은 외부 변경을 하지 않는 handoff note를 만들 뿐이며, 사람 승인 없이는 QA와 DevOps 모두 호출되지 않습니다.
