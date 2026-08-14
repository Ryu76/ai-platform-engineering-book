# MCP client configuration capability: healthy attestation 뒤 exact Tool snapshot을 대조하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- fresh exact configuration attestation과 health evidence를 먼저 검증한 뒤 capability probe를 호출한다.
- health failure, malformed probe와 malformed receipt가 capability probe 호출 또는 handoff 반환 전에 멈추게 한다.
- client-visible Tool tuple이 original immutable handoff과 정확히 같을 때만 승격하고 extra/missing/reordered Tool에는 partial visibility를 반환하지 않는다.
- in-memory capability seam과 actual `tools/list`, authenticated session/server identity, reconnect lifecycle의 production ownership을 구분한다.

## 2. health와 exact capability는 다르다

Configuration attestation의 receipt provenance와 health probe가 통과해도, client가 **현재 정확히 어떤 Tool을 보이는지**는 별도의 질문입니다. `verify_mcp_client_configuration_capability()`는 기존 health verifier를 먼저 대조한 뒤 deployment가 소유한 `McpClientConfigurationCapabilityProbe`에 one-shot immutable Tool snapshot을 요청합니다.

```text
exact application + fresh acknowledgement + challenge
                    │
                    v
      attestation verifier (exact True only)
                    │
                    v
       client health probe (exact True only)
                    │
                    v
  capability probe → exact immutable Tool-name tuple
                    │
                    v
          original immutable handoff

mismatch/malformed/exception: no partial handoff
```

Probe receipt에는 Tool name tuple만 있습니다. Configuration path/content, secret, credential, server response, connection/session object나 adapter log를 보관하거나 반환하지 않습니다. Receipt tuple은 expected handoff tuple과 **순서까지** 같아야 합니다. 따라서 extra Tool, missing Tool, reordered Tool, wildcard 혹은 mutable/forged receipt는 거부됩니다.

## 3. 좁은 API 계약

- `verify_mcp_client_configuration_capability(request, attestation, attestation_verifier, health_probe, capability_probe)`은 invalid request/attestation/verifier/probe를 먼저 검증한다.
- existing health boundary가 실패하면 capability probe를 호출하지 않는다.
- health가 통과한 경우에만 capability probe를 정확히 한 번 호출한다.
- `McpClientConfigurationCapabilityReceipt`는 1–16개의 unique exact non-empty single-line Tool name tuple만 받는다.
- probe exception, malformed receipt, extra/missing/reordered name에는 raw adapter detail 또는 partial handoff 없이 generic error가 된다.

이 module은 Hermes Agent/Codex CLI, configuration file, credential/signature library, actual `tools/list`, reload/connect command, subprocess, filesystem, network, MCP server, Tool 또는 destructive action을 호출하지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_client_configuration_capability.py
uv run pytest tests/volume03/test_mcp_client_capability.py -q
```

예상 출력입니다.

```text
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
capability_probe_calls: 1
```

예제는 fixed in-memory `safe_calculator` visibility, acknowledgement, challenge와 three fake seam만 사용합니다. Hermes/Codex client, configuration file, secret, Popen, shell, filesystem, network, MCP server, Tool 또는 destructive action은 실행하지 않습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_client_capability.py`는 다음을 검증합니다.

1. exact attestation·health·capability가 seam별 한 번의 call 뒤 original immutable handoff을 반환한다.
2. attestation mismatch와 failed health가 downstream capability probe 호출 전에 거부된다.
3. extra/missing Tool tuple, reordered tuple, non-receipt result가 partial handoff 없이 거부된다.
4. probe exception의 raw adapter detail을 숨기고, frozen receipt를 우회해 mutation한 tuple도 probe 뒤 재검증한다.
5. invalid capability probe는 verifier, health probe, capability probe 호출 전에 거부된다.

## 6. production에 그대로 연결하지 않기

Fake receipt의 exact tuple은 actual client `tools/list`, reload/reconnect success, authenticated client/session, server identity, transport health 또는 server-side execution authorization을 증명하지 않습니다. Production adapter는 Hermes의 actual MCP configuration과 lifecycle을 공식 [Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes)에 따라 구현하고, Codex는 배포 중인 version의 official configuration schema를 별도로 대조해야 합니다.

또한 supported schema/version, authenticated issuer/signature와 key rotation, secret injection, config file ownership/permission, atomic write/rollback, reload acknowledgement provenance, bounded reconnect and capability query timeout, server identity, TLS/STDIO transport lifecycle, tenant isolation, server-side allowlist/JSON Schema/approval/quota, durable audit/idempotency/reconciliation, metrics/alerts와 operator review가 필요합니다. Side-effecting Tool은 capability snapshot이 있다고 blind retry하지 말고 receiver acknowledgement와 durable reconciliation record를 확인하세요.

## 7. 완료 체크리스트

- [ ] capability probe가 fresh exact provenance attestation과 health evidence 뒤에만 호출되는지 확인했다.
- [ ] exact Tool tuple mismatch, malformed result와 exception이 partial handoff 없이 거부되는지 확인했다.
- [ ] example/test가 actual client, config file, credential, process, network, Tool, destructive action 없이 실행됐는지 확인했다.
- [ ] fake capability receipt가 actual `tools/list`/reconnect/server identity proof가 아님을 확인했다.
- [ ] official schema, authenticated lifecycle, credential/file ownership, server-side authorization과 durable operations가 별도 production 검증임을 확인했다.
