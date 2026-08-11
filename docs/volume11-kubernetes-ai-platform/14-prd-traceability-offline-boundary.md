# Volume 11 PRD 추적성: 오프라인 증거와 미완료 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- PRD의 Volume 11 필수 내용·필수 실습을 repository의 학습 artifact와 연결한다.
- local file, in-memory probe, render/config 검증이 제공하는 증거와 제공하지 않는 증거를 구분한다.
- 실행 금지 범위 때문에 아직 완료로 표시할 수 없는 실습을 `not verified`로 남긴다.
- `VOLUME11_COMPLETE=true`를 설정할 수 있는 조건과 현재 그 조건이 충족되지 않은 이유를 설명한다.

## 2. 이 장의 범위

이 문서는 PRD의 Volume 11 요구사항을 **추적하는 offline audit**입니다. 새 image, container, Secret, credential, listener, cluster resource, alert, backend 또는 deployment를 만들지 않습니다. 모든 Manifest의 이름과 이미지는 기존 `example.invalid` 또는 placeholder 값만 가리킵니다.

> [!WARNING]
> PRD의 Docker Compose 통합 실행, Kubernetes 로컬 환경 구성, Rolling Update, Rollback, 최종 AI Platform 배포는 실제 실행 상태를 확인해야 합니다. 이 작업의 범위는 container 실행, live cluster, deployment를 금지하므로 이 장이나 local test의 통과를 그 실습의 성공으로 해석하지 않습니다. 따라서 이 Volume은 아직 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 필수 내용 추적표

아래 표의 “local evidence”는 repository 안에서 읽거나 실행 가능한 작은 계약입니다. “운영 전 별도 evidence”는 이 Volume이 아직 만들지 않은 증거입니다.

| PRD 필수 내용 | Volume 11 local artifact | local evidence | 운영 전 별도 evidence |
|---|---|---|---|
| Dockerfile, multi-stage build, environment variable | `docker/volume11/Dockerfile`, `compose.health.yaml`, [01장](01-health-probes.md) | Dockerfile text와 Compose config가 runtime configuration 예제를 표현한다. | image build, SBOM/provenance, image scan, container execution |
| Docker Compose와 Qdrant·Redis·PostgreSQL | `docker/volume11/compose.dependencies.yaml`, [03장](03-compose-dependency-topology.md) | 네 placeholder image와 internal topology를 config/text로 확인한다. | image pull, service start, DNS, dependency connectivity, integrated API request |
| ConfigMap과 Secret 분리 | `k8s/volume11/configmap.yaml`, `secret.example.yaml`, [02장](02-configmap-dependency-readiness.md) | non-secret policy와 base set에서 제외된 Secret reference placeholder를 확인한다. | approved Secret value/reference, RBAC, workload injection |
| health check, readiness probe, liveness probe | `src/ai_platform/api/health.py`, `k8s/volume11/deployment.yaml`, [01장](01-health-probes.md) | in-memory `/livez`·`/readyz` 결과와 서로 다른 probe path를 확인한다. | Pod lifecycle, probe timing, traffic exclusion, restart behavior |
| logging, metrics, tracing, observability | `correlation.py`, `telemetry.py`, [09장](09-structured-correlation-logging-boundary.md), [10장](10-telemetry-data-minimization-exporter-failure.md) | allow-list correlation event와 low-cardinality process-local telemetry를 확인한다. | collector delivery, sampling, retention, access control, alert action |
| Pod, Deployment, Service, Ingress | `k8s/volume11/deployment.yaml`, `k8s/volume11/service.yaml`, `k8s/volume11/ingress.yaml`, [04장](04-ingress-http-boundary.md) | Kustomize render와 example image/host/service-port contract를 확인한다. | admission, scheduler, endpoints, DNS, TLS, Ingress controller |
| Job, CronJob, PVC, HPA | `k8s/volume11/batch/`, `k8s/volume11/storage/`, `k8s/volume11/autoscaling/`, [05장](05-job-cronjob-completion-retry.md)~[07장](07-hpa-cpu-scaling-boundary.md) | suspended batch, placeholder PVC, separate HPA target을 local render/text로 확인한다. | scheduler, storage binding, metrics pipeline, replica changes, cost |
| resource limit, Rolling Update, Rollback | `k8s/volume11/deployment.yaml`, [08장](08-rolling-update-rollback-boundary.md) | CPU/memory request·limit과 declared RollingUpdate/revision values를 확인한다. | workload capacity, image availability, migration compatibility, rollout/rollback effects |
| 장애 대응과 비용 관리 | [11장](11-incident-response-observability-cost-boundaries.md), [13장](13-preflight-checklist-glossary-handoff.md) | sample decision·owner·privacy/cost boundary를 읽는다. | live detection, impact classification, mitigation, recovery, on-call evidence |

## 4. 필수 실습 상태

