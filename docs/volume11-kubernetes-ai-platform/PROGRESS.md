# Volume 11 진행 기록

> 상태: 진행 중. 이 권은 아직 PRD의 Volume Definition of Done을 충족하지 않았습니다. `VOLUME11_COMPLETE=true`는 설정하지 않습니다.

## 2026-08-11 — Slice 09: 구조화된 request correlation logging의 로컬 관측 경계

### 완료한 범위

- `src/ai_platform/api/correlation.py`에 표준 라이브러리만 쓰는 correlation 계약을 추가했습니다.
  - `X-Request-ID`는 영문·숫자로 시작하고 영문·숫자·`.`·`_`·`-`만 쓰는 1~64자 allow-list에 맞을 때만 수용합니다.
  - header가 없거나 형식이 맞지 않으면 안전한 UUID hex 기반 ID를 생성하며, 테스트용 factory도 안전한 값을 돌려주지 않으면 거절합니다.
  - 완료 이벤트는 `event`, `request_id`, 알려진 probe route 또는 `unmatched`, HTTP status code만 JSON으로 기록합니다.
  - query string, body, 임의 header, raw 미지 path, environment, dependency detail, exception text, endpoint, credential은 이벤트에 넣지 않습니다.
- `HealthApplication`이 응답의 `X-Request-ID`와 한 개의 `http_request_completed` 구조화 로그에 같은 ID를 사용하도록 확장했습니다.
  - `/livez`와 `/readyz`의 기존 liveness/readiness 계약은 유지했습니다.
  - trace exporter, metric endpoint, telemetry backend, network 연결 또는 cluster 동작은 추가하지 않았습니다.
- `examples/volume11/correlation_logging_demo.py` 및 Volume 11 단위·통합 테스트를 추가했습니다.
  - 메모리 WSGI 호출로 accepted, generated, malformed-header replacement를 보여 주며 TCP listener나 외부 backend를 열지 않습니다.
  - 테스트는 응답 header·JSON event 연결과 raw 입력 미기록을 검사합니다.
- [구조화된 request correlation logging: 관측 경계를 로컬에서 읽기](09-structured-correlation-logging-boundary.md) 장과 README를 추가·갱신했습니다.
  - 실제 telemetry 수집, privacy·retention·access control, metrics·tracing, alert와 incident 대응은 운영 전 검토 경계로 분리했습니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `uv run python examples/volume11/correlation_logging_demo.py` | 통과 — in-memory `/livez` 완료 이벤트 3개, 수용된 ID 1개와 생성·대체 ID 2개를 stdout에만 출력; TCP, backend, cluster 연결 없음 |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 24 passed |
| `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py` | 모두 통과 |
| `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — Ruff 전체 통과, mypy 12 source files 문제 없음, 전체 85 passed |
| `git diff --check` | 통과 |

### 남은 범위

- metrics·tracing의 데이터 최소화와 exporter 실패 경계 작성하기
- 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

예제 값과 로컬·메모리 기반 코드만 사용해 metric·trace 데이터 최소화와 exporter failure 경계를 설명하고, 실제 telemetry backend, endpoint, credential, cluster 연결 또는 deployment는 하지 않습니다.

## 2026-08-11 — Slice 08: Rolling Update·Rollback revision 계약의 오프라인 경계

### 완료한 범위

- 기본 `k8s/volume11/deployment.yaml`에 로컬 렌더링용 Deployment update 계약을 추가했습니다.
  - 기존 비실행용 `example.invalid/ai-platform-api:0.1.0` 이미지와 2개 replica는 유지했습니다.
  - `RollingUpdate` 전략에 `maxUnavailable: 0`, `maxSurge: 1`, `progressDeadlineSeconds: 120`, `revisionHistoryLimit: 2`만 선언했습니다.
  - restart annotation, Secret·토큰·암호·registry·cluster 주소, 실제 이미지 변경은 포함하지 않았습니다.
- [Rolling Update와 Rollback: Deployment revision 경계 읽기](08-rolling-update-rollback-boundary.md) 장을 작성했습니다.
  - Deployment strategy, revision 보존과 진행 deadline의 서로 다른 책임, readiness·capacity·migration·SLO가 YAML만으로 보장되지 않는 이유를 설명합니다.
  - `kubectl kustomize` 로컬 렌더링과 오프라인 테스트만 안내하며 `apply`, image 변경, rollout, `kubectl rollout undo`, cluster 연결을 명시적으로 제외합니다.
- Volume README와 통합 테스트를 갱신해 새 장 링크, example 이미지, Rolling Update 범위, revision/progress 경계와 비밀값·restart annotation 부재를 검사합니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `kubectl kustomize k8s/volume11` + Deployment update 경계 검사 | 통과 — Deployment 1개에 `RollingUpdate`, unavailable 0, surge 1, revision 2, deadline 120만 로컬 렌더링; HPA·Pod·ReplicaSet·revision·cluster 연결·리소스 생성 없음 |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 21 passed |
| `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py` | 모두 통과 |
| `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — Ruff 전체 통과, mypy 11 source files 문제 없음, 전체 82 passed |

