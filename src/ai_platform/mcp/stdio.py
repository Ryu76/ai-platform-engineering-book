"""한 줄 JSON-RPC와 좁은 catalog·명시적 Tool call 경계를 검증하는 MCP STDIO adapter.

이 모듈은 실제 ``sys.stdin``/``sys.stdout``를 열지 않는다. 호출자는 입력 줄 하나를
``receive_line()``에 전달하고 반환된 한 줄만 stdout에 쓸 수 있다. Tool 실행은 명시적인
``McpToolCallBoundary``를 전달했을 때에만 기존 dispatcher를 통해 일어난다.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from ai_platform.mcp.catalog import McpServerCatalog
from ai_platform.mcp.dispatcher import McpDispatchError, dispatch_mcp_tool_call
from ai_platform.mcp.prompts import McpPromptCatalog, McpPromptError
from ai_platform.mcp.requests import McpCallRequestError
from ai_platform.mcp.resources import McpResourceCatalog, McpResourceError
from ai_platform.tools.audit import InMemoryToolAuditSink
from ai_platform.tools.authorization import ApprovalGrant, ToolAuthorizationPolicy
from ai_platform.tools.execution import ToolExecutionPolicy
from ai_platform.tools.registry import ToolRegistry, ToolRegistryError, ToolResult

MCP_PROTOCOL_VERSION = "2025-03-26"
DEFAULT_MAX_MESSAGE_BYTES = 16_384
MAX_TOOL_RESULT_TEXT_BYTES = 4_096


class McpStdioError(ValueError):
    """교육용 STDIO JSON-RPC framing 또는 lifecycle 계약이 맞지 않을 때 발생한다."""


class McpStdioState(StrEnum):
    """initialize request와 initialized notification의 순서를 제한한다."""

    WAITING_FOR_INITIALIZE = "waiting_for_initialize"
    WAITING_FOR_INITIALIZED = "waiting_for_initialized"
    READY = "ready"
    CLOSED = "closed"


@dataclass(frozen=True, slots=True)
class McpJsonRpcRequest:
    """한 STDIO line에서 파싱한 JSON-RPC request 또는 notification이다."""

    method: str
    request_id: str | int | None
    params: Mapping[str, object]

    def __post_init__(self) -> None:
        """params snapshot을 고정해 이후 lifecycle 판단이 입력 객체 변경에 흔들리지 않게 한다."""
        object.__setattr__(self, "params", MappingProxyType(deepcopy(dict(self.params))))

    @property
    def is_notification(self) -> bool:
        """ID가 없어서 response를 만들지 않는 JSON-RPC notification인지 반환한다."""
        return self.request_id is None


@dataclass(frozen=True, slots=True)
class McpToolCallBoundary:
    """검토된 Tool 실행 정책을 STDIO transport와 명시적으로 연결하는 설정이다.

    이 경계는 handler나 caller가 보낸 승인·정책을 받지 않는다. 생성 시점에 신뢰된
    host가 구성한 registry, authorization, execution, audit만 사용한다.
    """

    registry: ToolRegistry
    authorization_policy: ToolAuthorizationPolicy
    execution_policy: ToolExecutionPolicy
    audit_sink: InMemoryToolAuditSink
    approval: ApprovalGrant | None = None

    def dispatch(self, request: McpJsonRpcRequest) -> ToolResult:
        """검증된 JSON-RPC params를 기존 parser·dispatcher 경계로 다시 전달한다."""
        if request.request_id is None:
            raise McpStdioError("tools/call must include a JSON-RPC request id")
        try:
            raw_request = json.dumps(
                dict(request.params),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as error:
            raise McpStdioError("tools/call params must be JSON serializable") from error
        return dispatch_mcp_tool_call(
            self.registry,
            request_id=mcp_stdio_request_correlation_id(request.request_id),
            raw_request=raw_request,
            authorization_policy=self.authorization_policy,
            execution_policy=self.execution_policy,
            audit_sink=self.audit_sink,
            approval=self.approval,
        )


class McpStdioSession:
    """고정 lifecycle 뒤 catalog와 명시적으로 연결한 Tool call만 좁게 노출한다.

    ``tools/list``, ``resources/list``, ``prompts/list``은 고정된 catalog snapshot만
    응답한다. ``resources/read``은 exact allowlisted URI의 내장 text snapshot만,
    ``prompts/get``은 exact allowlisted name과 빈 arguments의 고정 message snapshot만
    응답한다. ``tools/call``은 명시적인 ``McpToolCallBoundary``가 있을 때만 기존
    parser·allowlist·승인·timeout/retry·감사 dispatcher로 연결한다. Resource URI는
    catalog lookup key일 뿐 파일 경로 또는 URL로 해석하지 않는다.
    """

    def __init__(
        self,
        *,
        catalog: McpServerCatalog | None = None,
        resource_catalog: McpResourceCatalog | None = None,
        prompt_catalog: McpPromptCatalog | None = None,
        tool_call_boundary: McpToolCallBoundary | None = None,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
    ) -> None:
        _validate_max_message_bytes(max_message_bytes)
        self._max_message_bytes = max_message_bytes
        self._catalog = catalog or McpServerCatalog(())
        self._resource_catalog = resource_catalog or McpResourceCatalog(())
        self._prompt_catalog = prompt_catalog or McpPromptCatalog(())
        self._tool_call_boundary = tool_call_boundary
        self._state = McpStdioState.WAITING_FOR_INITIALIZE

    @property
    def state(self) -> McpStdioState:
        """현재 입력 lifecycle state를 반환한다."""
        return self._state

    def receive_line(self, raw_line: str) -> str | None:
        """한 framed line을 검증하고 lifecycle·catalog·Tool call response를 반환한다."""
        if self._state is McpStdioState.CLOSED:
            raise McpStdioError("STDIO session is closed")

        request = parse_stdio_jsonrpc_line(
            raw_line,
            max_message_bytes=self._max_message_bytes,
        )
        if self._state is McpStdioState.WAITING_FOR_INITIALIZE:
            return self._receive_initialize(request)
        if self._state is McpStdioState.WAITING_FOR_INITIALIZED:
            self._receive_initialized_notification(request)
            return None
        return self._receive_ready_request(request)

    def close(self) -> None:
        """새 input을 거부하도록 session을 닫는다; stdout이나 외부 resource는 건드리지 않는다."""
        self._state = McpStdioState.CLOSED

    def _receive_initialize(self, request: McpJsonRpcRequest) -> str:
        if request.method != "initialize":
            raise McpStdioError("first MCP message must be an initialize request")
        if request.is_notification:
            raise McpStdioError("initialize must include a JSON-RPC request id")
        _validate_initialize_params(request.params)
        self._state = McpStdioState.WAITING_FOR_INITIALIZED
        return encode_stdio_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": request.request_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "serverInfo": {
                        "name": "volume03-stdio-boundary",
                        "version": "0.1.0",
                    },
                },
            },
            max_message_bytes=self._max_message_bytes,
        )

    def _receive_initialized_notification(self, request: McpJsonRpcRequest) -> None:
        if request.method != "notifications/initialized" or not request.is_notification:
            raise McpStdioError("initialize must be followed by notifications/initialized")
        if request.params:
            raise McpStdioError("notifications/initialized must not include params")
        self._state = McpStdioState.READY

    def _receive_ready_request(self, request: McpJsonRpcRequest) -> str:
        """READY에서는 명시적으로 구성한 Tool call과 좁은 snapshot만 허용한다."""
        if request.method not in {
            "tools/list",
            "tools/call",
            "resources/list",
            "resources/read",
            "prompts/list",
            "prompts/get",
        }:
            raise McpStdioError(
                "no MCP methods are enabled besides tools/list, optionally configured "
                "tools/call, resources/list, fixed resources/read, prompts/list, and fixed "
                "prompts/get in this adapter"
            )
        if request.is_notification:
            raise McpStdioError(f"{request.method} must include a JSON-RPC request id")
        if request.method == "tools/call":
            result = self._call_configured_tool(request)
        elif request.method == "resources/read":
            result = self._read_fixed_resource(request.params)
        elif request.method == "prompts/get":
            result = self._get_fixed_prompt(request.params)
        elif request.params:
            raise McpStdioError(f"{request.method} params must be empty when present")
        elif request.method == "tools/list":
            result = {"tools": list(self._catalog.list_tools())}
        elif request.method == "resources/list":
            result = {"resources": list(self._resource_catalog.list_resources())}
        else:
            result = {"prompts": list(self._prompt_catalog.list_prompts())}
        return encode_stdio_jsonrpc_message(
            {
                "jsonrpc": "2.0",
                "id": request.request_id,
                "result": result,
            },
            max_message_bytes=self._max_message_bytes,
        )

    def _call_configured_tool(self, request: McpJsonRpcRequest) -> dict[str, object]:
        """검토된 boundary에서만 Tool을 호출하고 실패 세부정보를 transport에 노출하지 않는다."""
        if self._tool_call_boundary is None:
            raise McpStdioError("tools/call is not enabled without an explicit tool call boundary")
        try:
            result = self._tool_call_boundary.dispatch(request)
            return _mcp_tool_success_result(result)
        except (McpCallRequestError, McpDispatchError, ToolRegistryError, McpStdioError):
            return _mcp_tool_error_result()
        except Exception:
            return _mcp_tool_error_result()

    def _read_fixed_resource(self, params: Mapping[str, object]) -> dict[str, object]:
        """exact URI의 내장 text snapshot만 MCP contents envelope로 반환한다."""
        uri = params.get("uri")
        if not isinstance(uri, str) or not uri.strip():
            raise McpStdioError("resources/read uri must be a non-empty string")
        if set(params) != {"uri"}:
            raise McpStdioError("resources/read params must contain only uri")
        try:
            return {"contents": [self._resource_catalog.read_resource(uri)]}
        except McpResourceError as error:
            raise McpStdioError("resources/read uri is not allowlisted") from error

    def _get_fixed_prompt(self, params: Mapping[str, object]) -> dict[str, object]:
        """보간 없이 exact allowlist name의 정적 Prompt message snapshot만 반환한다."""
        name = params.get("name")
        if not isinstance(name, str) or not name.strip():
            raise McpStdioError("prompts/get name must be a non-empty string")
        if set(params) not in ({"name"}, {"name", "arguments"}):
            raise McpStdioError("prompts/get params must contain only name and optional arguments")
        if "arguments" in params:
            arguments = params["arguments"]
            if not isinstance(arguments, Mapping) or arguments:
                raise McpStdioError(
                    "prompts/get arguments must be an empty JSON object when present"
                )
        try:
            return self._prompt_catalog.get_prompt(name)
        except McpPromptError as error:
            raise McpStdioError("prompts/get name is not allowlisted") from error


def parse_stdio_jsonrpc_line(
    raw_line: str,
    *,
    max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
) -> McpJsonRpcRequest:
    """LF로 끝나는 하나의 UTF-8 JSON-RPC 2.0 object만 파싱한다."""
    _validate_max_message_bytes(max_message_bytes)
    json_text = _extract_single_line_json(raw_line, max_message_bytes=max_message_bytes)
    try:
        payload: object = json.loads(
            json_text,
            object_pairs_hook=_json_object_without_duplicate_keys,
            parse_constant=_reject_non_standard_json_constant,
        )
    except json.JSONDecodeError as error:
        raise McpStdioError("STDIO message must contain valid JSON") from error

    if not isinstance(payload, dict):
        raise McpStdioError("STDIO message must be a JSON object")
    _validate_jsonrpc_keys(payload)

    method = payload["method"]
    if not isinstance(method, str) or not method.strip():
        raise McpStdioError("JSON-RPC method must be a non-empty string")
    request_id = _parse_request_id(payload)
    params = payload.get("params", {})
    if not isinstance(params, dict):
        raise McpStdioError("JSON-RPC params must be a JSON object when present")
    return McpJsonRpcRequest(method=method, request_id=request_id, params=params)


def encode_stdio_jsonrpc_message(
    payload: Mapping[str, object],
    *,
    max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
) -> str:
    """검토된 response object 하나를 compact JSON + LF frame으로 안전하게 인코딩한다."""
    _validate_max_message_bytes(max_message_bytes)
    try:
        raw_line = (
            json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
        )
        raw_line.encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as error:
        raise McpStdioError("STDIO response must be UTF-8 JSON serializable") from error
    _validate_message_size(raw_line, max_message_bytes=max_message_bytes)
    return raw_line


def _extract_single_line_json(raw_line: str, *, max_message_bytes: int) -> str:
    """한 메시지가 여러 line으로 smuggling되지 않도록 LF frame을 엄격하게 분리한다."""
    if not isinstance(raw_line, str):
        raise McpStdioError("STDIO message must be a text line")
    _validate_message_size(raw_line, max_message_bytes=max_message_bytes)
    if not raw_line.endswith("\n"):
        raise McpStdioError("STDIO message must end with one LF")
    json_text = raw_line[:-1]
    if not json_text or "\n" in json_text or "\r" in json_text:
        raise McpStdioError("STDIO message must contain exactly one LF-delimited JSON object")
    return json_text


def _validate_message_size(raw_line: str, *, max_message_bytes: int) -> None:
    """문자 수가 아니라 transport에서 실제 소비하는 UTF-8 byte 수로 상한을 검사한다."""
    try:
        byte_count = len(raw_line.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise McpStdioError("STDIO message must be valid UTF-8 text") from error
    if byte_count > max_message_bytes:
        raise McpStdioError(f"STDIO message exceeds {max_message_bytes} bytes")


def _validate_max_message_bytes(max_message_bytes: int) -> None:
    """작은 response도 담고 의도치 않은 무제한 frame도 피하는 상한을 강제한다."""
    if isinstance(max_message_bytes, bool) or not isinstance(max_message_bytes, int):
        raise McpStdioError("max_message_bytes must be an integer")
    if not 256 <= max_message_bytes <= 65_536:
        raise McpStdioError("max_message_bytes must be between 256 and 65536")


def _json_object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """중복 JSON-RPC key가 앞선 검증된 값을 덮어쓰지 못하게 한다."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise McpStdioError(f"JSON-RPC message contains duplicate key: {key}")
        result[key] = value
    return result


