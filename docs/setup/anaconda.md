# Anaconda 환경 설정 (공식 경로)

이 교본의 Python 실습은 **Windows용 Anaconda Distribution의 `conda` 환경만** 공식 지원합니다.
`uv`, 프로젝트 `.venv`, 시스템 Python을 섞지 마세요. Docker·Kubernetes 명령에는 WSL을 쓸 수 있지만,
Python 예제·테스트·정적 검사는 Windows Anaconda Prompt 또는 Anaconda PowerShell Prompt에서 실행합니다.

## 1. 사전 확인

Anaconda Prompt를 열고 저장소 루트로 이동합니다.

```powershell
# 실행 위치: Anaconda PowerShell Prompt
conda --version
conda info --envs
Set-Location E:\python\ai-platform-engineering-book
```

`conda --version`이 출력되고 `Set-Location` 뒤 `environment.yml`, `pyproject.toml`이 보여야 합니다.

## 2. 교재 전용 환경 생성

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
conda env create --file environment.yml
conda activate ai-platform-engineering-book
python --version
python -c "import ai_platform; print('ai_platform import: OK')"
```

- 환경 이름은 `ai-platform-engineering-book`입니다.
- `environment.yml`은 Python 3.12, Pydantic, pytest, Ruff, mypy와 현재 저장소의 editable package를 함께 설치합니다.
- 정상이라면 Python 3.12 계열 버전과 `ai_platform import: OK`가 출력됩니다.

이미 만든 환경을 의존성 정의에 맞춰 갱신할 때만 다음 명령을 실행합니다.

```powershell
# 실행 위치: 저장소 루트의 Anaconda PowerShell Prompt
conda activate ai-platform-engineering-book
conda env update --file environment.yml --prune
```

## 3. 매 학습 세션의 시작·종료

```powershell
# 시작: Anaconda PowerShell Prompt
Set-Location E:\python\ai-platform-engineering-book
conda activate ai-platform-engineering-book

# 확인: API 키·네트워크 없이 전체 검증
.\scripts\run_all_tests.ps1

# 개별 도구만 확인하려면
pytest -q
ruff check .
mypy src

# 종료
conda deactivate
```

`conda activate`를 하지 않았다면 `python`, `pytest`, `ruff`, `mypy`를 실행하지 마세요.
환경이 잘못되면 시스템 Python에 패키지를 설치하지 말고, 먼저 `conda info --envs`와 `where python`을 확인합니다.

## 4. API 키는 나중에, 오프라인 실습부터

Volume 01~10의 기본 실습은 API 키 없이 동작합니다. 실습 전에 `.env`를 만들 필요가 없습니다.
라이브 API 호출 장에서만 `.env.example`을 `.env`로 복사한 뒤 **자신의 컴퓨터 안에서만** 값을 설정합니다.
`.env`와 키는 Git, 채팅, 스크린샷, 테스트 출력에 넣지 않습니다.

## 5. 자주 발생하는 문제

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `conda: command not found` | Anaconda Prompt가 아닌 일반 터미널일 수 있습니다. | 시작 메뉴에서 **Anaconda PowerShell Prompt**를 열고 다시 실행합니다. |
| `EnvironmentNameNotFound` | 환경 생성 전이거나 이름이 틀렸습니다. | 저장소 루트에서 `conda env create --file environment.yml`을 실행합니다. |
| `No module named ai_platform` | 환경이 활성화되지 않았거나 editable 설치가 누락됐습니다. | `conda activate ai-platform-engineering-book` 뒤 `conda env update --file environment.yml --prune`를 실행합니다. |
| Python이 3.12가 아님 | 다른 Python/Conda 환경이 선택됐습니다. | `conda deactivate` 후 `conda activate ai-platform-engineering-book`, `python --version`으로 재확인합니다. |
| solver 오류 | 오래된 channels/cache 또는 네트워크 문제입니다. | `conda clean --index-cache` 후 환경 생성 명령을 재시도하고, 해결되지 않으면 오류 전문을 보존합니다. |

## 6. VS Code와 WSL의 역할

VS Code에서는 `Python: Select Interpreter`로 `ai-platform-engineering-book` Conda 환경의 Python을 선택합니다.
WSL은 Docker·Kubernetes 도구를 실행할 때만 사용하며, Windows Anaconda 환경을 WSL 안에서 활성화하거나
WSL의 Python 패키지와 혼합하지 않습니다.