### 남은 범위

- 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

예제 값과 로컬·메모리 기반 코드만 사용해 구조화된 request correlation logging과 관측 경계를 추가하고, 실제 telemetry backend, endpoint, credential, cluster 연결 또는 deployment는 하지 않습니다.

## 2026-08-11 — Slice 07: HPA CPU 확장 계약의 오프라인 경계

### 완료한 범위

- `k8s/volume11/autoscaling/`에 기본 API Kustomize 집합과 분리된 `autoscaling/v2` HPA 로컬 렌더링 집합을 추가했습니다.
  - HPA는 존재하지 않는 `Deployment/ai-platform-api-example`만 target으로 참조하며, 기본 Deployment `ai-platform-api`와 의도적으로 다릅니다.
  - `minReplicas: 2`, `maxReplicas: 5`, CPU `averageUtilization: 70`의 최소 확장 계약만 선언합니다.
  - Secret·토큰·암호·주소·이미지·metrics server 설정을 포함하지 않았고, 기본 `k8s/volume11/kustomization.yaml`에도 포함하지 않았습니다.
  - 따라서 로컬 렌더링은 HPA YAML 계약만 읽으며 metric 수집, 부하 생성, Deployment scale 또는 클러스터 연결을 만들지 않습니다.
- [HPA: CPU 기반 확장 계약을 오프라인으로 읽기](07-hpa-cpu-scaling-boundary.md) 장을 작성했습니다.
  - CPU utilization이 CPU request 대비 비율이라는 점, min/max replica가 capacity·비용·SLO를 보장하지 않는다는 점, metrics pipeline과 운영 전 검토 경계를 설명합니다.
  - `kubectl kustomize` 로컬 렌더링과 오프라인 테스트만 안내하며 `apply`, `create`, metrics server 설치, 실제 target 변경 및 클러스터 연결을 명시적으로 제외합니다.
