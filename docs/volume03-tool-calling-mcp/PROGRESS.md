# Volume 03 진행 기록

## 현재 상태

- 현재 Phase: **fixed argv·explicit cwd/environment MCP STDIO subprocess factory seam**
- 완료 선언: 아직 하지 않음. stdout/stderr simultaneous bounded drain·backpressure, stdin ownership,
cancellation/disconnect, Windows/POSIX process-group/signal semantics, exit-code restart supervisor,
durable audit/idempotency와 Hermes/Codex 연동 및 전체 운영 DoD를 구현·문서화·검증해야 합니다.

## 이번 슬라이스: OS-specific Popen factory를 fake seam 뒤에 분리하기

- `src/ai_platform/mcp/subprocess_factory.py`
  - `McpStdioSubprocessConfig`가 trusted deployment의 absolute cwd와 non-empty bounded
    NUL-free environment를 immutable snapshot으로 보관합니다. parent environment는 merge하지
    않으므로 `PATH` 같은 필요한 값은 deployment가 명시해야 합니다.
  - `McpStdioSubprocessFactory`는 existing `McpStdioChildFactory` contract를 구현합니다.
    allowlisted tuple argv와 host-fixed `shell=False`만 받아 injected/default Popen factory를
    정확히 한 번 호출합니다.
  - Popen call은 `stdin=stdout=stderr=PIPE`, `shell=False`, explicit `cwd`/snapshot `env`,
    `text=False`, `bufsize=0`, `close_fds=True`로 고정합니다. command string, inherited env,
    caller-provided cwd/environment/shell option은 받지 않습니다.
  - wrapped child는 `subprocess.TimeoutExpired`만 bounded `wait()`의 `None`으로 바꾸며,
    raw start failure와 incomplete process object는 기존 host boundary가 generic error로
    좁힙니다. pipe drain/read/write, process groups, cancellation, restart는 이 slice에서
    의도적으로 구현하지 않았습니다.
- `src/ai_platform/mcp/__init__.py`
  - Popen seam, config, child adapter, factory와 error를 public export에 추가했습니다.
- `examples/volume03/mcp_stdio_subprocess_factory.py`
  - `OfflinePopen`/`OfflinePopenProcess` in-memory fake만 사용해 fixed argv·`shell=False`와
    정확히 한 번의 Popen seam call을 출력합니다. 실제 subprocess, shell, signal, pipe IO,
    filesystem, network, 외부 MCP server, Tool 또는 destructive action은 수행하지 않습니다.
- `tests/volume03/test_mcp_subprocess_factory.py`
  - fake Popen이 exact binary pipe/cwd/env/shell kwargs를 한 번 받는지, config environment가
    caller dict 변경에 흔들리지 않는지, unsafe config이 Popen 전에 거부되는지, raw Popen
    failure가 숨겨지는지, bounded Popen timeout이 `None`이 되는지를 검증합니다.
- `docs/volume03-tool-calling-mcp/23-mcp-stdio-subprocess-factory.md`
  - ownership, fixed Popen boundary, offline exercise, explicit non-goals을 문서화했습니다.
- `docs/volume03-tool-calling-mcp/README.md`
  - 스물세 번째 학습 장을 목록에 추가했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book-volume-03`

```text
$ uv run python examples/volume03/mcp_stdio_subprocess_factory.py
argv: volume03-safe-echo-server --stdio
shell: False
popen_calls: 1
child_already_exited: True

$ uv run ruff check src/ai_platform/mcp tests/volume03/test_mcp_subprocess_factory.py examples/volume03/mcp_stdio_subprocess_factory.py
All checks passed!

$ uv run mypy src
Success: no issues found in 22 source files

$ uv run pytest tests/volume03/test_mcp_host.py tests/volume03/test_mcp_subprocess_factory.py -q
33 passed in 0.20s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 22 source files

$ uv run pytest -q
198 passed in 1.16s

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

`uv` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만
프로젝트 가상환경에서 정상 실행했습니다. 실제 Popen default path는 test/example에서 호출하지
않았으며 fake in-memory Popen/process만 사용했습니다.

## 다음 슬라이스

Popen factory가 만든 stdout/stderr binary pipes를 actual deployment에서 안전하게 소비하기 전에,
동시 bounded drain의 ownership과 byte ceiling overflow policy를 separate adapter로 설계하고 fake
readable streams로 검증해야 합니다. 이때 stdout/stderr deadlock/backpressure, decode/redaction,
EOF/partial read/error 순서를 작은 slice로 분리하세요. stdin write framing, cancellation/disconnect,
Windows/POSIX process groups, exit-code restart/backoff, durable approval/audit/idempotency,
Hermes/Codex integration은 계속 별도 설계·문서·테스트가 필요합니다.
