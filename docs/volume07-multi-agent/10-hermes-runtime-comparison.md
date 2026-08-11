# 10. Hermes Agent Runtime과 직접 구현 비교

## 1. 학습 목표

이 장에서는 Volume 07의 작은 직접 구현과 Hermes Agent runtime의 책임 경계를 비교합니다. 이 장을 마치면 Planner·Developer·Reviewer·QA·DevOps 역할, 메시지 전달, bounded loop, 명시적 사람 승인을 **학습용 local workflow**에서는 어떻게 고정하는지, 그리고 Hermes를 사용할 때 어떤 runtime 설정과 보안 경계를 별도로 확인해야 하는지 설명할 수 있습니다.

> 이 실습은 Hermes를 실행·설정·수정하지 않습니다. local deterministic Mock만 사용하며, live API, secret, 네트워크 Agent 호출, 도구 실행, 배포를 수행하지 않습니다.

## 2. 왜 비교하는가

직접 구현한 workflow는 작아서 역할 순서와 종료 조건을 코드와 테스트에서 한눈에 볼 수 있습니다. 반면 Hermes Agent는 CLI, Gateway, batch runner, API server, Python library 같은 여러 진입점과 provider·prompt·tool subsystem을 가진 runtime입니다. runtime을 도입해도 다음 설계 책임은 자동으로 사라지지 않습니다.

- 누가 어떤 역할과 결정을 맡는가
- 어떤 메시지와 상태를 다음 역할에 넘기는가
- 재시도와 반복을 어디에서 제한하는가
- 어떤 단계가 사람 승인을 기다려야 하는가
- memory와 tool이 읽거나 바꿀 수 있는 범위는 무엇인가

따라서 이 교재는 runtime을 사용하기 전에 local Mock으로 안전 계약을 고정하고, Hermes 환경에서는 같은 계약을 설정·운영 절차·보안 정책으로 다시 점검하는 순서를 사용합니다.

## 3. 현재 Hermes 구조 요약

2026-08-11에 확인한 [Hermes Agent 공식 Architecture 문서](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)는 높은 수준에서 다음 흐름을 설명합니다.

```text
CLI / Gateway / ACP / Batch Runner / API Server / Python Library
                              |
                            AIAgent
          +-------------------+-------------------+
          |                   |                   |
    Prompt Builder     Provider Resolution    Tool Dispatch
          |                   |                   |
  context compression    model API mode      tool registry
       and caching                            and toolsets
```

이는 Volume 07의 local 역할 객체와 같은 단일 구조가 아닙니다. Hermes의 Agent runtime은 prompt 조립, provider 선택, tool dispatch를 포함합니다. 따라서 runtime의 결과가 Reviewer 메시지처럼 보여도 그것만으로 reviewer 권한, call budget, 또는 사람 승인 정책이 보장되지는 않습니다.

공식 문서의 세부 기능과 명령은 변경될 수 있으므로 Hermes를 실제로 구성할 때는 다음 최신 문서를 우선 확인합니다.

