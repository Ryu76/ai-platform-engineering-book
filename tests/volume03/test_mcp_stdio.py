"""Volume 03의 좁은 MCP STDIO JSON-RPC framing·lifecycle 경계를 검사한다."""
from __future__ import annotations

import json
from collections.abc import Mapping

import pytest

from ai_platform.mcp.catalog import McpServerCatalog, McpToolDefinition
from ai_platform.mcp.prompts import McpPromptCatalog, McpPromptMessage, McpStaticPrompt
from ai_platform.mcp.resources import McpResourceCatalog, McpStaticResource
from ai_platform.mcp.stdio import (
    MCP_PROTOCOL_VERSION,
    McpStdioError,
    McpStdioSession,
    McpStdioState,
    McpToolCallBoundary,
    encode_stdio_jsonrpc_message,
    mcp_stdio_request_correlation_id,
    parse_stdio_jsonrpc_line,
)
from ai_platform.tools.audit import InMemoryToolAuditSink, ToolAuditOutcome
from ai_platform.tools.authorization import ApprovalGrant, ToolAuthorizationPolicy, ToolRisk
from ai_platform.tools.execution import ToolExecutionPolicy
from ai_platform.tools.registry import SAFE_TEXT_CASE, ToolRegistry, ToolSpec


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


def _ready_session(*, tool_call_boundary: McpToolCallBoundary | None = None) -> McpStdioSession:
    session = McpStdioSession(tool_call_boundary=tool_call_boundary)
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    return session


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


def test_stdio_session_reads_fixed_allowlisted_resource_without_uri_resolution() -> None:
    resource_catalog = McpResourceCatalog(
        (
            McpStaticResource(
                uri="ai-platform://volume03/transport-boundary",
                name="Transport boundary note",
                mime_type="text/plain",
                text="Reading this resource does not read a file or execute a Tool.",
            ),
        )
    )
    session = McpStdioSession(resource_catalog=resource_catalog)
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"resource-001","method":"resources/read",'
        '"params":{"uri":"ai-platform://volume03/transport-boundary"}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line) == {
        "jsonrpc": "2.0",
        "id": "resource-001",
        "result": {
            "contents": [
                {
                    "uri": "ai-platform://volume03/transport-boundary",
                    "mimeType": "text/plain",
                    "text": "Reading this resource does not read a file or execute a Tool.",
                }
            ]
        },
    }
    assert session.state is McpStdioState.READY


@pytest.mark.parametrize(
    ("raw_line", "message"),
    (
        (
            '{"jsonrpc":"2.0","method":"resources/read",'
            '"params":{"uri":"ai-platform://volume03/transport-boundary"}}\n',
            "must include",
        ),
        (
            '{"jsonrpc":"2.0","id":"resource-002","method":"resources/read",'
            '"params":{}}\n',
            "uri must be",
        ),
        (
            '{"jsonrpc":"2.0","id":"resource-003","method":"resources/read",'
            '"params":{"uri":"ai-platform://volume03/transport-boundary/"}}\n',
            "not allowlisted",
        ),
        (
            '{"jsonrpc":"2.0","id":"resource-004","method":"resources/read",'
            '"params":{"uri":"file:///etc/passwd"}}\n',
            "not allowlisted",
        ),
        (
            '{"jsonrpc":"2.0","id":"resource-005","method":"resources/read",'
            '"params":{"uri":"ai-platform://volume03/transport-boundary","extra":true}}\n',
            "contain only uri",
        ),
    ),
)
def test_stdio_session_rejects_ambiguous_or_non_allowlisted_resource_read(
    raw_line: str, message: str
) -> None:
    session = McpStdioSession(
        resource_catalog=McpResourceCatalog(
            (
                McpStaticResource(
                    uri="ai-platform://volume03/transport-boundary",
                    name="Transport boundary note",
                    mime_type="text/plain",
                    text="Fixed text.",
                ),
            )
        )
    )
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    with pytest.raises(McpStdioError, match=message):
        session.receive_line(raw_line)


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


def test_stdio_session_projects_allowlisted_pure_tool_call_through_dispatcher() -> None:
    sink = InMemoryToolAuditSink()
    session = _ready_session(
        tool_call_boundary=McpToolCallBoundary(
            registry=ToolRegistry((SAFE_TEXT_CASE,)),
            authorization_policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.LOW}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
            audit_sink=sink,
        )
    )

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"call-001","method":"tools/call","params":'
        '{"name":"safe_text_case","arguments":{"text":"Mcp","operation":"upper"}}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line) == {
        "jsonrpc": "2.0",
        "id": "call-001",
        "result": {
            "content": [{"type": "text", "text": '{"text":"MCP"}'}],
            "isError": False,
        },
    }
    assert sink.events[0].request_id == "mcp-stdio:string:call-001"
    assert sink.events[0].outcome is ToolAuditOutcome.SUCCEEDED
    assert session.state is McpStdioState.READY


