# MCP STDIO finite restart/backoff: exit-code와 fake monotonic time을 좁게 모델링하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- allowlisted `McpStdioHostLaunchPlan`의 작은 `restart_limit`만 replacement child budget으로 사용한다.
- terminal exit code `0`과 bounded non-zero exit을 clean/unexpected으로 명확히 분류한다.
- injected monotonic clock과 sleeper로 0.25초부터 두 배가 되는 유한 backoff만 검증한다.
- unknown exit, exhausted budget, invalid plan, clock/sleeper failure가 replacement start 전에 멈추게 한다.

## 2. restart ownership을 OS adapter에서 분리하기

`McpStdioRestartSupervisor`는 actual child를 감시하거나 process를 죽이지 않습니다. Lifecycle owner가 이미 얻은 terminal exit code 하나를 전달하면, supervisor는 immutable allowlisted plan의 budget 안에서 **한 번의** replacement start 여부만 결정합니다.

```text
trusted terminal exit ──> finite restart supervisor ──> injected monotonic clock
                                  │                         │
allowlisted launch plan ──────────┼─> injected sleeper ─────┤
                                  │                         │
                                  └─> existing shell-free child factory

unknown/budget exhausted/clock-or-sleep failure: no new start
```

`0`은 clean exit이므로 restart하지 않습니다. `1..255` non-zero exit은 platform-specific signal name이나 stderr detail을 노출하지 않는 `UNEXPECTED` class입니다. `None`, bool, negative code, 255보다 큰 code는 terminal state를 확신할 수 없는 unknown exit으로 취급해 clock/sleeper/factory 전에 거부합니다.

## 3. 좁은 API 계약

- `McpStdioRestartSupervisor(plan, factory, monotonic_clock=..., sleeper=...)`는 trusted allowlisted plan과 child factory만 받는다.
- `observe_exit(exit_code)`는 clean exit 또는 exhausted budget에서 clock/sleeper/factory를 호출하지 않는다.
- successful restart마다 delay는 `0.25`, `0.5`, `1.0` 초처럼 두 배가 된다. 현재 plan의 maximum restart budget은 3이므로 delay도 유한하다.
- sleeper 뒤 두 번째 monotonic timestamp가 첫 timestamp보다 뒤이고 deadline 이상이어야 factory를 한 번 호출한다.
- clock/sleeper/factory exception과 invalid timestamp는 raw detail 없이 generic error가 된다. 실패한 replacement start는 budget을 소비하지 않고 automatic retry도 하지 않는다.

이 model은 subprocess, `time.monotonic`, `sleep`, signal, Job Object, process group, pipe, thread, event loop, network, Tool 또는 destructive action을 직접 호출하지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_restart_backoff_policy.py
uv run pytest tests/volume03/test_mcp_restart_policy.py -q
```

예상 출력입니다.

```text
exit_classification: unexpected
backoff_seconds: 0.25
restart_count: 1
offline_start_calls: 1
```

예제의 clock, sleeper, child, factory는 전부 in-memory fake입니다. command-looking argv도 allowlist 문자열 tuple일 뿐이며 실제 Popen, OS clock/sleep, process, shell, pipe, filesystem, network, MCP server, Tool 또는 destructive action은 수행하지 않습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_restart_policy.py`는 fake seam으로 다음을 검증합니다.

1. unexpected exit 둘은 0.25초, 0.5초 delay 뒤 shell-free plan으로 각각 한 번만 start한다.
2. clean exit은 clock, sleeper, factory를 호출하지 않는다.
3. finite restart budget이 다하면 backoff나 새 start를 하지 않는다.
4. unknown exit은 모든 side-effecting seam 전에 거부한다.
5. clock/sleeper failure detail을 숨기고 factory 전에 중단한다.
6. sleeper가 deadline까지 monotonic time을 전진시키지 않으면 start하지 않는다.
7. invalid plan은 supervisor construction 중 factory start 전에 거부한다.

## 6. production에 그대로 연결하지 않기

이 code는 crash-loop supervisor가 아닙니다. Real host는 OS-specific reaping, child/descendant ownership, wall-clock vs monotonic persistence, restart state durability, jitter, concurrency lock, health handshake, output-drain cleanup, exit taxonomy, metrics/alerts와 operator disable/reconciliation을 따로 설계해야 합니다.

특히 restart가 side-effecting Tool request의 exactly-once를 보장하지 않습니다. Durable idempotency key, receiver acknowledgement, approval binding, append-only audit, tenant quota, compensation/reconciliation 없이 destructive Tool을 automatic restart path에 연결하지 마세요.

## 7. 완료 체크리스트

- [ ] restart budget이 caller/model input이 아닌 allowlisted immutable plan에서만 왔다.
- [ ] clean, unexpected, unknown exit이 서로 다른 start behavior인지 확인했다.
- [ ] exhausted budget과 invalid time seam이 replacement start 전에 중단되는지 확인했다.
- [ ] monotonic deadline과 finite exponential delay를 fake clock/sleeper로 확인했다.
- [ ] example/test가 actual process, sleep, signal, Tool, destructive action 없이 실행됐는지 확인했다.
- [ ] OS reaping, durable crash-loop control, approval/audit/idempotency가 별도 작업임을 확인했다.
