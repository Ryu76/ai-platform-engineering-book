# Volume 07 작성 진행 로그

## 2026-08-11 — Slice 14: 결정론적 Mock 역할 바인딩

- `DeterministicMockAgent`, `DeterministicMockWorker`, `DeterministicMockConflictAgent`가 선언하는 `role`은 이제 workflow 구성 slot 또는 mapping key와 정확히 일치해야 한다. 잘못 배선된 role label은 첫 Agent 호출 전에 `WorkflowConfigurationError`로 fail-closed한다.
- `role` 속성이 없는 protocol adapter는 기존의 callable boundary 검사를 계속 사용한다. 이 slice는 local Mock fixture 배선 오류를 잡는 경계이며 production identity·tool 권한·사람 승인의 대체물이 아니다.
- `tests/volume07/test_declared_mock_role_binding.py`는 review, release handoff, delegation, conflict workflow의 네 role mismatch가 peer·coordinator·후속 Agent 호출 없이 구성 단계에서 중단되는지 고정한다. 모든 검증은 local Mock만 사용하며 네트워크, live API, secret, 도구 실행, 배포를 사용하지 않는다.
- `docs/volume07-multi-agent/11-declared-mock-role-binding.md`에 선언 role과 구성 role의 책임 분리를 기록했다.

## 2026-08-11 — Slice 13: Hermes runtime과 직접 구현의 책임 경계

- `docs/volume07-multi-agent/10-hermes-runtime-comparison.md`에 Volume 07의 deterministic local Mock workflow와 Hermes Agent runtime의 역할·메시지·state/memory·tool·bounded loop·사람 승인 책임을 비교했다.
- Hermes의 현재 architecture, configuration, tools, persistent memory, security 공식 문서를 연결했다. 비교 장은 Hermes profile 또는 설정을 변경하지 않으며, 실제 runtime 적용 전에는 최신 공식 문서로 설정과 보안 경계를 다시 확인하도록 명시한다.
- 비교 실습은 `examples/volume07/`의 네 local Mock 예제와 `tests/volume07`만 실행한다. live API, secret, network Agent 호출, 도구 실행, 배포는 사용하지 않는다.

## 2026-08-11 — Slice 12: 역할 범위 검토 권한

- `BoundedReviewWorkflow`와 `ApprovalGatedReleaseHandoffWorkflow`는 `ReviewDecision`을 Reviewer 역할에만 허용한다. Planner·Researcher·Developer·QA·DevOps의 명시적 review 값은 audit trail에 기록되거나 다음 역할을 호출하기 전에 `AgentProtocolError`로 fail-closed한다.
- Reviewer는 `APPROVE` 또는 `REVISE`를 반드시 명시해야 하며, 결정 누락도 audit 기록 전에 중단한다. 사람 승인은 역할 권한이나 Agent protocol 오류를 우회하지 않는다.
- `tests/volume07/test_runtime_review_decision_contract.py`는 Reviewer가 아닌 Planner가 review 권한을 주장하면 Researcher가 호출되지 않고, QA가 review 권한을 주장하면 DevOps handoff가 호출되지 않는지 고정한다. 모든 검증은 local Mock만 사용하며 네트워크, live API, secret, 도구 실행, 배포를 사용하지 않는다.
- `docs/volume07-multi-agent/09-role-scoped-review-authority.md`에 역할 권한과 사람 승인 게이트의 분리를 기록했다.

## 2026-08-11 — Slice 11: 실행 중 검토 결정 계약

- `BoundedReviewWorkflow`와 `ApprovalGatedReleaseHandoffWorkflow`는 모든 신뢰할 수 없는 실행 Agent 응답의 `review`를 `ReviewDecision` 또는 `None`으로 audit 기록과 후속 역할 호출 전에 검사한다. `"approve"` 같은 문자열은 enum처럼 보여도 `AgentProtocolError`로 fail-closed한다.
- 잘못된 Planner review는 Researcher·Developer·Reviewer·QA를 호출하지 않고, 잘못된 Release Reviewer review는 명시적 `APPROVED` 입력이 있어도 QA·DevOps를 호출하지 않는다.
- `tests/volume07/test_runtime_review_decision_contract.py`는 고정 Mock 생성자 검증을 우회하는 local test double로 두 실행 경계를 고정한다. 네트워크, live API, secret, 도구 실행, 배포는 사용하지 않는다.
- `docs/volume07-multi-agent/08-runtime-review-decision-contract.md`에 구성 fixture 검증과 신뢰할 수 없는 실행 Agent protocol 검증의 역할 분리를 기록했다.

## 2026-08-11 — Slice 10: 고정 Mock script 항목 계약

