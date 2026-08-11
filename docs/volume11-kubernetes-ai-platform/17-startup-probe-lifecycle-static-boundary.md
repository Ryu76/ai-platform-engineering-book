# Startup Probe: 초기화 시간과 재시작 판단의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `startupProbe`, liveness probe, readiness probe의 다른 질문을 구분한다.
- 예제 Deployment에 선언된 `/livez` startup probe의 period, timeout, failure threshold를 읽는다.
- local manifest text와 kubelet의 실제 startup/restart 판단을 혼동하지 않는다.
- 실행 증거 없이 `VOLUME11_COMPLETE=true`를 설정하지 않는 이유를 설명한다.

## 2. 왜 필요한가

AI API는 프로세스가 시작된 뒤 모델 metadata 확인, 설정 해석, cache 준비처럼 일정 시간이 걸리는 초기화를 할 수 있습니다. 이 시간이 liveness failure로 해석되면 준비 중인 컨테이너가 반복해서 재시작될 수 있습니다. Startup Probe는 **초기화가 완료되기 전** 다른 probe의 재시작 또는 endpoint 판단을 지연하도록 kubelet에 요청하는 별도 계약입니다.

그러나 Startup Probe가 있다고 readiness가 자동으로 성공하거나 dependency가 연결되는 것은 아닙니다. 이 Volume의 `/livez`는 process-local liveness 질문이고 `/readyz`는 traffic 수신 준비 질문입니다. 실제 model warm-up, image pull, process startup, dependency connectivity, kubelet event는 별도 실행 증거가 필요합니다.

> [!WARNING]
> 이 장의 Deployment는 `example.invalid/ai-platform-api:0.1.0` placeholder만 사용합니다. `kubectl kustomize`와 local review는 YAML을 읽거나 렌더링할 뿐 kubelet을 실행하지 않습니다. 이 작업에서는 container execution, cluster connection, deployment가 금지되어 startup success와 restart behavior는 `not verified`입니다. 따라서 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 핵심 개념

- **Startup Probe:** container가 시작을 마칠 때까지 kubelet이 startup 여부를 검사하도록 요청하는 probe입니다. 성공 전에는 liveness와 readiness의 normal handling이 시작되지 않습니다.
- **Liveness Probe:** process가 계속 실행 가능한지 묻는 probe입니다. startup 성공 뒤의 liveness failure 처리는 Startup Probe의 역할과 다릅니다.
- **Readiness Probe:** 새 traffic을 받아도 되는지 묻는 probe입니다. startup success가 dependency-ready 또는 Service endpoint 포함을 보장하지는 않습니다.
- **`periodSeconds: 5`:** kubelet에게 검사 사이의 예제 간격으로 5초를 요청합니다.
- **`timeoutSeconds: 2`:** 각 HTTP probe request에 주는 예제 응답 시간 상한입니다.
- **`failureThreshold: 12`:** 연속 failure를 허용하는 예제 횟수입니다. YAML의 세 값만으로 process가 정확히 몇 초에 시작하거나 언제 재시작되는지 단정하지 않습니다.

## 4. 동작 구조

```text
local file: k8s/volume11/deployment.yaml
  startupProbe: GET /livez, period 5, timeout 2, failures 12
  readinessProbe: GET /readyz
  livenessProbe: GET /livez
              │
              ▼
kubectl kustomize / local text review
              │
              ▼
static declaration only

kubelet probe scheduling ─┐
container startup         ├── not verified in this slice
restart / endpoint state  ┘
```

Startup Probe는 초기화 창을 선언하고, readiness probe는 traffic 여부를 선언하며, liveness probe는 process health 질문을 선언합니다. 세 probe가 같은 route를 쓰는지 여부보다 각 route가 무슨 상태를 의미하는지가 중요합니다. 이 예제는 startup 및 liveness에 `/livez`, readiness에 `/readyz`를 사용합니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/deployment.yaml` | placeholder image와 세 probe의 정적 Deployment 계약 |
| `src/ai_platform/api/health.py` | in-memory `/livez`, `/readyz` HTTP 계약 |
| `src/ai_platform/api/operations_review.py` | local text check `deployment_declares_startup_probe_boundary` |
| `tests/integration/test_volume11_startup_probe.py` | startup declaration과 runtime boundary 검사 |
| `examples/volume11/local_operations_review_demo.py` | deterministic local-only review 출력 |

실행에는 Python과 `uv`가 필요합니다. 선택적으로 `kubectl` CLI가 있으면 local Kustomize render를 실행할 수 있습니다. kubeconfig, cluster, registry, Secret, actual image는 필요하지 않으며 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 local artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력의 `artifact_checks.deployment_declares_startup_probe_boundary`가 `true`인지 확인합니다. 이 값은 Deployment source text에 `startupProbe`, `/livez`, `periodSeconds: 5`, `timeoutSeconds: 2`, `failureThreshold: 12`가 있음을 뜻합니다. HTTP listener, Docker daemon, kubelet, Kubernetes API를 호출하지 않습니다.

### 6.2 오프라인 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_health_artifacts.py tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_startup_probe.py -q
```

테스트는 placeholder image, Startup Probe field, review key, 문서의 runtime-evidence 경계를 검사합니다. container를 시작하거나 image를 pull하거나 cluster에 resource를 생성하지 않습니다.

### 6.3 Deployment를 연결 없이 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