- Volume README와 통합 테스트를 갱신해 새 장 링크, 예제 target, min/max 범위, CPU resource utilization target, Secret·인증 값 부재 및 기본 Kustomize 집합에서의 제외를 검사합니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `kubectl kustomize k8s/volume11/autoscaling` 및 `kubectl kustomize k8s/volume11` 경계 검사 | 통과 — autoscaling 출력에 `HorizontalPodAutoscaler` 1개와 placeholder target/2~5/CPU 70%만, 기본 출력에는 HPA 없음; 모두 로컬 렌더링이며 클러스터 연결·리소스 생성 없음 |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 20 passed |
| `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py` | 모두 통과 |
| `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — Ruff 전체 통과, mypy 11 source files 문제 없음, 전체 81 passed |
| `git diff --check` | 통과 |

### 남은 범위

- Rolling Update/Rollback 예제 작성하기
- 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

예제 이미지·자리표시자·로컬 렌더링만으로 Deployment의 Rolling Update 전략과 rollback 검토 경계를 추가하고, 실제 이미지 교체, rollout 실행, 클러스터 적용은 하지 않습니다.

## 2026-08-11 — Slice 06: PVC 수명 주기·접근 모드·보존의 오프라인 경계

### 완료한 범위

- `k8s/volume11/storage/`에 기본 API Kustomize 집합과 분리된 PVC 로컬 렌더링 집합을 추가했습니다.
  - PVC는 `example-storage-class` 비운영용 자리표시자, `ReadWriteOnce`, `Filesystem`, `1Gi` 요청만 선언합니다.
  - `volumeName`, data source, Secret 참조, CSI driver, 실제 StorageClass, `volumeMounts`를 포함하지 않았고, 기본 `k8s/volume11/kustomization.yaml`에도 포함하지 않았습니다.
  - 따라서 로컬 렌더링은 PVC 계약만 읽으며 실제 PV/PVC 바인딩, 프로비저닝, 데이터 기록, 클러스터 연결을 만들지 않습니다.
- [PVC: 수명 주기·접근 모드·보존 경계](06-pvc-lifecycle-access-retention.md) 장을 작성했습니다.
  - PVC·PV·StorageClass의 책임, RWO가 단일 Pod 보장이 아닌 단일 노드 접근 요청이라는 점, PVC 삭제와 backing storage 보존의 분리된 책임을 설명합니다.
  - `kubectl kustomize` 로컬 렌더링과 오프라인 테스트만 안내하며 `apply`, `create`, 실제 StorageClass·PV·데이터 사용을 명시적으로 제외합니다.
- Volume README와 통합 테스트를 갱신해 새 장 링크, placeholder StorageClass, 접근 모드·volume mode·용량 요청, Secret·인증 값 부재, 기본 Kustomize 집합에서의 제외를 검사합니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `kubectl kustomize k8s/volume11/storage` 및 `kubectl kustomize k8s/volume11` 경계 검사 | 통과 — storage 출력에 PersistentVolumeClaim 1개와 placeholder/RWO/Filesystem/1Gi만, 기본 출력에는 PersistentVolumeClaim·Job·CronJob 없음; 모두 로컬 렌더링이며 클러스터 연결·리소스 생성 없음 |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 19 passed |
| `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py` | 모두 통과 |
| `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — Ruff 전체 통과, mypy 11 source files 문제 없음, 전체 80 passed |
| `git diff --check` | 통과 |

### 남은 범위

- HPA와 Rolling Update/Rollback 예제 작성하기
- 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

예제 이미지·자리표시자·로컬 렌더링만으로 HPA의 최소/최대 replica와 CPU 기반 확장 계약을 추가하고, 실제 metrics server, 부하 생성, 클러스터 적용은 하지 않습니다.

## 2026-08-11 — Slice 05: Job/CronJob 완료·재시도·중복 실행의 오프라인 경계

### 완료한 범위

- `k8s/volume11/batch/`에 기본 API Kustomize 집합과 분리된 `batch/v1` Job/CronJob 로컬 렌더링 집합을 추가했습니다.
  - Job은 `completions: 1`, `parallelism: 1`, `backoffLimit: 2`, `activeDeadlineSeconds: 120`, `restartPolicy: Never`, `ttlSecondsAfterFinished: 300`으로 완료·재시도·시간·정리 경계를 선언합니다.
  - CronJob은 예시 schedule을 읽을 수 있으나 `suspend: true`로 새 Job 생성을 막고, `concurrencyPolicy: Forbid`, 이력 제한, Job template의 재시도·시간 상한을 선언합니다.
  - 두 Manifest는 `example.invalid/ai-platform-maintenance:0.1.0` 자리표시자 이미지와 출력 전용 명령만 사용하며 Secret 참조, 환경 변수, 토큰, 암호, 연결 주소를 포함하지 않습니다.
  - 기본 `k8s/volume11/kustomization.yaml`에는 배치 리소스를 포함하지 않아 기존 API 집합의 로컬 렌더링과 분리합니다.
- [Job과 CronJob: 완료·재시도·중복 실행 경계](05-job-cronjob-completion-retry.md) 장을 작성했습니다.
  - Deployment와 Job 수명 주기, 재시도가 멱등성을 보장하지 않는 이유, suspend·동시성·보존 경계, 운영 승인 전 검토 항목을 설명합니다.
  - `kubectl kustomize`의 로컬 렌더링과 오프라인 테스트만 안내하며 `apply`, `create`, 실제 이미지, 클러스터 연결, 예약 활성화를 명시적으로 제외합니다.