- `DeterministicMockAgent`, `DeterministicMockCoordinator`, `DeterministicMockWorker`, `DeterministicMockConflictAgent`는 immutable tuple 컨테이너뿐 아니라 모든 고정 response/plan/proposal 항목의 타입과 기본 필드를 구성 단계에서 검사한다. 빈 문자열, 잘못된 type, Worker boolean 위반, 중복 delegated task ID는 첫 Agent 호출 전에 `WorkflowConfigurationError`로 fail-closed한다.
- workflow별 정책인 task 수 상한, assignee allow-list, reviewer의 명시적 승인 결정과 사람 승인 게이트는 실행 시점 검증으로 유지한다. 유효한 fixture도 `PENDING`에서 QA·Worker·DevOps 실행을 허용하지 않는다.
- `tests/volume07/test_immutable_mock_scripts.py`와 기존 Volume 07 contract tests는 이 구성 경계와 기존 bounded-loop/approval 경계를 함께 고정한다.
- `docs/volume07-multi-agent/07-fixed-script-entry-contracts.md`에 구성 계약과 실행 정책의 책임 분리를 기록했고, 06장의 설명을 현재 동작으로 갱신했다.

## 2026-08-11 — Slice 09: 결정론적 Mock script 불변성

- `DeterministicMockAgent`, `DeterministicMockCoordinator`, `DeterministicMockWorker`, `DeterministicMockConflictAgent`는 response/plan/proposal script로 비어 있지 않은 immutable tuple만 구성 단계에서 허용한다. mutable list는 실행 전 `WorkflowConfigurationError`로 fail-closed한다.
- 모든 role 기반 결정론적 Mock은 role을 비어 있지 않은 문자열로 검사하여 문자열이 아닌 값도 `AttributeError` 없이 명시적인 구성 오류로 종료한다.
- `tests/volume07/test_immutable_mock_scripts.py`는 네 Mock이 mutable script와 잘못된 role을 실행 전 거절하고, tuple script의 소진은 fallback 없이 기존 `AgentProtocolError` 경계를 유지하는지 고정한다.
- `docs/volume07-multi-agent/06-immutable-mock-scripts.md`에 script container 불변성과 bounded 호출 예산의 관계를 기록했다.

## 2026-08-11 — Slice 08: 구성 단계 Agent 경계 검증

- `src/ai_platform/agents/workflow.py`와 `release_handoff.py`는 모든 named role에 호출 가능한 `act(context)` 경계가 있는지 생성 시 검사한다. 잘못된 역할은 첫 Agent 호출 전에 `WorkflowConfigurationError`로 fail-closed한다.
- `src/ai_platform/agents/delegation.py`는 Coordinator의 `propose(context)`, Worker의 `act(context)`, `workers` mapping, immutable non-empty `frozenset` assignee allow-list를 구성 시 검증한다.
- `src/ai_platform/agents/conflict.py`는 role-to-agent mapping과 모든 `propose(context)` 경계를 실행 전에 검증한다.
- `tests/volume07/test_agent_boundary_configuration.py`는 네 workflow의 non-callable boundary와 mutable allow-list가 어떤 Agent 호출보다 먼저 거절되며, 정상 Deterministic Mock은 approval 대기까지 계속 동작함을 고정한다.
- `docs/volume07-multi-agent/05-agent-boundary-configuration.md`에 구성·실행 protocol 검증의 분리와 fail-closed 이유를 기록했다.

## 2026-08-11 — Slice 07: 충돌 해결 입력·제안 경계 강화

- `src/ai_platform/agents/conflict.py`에서 objective를 비어 있지 않은 문자열로 제한해 잘못된 요청이 첫 Conflict Agent 호출 전에 종료되도록 했다.
- Agent proposal은 `ConflictProposal`이고 option·rationale 모두 비어 있지 않은 문자열인지 다음 Agent 호출 전에 검증한다. 객체 형식 또는 필드 형식이 잘못된 proposal은 `AgentProtocolError`로 fail-closed한다.
- `tests/volume07/test_bounded_conflict_resolution.py`는 잘못된 objective가 모든 Agent 호출 전에 중단되고, 잘못된 proposal 또는 필드 형식이 다음 Agent 실행 없이 중단하는지 고정한다.
- `docs/volume07-multi-agent/03-bounded-conflict-resolution.md`에 입력·제안 검증 규칙을 기록했다.

## 2026-08-11 — Slice 06: 위임 입력·Worker 응답 경계 강화

- `src/ai_platform/agents/delegation.py`에서 objective를 비어 있지 않은 문자열로 제한해 잘못된 입력이 Coordinator 호출 전에 종료되도록 했다.
- Coordinator 결과는 immutable tuple task를 가진 `DelegationPlan`인지, 각 task의 ID·지시문·담당자가 문자열 계약을 충족하는지 검증한다. Worker 결과도 `WorkerResponse`, 비어 있지 않은 content, boolean succeeded 계약을 만족해야 audit trail에 기록된다.
- `tests/volume07/test_approval_gated_delegation.py`는 잘못된 objective가 모든 Agent 호출 전에 멈추고, 잘못된 Coordinator/Worker 출력이 다음 Worker 실행 없이 `AgentProtocolError`로 fail-closed하는지 고정한다.
- `docs/volume07-multi-agent/02-approved-bounded-delegation.md`에 새 입력·응답 경계를 기록했다.

## 2026-08-11 — Slice 05: 검토 워크플로 입력·응답 경계 강화

