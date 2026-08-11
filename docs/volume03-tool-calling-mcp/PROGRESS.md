# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **allowlisted MCP STDIO child의 injected finite graceful/force shutdown 상태 기계**
- 완료 선언: 아직 하지 않음. actual subprocess factory·OS pipe backpressure·cancellation/signal semantics·exit-code restart supervisor·durable audit/idempotency·Hermes/Codex 연동과 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: injected child의 유한한 종료 순서

- `src/ai_platform/mcp/host.py`
  - `McpStdioChildProcess`는 trusted host가 이미 소유한 child의 `poll`/`terminate`/bounded `wait`/`kill` 최소 adapter 계약만 정의합니다. 이 module은 process를 만들지 않고 shell·pipe·network·Tool을 열지 않습니다.
  - `shutdown_mcp_stdio_child()`는 이미 종료한 child를 먼저 확인하고, 실행 중일 때만 terminate 한 번 → immutable plan의 grace wait 한 번 → 만료 때 kill 한 번 → `wait(0.0)` final status라는 유한한 순서를 적용합니다.
  - invalid/ambiguous exit code, child adapter failure, force-kill 뒤에도 종료하지 않은 상태는 raw detail 없이 generic `McpStdioHostError`로 끝내며 restart나 unbounded wait를 하지 않습니다.
  - `McpStdioHostShutdownResult`은 server name·exit code·terminate 요청 여부·force-kill 여부만 가진 immutable process-local result입니다.
- `src/ai_platform/mcp/__init__.py`
  - child shutdown protocol, result, function public export를 추가했습니다.
- `examples/volume03/mcp_stdio_injected_child_shutdown.py`
  - fixed `safe-echo` plan과 in-memory `OfflineChild`로 graceful shutdown result만 출력합니다. 실제 subprocess/signal/destructive action은 수행하지 않습니다.
- `tests/volume03/test_mcp_host.py`
  - already-exited no-signal, plan grace 사용 graceful stop, grace expiry 뒤 한 번의 force-kill, final non-exit 거부, ambiguous exit code 거부와 exact fake-child call order를 검증합니다.
- `docs/volume03-tool-calling-mcp/21-mcp-stdio-injected-child-shutdown.md`
  - process ownership의 종료 부분, finite call order, offline exercise와 아직 구현하지 않은 factory/pipe/restart/durable operation을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물한 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_injected_child_shutdown.py
server_name: safe-echo
exit_code: 0
termination_requested: True
force_killed: False

$ uv run ruff check src tests/volume03 examples/volume03
All checks passed!

$ uv run mypy src
Success: no issues found in 21 source files

$ uv run pytest tests/volume03/test_mcp_host.py -q
22 passed in 0.16s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 21 source files

$ uv run pytest -q
187 passed in 1.07s

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

`uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. 예제와 테스트는 fake in-memory child만 사용했으며 실제 process, sys.stdin/sys.stdout, filesystem, shell, pipe, signal, network, 외부 MCP server, destructive Tool을 사용하지 않았습니다.

## 다음 슬라이스

실제 OS process factory 자체를 열기 전, launch ownership과 fixed argv/`shell=False` contract를 production-specific adapter로 분리하고 fake factory로 검증해야 합니다. 그 뒤 stdout/stderr simultaneous bounded drain·backpressure, cancellation/disconnect, OS signal/process group semantics, exit-code 분류와 finite restart/backoff를 각각 작은 slice로 분리합니다. durable approval/audit/idempotency와 Hermes/Codex integration은 계속 별도 설계·문서·테스트가 필요합니다.
