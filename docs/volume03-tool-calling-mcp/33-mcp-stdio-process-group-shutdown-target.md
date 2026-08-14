# MCP STDIO process-group shutdown target: child-owned isolation intent를 fake seam으로 검증하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- allowlisted `McpStdioHostLaunchPlan`을 actual signal API가 아닌 typed shutdown intent에만 연결한다.
- POSIX direct child-owned process group과 Windows child-owned Job scope를 서로 다른 target kind로 구분한다.
- foreign/shared group, unsupported platform, invalid plan을 sender 호출 전에 거부한다.
- graceful/force를 caller가 명시적으로 선택한 한 단계로만 전달하고 자동 escalation을 하지 않는다.

## 2. 실제 signal보다 먼저 isolation ownership을 검증하기

`McpStdioIsolatedChildGroup`은 trusted platform adapter가 이미 확인한 snapshot입니다. Untrusted MCP client/model은 PID, group ID, platform, phase를 만들거나 바꿀 수 없습니다.

```text
trusted allowlisted plan ───┐
trusted platform fixture ───┼─> typed shutdown target ─> injected sender
trusted lifecycle phase ────┘        │                         │
                                      │                         └─ real OS API는 이 장의 범위 밖
                           foreign/invalid: no sender call
```

POSIX fixture에서는 direct child PID가 isolation owner와 process-group ID 모두와 같아야 합니다. 따라서 parent/sibling/shared group을 target으로 보내지 않습니다. Windows fixture에서는 direct child가 Job scope의 owner여야 하고 Job scope ID는 trusted adapter가 제공한 positive opaque ID입니다. 이 model은 member discovery나 OS API를 수행하지 않습니다.

`McpStdioGroupShutdownPhase.GRACEFUL`과 `FORCE`는 raw signal name이 아닙니다. Existing lifecycle owner가 각각의 의미를 platform-specific adapter에 매핑해야 하며, 이 module은 graceful wait, force escalation, retry, child reap, restart를 수행하지 않습니다.

## 3. 좁은 API 계약

- `prepare_mcp_stdio_group_shutdown_target(plan, group, phase)`은 I/O 없이 immutable typed target을 만듭니다.
- `send_mcp_stdio_group_shutdown_target(...)`은 validation이 끝난 target 하나만 injected `sender.send()`에 한 번 전달합니다.
- sender failure는 raw platform error를 숨긴 generic error가 되고 retry나 force escalation을 자동 수행하지 않습니다.
- invalid plan/group/platform/phase/sender는 sender 호출 전에 거부합니다.

이 경계는 subprocess, `os.killpg`, `signal`, Windows Job Object API, shell, pipe, network, Tool 또는 destructive action을 직접 호출하지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_stdio_process_group_shutdown_target.py
uv run pytest tests/volume03/test_mcp_process_group.py -q
```

예상 출력입니다.

```text
server_name: safe-echo
platform: posix
target_kind: posix_process_group
phase: graceful
offline_sender_calls: 1
```

예제의 `OfflineGroupShutdownSender`는 target을 memory list에만 기록합니다. 실제 child, process group, Job Object, signal, subprocess, shell, filesystem, network, MCP server, Tool 또는 destructive action은 없습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_process_group.py`는 fake sender로 다음을 검증합니다.

1. POSIX child-owned group에는 `POSIX_PROCESS_GROUP` graceful target 하나만 전달한다.
2. Windows child-owned Job scope에는 `WINDOWS_JOB` force target 하나만 전달한다.
3. foreign owner와 child가 leader가 아닌 POSIX scope는 construction 중 거부되어 sender가 호출되지 않는다.
4. unsupported platform, invalid plan, invalid phase도 sender 호출 전에 거부된다.
5. sender exception detail은 숨기고 한 번 호출 뒤 retry/escalation하지 않는다.
6. target은 immutable이며 platform과 target kind가 섞이면 거부된다.

## 6. 운영에 그대로 연결하지 않기

이 model의 fixture 값은 OS가 제공하는 진실의 원천이 아닙니다. Production host는 fixed `shell=False` launch path에서 child를 새 POSIX session/process group 또는 reviewed Windows Job으로 **생성 시점부터** 격리하고, handle/PID reuse, privilege boundary, descendant policy, reaping, timeout, concurrent pipe drain을 OS별로 검증해야 합니다.

특히 `FORCE` intent는 side-effecting work를 중간 상태로 남길 수 있습니다. Durable approval, idempotency key, receiver acknowledgement, append-only audit, compensation/reconciliation을 갖춘 execution service 없이 destructive Tool에 연결하지 마세요.

## 7. 완료 체크리스트

- [ ] allowlisted plan과 trusted child-owned fixture만 target 생성에 쓰는지 확인했다.
- [ ] POSIX group leader/Windows Job owner가 direct child와 일치하지 않으면 거부하는지 확인했다.
- [ ] invalid input이 sender/OS signal 전에 중단되는지 확인했다.
- [ ] graceful/force가 raw signal이나 자동 escalation이 아닌 typed one-shot intent인지 확인했다.
- [ ] example/test가 실제 process·signal·Tool·destructive action 없이 실행됐는지 확인했다.
- [ ] actual platform isolation/reaping/restart와 durable execution controls가 별도 작업임을 확인했다.
