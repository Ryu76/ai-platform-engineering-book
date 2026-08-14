# Function Calling: 여러 Tool Schema와 Mock 선택 결과

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있습니다.

- allowlist에 있는 여러 Tool을 제공자 호환 Function Calling 정의로 직렬화한다.
- 모델이 돌려준 Tool-call payload를 JSON 객체로 파싱한다.
- 모델의 선택 결과도 기존 allowlist와 인자 검증을 반드시 통과하게 연결한다.
- 실제 모델 API 없이 Mock 응답으로 전체 경계를 테스트한다.

## 2. 핵심 원칙

Function Calling은 모델이 `name`과 JSON 인자를 **제안**하는 프로토콜입니다. `tools` 배열에 Schema를 보냈다는 사실이나 모델이 `type: "function"`을 반환했다는 사실은 실행 권한이 아닙니다.

이 슬라이스의 경계는 아래와 같습니다.

```text
등록 Tool 2개 ──► OpenAI 호환 tools 정의 ──► 고정 Mock 모델 응답
                                             │
                                parse_function_call()
                                             │
                                             ▼
                              ToolRegistry.execute()
                                  │        │
                  미등록 이름 ───┘        └── Schema 위반
                       거부                       거부
                                             │
                                             ▼
                              순수 safe_text_case 실행
```

`safe_calculator`와 `safe_text_case`만 등록합니다. 후자는 `upper`/`lower` 문자열 변환만 하는 순수 함수입니다. 두 Tool 모두 파일, 셸, 네트워크, 환경 변수, 실제 서비스에 접근하지 않습니다.

> [!WARNING]
> `function.name`을 셸 명령, 파일 경로, URL 또는 동적 import에 전달하지 마세요. `function.arguments`도 `json.loads()` 뒤 곧바로 실행하지 않습니다. 이 예제처럼 파싱 후 Registry의 allowlist와 JSON Schema 검증을 다시 거쳐야 합니다.

## 3. 제공자 호환 정의 형식

`serialize_function_tools()`는 등록 순서대로 다음과 같은 OpenAI 호환 형식을 만듭니다.

```json
{
  "type": "function",
  "function": {
    "name": "safe_text_case",
    "description": "문자열을 대문자 또는 소문자로만 변환합니다. 외부 시스템을 변경하지 않습니다.",
    "parameters": {
      "type": "object",
      "properties": {
        "text": {"type": "string"},
        "operation": {"type": "string", "enum": ["upper", "lower"]}
      },
      "required": ["text", "operation"],
      "additionalProperties": false
    },
    "strict": true
  }
}
```

`strict: true`은 지원하는 제공자에 Schema 준수를 요청하는 힌트입니다. 제공자가 이를 지원하지 않거나 모델이 잘못된 payload를 생성할 수 있으므로, 서버 쪽 검증을 제거할 근거가 되지 않습니다.

## 4. 오프라인 실습

저장소 루트에서 의존성을 준비합니다.

```bash
cd /e/python/ai-platform-engineering-book-volume-03
conda env update --file environment.yml --prune
```

고정 Mock 모델은 두 Schema를 받은 뒤 `safe_text_case`의 `upper` 호출을 반환합니다. 네트워크나 API 키는 사용하지 않습니다.

```bash
python examples/volume03/mock_function_calling.py
```

정상 출력은 다음 한 줄입니다.

```text
safe_text_case: AI PLATFORM
```

회귀 경계도 실행합니다.

```bash
pytest tests/volume03/test_function_calling.py -q
```

이 테스트는 (1) 두 allowlisted Tool만 직렬화되는지, (2) Mock 응답이 실행되는지, (3) JSON 배열·잘못된 JSON·누락 필드를 파싱 단계에서 거부하는지, (4) `delete_file`과 enum 밖 `title` 요청이 실행 경계에서 거부되는지를 확인합니다.

## 5. 코드 읽기 순서

1. `ToolRegistry.allowed_tools()`는 코드에 등록된 `ToolSpec`만 반환합니다.
2. `serialize_function_tools()`는 그 목록을 `type: function` 정의로 복사해 내보냅니다. 출력 Schema를 수정해도 Registry의 원본 계약이 바뀌지 않도록 깊은 복사를 사용합니다.
3. `parse_function_call()`은 `id`, `type`, `function.name`, JSON 문자열 `function.arguments`를 확인하고, 인자가 객체일 때만 `FunctionCall`을 만듭니다.
4. `dispatch_function_call()`은 별도의 실행기를 만들지 않고 `ToolRegistry.execute()`로 전달합니다. 따라서 `delete_file` 같은 이름은 Tool 정의에 섞여 있어도 등록되지 않았으면 거부됩니다.

## 6. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `function arguments are not valid JSON` | 모델이 JSON 문자열 대신 자연어 또는 손상된 JSON을 반환했습니다. | 결과를 실행하지 말고 모델에 구조화된 재생성을 요청하거나 실패로 처리합니다. |
| `function arguments must decode to a JSON object` | JSON 배열·문자열·숫자를 받았습니다. | 객체 인자만 허용하고 배열을 임의 위치 인자로 해석하지 않습니다. |
| `tool is not allowlisted` | 응답 이름이 Registry에 등록되지 않았습니다. | 모델이 제안한 이름을 자동 등록하지 말고 거부·감사합니다. |
| `operation must be one of` | 인자가 Tool Schema enum과 다릅니다. | 검증 오류를 안전한 형식으로 모델에 돌려주고 재시도를 제한합니다. |

## 7. 운영 적용 시 추가할 것

이 예제의 Mock은 교육용입니다. 실제 제공자 클라이언트는 HTTP timeout, 제한된 retry, 요청·응답 크기 제한, 제공자 오류 분류를 별도 어댑터에 둡니다. 위험한 Tool에는 호출 주체 권한, 사람 승인, 감사 로그를 Registry 이전 또는 실행 직전에 추가해야 합니다. `strict`과 JSON Schema는 형식을 제한할 뿐, 권한·승인·비용 한도·데이터 분류를 해결하지 않습니다.

## 8. 완료 체크리스트

- [ ] 여러 등록 Tool만 Function Calling `tools` 정의에 들어감을 확인했다.
- [ ] 모델 payload의 인자가 JSON 객체가 아니면 실행 전에 거부됨을 확인했다.
- [ ] 파싱 성공 뒤에도 allowlist와 Schema 검증이 다시 적용됨을 설명할 수 있다.
- [ ] Mock 예제와 테스트를 API 키·네트워크 없이 실행했다.
- [ ] Tool 이름이나 인자를 셸·파일 API·동적 실행에 전달하지 않았다.
