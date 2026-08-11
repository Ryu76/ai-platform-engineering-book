"""Volume 03의 좁은 MCP STDIO JSON-RPC framing·lifecycle 경계를 검사한다."""
from __future__ import annotations

import json

import pytest

from ai_platform.mcp.catalog import McpServerCatalog, McpToolDefinition
from ai_platform.mcp.prompts import McpPromptCatalog, McpPromptMessage, McpStaticPrompt
from ai_platform.mcp.resources import McpResourceCatalog, McpStaticResource
from ai_platform.mcp.stdio import (
    MCP_PROTOCOL_VERSION,
    McpStdioError,
    McpStdioSession,
    McpStdioState,
    encode_stdio_jsonrpc_message,
    parse_stdio_jsonrpc_line,
)


def _initialize_line(*, request_id: str = "initialize-001") -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        }
    ) + "\n"


def test_stdio_session_requires_initialize_then_notification_and_emits_response() -> None:
    session = McpStdioSession()

    response_line = session.receive_line(_initialize_line())

    assert response_line is not None
    assert response_line.endswith("\n")
    response = json.loads(response_line)
    assert response == {
        "jsonrpc": "2.0",
        "id": "initialize-001",
        "result": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "serverInfo": {"name": "volume03-stdio-boundary", "version": "0.1.0"},
        },
    }
    assert session.state is McpStdioState.WAITING_FOR_INITIALIZED

    assert session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n') is None
    assert session.state is McpStdioState.READY


def test_stdio_session_projects_fixed_catalog_with_read_only_tools_list() -> None:
    catalog = McpServerCatalog(
        (
            McpToolDefinition(
                name="safe_echo",
                description="Returns text without accessing an external system.",
                input_schema={"type": "object", "properties": {}},
            ),
        )
    )
    session = McpStdioSession(catalog=catalog)
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"list-001","method":"tools/list","params":{}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line) == {
        "jsonrpc": "2.0",
        "id": "list-001",
        "result": {
            "tools": [
                {
                    "name": "safe_echo",
                    "description": "Returns text without accessing an external system.",
                    "inputSchema": {"type": "object", "properties": {}},
                }
            ]
        },
    }
    assert session.state is McpStdioState.READY


def test_stdio_session_projects_fixed_catalog_with_read_only_resources_list() -> None:
    resource_catalog = McpResourceCatalog(
        (
            McpStaticResource(
                uri="ai-platform://volume03/transport-boundary",
                name="Transport boundary note",
                mime_type="text/plain",
                text="Listing a resource does not read a file or execute a Tool.",
            ),
        )
    )
    session = McpStdioSession(resource_catalog=resource_catalog)
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"resources-001","method":"resources/list","params":{}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line) == {
        "jsonrpc": "2.0",
        "id": "resources-001",
        "result": {
            "resources": [
                {
                    "uri": "ai-platform://volume03/transport-boundary",
                    "name": "Transport boundary note",
                    "mimeType": "text/plain",
                }
            ]
        },
    }
    assert session.state is McpStdioState.READY


def test_stdio_session_projects_fixed_catalog_with_read_only_prompts_list() -> None:
    prompt_catalog = McpPromptCatalog(
        (
            McpStaticPrompt(
                name="review-tool-boundary",
                description="Reviews the fixed Tool Calling safety boundary.",
                messages=(
                    McpPromptMessage(
                        role="system",
                        content="Review allowlist and approval boundaries without executing Tools.",
                    ),
                ),
            ),
        )
    )
    session = McpStdioSession(prompt_catalog=prompt_catalog)
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"prompts-001","method":"prompts/list","params":{}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line) == {
        "jsonrpc": "2.0",
        "id": "prompts-001",
        "result": {
            "prompts": [
                {
                    "name": "review-tool-boundary",
                    "description": "Reviews the fixed Tool Calling safety boundary.",
                }
            ]
        },
    }
    assert session.state is McpStdioState.READY


def test_stdio_session_returns_fixed_allowlisted_prompt_without_rendering() -> None:
    prompt_catalog = McpPromptCatalog(
        (
            McpStaticPrompt(
                name="review-tool-boundary",
                description="Reviews the fixed Tool Calling safety boundary.",
                messages=(
                    McpPromptMessage(
                        role="system",
                        content="Review allowlist and approval boundaries without executing Tools.",
                    ),
                ),
            ),
        )
    )
    session = McpStdioSession(prompt_catalog=prompt_catalog)
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"prompt-001","method":"prompts/get",'
        '"params":{"name":"review-tool-boundary","arguments":{}}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line) == {
        "jsonrpc": "2.0",
        "id": "prompt-001",
        "result": {
            "name": "review-tool-boundary",
            "description": "Reviews the fixed Tool Calling safety boundary.",
            "messages": [
                {
                    "role": "system",
                    "content": "Review allowlist and approval boundaries without executing Tools.",
                }
            ],
        },
    }
    assert session.state is McpStdioState.READY


