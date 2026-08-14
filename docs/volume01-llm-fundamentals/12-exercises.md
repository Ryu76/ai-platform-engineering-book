# 과제: 외부 전송 없이 LLM 실행 경계 점검하기

## 1. 학습 목표

이 과제를 마치면 Volume 01의 오프라인 데모, Mock 단위 테스트, 별도 프로세스 통합 테스트가 각각 무엇을 검증하는지 구분할 수 있습니다. 또한 API 키·네트워크 없이 CLI 챗봇의 입력, 응답, 종료, 오류 처리 경계를 재현 가능하게 확인할 수 있습니다.

## 2. 왜 필요한가

LLM 기능은 모델 응답만 맞는다고 안전한 것이 아닙니다. 빈 입력이나 종료 명령이 제공자로 전송되면 비용과 로그가 불필요하게 생길 수 있습니다. 오류 메시지에 원본 예외를 그대로 출력하면 키나 내부 정보가 노출될 수도 있습니다.

이 과제는 다음 Volume의 Prompt와 Tool을 붙이기 전에 현재 사용자 입구의 안전 계약을 스스로 확인하게 합니다. 모든 검증은 기존 [안전한 CLI 챗봇](10-cli-chatbot.md)과 [미니 프로젝트](11-mini-project.md)의 오프라인 경계를 재사용합니다.

## 3. 핵심 개념

**Mock 단위 테스트**는 `ScriptedClient`처럼 외부 클라이언트를 메모리 객체로 바꾸어 한 함수의 분기를 검사합니다. **통합 테스트**는 실제 Python 프로세스로 CLI를 실행하여 시작, 표준 입력, 출력, 종료가 이어지는지 확인합니다. 둘 다 `--offline-demo` 또는 Mock만 사용하므로 모델 제공자에 요청하지 않습니다.

과제의 답안은 문서로 정리해도 되지만, 검증 명령은 실제로 실행해야 합니다. 결과에 API 키, 회사 문서, 개인정보, 라이브 응답을 복사하지 않습니다.

> [!WARNING]
> 기본 모드의 `chat_cli.py`는 설정이 존재하면 선택한 제공자에 입력을 전송할 수 있습니다. 이 과제에서는 `--offline-demo` 없는 실행과 `.env` 작성이 필요하지 않습니다. 키가 있더라도 터미널 출력, 과제 파일, Git 커밋에 넣지 않습니다.

## 4. 동작 구조

```text
과제 명령 또는 학습자 변경
           │
           ├── 단위 경계 ──► tests/unit/test_chat.py
           │                 ScriptedClient / 외부 전송 없음
           │
           └── 통합 경계 ──► chat_cli.py --offline-demo
                             OfflineDemoClient / 외부 전송 없음
                                           │
                                           ▼
                              시작 · 질문 · 안전한 종료 확인
```

## 5. 실습 환경

다음 기존 파일을 수정 전 먼저 읽습니다.

- `src/ai_platform/llm/chat.py`: 대화 이력과 종료·오류 처리 계약입니다.
- `examples/volume01/chat_cli.py`: `--offline-demo` 선택 시 `OfflineDemoClient`를 사용합니다.
- `tests/unit/test_chat.py`: Mock으로 대화 루프의 분기를 검사합니다.
- `tests/integration/test_volume01_chat_cli.py`: 별도 프로세스에서 오프라인 CLI를 검사합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
conda env update --file environment.yml --prune
```

`conda env update --file environment.yml --prune`는 과제의 테스트 도구를 준비합니다. Windows에서 WSL을 사용한다면 Windows PowerShell 경로가 아니라 WSL 안의 저장소 경로에서 실행합니다.

## 6. 단계별 실습

### 6.1 기본 과제: 로컬 종료 경로 확인

아래 명령을 실행해 질문 하나와 `/quit`이 모두 로컬 오프라인 경로에서 처리되는지 확인합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
printf 'Token이란 무엇인가요?\n/quit\n' | python examples/volume01/chat_cli.py --offline-demo
```

