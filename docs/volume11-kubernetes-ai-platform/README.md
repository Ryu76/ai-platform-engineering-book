# Volume 11. Kubernetes 기반 AI 운영

## 목표

완성된 AI Platform을 컨테이너화하고 Kubernetes에서 운영하는 데 필요한 배포 객체, 상태 확인(health check), 설정 분리, 관찰성, 장애 대응을 단계적으로 익힙니다. 이 권의 모든 Manifest는 예제 이미지와 자리표시자만 사용합니다. 실제 Secret, 클러스터 접속 정보, 조직 리소스는 저장하지 않습니다.

## 장 목록

1. [Health Probe: liveness와 readiness를 분리하기](01-health-probes.md)
2. [ConfigMap과 의존성 readiness 정책 분리](02-configmap-dependency-readiness.md)

## 현재 실습 경계

첫 번째 실습은 외부 의존성이 없는 HTTP 상태 확인 API와 Docker/Kubernetes 예제 Manifest를 다룹니다. 두 번째 실습은 ConfigMap의 비밀 없는 readiness 정책, 주입 가능한 의존성 검사 경계, 적용하지 않는 Secret 자리표시자 예제를 추가합니다. 이후 장에서 Compose 의존 서비스, Ingress, Job/CronJob, PVC, HPA, Rolling Update/Rollback, 관찰성 및 장애 대응을 추가합니다.

- 실행 예제: `examples/volume11/health_probe_demo.py`, `examples/volume11/dependency_readiness_demo.py`
- API 코드: `src/ai_platform/api/health.py`, `src/ai_platform/api/dependencies.py`, `src/ai_platform/api/server.py`
- 컨테이너 예제: `docker/volume11/Dockerfile`, `docker/volume11/compose.health.yaml`
- Kubernetes 예제: `k8s/volume11/` (기본 Kustomize 집합과 적용하지 않는 `secret.example.yaml` 포함)
- 작업 이력: [PROGRESS.md](PROGRESS.md)
