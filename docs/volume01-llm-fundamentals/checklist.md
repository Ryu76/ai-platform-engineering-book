# Volume 01 학습자·제작 검수 체크리스트

## 1. 목적

이 체크리스트는 Volume 01을 학습한 뒤 다음 Volume으로 넘어가기 전에 사용합니다. 체크 표시는 학습자가 실제로 실행하고 확인한 뒤 직접 표시합니다. 문서가 존재한다는 사실과 학습자가 이해했다는 사실은 다르므로, 테스트 통과만으로 학습 항목을 자동 완료하지 않습니다.

## 2. 권의 연결 구조

```text
환경 변수와 안전한 설정
          │
          ▼
LLM Client ──► Streaming · 오류 처리 · 사용량
          │
          ▼
오프라인 CLI 챗봇 ──► Volume 02 Prompt 템플릿과 입력 검증
```

이 권의 CLI 입구(`examples/volume01/chat_cli.py`)는 이후 Prompt, Tool, RAG, Router를 연결할 공통 경계입니다. 학습자는 라이브 호출보다 먼저 오프라인 실행과 Mock 테스트를 재현해야 합니다.

## 3. 학습자 완료 체크리스트

### 3.1 개념

- [ ] 생성형 AI, LLM, Token, Tokenizer의 관계를 설명할 수 있다.
- [ ] Context Window 안에서 입력 토큰과 출력 토큰이 함께 예산을 쓴다는 점을 설명할 수 있다.
- [ ] System, User, Assistant 메시지의 역할을 구분할 수 있다.
- [ ] Temperature, Top-p, 최대 출력 토큰, Stop Sequence가 결과와 비용에 미치는 영향을 설명할 수 있다.
- [ ] 모델의 학습 지식, 현재 정보, Hallucination 위험을 구분할 수 있다.

### 3.2 환경과 보안

- [ ] 저장소 루트에서 `uv sync --all-groups`를 실행했다.
- [ ] `.env.example`만 공유하고 `.env`와 실제 API 키를 Git에 넣지 않는 이유를 설명할 수 있다.
- [ ] 라이브 호출은 입력을 선택한 제공자에 전송하고 비용을 만들 수 있음을 이해한다.
- [ ] 테스트와 과제에 회사 문서, 개인정보, 실제 키를 넣지 않았다.

### 3.3 실행과 검증

- [ ] `printf 'Token이란 무엇인가요?\n/exit\n' | uv run python examples/volume01/chat_cli.py --offline-demo`를 실행했다.
- [ ] `--offline-demo`가 API 키와 네트워크 없이 결정론적으로 실행됨을 확인했다.
- [ ] `uv run pytest tests/unit/test_llm_client.py -q`로 Mock 기반 Client 계약을 확인했다.
- [ ] `uv run pytest tests/unit/test_chat.py -q`로 빈 입력·안전한 오류·이력 경계를 확인했다.
- [ ] `uv run pytest tests/integration/test_volume01_chat_cli.py -q`로 별도 프로세스 CLI를 확인했다.
- [ ] `bash scripts/run_all_tests.sh`를 실행하고 실패가 없음을 확인했다.

## 4. 제작 검수 결과와 근거

다음은 저장소 제작자가 확인할 수 있는 결과물 목록입니다. 학습자의 체크 표시와 달리, 파일 존재와 오프라인 회귀 검증 경로를 확인하는 기준입니다.

- [x] Volume README가 13개 학습 문서와 이 체크리스트를 연결한다.
- [x] 설정·Client·사용량·대화 이력 코드가 `src/ai_platform/` 아래에 있다.
- [x] `examples/volume01/chat_cli.py --offline-demo`와 단위·통합 테스트 경로가 있다.
- [x] 미니 프로젝트와 기본·응용·심화 과제가 있다.
- [x] [용어집](../glossary.md)에 Volume 01 주요 용어가 있다.
- [x] 다음 권의 [Volume 02. Prompt Engineering](../volume02-prompt-engineering/README.md)으로 인계할 안전 경계를 명시했다.
- [x] 각 장의 전체 Definition of Done과 권 단위 재실행 결과를 출고 감사에서 확인했다. `bash scripts/run_all_tests.sh`는 Ruff, mypy, 문서·링크·코드 블록·비밀값 검사 및 전체 pytest `88 passed`를 모두 통과했다.

> [!WARNING]
> 마지막 항목이 완료되기 전에는 이 체크리스트의 제작 검수 결과만으로 Volume 01 전체 완료를 선언하지 않습니다. `--offline-demo` 없는 기본 모드는 설정이 있으면 실제 제공자로 입력을 전송할 수 있으므로, 이 권의 CI와 반복 검증에는 사용하지 않습니다.

## 5. 다음 Volume으로의 인계

Volume 02에서는 이 권에서 만든 안전한 LLM Client와 CLI 입력 경계를 유지한 채 Prompt 템플릿, 구조화된 JSON 출력, 입력 검증, Prompt Injection 방어, 버전 비교 테스트를 추가합니다.

인계할 파일은 다음과 같습니다.

- `src/ai_platform/core/settings.py`: 환경 변수와 설정 검증 경계
- `src/ai_platform/llm/client.py`: Timeout·오류 분류가 있는 제공자 Client 경계
- `src/ai_platform/llm/chat.py`: System 메시지와 제한된 대화 이력
- `src/ai_platform/llm/usage.py`: 사용량과 비용 추정 자료형
- `examples/volume01/chat_cli.py`: 외부 전송 없는 CLI 회귀 경로

Volume 02에서 사용자 입력은 신뢰되지 않은 데이터로 다룹니다. 입력 문자열을 System 지시문, 파일 경로, Tool 권한과 직접 결합하지 않습니다.

## 6. 관련 문서

- [Volume 01 목차](README.md)
- [미니 프로젝트](11-mini-project.md)
- [오프라인 경계 과제](12-exercises.md)
- [핵심 정리](11-summary.md)
- [Volume 02 시작](../volume02-prompt-engineering/README.md)
