# Volume 01 제작 진행 기록

## 현재 상태

- 마지막 완료 슬라이스: 03장 `LLM·Transformer·Token`을 초보자용 14개 장 구조로 확장하고, AI·ML·딥러닝·생성형 AI·LLM의 관계, Tokenizer, Transformer 개요, Context Window 예산과 오프라인 검증 경계를 문서화했다.
- 검증 근거: `tests/integration/test_volume01_completion_contract.py`의 03장 계약과 Volume 01 관련 단위·통합 테스트를 실행한다.
- 다음 작은 슬라이스: 04장 `환경 설정`의 동일한 장 구조, Windows/WSL 경로 및 `.env` 안전 경계를 출고 수준으로 보완한다.

## 완료 선언 정책

모든 PRD 필수 내용·실습·결과물의 Definition of Done과 권 단위 검증이 통과하기 전에는 `VOLUME01_COMPLETE=true`를 기록하지 않는다. 라이브 API 호출·실제 키·회사 데이터는 완료 검증에 사용하지 않는다.
