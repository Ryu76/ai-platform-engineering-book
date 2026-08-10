# Volume 11 진행 기록

> 상태: 진행 중. 이 권은 아직 PRD의 Volume Definition of Done을 충족하지 않았습니다. `VOLUME11_COMPLETE=true`는 설정하지 않습니다.

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
