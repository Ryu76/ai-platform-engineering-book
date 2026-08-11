# Service Selector: Pod template label 연결의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Service selector와 Deployment Pod template label의 역할을 구분한다.
- `app.kubernetes.io/name: ai-platform-api`라는 예제 label의 정적 일치를 읽는다.
- `deployment_template_and_service_selector_share_app_label`가 local text check임을 설명한다.
- selector 선언과 실제 EndpointSlice·traffic delivery 증거를 혼동하지 않는다.

## 2. 왜 필요한가

Kubernetes Service는 Deployment 이름을 보고 Pod를 고르지 않습니다. Service의 `spec.selector`가 Pod label과 일치해야 후보 Pod를 선택할 수 있습니다. 사람이 보기에는 Deployment와 Service 이름이 같아도 template label이 빠지거나 selector key/value가 달라지면 Service가 대상 Pod를 찾지 못할 수 있습니다.

이 Volume의 placeholder API는 `app.kubernetes.io/name: ai-platform-api`를 Deployment Pod template label과 Service selector에 함께 선언합니다. 이 반복은 수정 시 검토할 연결 지점을 드러내는 정적 계약입니다.

> [!WARNING]
> 이 장은 `k8s/volume11/deployment.yaml`과 `k8s/volume11/service.yaml`의 local UTF-8 source text만 읽습니다. `example.invalid/ai-platform-api:0.1.0`은 실행 불가능한 placeholder image입니다. local review와 Kustomize render는 Pod 생성, label admission, Service controller, EndpointSlice, DNS, kube-proxy, NetworkPolicy, container listener, traffic delivery를 검증하지 않습니다. container execution, Kubernetes API connection, deployment가 금지된 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 핵심 개념

- **Pod template label:** Deployment의 `spec.template.metadata.labels`입니다. Deployment가 Pod를 만들 때 붙이려는 label 선언입니다.
- **Service selector:** Service의 `spec.selector`입니다. 이 selector와 일치하는 Pod label을 대상으로 삼으려는 선언입니다.
- **Label key/value:** 예제의 `app.kubernetes.io/name`과 `ai-platform-api`입니다. key와 value 모두 일치해야 합니다.
- **Selector match:** local source text에서 template label과 selector가 같은 모양이라는 증거입니다. 실제 controller가 EndpointSlice를 만들었다는 증거가 아닙니다.
- **Endpoint evidence:** 실행 중인 Pod의 label, readiness, Service controller 결과, EndpointSlice address를 함께 확인한 결과입니다. 이 장의 범위 밖입니다.

## 4. 동작 구조

```text
local source text only

Deployment
  spec.template.metadata.labels
    app.kubernetes.io/name: ai-platform-api
                    │
                    │ same declared key/value
                    ▼
Service
  spec.selector
    app.kubernetes.io/name: ai-platform-api

render_only_artifact_checks()
  └── declaration text shape: true | false

Pod creation, selector evaluation, readiness, EndpointSlice, DNS,
kube-proxy, NetworkPolicy, container listener, traffic delivery ── not verified
```

이 계약은 Deployment metadata의 이름이나 Service metadata의 이름을 비교하지 않습니다. Service가 선택하는 기준은 template에 붙일 label과 selector이므로, 이 예제는 두 위치를 의도적으로 분리해 읽습니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/deployment.yaml` | placeholder API Deployment의 Pod template label 선언 |
| `k8s/volume11/service.yaml` | `ClusterIP` Service의 selector와 named `http` targetPort 선언 |
| `src/ai_platform/api/operations_review.py` | local text check `deployment_template_and_service_selector_share_app_label` |
| `tests/integration/test_volume11_service_selector.py` | selector/template 선언과 runtime-evidence 경계 검사 |
| `examples/volume11/local_operations_review_demo.py` | deterministic local-only review JSON |

실습에는 Python과 `uv`가 필요합니다. 선택적으로 `kubectl` CLI가 있으면 local Kustomize render를 할 수 있습니다. kubeconfig, cluster, registry, Secret, credential, 실제 image는 필요하지 않으며 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 local artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력의 `artifact_checks.deployment_template_and_service_selector_share_app_label`가 `true`인지 확인합니다. check는 Deployment template label과 Service selector의 예제 key/value를 local file에서 찾을 뿐입니다. Docker daemon, Kubernetes API, DNS, network, kubelet을 호출하지 않습니다.

### 6.2 오프라인 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_service_selector.py -q
```

테스트는 placeholder image와 source text 선언을 검토합니다. image pull, container 시작, Kubernetes API 호출, EndpointSlice 생성, Service 요청 또는 deployment를 실행하지 않습니다.

### 6.3 연결 없이 Manifest 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

rendered YAML의 Deployment `spec.template.metadata.labels`와 Service `spec.selector`에서 같은 key/value를 읽습니다. 이 명령은 local YAML render일 뿐 Pod, EndpointSlice, DNS record, network connection, cluster resource를 만들지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 7. 코드와 Manifest 설명

