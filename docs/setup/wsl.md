# WSL2와 Ubuntu 설정

WSL2는 이 교본에서 Docker, Kubernetes, `kubectl`, kind/minikube를 실행할 때만 사용합니다.
Python 예제·테스트·Ruff·mypy는 Windows의 [Anaconda Conda 환경](anaconda.md)에서 실행합니다.
Windows Anaconda 환경을 WSL 안에서 활성화하거나, WSL의 `apt` Python·`venv`·`uv`를 교재 실습에 섞지 마세요.

```bash
# 실행 위치: WSL Ubuntu 터미널
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl
mkdir -p ~/projects
```

`/mnt/c/...`는 Windows 디스크 경로입니다. 컨테이너 소스 마운트 성능과 권한 문제가 생기면 Docker/Kubernetes용 파일만 WSL 홈으로 복사해 사용하고, Python 환경의 기준은 계속 Windows Conda로 유지합니다.

다음 단계는 [Docker Desktop 설정](docker.md)이며, Python 학습으로 돌아갈 때는 Anaconda PowerShell Prompt에서 `conda activate ai-platform-engineering-book`를 실행합니다.
