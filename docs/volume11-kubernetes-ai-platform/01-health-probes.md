# Health Probe: liveness와 readiness를 분리하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 컨테이너 프로세스 생존 확인(liveness)과 트래픽 수신 준비 확인(readiness)의 책임을 구분한다.
- API의 `/livez`, `/readyz`가 서로 다른 HTTP 상태를 반환하도록 구현한다.
- 외부 의존성·비밀값 없이 로컬 메모리에서 Probe 계약을 테스트한다.
- 예제 Dockerfile과 Kubernetes Deployment에 독립된 liveness/readiness Probe를 연결한다.
- 예제 이미지와 ConfigMap을 사용한 Manifest를 읽고, 실제 클러스터 적용 전에 검증 범위를 판단한다.

## 2. 왜 필요한가

컨테이너가 실행 중이라는 사실만으로 요청을 처리할 준비가 된 것은 아닙니다. 예를 들어 API 프로세스는 살아 있지만 초기화가 끝나지 않았거나, 필수 의존성 확인이 실패했을 수 있습니다. 이 상태에서 Service가 요청을 보내면 사용자는 일시적인 5xx 오류를 받습니다.

liveness probe는 **프로세스가 계속 실행 가능한가**를 확인합니다. 실패하면 Kubernetes는 보통 컨테이너 재시작을 시도합니다. readiness probe는 **지금 이 Pod에 새 요청을 보내도 되는가**를 확인합니다. 실패한 Pod는 Service의 Endpoint에서 제외되지만, 반드시 재시작되지는 않습니다. 두 질문을 같은 엔드포인트로 합치면 단순한 의존성 장애 때문에 정상 프로세스가 반복 재시작될 수 있습니다.

> [!WARNING]
> 이 장의 `AI_PLATFORM_READY`는 Probe의 차이를 재현하기 위한 예제 플래그입니다. 실제 비밀값이나 접속 문자열이 아닙니다. 운영 환경에서는 의존성별 Timeout, 인증, 오류 분류, 관찰 지표를 설계한 뒤 readiness 판단에 포함합니다. Probe 실패를 해결하려고 실제 Secret을 코드·Manifest·로그에 넣지 마세요.

## 3. 핵심 개념

- **Liveness probe:** 프로세스가 교착 상태이거나 요청을 처리할 수 없을 때 재시작 판단에 쓰는 검사입니다. 외부 DB의 일시 장애를 여기서 검사하면 불필요한 재시작이 생길 수 있습니다.
- **Readiness probe:** 초기화 완료와 요청 수신 가능 여부를 Service에 알리는 검사입니다. `503 Service Unavailable`은 이 Pod로의 새 트래픽을 보류해야 한다는 신호로 쓸 수 있습니다.
- **HTTP 상태 코드:** 이 예제에서 `200 OK`는 검사 통과, `503 Service Unavailable`은 준비되지 않음을 뜻합니다. 정의되지 않은 경로는 `404`, GET 이외 메서드는 `405`입니다.
- **ConfigMap:** 비밀이 아닌 설정을 Pod에 주입하는 Kubernetes 객체입니다. `k8s/volume11/configmap.yaml`은 실습용 Boolean만 담습니다.
- **리소스 요청과 제한:** `requests`는 스케줄링 판단의 기준이고 `limits`는 컨테이너가 사용할 수 있는 상한입니다. 예제 값은 측정된 운영 권장값이 아닙니다.

## 4. 동작 구조

```text
Kubernetes kubelet                         Service Endpoint Controller
        │                                             │
        │ GET /livez                                 │ GET /readyz
        ▼                                             ▼
┌───────────────────┐                        ┌───────────────────┐
│ ai-platform-api   │ ── 200 ──► 프로세스 생존 │ ai-platform-api   │ ── 200 ──► 트래픽 포함
│ 표준 라이브러리   │                        │ readiness 경계    │ ── 503 ──► 트래픽 제외
│ HTTP API          │                        └───────────────────┘
└───────────────────┘
        │
        └── liveness 실패 시에만 재시작 정책의 후보가 됨

ConfigMap: AI_PLATFORM_READY=true|false
        │
        └── 예제 readiness 판단에만 주입; Secret이나 실제 의존성 주소는 없음
```

이 구현에서 `/livez`는 readiness가 `false`여도 `200`을 반환합니다. `/readyz`만 `503`을 반환합니다. 따라서 의존성 준비 실패와 프로세스 실패를 분리해 관찰할 수 있습니다.

## 5. 실습 환경

다음 파일은 이미 저장소에 있습니다.

| 경로 | 역할 |
|---|---|
| `src/ai_platform/api/health.py` | `/livez`, `/readyz` WSGI 계약과 예제 readiness 플래그 |
| `src/ai_platform/api/server.py` | 표준 라이브러리 WSGI 서버 실행 진입점 |
| `examples/volume11/health_probe_demo.py` | 포트를 열지 않는 오프라인 데모 |
| `docker/volume11/Dockerfile` | 비밀값 없는 비루트 컨테이너 예제 |
| `docker/volume11/compose.health.yaml` | API 단독 Compose 구문·healthcheck 예제 |
| `k8s/volume11/*.yaml` | Namespace, ConfigMap, Deployment, Service 예제 |
| `tests/unit/test_volume11_health.py` | HTTP 계약의 정상·실패 경계 검사 |

