"""Volume 03의 OS-specific MCP STDIO Popen seam을 real process 없이 검증한다."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from subprocess import PIPE, TimeoutExpired
from typing import Literal

import pytest

from ai_platform.mcp.host import (
    McpStdioHostAllowlist,
    McpStdioHostError,
    McpStdioServerSpec,
    start_mcp_stdio_child,
)
from ai_platform.mcp.subprocess_factory import (
    McpStdioPopenProcess,
    McpStdioSubprocessConfig,
    McpStdioSubprocessError,
    McpStdioSubprocessFactory,
)


def _launch_plan() -> object:
    return McpStdioHostAllowlist(
        (
            McpStdioServerSpec(
                name="safe-echo",
                argv=("volume03-safe-echo-server", "--stdio"),
                max_stdout_bytes=16_384,
                max_stderr_bytes=4_096,
                shutdown_grace_seconds=2.0,
                restart_limit=0,
            ),
        )
    ).prepare_launch("safe-echo")


class _FakePopenProcess(McpStdioPopenProcess):
    def __init__(self, *, timeout: bool = False) -> None:
        self.actions: list[str] = []
        self.timeout = timeout

    def poll(self) -> int | None:
        self.actions.append("poll")
        return None

    def terminate(self) -> None:
        self.actions.append("terminate")

    def wait(self, timeout: float | None = None) -> int:
        self.actions.append(f"wait:{timeout}")
        if self.timeout:
            raise TimeoutExpired("volume03-safe-echo-server", timeout)
        return 0

    def kill(self) -> None:
        self.actions.append("kill")


class _RecordingPopen:
    def __init__(self, process: McpStdioPopenProcess) -> None:
        self.process = process
        self.calls: list[dict[str, object]] = []

    def __call__(
        self,
        argv: tuple[str, ...],
        *,
        stdin: int,
        stdout: int,
        stderr: int,
        shell: Literal[False],
        cwd: str,
        env: Mapping[str, str],
        text: Literal[False],
        bufsize: int,
        close_fds: bool,
    ) -> McpStdioPopenProcess:
        self.calls.append(
            {
                "argv": argv,
                "stdin": stdin,
                "stdout": stdout,
                "stderr": stderr,
                "shell": shell,
                "cwd": cwd,
                "env": dict(env),
                "text": text,
                "bufsize": bufsize,
                "close_fds": close_fds,
            }
        )
        return self.process


def test_factory_calls_injected_popen_once_with_fixed_shell_free_pipe_configuration() -> None:
    fake_popen = _RecordingPopen(_FakePopenProcess())
    config = McpStdioSubprocessConfig(
        cwd=str(Path.cwd()), environment={"PATH": "C:/trusted/bin", "MCP_MODE": "offline"}
    )
    factory = McpStdioSubprocessFactory(config, popen_factory=fake_popen)

    child = start_mcp_stdio_child(_launch_plan(), factory)  # type: ignore[arg-type]

    assert child.poll() is None
    assert fake_popen.calls == [
        {
            "argv": ("volume03-safe-echo-server", "--stdio"),
            "stdin": PIPE,
            "stdout": PIPE,
            "stderr": PIPE,
            "shell": False,
            "cwd": str(Path.cwd()),
            "env": {"PATH": "C:/trusted/bin", "MCP_MODE": "offline"},
            "text": False,
            "bufsize": 0,
            "close_fds": True,
        }
    ]


def test_config_snapshots_environment_without_retaining_the_caller_mapping() -> None:
    supplied_environment = {"PATH": "C:/trusted/bin"}

    config = McpStdioSubprocessConfig(cwd=str(Path.cwd()), environment=supplied_environment)
    supplied_environment["UNTRUSTED"] = "later-change"

    assert dict(config.environment) == {"PATH": "C:/trusted/bin"}
    with pytest.raises(TypeError):
        config.environment["OTHER"] = "blocked"  # type: ignore[index]


@pytest.mark.parametrize(
    ("cwd", "environment", "message"),
    (
        ("relative/mcp", {"PATH": "C:/trusted/bin"}, "absolute path"),
        (str(Path.cwd()), {}, "non-empty mapping"),
        (str(Path.cwd()), {"BAD=NAME": "value"}, "environment keys"),
        (str(Path.cwd()), {"PATH": "bad\x00value"}, "environment values"),
    ),
)
def test_config_rejects_ambiguous_cwd_or_environment(
    cwd: str, environment: dict[str, str], message: str
) -> None:
    with pytest.raises(McpStdioSubprocessError, match=message):
        McpStdioSubprocessConfig(cwd=cwd, environment=environment)


def test_factory_failure_is_narrowed_by_existing_host_start_boundary() -> None:
    def failing_popen(
        argv: tuple[str, ...],
        **kwargs: object,
    ) -> McpStdioPopenProcess:
        del argv, kwargs
        raise RuntimeError("real executable path must not leak")

    factory = McpStdioSubprocessFactory(
        McpStdioSubprocessConfig(cwd=str(Path.cwd()), environment={"PATH": "C:/trusted/bin"}),
        popen_factory=failing_popen,  # type: ignore[arg-type]
    )

    with pytest.raises(McpStdioHostError, match="child start failed") as error:
        start_mcp_stdio_child(_launch_plan(), factory)  # type: ignore[arg-type]

    assert "real executable path" not in str(error.value)


def test_child_converts_only_popen_timeout_to_bounded_wait_result() -> None:
    fake_process = _FakePopenProcess(timeout=True)
    factory = McpStdioSubprocessFactory(
        McpStdioSubprocessConfig(cwd=str(Path.cwd()), environment={"PATH": "C:/trusted/bin"}),
        popen_factory=_RecordingPopen(fake_process),
    )

    child = start_mcp_stdio_child(_launch_plan(), factory)  # type: ignore[arg-type]

    assert child.wait(0.0) is None
    assert fake_process.actions == ["wait:0.0"]
