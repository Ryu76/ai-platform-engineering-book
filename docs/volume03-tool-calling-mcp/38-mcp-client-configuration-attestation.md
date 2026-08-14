# MCP client configuration attestation: fresh receipt와 provenance verifier를 분리하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- exact configuration acknowledgement에 deployment-owned one-shot challenge를 묶어 stale receipt를 먼저 막는다.
- receipt의 client-specific provenance 판단을 별도의 trusted verifier seam으로 한 번만 넘긴다.
- challenge/acknowledgement mismatch, malformed verifier, verifier failure를 client I/O 전에 generic error로 끝낸다.
- freshness equality와 authenticated signature, credential, file permission, reload/reconnect health ownership을 분리한다.

## 2. challenge가 authentication을 대체하지 않는다

`McpClientConfigurationAttestationRequest`는 기존 `McpClientConfigurationApplication`과 16–128자의 opaque single-line `attestation_challenge`를 묶습니다. External adapter가 반환하는 `McpClientConfigurationAttestation`은 기존 exact acknowledgement와 challenge echo만 보관합니다.

```text
exact application + fresh challenge ──> separate client-specific adapter
                                           │
exact acknowledgement + challenge echo ───┼─> trusted provenance verifier (one call)
                                           │
                              true only ───┴─> original immutable handoff

mismatch/malformed/false/exception: no client I/O by this model
```

`verify_mcp_client_configuration_attestation()`은 request와 attestation의 challenge가 같고, 기존 client/server/exact Tool tuple/generation acknowledgement가 모두 맞는지 **먼저** 확인합니다. 그 뒤에만 caller가 소유한 `McpClientConfigurationAttestationVerifier.verify()`를 한 번 호출합니다. `True`라는 정확한 bool만 성공으로 인정하며 `1`, 문자열, `None`, `False`, exception은 raw adapter detail 없이 거부합니다.

Challenge는 credential, signature, config file path/content, client session ID가 아닙니다. Challenge equality는 replay 방지에 필요한 freshness correlation model일 뿐 receipt issuer의 identity나 signature 검증을 증명하지 않습니다.

## 3. 좁은 API 계약

- `McpClientConfigurationAttestationRequest(application, attestation_challenge)`는 typed application과 16–128자 one-line challenge만 받는다.
- `McpClientConfigurationAttestation(acknowledgement, attestation_challenge)`은 최소 receipt와 같은 shape의 echo만 받는다.
- `verify_mcp_client_configuration_attestation(request, attestation, verifier)`은 challenge와 exact acknowledgement를 verifier 전에 검증한다.
- verifier는 exactly `True`일 때만 원래 immutable handoff을 반환한다. verifier exception/false/non-bool은 generic error이며 partial handoff을 반환하지 않는다.

이 module은 Hermes Agent/Codex CLI, config file, credential/signature library, subprocess, network, MCP server, Tool 또는 destructive action을 호출하지 않습니다.

## 4. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv run python examples/volume03/mcp_client_configuration_attestation.py
uv run pytest tests/volume03/test_mcp_client_attestation.py -q
```

예상 출력입니다.

```text
client: hermes-agent
server_name: safe-tools
visible_tools: safe_calculator
verifier_calls: 1
```

예제는 fixed in-memory `safe_calculator` visibility, challenge, receipt와 `OfflineReceiptVerifier`만 사용합니다. Hermes/Codex client, configuration file, secret, cryptographic key, Popen, shell, filesystem, network, MCP server, Tool 또는 destructive action은 실행하지 않습니다.

## 5. 검증 경계

`tests/volume03/test_mcp_client_attestation.py`는 다음을 검증합니다.

1. fresh exact attestation만 verifier 한 번 뒤 original immutable handoff을 반환한다.
2. challenge와 acknowledgement mismatch는 verifier 호출 전에 거부된다.
3. `False`, non-bool return, verifier exception은 partial handoff이나 raw adapter detail 없이 거부된다.
4. too-short/newline/oversize challenge와 invalid verifier는 external receipt trust 전에 거부된다.

## 6. production에 그대로 연결하지 않기

이 model은 verifier의 authentication implementation을 제공하거나 adapter provenance를 독립적으로 증명하지 않습니다. Production adapter는 client별 공식 schema와 supported version을 확인하고, authenticated signature/attestation issuer와 key rotation, challenge lifecycle/replay store, credential/secret injection, config file ownership·permission, atomic write/rollback, reload acknowledgement provenance, reconnect/health check, server identity, TLS/STDIO lifecycle, tenant isolation, durable audit/idempotency, metrics/alerts와 operator review를 별도로 구현·검증해야 합니다.

Hermes의 actual MCP 구성과 transport lifecycle은 공식 [Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes)를 따르세요. Client filtering 또는 receipt attestation은 server-side allowlist, JSON Schema validation, approval, durable audit/idempotency, quota를 대체하지 않습니다. Reload/reconnect 뒤 side-effecting Tool을 blind retry하지 말고 receiver acknowledgement와 durable reconciliation record를 확인하세요.

## 7. 완료 체크리스트

- [ ] fresh challenge와 exact receipt mismatch가 verifier 전에 거부되는지 확인했다.
- [ ] verifier가 exact bool `True`만 trusted handoff으로 승격하는지 확인했다.
- [ ] equality/freshness model이 signature·credential·health proof가 아님을 확인했다.
- [ ] example/test가 actual client, config file, credential, process, network, Tool, destructive action 없이 실행됐는지 확인했다.
- [ ] official schema/version, authentication, atomic reload/health, durable operations가 별도 production 검증임을 확인했다.