출력에 `오프라인 데모 응답`과 `대화를 마칩니다.`가 있어야 합니다. `/quit` 자체에 대한 데모 응답이 없어야 합니다. 이 명령은 API 키를 읽지 않고 네트워크에 연결하지 않습니다.

### 6.2 응용 과제: Mock으로 실패 이력 분리 확인

기존 단위 테스트를 실행합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/unit/test_chat.py -q
```

`test_chat_loop_does_not_record_failed_turn_and_shows_safe_error`를 찾아 다음을 설명합니다.

1. 시간 초과가 난 첫 질문이 두 번째 제공자 요청에 포함되지 않는 이유
2. 원본 예외 문자열이 사용자 출력에 없어야 하는 이유
3. `ScriptedClient`가 실제 API 호출을 대체하는 방식

설명은 `reports/` 밖의 개인 학습 노트에 작성해도 됩니다. 저장소에 답안을 추가한다면 비밀값과 실제 대화 내용을 넣지 않습니다.

### 6.3 심화 과제: 프로세스 통합 경계 확인

기존 통합 테스트를 실행합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
pytest tests/integration/test_volume01_chat_cli.py -q
```

`tests/integration/test_volume01_chat_cli.py`의 `timeout=10`, `check=True`, `capture_output=True`가 각각 잡는 실패를 한 가지씩 적습니다. 이어서 질문을 `Context Window는 무엇인가요?`로 바꾼 별도 테스트를 작성하거나, 기존 테스트의 입력을 바꾸어도 시작 안내·오프라인 응답·종료 안내 검사가 유지되는지 확인합니다.

> [!TIP]
> 심화 변경을 저장소에 남긴다면 기존 통합 테스트의 핵심은 모델 답변의 품질이 아니라 외부 전송 없는 CLI 실행 계약이라는 점을 유지합니다. 제공자 SDK를 테스트에 추가하지 마십시오.

## 7. 코드 설명

기본 과제의 실행 파일은 인자를 먼저 읽고 `--offline-demo`일 때만 `OfflineDemoClient`를 `run_chat_loop()`에 전달합니다.

```python
arguments = parse_arguments()
if arguments.offline_demo:
    run_chat_loop(OfflineDemoClient())
    return
```

이 분기 뒤에는 `LlmSettings.from_environment()`가 호출되지 않습니다. 따라서 과제의 오프라인 실행은 키 누락 오류나 라이브 HTTP 요청과 독립적입니다.

통합 테스트는 현재 활성 Conda 환경의 Python을 사용해 위 실행 파일을 별도 프로세스로 시작합니다.

```python
result = subprocess.run(
    [sys.executable, str(CHAT_CLI), "--offline-demo"],
    input="AI Platform이란 무엇인가요?\n/exit\n",
    text=True,
    capture_output=True,
    check=True,
    timeout=10,
)
```

`check=True`는 종료 코드가 0이 아니면 실패하게 하고, `timeout=10`은 종료 명령이 동작하지 않아 무한 대기하는 회귀를 발견합니다. `capture_output=True`는 표준 출력의 안전한 안내 문구를 확인하게 합니다.

## 8. 정상 실행 결과

6.1의 출력은 다음과 유사합니다.

```text
AI 업무 처리 플랫폼 챗봇입니다. 종료하려면 /exit 또는 /quit을 입력하세요.
사용자> AI> 오프라인 데모 응답: 'Token이란 무엇인가요?' 요청을 기록했습니다.
사용자> 대화를 마칩니다.
```

6.2와 6.3의 정상 결과는 각각 다음과 유사합니다. 테스트 개수는 이후 과제 확장에 따라 달라질 수 있습니다.

