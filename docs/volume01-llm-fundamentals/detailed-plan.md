# Volume 01 상세 작업 계획

## 생성 파일
- `src/ai_platform/core/settings.py`
- `src/ai_platform/llm/client.py`
- `examples/volume01/chat_cli.py`
- `tests/unit/test_settings.py`
- `tests/unit/test_llm_client.py`

## 이론 범위
AI와 생성형 AI의 관계, Transformer 개요, Token·Context Window, System/User/Assistant 메시지, Temperature·Top-p·최대 출력 토큰, Hallucination, Streaming, 사용량과 비용을 다룹니다.

## 실습 범위
1. Python 3.12와 uv 환경 구성
2. `.env`와 `.env.example`의 역할 분리
3. 설정 객체와 키 누락 오류 처리
4. Timeout이 있는 LLM Client 인터페이스
5. Mock 기반 최초 호출·Streaming·사용량 테스트
6. 간단한 CLI 챗봇

## 테스트 항목
- API 키 누락 시 키를 포함하지 않는 오류
- 모델명·Timeout 검증
- 성공·실패·재시도 불가 오류 분리
- 로그와 예외 메시지에 비밀값 미노출

## 완료 기준
초보자가 명령 위치를 따라 환경을 만들고, 실제 키 없이 테스트를 실행하며, 키가 있을 때만 명시적으로 라이브 호출을 선택할 수 있어야 합니다.