기본 실습은 Docker Desktop, kind, minikube, `kubectl` 또는 실제 클러스터가 없어도 됩니다. Python과 `uv`만 사용합니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
uv sync --all-groups
```

이 명령은 프로젝트와 검증 도구를 준비합니다. 파일 경로가 Windows에 있다면 WSL에서 `/mnt/c/...` 경로로 저장소를 열거나, 해당 터미널에서 저장소 루트로 이동합니다.

## 6. 단계별 실습

### 6.1 메모리 안에서 두 Probe 확인

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume11/health_probe_demo.py
```

이 데모는 WSGI 애플리케이션을 메모리에서 직접 호출하므로 네트워크 포트, Docker, Kubernetes, API 키가 필요하지 않습니다. `/livez`와 `/readyz`가 각각 `200 OK` 및 JSON 본문을 출력하면 계약이 연결된 것입니다.

### 6.2 readiness 실패와 liveness 성공의 차이 테스트

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/integration/test_volume11_health_artifacts.py -q
```

단위 테스트는 readiness 콜백을 `False`로 주입합니다. 그때 `/readyz`가 `503`, `/livez`가 `200`인지 확인합니다. 통합 테스트는 예제 실행, 이미지 자리표시자, Manifest의 Probe 경로를 검사합니다. 테스트는 네트워크와 API 키를 사용하지 않으며 클러스터에 적용하거나 배포하지 않습니다.

### 6.3 컨테이너 설정을 적용 없이 해석

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
docker compose -f docker/volume11/compose.health.yaml config
```

이 명령은 Compose 파일을 합성해 화면에 출력할 뿐 컨테이너를 시작하지 않습니다. `AI_PLATFORM_READY: "true"`, `healthcheck`, 빌드 컨텍스트가 보이는지 확인합니다. `up`은 로컬 포트와 컨테이너를 변경하므로 이 장의 기본 검증 명령에는 포함하지 않습니다.

