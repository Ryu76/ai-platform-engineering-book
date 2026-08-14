# MCP client integration handoff: Hermes·Codex에 exact Tool visibility만 넘기기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- Hermes Agent와 Codex CLI를 **실행하지 않고** client consumer label로만 구분한다.
- deployment-owned exact Tool allowlist가 static MCP catalog에 실제 있을 때만 immutable handoff을 만든다.
- wildcard, prefix, empty/mutable list, catalog 밖 Tool을 client config writer 전에 막는다.
- handoff 생성과 실제 client config write/reload/connect/Tool execution ownership을 분리한다.

## 2. 실제 client configuration을 model policy와 섞지 않기

`prepare_mcp_client_integration_handoff()`은 `McpStdioHostLaunchPlan`, `McpServerCatalog`,
`McpClientToolVisibilityPolicy`의 in-memory snapshot만 받습니다. 결과는 client 이름, allowlisted
server 이름, exact visible Tool name tuple뿐입니다.

```text
trusted launch plan ──────────┐
trusted static catalog ───────┼─> client-neutral handoff ─> separate config adapter
trusted exact visibility policy┘             │
                                   missing/wildcard: no client I/O
```

`hermes-agent`와 `codex-cli` enum은 이 teaching fixture의 **consumer label**입니다. 이 module은
각 client의 config schema, executable path, environment, reload command, connection lifecycle을
알거나 생성하지 않습니다. Hermes의 실제 MCP 구성·filtering 절차는 공식 문서
[Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes)를 따르세요.

## 3. 좁은 API 계약

- `McpClientToolVisibilityPolicy(client, tool_names)`는 1–16개 immutable exact Tool name tuple만
  허용한다. `*`, line break, duplicate와 mutable list는 거부한다.
- `prepare_mcp_client_integration_handoff(plan, catalog, policy)`는 policy의 모든 name이 현재 static
  catalog에 있을 때만 handoff을 반환한다.
- catalog 밖 name, invalid plan/catalog/policy, catalog snapshot failure는 raw catalog metadata나
  adapter exception detail 없이 generic error로 끝난다.
- 성공 handoff은 client configuration 파일을 write하거나 reload하지 않고, MCP server를 launch/connect
  하지 않으며 Tool execution/approval/audit/idempotency를 우회하지 않는다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_client_integration_handoff.py
uv run pytest tests/volume03/test_mcp_client_handoff.py -q
```

예상 출력입니다.

```text
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
```

예제는 `safe_calculator`/`safe_text_case` allowlist definition과 memory-only launch plan/catalog/policy만
사용합니다. Hermes/Codex client, Popen, shell, filesystem, network, MCP server, Tool 또는 destructive
action은 실행하지 않습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_client_handoff.py`는 다음을 검증합니다.

1. Hermes Agent와 Codex CLI label 모두 exact selected Tool 하나만 handoff에 남긴다.
2. mutable/empty/duplicate/wildcard/newline name은 catalog 조회 전에 거부된다.
3. catalog에 없는 Tool은 available Tool metadata를 반사하지 않고 거부된다.
4. invalid launch plan 또는 catalog는 client handoff 전에 거부된다.

## 6. production에 그대로 연결하지 않기

이 code는 Hermes/Codex adapter나 security boundary를 대체하지 않습니다. Production config writer는
client별 공식 schema와 version compatibility, credential/secret handling, file permission, atomic write,
reload acknowledgement, transport TLS/STDIO ownership, server identity, tenant policy와 operator rollback을
별도로 검증해야 합니다.

특히 client의 tool filtering은 server-side allowlist, Tool schema validation, approval, durable
audit/idempotency, resource quota를 대체하지 않습니다. Client reload 또는 MCP reconnect 뒤에도
side-effecting Tool을 blind retry하지 말고 receiver acknowledgement와 reconciliation record를 확인하세요.

## 7. 완료 체크리스트

- [ ] client label과 actual config/launch ownership을 분리했다.
- [ ] visible Tool이 wildcard가 아닌 deployment-owned exact allowlist인지 확인했다.
- [ ] 모든 selected Tool이 static catalog에 존재하는지 client I/O 전에 확인했다.
- [ ] example/test가 actual client, process, network, Tool, destructive action 없이 실행됐는지 확인했다.
- [ ] Hermes actual config는 공식 문서, Codex client-specific schema는 해당 공식 문서로 별도 검증해야 함을 확인했다.
