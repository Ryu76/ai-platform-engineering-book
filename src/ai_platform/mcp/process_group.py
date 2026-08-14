"""MCP STDIO child group isolation intent를 typed fake seam으로 좁힌다.

이 module은 OS process group, Windows Job Object, signal API 또는 subprocess를 직접 열지 않는다.
Allowlisted launch plan과 trusted platform fixture를 검증한 뒤 graceful/force shutdown의 한 target만
injected sender에 전달한다. 실제 host는 이 intent를 platform-specific adapter에서 별도 구현한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from ai_platform.mcp.host import McpStdioHostLaunchPlan


class McpStdioProcessGroupError(ValueError):
    """group isolation intent가 sender 호출 전에 거부되었음을 나타낸다."""


class McpStdioProcessPlatform(StrEnum):
    """교육용 host가 명시적으로 모델링하는 두 process-isolation platform이다."""

    POSIX = "posix"
    WINDOWS = "windows"


class McpStdioGroupShutdownPhase(StrEnum):
    """host shutdown owner가 선택하는 한 번의 shutdown 단계다."""

    GRACEFUL = "graceful"
    FORCE = "force"


class McpStdioGroupShutdownTargetKind(StrEnum):
    """platform adapter가 해석할 isolated target 종류다."""

    POSIX_PROCESS_GROUP = "posix_process_group"
    WINDOWS_JOB = "windows_job"


@dataclass(frozen=True, slots=True)
class McpStdioIsolatedChildGroup:
    """trusted platform adapter가 증명한 child-owned isolation scope snapshot이다.

    POSIX fixture는 process-group leader와 process-group ID가 모두 direct child PID여야 한다.
    Windows fixture는 child가 job owner여야 하며, job scope ID는 deployment adapter가 부여한
    positive opaque identifier다. 이 contract는 sibling/parent/shared foreign group을 target으로
    보내지 않게 하며, group member discovery나 OS API 호출은 하지 않는다.
    """

    platform: McpStdioProcessPlatform
    child_pid: int
    isolation_owner_pid: int
    shutdown_scope_id: int

    def __post_init__(self) -> None:
        if not isinstance(self.platform, McpStdioProcessPlatform):
            raise McpStdioProcessGroupError("MCP STDIO process platform is unsupported")
        _validate_pid(self.child_pid, field_name="child pid")
        _validate_pid(self.isolation_owner_pid, field_name="isolation owner pid")
        _validate_pid(self.shutdown_scope_id, field_name="shutdown scope id")
        if self.isolation_owner_pid != self.child_pid:
            raise McpStdioProcessGroupError(
                "MCP STDIO process group is not owned by the direct child"
            )
        if (
            self.platform is McpStdioProcessPlatform.POSIX
            and self.shutdown_scope_id != self.child_pid
        ):
            raise McpStdioProcessGroupError(
                "MCP STDIO POSIX process group leader does not match the direct child"
            )


@dataclass(frozen=True, slots=True)
class McpStdioGroupShutdownTarget:
    """raw signal name 없이 platform adapter에 전달하는 one-shot isolated target이다."""

    server_name: str
    platform: McpStdioProcessPlatform
    target_kind: McpStdioGroupShutdownTargetKind
    shutdown_scope_id: int
    phase: McpStdioGroupShutdownPhase

    def __post_init__(self) -> None:
        if not isinstance(self.server_name, str) or not self.server_name:
            raise McpStdioProcessGroupError("MCP STDIO process group server is invalid")
        if not isinstance(self.platform, McpStdioProcessPlatform):
            raise McpStdioProcessGroupError("MCP STDIO process platform is unsupported")
        if not isinstance(self.target_kind, McpStdioGroupShutdownTargetKind):
            raise McpStdioProcessGroupError("MCP STDIO process group target kind is invalid")
        if not isinstance(self.phase, McpStdioGroupShutdownPhase):
            raise McpStdioProcessGroupError("MCP STDIO process group shutdown phase is invalid")
        _validate_pid(self.shutdown_scope_id, field_name="shutdown scope id")
        expected_kind = _target_kind_for_platform(self.platform)
        if self.target_kind is not expected_kind:
            raise McpStdioProcessGroupError("MCP STDIO process group target kind is invalid")


@runtime_checkable
class McpStdioGroupShutdownSender(Protocol):
    """trusted host가 구현하는 one-shot platform shutdown adapter seam이다."""

    def send(self, target: McpStdioGroupShutdownTarget) -> None:
        """검증된 target 하나를 OS-specific graceful 또는 force action으로 해석한다."""


def prepare_mcp_stdio_group_shutdown_target(
    plan: McpStdioHostLaunchPlan,
    group: McpStdioIsolatedChildGroup,
    phase: McpStdioGroupShutdownPhase,
) -> McpStdioGroupShutdownTarget:
    """allowlisted plan의 child-owned group에서 한 typed shutdown target을 만든다; I/O는 없다."""
    if not isinstance(plan, McpStdioHostLaunchPlan):
        raise McpStdioProcessGroupError("MCP STDIO process group launch plan is invalid")
    if not isinstance(group, McpStdioIsolatedChildGroup):
        raise McpStdioProcessGroupError("MCP STDIO isolated child group is invalid")
    if not isinstance(phase, McpStdioGroupShutdownPhase):
        raise McpStdioProcessGroupError("MCP STDIO process group shutdown phase is invalid")
    return McpStdioGroupShutdownTarget(
        server_name=plan.server_name,
        platform=group.platform,
        target_kind=_target_kind_for_platform(group.platform),
        shutdown_scope_id=group.shutdown_scope_id,
        phase=phase,
    )


def send_mcp_stdio_group_shutdown_target(
    plan: McpStdioHostLaunchPlan,
    group: McpStdioIsolatedChildGroup,
    phase: McpStdioGroupShutdownPhase,
    sender: McpStdioGroupShutdownSender,
) -> McpStdioGroupShutdownTarget:
    """validated target 하나만 trusted sender에 전달한다.

    Invalid plan/group/phase/sender는 sender를 호출하지 않는다. Sender failure는 raw platform
    detail, retry, escalation, process wait 없이 generic error로 끝난다. Graceful 뒤 force 여부와
    child reaping은 caller-owned lifecycle policy다.
    """
    target = prepare_mcp_stdio_group_shutdown_target(plan, group, phase)
    if not isinstance(sender, McpStdioGroupShutdownSender):
        raise McpStdioProcessGroupError("MCP STDIO process group shutdown sender is invalid")
    try:
        sender.send(target)
    except Exception:
        raise McpStdioProcessGroupError("MCP STDIO process group shutdown request failed") from None
    return target


def _target_kind_for_platform(platform: McpStdioProcessPlatform) -> McpStdioGroupShutdownTargetKind:
    if platform is McpStdioProcessPlatform.POSIX:
        return McpStdioGroupShutdownTargetKind.POSIX_PROCESS_GROUP
    return McpStdioGroupShutdownTargetKind.WINDOWS_JOB


def _validate_pid(value: object, *, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise McpStdioProcessGroupError(f"MCP STDIO process group {field_name} is invalid")
