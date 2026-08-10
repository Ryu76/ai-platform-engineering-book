# System Prompt와 생성 파라미터

## 1. 학습 목표

이 장을 마치면 System Prompt의 책임을 사용자 입력과 분리해 설명할 수 있습니다. 또한 Temperature, Top-p, 최대 출력 토큰(Max Output Tokens), Stop Sequence를 함께 조정할 때의 트레이드오프를 이해하고, `GenerationParameters`로 안전하게 검증된 요청을 만들 수 있습니다.

## 2. 왜 필요한가

같은 모델과 같은 질문도 생성 파라미터에 따라 길이와 표현이 달라질 수 있습니다. 업무 처리 플랫폼에서 라우팅 결과를 JSON으로 요약하거나, 운영 안내를 일정한 톤으로 제공하려면 요청마다 우연히 달라지는 출력을 줄여야 합니다. 반대로 창의적 초안처럼 여러 표현을 탐색할 때는 제한적으로 다양성을 높일 수 있습니다.

System Prompt는 제품 또는 작업 흐름의 지속 규칙을 담당하고, User Message는 현재 사용자의 요청을 담당합니다. 둘을 하나의 문자열에 섞으면 대화 이력 관리와 테스트가 어려워집니다. 이 장은 Volume 01의 최초 호출 경계를 확장해, 파라미터를 코드에서 명시하고 외부 API 없이 직렬화 결과를 검증합니다.

> [!WARNING]
> System Prompt는 보안 경계가 아닙니다. 사용자가 "앞선 규칙을 무시하라"고 입력해도 권한 상승, 비밀값 공개, 위험한 Tool 실행을 허용해서는 안 됩니다. 이후 Volume 02의 Prompt Injection 방어와 Volume 03의 Tool 권한 검증을 별도 경계로 구현합니다.

## 3. 핵심 개념

**System Prompt**는 모델이 대화 전체에서 따라야 할 역할, 출력 언어, 범위, 안전 제약을 전달하는 메시지입니다. 예를 들어 "두 문장 이내의 한국어 답변"은 검증 가능한 형식 제약입니다. 그러나 모델이 만든 답변의 사실성을 보장하지는 않습니다. 외부 문서의 근거와 인용은 Volume 05 RAG에서 추가합니다.

**Temperature**는 다음 토큰의 후보 확률을 얼마나 평탄하게 만들지 조절합니다. `0`에 가까우면 상대적으로 예측 가능한 선택을, 큰 값은 더 다양한 선택을 유도합니다. 이 구현은 호환성을 위해 `0`부터 `2`까지 허용합니다.

**Top-p**(nucleus sampling)는 누적 확률이 `p`가 될 때까지의 후보에서 토큰을 고르는 방식입니다. `0`보다 크고 `1` 이하여야 합니다. Temperature와 Top-p를 동시에 크게 바꾸면 원인을 분리하기 어렵습니다. 실무 실험에서는 한 번에 하나를 기준값에서 바꾸고 평가 데이터셋으로 비교합니다.

**최대 출력 토큰**은 응답이 생성할 수 있는 토큰의 상한입니다. 짧은 요약에 작은 값을 두면 지연 시간과 비용의 상한을 관리할 수 있지만, 문장이 중간에 끊길 수 있습니다. 이 클라이언트는 Chat Completions 호환 요청 필드인 `max_tokens`로 전송합니다.

**Stop Sequence**는 모델이 특정 문자열을 생성하면 출력을 멈추도록 요청하는 종료 표식입니다. 예제는 다음 사용자 차례가 답변에 섞이는 것을 줄이기 위해 `"\n\n사용자:"`를 사용합니다. 모델별 지원 여부와 세부 동작은 다르므로 실제 제공자 문서를 확인해야 합니다.

## 4. 동작 구조

```text
System Prompt ─── 역할·형식·제약 ─┐
User Message ──── 현재 요청 ──────┼──► LlmClient.complete()
GenerationParameters ─────────────┘          │
          │                                   ▼
          ├─ temperature (0 ~ 2)       OpenAI 호환 JSON 요청
          ├─ top_p (0 초과, 1 이하)            │
          ├─ max_output_tokens (양의 정수)     ▼
          └─ stop_sequences (최대 4개)   LLM 제공자 또는 Mock 전송 계층

테스트: 네트워크 없이 payload의 파라미터와 검증 오류를 확인
```

## 5. 실습 환경

