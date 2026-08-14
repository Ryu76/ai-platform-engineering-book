# MCP client configuration acknowledgement: exact handoff receipt를 config adapter와 분리하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- client-neutral exact Tool handoff을 deployment generation과 함께 immutable application으로 묶는다.
- 별도 Hermes/Codex configuration adapter가 반납한 최소 receipt가 client·server·Tool tuple·generation까지 모두 같은지 대조한다.
- wildcard, mutable list, duplicate, 줄바꿈이 든 visibility receipt와 manually forged handoff을 receipt 신뢰 전에 막는다.
- receipt equality와 actual client config의 schema/version, credential, file permission, reload health ownership을 분리한다.

## 2. client apply를 memory policy와 섞지 않기

`McpClientConfigurationApplication`과 `verify_mcp_client_configuration_acknowledgement()`는 external client adapter의 **최소 성공 receipt**만 대조합니다. Hermes Agent나 Codex CLI를 실행하거나 config file을 쓰지 않습니다.

```text
reviewed exact handoff + deployment generation ──> separate client-specific adapter
                                                     │
minimal exact acknowledgement <─────────────────────┘
             │
             └── equal client/server/tools/generation only: verified handoff

mismatch/mutable/wildcard/forged input: no client I/O by this model
```

`configuration_generation`은 deployment가 정한 opaque single-line correlation label입니다. 경로, config 내용, credential, reload log 또는 client schema가 아닙니다. Receipt가 equality를 통과해도 configuration file이 안전하거나 client가 실제로 connected 상태임을 증명하지 않습니다.

Hermes의 actual MCP 구성과 transport lifecycle은 공식 [Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes)를 따라 client-specific adapter에서 별도로 검증하세요. Codex도 사용 중인 version의 공식 configuration schema를 별도 검증해야 합니다.

## 3. 좁은 API 계약

- `McpClientConfigurationApplication(handoff, configuration_generation)`은 direct construction된 handoff도 다시 검사하며 non-empty one-line generation만 받는다.
- `McpClientConfigurationAcknowledgement(...)`는 successful apply/reload 뒤 external adapter가 줄 수 있는 client, server name, exact immutable Tool tuple, generation만 보관한다.
- `verify_mcp_client_configuration_acknowledgement(application, acknowledgement)`은 네 값이 exact match할 때만 **original** immutable handoff을 반환한다.
- client/server/Tool/generation 중 하나라도 다르거나 invalid object이면 generic error로 끝나며, config content, secret, file path, adapter log 또는 partial visibility를 반환하지 않는다.

이 module은 config write/reload/connect, subprocess, network, Tool execution, approval, audit, idempotency 또는 destructive action을 수행하지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_client_configuration_acknowledgement.py
uv run pytest tests/volume03/test_mcp_client_acknowledgement.py -q
```

예상 출력입니다.

```text
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
configuration_generation: volume03-demo-001
```

예제는 `safe_calculator` visibility라는 fixed in-memory snapshot만 대조합니다. Hermes/Codex client, configuration file, secret, Popen, shell, filesystem, network, MCP server, Tool 또는 destructive action은 실행하지 않습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_client_acknowledgement.py`는 다음을 검증합니다.

1. exact matching acknowledgement만 original immutable handoff을 반환한다.
2. client, server, Tool tuple, deployment generation 각각의 mismatch가 partial visibility 없이 거부된다.
3. mutable/empty/duplicate/wildcard/newline Tool receipt가 verification 전에 거부된다.
4. manually forged handoff의 invalid server name과 invalid application/acknowledgement object가 external adapter trust 전에 거부된다.

## 6. production에 그대로 연결하지 않기

이 model은 configuration adapter의 receipt equality만 검사하며 receipt provenance나 client health를 증명하지 않습니다. Production adapter는 공식 client schema/version compatibility, server identity, authenticated credential reference와 secret injection, config file ownership/permission, atomic write/rollback, reload acknowledgement provenance, reconnect/health check, transport TLS/STDIO lifecycle, tenant isolation, metrics/alerts와 operator review를 별도로 구현·검증해야 합니다.

Client-visible filtering은 server-side allowlist, JSON Schema validation, approval, durable audit/idempotency, quota를 대체하지 않습니다. Reload/reconnect 후 side-effecting Tool을 blind retry하지 말고 receiver acknowledgement와 durable reconciliation record를 확인하세요.

## 7. 완료 체크리스트

- [ ] receipt가 client·server·exact Tool tuple·deployment generation까지 exact match하는지 확인했다.
- [ ] mutable/wildcard visibility와 forged handoff이 external adapter trust 전에 거부되는지 확인했다.
- [ ] equality verification이 config content·credential·file path를 저장하지 않는지 확인했다.
- [ ] example/test가 actual client, config file, process, network, Tool, destructive action 없이 실행됐는지 확인했다.
- [ ] Hermes/Codex official schema, credential/file permission, atomic reload/health가 별도 production 검증임을 확인했다.
