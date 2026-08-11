# Named HTTP Port: Probe와 Service 연결의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 컨테이너의 named port와 Service `targetPort`의 책임을 구분한다.
- startup, readiness, liveness probe가 같은 named `http` port를 참조하는 선언을 읽는다.
- `deployment_and_service_share_named_http_port`가 local text check임을 설명한다.
- 정적 port name 일치와 실제 endpoint·network·traffic delivery 증거를 혼동하지 않는다.

## 2. 왜 필요한가

Kubernetes Manifest에서 `8080`, `80`처럼 숫자만 반복하면 컨테이너 포트, Service 노출 포트, probe 대상 포트의 역할이 섞이기 쉽습니다. named port는 컨테이너가 제공하는 논리적 HTTP 인터페이스에 이름을 주고, Service와 probe가 같은 이름을 참조하도록 합니다.

이 Volume의 예제는 container port `http: 8080`, Service port `80`, Service `targetPort: http`를 구분합니다. Service가 받는 포트와 container가 수신한다고 선언한 포트가 반드시 같은 숫자일 필요는 없습니다. 그러나 `targetPort`와 probe의 `port`가 intended container port name을 가리키는지 확인하지 않으면 Manifest를 수정할 때 연결이 끊길 수 있습니다.

> [!WARNING]
> 이 장은 `k8s/volume11/deployment.yaml`과 `k8s/volume11/service.yaml`의 local source text만 읽습니다. `example.invalid/ai-platform-api:0.1.0` placeholder image는 실행할 수 없습니다. local review와 Kustomize render는 endpoint 생성, DNS, kube-proxy, kubelet probe, network policy, container listener, traffic delivery를 검증하지 않습니다. container execution, cluster connection, deployment가 금지된 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 핵심 개념

- **Named container port:** `containerPort: 8080`에 붙인 `name: http`입니다. 이 예제에서 `http`는 프로토콜 구현이나 network reachability를 보장하는 이름이 아니라 Manifest 내 참조용 식별자입니다.
- **Service `port`:** Service가 추상적으로 노출하는 포트입니다. 예제에서는 `80`입니다.
- **Service `targetPort`:** Service가 선택한 Pod의 container port로 보내려는 대상입니다. 문자열 `http`는 selected container의 named port를 가리키는 선언입니다.
- **Probe `port`:** kubelet이 HTTP probe를 보낼 대상으로 해석할 port입니다. startup, readiness, liveness probe의 `port: http`는 같은 named port를 참조하는 예제입니다.
- **Static contract:** source text에서 name과 참조의 모양이 일치한다는 증거입니다. 실제 Pod, EndpointSlice, listener, routing table의 상태는 아닙니다.

## 4. 동작 구조

```text
local source text only

Deployment container
  name: http
  containerPort: 8080
       ▲             ▲
       │             │
probe port: http ────┘             Service targetPort: http
  startup / readiness / liveness              │
                                              ▼
                                     Service port: 80

render_only_artifact_checks()
  └── declaration names and text shape: true | false

Pod creation, EndpointSlice, DNS, kube-proxy, kubelet HTTP request,
container listener, network policy, traffic delivery ── not verified
```

같은 `http` 문자열이 여러 위치에 있다는 사실은 사람이 읽는 연결 계약을 단순하게 만듭니다. 그것만으로 Service selector가 실제 Pod를 찾거나 `/readyz`가 성공하거나 Ingress traffic이 전달된다는 결론을 내릴 수는 없습니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/deployment.yaml` | placeholder API container, named `http` port, 세 HTTP probe 선언 |
| `k8s/volume11/service.yaml` | `ClusterIP` Service의 `port: 80`, `targetPort: http` 선언 |
| `src/ai_platform/api/operations_review.py` | local text check `deployment_and_service_share_named_http_port` |
| `tests/integration/test_volume11_named_http_port.py` | named port 선언과 runtime-evidence 경계 검사 |
| `examples/volume11/local_operations_review_demo.py` | deterministic local-only review JSON |

실습에는 Python과 `uv`가 필요합니다. 선택적으로 `kubectl` CLI가 있으면 local Kustomize render를 할 수 있습니다. kubeconfig, cluster, registry, Secret, credential, actual image는 필요하지 않으며 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 local artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력의 `artifact_checks.deployment_and_service_share_named_http_port`가 `true`인지 확인합니다. 이 check는 Deployment에 `name: http`와 `containerPort: 8080`, 세 `port: http` 참조가 있고 Service에 `port: 80`, `targetPort: http`가 있는지만 읽습니다. Docker daemon, socket, Kubernetes API, DNS, kubelet을 호출하지 않습니다.

### 6.2 오프라인 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_named_http_port.py -q
```

테스트는 placeholder image가 유지되고 named port 참조가 source text에 연결되어 있는지 확인합니다. container를 시작하거나 image를 pull하거나 Service endpoint를 만들거나 cluster에 resource를 생성하지 않습니다.

### 6.3 Deployment와 Service를 연결 없이 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

rendered YAML에서 Deployment의 `name: http`, `containerPort: 8080`, 각 probe의 `port: http`, Service의 `targetPort: http`를 읽습니다. 이 명령은 local YAML render일 뿐 Kubernetes API, Pod, EndpointSlice, DNS, NetworkPolicy, traffic을 만들지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 7. 코드와 Manifest 설명