이 장은 앞 장의 환경을 그대로 사용합니다.

- `src/ai_platform/llm/client.py`: `GenerationParameters`와 요청 직렬화를 제공합니다.
- `examples/volume01/system_prompt_parameters.py`: 실제 호출을 명시적으로 선택하는 예제입니다.
- `tests/unit/test_llm_client.py`: Mock 전송 계층으로 파라미터 전달과 경계값을 검사합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
uv sync --all-groups
```

이 명령은 프로젝트 가상환경을 동기화합니다. Windows 네이티브 경로에서 실행한다면 저장소 루트로 이동한 뒤 동일한 `uv run` 명령을 사용합니다. API 키 없이도 다음 단위 테스트를 실행할 수 있습니다.

## 6. 단계별 실습

### 6.1 외부 호출 없는 파라미터 계약 테스트

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/unit/test_llm_client.py -q
```

정상 결과에는 모든 테스트의 통과 수가 표시됩니다. 추가된 테스트는 `temperature=0.2`, `top_p=0.9`, `max_tokens=120`, `stop` 목록이 HTTP payload에 정확히 들어가는지 확인합니다. 실제 API 키나 네트워크는 사용하지 않습니다.

### 6.2 System Prompt와 파라미터 코드 읽기

`examples/volume01/system_prompt_parameters.py`는 역할과 형식을 System Message에 두고, 현재 질문을 User Message에 둡니다.

```python
response = client.complete(
    [
        ChatMessage(
            role="system",
            content="검증되지 않은 사실은 단정하지 말고, 한국어로 두 문장 이내로 답하세요.",
        ),
        ChatMessage(role="user", content="AI 업무 처리 플랫폼에서 Router의 역할을 설명하세요."),
    ],
    generation=GenerationParameters(
        temperature=0.2,
        top_p=0.9,
        max_output_tokens=120,
        stop_sequences=("\n\n사용자:",),
    ),
)
```

이 값은 요약처럼 형식이 중요한 작업을 위한 출발점일 뿐입니다. 답변 정확도는 파라미터가 아니라 입력 근거, 검색 품질, 평가로 관리해야 합니다.

### 6.3 선택 사항: 자신의 제공자로 한 번 실행

