# Volume 11 미니 프로젝트: 로컬 AI Platform 운영 검토

## 1. 프로젝트 목표

앞 장에서 만든 health probe, dependency readiness 정책, correlation logging, 최소 telemetry와 render-only Docker/Kubernetes 예제를 한 번의 **로컬 증거 검토**로 묶습니다. 이 미니 프로젝트의 결과물은 배포 도구가 아니라, 다음 질문에 작은 증거를 붙이는 JSON report입니다.

1. process liveness와 readiness 결과를 서로 분리했는가?
2. readiness failure와 telemetry exporter failure가 서로 다른 결과인지 보였는가?
3. telemetry가 process-local callback에서만 만들어지고 request ID를 report에 복사하지 않는가?
4. Compose와 Manifest가 `example.invalid` 및 placeholder boundary를 지키는가?
5. 아직 확인하지 않은 운영 사실을 성공으로 주장하지 않는가?

## 2. 사전 조건과 범위

저장소 루트에서 Python과 `uv`를 사용할 수 있어야 합니다. 기존 `HealthApplication`과 Volume 11 example artifact를 사용하며 새 package, endpoint, network listener, container 또는 cloud resource를 만들지 않습니다.

> [!WARNING]
> 이 프로젝트는 in-memory WSGI 호출과 local file read만 수행합니다. `docker compose up`, image pull/build, `kubectl apply`, `kubectl get`, rollout, rollback, alert 생성, telemetry backend query, Secret 작성, credential 사용, cluster 연결 또는 deployment를 실행하지 마세요. `kubectl kustomize`가 필요한 경우에도 별도의 읽기 전용 학습 검토로만 취급합니다.

## 3. 생성 파일과 역할

| 파일 | 역할 |
|---|---|
| `src/ai_platform/api/operations_review.py` | WSGI probe를 memory에서 호출하고 local artifact의 placeholder/render-only contract를 읽는다. |
| `examples/volume11/local_operations_review_demo.py` | 한 줄의 deterministic JSON review를 stdout에 출력한다. |
| `tests/integration/test_volume11_mini_project.py` | report의 probe 상태, exporter 격리, artifact boundary, 비검증 범위를 검사한다. |

`operations_review.py`는 API server가 시작될 때 자동으로 실행되지 않습니다. 이 함수는 mini project demo와 test가 명시적으로 호출할 때만 실행됩니다.

## 4. 실행하기

실행 위치는 **저장소 루트**입니다.

```bash
uv run python examples/volume11/local_operations_review_demo.py
```

정상 결과는 key 순서가 고정된 JSON 한 줄입니다. 주요 값은 다음과 같습니다.

```json
{
  "scope": "local-only",
  "probe_checks": {
    "liveness": "200 OK",
    "readiness_available": "200 OK",
    "readiness_unavailable": "503 Service Unavailable",
    "exporter_failure_isolated": "200 OK"
  },
  "telemetry": {
    "local_event_count": 2,
    "delivery": "process-local callback only"
  }
}
```

report에는 request ID, raw path/query/body/header, environment value, dependency detail, exception text, endpoint, credential, image registry 또는 cluster address를 넣지 않습니다. `artifact_checks`의 `true`는 **파일 문자열의 교육용 계약이 존재한다**는 의미일 뿐, 이미지를 pull할 수 있거나 YAML을 cluster에서 실행했다는 의미가 아닙니다.

## 5. 코드가 확인하는 증거

### 5.1 Probe와 exporter 격리

프로그램은 TCP port를 열지 않고 `HealthApplication`을 직접 호출합니다.

- `liveness`는 readiness policy와 별도로 `200 OK`여야 합니다.
- `readiness_available`은 injected policy가 `True`일 때 `200 OK`여야 합니다.
- `readiness_unavailable`은 injected policy가 `False`일 때 `503 Service Unavailable`이어야 합니다.
- `exporter_failure_isolated`는 injected callback이 예외를 던져도 healthy readiness가 `200 OK`인지를 확인합니다.

