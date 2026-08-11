# Volume 07. Multi-Agent 설계

## 목표

Planner, Researcher, Developer, Reviewer, QA 역할의 메시지·상태·도구·종료 조건을 구현합니다. 모든 실습은 결정론적 Mock을 우선 사용하고, 반복은 유한하게 제한하며, 영향 있는 다음 단계 전에 명시적 사람 승인을 둡니다.

## 장 목록

1. [결정론적 다중 에이전트 검토 워크플로](01-bounded-review-workflow.md) — 역할 메시지, 재작업 상한, QA 사람 승인 게이트
2. [승인 게이트가 있는 유한 위임](02-approved-bounded-delegation.md) — 검토 가능한 manifest, 담당자 allow-list, Worker 재시도 상한
3. [유한 충돌 해결과 사람 승인](03-bounded-conflict-resolution.md) — exact consensus, 충돌 round 상한, 완료 승인 게이트
4. [승인 게이트가 있는 로컬 Release Handoff](04-approved-release-handoff.md) — role별 immutable 결과 공유, DevOps handoff, QA/DevOps 승인 게이트
5. [구성 단계 Agent 경계 검증](05-agent-boundary-configuration.md) — 호출 가능한 역할 계약, immutable assignee allow-list, 실행 전 fail-closed
6. [결정론적 Mock script 고정](06-immutable-mock-scripts.md) — immutable response/plan/proposal script, 구성 시 fail-closed
7. [고정 Mock script 항목 계약](07-fixed-script-entry-contracts.md) — fixture 형식·필수 값 구성 시 fail-closed
8. [실행 중 검토 결정 계약](08-runtime-review-decision-contract.md) — 신뢰할 수 없는 Agent의 review enum을 audit/후속 역할 전에 fail-closed
9. [역할 범위 검토 권한](09-role-scoped-review-authority.md) — Reviewer 외 역할의 review 결정은 audit/후속 역할 전에 fail-closed

## 진행 상태

제작 이력과 아직 완료되지 않은 권 단위 Definition of Done은 [PROGRESS.md](PROGRESS.md)에 기록합니다.
