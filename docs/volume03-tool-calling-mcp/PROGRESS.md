# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **allowlisted MCP STDIO child의 injected shell-free factory ownership 경계**
- 완료 선언: 아직 하지 않음. actual subprocess factory·OS pipe backpressure·cancellation/signal semantics·exit-code restart supervisor·durable audit/idempotency·Hermes/Codex 연동과 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: immutable launch plan으로 child factory 시작하기

- `src/ai_platform/mcp/host.py`
  - `McpStdioChildFactory`는 trusted host가 구현할 fixed-argv child start adapter contract만 정의합니다. 이 module은 subprocess, shell, pipe, network 또는 Tool을 열지 않습니다.
  - `start_mcp_stdio_child()`는 `McpStdioHostLaunchPlan`의 immutable tuple argv, stdout/stderr byte budget, host-fixed `shell=False`만 factory에 정확히 한 번 전달합니다. selector·command string·cwd·environment·stream을 받지 않으며 retry/restart를 하지 않습니다.
  - factory exception과 `poll`/`terminate`/`wait`/`kill` contract가 없는 반환값은 raw detail 없이 generic `McpStdioHostError`로 거부합니다.
  - `McpStdioChildProcess`를 runtime-checkable protocol로 표시해 trusted factory output의 최소 shutdown contract를 확인합니다.
- `src/ai_platform/mcp/__init__.py`
  - child factory protocol과 start function을 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_injected_child_factory.py`
  - fixed `safe-echo` plan, in-memory `OfflineFactory`, in-memory `OfflineChild`만 사용해 fixed argv 및 `shell=False` 전달을 출력합니다. 실제 process/shell/signal/destructive action은 수행하지 않습니다.
- `tests/volume03/test_mcp_host.py`
  - factory가 exact allowlisted plan values와 `shell=False`만 한 번 받는지, factory raw failure가 숨겨지는지, incomplete child 반환값이 거부되는지를 검증합니다.
- `docs/volume03-tool-calling-mcp/22-mcp-stdio-injected-child-factory.md`
  - start ownership, finite factory call, offline exercise, 현재 의도적으로 제외한 actual process/pipe/cancellation/restart/durable operation을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물두 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_injected_child_factory.py
server_name: safe-echo
argv: volume03-safe-echo-server --stdio
shell: False
child_already_exited: True

$ uv run ruff check src/ai_platform/mcp tests/volume03/test_mcp_host.py examples/volume03/mcp_stdio_injected_child_factory.py
All checks passed!

$ uv run mypy src
Success: no issues found in 21 source files

$ uv run pytest tests/volume03/test_mcp_host.py -q
25 passed in 0.38s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 21 source files

$ uv run pytest -q
190 passed in 1.22s

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

`uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만 프로젝트 가상환경에서 정상 실행했습니다. 예제와 테스트는 fake in-memory factory/child만 사용했으며 실제 process, sys.stdin/sys.stdout, filesystem, shell, pipe, signal, network, 외부 MCP server, destructive Tool을 사용하지 않았습니다.

## 다음 슬라이스

actual OS process factory를 열기 전에, platform-specific `subprocess` adapter의 exact `shell=False`·fixed argv·explicit cwd/environment boundary를 production-specific module로 분리하고 fake `Popen` API로 검증해야 합니다. 그 뒤 stdout/stderr simultaneous bounded drain·backpressure, cancellation/disconnect, OS signal/process group semantics, exit-code 분류와 finite restart/backoff를 각각 작은 slice로 분리합니다. durable approval/audit/idempotency와 Hermes/Codex integration은 계속 별도 설계·문서·테스트가 필요합니다.
