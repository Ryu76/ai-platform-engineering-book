# Windows 사전 준비

## 목적

이 교본의 Python 실습은 **Windows Anaconda Distribution**에서 실행합니다. WSL2는 Docker·Kubernetes가 필요한 뒤쪽 Volume에서만 사용합니다.

## 1. Anaconda 설치와 확인

Anaconda Distribution을 설치한 뒤 시작 메뉴에서 **Anaconda PowerShell Prompt**를 엽니다.

```powershell
# 실행 위치: Anaconda PowerShell Prompt
conda --version
conda info --base
```

두 명령이 버전과 Anaconda 설치 경로를 출력하면 준비됐습니다. 일반 PowerShell, Git Bash, WSL 터미널에서 Python 패키지를 별도로 설치하지 마세요.

## 2. 선택: WSL2와 Docker Desktop

Kubernetes 실습을 진행할 때만 PowerShell을 **관리자 권한**으로 열어 다음을 실행합니다.

```powershell
# 실행 위치: Windows PowerShell 관리자 권한
wsl --install
```

재부팅 후 Ubuntu를 초기 설정합니다. 이 교본에서는 WSL에 Python/Conda 환경을 별도로 만들지 않고, Docker·kubectl·kind 같은 컨테이너 도구만 WSL에서 사용합니다.

## 다음 단계

[Anaconda 환경 설정](anaconda.md)에서 교재 전용 Conda 환경을 만든 뒤 Volume 01을 시작합니다.

> [!WARNING]
> API 키를 PowerShell 기록, Git 설정, 소스 코드, 채팅 메시지에 넣지 마세요.
