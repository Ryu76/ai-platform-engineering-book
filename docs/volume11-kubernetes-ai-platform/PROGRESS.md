# Volume 11 진행 기록

> 상태: 진행 중. 이 권은 아직 PRD의 Volume Definition of Done을 충족하지 않았습니다. `VOLUME11_COMPLETE=true`는 설정하지 않습니다.

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
