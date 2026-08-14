# MCP STDIO 두 Output: fake stream을 공정하게 bounded drain하기

`stdout`과 `stderr`를 순서대로 전부 읽으면 첫 stream이 계속 데이터를 제공할 때 다른 stream이
기아 상태가 될 수 있습니다. 그러나 이 문제를 해결한다는 이유로 Tool 실행, 실제 `Popen`, thread,
async runtime 또는 child signal까지 한 함수에 결합하면 출력 수집의 실패 소유권이 흐려집니다.

이 장은 **trusted host가 이미 가진 두 fake binary stream**만 받아, 아직 EOF가 아닌 각 stream을
한 turn씩 교대하는 작은 모델을 만듭니다. 실제 OS pipe에서 block 없이 읽는 concurrent adapter는
아직 만들지 않습니다.

## 계약

`drain_mcp_stdio_stream_pair_fairly()`는 다음만 수행합니다.

- `stdout_stream`과 `stderr_stream`은 서로 다른 `read(size) -> bytes` object여야 합니다.
- stdout부터 시작해, EOF가 아닌 각 stream에 round마다 정확히 한 번만 read를 요청합니다.
- 각 stream은 독립적인 1,024–1,048,576 byte ceiling을 갖습니다. 각 요청은 최대 4 KiB이자
  남은 ceiling보다 한 byte 큰 overflow sentinel까지만 요청합니다.
- 두 stream이 모두 EOF를 반환한 경우에만 immutable raw-byte pair snapshot을 반환합니다.
- 한 read failure, non-bytes 값, requested size 초과, ceiling overflow가 발생하면 partial output을
  반환하지 않고 즉시 generic error로 끝냅니다. 그 뒤 다른 stream도 더 읽지 않습니다.

이 모델은 scheduler ordering을 검증할 수 있게 하지만, synchronous `read()` 자체가 OS pipe에서
block하지 않는다는 보장은 제공하지 않습니다. 실제 child pipe에는 selector/thread/async와
backpressure 및 shutdown ownership을 명시한 별도 adapter가 필요합니다.

## 안전한 예제

```bash
uv run python examples/volume03/mcp_stdio_fair_stream_pair_drain.py
```

예상 출력:

```text
stdout_bytes: 10
stderr_bytes: 10
turns: stdout,stderr,stdout,stderr,stdout,stderr
```

예제는 메모리의 fixed byte chunk만 사용합니다. shell, subprocess, OS pipe, filesystem, network,
외부 MCP server, Tool 호출과 destructive action을 수행하지 않습니다.

## 검증 포인트

`tests/volume03/test_mcp_fair_drain.py`는 다음을 검증합니다.

1. 두 unfinished stream의 round-robin turn 순서와 EOF 뒤 skip을 확인합니다.
2. stdout overflow 뒤 stderr를 더 읽지 않고 partial capture도 돌려주지 않음을 확인합니다.
3. stderr read failure의 raw adapter detail이 error message에 섞이지 않고 다음 stdout turn도 없음을 확인합니다.
4. oversized 반환, invalid stream, 같은 object 재사용, invalid budget을 read 전에 거부함을 확인합니다.

## 의도적 비범위

이 장은 UTF-8/JSON decode, redaction/logging, stdin write/framing, cancellation/disconnect,
child shutdown, process group/signal, real concurrent pipe IO, exit-code restart/backoff,
durable audit/idempotency 또는 Hermes/Codex integration을 구현하지 않습니다. 특히 이 fake
round-robin model을 실제 subprocess deadlock 방지책으로 사용해서는 안 됩니다.
