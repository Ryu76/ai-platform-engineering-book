# 역할 Prompt와 구조화된 JSON 출력: 요구와 검증을 분리하기

## 1. 학습 목표

이 장을 마치면 역할 Prompt(Role Prompt)가 담당 범위를 설명하는 설정임을 이해하고, JSON 출력 요구와 별도의 스키마 검증을 함께 구현할 수 있습니다.

- 역할을 사용자 입력이 아닌 서비스 소유 Prompt 설정으로 둔다.
- JSON 객체만 반환하도록 출력 계약을 명시한다.
- `category`, `reason`의 허용값·필수 여부·길이를 코드로 검증한다.
- JSON이 아니거나 알 수 없는 필드가 있으면 후속 처리 전에 거부한다.
- 역할 선언과 JSON 요구만으로 품질·보안·정확성이 보장되지 않음을 설명한다.

## 2. 왜 필요한가

`고객 지원 전문가처럼 답해 주세요`만으로는 처리 범위와 프로그램이 읽을 결과 모양이 정해지지 않습니다. 사람은 문장을 읽어 이해할 수 있어도, 다음 단계의 코드가 자유 형식 문장에서 분류값을 안전하게 꺼내기는 어렵습니다.

역할은 모델이 맡은 업무 관점을 짧게 제한합니다. 출력 계약은 호출자가 필요한 필드와 허용값을 정합니다. 그러나 모델에게 JSON을 요청하는 것은 **요구**일 뿐 강제가 아닙니다. 응답을 사용하는 코드가 스키마를 다시 검사해야 잘못된 분류, 추가 필드, 빈 근거를 모델 호출 직후 중단할 수 있습니다.

> [!WARNING]
> 이 장은 외부 모델을 호출하지 않습니다. `RolePrompt`의 역할 태그, `JSON 객체만 반환` 문구, Pydantic 검증은 서로 다른 방어층입니다. 특히 Prompt Injection, 권한 상승, Tool 실행 승인은 JSON 검증만으로 해결되지 않습니다. 실제 고객 원문·개인정보·API 키를 예제·테스트·로그에 넣지 마세요.

## 3. 핵심 개념

- **역할 Prompt(Role Prompt):** 서비스가 정한 업무 관점입니다. 예: `고객 지원 문의를 분류하는 담당자`.
- **구조화된 출력(Structured Output):** 호출자가 읽을 필드와 타입을 미리 합의한 응답 형태입니다.
- **JSON Output:** 구조화된 출력의 한 형식입니다. 텍스트가 JSON처럼 보여도 파싱·스키마 검증 전에는 신뢰하지 않습니다.
- **스키마(schema):** `category`의 허용값, `reason`의 길이, 추가 필드 금지처럼 기계가 검사할 계약입니다.
- **실패 닫힘(fail closed):** 유효하지 않은 응답을 추측해 고치지 않고 오류로 반환하여 후속 처리·Tool 호출을 막는 방식입니다.

이 장의 `SupportClassification`은 다음 JSON만 허용합니다.

```json
{"category": "billing", "reason": "영수증 재발급 요청입니다."}
```

`category`는 `billing`, `technical`, `unknown` 중 하나이고, `reason`은 공백 제거 뒤 1~240자여야 합니다. 알 수 없는 키는 허용하지 않습니다.

## 4. 동작 구조

```text
서비스가 검토한 역할 + PromptSections
              │
              ▼
      RolePrompt.render() ──> [ROLE] + 출력 JSON 계약
              │                         │
신뢰되지 않은 사용자 입력 ───────────────┴─> [UNTRUSTED USER INPUT]
                                                │
                                                ▼
                              (분리된 모델 호출 계층; 이 장에서는 미실행)
                                                │
                                                ▼
                   validate_classification_json(raw_response)
                        │ 성공                    │ 실패
                        ▼                         ▼
      SupportClassification 객체            StructuredOutputError
                        │                         │
                        ▼                         ▼
             제한된 후속 처리              후속 처리·Tool 실행 중단
```

