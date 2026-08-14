# Volume 07 작성 진행 로그

## 2026-08-14 — Slice 31: Chapter 07 고정 Mock script 항목 PRD 학습 계약

- `07-fixed-script-entry-contracts.md`에 전체 Volume 07 regression 실행 단계와 `PENDING`/`APPROVED`/`REJECTED`의 독립 책임을 명시했다. fixed fixture의 구성 오류는 approval로 우회할 수 없고, `REJECTED`는 Agent 호출 전에 종료하며, 유효한 tuple fixture도 bounded loop와 explicit human approval을 변경하지 않는다.
- `test_fixed_script_entry_contracts_documentation.py`를 추가해 Chapter 07의 14 section, 네 deterministic Mock과 `AgentResponse`/`DelegationPlan`/`WorkerResponse`/`ConflictProposal` 항목 계약, `WorkflowConfigurationError`, focused/full regression 명령, bounded loop 및 local-only live API·secret·tool 실행·deployment safety scope를 회귀 검증한다.
- `uv run pytest tests/volume07/test_immutable_mock_scripts.py tests/volume07/test_fixed_script_entry_contracts_documentation.py -q`는 7 passed였다. review example의 기본 실행은 QA 없이 `awaiting_human_approval`이었고, `--approve`는 local QA message만 포함한 `completed`였다. 전체 `uv run pytest tests/volume07 -q`는 70 passed였으며, `uv run ruff check src/ai_platform/agents tests/volume07`, `uv run mypy src/ai_platform/agents`, `validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 통과했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-14 — Slice 30: Chapter 12 접근 불가 Agent 경계 PRD 학습 계약

- `12-inaccessible-agent-boundaries.md`를 PRD Chapter template의 14개 section(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 정상 출력, 오류 해결, 응용, 실무 적용, 기본·응용·심화 과제, 체크리스트, 요약)으로 확장했다. `UnreadableActBoundary`와 `UnreadableProposeBoundary`의 local-only configuration failure를 보여 주고, callable discovery가 protocol method 실행·live API·secret 조회·tool 초기화·파일 변경·deployment를 수행하지 않는 경계를 명시했다.
- `test_inaccessible_agent_boundaries_documentation.py`를 추가해 Chapter 12의 14 section, `validate_callable_boundary`, 두 unreadable local test double, `WorkflowConfigurationError`, `PENDING`/`APPROVED`/`REJECTED`, focused/full regression 명령, bounded loop와 local-only safety scope를 회귀 검증한다. approval enum은 boundary configuration 오류를 우회하거나 capability를 전달하지 않는다.
- `uv run pytest tests/volume07/test_inaccessible_agent_boundaries.py tests/volume07/test_inaccessible_agent_boundaries_documentation.py -q`는 5 passed였다. 전체 `uv run pytest tests/volume07 -q`는 69 passed였고, `uv run ruff check src/ai_platform/agents tests/volume07`, `uv run mypy src/ai_platform/agents`, `validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py`도 통과했다. mini project의 기본 실행은 네 `awaiting_human_approval`을, 네 explicit approval flag는 local-only `completed`와 no-deployment handoff note를 실제 출력했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-14 — Slice 29: Chapter 10 Hermes runtime 비교 PRD 학습 계약

- `10-hermes-runtime-comparison.md`를 PRD Chapter template의 14개 section(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 정상 출력, 오류 해결, 응용, 실무 적용, 과제, 체크리스트, 요약)으로 확장했다. local `AgentContext`/`AgentResponse`/`DeterministicMockAgent`와 Hermes runtime의 prompt·provider·memory·tool policy 책임을 분리하고, role label·message·local `completed`가 capability 또는 운영 승인이 아님을 명시했다.
- `test_hermes_runtime_comparison_documentation.py`를 추가해 Chapter 10의 14 section, immutable deterministic Mock, `PENDING`/`APPROVED`/`REJECTED`, focused/full regression 명령, Hermes Architecture·Configuration·Tools·Persistent Memory·Security 공식 문서 참조, live API·secret·deployment 없는 local-only 범위를 회귀 검증한다.
- `uv run pytest tests/volume07/test_offline_multi_agent_mini_project.py tests/volume07/test_hermes_runtime_comparison_documentation.py -q`는 7 passed였고, Chapter 10 focused documentation test는 1 passed였다. mini project의 기본 실행은 네 `awaiting_human_approval`을, 네 explicit approval flag는 local-only `completed`와 no-deployment handoff note를 실제 출력했다. `uv run pytest tests/volume07 -q`는 68 passed, `uv run ruff check src/ai_platform/agents tests/volume07`, `uv run mypy src/ai_platform/agents`, `validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`도 통과했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-14 — Slice 28: Chapter 08 실행 중 검토 결정 PRD 학습 계약

- `08-runtime-review-decision-contract.md`를 PRD Chapter template의 14개 section(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 정상 출력, 오류 해결, 응용, 실무 적용, 과제, 체크리스트, 요약)으로 확장했다. 문서는 fixed deterministic Mock의 구성 단계 검증과 local untrusted `InvalidReviewAgent`의 실행 단계 `AgentResponse` schema 검증을 분리하고, enum-like 문자열 `"approve"` 및 Reviewer 외 role의 `ReviewDecision`이 audit trail과 다음 Agent 호출 전에 `AgentProtocolError`로 fail-closed됨을 현재 구현과 테스트에 맞춰 설명한다.
- `test_runtime_review_decision_documentation.py`를 추가해 Chapter 08의 14 section, `AgentResponse`/`ReviewDecision`/`AgentProtocolError`/`InvalidReviewAgent`, `PENDING`/`APPROVED`/`REJECTED`, focused/full regression 명령, local-only live API·secret·deployment safety scope를 회귀 검증한다.
- `uv run pytest tests/volume07/test_runtime_review_decision_contract.py tests/volume07/test_runtime_review_decision_documentation.py -q`는 6 passed였다. review와 release example의 기본 실행은 각각 `awaiting_human_approval`이며 QA/DevOps를 호출하지 않았고, `--approve`는 local `completed`만 출력했다. mini project의 기본 네 stage pause와 네 explicit approval flag의 local completion도 실제 실행으로 확인했다. `uv run pytest tests/volume07 -q`는 67 passed, `uv run ruff check src/ai_platform/agents tests/volume07`, `uv run mypy src/ai_platform/agents`, `validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`도 통과했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-14 — Slice 27: Chapter 14 Agent 계약·상태·Capability PRD 학습 계약

- `14-agent-contract-state-and-capability-boundaries.md`를 PRD Chapter template의 14개 section(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 정상 출력, 오류 해결, 응용, 실무 경계, 과제, 체크리스트, 요약)으로 완성했다. 문서는 `AgentContext` immutable execution state, `AgentResponse` schema, Reviewer-only `ReviewDecision`, 장기 memory의 별도 writer/retention 책임, message와 tool capability의 분리, workflow별 bounded loop와 explicit `PENDING`/`APPROVED`/`REJECTED` human gate를 현재 구현에 맞춰 설명한다.
- `test_agent_contract_state_documentation.py`를 추가해 Chapter 14의 14 section, `AgentContext`/`AgentResponse`/`DeterministicMockAgent`, approval enum, executable full regression 명령, `awaiting_human_approval`, local-only live API·secret·deployment 안전 범위를 회귀 검증한다.
- `uv run pytest tests/volume07/test_agent_contract_state_documentation.py -q`는 1 passed였다. `uv run python examples/volume07/offline_multi_agent_mini_project.py`는 네 stage의 `awaiting_human_approval` 및 gated detail 없는 출력을, 네 `--approve-*` flag는 `completed`와 local-only handoff note를 실제 출력했다. 전체 `uv run pytest tests/volume07 -q`는 66 passed, `uv run ruff check src/ai_platform/agents tests/volume07`와 `uv run mypy src/ai_platform/agents`도 통과했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-13 — Slice 26: Chapter 06 불변 deterministic Mock PRD 학습 계약

- `06-immutable-mock-scripts.md`를 PRD Chapter template의 14개 section(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 정상 출력, 오류 해결, 응용, 실무 경계, 과제, 체크리스트, 요약)으로 확장했다. 문서는 네 local `DeterministicMock*`의 non-empty immutable tuple script, script 소진의 fallback 없는 `AgentProtocolError`, workflow별 bounded loop와 별도 runtime policy를 현재 구현에 맞춰 설명한다.
- `test_immutable_mock_scripts_documentation.py`를 추가해 Chapter 06의 14 section, 네 Mock, focused/full test 명령, tuple·`PENDING`/`APPROVED`, live API·secret·deployment 없는 local-only safety scope를 회귀 검증한다. 고정 script가 유효해도 explicit human approval을 우회하지 않고, `--approve`도 local QA audit만 허용함을 기록했다.
- `uv run pytest tests/volume07/test_immutable_mock_scripts.py tests/volume07/test_immutable_mock_scripts_documentation.py -q`는 7 passed였다. `uv run python examples/volume07/offline_review_workflow.py`는 `awaiting_human_approval` 및 QA 미호출을, `--approve`는 local QA를 포함한 `completed`를 실제 출력했다. 전체 `uv run pytest tests/volume07 -q`는 65 passed, `uv run ruff check src/ai_platform/agents tests/volume07` 및 `uv run mypy src/ai_platform/agents`도 통과했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-13 — Slice 25: Chapter 04 PRD 학습 문서 실행 계약

- `test_approval_gated_release_handoff_documentation.py`를 추가해 Chapter 04가 PRD 학습 템플릿의 14개 section, deterministic local release-handoff example·contract test 실행 명령, explicit `--approve` 경계, `completed`의 local handoff note 의미와 no-deployment/API-key safety scope를 계속 포함하도록 회귀 검증했다.
- 기존 Chapter 04와 example은 이미 Planner→bounded Developer/Reviewer→explicit human approval→QA→local DevOps handoff 순서, `PENDING`의 QA/DevOps 미호출, `REJECTED`의 pre-call 종료, immutable message audit trail을 설명하고 구현한다. 이 slice는 그 실습 문서의 PRD 형식과 실행 가능한 local-only contract를 테스트로 고정한 한 tick이다.
- `uv run python examples/volume07/offline_release_handoff.py`는 `status=awaiting_human_approval`과 QA/DevOps 없는 audit trail을, `--approve`는 `status=completed` 및 `Handoff: local release notes are ready; no deployment ran.`을 실제로 출력했다. 새 documentation test는 1 passed였고, `uv run pytest tests/volume07 -q`는 64 passed, `uv run ruff check src/ai_platform/agents tests/volume07` 및 `uv run mypy src/ai_platform/agents`도 통과했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-13 — Slice 24: 구성 단계 context-compatible Agent signature 경계

- `validate_callable_boundary()`는 이제 `act`/`propose` attribute가 callable인지 확인한 뒤에도 `inspect.signature(...).bind(context)`로 orchestrator가 전달하는 한 positional immutable context를 실제로 받을 수 있는지 **호출 없이** 검증한다. `act()`나 `propose()`처럼 callable이지만 arity가 맞지 않는 boundary와 추가 required argument가 있는 boundary는 첫 Agent call 전에 cause-preserving `WorkflowConfigurationError`로 fail-closed한다.
- `tests/volume07/test_callable_signature_configuration.py`를 추가해 review/release의 `act`, delegation Coordinator/Worker의 `propose`/`act`, conflict peer의 `propose`가 context를 받지 못하면 workflow 구성 자체가 실패하고 valid local peer·Coordinator·Worker의 call history가 비어 있는지 고정했다. deterministic Mock, finite bound, explicit human approval의 기존 경계는 변경하지 않았다.
- `05-agent-boundary-configuration.md`에 callable existence와 one-context signature compatibility의 차이, non-invoking `inspect.signature`/`bind` 검사, 실행 명령과 오류 해결을 추가했다. `uv run pytest tests/volume07/test_callable_signature_configuration.py -q`는 4 passed였고, 전체 `uv run pytest tests/volume07 -q`는 63 passed였다. `uv run ruff check src/ai_platform/agents tests/volume07`와 `uv run mypy src/ai_platform/agents`도 통과했다. live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.

## 2026-08-13 — Slice 23: Chapter 05 구성 단계 Agent 경계 PRD 학습 문서 완성

- `05-agent-boundary-configuration.md`를 PRD Chapter template의 14개 항목(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 실제 출력, 오류 해결, 응용, 실무 경계, 과제, 체크리스트, 요약)으로 확장했다.
- 문서는 `act(context)`/`propose(context)` callable discovery, accessor failure의 cause-preserving `WorkflowConfigurationError`, deterministic Mock declared-role binding, runtime response schema 검증과 explicit human approval의 독립 책임을 현재 `workflow.py`, `delegation.py`, `conflict.py`, `release_handoff.py` 동작에 맞춰 설명한다.
- `tests/volume07/test_agent_boundary_configuration_documentation.py`를 추가해 이 Chapter의 PRD section, executable boundary test 참조, 전체 regression 명령, local-only safety boundary 문구를 회귀 검증한다. live API, secret, network Agent, tool 실행, 파일 변경, deployment는 추가하거나 사용하지 않았다.
- `uv run pytest tests/volume07/test_agent_boundary_configuration.py -q`는 5 passed였고, pending review/delegation example의 실제 output을 확인했다. 확장 뒤 `uv run pytest tests/volume07 -q`는 59 passed, 새 문서 contract test는 1 passed였다. 네 original example과 전체 approval mini project도 실제로 completed 경로를 실행해 확인했다.

## 2026-08-11 — Slice 22: Chapter 03 PRD 학습 문서 완성도 확장

- `03-bounded-conflict-resolution.md`를 PRD Chapter template의 14개 항목(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 실제 출력, 오류 해결, 응용, 실무 경계, 과제, 체크리스트, 요약)으로 확장했다.
- 문서는 `ConflictProposal`/immutable audit trail, `max_agents`·`max_rounds`의 곱으로 제한되는 proposal 호출 예산, option exact equality와 무합의 시 다수결·정규화·fallback 없이 `conflict_limit_reached`로 멈추는 경계를 현재 `conflict.py`와 예제 동작에 맞춰 설명한다.
- `PENDING` consensus recommendation과 `APPROVED` local completion을 분리하고 `REJECTED`가 모든 Agent 호출 전에 종료됨을 명시했다. deterministic fixed tuple Mock만 사용하며 live API, secret, network Agent, tool 실행, 파일 변경, deployment를 추가하거나 사용하지 않았다.
- `uv run python examples/volume07/offline_conflict_resolution.py`와 `--approve` 경로를 실제 실행해 각각 `awaiting_human_approval`과 `completed`를 확인했다. `uv run pytest tests/volume07/test_bounded_conflict_resolution.py -q`는 7 passed, 전체 `uv run pytest tests/volume07 -q`는 58 passed였다.

## 2026-08-11 — Slice 21: Chapter 02 PRD 학습 문서 완성도 확장

- `02-approved-bounded-delegation.md`를 PRD Chapter template의 14개 항목(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 실제 출력, 오류 해결, 응용, 실무 경계, 과제, 체크리스트, 요약)으로 확장했다.
- 문서는 Coordinator의 immutable `DelegationPlan` proposal과 `APPROVED` 뒤 Worker dispatch를 분리하고, `max_tasks`/`max_worker_attempts`의 독립 호출 상한, `PENDING`/`APPROVED`/`REJECTED` fail-closed 경계, Worker retry-limit 뒤 subsequent task 미실행을 현재 `delegation.py`와 예제의 동작에 맞춰 설명한다.
- `uv run python examples/volume07/offline_approved_delegation.py`와 `--approve` 경로를 실제 실행해 각각 `awaiting_human_approval`(Coordinator manifest만 기록)과 `completed`(`draft,verify` local Worker audit)을 확인했다. `uv run pytest tests/volume07/test_approval_gated_delegation.py -q`는 7 passed였다. live API, secret, network Agent, tool 실행, 파일 변경, deployment는 추가하거나 사용하지 않았다.

## 2026-08-11 — Slice 20: Chapter 01 PRD 학습 문서 완성도 확장

- `01-bounded-review-workflow.md`를 PRD Chapter template의 14개 항목(학습 목표, 필요성, 핵심 개념, ASCII 구조, 환경, 실행 위치가 있는 단계별 실습, 코드 설명, 실제 출력, 오류 해결, 응용, 실무 경계, 과제, 체크리스트, 요약)으로 확장했다.
- 문서는 Reviewer의 `ReviewDecision`과 QA를 여는 `HumanApproval`을 분리하고, immutable `AgentContext.messages`, deterministic fixed tuple Mock, `max_review_cycles`, `PENDING`/`APPROVED`/`REJECTED` fail-closed 경계를 실제 `workflow.py`와 예제의 동작에 맞춰 설명한다.
- `uv run python examples/volume07/offline_review_workflow.py`와 `--approve` 경로를 실제 실행해 각각 `awaiting_human_approval`(QA 없음)과 `completed`(local QA message)을 확인했다. `uv run pytest tests/volume07/test_bounded_review_workflow.py -q`는 7 passed, 전체 `uv run pytest tests/volume07 -q`는 58 passed였다. live API, secret, network Agent, tool 실행, 파일 변경, deployment는 추가하거나 사용하지 않았다.

## 2026-08-11 — Slice 19: stage별 사람 승인 flag 격리 계약

- `tests/volume07/test_offline_multi_agent_mini_project.py`는 이제 review, delegation, conflict, release의 네 단일 `--approve-*` 실행을 각각 subprocess로 검증한다. 선택한 stage 하나만 `completed`이며 나머지 세 stage는 계속 `awaiting_human_approval`이어야 한다.
- delegation의 단일 승인에서는 `draft,verify` local worker 결과만, release의 단일 승인에서는 local handoff note만 허용한다. 한 flag가 다른 QA·Worker·DevOps gate를 열 수 없음을 고정했고, live API, secret, network Agent, tool 실행, 파일 변경, deployment는 추가하지 않았다.
- `13-offline-multi-agent-mini-project.md`에 단일 flag의 예상 경계와 이미 구현한 exercise test를 반영했다. 모든 workflow는 immutable deterministic Mock script와 기존의 finite review/round/task/attempt bound를 유지한다.

## 2026-08-11 — Slice 18: 권 단위 학습 체크리스트·용어집·Router 인계

- `docs/volume07-multi-agent/15-volume-learning-checklist-glossary-and-router-handoff.md`에 네 deterministic local workflow의 권 단위 재실행 순서, 기본 `PENDING` pause와 독립 approval flag의 예상 출력을 추가했다.
- 이 장은 Agent, role, state, memory, message passing, deterministic Mock, bounded loop, fail-closed, human-in-the-loop, exact consensus, local handoff, Router handoff 용어를 Volume 07 범위에서 정의했다. 다음 Volume Router는 workflow를 선택할 수 있지만 approval를 생성하거나 tool/deployment capability를 위임할 수 없음을 명시했다.
- Router 인계표와 learner checklist는 status/audit snapshot처럼 넘길 수 있는 data를 approval, secret, tool object, mutable script처럼 넘기면 안 되는 authority/capability와 분리한다. live API, network Agent, secret, tool 실행, 파일 변경, deployment를 추가하지 않았다.
- `uv run pytest tests/volume07 -q`로 Volume 07 deterministic Mock, bounded loop, role authority, approval-gate contract 54개를 다시 검증했다. local mini project의 기본 pause 및 네 approval flag completed 경로도 실제로 실행해 확인했다.

## 2026-08-11 — Slice 17: Agent 계약·실행 상태·Capability 경계

- `docs/volume07-multi-agent/14-agent-contract-state-and-capability-boundaries.md`에 Agent와 단순 LLM 호출의 차이, role·goal·입출력 schema·capability·authority·stop condition·human gate 계약을 추가했다.
- 이 장은 `AgentContext`/immutable audit message를 현재 실행 state로 설명하고, 장기 memory의 scope·writer·retention 및 approval record 책임을 실행 state와 분리한다. 메시지 text는 tool capability 또는 deployment 권한이 아니며, Volume 07 deterministic Mock에는 network, secret, tool executor, file mutation, deployment 경로가 없음을 명시했다.
- review/delegation/conflict/release의 bounded counter, fail-closed status, `PENDING`/`REJECTED`/`APPROVED` 승인 경계를 표와 local-only 실습·오류 해결·과제로 연결했다. README에 새 장 링크를 추가했다.
- `uv run pytest tests/volume07 -q`로 Volume 07의 deterministic Mock, bounded loop, role authority, approval-gate contract 54개를 검증했다. live API, secret, network Agent, tool 실행, 배포를 사용하지 않았다.

## 2026-08-11 — Slice 16: 결정론적 Offline Multi-Agent 미니 프로젝트

- `examples/volume07/offline_multi_agent_mini_project.py`는 review, delegation, exact-consensus conflict, local release handoff를 각각 새 deterministic Mock workflow로 구성한다. 모든 script는 immutable tuple이고 review cycle 1, conflict round 1, task 2, Worker attempt 1로 호출 예산이 유한하다.
- `--approve-review`, `--approve-delegation`, `--approve-conflict`, `--approve-release`는 서로 독립된 사람 승인 gate다. flag가 없으면 해당 workflow는 `awaiting_human_approval`에서 멈추며 QA·Worker·DevOps 같은 gated role은 실행하지 않는다. 네 flag 모두를 전달해도 결과는 local audit/handoff note뿐이며 live API, secret, network Agent, tool 실행, 배포는 없다.
- `tests/volume07/test_offline_multi_agent_mini_project.py`는 subprocess로 실제 CLI의 pending 출력과 모든 별도 approval flag의 completed 출력을 고정한다.
- `docs/volume07-multi-agent/13-offline-multi-agent-mini-project.md`는 실행 위치, 예상 출력, stage별 approval 범위, 오류 해결, 실무 경계, 과제를 포함한 미니 프로젝트 실습을 기록했다.

## 2026-08-11 — Slice 15: 접근 불가 Agent 경계의 구성 단계 차단

- 공통 `validate_callable_boundary()`는 `act(context)` 또는 `propose(context)` attribute를 읽는 중 local adapter/property가 예외를 내면, 원래 예외를 원인으로 보존하는 `WorkflowConfigurationError`로 fail-closed한다. protocol method는 이 검사에서 호출하지 않는다.
- `BoundedReviewWorkflow`, `ApprovalGatedReleaseHandoffWorkflow`, `ApprovalGatedDelegationWorkflow`, `BoundedConflictResolutionWorkflow`가 공통 발견 경계를 사용한다. 접근 불가 boundary는 어떤 Planner·Coordinator·Worker·peer·QA·DevOps 호출과 audit trail 생성보다 먼저 구성을 중단한다.
- `tests/volume07/test_inaccessible_agent_boundaries.py`는 네 workflow에서 local `act`/`propose` property accessor 예외가 안정적인 구성 오류로 변환되고, 유효한 local Mock peer도 호출되지 않는지 고정한다. 모든 검증은 network, live API, secret, 도구 실행, 배포 없이 local Mock/test double만 사용한다.
- `docs/volume07-multi-agent/12-inaccessible-agent-boundaries.md`에 protocol method discovery를 구성 단계 안전 경계로 기록했다.

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
