# Tool Calling: allowlist와 안전한 계산기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- LLM의 자연어 응답과 Tool 호출 요청을 구분한다.
- Tool 이름 allowlist가 필요한 이유를 설명한다.
- JSON Schema의 필수 인자, 타입, `enum`, 추가 필드 금지를 검증한다.
- 외부 부작용이 없는 계산기 Tool을 로컬에서 실행하고 테스트한다.

## 2. 왜 필요한가

LLM은 "파일을 지워라" 같은 문자열을 만들 수 있지만, 그 문자열이 시스템 명령을 실행할 권한은 아닙니다. 모델 출력은 **신뢰되지 않은 요청**으로 다루고, 애플리케이션이 미리 등록·검토한 Tool만 실행해야 합니다. 이 경계가 없으면 프롬프트 인젝션이나 모델 오류가 임의 명령 실행으로 이어질 수 있습니다.

> [!WARNING]
> 이 장의 `safe_calculator`는 사칙연산만 수행하는 순수 함수입니다. 파일, 셸, 네트워크, 환경 변수, 실제 서비스에 접근하지 않습니다. 모델이 제안한 도구 이름이나 인자를 `subprocess`, `eval`, 파일 API에 직접 전달하지 마세요.

## 3. 핵심 개념

- **Tool Calling:** 모델이 직접 작업하지 않고, 이름과 JSON 인자로 Tool 실행을 *요청*하는 인터페이스입니다.
- **Allowlist:** 애플리케이션이 등록한 Tool 이름만 실행하는 정책입니다. 미등록 이름은 거부합니다.
- **JSON Schema:** Tool이 받는 객체의 필수 필드, 타입, 허용 값 같은 계약입니다.
- **Argument validation:** 실행 전에 모델 요청이 계약을 만족하는지 확인하는 단계입니다. 검증 실패는 Tool을 실행하지 않습니다.

## 4. 동작 구조

```text
LLM 또는 테스트가 만든 Tool 요청
          │
          ▼
ToolRegistry.execute(name, arguments)
          │
          ├── 이름이 allowlist에 없음 ──► ToolNotAllowedError (실행 안 함)
          │
          ▼
JSON Schema 검증: required / type / enum / 추가 필드
          │
          ├── 계약 위반 ──► ToolArgumentsError (실행 안 함)
          │
          ▼
safe_calculator: add | subtract | multiply | divide
          │
          ▼
구조화된 ToolResult {"value": ...}
```

Tool Registry는 권한 결정자이며 LLM이 아닙니다. 이 장에서는 사람이 코드에 `SAFE_CALCULATOR`를 등록합니다. 다음 슬라이스에서 모델이 여러 Schema 중 하나를 선택하더라도 이 실행 경계는 바꾸지 않습니다.

## 5. 실습 환경