역할과 템플릿은 서비스가 소유합니다. 사용자가 보낸 문장은 `render()` 인자로만 들어갑니다. 응답도 신뢰하지 않고 `validate_classification_json()`이 파싱과 스키마 검사를 통과시킨 객체만 사용합니다.

## 5. 실습 환경

- `src/ai_platform/prompts/structured_output.py`: 역할 Prompt, JSON 스키마, 실패 닫힘 검증을 제공합니다.
- `examples/volume02/structured_output_demo.py`: 고정된 안전 샘플을 렌더링·검증합니다.
- `tests/unit/test_prompts.py`: 역할 경계와 유효·무효 JSON 계약을 검사합니다.

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
uv sync --all-groups
uv run python examples/volume02/structured_output_demo.py
uv run pytest tests/unit/test_prompts.py -q
```

첫 명령은 Pydantic과 개발 검사 도구를 준비합니다. 둘째 명령은 네트워크, API 키, 모델 호출 없이 Prompt와 검증된 샘플을 출력합니다. 셋째 명령은 JSON 계약을 테스트합니다.

## 6. 단계별 실습

### 6.1 역할과 JSON 계약 렌더링

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
uv run python examples/volume02/structured_output_demo.py
```

출력에서 `[ROLE]`이 `[INSTRUCTION]`보다 앞에 있고, 사용자 문의가 마지막 `<user_input>`에 있는지 확인합니다. `[OUTPUT FORMAT]`과 `[CONSTRAINTS]`에는 JSON 객체·허용 분류·Markdown 금지가 표시됩니다.

### 6.2 JSON 응답을 사용 전 검증하기

```python
from ai_platform.prompts import validate_classification_json

response = validate_classification_json(
    '{"category": "technical", "reason": "앱이 멈춘다는 문의입니다."}'
)
assert response.category == "technical"
```

`validate_classification_json()`은 JSON 문법, 필수 키, 허용 분류, `reason` 길이, 추가 키를 한 번에 확인합니다. 호출 계층은 이 함수가 오류를 내면 재시도·사용자 안내·관측 로그 같은 분리된 정책으로 전환해야 하며, 임의 문자열을 Tool 인자로 전달하면 안 됩니다.

## 7. 코드 설명

`RolePrompt`는 `role`과 `PromptSections`를 불변 데이터 클래스에 보관합니다. 생성할 때 빈 역할과 잘못된 템플릿 타입을 거부합니다. 렌더링은 `[ROLE]`을 먼저 놓은 뒤 1장의 고정된 구성 요소와 신뢰되지 않은 입력 경계를 재사용합니다.

`SupportClassification`은 Pydantic 모델입니다. `Literal`은 분류값을 세 값으로 제한하고, `Field`는 근거 길이를 제한합니다. `ConfigDict(extra="forbid")`는 호출자가 기대하지 않은 `admin` 같은 키를 거부합니다. `validate_classification_json()`은 Pydantic의 상세 오류를 API 응답처럼 노출하지 않고 `StructuredOutputError`로 감싸며, 유효하지 않은 값을 자동 보정하지 않습니다.

## 8. 정상 실행 결과

데모 출력은 다음 순서를 가져야 합니다.

```text
[ROLE]
고객 지원 문의를 분류하는 담당자

[INSTRUCTION]
...

[VALIDATED JSON]
{"category":"billing","reason":"영수증 재발급 요청입니다."}
```

JSON의 공백은 Pydantic 버전에 따라 달라질 수 있지만, `category`와 `reason` 두 키가 있어야 합니다. 테스트 명령은 `passed`로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `response must match the SupportClassification JSON schema` | JSON이 아니거나 필수 필드·허용값·길이 계약을 어겼습니다. | 원문을 그대로 기록하지 말고 안전하게 오류 유형을 관측한 뒤, 출력 계약을 검토하거나 제한된 재시도 정책을 적용합니다. |
| `Extra inputs are not permitted` | 모델이 계약에 없는 키를 반환했습니다. | 추가 키를 무시하지 말고 `extra="forbid"`를 유지한 채 Prompt·모델 설정·후속 계약을 함께 검토합니다. |
| `role must be a non-empty string` | 역할 설정이 공백뿐입니다. | 서비스가 검토할 담당 범위를 짧고 명확하게 설정합니다. 사용자 입력으로 역할을 만들지 않습니다. |
| JSON을 요구했는데 코드 블록이 함께 옴 | 요청 문구만으로 출력 형식을 보장할 수 없습니다. | 코드 블록을 제거해 파싱하지 말고 스키마 오류로 처리합니다. 필요하면 제한된 재시도 정책을 별도로 설계합니다. |

