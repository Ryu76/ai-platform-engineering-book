"""MCP STDIO output decode/redaction이 memory snapshot만 처리함을 확인한다."""
from __future__ import annotations

from ai_platform.mcp.fair_drain import McpStdioStreamPairCapture
from ai_platform.mcp.output_decode import (
    McpStdioOutputRedactionPolicy,
    decode_and_redact_mcp_stdio_output,
)
from ai_platform.mcp.stream_drain import McpStdioStreamCapture


def main() -> None:
    """fixed raw bytes를 strict decode/redact하며 process나 Tool을 실행하지 않는다."""
    capture = McpStdioStreamPairCapture(
        stdout=McpStdioStreamCapture(channel="stdout", data=b"result=ok; token=demo-secret"),
        stderr=McpStdioStreamCapture(channel="stderr", data=b"diagnostic=demo-secret"),
    )
    output = decode_and_redact_mcp_stdio_output(
        capture, McpStdioOutputRedactionPolicy(literals=("demo-secret",))
    )

    print(f"stdout: {output.stdout}")
    print(f"stderr: {output.stderr}")


if __name__ == "__main__":
    main()
