# VS Code와 Anaconda Conda 환경

VS Code에서는 교재를 일반 Windows 창으로 열고, Python 인터프리터를 교재 전용 Conda 환경으로 고정합니다.
WSL Remote 창을 Python 실습에 사용하지 마세요.

## 1. 프로젝트 열기

```powershell
# 실행 위치: Anaconda PowerShell Prompt, 저장소 루트
conda activate ai-platform-engineering-book
code .
```

## 2. 인터프리터 선택

1. `Ctrl+Shift+P` → **Python: Select Interpreter**를 엽니다.
2. `Conda: ai-platform-engineering-book (Python 3.12)`를 선택합니다.
3. VS Code 통합 터미널에서 아래를 확인합니다.

```powershell
python --version
python -c "import ai_platform; print('OK')"
```

Python 3.12 계열과 `OK`가 출력되면 준비됐습니다. 목록에 환경이 없으면 VS Code를 종료한 뒤 Anaconda Prompt에서 `conda activate ai-platform-engineering-book`를 확인하고 다시 엽니다.