- `src/ai_platform/agents/workflow.py`에서 task가 비어 있지 않은 문자열인지 확인하고, Planner·Researcher·Developer·Reviewer·QA의 모든 출력이 `AgentResponse` 및 비어 있지 않은 `content` 계약을 만족하는지 다음 역할 호출 전에 검사하도록 했다.
- 잘못된 task는 어떤 역할도 호출하지 않으며, 초기 역할의 빈 응답은 Researcher·Developer·Reviewer·QA로 진행하지 않고 `AgentProtocolError`로 fail-closed한다.
- `tests/volume07/test_bounded_review_workflow.py`에 이 두 경계를 고정하고, `docs/volume07-multi-agent/01-bounded-review-workflow.md`에 검증 규칙을 기록했다.

## 2026-08-10 — Slice 01: 유한 검토와 사람 승인 게이트

- `src/ai_platform/agents/workflow.py`에 Planner, Researcher, Developer, Reviewer, QA용 결정론적 Mock 경계와 감사 메시지 모델을 추가했다.
- Reviewer 재작업은 `max_review_cycles` 양의 정수로 제한하고, Mock 응답 소진도 fail-closed로 처리했다.
- Reviewer 승인만으로 QA를 실행하지 않으며, `HumanApproval.APPROVED`가 있을 때만 QA와 `completed` 상태에 도달한다. 거절은 모든 Agent 호출 전에 종료한다.
- `examples/volume07/offline_review_workflow.py`는 라이브 API·비밀값 없이 승인 대기와 명시 승인을 재현한다.
- `tests/volume07/test_bounded_review_workflow.py`로 이 slice의 안전 계약을 검증한다.

## 2026-08-10 — Slice 02: 승인된 유한 위임과 Worker 재시도 상한

- `src/ai_platform/agents/delegation.py`에 Coordinator 계획과 Worker 실행을 분리하는 결정론적 Mock 경계, immutable manifest/audit message 모델을 추가했다.
- `ApprovalGatedDelegationWorkflow`는 task 수, 고유 task ID, 비어 있지 않은 지시문, 담당자 allow-list를 Worker 호출 전에 검사한다.
- 기본 `PENDING`은 Coordinator manifest만 남기고 멈추며, `APPROVED`에서만 manifest의 Worker를 호출한다. `REJECTED`는 모든 Agent 호출 전에 종료한다.
- Worker 재시도는 `max_worker_attempts` 양의 정수로 제한한다. 실패 시 fallback하거나 뒤 task를 실행하지 않고 `worker_retry_limit_reached`로 fail-closed한다.
- `examples/volume07/offline_approved_delegation.py`와 `tests/volume07/test_approval_gated_delegation.py`는 라이브 API·비밀값 없이 이 경계를 재현하고 검증한다.

## 2026-08-10 — Slice 03: 유한 충돌 해결과 완료 승인

- `src/ai_platform/agents/conflict.py`에 Planner와 Reviewer 등 역할별 결정론적 Mock proposal 경계와 immutable conflict audit message 모델을 추가했다.
- `BoundedConflictResolutionWorkflow`는 Agent 수와 conflict round를 양의 정수 상한으로 제한한다. 모든 proposal option이 정확히 같을 때만 consensus recommendation을 만들며, 다수결·추측·fallback으로 충돌의 승자를 고르지 않는다.
- 기본 `PENDING`은 consensus recommendation에서 멈추고, `APPROVED`에서만 `completed`가 된다. `REJECTED`는 모든 Agent 호출 전에 종료한다. 합의하지 못하면 `conflict_limit_reached`로 fail-closed한다.
- `examples/volume07/offline_conflict_resolution.py`와 `tests/volume07/test_bounded_conflict_resolution.py`는 API·비밀값·장기 메모리 없이 이 경계를 재현하고 검증한다.

## 2026-08-10 — Slice 04: 승인 게이트가 있는 로컬 Release Handoff

- `src/ai_platform/agents/release_handoff.py`에 Planner, Developer, Reviewer, QA, DevOps용 결정론적 Mock 경계와 immutable handoff audit message 모델을 추가했다.
- `ApprovalGatedReleaseHandoffWorkflow`는 Developer/Reviewer 재작업을 `max_review_cycles` 양의 정수로 제한한다. Reviewer 결정 누락, 빈 응답, script 소진은 다음 역할이나 fallback 없이 fail-closed한다.
- 기본 `HumanApproval.PENDING`은 Reviewer 승인 audit trail에서 멈춘다. `APPROVED`일 때만 QA와 DevOps가 순서대로 호출되어 **로컬 handoff note**를 만들며, 배포·네트워크·도구 실행은 구현하지 않는다. `REJECTED`는 모든 역할 호출 전에 종료한다.
- `examples/volume07/offline_release_handoff.py`와 `tests/volume07/test_approval_gated_release_handoff.py`로 역할별 결과 공유, 승인 게이트, 재작업 상한, 거절, protocol 오류와 script 소진의 fail-closed 동작을 API·비밀값 없이 재현하고 검증한다.

## 완료 상태

Volume 07 전체 PRD Definition of Done은 아직 완료되지 않았다. 따라서 `VOLUME07_COMPLETE=true`는 설정하지 않았고, cron self-pause도 하지 않는다.