- Volume README와 통합 테스트를 갱신해 새 장 링크, 별도 batch Kustomize 집합, placeholder 이미지, Job 완료·재시도 경계, CronJob suspend·중복 방지, Secret·인증 값 부재를 검사합니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `kubectl kustomize k8s/volume11/batch` 및 `kubectl kustomize k8s/volume11` 경계 검사 | 통과 — batch 출력에 Job·CronJob만, 기본 출력에는 Job·CronJob 없음; 모두 로컬 렌더링이며 클러스터 연결·리소스 생성 없음 |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 18 passed |
| `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — Ruff 전체 통과, mypy 11 source files 문제 없음, 전체 79 passed |
| `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py` | 모두 통과 |
| `git diff --check` | 통과 |

### 남은 범위

- PVC, HPA와 Rolling Update/Rollback 예제 작성하기
- 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

예제 이미지와 비밀 없는 Manifest만 사용해 PVC의 수명 주기·접근 모드·보존 경계를 로컬 렌더링·오프라인 테스트로 추가합니다. 실제 StorageClass, PVC 바인딩, 클러스터 적용은 하지 않습니다.


## 2026-08-10 — Slice 04: Ingress HTTP 경계와 Service backend의 오프라인 검증

### 완료한 범위

- `k8s/volume11/ingress.yaml`에 `networking.k8s.io/v1` 학습용 Ingress를 추가하고 기본 Kustomize 집합에 포함했습니다.
  - 호스트는 비실행용 `api.volume11.example.invalid`, IngressClass는 `example-ingress-class` 자리표시자만 사용합니다.
  - `/` `Prefix` 규칙은 `ai-platform-api` ClusterIP Service의 명명된 `http` 포트만 참조합니다.
  - TLS, `secretName`, 인증 값, 실제 DNS·IP·Controller annotation은 포함하지 않았습니다.
- [Ingress HTTP 경계: Service로 안전하게 연결하기](04-ingress-http-boundary.md) 장을 작성했습니다.
  - Ingress, Service, Controller, DNS/TLS의 책임 경계를 구분하고 `kubectl kustomize` 로컬 렌더링만 안내합니다.
  - `apply`, Controller 설치, DNS·인증서 구성과 실제 클러스터 연결은 명시적으로 범위에서 제외했습니다.
- Volume README와 통합 테스트를 갱신해 새 장 링크, 예제 IngressClass·호스트, Prefix backend, Service 포트 연결, TLS Secret·인증 값 부재를 검사합니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `kubectl kustomize k8s/volume11` + Ingress/예제 호스트/`http` 포트/Secret 부재 경계 검사 | 통과 — Namespace, ConfigMap, Service, Deployment, Ingress만 로컬 렌더링; 클러스터 연결·리소스 생성 없음 |
| `uv run ruff check src/ai_platform/api examples/volume11 tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py` | 통과 |
| `uv run mypy src/ai_platform/api` | 통과 — 4 source files, no issues |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 17 passed |
| `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py` | 모두 통과 |
| 전체 품질 게이트: `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — 78 passed |
| `git diff --check` | 통과 |

### 남은 범위

- Job/CronJob, PVC, HPA와 업데이트·롤백 예제 작성하기
- 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

예제 이미지와 비밀 없는 Manifest만 사용해 완료 보장·재시도 경계를 설명하는 Job/CronJob을 로컬 렌더링·오프라인 테스트로 추가합니다. 실제 클러스터에는 적용하지 않습니다.

## 2026-08-10 — Slice 03: Compose 의존 서비스 토폴로지의 실행 전 검증

### 완료한 범위

- `docker/volume11/compose.dependencies.yaml`에 API, Qdrant, Redis, PostgreSQL의 학습용 Compose 토폴로지를 추가했습니다.
  - 모든 이미지는 실행 불가능한 `example.invalid` 자리표시자입니다.
  - 의존 서비스 포트는 Compose 내부 `expose`로만 설명하고, 호스트 `ports`·인증 환경 변수·초기화 값은 포함하지 않았습니다.
  - 서비스는 `internal: true`인 `ai-platform-internal` 네트워크에만 선언했습니다.
  - API의 `depends_on: service_started`는 시작 순서일 뿐 readiness 보장이 아님을 명시했습니다.