출력에서 `startupProbe`와 `/livez` route를 읽을 수 있습니다. 이 명령은 local YAML render일 뿐 kubelet probe, Pod, Event, Service endpoint 또는 restart를 만들지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 7. 코드와 Manifest 설명

`k8s/volume11/deployment.yaml`의 `startupProbe`는 named `http` port의 `/livez`를 사용합니다. `periodSeconds: 5`, `timeoutSeconds: 2`, `failureThreshold: 12`는 의도적인 sample declaration입니다. workload별 초기화 시간, model load, dependency timeout을 측정한 production setting이 아닙니다.

`render_only_artifact_checks()`는 local file text를 읽어 `deployment_declares_startup_probe_boundary` boolean을 만들 뿐입니다. YAML parser, Docker daemon, socket, Kubernetes client를 사용하지 않습니다. 따라서 check가 `true`여도 image가 pull되거나 application이 startup probe에 200을 반환했다는 뜻이 아닙니다.

## 8. 정상 실행 결과

6.1의 JSON에는 다음 모양의 field가 포함됩니다.

```json
{"artifact_checks":{"deployment_declares_startup_probe_boundary":true}}
```

실제 출력은 다른 local artifact check도 포함합니다. 6.2는 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다. 6.3을 실행했다면 rendered Deployment에서 `startupProbe` YAML을 볼 수 있지만 Pod name, probe Event, restart count 또는 kubelet response는 나타나지 않아야 합니다.

## 9. 오류 해결

| 증상 | local 확인 | 안전한 해결 |
|---|---|---|
| review key가 `false` | `deployment.yaml`에 route, period, timeout, threshold가 모두 있는지 읽는다 | 의도된 변경이면 Manifest, test, 문서를 함께 갱신한다. cluster에 apply하지 않는다. |
| startup route가 readiness와 혼동됨 | `/livez`와 `/readyz`의 질문을 `health.py`와 첫 장에서 비교한다 | external dependency failure를 liveness로 승격하기 전에 restart 영향과 evidence를 검토한다. |
| 실제 workload가 재시작될 것으로 예상됨 | 이 Volume의 local render가 kubelet Event나 container startup을 읽지 않는다고 기록한다 | 승인된 환경에서 image, startup latency, kubelet events, readiness와 dependency evidence를 별도 검증한다. |
| `kubectl kustomize`를 찾을 수 없음 | CLI 설치 여부를 확인한다 | Python local review와 pytest를 먼저 실행한다. cluster를 만들거나 연결하지 않는다. |

## 10. 응용 실습

실제 값을 적용하지 말고 다음 검토표를 작성합니다.

1. model warm-up, configuration validation, dependency policy 확인을 각각 startup, liveness, readiness 중 어디에 둘지와 근거를 적습니다.
2. sample `periodSeconds`, `timeoutSeconds`, `failureThreshold`가 startup budget에 어떤 영향을 줄 수 있는지 측정 계획으로 정리합니다.
3. startup failure, readiness failure, liveness failure를 같은 incident로 묶지 않아야 하는 증거와 owner를 구분합니다.

표에는 cluster name, registry, image digest, endpoint, credential, real user data를 넣지 않습니다.

## 11. 실무 적용

승인된 runtime에서 probe 값을 정하기 전에는 image pull과 process launch를 제외한 application startup distribution, model/cache initialization, configuration validation, dependency policy, CPU throttling, node scheduling, error budget을 함께 검토합니다. Startup Probe가 길다고 무한 초기화를 허용해서는 안 되며, 짧다고 정상적인 warm-up을 restart loop로 만들어서도 안 됩니다.

또한 startup success는 traffic success가 아닙니다. readiness에 dependency policy를 넣는 경우 timeout, failure classification, caching, observability privacy와 Service endpoint behavior를 따로 확인합니다. production probe Event나 log에 request content, credential, raw endpoint를 기록하지 않습니다.

## 12. 과제

- **기본:** Startup Probe, liveness probe, readiness probe가 묻는 질문을 각각 한 문장으로 작성합니다.
- **응용:** 초기화가 느린 가상 AI API에 대한 probe budget 가설과 이를 검증할 관측 항목을 작성합니다. 실제 deployment는 하지 않습니다.
- **심화:** image pull failure, model warm-up failure, dependency readiness failure, process deadlock을 구분한 triage 표를 작성합니다. 각 행에 안전한 evidence source와 승인 owner를 적고 actual cluster command나 credential은 넣지 않습니다.

## 13. 완료 체크리스트

- [ ] Startup Probe가 liveness와 readiness의 normal handling 전 초기화 여부를 확인하는 계약임을 설명할 수 있다.
- [ ] `/livez` startup route와 `/readyz` readiness route의 책임을 구분했다.
- [ ] `periodSeconds: 5`, `timeoutSeconds: 2`, `failureThreshold: 12`가 sample declaration임을 확인했다.
- [ ] `deployment_declares_startup_probe_boundary`가 local text check일 뿐임을 설명할 수 있다.
- [ ] container execution, kubelet probe scheduling, restart, Service endpoint state가 `not verified`임을 유지했다.
- [ ] 실제 Secret, credential, cluster connection 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 14. 핵심 정리

Startup Probe는 초기화 중인 container가 liveness failure로 성급히 재시작되지 않도록 kubelet에 주는 선언입니다. 이 Volume은 placeholder Deployment에 `/livez` startup contract를 추가하고 local review, pytest, Kustomize render로 text shape만 확인합니다. image build, container execution, kubelet scheduling, restart, endpoint inclusion은 증명하지 않았으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
