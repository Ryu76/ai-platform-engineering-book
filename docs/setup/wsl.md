# WSL2와 Ubuntu 설정

```bash
# 실행 위치: WSL Ubuntu 터미널
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl
mkdir -p ~/projects
```
`/mnt/c/...`는 Windows 디스크 경로입니다. 성능과 권한 문제를 줄이려면 소스는 WSL 홈 디렉터리에 두는 것을 권장합니다.