`render_only_artifact_checks()`는 Deployment와 Service를 UTF-8 text로 읽습니다. `deployment_template_and_service_selector_share_app_label`는 다음의 좁은 teaching contract를 확인합니다.

1. Deployment template metadata labels에 `app.kubernetes.io/name: ai-platform-api`가 있다.
2. Service selector에 같은 `app.kubernetes.io/name: ai-platform-api`가 있다.

구현은 YAML parser나 Kubernetes client를 사용하지 않습니다. 따라서 `true`는 local example의 text shape가 의도대로라는 뜻입니다. selector가 실제 Pod label과 평가되었는지, Pod가 Ready인지, EndpointSlice address가 만들어졌는지, named port가 해석되는지, request가 성공했는지는 뜻하지 않습니다.

## 8. 정상 실행 결과

6.1의 JSON에는 다음 모양의 field가 포함됩니다.

```json
{"artifact_checks":{"deployment_template_and_service_selector_share_app_label":true}}
```

실제 출력에는 다른 local artifact check도 포함됩니다. 6.2는 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다. 6.3의 rendered YAML에는 selector와 template label이 보이지만 Pod name, EndpointSlice address, DNS lookup 결과, request log, Service controller Event는 나타나지 않아야 합니다.

## 9. 오류 해결

| 증상 | local 확인 | 안전한 해결 |
|---|---|---|
| review key가 `false` | template label과 Service selector의 key/value를 각각 읽는다 | 의도된 구조 변경이면 local check, test, 문서를 함께 갱신한다. cluster에 apply하지 않는다. |
| Deployment와 Service 이름은 같지만 selector가 다름 | 이름은 selector match 조건이 아님을 확인한다 | workload 이름이 아닌 Pod template label contract를 먼저 설계한다. |
| selector value typo가 보임 | key뿐 아니라 value까지 비교한다 | API, worker, batch처럼 역할이 다른 workload의 label을 무심코 복사하지 않는다. |
| `kubectl kustomize`를 찾을 수 없음 | CLI 설치 여부를 확인한다 | Python local review와 pytest를 먼저 실행한다. cluster를 만들거나 연결하지 않는다. |
| 실제 endpoint가 필요함 | local text와 render가 endpoint evidence가 아님을 기록한다 | 승인된 환경에서 Pod label, readiness, EndpointSlice, DNS, policy, request evidence를 별도로 검증한다. |

## 10. 응용 실습

1. API, worker, maintenance Job이 있는 가상 Platform의 label key/value와 각 Service selector를 표로 작성합니다.
2. template label만 바꾸는 가상 변경과 Service selector만 바꾸는 가상 변경을 만들고 source review 항목을 적습니다.
3. selector mismatch, Pod NotReady, port mismatch, NetworkPolicy deny를 서로 다른 가설로 둔 triage 표를 작성합니다. 실제 cluster name, endpoint, credential, user data는 넣지 않습니다.

## 11. 실무 적용

운영 Manifest에서는 label을 Service뿐 아니라 Deployment selector, PodDisruptionBudget, NetworkPolicy, monitoring target, cost allocation에도 사용할 수 있습니다. label을 변경할 때는 immutable selector 제약, 다른 controller의 ownership, rollout 중 구 버전과 신 버전의 label compatibility를 별도로 검토합니다.

배포 전에는 approved image provenance, admitted Pod labels, readiness, EndpointSlice membership, DNS, network policy, request timeout, rollback plan을 분리해 evidence를 수집합니다. log나 label에는 credential, raw request body, 개인 endpoint를 넣지 않습니다.

## 12. 과제

- **기본:** Deployment 이름, Pod template label, Service selector가 각각 답하는 질문을 한 문장으로 작성합니다.
- **응용:** API와 worker가 있는 가상 Platform의 label table 및 Service selector plan을 작성합니다. 실제 Manifest를 적용하지 않습니다.
- **심화:** selector mismatch, readiness failure, named-port mismatch, policy deny를 구분하는 investigation plan을 작성합니다. 각 행에 필요한 evidence source와 approval owner를 적고 actual cluster command나 credential은 넣지 않습니다.

## 13. 완료 체크리스트

- [ ] Deployment Pod template label의 위치와 책임을 읽었다.
- [ ] Service selector와 workload metadata name의 차이를 설명할 수 있다.
- [ ] `app.kubernetes.io/name: ai-platform-api`의 key/value 일치를 확인했다.
- [ ] `deployment_template_and_service_selector_share_app_label`가 local text check일 뿐임을 설명할 수 있다.
- [ ] EndpointSlice, DNS, kube-proxy, traffic delivery가 `not verified`임을 유지했다.
- [ ] 실제 Secret, credential, Kubernetes API connection 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 14. 핵심 정리

Service selector와 Deployment Pod template label의 같은 key/value는 사람이 읽을 수 있는 정적 연결 계약입니다. 이 Volume은 placeholder Deployment와 Service source text를 local review, pytest, Kustomize render로만 확인합니다. Pod admission, readiness, EndpointSlice, DNS, network path, traffic delivery는 증명하지 않았으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