아래 명령은 외부 요청과 비용을 발생시킵니다. 외부 전송을 원하지 않거나 키가 없다면 실행하지 말고 6.1 테스트만 실행합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cp .env.example .env
# .env에 OPENAI_API_KEY와 LLM_MODEL을 자신의 값으로만 설정
set -a
. ./.env
set +a
uv run python examples/volume01/system_prompt_parameters.py
```

정상 실행 시 첫 줄은 모델의 답변이고, 다음 두 줄은 모델명·입력 토큰·출력 토큰입니다. `.env` 파일은 Git에 추가하지 않습니다.

## 7. 코드 설명

`GenerationParameters`는 불변 dataclass입니다. `temperature`, `top_p`, `max_output_tokens`는 값이 지정된 경우에만 검증합니다. 따라서 제공자의 기본값을 그대로 쓰려면 `generation` 인자를 생략할 수 있습니다. Stop Sequence는 빈 문자열을 금지하고, 요청 크기와 제공자 호환성을 단순하게 유지하기 위해 최대 네 개로 제한합니다.

`as_payload()`는 지정된 값만 JSON에 넣습니다. `max_output_tokens`라는 학습자용 이름은 Chat Completions의 `max_tokens`로 변환됩니다. `LlmClient.complete(..., generation=...)`는 이 사전을 기존 모델·메시지 payload에 합친 뒤 주입된 전송 계층에 전달합니다. 따라서 단위 테스트는 HTTP 호출 없이도 계약을 검증합니다.

## 8. 정상 실행 결과

이 장의 Mock 테스트에는 다음과 같은 결과가 포함됩니다.

```text
14 passed
```

실제 통과 수는 앞뒤 장에서 추가된 테스트에 따라 달라질 수 있습니다. 선택 실습의 모델 답변은 제공자와 모델에 따라 다르지만, `model=... input_tokens=...` 및 `output_tokens=...` 줄이 뒤따릅니다. 답변이 두 문장을 넘을 수 있으므로 출력 제약은 테스트와 후처리 정책으로도 확인해야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `temperature must be between 0 and 2` | 음수 또는 2보다 큰 값을 넣었습니다. | 우선 `0.2` 같은 작은 값으로 되돌리고, 변경 전후를 같은 테스트 질문으로 비교합니다. |
| `top_p must be greater than 0 and at most 1` | `0`, 음수 또는 1 초과 값입니다. | `0.9`처럼 범위 안의 값을 사용합니다. Temperature와 Top-p를 동시에 크게 바꾸지 않습니다. |
| `max_output_tokens must be a positive integer` | 0 이하 또는 불명확한 출력 상한입니다. | 작업에 필요한 양의 정수를 지정합니다. 응답이 잘리면 상한과 프롬프트 길이를 함께 점검합니다. |
| `stop sequences must not be empty` | 빈 종료 문자열은 어느 위치에서나 일치할 수 있습니다. | 의도가 분명한 비어 있지 않은 문자열만 사용합니다. |
| 실제 호출에서 400 응답 | 제공자가 `max_tokens` 또는 `stop`을 지원하지 않을 수 있습니다. | 해당 모델의 API 문서를 확인하고, 지원하지 않는 파라미터를 생략합니다. 키를 오류 메시지에 넣지 않습니다. |
| 사용자가 시스템 지시를 무시하라고 요청 | Prompt만으로 권한을 통제하려 했습니다. | 데이터·권한·Tool 호출을 Prompt와 분리하고, 이후 Volume의 입력 검증과 승인 흐름을 적용합니다. |

## 10. 응용 실습

1. `GenerationParameters(temperature=0.0, max_output_tokens=40)`를 사용하는 Mock 테스트를 추가하고, payload에 `top_p`가 없는지 검사합니다.
2. 같은 질문으로 `temperature=0.2`와 `temperature=1.0`의 결과를 기록하는 비교 스크립트를 설계합니다. 실제 호출은 자신의 승인과 비용 한도 안에서만 수행합니다.
3. 응답이 JSON이어야 하는 업무를 가정하고, System Prompt의 형식 지시와 별도로 응답 JSON 검증기를 설계합니다. Prompt만으로 JSON을 신뢰하지 마세요.

## 11. 실무 적용

운영 환경에서는 작업 유형별 기본 파라미터를 코드에 흩어 놓지 말고 버전이 있는 정책으로 관리합니다. 예를 들어 검색 근거 요약은 낮은 Temperature와 작은 출력 상한을, 초안 생성은 별도 평가를 통과한 정책을 사용할 수 있습니다. 어떤 정책이 어떤 응답을 만들었는지는 비밀값과 원문 개인정보를 제외한 식별자·버전·토큰 사용량으로 기록합니다.

Stop Sequence는 안전 제어가 아니라 출력 형식 보조 수단입니다. 출력 길이, JSON 구조, 인용 유무는 응답을 받은 뒤에도 프로그램으로 확인해야 합니다. 이 플랫폼은 다음 장에서 Streaming을 추가하더라도 동일한 메시지·파라미터 경계를 유지합니다.

## 12. 과제

- **기본:** Temperature와 Top-p가 각각 어떤 후보 선택을 조절하는지 두 문장으로 비교합니다.
- **응용:** 응답이 너무 자주 잘리는 상황을 가정해, 최대 출력 토큰과 System Prompt를 어떻게 함께 수정할지 제안합니다.
- **심화:** `GenerationParameters`에 제공자별 정책 이름을 직접 넣지 않고도 정책을 선택할 수 있는 설정 구조를 설계하고 Mock 테스트 사례를 작성합니다.

## 13. 완료 체크리스트

- [ ] System Prompt와 User Message의 책임을 분리해 설명할 수 있다.
- [ ] Temperature와 Top-p를 동시에 크게 바꾸지 않는 이유를 설명할 수 있다.
- [ ] 최대 출력 토큰이 비용·지연 시간·잘림에 미치는 영향을 설명할 수 있다.
- [ ] Stop Sequence가 보안 제어가 아님을 이해한다.
- [ ] 파라미터 직렬화와 범위 검증 테스트를 외부 호출 없이 실행했다.
- [ ] 실제 호출이 선택 사항이며 키·비용·외부 전송을 관리해야 함을 확인했다.

## 14. 핵심 정리

System Prompt는 지속 규칙, User Message는 현재 요청, 생성 파라미터는 출력의 확률적 특성과 상한을 담당합니다. `GenerationParameters`로 값을 명시하고 Mock 테스트로 요청 형식을 검증하면, 다음 Streaming 장에서도 재현 가능한 호출 경계를 유지할 수 있습니다.