### 6.4 Kubernetes Manifest를 연결 없이 렌더링

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
kubectl kustomize k8s/volume11
```

`kubectl kustomize`는 `kustomization.yaml`이 가리키는 네 Manifest를 로컬에서 합쳐 표준 YAML로 출력합니다. API 서버 연결, 리소스 생성, 스키마 다운로드를 하지 않습니다. 이는 YAML 렌더링 확인일 뿐 Kubernetes API 스키마 검증이나 배포가 아닙니다. 실제 클러스터에 연결하는 `kubectl apply`는 이 교재의 기본 검증 명령에 포함하지 않습니다. `kubectl`이 없으면 6.1과 6.2만으로 API 계약을 검증하고, 설치 후 이 명령을 다시 실행합니다.

## 7. 코드 설명

`HealthApplication`은 WSGI 호출 가능 객체입니다. 요청 메서드와 경로를 먼저 제한한 뒤, `/livez`에서는 언제나 생존 JSON을 반환합니다. `/readyz`에서는 주입받은 `readiness_check`만 호출합니다. 이 의존성 주입 덕분에 테스트는 DB·Redis·Qdrant·네트워크 없이 준비 실패를 재현합니다.

`readiness_from_environment()`는 `AI_PLATFORM_READY`의 `true` 또는 `false`만 허용합니다. 오타를 조용히 성공으로 처리하면 Pod가 잘못 준비된 상태로 표시될 수 있으므로 `sometimes` 같은 값은 `ValueError`로 거절합니다. 함수는 환경 변수의 값 자체를 HTTP 응답이나 로그에 반환하지 않습니다.

`k8s/volume11/deployment.yaml`은 `/readyz`와 `/livez`를 각각 다른 Probe로 지정합니다. `example.invalid/ai-platform-api:0.1.0`은 의도적으로 가져올 수 없는 문서용 자리표시자입니다. 학습자는 자신의 레지스트리·태그·승인 절차가 준비되기 전에는 이를 실제 이미지로 바꾸지 않습니다.

## 8. 정상 실행 결과

6.1의 출력에는 다음 두 줄이 포함됩니다.

```text
/livez 200 OK {"status":"ok","service":"ai-platform-api","check":"liveness"}
/readyz 200 OK {"status":"ok","service":"ai-platform-api","check":"readiness"}
```

6.2의 pytest 출력은 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다. 6.3을 실행했다면 Compose 설정이 YAML로 출력되어야 하며, 컨테이너 목록은 생성되지 않습니다. 6.4를 실행했다면 네 Kubernetes 객체가 합쳐진 YAML이 출력되어야 하며, 클러스터 연결은 발생하지 않습니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `No module named ai_platform` | 저장소 루트가 아니거나 `uv run`을 생략했을 수 있습니다. | 저장소 루트에서 `uv sync --all-groups` 후 명령을 다시 실행합니다. |
| `/readyz`가 `503` | `AI_PLATFORM_READY=false`이거나 테스트가 준비 실패를 주입했습니다. | 예제에서는 예상된 결과입니다. 무조건 liveness와 같은 응답으로 바꾸지 말고 준비 조건을 확인합니다. |
| `AI_PLATFORM_READY must be true or false` | ConfigMap 또는 환경 변수의 Boolean 철자가 잘못되었습니다. | `true` 또는 `false`만 사용합니다. 비밀값을 환경 변수에 추가하지 않습니다. |
| `docker compose`를 찾을 수 없음 | Docker Desktop 또는 Compose CLI가 설치되지 않았습니다. | 이 장의 필수 검증은 Python 테스트입니다. Docker 설치 후 6.3을 별도로 실행합니다. |
| `kubectl`을 찾을 수 없음 | Kubernetes CLI가 설치되지 않았습니다. | 클러스터 생성이나 연결을 하지 말고, CLI 설치 후 `kubectl kustomize k8s/volume11`만 실행합니다. |
| Pod가 ImagePullBackOff | `example.invalid`는 실제 이미지를 제공하지 않는 자리표시자입니다. | 예제는 기본적으로 적용하지 않습니다. 승인된 빌드·레지스트리 절차가 생긴 뒤에만 자체 이미지로 교체합니다. |

## 10. 응용 실습

1. `HealthApplication(readiness_check=lambda: False)`를 사용해 `/livez`와 `/readyz`의 상태 코드가 달라지는 이유를 자신의 말로 설명합니다.
2. `k8s/volume11/deployment.yaml`의 `resources` 값을 측정 결과가 있다고 가정한 값으로 바꾸는 계획을 작성합니다. 실제 Manifest를 적용하지 않습니다.
3. `AI_PLATFORM_READY` 대신 실제 의존성 검사로 확장한다면 필요한 Timeout, 실패 분류, 캐시, 관찰 지표를 설계합니다. 접속 문자열·토큰·실제 회사 서비스 이름은 쓰지 않습니다.

## 11. 실무 적용

운영 readiness는 프로세스 시작 완료, 필수 설정 유효성, 필요한 의존성의 제한된 상태 검사를 조합할 수 있습니다. 반면 liveness는 가능한 한 프로세스 내부의 회복 불가능한 상태에 집중합니다. 외부 시스템의 느린 응답을 매 요청마다 liveness에 연결하면 전체 장애에서 재시작 폭주가 생길 수 있습니다.

Probe는 관찰성의 시작점일 뿐입니다. HTTP 요청 지연, 오류율, 재시작 횟수, 준비되지 않은 Pod 수, 의존성별 실패 이유를 메트릭과 구조화된 로그로 함께 봐야 합니다. 로그에는 API 키, Authorization 헤더, 원문 프롬프트, 개인정보를 기록하지 않습니다. 운영 변경은 검토·승인·롤백 계획이 있는 별도 절차에서 수행합니다.

## 12. 과제

- **기본:** liveness와 readiness의 질문을 각각 한 문장으로 작성하고, readiness가 `503`일 때 Service가 취할 행동을 설명합니다.
- **응용:** 초기화에 20초가 걸리는 가상 API의 `initialDelaySeconds`, `periodSeconds`, `failureThreshold`를 제안하고 근거를 적습니다.
- **심화:** Qdrant, Redis, PostgreSQL을 쓰는 API의 readiness 정책을 설계합니다. 각 의존성이 일시적으로 실패할 때 요청 보류, 재시도, 경보, 사람 승인 중 무엇이 필요한지 표로 정리합니다. 실제 접속 정보는 넣지 않습니다.

## 13. 완료 체크리스트

- [ ] liveness와 readiness가 각각 프로세스 생존과 트래픽 수신 준비를 확인함을 설명할 수 있다.
- [ ] `/livez`는 readiness 실패와 독립적으로 `200`을 반환함을 테스트로 확인했다.
- [ ] `/readyz`가 준비 실패에서 `503`을 반환함을 테스트로 확인했다.
- [ ] `uv run python examples/volume11/health_probe_demo.py`를 실행했다.
- [ ] `uv run pytest tests/unit/test_volume11_health.py tests/integration/test_volume11_health_artifacts.py -q`가 통과했다.
- [ ] Docker Compose를 실행하지 않고 `config`로만 해석할 수 있음을 이해했다.
- [ ] Kubernetes Manifest가 예제 이미지와 ConfigMap만 사용하며 실제 Secret이 없음을 확인했다.
- [ ] 클러스터에 적용하거나 배포하지 않았고, 실제 Secret·접속 정보·개인정보를 저장하지 않았다.

## 14. 핵심 정리

Kubernetes 운영에서 liveness와 readiness는 같은 검사가 아닙니다. liveness는 프로세스 재시작 판단을, readiness는 새 트래픽 포함 여부를 돕습니다. 이 장은 표준 라이브러리 HTTP API, 오프라인 테스트, 비루트 Dockerfile, 예제 전용 Kubernetes Manifest로 두 경계를 분리했습니다. 다음 실습에서는 이 기반 위에 설정 분리와 실제 의존 서비스의 안전한 로컬 검증 경계를 추가합니다.
