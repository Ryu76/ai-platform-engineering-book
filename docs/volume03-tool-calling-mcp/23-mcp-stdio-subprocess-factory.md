# MCP STDIO subprocess factory: fixed argv·cwd·environment를 fake Popen seam으로 검증하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- allowlist가 만든 tuple argv와 host-fixed `shell=False`만 OS-specific factory에 전달한다.
- parent environment를 암묵적으로 물려주지 않고 trusted deployment의 complete environment snapshot을 사용한다.
- 상대 경로나 caller/model/MCP peer가 제공한 cwd·environment·shell flag를 Popen 호출에 전달하지 않는다.
- 실제 process를 만들지 않는 fake Popen API로 exact pipe configuration을 검증한다.

## 2. Popen adapter ownership 경계

`McpStdioSubprocessFactory`는 앞 장의 generic `McpStdioChildFactory` contract를 구현하는
production-specific adapter입니다. `McpStdioSubprocessConfig`는 trusted deployment가 생성할
immutable cwd/environment snapshot입니다. 시작 request에는 selector, command text, cwd,
environment, shell flag, pipe object가 없습니다.

```text
untrusted selector → exact allowlist → immutable launch plan
                                      │ fixed argv + shell=False
trusted config (cwd + complete env) ─┼→ McpStdioSubprocessFactory
                                      │             │
                                      │             └→ injected Popen seam
                                      │                    stdin/stdout/stderr=PIPE
                                      └→ wrapped child shutdown contract
```

factory는 `stdin=PIPE`, `stdout=PIPE`, `stderr=PIPE`, `text=False`, `bufsize=0`,
`close_fds=True`, `shell=False`를 정확히 고정합니다. `env`에는 current parent environment를
merge하지 않고 config snapshot만 전달합니다. 따라서 deployment는 executable lookup에 필요한
`PATH`와 platform-required variables를 명시적으로 review해야 합니다.

## 3. 이 slice의 유한한 start 알고리즘

1. trusted config에서 non-empty absolute cwd와 bounded NUL-free environment를 snapshot한다.
2. 기존 `start_mcp_stdio_child()`가 allowlisted plan의 tuple argv와 `shell=False`만 factory에
   한 번 전달한다.
3. factory는 injected/default `Popen` adapter를 정확히 한 번 호출해 fixed stdio pipe topology와
   config cwd/environment를 설정한다.
4. 반환 process는 `poll`/`terminate`/`wait`/`kill` contract로 좁혀 child adapter로 감싼다.
5. Popen start failure나 invalid process object는 raw executable/path/OS detail 없이 generic
   host start failure로 끝낸다.

`wait()`의 `subprocess.TimeoutExpired`만 bounded wait의 `None`으로 바꿉니다. 다른 adapter
failure는 기존 host shutdown boundary가 generic failure로 좁힙니다. 이 단계는 restart, retry,
command parsing, stdout/stderr read/write를 하지 않습니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_subprocess_factory.py
uv run pytest tests/volume03/test_mcp_subprocess_factory.py -q
```

예제 출력은 다음과 같습니다.

```text
argv: volume03-safe-echo-server --stdio
shell: False
popen_calls: 1
child_already_exited: True
```

예제의 `OfflinePopen`과 `OfflinePopenProcess`는 메모리 fake입니다. `Popen`을 호출하지 않고
받은 kwargs만 기록합니다. command-looking argv도 단순 문자열 tuple입니다. 예제와 테스트는
실제 subprocess, shell, process signal, pipe IO, filesystem, network, 외부 MCP server, Tool,
destructive action을 실행하지 않습니다.

## 5. 검증하는 허용·거부 경계

| 입력/상태 | 처리 |
|---|---|
| allowlisted immutable argv | fake Popen에 tuple 그대로 한 번 전달 |
| host config의 absolute cwd·env | explicit `cwd`·snapshot `env`로만 전달 |
| Popen topology | three binary pipes, `shell=False`, unbuffered binary mode, `close_fds=True` |
| caller가 나중에 env dict 변경 | config snapshot은 변하지 않음 |
| relative cwd/empty env/NUL/env key의 `=` | Popen 전 거부 |
| fake Popen start exception | raw detail 없는 generic host start failure |
| Popen `wait` timeout | `None`으로 한 번 반환; 재시작하지 않음 |

## 6. 아직 의도적으로 제외한 운영 책임

이 adapter가 `Popen`을 열 수 있다는 사실만으로 production MCP host가 안전해지지는 않습니다.
다음은 각각 별도 slice에서 설계·검증해야 합니다.

- stdout/stderr simultaneous bounded drain, byte-budget enforcement, decode/redaction, backpressure
- stdin write framing, peer disconnect/cancellation, partial IO failure semantics
- Windows/POSIX process group, console/control signal, orphan/zombie reaping semantics
- exit-code taxonomy, finite restart/backoff, crash-loop metrics and operator reconciliation
- authenticated identity/tenant boundary, durable approval/idempotency/append-only audit and compensation

특히 child가 실행할 Tool을 이 adapter에 직접 연결하지 마세요. side-effecting action은 durable
approval, idempotency, quota, compensation policy를 가진 별도 execution service에서 처리해야 합니다.

## 7. 완료 체크리스트

- [ ] Popen이 string command가 아닌 allowlisted tuple argv만 받는지 확인했다.
- [ ] `shell=False`, fixed binary pipe topology, `close_fds=True`가 host-owned인지 확인했다.
- [ ] cwd와 complete environment가 trusted immutable config snapshot인지 확인했다.
- [ ] fake Popen으로 actual process 없이 exact kwargs와 raw failure narrowing을 검증했다.
- [ ] pipe drain, cancellation, process-group signal, restart, durable audit/idempotency가 별도 작업임을 확인했다.