- [Docker Compose 의존 서비스 토폴로지: 실행 전 경계 확인](03-compose-dependency-topology.md) 장을 작성했습니다.
  - `docker compose ... config --no-interpolate`만 실행하도록 하며 `up`, `pull`, `build`는 명시적으로 제외합니다.
  - Compose 토폴로지와 ConfigMap 기반의 오프라인 readiness 정책을 연결해 설명했습니다.
- Volume README와 통합 테스트를 갱신해 새 장의 링크, 자리표시자 이미지, 내부 네트워크, 호스트 포트·인증 값 부재를 검사합니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `docker compose -f docker/volume11/compose.dependencies.yaml config --no-interpolate` | 통과 — API, Qdrant, Redis, PostgreSQL 및 내부 네트워크만 로컬 렌더링; 컨테이너·이미지·네트워크·볼륨 미생성 |
| `uv run python examples/volume11/dependency_readiness_demo.py` | 통과 — 모든 필수 라벨 준비 시 `True`, Redis 미준비 시 `False` |
| `uv run ruff check src/ai_platform/api examples/volume11 tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py` | 통과 |
| `uv run mypy src/ai_platform/api` | 통과 — 4 source files, no issues |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 16 passed |
| `uv run python scripts/validate_docs.py`, `validate_links.py`, `validate_code_blocks.py`, `check_secrets.py` | 모두 통과 |
| 전체 품질 게이트: `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — 77 passed |
| `git diff --check` | 통과 |

### 남은 범위

- Ingress, Job/CronJob, PVC, HPA와 업데이트·롤백 예제 작성하기
- 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

예제 이미지와 비밀 없는 Manifest만 사용해 Ingress의 HTTP 경계와 기본 Service 연결을 로컬 렌더링·오프라인 테스트로 추가합니다. 실제 클러스터에는 적용하지 않습니다.

## 2026-08-10 — Slice 02: ConfigMap 정책과 의존성 readiness 경계

### 완료한 범위

- `src/ai_platform/api/dependencies.py`에 네트워크 연결·주소·인증 정보 없이 readiness 정책을 검증하는 코드를 추가했습니다.
  - ConfigMap 스타일 환경 변수의 논리적 의존성 이름은 중복 및 허용하지 않는 문자를 거절합니다.
  - `DependencyReadiness`는 주입된 검사 함수가 `False`를 반환하거나 예외를 던지면 not-ready를 반환합니다.
  - `/readyz`는 검사 예외를 상세 내용 없이 `503 Service Unavailable`으로 변환합니다. `/livez`의 독립성은 유지합니다.
- `examples/volume11/dependency_readiness_demo.py`와 Volume 11 단위·통합 테스트를 추가했습니다. 예제는 Qdrant·Redis·PostgreSQL 이름 라벨만 사용하며 포트·네트워크·컨테이너를 사용하지 않습니다.
- `k8s/volume11/configmap.yaml`에 비밀 없는 학습용 정책 라벨을 추가했고, `k8s/volume11/secret.example.yaml`에는 적용하지 않는 참조 자리표시자만 작성했습니다.
  - `secret.example.yaml`은 `kustomization.yaml`에 포함하지 않았습니다.
  - 실제 Secret, 접속 문자열, 토큰, 레지스트리 및 클러스터 정보는 포함하지 않았습니다.
- [ConfigMap과 의존성 readiness 정책 분리](02-configmap-dependency-readiness.md) 장을 작성하고 Volume README 및 기존 Probe 장의 링크·설명을 갱신했습니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `uv run ruff check src/ai_platform/api examples/volume11 tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py` | 통과 |
| `uv run mypy src/ai_platform/api` | 통과 — 4 source files, no issues |
| `uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 15 passed |
| `uv run python examples/volume11/dependency_readiness_demo.py` | 통과 — 모든 필수 라벨 준비 시 `True`, Redis 미준비 시 `False` |
| `kubectl kustomize k8s/volume11` | 통과 — Namespace, ConfigMap, Deployment, Service만 로컬 렌더링; Secret 예제는 제외 |
| `docker compose -f docker/volume11/compose.health.yaml config` | 통과 — 구성만 렌더링, 컨테이너 미시작 |
| 문서·링크·코드블록·비밀값 검사 | 통과 |
| 전체 품질 게이트: `uv run ruff check .`, `uv run mypy src`, `uv run pytest -q` | 통과 — 76 passed |

