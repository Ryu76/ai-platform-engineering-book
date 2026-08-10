# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 두 번째 장 `02-why-it-matters.md`를 PRD Chapter Definition of Done의 14개 장 섹션을 갖춘 독립 장으로 보완하고, LLM·검증 코드·사람 승인의 책임 경계 및 실제 오프라인 검증 경로를 계약 테스트로 고정했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 `03-theory.md`를 포함한 나머지 장의 장별 출고 감사와 전체 실습 재실행 근거가 필요합니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/02-why-it-matters.md`
  - 학습 목표, 필요성, 핵심 개념, ASCII 책임 경계도, 환경 설정, 단계별 오프라인 실습, 코드 설명, 정상 결과, 오류 해결, 응용 실습, 실무 적용, 과제, 체크리스트, 핵심 정리를 한국어로 보완했습니다.
  - 규칙 기반 코드와 LLM의 역할, 환각·최신성, 외부 전송·비용, 위험 작업의 검증된 Tool·사람 승인 경계를 설명했습니다.
  - `printf ... | uv run python examples/volume01/chat_cli.py --offline-demo` 및 Mock/오프라인 CLI 테스트를 실제 실행 경로로 명시했습니다.
  - 라이브 호출은 선택 사항이며 기본 학습·CI 경로는 API 키·네트워크·외부 전송이 없는 경로임을 명시했습니다.
  - 다음 장 `03-theory.md`로의 연결을 추가했습니다.
- `tests/integration/test_volume01_completion_contract.py`
  - 두 번째 장에 PRD의 14개 필수 장 섹션, 오프라인 CLI 명령, Mock 테스트 명령, 외부 전송 없는 설명, 사람 승인 경계, 다음 장 링크가 유지되는지 검사하는 계약 테스트를 추가했습니다.

이번 변경은 문서와 오프라인 검증만 다룹니다. 실제 LLM API 호출·외부 데이터 전송·비용·배포는 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ printf '%s\n' '배송 상태를 확인하고 싶습니다.' '/exit' | uv run python examples/volume01/chat_cli.py --offline-demo
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> AI> 오프라인 데모 응답: '배송 상태를 확인하고 싶습니다.' 요청을 기록했습니다.
사용자> 대화를 마칩니다.

$ uv run pytest tests/integration/test_volume01_completion_contract.py tests/integration/test_volume01_chat_cli.py tests/unit/test_llm_client.py -q
....................................                                     [100%]
36 passed in 0.72s

$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 7 source files

$ uv run pytest -q
.............................................................            [100%]
61 passed in 0.81s

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과

$ git diff --check
(exit 0; Git의 LF→CRLF 작업 트리 경고만 출력)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다.

## 알려진 차단 사항

- Volume 01을 완료로 선언할 수 없습니다. 첫 번째와 두 번째 장만 PRD의 14개 Chapter Definition of Done 섹션과 문서 계약 테스트로 보완했습니다. `03-theory.md`를 포함한 나머지 장의 장별 출고 감사와 보완 근거가 아직 없습니다.
- 라이브 모드는 입력을 선택한 제공자에 전송하고 비용이 발생할 수 있으므로, 학습·CI 검증에는 `--offline-demo`와 Mock/통합 테스트를 사용합니다.

## 다음 작업

- Volume 01의 세 번째 장 `03-theory.md`를 PRD Chapter Definition of Done에 맞는 독립 장으로 보완하고, 해당 장의 문서 계약 테스트와 오프라인 검증을 추가합니다.
