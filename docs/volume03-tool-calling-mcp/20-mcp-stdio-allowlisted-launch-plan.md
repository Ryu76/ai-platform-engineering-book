# MCP STDIO host launch plan: shell 없이 고정 allowlist와 resource budget을 모델링하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- MCP STDIO server 선택값을 임의 command가 아닌 exact allowlist lookup으로 제한한다.
- shell command string 대신 immutable `argv` tuple만 host launch plan에 넣는다.
- stdout/stderr buffer, cancellation grace period, restart 횟수에 작은 상한을 둔다.
- 이 configuration model이 아직 process를 실행하거나 Tool 권한을 주지 않는다는 점을 구분한다.

## 2. 실행 전 경계

`McpStdioHostAllowlist`는 deployment 시 신뢰된 `McpStdioServerSpec` tuple로만 생성합니다. request나 model output은 server name 하나만 줄 수 있고, `prepare_launch()`는 정확히 일치하는 이름에서만 immutable `McpStdioHostLaunchPlan`을 만듭니다.

```text
untrusted selector: "safe-echo"
          │ exact lookup only
          ▼
trusted host allowlist
          │ fixed argv + bounded budgets
          ▼
immutable launch plan
          │ (future host owns subprocess lifecycle)
          ▼
no process started in this chapter
```

각 spec은 `argv` tuple을 보관합니다. 이것은 shell에 전달하는 command line string이 아닙니다. 이 모델에는 `shell=True` 같은 선택지가 없고, selector가 executable·argument·buffer limit·restart 수를 바꿀 수도 없습니다. 나중에 실제 host를 만들면 plan의 argv를 OS process API에 list/tuple 그대로 전달하고 shell을 끈 상태로 실행해야 합니다.

## 3. 유한한 host budget

실제 child process는 정상 request만 보내도 stdout/stderr를 계속 쓸 수 있고, disconnect나 crash 뒤 restart loop가 생길 수 있습니다. 그래서 spec 생성 시 아래 값이 이미 고정됩니다.

| 값 | 교육용 허용 범위 | 의미 |
|---|---:|---|
| `max_stdout_bytes` | 1,024–1,048,576 | MCP response pipe에 대해 host가 구현할 bounded drain budget |
| `max_stderr_bytes` | 1,024–1,048,576 | diagnostic pipe가 무한 메모리를 쓰지 않게 할 budget |
| `shutdown_grace_seconds` | 0.1–60초 | cancellation/disconnect 뒤 graceful shutdown을 기다릴 최대 시간 |
| `restart_limit` | 0–3 | crash/disconnect 재시작의 유한한 추가 시도 수 |

이 값들은 **계획**일 뿐입니다. 이 장의 code는 pipe를 drain하거나 signal을 보내거나 restart하지 않습니다. 실제 implementation은 pipe backpressure, UTF-8 decode 오류, process group/signal semantics, client disconnect, exit-code 분류, exponential backoff, log redaction와 durable audit를 별도로 구현하고 테스트해야 합니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_allowlisted_launch_plan.py
uv run pytest tests/volume03/test_mcp_host.py -q
```

예제 출력은 다음과 같습니다.

```text
server_name: safe-echo
argv: volume03-safe-echo-server --stdio
stdout_limit_bytes: 16384
restart_limit: 0
```

예제는 `safe-echo`라는 고정 name과 고정 argv snapshot만 출력합니다. executable, shell, subprocess, pipe, signal, network, file 또는 Tool을 실제로 실행하지 않습니다. `argv` 텍스트는 설명용 launch plan이며 이 저장소에 그 executable이 설치되어 있음을 뜻하지 않습니다.

## 5. 검증하는 거부 경계

| 입력/설정 | 결과 |
|---|---|
| exact `safe-echo` selector | review된 immutable plan만 반환 |
| unknown name, 공백이 붙은 name, non-string selector | generic allowlist error; command 세부정보 미노출 |
| duplicate name 또는 mutable list configuration | host 시작 전 거부 |
| shell-like string argv, NUL/LF/CR이 든 argument | spec 생성 전 거부 |
| 너무 작거나 boolean인 stream limit | spec 생성 전 거부 |
| 무한/0초 grace 또는 3 초과 restart budget | spec 생성 전 거부 |

## 6. 완료 체크리스트

- [ ] untrusted selector가 고정 allowlisted server name만 선택하는지 확인했다.
- [ ] command text가 아니라 tuple argv로만 launch plan을 만드는지 확인했다.
- [ ] stdout/stderr, shutdown, restart의 유한한 budget을 검증했다.
- [ ] 예제가 실제 subprocess나 Tool을 실행하지 않았는지 확인했다.
- [ ] 실제 process lifecycle·pipe drain·signal·restart 구현은 아직 별도 작업임을 확인했다.