실행 위치는 저장소 루트입니다. Python과 검사 도구는 `uv`가 관리합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
uv sync --all-groups
```

확인할 파일은 다음과 같습니다.

- `src/ai_platform/tools/registry.py`: allowlist, 좁은 JSON Schema 검증, 순수 계산기
- `examples/volume03/safe_calculator.py`: 고정된 안전 입력으로 Tool을 실행하는 예제
- `tests/volume03/test_tool_registry.py`: 외부 호출 없는 회귀 테스트

## 6. 단계별 실습

### 6.1 allowlisted 계산기 실행

```bash
uv run python examples/volume03/safe_calculator.py
```

예제는 `safe_calculator` 하나만 등록하고 `{ "left": 21, "right": 2, "operation": "multiply" }`를 전달합니다. 입력은 코드에 고정되어 있으며 외부 시스템을 변경하지 않습니다.

### 6.2 거부 경계 확인

```bash
uv run pytest tests/volume03/test_tool_registry.py -q
```

테스트는 `delete_file`이라는 미등록 Tool, 누락 인자, `power`처럼 enum에 없는 연산, boolean 숫자, 추가 `path` 필드, 0 나누기를 모두 거부하는지 확인합니다. 실패 요청에서는 handler가 실행되지 않습니다.

## 7. 코드 설명

`ToolSpec`은 이름·설명·입력 Schema·handler를 함께 보관합니다. `ToolRegistry.execute()`는 먼저 이름으로 `_tools` 사전을 조회하므로 등록되지 않은 Tool을 호출할 수 없습니다. 그 뒤 `_validate_arguments()`가 `required`, `additionalProperties: false`, 숫자 유한성, 문자열 `enum`을 확인합니다.

`SAFE_CALCULATOR`의 `operation`은 `add`, `subtract`, `multiply`, `divide` 네 값뿐입니다. handler는 이 값에 대응하는 순수 사칙연산만 수행합니다. 따라서 LLM이 반환한 `"delete_file"` 또는 `"shell"` 문자열은 실행 경로에 존재하지 않습니다.

## 8. 정상 실행 결과

6.1 명령의 출력은 다음 한 줄입니다.

```text
42
```

6.2 명령은 설치 환경에 따라 실행 시간이 다르지만 `9 passed`로 끝나야 합니다. 이 결과는 실제 LLM, MCP Server, 파일 시스템 변경, 네트워크 호출이 없다는 조건에서 재현됩니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `No module named ai_platform` | 저장소 루트 밖에서 실행했거나 `uv run`을 생략했을 수 있습니다. | 루트에서 `uv sync --all-groups` 후 예제 명령을 다시 실행합니다. |
| `tool is not allowlisted` | Tool 이름이 등록된 이름과 다릅니다. | 임의 이름을 추가하지 말고 `allowed_tool_names()`와 코드 검토를 확인합니다. |
| `missing required argument` | 모델 요청에 Schema 필수 필드가 없습니다. | 요청을 재시도하기 전에 Schema에 맞는 구조화 인자를 만듭니다. |
| `unexpected argument` | 허용되지 않은 추가 필드가 들어왔습니다. | `additionalProperties: false`를 유지하고 필드를 무시하지 말고 거부합니다. |
| `division by zero` | 계산 결과가 정의되지 않습니다. | 0이 아닌 `right`를 전달하거나 호출 전에 별도 사용자 확인 흐름을 둡니다. |

## 10. 응용 실습

1. `safe_calculator`에 새 연산을 바로 추가하지 말고, 먼저 `enum`, handler 매핑, 정상·거부 테스트를 함께 작성합니다.
2. `ToolSpec`에 "파일 조회" 후보를 설계하되 구현하지 않습니다. 읽기 전용 허용 디렉터리, 최대 바이트 수, 금지 확장자를 Schema 밖의 정책으로 어떻게 검증할지 적습니다.
3. 실패 결과를 모델에 반환할 때 시스템 경로나 비밀값을 포함하지 않는 오류 형식을 설계합니다.

## 11. 실무 적용

운영 Tool에는 allowlist 외에도 호출 주체의 권한, 요청별 timeout, 제한된 retry, 감사 로그, 속도 제한, 위험 작업의 사람 승인이 필요합니다. 특히 삭제·배포·결제·권한 변경은 모델의 요청이나 JSON Schema 통과만으로 실행하면 안 됩니다. 검증은 입력 형식을 확인할 뿐 업무 승인이나 권한을 부여하지 않습니다.

Tool 결과도 신뢰 경계입니다. 반환 데이터에는 필요 최소한만 포함하고, 모델이나 사용자에게 내부 경로·토큰·원문 개인정보를 그대로 전달하지 않습니다.

## 12. 과제

- **기본:** allowlist가 단순한 Tool 설명문보다 강한 통제인 이유를 설명합니다.
- **응용:** `{ "path": "..." }`를 받는 읽기 전용 Tool의 별도 권한 정책 세 가지를 작성합니다.
- **심화:** Tool timeout, retry, 사람 승인을 어느 계층에서 적용할지 그리고 왜 Schema 검증만으로 충분하지 않은지 설계합니다.

## 13. 완료 체크리스트

- [ ] Tool 요청이 실행 명령이나 권한 부여가 아니라는 점을 설명할 수 있다.
- [ ] `safe_calculator`가 등록된 이름만 실행함을 확인했다.
- [ ] 필수 필드, 타입, enum, 추가 필드 금지의 목적을 설명할 수 있다.
- [ ] 예제와 테스트를 API 키·네트워크 없이 실행했다.
- [ ] 파일 삭제, 셸 실행, 배포, 권한 변경을 이 예제에 추가하지 않았다.
- [ ] JSON Schema 통과가 사람 승인이나 권한 검사를 대신하지 않음을 설명할 수 있다.

## 14. 핵심 정리

안전한 Tool Calling은 모델의 텍스트를 바로 실행하지 않습니다. 애플리케이션의 allowlist가 호출 가능한 기능을 고정하고, JSON Schema 검증이 인자의 형태를 제한하며, 검증된 순수 handler가 최소 결과를 반환합니다. 다음 슬라이스에서는 이 경계를 유지한 채 여러 Tool Schema를 모델에 제시하고 선택 결과를 안전하게 해석합니다.
