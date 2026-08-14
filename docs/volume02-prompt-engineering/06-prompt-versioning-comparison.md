# 06. Prompt Versioning·Template·결과 비교

## 이 장에서 만드는 것

같은 고객 문의 분류 Prompt를 `v1`, `v2`처럼 **변경 가능한 자산**으로 관리하고, 고정된 검토 기록을 이용해 버전별 결과를 비교합니다. 구현은 다음 경로에 있습니다.

- `src/ai_platform/prompts/prompt_runner.py`: 버전 메타데이터 렌더링과 오프라인 비교 계약
- `examples/volume02/prompt_version_comparison_demo.py`: 두 버전의 고정 기록 비교
- `tests/unit/test_prompts.py`: 버전·입력 식별자·JSON 실패 처리 검사

이 장의 프로그램은 모델을 선택하거나 호출하지 않습니다. API 키, 네트워크, 회사 문서, 개인정보가 없어도 실행됩니다. `RecordedClassification`은 모델이 방금 생성한 결과가 아니라, 사람이 검토를 위해 제공한 **고정 응답 기록**입니다.

## 왜 버전을 관리해야 하는가

Prompt는 문자열처럼 보여도 서비스 동작을 바꾸는 설정입니다. 예를 들어 출력 형식을 바꾸거나 `unknown` 처리 제약을 추가하면, 같은 입력도 다른 결과를 낼 수 있습니다. 단순히 파일을 덮어쓰면 다음 질문에 답하기 어렵습니다.

- 현재 운영 검토 대상은 어느 Prompt인가?
- 무엇을 왜 바꾸었는가?
- 변경 뒤 JSON 형식 준수율과 기대 분류 일치율은 좋아졌는가?
- 잘못된 응답을 코드가 몰래 보정한 것은 아닌가?

`VersionedPrompt`는 버전 ID, 변경 요약, 기존 `PromptSections`를 한 객체로 묶습니다. 버전은 `v1`, `v2`처럼 순차적인 형식만 허용합니다. 렌더링 시 서비스 소유 메타데이터와 Prompt 계약은 신뢰되지 않은 입력보다 앞에 위치합니다.

## 버전 비교의 경계

비교는 품질을 관찰하는 도구이지 모델 평가를 대신하지 않습니다. 이 예제는 아래처럼 분리합니다.

1. 사람이 기대 분류를 검토해 `PromptComparisonCase`로 등록합니다.
2. 각 버전에서 얻었다고 **기록된** 응답을 `RecordedClassification`으로 명시합니다.
3. `compare_recorded_classifications()`가 기존 JSON 스키마로 응답을 검증합니다.
4. 유효 JSON 수와 기대 분류 일치 수를 버전별로 집계합니다.

입력 ID의 중복, 알 수 없는 ID, 누락된 결과는 모두 실패합니다. 잘못된 JSON은 추측·수정하지 않고 해당 케이스를 `schema_valid=False`, `category_matches=False`로 기록합니다. 원문 응답은 오류 메시지에 재출력하지 않으므로 검토 로그에 불필요한 사용자 데이터를 늘리지 않습니다.

## 실행

저장소 루트의 Git Bash, WSL, Linux 터미널에서 실행합니다.

```bash
conda env update --file environment.yml --prune
python examples/volume02/prompt_version_comparison_demo.py
pytest tests/unit/test_prompts.py -q
```

정상 실행에는 `v2`의 `[PROMPT VERSION]`과 `[UNTRUSTED USER INPUT]` 경계가 보입니다. 이어지는 비교에는 다음처럼 고정 기록의 결과만 표시됩니다.

```text
[RECORDED COMPARISON — no model was called]
v1: schema=1/2, category_match=1/2
v2: schema=2/2, category_match=2/2
```

이 숫자는 두 개의 교육용 기록에 대한 결과일 뿐, 실제 모델 성능 수치가 아닙니다. 실제 환경에서는 같은 버전에 대한 승인된 테스트 데이터, 모델 ID, 실행 시각, 안전한 접근 제어가 별도 필요합니다.

## 코드 사용 예

```python
from ai_platform.prompts import PromptSections, VersionedPrompt

prompt = VersionedPrompt(
    version="v2",
    change_summary="unknown 분류와 JSON 계약을 명확히 했습니다.",
    sections=PromptSections(
        instruction="문의 유형을 분류하세요.",
        context="허용 분류는 billing, technical, unknown입니다.",
        output_format='JSON: {"category": "...", "reason": "..."}',
    ),
)
rendered = prompt.render("영수증을 다시 받고 싶어요.")
```

`rendered`는 전송 가능한 문자열일 뿐입니다. 후속 호출 계층을 추가하더라도 API 키를 Prompt, 테스트 데이터, Git 기록에 넣지 말고, 검증된 JSON만 후속 업무 로직으로 전달하세요.

## 실무 체크리스트

- [ ] 변경 전 `vN` 버전과 변경 사유를 기록했다.
- [ ] Instruction, Context, Output Format, Constraint, 사용자 입력 경계를 분리했다.
- [ ] 버전마다 동일한 검토 케이스와 기대값을 사용했다.
- [ ] JSON 스키마 실패를 보정하지 않고 실패로 집계했다.
- [ ] 입력/결과 ID의 중복·누락·알 수 없는 매핑을 실패 닫힘으로 처리했다.
- [ ] 비교 숫자를 실제 모델 전체 성능으로 과장하지 않았다.
- [ ] API 키·실제 고객 데이터·라이브 API 호출을 예제와 테스트에 넣지 않았다.

다음 장에서는 이 비교용 케이스를 독립된 Prompt 테스트 데이터로 정리하고, 미니 프로젝트와 과제로 연결합니다.