```text
8 passed
1 passed
```

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `No module named ai_platform` | 저장소 밖에서 Python을 실행했거나 가상환경이 준비되지 않았습니다. | 저장소 루트에서 `conda env update --file environment.yml --prune` 뒤 활성 Conda 환경의 명령을 다시 실행합니다. |
| 제공자 설정 오류가 보임 | `--offline-demo`를 빼고 기본 모드를 실행했습니다. | 과제 명령에 `--offline-demo`가 있는지 확인합니다. `.env`나 API 키를 과제를 위해 추가하지 않습니다. |
| 통합 테스트가 시간 초과됨 | 종료 명령 입력 또는 루프의 종료 분기가 깨졌을 수 있습니다. | 입력 문자열에 `/exit\n` 또는 `/quit\n`이 있는지와 `is_exit_command()` 경로를 확인합니다. |
| 테스트 출력에 민감한 문자열이 보임 | 원본 예외나 실제 입력을 그대로 출력하도록 바꿨을 수 있습니다. | 안전한 고정 안내만 출력하도록 복원하고 `test_chat_loop_does_not_record_failed_turn_and_shows_safe_error`를 실행합니다. |
| 출력 줄 모양이 예시와 다름 | 파이프 입력에서는 프롬프트와 응답이 같은 줄에 붙을 수 있습니다. | 줄 위치 대신 시작 안내, 오프라인 응답, 종료 문구가 모두 있는지 확인합니다. |

## 10. 응용 실습

1. `/help`를 로컬 명령으로 설계합니다. 도움말에는 외부 전송 경고와 `/exit`, `/quit`만 표시하고, Mock 테스트로 `/help`가 `complete()`를 호출하지 않음을 검증합니다.
2. `ConversationHistory(max_turns=2)`에서 세 번 성공한 질문 뒤 네 번째 요청의 메시지 목록을 예상하고, `tests/unit/test_chat.py`의 Mock 패턴으로 검증합니다.
3. 통합 테스트에 `/quit` 전용 테스트를 추가합니다. API 키, 환경 파일, 네트워크 라이브러리 없이 종료 코드 0과 종료 문구를 확인합니다.

## 11. 실무 적용

CI에서는 제공자 계정이나 네트워크 상태가 아닌 재현 가능한 계약을 먼저 검사해야 합니다. Mock은 오류와 이력 정책을 빠르게 확인하고, 오프라인 통합 테스트는 실행 경로와 패키징 경계를 확인합니다. 실제 모델 품질, 비용, 인용 정확도는 나중에 별도의 승인된 평가 환경에서 측정합니다.

다음 Volume에서는 이 CLI 입구에 Prompt 템플릿과 입력 검증을 연결합니다. 그때도 사용자 입력과 외부 문서는 신뢰되지 않은 데이터로 취급하고, 시스템 지시문이나 Tool 권한과 섞지 않습니다.

## 12. 과제

- **기본:** 6.1을 실행하고 `/quit`이 LLM 요청이 아닌 로컬 종료라는 근거를 출력과 코드 분기로 설명합니다.
- **응용:** 6.2의 Mock 테스트에서 실패한 턴을 이력에 저장하면 생길 문맥·보안 문제를 두 가지 작성합니다.
- **심화:** 6.3의 통합 테스트에 `/quit` 경로를 추가하고, 실제 API·키·네트워크 없이 실행된다는 테스트 근거를 제출합니다.

## 13. 완료 체크리스트

- [ ] `--offline-demo`로 기본 과제를 실행했고, API 키를 설정하지 않았다.
- [ ] `/quit`이 데모 응답 없이 로컬 종료됨을 확인했다.
- [ ] `tests/unit/test_chat.py`를 실행해 Mock 경계를 확인했다.
- [ ] `tests/integration/test_volume01_chat_cli.py`를 실행해 별도 프로세스 경계를 확인했다.
- [ ] 오류 출력에 원본 예외·API 키·전체 사용자 입력을 넣지 않았다.
- [ ] 라이브 호출 없이도 CLI의 시작·입력·응답·종료 계약을 검증할 수 있음을 설명할 수 있다.

## 14. 핵심 정리

이 과제는 LLM의 답변을 외부 제공자에 맡기지 않고도 프로그램의 안전한 실행 경계를 검증합니다. Mock은 이력과 오류 분기를, `--offline-demo` 통합 테스트는 실제 CLI 프로세스의 시작과 종료를 확인합니다. 이 경계는 다음 Volume에서 Prompt 기능을 추가할 때도 유지해야 할 회귀 방지 장치입니다.
