"""Volume 03의 정적 MCP Resource가 파일·Tool 권한을 만들지 않는지 검사한다."""
from __future__ import annotations

import pytest

from ai_platform.mcp.resources import (
    McpResourceCatalog,
    McpResourceError,
    McpStaticResource,
)

POLICY_NOTE = McpStaticResource(
    uri="ai-platform://volume03/tool-policy",
    name="Tool policy note",
    mime_type="text/plain",
    text="Only reviewed, allowlisted Tools may be executed.",
)


def test_resource_catalog_lists_and_reads_only_embedded_allowlisted_text() -> None:
    catalog = McpResourceCatalog((POLICY_NOTE,))

    assert catalog.list_resources() == (
        {
            "uri": "ai-platform://volume03/tool-policy",
            "name": "Tool policy note",
            "mimeType": "text/plain",
        },
    )
    assert catalog.read_resource("ai-platform://volume03/tool-policy") == {
        "uri": "ai-platform://volume03/tool-policy",
        "mimeType": "text/plain",
        "text": "Only reviewed, allowlisted Tools may be executed.",
    }
    assert not hasattr(catalog, "execute")


def test_resource_catalog_does_not_resolve_unlisted_uri_as_a_file_or_alias() -> None:
    catalog = McpResourceCatalog((POLICY_NOTE,))

    with pytest.raises(McpResourceError, match="not allowlisted: file:///etc/passwd"):
        catalog.read_resource("file:///etc/passwd")
    with pytest.raises(McpResourceError, match="not allowlisted: ai-platform://volume03/tool-policy/"):
        catalog.read_resource("ai-platform://volume03/tool-policy/")


def test_resource_catalog_rejects_duplicate_or_non_static_resource_contracts() -> None:
    with pytest.raises(McpResourceError, match="URIs must be unique"):
        McpResourceCatalog((POLICY_NOTE, POLICY_NOTE))
    with pytest.raises(McpResourceError, match="must be an ai-platform URI"):
        McpStaticResource(
            uri="file:///not-a-resource.txt",
            name="File reference",
            mime_type="text/plain",
            text="This must remain embedded text.",
        )
    with pytest.raises(McpResourceError, match="MIME type must be text/plain"):
        McpStaticResource(
            uri="ai-platform://volume03/structured",
            name="Structured note",
            mime_type="application/json",
            text="{}",
        )
    with pytest.raises(McpResourceError, match="at most 4096"):
        McpStaticResource(
            uri="ai-platform://volume03/too-large",
            name="Too large note",
            mime_type="text/plain",
            text="x" * 4097,
        )
