# MCP STDIO child shutdown: injected process에 유한한 graceful/force 종료 순서 적용하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- 이미 allowlisted launch plan에서 검증된 grace period를 child 종료 대기에만 사용한다.
- 이미 종료한 child에는 termination signal을 다시 보내지 않는다.
- graceful 종료가 시간 안에 끝나지 않을 때 정확히 한 번만 force-kill 한다.
- force-kill 뒤에도 exit code를 얻지 못하면 restart나 무한 wait 없이 실패로 끝낸다.

## 2. 소유권이 있는 shutdown 경계

`shutdown_mcp_stdio_child(plan, child)`는 **이미 신뢰된 host가 만들고 소유하는**
`McpStdioChildProcess` adapter만 받습니다. untrusted MCP client/model은 child object,
executable, argv, grace period, signal 종류를 전달할 수 없습니다. `plan`은 앞 장의 exact
allowlist lookup에서 만든 immutable snapshot이어야 합니다.

```text
trusted allowlist → immutable launch plan ──┐
trusted OS adapter → owned child process ───┼→ shutdown_mcp_stdio_child()
                                             │
child already exited → record exit only      │
running → terminate once → wait(grace)       │
wait expired → kill once → wait(0.0)         │
no final exit → generic host failure         │
```

이 작은 adapter는 `poll()`, `terminate()`, `wait(timeout)`, `kill()` 네 operation만
요구합니다. OS별 signal/process group 의미는 trusted adapter가 결정해야 합니다. 호출
순서와 timeout budget만 여기서 고정합니다.

## 3. 유한한 종료 알고리즘

1. `poll()`이 integer exit code를 주면 child는 이미 종료했습니다. 어떤 stop action도 보내지
   않고 result에 그 code만 기록합니다.
2. 아직 실행 중이면 `terminate()`를 한 번 요청하고 plan의
   `shutdown_grace_seconds`만큼 `wait()` 합니다.
3. grace wait이 `None`을 반환하면 `kill()`을 정확히 한 번 요청한 뒤 `wait(0.0)`으로
   child adapter의 최종 상태를 확인합니다.
4. force-kill 뒤에도 `None`이면 무한 wait, 자동 restart, 추가 kill을 하지 않고 generic
   `McpStdioHostError`를 발생시킵니다.

`McpStdioHostShutdownResult`는 server name, final exit code, graceful terminate 요청 여부,
force-kill 여부만 가진 immutable process-local result입니다. raw command, stderr, signal
exception detail은 반환하지 않습니다. boolean이나 string처럼 모호한 exit code도 거부합니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
uv run python examples/volume03/mcp_stdio_injected_child_shutdown.py
uv run pytest tests/volume03/test_mcp_host.py -q
```

예제 출력은 다음과 같습니다.

```text
server_name: safe-echo
exit_code: 0
termination_requested: True
force_killed: False
```

예제의 `OfflineChild`는 메모리 안의 fake object입니다. `terminate()`는 아무 OS signal도 보내지
않고 `wait()`도 고정 `0`만 반환합니다. executable, subprocess, shell, pipe, file, network,
외부 MCP server, Tool 또는 destructive action은 실행하지 않습니다.

## 5. 검증하는 종료·거부 경계

| child 상태 | 결과 |
|---|---|
| `poll()`이 `17` | terminate/kill/wait 없이 exit `17` 기록 |
| running, graceful wait이 `0` | terminate 한 번, plan grace 사용, force-kill 없음 |
| graceful wait이 `None`, forced wait이 `-9` | kill 한 번만 요청하고 exit `-9` 기록 |
| forced wait도 `None` | 추가 retry/restart 없이 generic host failure |
| boolean/string exit code | ambiguous status로 거부 |
| child adapter의 poll/terminate/wait/kill 예외 | raw exception을 숨긴 generic host failure |

`restart_limit`은 launch plan에서 이미 유한하게 검증되지만, 이 슬라이스에서는 의도적으로
사용하지 않습니다. exit-code 분류와 restart backoff/idempotency는 별도의 supervisor
slice에서 child start와 함께 설계해야 합니다.

## 6. 운영 적용 시 추가할 것

이 코드는 actual child를 시작하거나 pipe를 읽지 않습니다. production host에는 다음을 별도로
추가·검증해야 합니다.

- `shell=False` 및 fixed argv를 보장하는 OS-specific process factory
- stdout/stderr 동시 bounded drain, UTF-8 decode failure, backpressure와 redaction
- process-group teardown과 Windows/POSIX signal semantic 차이
- client disconnect/cancellation, exit-code 분류, finite restart/backoff
- authenticated identity, tenant boundary, durable approval·idempotency·append-only audit
- zombie/reaping, metrics, resource quota와 operator reconciliation

특히 force-kill은 실제 외부 process의 작업을 중간에 남길 수 있습니다. side-effecting Tool을
이 educational adapter에 연결하지 말고, durable approval·idempotency·compensation을 가진
운영 execution service에서 정확한 복구 정책을 정의하세요.

## 7. 완료 체크리스트

- [ ] already-exited child에는 stop action을 보내지 않는지 확인했다.
- [ ] graceful terminate와 plan의 bounded grace wait이 한 번씩만 호출되는지 확인했다.
- [ ] timeout 뒤 force-kill이 한 번만 호출되고 final exit를 요구하는지 확인했다.
- [ ] child adapter의 raw failure와 ambiguous exit code가 숨겨지는지 확인했다.
- [ ] example/test가 실제 subprocess·signal·Tool·destructive action 없이 실행됐는지 확인했다.
- [ ] pipe drain, cancellation, restart, durable audit/idempotency가 아직 별도 작업인지 확인했다.
