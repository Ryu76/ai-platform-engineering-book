# Docker Desktop과 WSL 연동

Docker Desktop에서 **Use WSL 2 based engine**과 Ubuntu 배포판 WSL Integration을 활성화합니다.

```bash
# 실행 위치: WSL Ubuntu 터미널
docker version
docker run --rm hello-world
```
Client와 Server 정보가 출력되면 연동이 정상입니다.
