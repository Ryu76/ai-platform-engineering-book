# MCP client configuration health: attested receipt 뒤 health evidence를 분리하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- fresh exact configuration attestation을 먼저 검증한 뒤 client-specific health probe를 호출한다.
- malformed probe와 attestation mismatch/failure가 health probe 호출 전에 멈추게 한다.
- probe의 exact bool `True`만 original immutable handoff으로 승격하고, false/non-bool/exception에서는 partial visibility를 반환하지 않는다.
- in-memory health seam과 actual reload/reconnect, server identity, transport health의 production ownership을 구분한다.

## 2. receipt provenance와 usable state는 다르다

Configuration acknowledgement equality와 receipt provenance가 통과해도, client가 현재 reload를 끝냈거나 MCP server에 연결 가능한지는 별도의 질문입니다. `verify_mcp_client_configuration_health()`는 기존 attestation을 먼저 대조한 뒤 deployment가 소유한 `McpClientConfigurationHealthProbe`에 정확히 한 번의 health evidence를 요청합니다.

```text
exact application + fresh acknowledgement + challenge
                    │
                    v
      attestation verifier (exact True only)
                    │
                    v
       client-specific health probe (exact True only)
                    │
                    v
             original immutable handoff

invalid/mismatch/false/exception: no partial handoff
```

Probe는 `McpClientConfigurationAttestationRequest`만 받습니다. 따라서 이 teaching boundary는 config path/content, secret, credential, adapter log, connection object를 보관하거나 반환하지 않습니다. `True`만 성공이며 `1`, `"healthy"`, `None`, `False`는 모두 거부됩니다.

## 3. 좁은 API 계약

- `verify_mcp_client_configuration_health(request, attestation, attestation_verifier, health_probe)`은 invalid request/attestation/verifier/probe를 먼저 검증한다.
- existing freshness/provenance attestation이 실패하면 health probe를 호출하지 않는다.
- attestation이 성공한 경우에만 health probe를 정확히 한 번 호출한다.
- probe exception, `False`, non-bool return은 raw adapter detail 없이 generic error가 되며 original handoff 또는 partial Tool visibility를 반환하지 않는다.

이 module은 Hermes Agent/Codex CLI, configuration file, credential/signature library, reload/connect command, subprocess, filesystem, network, MCP server, Tool 또는 destructive action을 호출하지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_client_configuration_health.py
uv run pytest tests/volume03/test_mcp_client_health.py -q
```

예상 출력입니다.

```text
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
health_probe_calls: 1
```

예제는 fixed in-memory `safe_calculator` visibility, acknowledgement, challenge와 two fake verifier/probe만 사용합니다. Hermes/Codex client, configuration file, secret, Popen, shell, filesystem, network, MCP server, Tool 또는 destructive action은 실행하지 않습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_client_health.py`는 다음을 검증합니다.

1. exact attestation과 healthy probe가 seam별 한 번의 call 뒤 original immutable handoff을 반환한다.
2. challenge mismatch와 false attestation verifier는 health probe 호출 전에 거부된다.
3. health probe `False`, non-bool return, exception이 partial handoff과 raw adapter detail 없이 거부된다.
4. invalid health probe는 attestation verifier와 health probe 호출 전에 거부된다.

## 6. production에 그대로 연결하지 않기

이 model의 fake probe `True`는 actual client reload, reconnect, server identity, authenticated session 또는 usable MCP method를 증명하지 않습니다. Production adapter는 Hermes의 actual MCP configuration과 lifecycle을 공식 [Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes)에 따라 구현하고, Codex는 배포 중인 version의 official configuration schema를 별도로 대조해야 합니다.

또한 supported schema/version, authenticated issuer/signature와 key rotation, secret injection, config file ownership/permission, atomic write/rollback, reload acknowledgement provenance, reconnect/health timeout, server identity, TLS/STDIO transport lifecycle, tenant isolation, durable audit/idempotency/reconciliation, metrics/alerts와 operator review가 필요합니다. Client-visible filtering과 health receipt는 server-side allowlist, JSON Schema validation, approval, quota를 대체하지 않습니다. Reload/reconnect 뒤 side-effecting Tool을 blind retry하지 말고 receiver acknowledgement와 durable reconciliation record를 확인하세요.

## 7. 완료 체크리스트

- [ ] health probe가 fresh exact provenance attestation 뒤에만 호출되는지 확인했다.
- [ ] exact bool `True` 이외의 probe 결과와 exception이 partial handoff 없이 거부되는지 확인했다.
- [ ] example/test가 actual client, config file, credential, process, network, Tool, destructive action 없이 실행됐는지 확인했다.
- [ ] fake health evidence가 actual reload/reconnect/server identity proof가 아님을 확인했다.
- [ ] official schema, authenticated lifecycle, credential/file ownership, durable operations가 별도 production 검증임을 확인했다.