def _reject_non_standard_json_constant(value: str) -> object:
    """NaN과 Infinity처럼 JSON 표준 밖인 숫자 상수를 거부한다."""
    raise McpStdioError(f"JSON-RPC constant is not allowed: {value}")


def _validate_jsonrpc_keys(payload: Mapping[str, object]) -> None:
    """이 교육용 adapter가 request/notification envelope 외 필드를 받지 않게 한다."""
    expected = {"jsonrpc", "id", "method", "params"}
    unexpected = sorted(set(payload) - expected)
    if unexpected:
        raise McpStdioError(f"JSON-RPC message has unexpected key: {unexpected[0]}")
    required = {"jsonrpc", "method"}
    missing = sorted(required - set(payload))
    if missing:
        raise McpStdioError(f"JSON-RPC message is missing key: {missing[0]}")
    if payload["jsonrpc"] != "2.0":
        raise McpStdioError("JSON-RPC version must be exactly 2.0")


def _parse_request_id(payload: Mapping[str, object]) -> str | int | None:
    """null, boolean, float·제어 문자가 든 ID를 거부해 correlation을 명확히 구분한다."""
    if "id" not in payload:
        return None
    request_id = payload["id"]
    _validate_stdio_request_id(request_id)
    return cast("str | int", request_id)


