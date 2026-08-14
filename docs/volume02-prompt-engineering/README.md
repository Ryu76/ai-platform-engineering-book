# Volume 02. Prompt Engineering

> **공식 실습 환경:** 저장소 루트의 Anaconda PowerShell Prompt에서 `conda activate ai-platform-engineering-book`를 먼저 실행합니다. Python 예제·테스트·검사는 `uv`, `.venv`, 시스템 Python을 섞지 않고 이 Conda 환경에서만 실행합니다. 전체 절차는 [Anaconda 환경 설정](../setup/anaconda.md)을 참고합니다.




## 목표

Instruction, Context, Input Data, Output Format, Constraint를 분리해 재사용 가능한 Prompt와 오프라인 테스트를 작성합니다. 이 권의 모든 기본 실습은 API 키와 외부 LLM 호출 없이 실행할 수 있으며, 사용자 입력과 외부 문서를 신뢰되지 않은 데이터로 다룹니다.

## 장 목록

1. [Prompt 구성 요소와 첫 템플릿](01-prompt-components.md) — Instruction·Context·입력·형식·제약을 분리합니다.
2. [Zero-shot·One-shot·Few-shot](02-zero-one-few-shot.md) — 예시 수를 계약으로 관리하고 검토된 시연 데이터를 분리합니다.
3. [역할 Prompt와 구조화된 JSON 출력](03-role-structured-output.md) — 역할 설정과 JSON 스키마 검증을 분리합니다.
4. [ReAct 개념과 내부 추론 비노출 구조 설계](04-react-without-cot-exposure.md) — 행동·관찰·공개 결과를 분리합니다.
5. [Prompt Injection 방어와 입력 검증](05-prompt-injection-input-validation.md) — 신뢰 경계, 실패 닫힘 입력 검증, 위험 신호 검토를 분리합니다.
6. [Prompt Versioning·Template·결과 비교](06-prompt-versioning-comparison.md) — 버전 메타데이터와 고정 검토 기록을 분리해 비교합니다.
7. [Prompt 테스트 데이터](07-prompt-test-data.md) — 검토된 고정 fixture를 버전 비교에서 재사용합니다.
8. [미니 프로젝트: 오프라인 Prompt 회귀 검토](08-mini-project-offline-prompt-regression.md) — 같은 fixture로 버전의 JSON·기대값 계약을 비교합니다.
9. [권 단위 과제: 오프라인 Prompt 계약 검토](09-exercises.md) — 구성·입력 경계·구조화 출력·회귀 검토를 한 흐름으로 점검합니다.

학습 완료 여부와 Volume 03 인계 경계는 [학습자·제작 검수 체크리스트](checklist.md)에서 확인합니다. 작성된 장과 검증 이력은 [PROGRESS.md](PROGRESS.md)에서 확인합니다. 주요 개념의 짧은 정의와 안전 경계는 [Volume 02 주요 용어집](glossary.md)에서 확인합니다.

## 이 권의 결과물 경로

- `src/ai_platform/prompts/`: 재사용 가능한 Prompt 구성·검증 코드
- `examples/volume02/`: 외부 API를 호출하지 않는 실행 예제
- `tests/unit/test_prompts.py`: Prompt 문자열과 입력 경계를 검사하는 단위 테스트
- `glossary.md`: 이 권에서 사용하는 주요 Prompt Engineering 용어와 안전 경계

## 빠른 오프라인 확인

```bash
# 실행 위치: WSL Ubuntu, Linux 또는 Git Bash 터미널의 저장소 루트
conda env update --file environment.yml --prune
python examples/volume02/prompt_template_demo.py
pytest tests/unit/test_prompts.py -q
```

첫 명령은 의존성을 준비합니다. 둘째 명령은 템플릿을 렌더링할 뿐 네트워크에 연결하지 않습니다. 셋째 명령은 고정 섹션 순서와 입력 검증을 테스트합니다. 실제 API 키, 회사 문서, 개인정보를 이 경로에 넣지 마세요.

## Volume 완료 기준

이 권은 PRD의 필수 개념·실습·결과물, 장별 DoD, 오프라인 재실행, 미니 프로젝트, 테스트, 학습자 체크리스트, 다음 Volume 인계 목록을 모두 갖춘 뒤 완료로 선언했습니다. 출고 감사의 실행 근거와 완료 표식은 [PROGRESS.md](PROGRESS.md)에 기록합니다.
