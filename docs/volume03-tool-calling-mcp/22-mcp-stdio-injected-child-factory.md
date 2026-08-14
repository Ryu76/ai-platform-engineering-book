# MCP STDIO child factory: allowlisted plan만 trusted factory에 전달하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- untrusted selector나 command text 대신 이미 검증된 immutable launch plan만 child factory에 전달한다.
- factory 호출에서 `shell=False`를 고정하고 argv와 stdout/stderr byte budget을 바꾸지 않는다.
- factory의 raw failure나 불완전한 child object를 generic host error로 좁힌다.
- start failure에서 자동 restart 또는 재시도를 하지 않는다.

## 2. 시작 ownership 경계

`start_mcp_stdio_child(plan, factory)`는 exact allowlist lookup이 만든
`McpStdioHostLaunchPlan`과 trusted host가 제공한 `McpStdioChildFactory`만 받습니다.
Client, model, MCP peer는 executable, command string, shell flag, cwd, environment,
pipe object, resource limit을 전달할 수 없습니다.

```text
untrusted server selector → exact allowlist lookup → immutable plan
trusted OS-specific factory ← fixed argv + byte budgets + shell=False
                                               │
                                               └→ owned child adapter → finite shutdown
```

factory contract에는 `argv`, `max_stdout_bytes`, `max_stderr_bytes`, `shell=False`만
있습니다. 실제 OS process API, stdin/stdout/stderr pipe 생성, process group과 platform
signal 선택은 아직 구현하지 않았습니다. 따라서 이 slice는 subprocess, shell, file,
network 또는 Tool을 실행하지 않습니다.

## 3. 유한한 start 알고리즘

1. `plan`이 public immutable launch-plan type인지 확인한다.
2. factory를 정확히 한 번 호출하고 plan의 tuple argv·두 byte budget·`shell=False`만
   전달한다.
3. 반환 객체가 `poll`/`terminate`/bounded `wait`/`kill` child contract를 모두 제공하는지
   확인한다.
4. factory failure 또는 불완전한 child에서는 command/path/OS exception detail을 노출하지
   않는 `McpStdioHostError`로 끝낸다.

이 함수에는 retry, restart, sleep, command parsing이 없습니다. start가 실패했다고 다른
command를 시도하거나 같은 command를 다시 실행하지 않습니다.

## 4. 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
python examples/volume03/mcp_stdio_injected_child_factory.py
pytest tests/volume03/test_mcp_host.py -q
```

예제 출력은 다음과 같습니다.

```text
server_name: safe-echo
argv: volume03-safe-echo-server --stdio
shell: False
child_already_exited: True
```

`OfflineFactory`와 `OfflineChild`는 메모리 객체입니다. 출력의 command-looking argv도
문자열 tuple을 표시할 뿐 실행하지 않습니다. 예제는 실제 subprocess, shell, OS signal,
pipe, filesystem, network, 외부 MCP server, Tool 또는 destructive action을 수행하지 않습니다.

## 5. 검증하는 시작·거부 경계

| 입력/결과 | 처리 |
|---|---|
| allowlisted plan | tuple argv·fixed byte budgets·`shell=False`로 factory 한 번 호출 |
| factory가 child 반환 | shutdown에서 쓸 최소 child contract만 반환 |
| factory가 예외 발생 | raw exception detail 없이 generic start failure |
| factory가 `object()` 반환 | incomplete child를 거부 |
| caller가 non-plan 전달 | generic invalid-plan failure |

## 6. 운영 적용 시 추가할 것

다음 slice에서만 실제 OS-specific factory를 별도 adapter로 설계·검증해야 합니다.

- Python `subprocess` API의 exact `shell=False`, fixed argv, cwd/environment allowlist
- stdin write ownership과 stdout/stderr simultaneous bounded drain·backpressure
- Windows/POSIX process-group, cancellation, zombie reaping과 signal semantics
- exit-code 분류, finite restart/backoff, durable idempotency/audit·operator reconciliation

side-effecting Tool을 child start와 직접 결합하지 마세요. production에서는 authenticated
identity와 tenant boundary, durable approval/audit/idempotency, quota와 compensation policy를
정의한 execution service가 별도로 필요합니다.

## 7. 완료 체크리스트

- [ ] factory가 exact allowlisted plan 값만 한 번 받는지 확인했다.
- [ ] `shell=False`가 caller input이 아니라 host에서 고정되는지 확인했다.
- [ ] factory exception과 invalid child result가 raw detail 없이 거부되는지 확인했다.
- [ ] 예제와 테스트가 fake in-memory factory/child만 사용하는지 확인했다.
- [ ] actual process factory, pipe drain, cancellation, restart, durable audit/idempotency가 별도 작업인지 확인했다.