- [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)
- [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
- [Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)
- [Persistent Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)

## 4. 직접 구현과 runtime의 책임 비교

| 관심사 | Volume 07 직접 구현 | Hermes runtime에서 별도로 확인할 것 |
|---|---|---|
| 역할 | Workflow 생성자에 `planner`, `researcher`, `developer`, `reviewer`, `qa`, `devops` 경계를 명시한다. | Agent identity, prompt, skill, access policy가 의도한 역할과 일치하는지 확인한다. 역할 이름만으로 권한을 추정하지 않는다. |
| 메시지 전달 | `AgentContext.messages`의 immutable tuple만 다음 호출에 전달한다. | prompt 조립, context file, session context가 어떤 입력을 포함하는지 확인한다. |
| state / memory | 실행 중 audit trail만 사용하며 장기 memory를 쓰지 않는다. | Hermes memory는 profile별로 session 사이에 유지될 수 있으므로 scope와 writer를 명시한다. |
| tool | Mock에는 network client·tool executor·fallback이 없다. | toolset은 platform별로 활성/비활성할 수 있다. 필요한 최소 tool만 허용하고 위험한 명령 승인 정책을 확인한다. |
| 반복·재시도 | `max_review_cycles`, `max_worker_attempts`, `max_rounds`가 양의 정수 상한이다. | runtime, skill, cron, 외부 workflow 어느 계층이 반복을 만들 수 있는지 식별하고 독립적인 상한과 종료 조건을 둔다. |
| 사람 승인 | `PENDING`은 영향 있는 다음 역할 전에 멈추며, enum의 명시적 `APPROVED`만 다음 단계를 허용한다. | Hermes의 command approval은 위험한 명령에 대한 보안 경계다. 업무 검토·release 승인 정책과 혼동하지 말고 별도 approval record와 절차를 둔다. |
| 실패 처리 | 잘못된 response, script 소진, 권한 위반은 `AgentProtocolError`로 다음 역할 전에 중단한다. | provider, tool, session 오류 시 재시도·fallback이 의도치 않은 권한 상승이나 외부 실행으로 이어지지 않는지 점검한다. |

## 5. Memory와 Tool을 분리해서 생각하기

### 5.1 Memory

이 권의 Mock workflow는 `AgentContext`와 결과 객체 안의 현재 실행 audit trail만 읽습니다. `DeterministicMockAgent`는 이전 실행을 기억하지 않으며, fixed script 이외의 응답을 만들지 않습니다. 이 선택은 테스트가 실행 순서에 따라 변하지 않게 합니다.

Hermes의 공식 Persistent Memory 문서는 profile 범위의 memory가 session 시작 시 system prompt에 snapshot으로 들어가며, 여러 writer가 하나의 Hermes home을 공유하지 않도록 안내합니다. production 설계에서는 다음을 먼저 결정합니다.

1. 역할별로 memory가 정말 필요한지 결정한다.
2. 필요하다면 profile 또는 external provider의 소유자와 writer를 하나로 제한한다.
3. 민감한 값, 승인 결정, release 권한을 일반 memory 문장에 저장하지 않는다.
4. workflow의 현재 audit와 장기 사용자 선호를 서로 다른 데이터 모델로 유지한다.

### 5.2 Tool

`src/ai_platform/agents/`의 Volume 07 구현은 파일 변경, terminal, browser, deployment, 외부 API를 Agent capability로 제공하지 않습니다. DevOps 역할도 local handoff note 문자열만 만듭니다.

Hermes 공식 Tools & Toolsets 문서는 web, terminal/files, browser, media, memory, delegation, scheduled task 등을 포함하는 tool registry를 설명합니다. 실제 runtime에 역할을 연결할 때는 다음의 allow-list를 먼저 작성합니다.

```text
Reviewer: read-only evidence inspection only
QA:       deterministic local verification only
DevOps:   handoff-note preparation only
```

그 뒤에만 각 역할에 필요한 최소 toolset을 매핑합니다. tool을 비활성화했다고 해서 업무 승인까지 해결되는 것은 아니며, tool 허용과 사람 승인 모두 필요합니다.

## 6. 안전한 비교 실습

저장소 루트에서 아래 명령은 Volume 07 코드만 실행합니다. Hermes profile, `~/.hermes/`, API key, network endpoint를 읽거나 바꾸지 않습니다.

```bash
# 실행 위치: 저장소 루트의 bash 또는 WSL 터미널
uv run python examples/volume07/offline_review_workflow.py
uv run python examples/volume07/offline_approved_delegation.py
uv run python examples/volume07/offline_conflict_resolution.py
uv run python examples/volume07/offline_release_handoff.py
uv run pytest tests/volume07 -q
```

각 예제의 기본 출력은 `awaiting_human_approval`에서 멈춰야 합니다. Reviewer 승인, coordinator manifest, 또는 conflict consensus가 있어도 기본 실행은 QA, Worker, DevOps 또는 completion을 묵시적으로 허용하지 않습니다.

실습 뒤에는 다음 질문에 답해 봅니다.

1. local workflow에서 Reviewer가 `APPROVE`를 반환해도 왜 QA가 실행되지 않는가?
2. Hermes의 위험 명령 승인과 업무상의 release 승인 기록은 왜 같은 것이 아닌가?
3. persistent memory가 켜진 runtime에서 deterministic test fixture가 변하지 않도록 하려면 무엇을 분리해야 하는가?
4. DevOps 역할에 toolset을 추가하려면 사람 승인 전에 어떤 allow-list와 종료 조건을 정해야 하는가?

## 7. 운영 적용 전 점검표

실제 Hermes 기반 구성을 시작하기 전 다음 항목을 문서화하고 검토합니다.

- [ ] 각 역할의 identity, goal, 입력 schema, 출력 schema를 지정했다.
- [ ] Reviewer 결정 권한과 QA 결과 보고 권한을 분리했다.
- [ ] 모든 반복과 retry에 수치 상한과 terminal state를 지정했다.
- [ ] toolset을 역할별 최소 권한 allow-list로 제한했다.
- [ ] 업무 approval record와 Hermes command approval을 별도 정책으로 모델링했다.
- [ ] memory의 profile scope, writer, retention, 민감정보 금지 규칙을 정했다.
- [ ] provider, tool, session 실패가 다음 역할 또는 외부 작업으로 자동 확장되지 않음을 테스트했다.
- [ ] 최신 Hermes 공식 문서로 configuration과 security 설정을 다시 확인했다.

## 8. 핵심 정리

Hermes Agent는 prompt, provider, tool, memory, session을 조합하는 runtime이고, Volume 07의 deterministic Mock은 그 이전에 역할 경계와 안전 계약을 학습하기 위한 최소 모델입니다. 두 접근은 경쟁하지 않습니다. 먼저 local 코드에서 메시지 전달, bounded loop, fail-closed, explicit human approval을 검증하고, runtime을 도입할 때는 memory·tool·provider·security 경계에 동일한 원칙을 적용해야 합니다.