`render_only_artifact_checks()`는 Deployment와 Service를 UTF-8 text로 읽습니다. `deployment_and_service_share_named_http_port`는 exact teaching contract만 확인합니다.

1. Deployment container port section에 `name: http`와 `containerPort: 8080`이 있다.
2. Manifest 전체에 startup, readiness, liveness probe의 세 `port: http` 참조가 있다.
3. Service port section에 `name: http`, `port: 80`, `targetPort: http`가 있다.

이 구현은 YAML parser나 Kubernetes client를 쓰지 않습니다. 그러므로 `true`는 local example의 text shape가 의도대로라는 뜻일 뿐 Service selector match, named-port resolution, probe response, endpoints, connection success를 뜻하지 않습니다. YAML 구조를 크게 바꾸면 check, test, 문서를 함께 바꾼 뒤 별도로 schema와 runtime evidence를 검토해야 합니다.

## 8. 정상 실행 결과

6.1의 JSON에는 다음 모양의 field가 포함됩니다.

```json
{"artifact_checks":{"deployment_and_service_share_named_http_port":true}}
```

실제 출력은 다른 local artifact check도 포함합니다. 6.2는 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다. 6.3의 rendered YAML에는 named `http` port와 `targetPort: http`가 보이지만 Pod IP, EndpointSlice address, DNS lookup 결과, request log, probe Event는 나타나지 않아야 합니다.

## 9. 오류 해결

| 증상 | local 확인 | 안전한 해결 |
|---|---|---|
| review key가 `false` | Deployment의 named port, 세 probe port, Service targetPort 문자열을 읽는다 | 의도된 구조 변경이면 local check, test, 문서를 함께 갱신한다. cluster에 apply하지 않는다. |
| `targetPort`가 숫자로 보임 | 숫자 targetPort와 named targetPort는 다른 reference 방식임을 확인한다 | 이 예제의 named-port contract를 유지하거나 별도 example과 evidence plan을 만든다. 실제 workload를 추측해 바꾸지 않는다. |
| probe가 다른 port name을 참조함 | startup, readiness, liveness section을 각각 비교한다 | route 의미와 container interface를 먼저 검토한다. readiness failure를 liveness restart 문제로 바꾸지 않는다. |
| `kubectl kustomize`를 찾을 수 없음 | CLI 설치 여부를 확인한다 | Python local review와 pytest를 먼저 실행한다. cluster를 만들거나 연결하지 않는다. |
| 실제 endpoint가 필요함 | local render가 endpoint 또는 network evidence를 만들지 않음을 기록한다 | 승인된 환경에서 image, Pod readiness, EndpointSlice, DNS, policy, request evidence를 별도로 검증한다. |

## 10. 응용 실습

1. API에 HTTP와 metrics라는 두 container port가 있다고 가정하고, 어떤 consumer가 어떤 named port를 참조해야 하는지 표로 작성합니다.
2. Service `port`, `targetPort`, container `containerPort`를 각각 변경하는 가상 변경을 만들고 source review에서 확인할 항목을 적습니다.
3. selector mismatch, named-port typo, readiness failure, network policy deny를 서로 다른 가설로 둔 triage 표를 작성합니다. 실제 cluster name, endpoint, credential, user data는 넣지 않습니다.

## 11. 실무 적용

운영 Manifest에서는 port name이 API contract의 일부가 될 수 있으므로 Deployment, Service, Ingress backend, NetworkPolicy, monitoring scrape declaration의 참조를 함께 검토합니다. `containerPort` declaration 자체는 application이 listener를 열었다는 보증이 아니며, named port가 같아도 container process가 다른 interface에 bind하면 traffic은 실패할 수 있습니다.

배포 전에는 approved image provenance, process listener, readiness result, selector labels, EndpointSlice membership, DNS, network policy, request timeout, rollback plan을 분리해 evidence를 수집합니다. probe 또는 access log에 credential, raw request body, private endpoint를 기록하지 않습니다.

## 12. 과제

- **기본:** `containerPort`, Service `port`, `targetPort`, probe `port`가 답하는 질문을 각각 한 문장으로 작성합니다.
- **응용:** HTTP API와 metrics endpoint를 가진 가상 Pod의 named-port table과 Service 분리 계획을 작성합니다. 실제 Manifest를 적용하지 않습니다.
- **심화:** named-port mismatch, selector mismatch, readiness failure, policy deny를 구분하는 investigation plan을 작성합니다. 각 행에 필요한 evidence source와 approval owner를 적고 actual cluster command나 credential은 넣지 않습니다.

## 13. 완료 체크리스트

- [ ] container named `http` port와 `containerPort: 8080` 선언을 읽었다.
- [ ] Service `port: 80`과 `targetPort: http`의 역할을 구분했다.
- [ ] startup, readiness, liveness probe의 `port: http` 참조를 확인했다.
- [ ] `deployment_and_service_share_named_http_port`가 local text check일 뿐임을 설명할 수 있다.
- [ ] endpoint, DNS, kubelet probe, network policy, traffic delivery가 `not verified`임을 유지했다.
- [ ] 실제 Secret, credential, cluster connection 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 14. 핵심 정리

Named `http` port는 container port, 세 health probe, Service `targetPort`를 사람이 읽을 수 있는 하나의 정적 계약으로 묶습니다. 이 Volume은 placeholder Deployment와 Service source text를 local review, pytest, Kustomize render로만 확인합니다. container listener, endpoint creation, DNS, kubelet enforcement, network path, traffic delivery는 증명하지 않았으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
