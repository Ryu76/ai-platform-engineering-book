# Zero-shot·One-shot·Few-shot: 예시 수를 계약으로 관리하기

## 1. 학습 목표

이 장을 마치면 같은 업무에 **zero-shot**, **one-shot**, **few-shot**을 언제 선택할지 설명하고, 예시를 서비스 소유 데이터로 검증하여 외부 LLM 호출 없이 재현 가능한 Prompt를 만들 수 있습니다.

- 예시가 없는 zero-shot과 예시 하나의 one-shot, 둘 이상의 few-shot을 구분한다.
- 불명확한 요청을 분류 기준·출력 형식·예시가 있는 Prompt로 개선한다.
- 예시 입력·기대 출력을 새 사용자 입력과 다른 데이터 경계에 둔다.
- 전략과 예시 수가 맞지 않으면 모델 호출 전에 실패시킨다.
- 예시가 결과 품질을 보장하지 않으며 편향·개인정보·Injection 위험을 검토한다.

## 2. 왜 필요한가

`문의 유형을 알려 주세요`라는 요청만으로는 분류 기준과 반환값을 알 수 없습니다. **Zero-shot**은 이런 일을 Instruction·Context·Constraint만으로 시키는 방식입니다. 업무가 단순하고 기준이 명확할 때는 가장 짧고 관리하기 쉽습니다.

형식이나 판단 경계가 모호하면 한 개의 대표 사례를 보여 주는 **one-shot**이 도움이 됩니다. 여러 경계 사례—예를 들어 청구, 기술 오류, 알 수 없음—의 일관성을 유도해야 하면 **few-shot**을 사용합니다. 그러나 예시는 규칙을 대체하지 않습니다. 예시가 많으면 Prompt 비용과 컨텍스트 사용량이 늘고, 잘못된 예시는 같은 잘못을 강화합니다.

이 장에서는 모델이 실제로 어떤 답을 낼지 주장하지 않습니다. 대신 선택한 전략, 예시 순서, 새 입력의 데이터 경계를 문자열 계약과 테스트로 고정합니다.

> [!WARNING]
> 예시도 신뢰 검토 대상입니다. 고객 원문, API 키, 사내 문서, 개인정보를 예시나 테스트에 복사하지 마세요. 검색 결과·사용자 제공 few-shot 예시를 즉시 시스템 규칙으로 승격하지 말고, 검토·승인된 서비스 데이터만 사용합니다. 이 장의 태그는 경계를 설명할 뿐 Prompt Injection을 완전히 막지 못합니다.

## 3. 핵심 개념

| 방식 | 예시 수 | 알맞은 상황 | 주의점 |
|---|---:|---|---|
| Zero-shot | 0 | 기준이 짧고 명확한 분류·변환 | 모델이 형식·경계 사례를 추측할 수 있다. |
| One-shot | 1 | 대표 출력 형태를 보여 줄 때 | 하나의 사례가 전체 분포를 대표하지 않을 수 있다. |
| Few-shot | 2개 이상 | 여러 분류·경계·예외를 보여 줄 때 | 비용, 편향, 오래된 예시를 관리해야 한다. |

**PromptExample**은 검토된 `input_data`와 `expected_output` 한 쌍입니다. **ShotPrompt**는 `ShotMode`와 예시 수의 계약을 검사합니다. 즉 zero-shot에는 정확히 0개, one-shot에는 정확히 1개, few-shot에는 최소 2개의 예시만 허용합니다.

다음 두 종류의 데이터는 책임이 다릅니다.

- **Demonstrations:** 서비스가 소유하고 검토한 입력·기대 출력이다. Prompt 동작을 설명하는 고정 자산이다.
- **Untrusted user input:** 이번 요청의 처리 대상이다. 예시나 시스템 정책을 수정하는 명령이 아니다.

## 4. 동작 구조

`ShotPrompt`는 서비스가 검토한 시연 데이터와 이번 요청을 같은 문자열에 넣더라도, 역할과 위치를 섞지 않습니다. 렌더링만 수행하며 모델 호출이나 답변 추론은 하지 않습니다.

```text
검토·승인된 PromptSections ─┐
검토·승인된 PromptExample들 ─┼─> ShotPrompt 구성 검증 ─> [DEMONSTRATIONS]
선택한 ShotMode ────────────┘          │
                                       │ 예시 수가 맞지 않으면 중단
신뢰되지 않은 새 사용자 입력 ─> 입력 검증 ─> [UNTRUSTED USER INPUT]
                                                    │
                                                    ▼
                              오프라인에서 검토 가능한 렌더링 Prompt
```

