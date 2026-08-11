"""한 줄 JSON-RPC와 read-only catalog 목록만 검증하는 MCP STDIO adapter.

이 모듈은 실제 ``sys.stdin``/``sys.stdout``를 열거나 Tool을 실행하지 않는다. 호출자는
입력 줄 하나를 ``receive_line()``에 전달하고, 반환된 한 줄만 stdout에 쓸 수 있다.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from ai_platform.mcp.catalog import McpServerCatalog
from ai_platform.mcp.prompts import McpPromptCatalog
from ai_platform.mcp.resources import McpResourceCatalog

MCP_PROTOCOL_VERSION = "2025-03-26"
DEFAULT_MAX_MESSAGE_BYTES = 16_384


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


class McpStdioSession:
    """고정 lifecycle 뒤 catalog를 read-only 목록 method로만 노출한다.

    ``tools/list``, ``resources/list``, ``prompts/list``은 고정된 catalog snapshot만
    응답한다. ``tools/call``, ``resources/read``, ``prompts/get``을 포함한 다른 모든
    method는 dispatcher, loader, prompt renderer에 전달하지 않으므로 transport metadata가
    Tool 실행 인자나 승인 입력으로 섞이거나 URI가 파일 경로로 해석될 수 없다.
    """

    def __init__(
        self,
        *,
        catalog: McpServerCatalog | None = None,
        resource_catalog: McpResourceCatalog | None = None,
        prompt_catalog: McpPromptCatalog | None = None,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
    ) -> None:
        _validate_max_message_bytes(max_message_bytes)
        self._max_message_bytes = max_message_bytes
        self._catalog = catalog or McpServerCatalog(())
        self._resource_catalog = resource_catalog or McpResourceCatalog(())
        self._prompt_catalog = prompt_catalog or McpPromptCatalog(())
        self._state = McpStdioState.WAITING_FOR_INITIALIZE

    @property
    def state(self) -> McpStdioState:
        """현재 입력 lifecycle state를 반환한다."""
        return self._state

    def receive_line(self, raw_line: str) -> str | None:
        """한 framed line을 검증하고 initialize 또는 read-only catalog response를 반환한다."""
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
        """READY에서는 execution-free catalog list request만 허용한다."""
        if request.method not in {"tools/list", "resources/list", "prompts/list"}:
            raise McpStdioError(
                "no MCP methods are enabled besides read-only tools/list, resources/list, "
                "and prompts/list in this adapter"
            )
        if request.is_notification:
            raise McpStdioError(f"{request.method} must include a JSON-RPC request id")
        if request.params:
            raise McpStdioError(f"{request.method} params must be empty when present")
        result: dict[str, object]
        if request.method == "tools/list":
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
    """null, boolean, float ID를 허용하지 않아 request와 notification을 명확히 구분한다."""
    if "id" not in payload:
        return None
    request_id = payload["id"]
    if isinstance(request_id, bool) or not isinstance(request_id, (str, int)):
        raise McpStdioError("JSON-RPC id must be a string or integer when present")
    if isinstance(request_id, str) and not request_id.strip():
        raise McpStdioError("JSON-RPC string id must not be empty")
    return request_id


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
