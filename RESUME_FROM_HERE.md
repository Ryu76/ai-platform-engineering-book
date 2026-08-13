# AI Platform Engineering Bootcamp — 재개 지점

> 기록 시각: 2026-08-13 15:08 KST
> 기록 목적: 모든 자동 cron을 중지한 상태에서, 다음 작업자가 앞선 대화·자동 보고를 다시 읽지 않고 실제 Git/Worktree 상태부터 안전하게 재개하도록 한다.

## 현재 운영 규칙

- 모든 Hermes cron 작업은 **중지(paused)** 상태다.
- 이 프로젝트는 현재 대화 세션에서만 수정한다. 사용자가 별도로 재개를 승인하기 전에는 cron을 만들거나 재개하지 않는다.
- 실제 LLM API 호출, 외부 서비스 전송, Docker 컨테이너 실행, Kubernetes 배포는 명시 승인 없이 하지 않는다.
- 작업은 작은 변경 → 해당 테스트 → 전체 품질 검사 → 커밋 순서로 진행한다.
- 현재 프로젝트 루트: `E:\python\ai-platform-engineering-book`
- 기본 브랜치: `main` (`a567410 Merge branch 'volume-02'`)

## 가장 먼저 할 일

1. `git worktree list --porcelain`으로 worktree 경로를 다시 확인한다.
2. 각 worktree에서 `git status --short`를 실행한다. 특히 Volume 08에는 **보존해야 할 미커밋 작업 5개**가 있다.
3. 완료 표기는 과거 자동 작업에서 모순된 기록이 있으므로, `VOLUMEXX_COMPLETE=true` 문자열만으로 완료 처리하지 않는다.
4. 완료 판단은 다음 모두를 만족할 때만 한다.
   - Volume PRD 목표·필수 내용·실습·결과물·DoD 체크리스트 대조
   - `scripts/run_all_tests.sh` 또는 동등한 ruff/mypy/docs/links/code-blocks/secrets/pytest 전체 검사 통과
   - Git 작업 트리 clean
   - PROGRESS.md의 완료 선언이 이후의 `미완료` 선언과 모순되지 않음
5. 검증된 Volume만 `main`에 병합한다. 병합 전 `main`이 clean인지 확인하고, 충돌 시 기능/문서 계약을 유지한다.

## 브랜치 및 작업 현황

| Volume | 브랜치 | main 대비 미통합 커밋 | HEAD | 재개 판단 |
|---|---|---:|---|---|
| 01 LLM 기초 | `volume-01` | 10 | `68a81f0` | 완료 마커가 있으나 PROGRESS에 이후 장별 출고 감사 미완료가 명시됨. 완료 재검증부터. |
| 02 Prompt Engineering | `volume-02` | 0 | `4b0c189` | main에 반영됨. 완료 마커가 있음. 전체 통합 검사 때 재검증. |
| 03 Tool Calling & MCP | `volume-03` | 27 | `4386c59` | 완료 마커 없음. MCP 출력 decode/redaction 이후부터 계속. |
| 04 Embedding & Vector DB | `volume-04` | 27 | `d513495` | 실제 Qdrant persistence/filter/reindex DoD가 미검증이라고 명시됨. |
| 05 RAG | `volume-05` | 0 | `63555ac` | main에 반영됨. 완료 마커와 이후 미완료 서술이 충돌함. 재검증 필요. |
| 06 Reranker | `volume-06` | 0 | `889a77e` | main에 반영됨. 완료 마커가 있음. 전체 통합 검사 때 재검증. |
| 07 Multi-Agent | `volume-07` | 25 | `d53ce0a` | PROGRESS가 전체 DoD 미완료를 명시함. |
| 08 Router | `volume-08` | 23 | `3e422f4` | PRD DoD 미완료. 아래 미커밋 변경을 먼저 보존·검증·커밋해야 함. |
| 09 LangGraph | `volume-09` | 23 | `764cb76` | PROGRESS가 전체 DoD 미완료를 명시함. |
| 10 Evaluation | `volume-10` | 0 | `2090a34` | main에 반영됨. 완료 마커가 있음. 전체 통합 검사 때 재검증. |
| 11 Kubernetes 운영 | `volume-11` | 22 | `421f233` | 실제 Docker/cluster/rollout 검증이 없으므로 미완료. |

## 보호해야 하는 미커밋 변경

다른 worktree의 변경을 루트에서 reset/checkout/stash하지 않는다.

### Volume 08 worktree
경로: `E:\python\ai-platform-engineering-book-volume-08`

```text
M docs/volume08-router/09-router-mini-project.md
M docs/volume08-router/PROGRESS.md
M docs/volume08-router/checklist.md
M src/ai_platform/router/audit.py
M tests/unit/test_volume08_router_audit.py
```

재개 시 위 5개 파일의 diff를 읽고, 좁은 Router 감사 로그 테스트를 먼저 실행한 뒤 한 커밋으로 정리한다.

## 권장 재개 순서

1. **Volume 08 미커밋 변경 보존**: diff 검토 → 단위 테스트 → 커밋
2. **Volume 03**: MCP Tool Calling 완료 기준, 출력 redaction/승인/timeout/retry/권한 및 문서·실습·테스트 감사
3. **Volume 04**: Qdrant가 필요한 실제 실행 DoD를 별도 승인 필요 항목으로 유지하고, 허용된 오프라인 범위의 문서·테스트 계약을 완료
4. **Volume 07 / 08 / 09**: Agent → Router → LangGraph 의존 순서로 완료 조건·handoff 정리
5. **Volume 11**: Docker/Kubernetes 정적 산출물과 실제 실행이 필요한 DoD를 분리해 명확히 기록. live cluster 검증은 별도 승인 전에는 완료로 표시하지 않음.
6. Volume 01·02·05·06·10의 완료 표기는 PRD DoD 재감사 후에만 최종 확정
7. 검증된 브랜치를 순차 병합하고 전체 품질 검사 실행

## 공통 검증 명령

실행 위치: 프로젝트 또는 해당 Volume worktree 루트

```bash
uv run ruff check .
uv run mypy src
uv run python scripts/validate_docs.py
uv run python scripts/validate_links.py
uv run python scripts/validate_code_blocks.py
uv run python scripts/check_secrets.py
uv run pytest
```

> [!WARNING]
> Windows에서 Hermes 활성 환경 경고가 출력될 수 있다. `uv run`이 프로젝트 `.venv`를 사용했고 종료 코드가 0인지 확인한다. 경고만으로 성공을 주장하지 않는다.

## 완료 상태 정의

전체 프로젝트 완료는 다음을 모두 만족할 때만 선언한다.

- 11개 Volume 각각의 DoD 및 실습/테스트 증거가 존재한다.
- 문서·링크·코드 블록·비밀값 검증과 `ruff`, `mypy`, `pytest`가 전체 저장소에서 통과한다.
- Docker/Kubernetes처럼 실제 실행이 요구되는 항목은 실제 실행 증거가 있거나, 사용자와 합의해 실행 불가 범위를 완료 조건에서 명시적으로 제외한다.
- `main`은 clean 상태이며 필요한 Volume 변경이 모두 병합돼 있다.
- 비밀값, 실제 API key, 개인정보가 저장소에 없다.

## Cron 상태

2026-08-13 15:08 KST에 등록된 cron 15개를 모두 pause했다. 이 문서 작성 시점에 활성 cron은 0개여야 한다.

재개 시에는 기본적으로 cron을 만들지 않는다. 사용자가 명시적으로 병렬/주기 실행을 다시 요청할 때만 새 schedule을 구성한다.
