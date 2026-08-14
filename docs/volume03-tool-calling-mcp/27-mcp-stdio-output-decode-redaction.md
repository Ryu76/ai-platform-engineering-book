# MCP STDIO output decode/redaction: 성공한 raw snapshot만 strict text로 바꾸기

## 1. 왜 drain 다음에 별도 decode 경계가 필요한가

bounded drain은 raw `bytes`를 EOF까지 수집하는 책임만 가집니다. 그 bytes가 valid UTF-8인지,
출력에 review된 secret literal이 있는지, 어느 logging backend에 기록할지는 다른 문제입니다.
둘을 pipe reader나 child shutdown에 섞으면 decode failure 뒤 partial output·shutdown·logging의
책임이 흐려집니다.

이 장의 `decode_and_redact_mcp_stdio_output()`은 이미 성공한 immutable
`McpStdioStreamPairCapture`와 trusted deployment의 immutable
`McpStdioOutputRedactionPolicy`만 받습니다. subprocess, pipe, selector, shell, filesystem,
network, external MCP server, Tool 또는 destructive action을 수행하지 않습니다.

```text
bounded EOF raw capture ──> strict UTF-8 decode ──> fixed literal redaction ──> text snapshot
     (previous boundary)          │                         │
                                  └── invalid bytes: generic failure, no partial text
```

## 2. 좁은 계약

- capture의 `stdout`은 `channel="stdout"`, `stderr`는 `channel="stderr"`인 bytes snapshot이어야
  합니다. swapped/malformed capture는 decode 전에 거부합니다.
- 모든 channel은 `errors="strict"` UTF-8로 decode합니다. invalid UTF-8에는 raw bytes나 decoder
  offset을 외부 error에 넣지 않고 partial text를 반환하지 않습니다.
- policy는 deployment에서 review한 최대 16개의 non-empty `str` literal tuple입니다. request,
  model output, MCP output이 literal이나 callback을 주입할 수 없습니다.
- literal은 256 character 이하이며 NUL/LF/CR 및 duplicate를 허용하지 않습니다. 긴 literal부터
  deterministic하게 `[REDACTED]`로 모두 치환하여 overlap에서 짧은 token이 긴 값을 먼저
  훼손하지 않게 합니다.
- 이 결과는 process-local immutable text snapshot일 뿐입니다. log emission, raw-output retention,
  JSON-RPC parse/framing, retry, child shutdown과 restart는 이 함수가 소유하지 않습니다.

## 3. 안전한 오프라인 실습

저장소 루트에서 실행합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
python examples/volume03/mcp_stdio_output_decode_redaction.py
pytest tests/volume03/test_mcp_output_decode.py -q
```

예상 출력입니다.

```text
stdout: result=ok; token=[REDACTED]
stderr: diagnostic=[REDACTED]
```

예제는 source에 고정한 in-memory bytes와 literal만 사용합니다. `demo-secret`은 실제 credential이
아닌 교육용 문자열입니다. executable, subprocess, OS pipe, shell, selector, filesystem, network,
MCP server, Tool 및 destructive action은 실행하지 않습니다.

## 4. 검증 경계

`tests/volume03/test_mcp_output_decode.py`는 다음을 offline fake data로 검증합니다.

1. stdout/stderr 모두 strict UTF-8 decode 뒤 fixed literal redaction이 적용된다.
2. overlap literal은 긴 값부터 mask되어 `abc123`이 `abc`의 partial mask가 되지 않는다.
3. empty trusted policy는 decoded text를 바꾸지 않는다.
4. stdout 또는 stderr의 invalid UTF-8은 generic channel error로 실패하며 raw token/byte detail을
   누출하지 않는다.
5. mutable list, empty/duplicate/line-break/oversize literal, 16개 초과 policy, invalid policy,
   swapped/non-bytes capture는 external I/O 전에 거부된다.

## 5. 운영 adapter로 잘못 확장하지 않기

literal redaction은 complete DLP, credential detection, tenant-aware observability 또는 durable audit가
아닙니다. 실제 운영 경로는 structured event schema, approved retention/access policy, redaction
coverage measurement 및 sink failure policy를 별도 설계해야 합니다. secret이 process command line,
environment, binary/protocol field, split chunk에 있을 수 있다는 점도 이 교육용 text boundary가
해결하지 않습니다.

다음 slice에서는 stdin JSON-RPC framing과 bounded partial write/flush ownership을 drain/decode와
분리하고, cancellation/disconnect, Windows/POSIX process group, exit-code restart/backoff, durable
approval/audit/idempotency, Hermes/Codex integration을 계속 별도 경계로 검증해야 합니다.