def _validate_initialize_params(params: Mapping[str, object]) -> None:
    """고정 MCP protocol version과 최소 client envelope를 검증한다."""
    expected = {"protocolVersion", "capabilities", "clientInfo"}
    missing = sorted(expected - set(params))
    if missing:
        raise McpStdioError(f"initialize params is missing key: {missing[0]}")
    unexpected = sorted(set(params) - expected)
    if unexpected:
        raise McpStdioError(f"initialize params has unexpected key: {unexpected[0]}")
    if params["protocolVersion"] != MCP_PROTOCOL_VERSION:
        raise McpStdioError(f"unsupported MCP protocol version: {params['protocolVersion']!r}")
    if not isinstance(params["capabilities"], Mapping):
        raise McpStdioError("initialize capabilities must be a JSON object")
    client_info = params["clientInfo"]
    if not isinstance(client_info, Mapping):
        raise McpStdioError("initialize clientInfo must be a JSON object")
    if set(client_info) != {"name", "version"}:
        raise McpStdioError("initialize clientInfo must contain only name and version")
    if not all(
        isinstance(client_info[key], str) and client_info[key].strip() for key in client_info
    ):
        raise McpStdioError("initialize clientInfo name and version must be non-empty strings")


def mcp_stdio_request_correlation_id(request_id: str | int) -> str:
    """신뢰된 host가 승인과 audit에 쓸 typed JSON-RPC correlation ID를 만든다.

    JSON-RPC string ID ``"7"``과 integer ID ``7``은 서로 다른 Tool request다. 승인
    workflow는 이 함수를 통해 dispatcher와 같은 request binding 값을 사용해야 한다.
    """
    _validate_stdio_request_id(request_id)
    if isinstance(request_id, str):
        return f"mcp-stdio:string:{request_id}"
    return f"mcp-stdio:integer:{request_id}"