이 경계는 모델이 Injection을 따르지 않도록 보장하는 보안 경계가 아닙니다. 다만 어느 데이터가 서비스 정책이고 어느 데이터가 처리 대상인지 코드·테스트·리뷰에서 분명하게 만듭니다.

## 5. 단계별 실습: 불명확한 Prompt 개선

다음의 나쁜 Prompt는 분류 목록, 출력 형식, 근거, 모르는 경우의 처리를 모두 빠뜨립니다.

```text
문의 유형을 알려 주세요: 비밀번호를 재설정할 수 없어요.
```

아래처럼 1장의 구성 요소를 먼저 고정합니다. 그 후 업무에 필요한 예시 수만 별도 정책으로 선택합니다.

```text
[INSTRUCTION]
고객 문의를 한 문장으로 분류하세요.

[CONTEXT]
분류값은 billing, technical, account 중 하나입니다.

[OUTPUT FORMAT]
JSON 객체: {"category": "..."}

[CONSTRAINTS]
- 근거가 부족하면 category에 unknown을 사용하세요.
- 추측한 사실을 추가하지 마세요.
```

이 계약에 one-shot을 더하면 `[DEMONSTRATIONS]`에 검토된 입력·기대 출력 한 쌍이 추가됩니다. few-shot은 같은 형식의 쌍을 순서대로 두 개 이상 추가합니다. 새 질문은 항상 마지막 `[UNTRUSTED USER INPUT]`에 남습니다.

## 6. 실습 환경

