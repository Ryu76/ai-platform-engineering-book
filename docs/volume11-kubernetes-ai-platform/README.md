# Volume 11. Kubernetes 기반 AI 운영

## 목표

완성된 AI Platform을 컨테이너화하고 Kubernetes에서 운영하는 데 필요한 배포 객체, 상태 확인(health check), 설정 분리, 관찰성, 장애 대응을 단계적으로 익힙니다. 이 권의 모든 Manifest는 예제 이미지와 자리표시자만 사용합니다. 실제 Secret, 클러스터 접속 정보, 조직 리소스는 저장하지 않습니다.

## 장 목록

1. [Health Probe: liveness와 readiness를 분리하기](01-health-probes.md)
2. [ConfigMap과 의존성 readiness 정책 분리](02-configmap-dependency-readiness.md)
3. [Docker Compose 의존 서비스 토폴로지: 실행 전 경계 확인](03-compose-dependency-topology.md)
4. [Ingress HTTP 경계: Service로 안전하게 연결하기](04-ingress-http-boundary.md)
5. [Job과 CronJob: 완료·재시도·중복 실행 경계](05-job-cronjob-completion-retry.md)
6. [PVC: 수명 주기·접근 모드·보존 경계](06-pvc-lifecycle-access-retention.md)
7. [HPA: CPU 기반 확장 계약을 오프라인으로 읽기](07-hpa-cpu-scaling-boundary.md)
8. [Rolling Update와 Rollback: Deployment revision 경계 읽기](08-rolling-update-rollback-boundary.md)
9. [구조화된 request correlation logging: 관측 경계를 로컬에서 읽기](09-structured-correlation-logging-boundary.md)

## 현재 실습 경계

첫 번째 실습은 외부 의존성이 없는 HTTP 상태 확인 API와 Docker/Kubernetes 예제 Manifest를 다룹니다. 두 번째 실습은 ConfigMap의 비밀 없는 readiness 정책, 주입 가능한 의존성 검사 경계, 적용하지 않는 Secret 자리표시자 예제를 추가합니다. 세 번째 실습은 API, Qdrant, Redis, PostgreSQL의 Compose 토폴로지를 모든 이미지가 자리표시자인 정적 구성으로 해석합니다. 네 번째 실습은 예제 도메인과 IngressClass 자리표시자로 HTTP 경계를 Service의 명명된 포트에 연결합니다. 다섯 번째 실습은 `example.invalid` 이미지와 `suspend: true`를 사용해 Job/CronJob의 완료·재시도·중복 실행 경계를 Kustomize 로컬 렌더링과 오프라인 테스트로만 검토합니다. 여섯 번째 실습은 `example-storage-class` 자리표시자 PVC를 기본 집합과 분리해 수명 주기·접근 모드·보존 책임을 읽습니다. 일곱 번째 실습은 존재하지 않는 `ai-platform-api-example` target과 CPU 70% 목표를 기본 집합과 분리해 HPA 확장 계약만 로컬로 읽습니다. 여덟 번째 실습은 기본 API 예제 Deployment의 `RollingUpdate`·revision 보존·진행 기한 계약을 로컬 렌더링으로만 읽고, 실제 이미지 교체·rollout·rollback은 수행하지 않습니다. 아홉 번째 실습은 allow-list `X-Request-ID`와 서버 생성 ID를 응답·구조화된 완료 로그에만 연결하고, telemetry backend·exporter·metric endpoint·실제 요청은 사용하지 않습니다. 이후 장에서 metrics·tracing 경계, 장애 대응과 비용 관리를 추가합니다.

- 실행 예제: `examples/volume11/health_probe_demo.py`, `examples/volume11/dependency_readiness_demo.py`, `examples/volume11/correlation_logging_demo.py`
- API 코드: `src/ai_platform/api/health.py`, `src/ai_platform/api/dependencies.py`, `src/ai_platform/api/correlation.py`, `src/ai_platform/api/server.py`
- 컨테이너 예제: `docker/volume11/Dockerfile`, `docker/volume11/compose.health.yaml`, `docker/volume11/compose.dependencies.yaml`
- Kubernetes 예제: `k8s/volume11/` (기본 Kustomize 집합의 Ingress, 적용하지 않는 `secret.example.yaml`, 별도 로컬 렌더링 집합 `batch/`의 Job·CronJob, `storage/`의 placeholder PVC 및 `autoscaling/`의 placeholder target HPA 포함)
- 작업 이력: [PROGRESS.md](PROGRESS.md)