## 10. 응용 실습

1. `SupportClassification`에 익명화된 `confidence` 숫자 필드를 추가하고 0~1 범위를 검증합니다.
2. `unknown` 응답일 때만 운영자 검토 큐로 보내는 **후속 코드**를 설계합니다. 이 규칙은 Prompt 문장이 아니라 검증을 통과한 객체에 적용합니다.
3. `reason`에 전화번호·계정번호 같은 개인정보 패턴이 있는 경우 보관 전에 마스킹하는 별도 계층을 설계합니다. 이 장의 스키마가 개인정보 검출을 제공한다고 가정하지 마세요.

## 11. 실무 적용

운영 코드에서 모델의 자연어 응답을 곧바로 데이터베이스 갱신, 이메일 발송, 권한 변경, Tool 인자에 사용하지 않습니다. JSON Schema 또는 Pydantic처럼 호출자가 통제하는 계약을 검증하고, 도메인 규칙·권한·인자 검증을 후속 계층에서 다시 적용합니다.

역할 Prompt는 책임 범위를 설명할 뿐 신원 인증이나 권한 부여가 아닙니다. `관리자`라는 역할 문구가 있어도 서비스의 액세스 제어 목록(allowlist)을 우회할 수 없습니다. 실패 응답의 전체 원문을 로그에 남기면 개인정보와 Injection 문자열을 재노출할 수 있으므로 보존·마스킹 정책도 별도로 둡니다.

## 12. 과제

- **기본:** Role Prompt와 Instruction이 각각 무엇을 정하는지 고객 문의 분류 예제로 설명합니다.
- **응용:** `billing`, `technical`, `unknown`의 정상 JSON 세 개와 잘못된 JSON 세 개를 작성하고, 각각 어떤 스키마 규칙을 통과·실패하는지 적습니다.
- **심화:** 유효한 JSON이지만 위험한 Tool 인자를 담은 응답을 가정합니다. JSON 스키마, 도메인 검증, 권한 검사, 사용자 승인 책임을 나누어 설계합니다.

## 13. 완료 체크리스트

- [ ] 역할을 서비스 소유 설정으로, 사용자 입력을 신뢰되지 않은 데이터로 분리했다.
- [ ] JSON 출력 요구가 유효한 JSON을 보장하지 않음을 설명할 수 있다.
- [ ] 허용 분류·필수 필드·근거 길이·추가 키를 스키마로 검증했다.
- [ ] 유효하지 않은 응답이 `StructuredOutputError`로 중단됨을 확인했다.
- [ ] 오프라인 데모와 `uv run pytest tests/unit/test_prompts.py -q`를 실행했다.
- [ ] JSON 검증이 Tool 권한·개인정보·Prompt Injection 방어를 대체하지 않음을 설명할 수 있다.
- [ ] 다음 장에서 내부 추론을 노출하지 않는 구조적 추론 설계를 다룬다는 점을 이해했다.

## 14. 핵심 정리

역할은 업무 관점을, Prompt 구성 요소는 요청 계약을, JSON 스키마는 프로그램이 사용할 데이터 계약을 담당합니다. 이 세 가지를 분리하면 응답이 잘못되었을 때 모델 문장·입력 데이터·후속 코드 중 어느 경계에서 멈춰야 하는지 명확해집니다. 출력 요구만 믿지 말고, 검증을 통과한 데이터만 제한된 다음 단계에 전달하세요.
