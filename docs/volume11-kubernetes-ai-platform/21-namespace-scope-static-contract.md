# Namespace scope: 기본 리소스의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Namespace 객체와 namespaced resource의 서로 다른 역할을 구분한다.
- 기본 Kustomize 집합의 `ConfigMap`, `Deployment`, `Service`, `Ingress`가 예제 `ai-platform-example` namespace를 선언하는지 읽는다.
- `base_resources_share_example_namespace`가 local text check임을 설명한다.
- 같은 namespace 문자열과 admission·격리·실행 증거를 혼동하지 않는다.

## 2. 왜 필요한가

Kubernetes resource name은 namespace 안에서만 고유합니다. 따라서 API Deployment가 참조하는 ConfigMap, Service가 선택할 Pod, Ingress backend가 참조하는 Service는 의도한 namespace scope를 함께 검토해야 합니다. 이름만 같은 다른 namespace의 객체는 이 source text 계약으로 연결되지 않습니다.

이 Volume의 기본 Kustomize 집합은 `namespace.yaml`에서 `ai-platform-example`이라는 placeholder Namespace를 선언하고, `ConfigMap`, `Deployment`, `Service`, `Ingress`에는 같은 `metadata.namespace`를 적습니다. 이는 변경 전 사람이 읽을 수 있는 좁은 정적 계약입니다.

> [!WARNING]
> 이 장은 `k8s/volume11/`의 local UTF-8 source text만 읽습니다. `example.invalid/ai-platform-api:0.1.0`은 실행 불가능한 placeholder image입니다. local review와 Kustomize render는 Namespace admission, resource creation, RBAC, ResourceQuota, LimitRange, NetworkPolicy, Pod scheduling, ConfigMap injection, Service endpoint, Ingress routing을 검증하지 않습니다. Kubernetes API connection과 deployment가 금지된 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 핵심 개념

- **Namespace:** namespaced object의 이름 범위와 정책 적용 경계를 제공하는 Kubernetes 객체입니다.
- **Namespaced resource:** 이 예제에서는 `ConfigMap`, `Deployment`, `Service`, `Ingress`입니다. 각 source text의 `metadata.namespace`가 대상 scope 선언입니다.
- **Base set:** `k8s/volume11/kustomization.yaml`이 local render에 포함하는 기본 artifact 집합입니다. batch, storage, autoscaling의 별도 학습 집합을 대신 포함하지 않습니다.
- **정적 일치:** local source text에 같은 example namespace가 있다는 뜻입니다. API admission 또는 namespace policy가 적용됐다는 뜻이 아닙니다.
- **Isolation evidence:** admitted object, effective RBAC/policy, running Pod, network path를 확인한 결과입니다. 이 장의 범위 밖입니다.

## 4. 동작 구조

```text
local source text only

namespace.yaml
  metadata.name: ai-platform-example
              │
              │ same declared example scope
              ▼
configmap.yaml  deployment.yaml  service.yaml  ingress.yaml
  metadata.namespace: ai-platform-example

render_only_artifact_checks()
  └── declaration text shape: true | false

admission, RBAC, quota, NetworkPolicy, scheduling, ConfigMap injection,
EndpointSlice, Ingress routing ── not verified
```