### 남은 범위

- Docker Compose로 Qdrant, Redis, PostgreSQL을 안전한 예제 구성으로 연결하기
- Ingress, Job/CronJob, PVC, HPA와 업데이트·롤백 예제 작성하기
- 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

Compose 의존 서비스 토폴로지를 예제 이미지·자리표시자·구성 렌더링 검증만으로 추가하고, 실제 컨테이너·클러스터·외부 연결은 시작하지 않습니다.

## 2026-08-10 — Slice 01: Health Probe 경계와 예제 Manifest

### 완료한 범위

- `src/ai_platform/api/health.py`에 외부 의존성이 없는 WSGI `/livez`, `/readyz` 계약을 추가했습니다.
  - liveness는 readiness 실패와 독립적으로 `200 OK`를 반환합니다.
  - readiness는 주입 가능한 검사 결과에 따라 `200 OK` 또는 `503 Service Unavailable`을 반환합니다.
  - 예제 플래그 `AI_PLATFORM_READY`는 `true`/`false`만 허용하며 비밀값을 읽거나 응답에 노출하지 않습니다.
- `examples/volume11/health_probe_demo.py`와 Volume 11 단위·통합 테스트를 추가했습니다.
- `docker/volume11/`에 비루트 실행 Dockerfile 및 Compose 구문/healthcheck 예제를 추가했습니다.
- `k8s/volume11/`에 Namespace, ConfigMap, Deployment, Service, Kustomization 예제를 추가했습니다.
  - 이미지 `example.invalid/ai-platform-api:0.1.0`은 의도적으로 비실행용 자리표시자입니다.
  - 실제 Secret, 레지스트리 주소, 클러스터 연결 정보는 포함하지 않습니다.
- [Health Probe: liveness와 readiness를 분리하기](01-health-probes.md) 장을 작성했습니다.

### 검증 결과

| 검증 | 결과 |
|---|---|
| `uv run ruff check src/ai_platform/api examples/volume11 tests/unit/test_volume11_health.py tests/integration/test_volume11_health_artifacts.py` | 통과 |
| `uv run mypy src/ai_platform/api` | 통과 — 3 source files, no issues |
| `uv run pytest tests/unit/test_volume11_health.py tests/integration/test_volume11_health_artifacts.py -q` | 통과 — 8 passed |
| `AI_PLATFORM_READY=false uv run python -m ai_platform.api.server --host 127.0.0.1 --port 18080` + 로컬 `curl` | 통과 — `/livez` 200, `/readyz` 503; 서버는 확인 후 종료 |
| `docker compose -f docker/volume11/compose.health.yaml config` | 통과 — 구성만 렌더링, 컨테이너 미시작 |
| `kubectl kustomize k8s/volume11` | 통과 — 4개 객체 로컬 렌더링, 클러스터 미연결 |
| 전체 품질 게이트: Ruff, mypy, 문서·링크·코드블록·비밀값 검사, `pytest -q` | 통과 — 69 passed |

### 남은 범위

- Docker Compose로 Qdrant, Redis, PostgreSQL을 안전한 예제 구성으로 연결하기
- Secret/ConfigMap 분리 심화, Ingress, Job/CronJob, PVC, HPA 작성하기
- Rolling Update/Rollback, 로그·메트릭·추적, 장애 대응과 비용 관리 장 작성하기
- Volume 미니 프로젝트, 전체 체크리스트, 용어집 인계 및 Volume 전체 검증 완료하기

### 다음 Slice

ConfigMap과 의존 서비스 readiness의 책임 경계를 확장하되, 로컬 예제·자리표시자·오프라인 테스트만 사용합니다.