def test_stdio_session_runs_high_risk_pure_tool_only_with_typed_rpc_id_bound_approval() -> None:
    sink = InMemoryToolAuditSink()
    arguments = {"text": "Mcp", "operation": "upper"}
    session = _ready_session(
        tool_call_boundary=McpToolCallBoundary(
            registry=ToolRegistry((SAFE_TEXT_CASE,)),
            authorization_policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.HIGH}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
            audit_sink=sink,
            approval=ApprovalGrant.for_request(
                approval_id="approval-stdio-001",
                request_id=mcp_stdio_request_correlation_id("high-risk-001"),
                tool_name="safe_text_case",
                arguments=arguments,
            ),
        )
    )

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"high-risk-001","method":"tools/call","params":'
        '{"name":"safe_text_case","arguments":{"text":"Mcp","operation":"upper"}}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line)["result"]["isError"] is False
    assert sink.events[0].request_id == "mcp-stdio:string:high-risk-001"
    assert sink.events[0].approval_id == "approval-stdio-001"
    assert sink.events[0].outcome is ToolAuditOutcome.SUCCEEDED


def test_stdio_session_rejects_high_risk_approval_bound_to_same_looking_other_id_type() -> None:
    sink = InMemoryToolAuditSink()
    arguments = {"text": "Mcp", "operation": "upper"}
    session = _ready_session(
        tool_call_boundary=McpToolCallBoundary(
            registry=ToolRegistry((SAFE_TEXT_CASE,)),
            authorization_policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.HIGH}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
            audit_sink=sink,
            approval=ApprovalGrant.for_request(
                approval_id="approval-integer-7",
                request_id=mcp_stdio_request_correlation_id(7),
                tool_name="safe_text_case",
                arguments=arguments,
            ),
        )
    )

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"7","method":"tools/call","params":'
        '{"name":"safe_text_case","arguments":{"text":"Mcp","operation":"upper"}}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line)["result"]["isError"] is True
    assert sink.events[0].request_id == "mcp-stdio:string:7"
    assert sink.events[0].outcome is ToolAuditOutcome.DENIED


@pytest.mark.parametrize("request_id", (True, 1.5, "", "\nlog-forgery"))
def test_stdio_request_correlation_id_rejects_non_canonical_jsonrpc_ids(request_id: object) -> None:
    with pytest.raises(McpStdioError, match="JSON-RPC"):
        mcp_stdio_request_correlation_id(request_id)  # type: ignore[arg-type]


def test_stdio_session_keeps_tool_calls_disabled_without_explicit_boundary() -> None:
    session = _ready_session()

    with pytest.raises(McpStdioError, match="not enabled without an explicit"):
        session.receive_line(
            '{"jsonrpc":"2.0","id":"call-001","method":"tools/call","params":{}}\n'
        )


def test_stdio_session_returns_fixed_error_for_invalid_tool_request_without_audit() -> None:
    sink = InMemoryToolAuditSink()
    session = _ready_session(
        tool_call_boundary=McpToolCallBoundary(
            registry=ToolRegistry((SAFE_TEXT_CASE,)),
            authorization_policy=ToolAuthorizationPolicy({"safe_text_case": ToolRisk.LOW}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
            audit_sink=sink,
        )
    )

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":'
        '{"name":"not_allowlisted","arguments":{"text":"secret","operation":"upper"}}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line)["result"] == {
        "content": [{"type": "text", "text": "Tool request was denied or failed."}],
        "isError": True,
    }
    assert sink.events == ()


def test_stdio_session_hides_handler_error_and_audits_failed_pure_tool_call() -> None:
    def failing_handler(_: Mapping[str, object]) -> Mapping[str, object]:
        raise RuntimeError("test-only handler detail must not cross the transport boundary")

    sink = InMemoryToolAuditSink()
    session = _ready_session(
        tool_call_boundary=McpToolCallBoundary(
            registry=ToolRegistry(
                (
                    ToolSpec(
                        "failing_text",
                        "Fails without touching an external system.",
                        SAFE_TEXT_CASE.input_schema,
                        failing_handler,
                    ),
                )
            ),
            authorization_policy=ToolAuthorizationPolicy({"failing_text": ToolRisk.LOW}),
            execution_policy=ToolExecutionPolicy(timeout_seconds=0.5),
            audit_sink=sink,
        )
    )

    response_line = session.receive_line(
        '{"jsonrpc":"2.0","id":"call-failure","method":"tools/call","params":'
        '{"name":"failing_text","arguments":{"text":"safe","operation":"upper"}}}\n'
    )

    assert response_line is not None
    assert json.loads(response_line)["result"] == {
        "content": [{"type": "text", "text": "Tool request was denied or failed."}],
        "isError": True,
    }
    assert sink.events[0].outcome is ToolAuditOutcome.FAILED
    assert "safe" not in str(sink.events[0])


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
            '{"jsonrpc":"2.0","id":"call-001","method":"tools/call","params":{}}\n',
            "not enabled without an explicit",
        ),
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



def test_stdio_session_rejects_tool_calls_without_explicit_boundary() -> None:
    session = McpStdioSession()
    session.receive_line(_initialize_line())
    session.receive_line('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')

    with pytest.raises(McpStdioError, match="not enabled without an explicit"):
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