같은 namespace 문자열은 Service selector, named port, Deployment selector를 검사하지 않습니다. label과 port의 연결은 각각 [19장](19-service-selector-static-contract.md), [18장](18-named-http-port-static-contract.md)에서 별도로 다룹니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/namespace.yaml` | example Namespace 선언 |
| `k8s/volume11/configmap.yaml` | 같은 namespace의 non-secret policy ConfigMap |
| `k8s/volume11/deployment.yaml` | placeholder API Deployment |
| `k8s/volume11/service.yaml` | placeholder API Service |
| `k8s/volume11/ingress.yaml` | placeholder host의 Ingress |
| `src/ai_platform/api/operations_review.py` | local text check `base_resources_share_example_namespace` |
| `tests/integration/test_volume11_namespace_scope.py` | namespace text와 runtime-evidence 경계 검사 |

실습에는 Python과 `uv`가 필요합니다. 선택적으로 `kubectl` CLI가 있으면 local Kustomize render를 할 수 있습니다. kubeconfig, cluster, registry, Secret, credential, 실제 image는 필요하지 않으며 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 local artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력의 `artifact_checks.base_resources_share_example_namespace`가 `true`인지 확인합니다. check는 namespace object name과 네 base resource의 `metadata.namespace` 예제 문자열만 local file에서 찾습니다. Docker daemon, Kubernetes API, RBAC, network를 호출하지 않습니다.

### 6.2 오프라인 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_namespace_scope.py -q
```

테스트는 placeholder image와 source text 선언을 검토합니다. Namespace 생성, ConfigMap 주입, Pod scheduling, Kubernetes API 호출, Ingress request 또는 deployment를 실행하지 않습니다.

### 6.3 연결 없이 Manifest 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

rendered YAML에서 Namespace name과 각 namespaced resource의 metadata namespace를 읽습니다. 이 명령은 local YAML render일 뿐 namespace를 만들거나 admission·RBAC·quota·NetworkPolicy·EndpointSlice·Ingress controller를 확인하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 7. 코드와 Manifest 설명

`render_only_artifact_checks()`는 local text를 읽어 `base_resources_share_example_namespace`를 계산합니다.

1. base Kustomization text에 `ai-platform-example` Namespace name이 있다.
2. ConfigMap, Deployment, Service, Ingress text에 `namespace: ai-platform-example`가 있다.

구현은 YAML parser나 Kubernetes client를 사용하지 않습니다. 따라서 `true`는 local example의 text shape가 의도대로라는 뜻뿐입니다. Namespace가 존재하는지, API server가 resource를 admit했는지, Service와 Deployment가 실제 같은 namespace에 생겼는지, RBAC 또는 NetworkPolicy가 기대대로 동작하는지는 뜻하지 않습니다.

## 8. 오류 해결

| 증상 | local 확인 | 안전한 해결 |
|---|---|---|
| review key가 `false` | Namespace object name과 각 base resource metadata namespace를 읽는다 | 의도된 scope 변경이면 local check, test, 문서를 함께 갱신한다. cluster에 apply하지 않는다. |
| resource name은 같지만 namespace가 다름 | Kubernetes name scope가 namespace 단위임을 확인한다 | 참조 관계와 label/port 계약을 별도로 검토한다. |
| Namespace policy 영향이 궁금함 | text check가 RBAC, quota, LimitRange, NetworkPolicy를 증명하지 않음을 기록한다 | 승인된 환경에서 policy owner와 admitted-object evidence를 별도로 검토한다. |
| `kubectl kustomize`를 찾을 수 없음 | CLI 설치 여부를 확인한다 | Python local review와 pytest를 먼저 실행한다. cluster를 만들거나 연결하지 않는다. |

## 9. 완료 체크리스트

- [ ] Namespace object와 namespaced resource의 책임을 구분했다.
- [ ] 기본 ConfigMap, Deployment, Service, Ingress의 `ai-platform-example` 선언을 읽었다.
- [ ] `base_resources_share_example_namespace`가 local text check일 뿐임을 설명할 수 있다.
- [ ] admission, RBAC, quota, NetworkPolicy, routing이 `not verified`임을 유지했다.
- [ ] 실제 Secret, credential, Kubernetes API connection 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 10. 핵심 정리

기본 Namespace와 namespaced resource의 같은 example scope는 사람이 읽을 수 있는 정적 계약입니다. 이 Volume은 placeholder source text를 local review, pytest, Kustomize render로만 확인합니다. Namespace admission, policy enforcement, workload lifecycle, network isolation, traffic delivery는 증명하지 않았으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
