# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **안전한 CLI 챗봇** 문서, 제한된 성공 대화 이력과 종료 명령·오류 안내를 갖춘 실행 코드, 외부 API 없는 오프라인 데모와 Mock 단위 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 미니 프로젝트·과제·핵심 정리와 Volume 완료 검수가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/10-cli-chatbot.md`
  - 대화 이력, 시스템·사용자·Assistant 메시지, 턴 한도, 로컬 종료 명령, 외부 전송 경고를 한국어로 설명했습니다.
  - 실행 위치가 있는 오프라인 데모·Mock 테스트·선택적 라이브 실행, 정상 결과, 오류 해결, 응용 실습, 과제, 체크리스트를 포함했습니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 10장 로컬 링크를 추가했습니다.
- `docs/glossary.md`
  - 대화 이력과 턴 용어를 추가했습니다.
- `src/ai_platform/llm/chat.py`
  - `ConversationHistory`는 시스템 메시지와 최근 성공 턴만 보관하고 가장 오래된 완료 쌍부터 제거합니다.
  - `run_chat_loop()`은 빈 입력, `/exit`·`/quit`, EOF·인터럽트, LLM 오류, 빈 응답을 안전하게 처리하며 실패한 입력은 기록하지 않습니다.
  - `ChatCompleter` Protocol을 통해 라이브 클라이언트와 Mock을 같은 실행 경계에 주입합니다.
- `examples/volume01/chat_cli.py`
  - 기본 모드는 환경 설정을 읽어 명시적으로 라이브 `LlmClient`를 만들고, `--offline-demo`는 API 키·외부 네트워크 없이 결정론적 응답을 제공합니다.
- `tests/unit/test_chat.py`
  - 이력 한도, 성공 이력 기록, 실패 이력 미기록, 빈 입력, EOF, 종료 명령, 비밀값 없는 오류 안내를 네트워크 없는 Mock으로 검증합니다.

이 슬라이스는 앞 장의 안전한 LLM 호출·오류·사용량 계약을 콘솔 대화로 연결합니다. 라이브 모드는 사용자가 명시적으로 실행할 때만 제공자에 입력을 전송할 수 있으며, 이번 검증에서는 오프라인 데모와 Mock만 사용했습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ printf 'RAG는 무엇인가요?\n/exit\n' | uv run python examples/volume01/chat_cli.py --offline-demo
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> AI> 오프라인 데모 응답: 'RAG는 무엇인가요?' 요청을 기록했습니다.
사용자> 대화를 마칩니다.

$ uv run python -m compileall -q src/ai_platform/llm/chat.py examples/volume01/chat_cli.py
(exit 0)

$ uv run pytest tests/unit/test_chat.py -q
........                                                                 [100%]
8 passed in 0.14s

$ bash scripts/run_all_tests.sh
All checks passed!
Success: no issues found in 7 source files
문서 검증 통과: Volume 11개
링크 검증 통과
코드 블록 검증 통과
비밀값 검사 통과
============================= test session starts =============================
platform win32 -- Python 3.14.5, pytest-8.4.2, pluggy-1.6.0
rootdir: E:\python\ai-platform-engineering-book
configfile: pyproject.toml
testpaths: tests
collected 55 items

tests\unit\test_chat.py ........                                         [ 14%]
tests\unit\test_llm_client.py ................................           [ 72%]
tests\unit\test_settings.py ..                                           [ 76%]
tests\unit\test_usage.py .............                                   [100%]

============================= 55 passed in 0.24s ==============================

$ git diff --check
(exit 0)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다.

## 알려진 차단 사항

- 없음. 라이브 모드는 입력을 선택한 제공자에 전송하고 비용이 발생할 수 있으므로, 학습·CI 검증에는 `--offline-demo`와 Mock 테스트를 사용합니다.

## 다음 작업

- Volume 01의 미니 프로젝트·과제·핵심 정리 문서와 처음부터 실행하는 Volume 검수를 한 개의 작은 슬라이스로 구현합니다.
