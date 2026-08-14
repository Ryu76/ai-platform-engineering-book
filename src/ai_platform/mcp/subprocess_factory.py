"""MCP STDIO용 OS subprocess adapter를 fixed configuration 뒤에 분리한다.

이 module은 allowlisted launch plan을 검증하거나 restart를 결정하지 않는다. trusted host가
만든 immutable configuration과 ``shell=False``인 tuple argv만 ``Popen`` adapter로 전달한다.
stdout/stderr drain, process group, cancellation, restart는 아직 소유하지 않는다.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from os import path
from subprocess import PIPE, Popen, TimeoutExpired
from types import MappingProxyType
from typing import Literal, Protocol, runtime_checkable

from ai_platform.mcp.host import McpStdioChildProcess


class McpStdioSubprocessError(ValueError):
    """OS-specific subprocess adapter의 고정 configuration 또는 start contract 오류다."""


@runtime_checkable
class McpStdioPopenProcess(Protocol):
    """``Popen`` 중 stream IO를 제외하고 shutdown adapter가 쓰는 최소 API다."""

    def poll(self) -> int | None:
        """종료했다면 exit code를, 실행 중이면 ``None``을 반환한다."""

    def terminate(self) -> None:
        """플랫폼의 기본 graceful terminate를 요청한다; group semantics는 후속 slice다."""

    def wait(self, timeout: float | None = None) -> int:
        """종료 code를 기다려 반환하거나 timeout이면 ``TimeoutExpired``를 발생시킨다."""

    def kill(self) -> None:
        """개별 child에 platform 기본 force-kill을 요청한다."""


class McpStdioPopenFactory(Protocol):
    """실제 Popen 대신 test가 fixed process creation kwargs를 확인할 수 있는 seam이다."""

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
        """한 fixed-argv process를 생성하고 shutdown API를 가진 adapter를 반환한다."""


@dataclass(frozen=True, slots=True)
class McpStdioSubprocessConfig:
    """trusted deployment가 subprocess adapter에 고정하는 cwd와 complete environment다.

    ``environment``는 parent process environment를 합치지 않는다. deployment가 필요한
    ``PATH`` 등의 값을 명시적으로 모두 제공해야 하며 caller/model/MCP peer가 start 때
    바꿀 수 없다.
    """

    cwd: str
    environment: Mapping[str, str]

    def __post_init__(self) -> None:
        """상대 cwd와 mutable/unbounded environment injection을 시작 전에 거부한다."""
        if not isinstance(self.cwd, str) or not self.cwd or "\x00" in self.cwd:
            raise McpStdioSubprocessError("cwd must be a non-empty NUL-free absolute path")
        if not path.isabs(self.cwd):
            raise McpStdioSubprocessError("cwd must be a non-empty NUL-free absolute path")
        if not isinstance(self.environment, Mapping) or not self.environment:
            raise McpStdioSubprocessError("environment must be a non-empty mapping")

        snapshot: dict[str, str] = {}
        total_bytes = 0
        for key, value in self.environment.items():
            if not isinstance(key, str) or not key or "=" in key or "\x00" in key:
                raise McpStdioSubprocessError("environment keys must be non-empty NUL-free names")
            if not isinstance(value, str) or "\x00" in value:
                raise McpStdioSubprocessError("environment values must be NUL-free strings")
            total_bytes += len(key.encode("utf-8")) + len(value.encode("utf-8")) + 2
            snapshot[key] = value
        if len(snapshot) > 128 or total_bytes > 32_768:
            raise McpStdioSubprocessError("environment exceeds the fixed adapter budget")
        object.__setattr__(self, "environment", MappingProxyType(snapshot))


@dataclass(frozen=True, slots=True)
class McpStdioSubprocessChild(McpStdioChildProcess):
    """Popen process를 existing finite shutdown contract로 좁히는 adapter다."""

    _process: McpStdioPopenProcess

    def poll(self) -> int | None:
        """wrapped process의 current exit status를 반환한다."""
        return self._process.poll()

    def terminate(self) -> None:
        """wrapped process 한 개에 기본 terminate를 전달한다."""
        self._process.terminate()

    def wait(self, timeout: float) -> int | None:
        """timeout을 무한 wait 없이 전달하고 ``TimeoutExpired``만 ``None``으로 바꾼다."""
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise McpStdioSubprocessError("child wait timeout must be a finite non-negative number")
        if not isfinite(timeout) or timeout < 0:
            raise McpStdioSubprocessError("child wait timeout must be a finite non-negative number")
        try:
            return self._process.wait(timeout=float(timeout))
        except TimeoutExpired:
            return None

    def kill(self) -> None:
        """wrapped process 한 개에 기본 force-kill을 전달한다."""
        self._process.kill()


class McpStdioSubprocessFactory:
    """fixed cwd/environment와 shell-free stdio pipe topology로 child 하나를 시작한다.

    기본 adapter는 Python ``Popen``이지만 test 또는 embedding host는 ``popen_factory``를
    주입할 수 있다. 이 class는 stdout/stderr를 읽거나 stdin에 쓰지 않으며 pipe byte budget은
    후속 bounded-drain owner가 사용할 launch plan metadata로 그대로 전달받을 뿐이다.
    """

    def __init__(
        self,
        config: McpStdioSubprocessConfig,
        *,
        popen_factory: McpStdioPopenFactory | None = None,
    ) -> None:
        if not isinstance(config, McpStdioSubprocessConfig):
            raise McpStdioSubprocessError("subprocess config is invalid")
        self._config = config
        self._popen_factory = popen_factory or _default_popen

    def start(
        self,
        *,
        argv: tuple[str, ...],
        max_stdout_bytes: int,
        max_stderr_bytes: int,
        shell: Literal[False],
    ) -> McpStdioChildProcess:
        """fixed argv와 explicit configuration만 Popen에 한 번 전달한다."""
        del max_stdout_bytes, max_stderr_bytes
        if shell is not False:
            raise McpStdioSubprocessError("subprocess factory requires shell=False")
        try:
            process = self._popen_factory(
                argv,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                shell=False,
                cwd=self._config.cwd,
                env=self._config.environment,
                text=False,
                bufsize=0,
                close_fds=True,
            )
        except Exception:
            raise McpStdioSubprocessError("MCP STDIO subprocess start failed") from None
        if not isinstance(process, McpStdioPopenProcess):
            raise McpStdioSubprocessError(
                "MCP STDIO subprocess factory returned an invalid process"
            )
        return McpStdioSubprocessChild(process)


def _default_popen(
    argv: tuple[str, ...],
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
    """실제 deployment용 Popen 호출을 한 곳에 두되 shell과 inherited env를 허용하지 않는다."""
    return Popen(
        argv,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        shell=shell,
        cwd=cwd,
        env=dict(env),
        text=text,
        bufsize=bufsize,
        close_fds=close_fds,
    )