@pytest.mark.parametrize(
    ("raw_line", "message"),
    (
        (
            '{"jsonrpc":"2.0","method":"prompts/get",'
            '"params":{"name":"review-tool-boundary"}}\n',
            "must include",
        ),
        (
            '{"jsonrpc":"2.0","id":"prompt-002","method":"prompts/get",'
            '"params":{}}\n',
            "name must be",
        ),
        (
            '{"jsonrpc":"2.0","id":"prompt-003","method":"prompts/get",'
            '"params":{"name":"review-tool-boundary",'
            '"arguments":{"unreviewed":"input"}}}\n',
            "arguments must be an empty",
        ),
        (
            '{"jsonrpc":"2.0","id":"prompt-003b","method":"prompts/get",'
            '"params":{"name":"review-tool-boundary","arguments":"not-an-object"}}\n',
            "arguments must be an empty",
        ),
        (
            '{"jsonrpc":"2.0","id":"prompt-004","method":"prompts/get",'
            '"params":{"name":"review-tool-boundary","extra":true}}\n',
            "contain only name",
        ),
        (
            '{"jsonrpc":"2.0","id":"prompt-005","method":"prompts/get",'
            '"params":{"name":"review-tool-boundary "}}\n',
            "not allowlisted",
        ),
    ),
)
def test_stdio_session_rejects_ambiguous_or_non_allowlisted_prompt_get(
    raw_line: str, message: str
) -> None:
    session = McpStdioSession(
        prompt_catalog=McpPromptCatalog(
            (
                McpStaticPrompt(
                    name="review-tool-boundary",
                    description="Fixed prompt.",
                    messages=(McpPromptMessage(role="system", content="Fixed message."),),
                ),
            )
        )
    )
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    with pytest.raises(McpStdioError, match=message):
        session.receive_line(raw_line)


@pytest.mark.parametrize(
    ("raw_line", "message"),
    (
        ('{"jsonrpc":"2.0","method":"tools/list"}\n', "tools/list must include"),
        (
            '{"jsonrpc":"2.0","id":"list-002","method":"tools/list",'
            '"params":{"cursor":"unexpected"}}\n',
            "tools/list params must be empty",
        ),
        ('{"jsonrpc":"2.0","method":"resources/list"}\n', "resources/list must include"),
        (
            '{"jsonrpc":"2.0","id":"resources-002","method":"resources/list",'
            '"params":{"cursor":"unexpected"}}\n',
            "resources/list params must be empty",
        ),
        ('{"jsonrpc":"2.0","method":"prompts/list"}\n', "prompts/list must include"),
        (
            '{"jsonrpc":"2.0","id":"prompts-002","method":"prompts/list",'
            '"params":{"cursor":"unexpected"}}\n',
            "prompts/list params must be empty",
        ),
        (
            '{"jsonrpc":"2.0","id":"read-001","method":"resources/read","params":{}}\n',
            "no MCP methods",
        ),
        ('{"jsonrpc":"2.0","id":"call-001","method":"tools/call","params":{}}\n', "no MCP methods"),
        (
            '{"jsonrpc":"2.0","id":"unknown-001","method":"unknown/method",'
            '"params":{}}\n',
            "no MCP methods",
        ),
    ),
)
def test_stdio_session_rejects_non_read_only_or_ambiguous_ready_methods(
    raw_line: str, message: str
) -> None:
    session = McpStdioSession()
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    with pytest.raises(McpStdioError, match=message):
        session.receive_line(raw_line)



def test_stdio_session_never_dispatches_tool_methods_after_handshake() -> None:
    session = McpStdioSession()
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    with pytest.raises(McpStdioError, match="no MCP methods are enabled"):
        session.receive_line(
            '{"jsonrpc":"2.0","id":"call-001","method":"tools/call","params":{}}\n'
        )


def test_stdio_rejects_out_of_order_messages_without_producing_a_response() -> None:
    session = McpStdioSession()

    with pytest.raises(McpStdioError, match="first MCP message must be an initialize request"):
        session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    assert session.state is McpStdioState.WAITING_FOR_INITIALIZE


@pytest.mark.parametrize(
    ("raw_line", "message"),
    (
        ('{"jsonrpc":"2.0","method":"initialize"}', "end with one LF"),
        ('{"jsonrpc":"2.0","method":"initialize"}\r\n', "exactly one LF-delimited"),
        (
            '{"jsonrpc":"2.0","method":"initialize"}\n'
            '{"jsonrpc":"2.0","method":"initialize"}\n',
            "exactly one LF-delimited",
        ),
        ('{"jsonrpc":"2.0","method":"one","method":"two"}\n', "duplicate key"),
        ('{"jsonrpc":"1.0","method":"initialize"}\n', "version must be exactly 2.0"),
        ('{"jsonrpc":"2.0","id":null,"method":"initialize"}\n', "id must be a string or integer"),
        ('{"jsonrpc":"2.0","method":"initialize","extra":true}\n', "unexpected key"),
    ),
)
def test_stdio_parser_rejects_ambiguous_or_invalid_envelopes(raw_line: str, message: str) -> None:
    with pytest.raises(McpStdioError, match=message):
        parse_stdio_jsonrpc_line(raw_line)


def test_stdio_limits_actual_utf8_bytes_for_input_and_output() -> None:
    unicode_line = '{"jsonrpc":"2.0","method":"가"}\n'

    with pytest.raises(McpStdioError, match="exceeds 256 bytes"):
        parse_stdio_jsonrpc_line(unicode_line * 20, max_message_bytes=256)
    with pytest.raises(McpStdioError, match="exceeds 256 bytes"):
        encode_stdio_jsonrpc_message({"result": "가" * 100}, max_message_bytes=256)


def test_initialize_rejects_unknown_protocol_and_never_advances_lifecycle() -> None:
    session = McpStdioSession()
    raw_line = _initialize_line().replace(MCP_PROTOCOL_VERSION, "2099-01-01")

    with pytest.raises(McpStdioError, match="unsupported MCP protocol version"):
        session.receive_line(raw_line)

    assert session.state is McpStdioState.WAITING_FOR_INITIALIZE


def test_closed_stdio_session_rejects_new_input() -> None:
    session = McpStdioSession()
    session.close()

    with pytest.raises(McpStdioError, match="session is closed"):
        session.receive_line(_initialize_line())