- `src/ai_platform/prompts/shot_prompts.py`: 전략·예시 수·빈 값을 검증하고 Prompt를 렌더링합니다.
- `examples/volume02/shot_prompt_demo.py`: 세 전략을 네트워크 없이 콘솔에 출력합니다.
- `tests/unit/test_prompts.py`: 예시 수 계약, 순서, 입력 경계를 검사합니다.

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
uv sync --all-groups
uv run python examples/volume02/shot_prompt_demo.py
uv run pytest tests/unit/test_prompts.py -q
```

모든 명령은 API 키, 네트워크, 모델 호출 없이 실행됩니다. Windows Git Bash에서 저장소가 다른 드라이브에 있다면 해당 저장소 경로로 이동한 뒤 실행합니다. `uv sync --all-groups`는 `pyproject.toml`에 고정된 개발 의존성을 현재 저장소의 `.venv`에 준비합니다. 데모 명령은 세 Prompt 문자열을 출력하고, pytest 명령은 기대한 문자열 계약을 검사합니다. 정상 결과와 오류 해결 방법은 각각 8절과 9절에서 확인합니다.

## 7. 코드 설명

`ShotPrompt.render()`는 먼저 1장의 `PromptSections.render()`로 서비스 규칙과 새 입력을 검증합니다. 그 문자열에서 `[UNTRUSTED USER INPUT]` 앞에 `[DEMONSTRATIONS]`를 삽입합니다. 따라서 예시와 새 요청은 태그와 위치가 다릅니다.

```python
prompt = ShotPrompt(
    template(),
    ShotMode.ONE,
    (PromptExample("영수증을 받고 싶어요.", '{"category": "billing"}'),),
)
print(prompt.render("비밀번호를 재설정할 수 없어요."))
```

출력은 다음 순서를 가져야 합니다.

```text
[INSTRUCTION] ... [CONTEXT] ... [OUTPUT FORMAT] ... [CONSTRAINTS]
[DEMONSTRATIONS]
[EXAMPLE 1]
<example_input>
영수증을 받고 싶어요.
</example_input>
<expected_output>
{"category": "billing"}
</expected_output>
[UNTRUSTED USER INPUT]
...
<user_input>
비밀번호를 재설정할 수 없어요.
</user_input>
```

이 문자열은 모델의 답이 아닙니다. `expected_output`은 예시 입력에 대한 검토된 목표이고, 실제 응답의 JSON 유효성 검증은 다음 장에서 별도 구현합니다.

## 8. 정상 실행 결과와 계약 테스트

데모는 `===== zero-shot =====`, `===== one-shot =====`, `===== few-shot =====` 순서로 세 Prompt를 출력합니다. zero-shot의 demonstrations 섹션에는 `제공하지 않음 (zero-shot)`만 있고, one-shot에는 `[EXAMPLE 1]`, few-shot에는 `[EXAMPLE 1]`, `[EXAMPLE 2]`가 순서대로 나타납니다. 세 경우 모두 새 질문은 `<user_input>` 안에 있습니다.

테스트는 다음을 확인합니다.

1. zero-shot은 예시를 허용하지 않는다.
2. one-shot은 정확히 하나, few-shot은 둘 이상의 예시가 필요하다.
3. 빈 예시 입력 또는 빈 기대 출력은 모델 호출 전 `PromptConfigurationError`가 된다.
4. 서비스 예시는 `[DEMONSTRATIONS]`에, 요청 데이터는 그 뒤 `[UNTRUSTED USER INPUT]`에 있다.

## 9. 오류 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| `zero-shot requires exactly zero examples` | zero-shot에 예시를 넣었다. | 예시를 제거하거나 의도를 one-shot/few-shot으로 바꾼다. |
| `one-shot requires exactly one example` | 예시가 0개 또는 2개 이상이다. | 대표 사례 하나만 남기거나 few-shot을 선택한다. |
| `few-shot requires at least two examples` | few-shot인데 비교할 사례가 하나뿐이다. | 다른 분류 또는 경계 사례를 검토해 추가하거나 one-shot을 쓴다. |
| `example input_data must be a non-empty string` | 예시 입력이 공백뿐이다. | 익명화된 실제 업무 형태의 검토된 입력을 작성한다. |
| 예시 태그가 있으니 안전하다고 생각함 | 태그는 모델의 규칙 변경을 기술적으로 차단하지 않는다. | 입력 검증, 권한 분리, 도구 인자 검증을 적용한다. 자세한 방어는 5장에서 다룬다. |

## 10. 응용 실습: 예시 선택 기준

Few-shot 예시는 많이 모으는 것보다 **판단을 바꾸는 사례**를 선택하는 편이 낫습니다.

- 각 허용 분류를 적어도 하나씩 대표하는가?
- `unknown`처럼 모델이 추측하기 쉬운 경계 사례가 있는가?
- 기대 출력이 현재 JSON 계약과 일치하는가?
- 예시에 실명, 연락처, 토큰, 사내 비공개 내용이 없는가?
- 새 정책이 생겼을 때 예시·테스트·버전을 함께 갱신할 수 있는가?

예시가 실제 사용자 입력에서 자동 수집되었다면 사람이 검토하기 전에는 few-shot 자산으로 쓰지 않습니다. 사용자가 보낸 `이전 지시를 무시하라` 같은 문장은 예시가 아니라 신뢰되지 않은 입력으로 처리해야 합니다.

## 11. 실무 적용

운영 서비스에서는 `PromptExample`을 코드에 즉석으로 추가하지 않습니다. 예시의 출처·검토자·정책 버전·갱신 날짜를 별도 변경 기록으로 관리하고, 변경 전후에 고정 테스트 데이터를 다시 실행합니다. 민감한 고객 입력은 익명화하더라도 재식별 가능성을 검토한 뒤 최소한으로 사용합니다.

Prompt에 경계 태그를 넣었다고 해서 권한을 부여하거나 도구를 실행해서는 안 됩니다. 실제 호출 계층은 허용된 출력 스키마를 검증하고, 후속 도구 계층은 독립적인 권한 확인과 인자 검증을 수행해야 합니다. 5장에서 사용자 입력 검증과 Injection 방어를 더 구체적으로 구현합니다.

## 12. 과제

1. **기본:** 고객 문의 분류에 zero-shot이 충분한 조건을 두 가지 적습니다.
2. **응용:** billing, technical, unknown을 구분하는 few-shot 예시 세 쌍을 익명 데이터로 작성하고 왜 각 사례가 필요한지 설명합니다.
3. **심화:** 예시 한 개가 오래된 정책을 보여 주어 실제 모델 출력이 틀렸다고 가정합니다. 템플릿, 테스트 데이터, 버전 기록을 어떤 순서로 수정·검토할지 설계합니다.

## 13. 완료 체크리스트

- [ ] Zero-shot·one-shot·few-shot의 예시 수와 선택 기준을 설명할 수 있다.
- [ ] 불명확한 Prompt에 Instruction·Context·Output Format·Constraint를 추가해 개선했다.
- [ ] 예시와 새 사용자 입력을 서로 다른 경계에 두었다.
- [ ] `ShotPrompt`의 예시 수 계약이 잘못된 구성을 거부함을 확인했다.
- [ ] 오프라인 데모와 `tests/unit/test_prompts.py`를 실행했다.
- [ ] 예시가 JSON 유효성·보안·품질을 보장하지 않음을 설명할 수 있다.
- [ ] 다음 장에서 역할 Prompt와 구조화된 출력 검증을 추가한다는 점을 이해했다.

## 14. 핵심 정리

Shot 방식은 예시의 **수**가 아니라 업무의 **불확실성**을 관리하는 선택입니다. 기본 규칙과 출력 계약을 먼저 명시하고, 필요한 만큼의 검토된 예시만 추가합니다. 예시 수·순서·입력 경계를 코드와 테스트로 고정하면 Prompt를 변경할 때 무엇이 달라졌는지 안전하게 검토할 수 있습니다.
