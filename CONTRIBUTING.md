# 기여 가이드

변경 전 `PRD.md`와 해당 Volume의 README를 읽습니다. 문서는 한국어로 작성하고, 모든 명령은 실행 위치·목적·정상 결과·오류 확인 방법을 포함합니다.

Python 검증은 교재 전용 Anaconda Conda 환경에서만 실행합니다. 환경 생성 방법은 [Anaconda 환경 설정](docs/setup/anaconda.md)을 따릅니다.

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
conda activate ai-platform-engineering-book
ruff check .
mypy src
pytest -q
python scripts/validate_docs.py
python scripts/check_secrets.py
```

실제 키, 개인정보, 비공개 문서를 커밋하지 않습니다.