def _validate_stdio_request_id(request_id: object) -> None:
    """허용되는 JSON-RPC ID가 audit/approval log framing을 깨지 않게 제한한다."""
    if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
        raise McpStdioError("JSON-RPC id must be a string or integer when present")
    if isinstance(request_id, str):
        if not request_id.strip():
            raise McpStdioError("JSON-RPC string id must not be empty")
        if any(ord(character) < 32 or ord(character) == 127 for character in request_id):
            raise McpStdioError("JSON-RPC string id must not contain control characters")


def _mcp_tool_success_result(result: ToolResult) -> dict[str, object]:
    """작고 JSON인 Tool output만 표준 text content snapshot으로 투영한다."""
    try:
        text = json.dumps(
            dict(result.output),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        byte_count = len(text.encode("utf-8"))
    except (TypeError, UnicodeEncodeError, ValueError):
        return _mcp_tool_error_result()
    if byte_count > MAX_TOOL_RESULT_TEXT_BYTES:
        return _mcp_tool_error_result()
    return {"content": [{"type": "text", "text": text}], "isError": False}


def _mcp_tool_error_result() -> dict[str, object]:
    """거부·실패 원인, 인자, handler 예외를 노출하지 않는 고정 MCP Tool result다."""
    return {
        "content": [{"type": "text", "text": "Tool request was denied or failed."}],
        "isError": True,
    }