이 결과는 external dependency 상태, model quality, customer impact, retry 성공 여부 또는 telemetry backend availability를 증명하지 않습니다. exporter exception detail은 report 또는 response에 기록하지 않습니다.

### 5.2 Local telemetry

available probe 두 개는 process-local list exporter에 최소 event 두 개만 전달합니다. 이는 `local_event_count: 2`로만 요약됩니다. report는 event payload를 다시 출력하지 않으므로 correlation ID를 두 번째 관측 데이터에 복사하지 않습니다. delivery는 queue, retry, collector, metric endpoint, trace backend, network connection을 구현하지 않는 `process-local callback only`입니다.

### 5.3 Render-only artifact contract

다음 항목은 local text read로만 확인합니다.

| artifact check | 확인하는 학습 계약 | 확인하지 않는 것 |
|---|---|---|
| Deployment | `example.invalid` image와 `/livez`·`/readyz` probe가 있다. | image pull, Pod start, probe timing |
| base Kustomization | `secret.example.yaml`이 base apply set에 없다. | 조직 Secret policy 또는 RBAC |
| Compose | placeholder image, internal network, host `ports` 부재가 있다. | container start order, dependency readiness, DNS |
| CronJob | `suspend: true`가 있다. | scheduler 또는 Job execution |
| HPA | base Deployment와 다른 example target을 쓴다. | metrics pipeline, replica change, capacity |

필요하면 아래 명령으로 Manifest를 **로컬 렌더링만** 할 수 있습니다. 이 명령은 project report에 포함되지 않으며 API call, resource 생성 또는 cluster 연결을 하지 않습니다.

```bash
kubectl kustomize k8s/volume11
kubectl kustomize k8s/volume11/batch
kubectl kustomize k8s/volume11/storage
kubectl kustomize k8s/volume11/autoscaling
```

## 6. 완료 기준

다음 네 항목을 모두 만족하면 이 mini project slice는 완료입니다.

- [ ] demo가 local-only JSON을 stdout에 출력하고 liveness/available readiness/exporter-isolated가 `200 OK`, unavailable readiness가 `503 Service Unavailable`이다.
- [ ] report가 process-local telemetry event 두 개를 요약하며 request ID와 exporter exception detail을 출력하지 않는다.
- [ ] all `artifact_checks`가 true이고 example image, suspended batch, separate HPA target, Secret example 제외가 유지된다.
- [ ] test가 다음 명령으로 통과하며 container, backend, Secret 또는 cluster를 만들지 않는다.

```bash
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/unit/test_volume11_telemetry.py tests/integration/test_volume11_health_artifacts.py tests/integration/test_volume11_mini_project.py -q
```

## 7. 실패 해석

| 증상 | 가능한 원인 | 안전한 다음 단계 |
|---|---|---|
| `readiness_available`이 200이 아님 | local injected readiness contract가 바뀌었을 수 있다. | unit test부터 확인하고 readiness와 liveness를 같은 실패로 취급하지 않는다. |
| `exporter_failure_isolated`이 200이 아님 | telemetry delivery failure가 response path에 섞였을 수 있다. | exporter callback의 예외 격리 계약을 검토한다. backend를 연결해 진단하지 않는다. |
| artifact check가 false | placeholder 또는 base/optional artifact 분리가 변경됐을 수 있다. | 해당 local Manifest 또는 Compose 텍스트를 검토하고 실제 apply로 확인하지 않는다. |
| JSON에 raw input 또는 exception detail이 보임 | observability data-minimization 경계가 깨졌을 수 있다. | 출력 schema를 축소하고 보안/privacy 검토로 이관한다. |

## 8. 운영 전 인계

이 프로젝트는 deployment approval이 아닙니다. 실제 환경으로 넘어가기 전에 platform, security/privacy, data, SRE/operations owner가 image provenance, dependency contract, resource request/limit, HPA metric source, alert action owner, retention, access control, rollback compatibility, customer-impact verification을 승인된 절차로 검토해야 합니다. 실제 명령, account, endpoint, Secret 또는 cluster detail은 이 학습 저장소에 추가하지 않습니다.