| PRD 필수 실습 | 현재 offline artifact | 상태 | 완료로 표시하지 않는 이유 |
|---:|---|---|---|
| 1. API Docker 이미지 생성 | Dockerfile과 Compose build instruction | artifact only | image build를 실행하지 않았다. |
| 2. Qdrant, Redis, PostgreSQL 구성 | placeholder Compose topology | artifact only | real service/container를 만들지 않았다. |
| 3. Docker Compose 통합 실행 | `docker compose ... config --no-interpolate` | config verified | `docker compose up`을 실행하지 않았다. |
| 4. Health Check 구현 | in-memory WSGI demo와 unit test | local contract verified | containerized runtime probe는 확인하지 않았다. |
| 5. Kubernetes 로컬 환경 구성 | Kustomize local render | render verified | local cluster를 만들거나 연결하지 않았다. |
| 6~10. Deployment·Service·ConfigMap/Secret·Ingress·HPA | example/placeholder manifests | render or text verified | `apply`, controller, Secret, metrics pipeline을 사용하지 않았다. |
| 11~12. Rolling Update·Rollback | declared Deployment update contract | declaration verified | image revision, rollout, rollback을 실행하지 않았다. |
| 13~14. 로그 확인·장애 상황 재현 | in-memory logging/telemetry and decision docs | local contract verified | live log backend, alert, operational fault injection을 사용하지 않았다. |
| 15. 최종 AI Platform 배포 | 없음 | not verified | deployment가 명시적으로 금지되어 있다. |

`artifact only`, `config verified`, `render verified`, `local contract verified`, `not verified`는 성공·실패 등급이 아닙니다. 각각은 증거가 확인된 범위를 뜻하며 실제 운영 결과를 대체하지 않습니다.

## 5. Local review에 추가한 추적 항목

`src/ai_platform/api/operations_review.py`의 `artifact_checks`는 file read만으로 다음 교육용 경계를 함께 확인합니다.

- Deployment가 `example.invalid` image, 분리된 liveness/readiness probe, CPU·memory request/limit을 선언한다.
- base Kustomize set이 Secret example을 제외한다.
- Compose dependency topology가 placeholder image, internal network, host port 부재를 유지한다.
- Ingress가 `example.invalid` host를 사용한다.
- CronJob이 suspended 상태이며, PVC는 placeholder StorageClass를 쓰고 base set과 분리된다.
- HPA가 base Deployment와 다른 example target을 가리킨다.

이 check는 YAML parser, Docker daemon, Kubernetes API를 호출하지 않습니다. `true`는 정확한 local text contract가 존재한다는 뜻뿐입니다.

## 6. 실행과 확인

실행 위치는 **저장소 루트**입니다.

```bash
uv run python examples/volume11/local_operations_review_demo.py
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/unit/test_volume11_telemetry.py tests/integration/test_volume11_health_artifacts.py tests/integration/test_volume11_mini_project.py -q
```

첫 명령은 in-memory WSGI와 local file read만 수행합니다. 두 번째 명령은 Volume 11의 offline contract를 검증합니다. Docker Compose 통합 실행이나 cluster deployment를 수행하지 않습니다.

선택적으로 다음 명령은 resource를 만들지 않는 local 구성 검사입니다.

```bash
docker compose -f docker/volume11/compose.dependencies.yaml config --no-interpolate
kubectl kustomize k8s/volume11
kubectl kustomize k8s/volume11/batch
kubectl kustomize k8s/volume11/storage
kubectl kustomize k8s/volume11/autoscaling
```

## 7. 완료 판정과 인계

PRD Volume Definition of Done에는 전체 실습 재실행, 동작하는 mini project, 테스트, 학습자 checklist, glossary가 필요합니다. 이 Volume에는 local mini project, tests, checklist와 glossary가 있지만, 실제 Compose 통합 실행·Kubernetes local environment·update/rollback·final deployment라는 필수 실습의 evidence가 없습니다.

그러므로 현재 판정은 다음과 같습니다.

- local-only artifact와 test slice: **verified**
- PRD Volume Definition of Done: **not verified / incomplete**
- completion flag: **absent** (`VOLUME11_COMPLETE=true`를 추가하지 않음)

실행 제한이 해제되고 승인된 환경에서 필요한 실습을 실제로 검증한 뒤에만, 그 evidence를 별도 승인 기록과 연결해 PRD 완료 여부를 다시 판정합니다. 그 전에는 `unknown` 또는 `not verified`를 success claim으로 바꾸지 않습니다.

## 8. 핵심 정리

PRD 추적성은 artifact 존재 여부와 운영 성공을 같은 것으로 취급하지 않습니다. 이 Volume의 Docker, Kubernetes, observability artifact는 안전한 placeholder와 local contract를 학습시키며, 실제 Compose 통합·cluster lifecycle·update/rollback·deployment의 evidence는 의도적으로 남겨 둡니다. 이 구분을 유지하는 것이 안전한 완료 보고와 다음 인계의 출발점입니다.
