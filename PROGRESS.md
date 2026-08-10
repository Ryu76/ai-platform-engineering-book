# 작업 진행 기록

## 현재 상태

- 현재 Phase: **Phase 2 — Volume 01 LLM 기초**
- 이번 슬라이스: Volume 01의 **미니 프로젝트**로 오프라인 안전 CLI 챗봇 실행 안내와 별도 프로세스 기반 통합 테스트를 추가했습니다.
- 완료 선언: 아직 하지 않음. Volume 01의 과제·핵심 정리·Volume 완료 검수가 남아 있습니다.

## 이번에 완료한 파일

- `docs/volume01-llm-fundamentals/11-mini-project.md`
  - Volume 01의 설정·완료 요청·오류 처리·사용량 계약·대화 이력을 하나의 안전한 CLI 챗봇으로 연결하는 한국어 미니 프로젝트 문서를 작성했습니다.
  - 실행 위치가 명시된 오프라인 실행, 통합 테스트, 전체 품질 검사, 코드 설명, 정상 결과, 오류 해결, 응용 실습, 과제, 체크리스트를 포함했습니다.
  - 기본 라이브 모드와 `--offline-demo`의 외부 전송 경계를 분리하고, 검증은 API 키·네트워크 없이 수행하도록 안내했습니다.
- `tests/integration/test_volume01_chat_cli.py`
  - `sys.executable`로 `examples/volume01/chat_cli.py --offline-demo`를 별도 프로세스에서 실행합니다.
  - 질문·`/exit` 표준 입력, 시작 안내·결정론적 데모 응답·로컬 종료 문구, 종료 코드 0, 빈 표준 오류를 외부 API 없이 검증합니다.
  - 10초 제한으로 종료 경로의 무한 대기를 감지합니다.
- `docs/volume01-llm-fundamentals/README.md`
  - 11장 미니 프로젝트 링크를 추가하고 과제·핵심 정리의 후속 순서를 갱신했습니다.

이 슬라이스는 기존 `ConversationHistory`, `run_chat_loop()`, `OfflineDemoClient`를 변경하지 않았습니다. 검증은 `--offline-demo`만 실행했으므로 실제 LLM API 호출·외부 데이터 전송·비용·배포는 수행하지 않았습니다.

## 검증 기록

실행 위치: `E:\python\ai-platform-engineering-book`

```text
$ printf 'AI Platform이란 무엇인가요?\n/exit\n' | uv run python examples/volume01/chat_cli.py --offline-demo
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> AI> 오프라인 데모 응답: 'AI Platform이란 무엇인가요?' 요청을 기록했습니다.
사용자> 대화를 마칩니다.

$ uv run pytest tests/integration/test_volume01_chat_cli.py -q
.                                                                        [100%]
1 passed in 0.60s

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
collected 56 items

tests\integration\test_volume01_chat_cli.py .                            [  1%]
tests\unit\test_chat.py ........                                         [ 16%]
tests\unit\test_llm_client.py ................................           [ 73%]
tests\unit\test_settings.py ..                                           [ 76%]
tests\unit\test_usage.py .............                                   [100%]

============================= 56 passed in 0.78s ==============================

$ git diff --check
(exit 0)
```

> [!NOTE]
> 모든 `uv run` 명령은 Hermes 활성 가상환경과 프로젝트 `.venv` 경로가 다르다는 경고를 출력했지만, 프로젝트 `.venv`를 사용해 정상 종료했습니다. 실제 외부 LLM API 호출·배포·데이터 전송은 수행하지 않았습니다.

## 알려진 차단 사항

- 없음. 라이브 모드는 입력을 선택한 제공자에 전송하고 비용이 발생할 수 있으므로, 학습·CI 검증에는 `--offline-demo`와 Mock/통합 테스트를 사용합니다.

## 다음 작업

- Volume 01의 학습 과제 문서를 한국어로 추가하고, 각 과제가 기존 오프라인 테스트 경계와 연결되는지 검증하는 한 개의 작은 문서 슬라이스를 구현합니다.
