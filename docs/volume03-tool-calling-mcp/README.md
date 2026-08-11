# Volume 03. Tool Calling & MCP

## 목표
LLM이 허용된 도구만 안전하게 선택·검증·호출하도록 구현하고 MCP Server/Client를 연결합니다.

## 장 목록
Function Calling · JSON Schema · Argument 검증 · Timeout/Retry · 권한 제어 · MCP Resource/Tool/Prompt · STDIO · Hermes/Codex 연동 · 승인 구조

## 학습 문서

1. [Tool Calling: allowlist와 안전한 계산기](01-tool-calling-allowlist.md) — 등록된 순수 함수만 호출하고 JSON 인자를 검증하는 첫 실행 경계
2. [Function Calling: 여러 Tool Schema와 Mock 선택 결과](02-function-calling-mock-dispatch.md) — 제공자 호환 정의를 만들고 Mock의 선택 결과도 allowlist로 다시 검증하는 경계
3. [Tool 실행: timeout과 제한된 retry](03-tool-timeout-retry.md) — 재시도가 기존 allowlist를 우회하지 않게 하고 Python timeout의 취소 한계를 확인하는 경계
4. [Tool 권한: 위험도와 사람 승인](04-tool-authorization-approval.md) — 승인 기록을 요청 전체에 묶되 allowlist와 Schema 검증을 대체하지 않는 경계
5. [Tool 감사 로그: 최소 데이터로 실행 경계 추적하기](05-tool-audit-log.md) — 원문 인자·결과 없이 성공·거부·실패를 구조화해 남기는 경계
6. [MCP Tool catalog: 실행 권한 없이 allowlist를 노출하기](06-mcp-tool-catalog.md) — 등록된 순수 Tool 정의만 MCP `tools/list` 형태로 투영하고 실행 경계와 분리하는 첫 모델
7. [MCP Tool call request: 실행 전에 신뢰되지 않은 JSON 다시 검증하기](07-mcp-tool-call-request-validation.md) — 제한된 `name`·객체형 `arguments` JSON을 파싱하고 기존 allowlist·Schema로 실행 전 재검증하는 경계
8. [MCP Resource: 짧은 내장 텍스트만 읽기 전용으로 노출하기](08-mcp-static-resources.md) — URI를 파일 경로로 해석하지 않고 명시적으로 등록한 정적 Resource만 반환하는 경계
9. [MCP Prompt: 고정 allowlist 템플릿을 보간 없이 제공하기](09-mcp-static-prompts.md) — 사용자 입력을 받거나 보간하지 않고 검토된 고정 message만 반환하는 경계
10. [MCP Tool dispatcher: 검증된 요청을 실행 정책에 묶기](10-mcp-tool-dispatcher.md) — parser·allowlist·승인·timeout/retry·최소 감사를 결합하되 전송 계층은 열지 않는 실행 경계
11. [MCP STDIO lifecycle: JSON-RPC 한 줄과 handshake를 좁게 검증하기](11-mcp-stdio-lifecycle.md) — 실제 표준 입출력이나 Tool 실행 없이 LF framing·크기·고정 protocol version·initialize 순서를 검증하는 adapter
12. [MCP STDIO `tools/list`: handshake 뒤 allowlist catalog만 읽기 전용으로 노출하기](12-mcp-stdio-tools-list.md) — READY 뒤 catalog snapshot만 JSON-RPC response로 반환하고 Tool 실행 경계를 열지 않는 adapter
13. [MCP STDIO `resources/list`: handshake 뒤 정적 Resource metadata만 읽기 전용으로 노출하기](13-mcp-stdio-resources-list.md) — READY 뒤 정적 Resource metadata snapshot만 JSON-RPC response로 반환하고 content read·URI 해석 경계를 열지 않는 adapter
14. [MCP STDIO `prompts/list`: handshake 뒤 고정 Prompt metadata만 읽기 전용으로 노출하기](14-mcp-stdio-prompts-list.md) — READY 뒤 allowlisted Prompt metadata snapshot만 JSON-RPC response로 반환하고 message 반환·보간 경계를 열지 않는 adapter
15. [MCP STDIO `prompts/get`: 고정 allowlist Prompt만 보간 없이 반환하기](15-mcp-stdio-prompts-get.md) — READY 뒤 exact Prompt name과 빈 arguments만 검증해 고정 message snapshot을 반환하는 adapter
16. [MCP STDIO `resources/read`: 고정 allowlist Resource만 반환하기](16-mcp-stdio-resources-read.md) — READY 뒤 exact Resource URI만 검증해 내장 text snapshot을 반환하고 URI 해석 경계를 열지 않는 adapter
17. [MCP STDIO `tools/call`: 명시적 실행 경계로 순수 Tool만 연결하기](17-mcp-stdio-tools-call.md) — explicit boundary가 있을 때만 transport params를 기존 parser·allowlist·승인·timeout/retry·감사 dispatcher로 다시 전달하는 adapter
18. [MCP STDIO 승인 상관관계: JSON-RPC ID의 타입까지 요청에 묶기](18-mcp-stdio-approval-correlation.md) — trusted host가 typed request ID·Tool·canonical arguments를 승인에 묶고 string/integer ID 혼동을 거부하는 경계
19. [MCP STDIO stream loop: EOF·전송 실패·안전한 JSON-RPC error 분리하기](19-mcp-stdio-stream-runner.md) — injected text stream만 EOF까지 연결하고 invalid request를 고정 error로 분리하며 read/write failure에서 재시도 없이 닫는 경계
20. [MCP STDIO host launch plan: shell 없이 고정 allowlist와 resource budget을 모델링하기](20-mcp-stdio-allowlisted-launch-plan.md) — subprocess를 시작하지 않고 exact server selector를 fixed argv와 bounded stdout/stderr·shutdown·restart budget의 immutable plan으로 좁히는 경계
21. [MCP STDIO child shutdown: injected process에 유한한 graceful/force 종료 순서 적용하기](21-mcp-stdio-injected-child-shutdown.md) — trusted child adapter에만 already-exited 확인 → terminate 한 번 → bounded wait → kill 한 번의 finite shutdown 순서를 적용하는 경계
22. [MCP STDIO child factory: allowlisted plan만 trusted factory에 전달하기](22-mcp-stdio-injected-child-factory.md) — immutable plan의 fixed argv·bounded stream budget·`shell=False`만 injected factory에 한 번 전달하고 실제 subprocess는 열지 않는 시작 ownership 경계
23. [MCP STDIO subprocess factory: fixed argv·cwd·environment를 fake Popen seam으로 검증하기](23-mcp-stdio-subprocess-factory.md) — OS-specific adapter를 분리하고 explicit cwd·complete environment·binary pipe topology·`shell=False`를 fake Popen으로 검증하는 시작 경계

진행 중인 구현 범위와 검증 기록은 [PROGRESS.md](PROGRESS.md)에서 확인합니다. 이 권의 모든 실습은 실제 파일 삭제, 셸 실행, 네트워크 요청 없이 시작합니다.
