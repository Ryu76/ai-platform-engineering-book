# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **MCP STDIO subprocess 시작 전 allowlisted shell-free launch plan·유한 host budget 경계**
- 완료 선언: 아직 하지 않음. 실제 subprocess host lifecycle, OS pipe backpressure, cancellation/signal, durable audit/idempotency, Hermes/Codex 연동과 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: subprocess를 시작하지 않는 allowlisted STDIO host launch plan

- `src/ai_platform/mcp/host.py`
  - `McpStdioServerSpec`은 trusted deployment configuration의 immutable tuple argv만 받습니다. selector는 executable, argument, shell flag, output limit, shutdown 또는 restart budget을 바꿀 수 없습니다.
  - `McpStdioHostAllowlist.prepare_launch()`는 exact server name을 static `McpStdioHostLaunchPlan`으로만 변환합니다. 이 모듈은 `subprocess`, shell, pipe, signal 또는 Tool을 실행하지 않습니다.
  - stdout/stderr 1 KiB–1 MiB, graceful shutdown 0.1–60초, restart 0–3회로 유한한 host budget을 configuration 단계에서 검증합니다.
- `src/ai_platform/mcp/__init__.py`
  - allowlisted host launch model public export를 추가했습니다.
- `examples/volume03/mcp_stdio_allowlisted_launch_plan.py`
  - 고정 `safe-echo` config의 launch plan만 출력하며 executable을 실제로 시작하지 않습니다.
- `tests/volume03/test_mcp_host.py`
  - `tests/volume03/test_mcp_host.py`가 exact selection, immutable snapshot, unknown selector non-disclosure, duplicate/mutable config, shell-like argv·bounded stream·shutdown·restart validation을 검증합니다.
- `docs/volume03-tool-calling-mcp/20-mcp-stdio-allowlisted-launch-plan.md`
  - subprocess ownership의 configuration 부분, shell-free argv, bounded host budget, offline exercise와 아직 구현하지 않은 OS lifecycle을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스무 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_allowlisted_launch_plan.py
server_name: safe-echo
argv: volume03-safe-echo-server --stdio
stdout_limit_bytes: 16384
restart_limit: 0

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 21 source files

$ uv run pytest tests/volume03/test_mcp_host.py -q
14 passed in 0.16s

$ uv run pytest -q
179 passed in 1.30s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0)
```

모든 `uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. 예제와 테스트는 실제 `sys.stdin`/`sys.stdout`, filesystem, shell, subprocess, pipe, signal, network, 외부 MCP server, 실제 destructive Tool을 사용하지 않았습니다.

## 다음 슬라이스

allowlisted launch plan 뒤에는 실제 host process의 ownership·pipe drain/backpressure, EOF/disconnect, cancellation/signal, exit-code/restart 실행, error propagation을 별도 작은 slice로 구현·문서·테스트합니다. durable approval/audit/idempotency와 Hermes/Codex integration은 계속 별도 설계·문서·테스트가 필요합니다.
