"""Volume 08의 모든 고정 Router fixture를 조합하는 로컬 미니 프로젝트 예제."""

from __future__ import annotations

from ai_platform.router.mini_project import build_router_mini_project


def main() -> None:
    """외부 API·네트워크 없이 재현 가능한 Router 결정 로그 집합을 출력한다."""
    print(build_router_mini_project().render_audit_report())


if __name__ == "__main__":
    main()
