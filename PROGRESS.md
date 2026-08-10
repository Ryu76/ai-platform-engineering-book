# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 학습 목표·필요성·핵심 이론·환경 설정 초안
- 완료 선언: 아직 하지 않음. Volume 01의 최초 호출, 파라미터, Streaming, 오류 처리, 비용·사용량, CLI 챗봇 및 미니 프로젝트가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/01-learning-objectives.md`
- `docs/volume01-llm-fundamentals/02-why-it-matters.md`
- `docs/volume01-llm-fundamentals/03-theory.md`
- `docs/volume01-llm-fundamentals/04-environment-setup.md`

위 문서는 하나의 동일한 AI 업무 처리 플랫폼의 출발점으로, 안전한 LLM 호출 경계(환경 변수, Timeout, Mock 검증)를 다음 실습 코드에서 구현하도록 연결합니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ uv run ruff check .
All checks passed!

$ uv run mypy src
Success: no issues found in 3 source files

$ uv run pytest
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\python\ai-platform-engineering-book
configfile: pyproject.toml
testpaths: tests
collected 1 item

tests\unit\test_settings.py .                                            [100%]

============================== 1 passed in 0.04s ==============================

$ uv run python scripts/validate_docs.py
문서 검증 통과: Volume 11개

$ uv run python scripts/validate_links.py
링크 검증 통과

$ uv run python scripts/validate_code_blocks.py
코드 블록 검증 통과

$ uv run python scripts/check_secrets.py
비밀값 검사 통과
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다.

## 알려진 차단 사항

- 없음. 실제 외부 LLM API 호출은 의도적으로 수행하지 않았습니다. 이후 테스트는 Mock 전송 계층을 사용하며, 라이브 호출은 학습자가 키를 설정하고 명시적으로 선택할 때만 수행합니다.

## 다음 작업

- Volume 01의 `05-first-call.md`를 작성하고, `src/ai_platform/llm/client.py`와 Mock 기반 최초 호출 테스트를 한 슬라이스로 구현합니다.
