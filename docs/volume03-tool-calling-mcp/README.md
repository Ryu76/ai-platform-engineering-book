# Volume 03. Tool Calling & MCP

## 목표
LLM이 허용된 도구만 안전하게 선택·검증·호출하도록 구현하고 MCP Server/Client를 연결합니다.

## 장 목록
Function Calling · JSON Schema · Argument 검증 · Timeout/Retry · 권한 제어 · MCP Resource/Tool/Prompt · STDIO · Hermes/Codex 연동 · 승인 구조

## 학습 문서

1. [Tool Calling: allowlist와 안전한 계산기](01-tool-calling-allowlist.md) — 등록된 순수 함수만 호출하고 JSON 인자를 검증하는 첫 실행 경계
2. [Function Calling: 여러 Tool Schema와 Mock 선택 결과](02-function-calling-mock-dispatch.md) — 제공자 호환 정의를 만들고 Mock의 선택 결과도 allowlist로 다시 검증하는 경계
3. [Tool 실행: timeout과 제한된 retry](03-tool-timeout-retry.md) — 재시도가 기존 allowlist를 우회하지 않게 하고 Python timeout의 취소 한계를 확인하는 경계

진행 중인 구현 범위와 검증 기록은 [PROGRESS.md](PROGRESS.md)에서 확인합니다. 이 권의 모든 실습은 실제 파일 삭제, 셸 실행, 네트워크 요청 없이 시작합니다.
