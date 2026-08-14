# Base Kustomization explicit namespace: 변환 없는 scope 선언의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- base `kustomization.yaml`의 `namespace:` 필드 부재와 resource별 `metadata.namespace` 선언을 구분한다.
- `base_kustomization_uses_explicit_example_resource_namespaces`가 local source-text check임을 설명한다.
- namespace transformer의 입력 모양과 Namespace admission·controller 동작을 같은 증거로 취급하지 않는다.

## 2. 정적 계약의 범위

`k8s/volume11/kustomization.yaml`은 `namespace.yaml`을 resource로 나열하지만 top-level `namespace:`를 선언하지 않습니다. 반대로 namespaced example resource인 `configmap.yaml`, `deployment.yaml`, `service.yaml`, `ingress.yaml`은 각각 `metadata.namespace: ai-platform-example`를 직접 선언합니다.

```text
base kustomization.yaml
  resources: namespace.yaml, configmap.yaml, deployment.yaml, service.yaml, ingress.yaml
  namespace: ── absent

namespaced resource text
  metadata.namespace: ai-platform-example ── explicitly declared
```

이 check는 현재 local UTF-8 source text의 제한된 모양만 읽습니다. `namespace:`가 없다는 것은 base가 현재 namespace transformer를 요청하지 않는다는 문자열 계약이고, 각 resource가 같은 example scope를 적었다는 것은 text 계약입니다. 이는 Kustomize parse 또는 transform 결과, Namespace object 존재, Kubernetes API admission, RBAC, quota, NetworkPolicy, controller reconciliation, Pod scheduling, Service endpoint 또는 deployment 증거가 아닙니다.

> [!WARNING]
> 현재 manifest는 example/placeholder만 사용합니다. check는 Docker daemon, kubeconfig, Kubernetes API, network, container, Secret, credential을 호출하지 않습니다. local test와 render가 성공해도 runtime evidence는 **not verified**이며 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 왜 resource별 선언을 읽는가

Kustomize의 top-level `namespace:`는 rendered namespaced resource의 namespace를 변환할 수 있는 별도 입력입니다. 이 base artifact에는 그 입력이 없습니다. 따라서 이 Volume은 각 namespaced example resource가 직접 적은 `ai-platform-example` 문자열과 `namespace.yaml` resource entry를 검토 대상으로 삼습니다.

이는 namespace transformer를 사용하면 안 된다는 운영 규칙이 아닙니다. 미래에 transformer를 추가한다면 대상 resource, Namespace resource 처리, overlay precedence, rendered output 및 admission evidence를 별도의 승인된 환경에서 검토해야 합니다. 이 local-only lesson에는 cluster URL, 실제 namespace, Secret 또는 credential을 넣지 않습니다.

## 4. local-only 실습

### 4.1 artifact review

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.base_kustomization_uses_explicit_example_resource_namespaces`가 `true`인지 확인합니다. 이 review는 base Kustomization text의 `namespace:` 부재, `namespace.yaml` entry, 네 resource text의 `namespace: ai-platform-example`만 읽습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_base_kustomization_explicit_namespace.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 local file read만 합니다. Kustomize transform 실행, `kubectl apply`, Namespace/resource 생성, image build/pull, container execution, Kubernetes API connection, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

이 명령은 별도의 local YAML render 확인입니다. render는 source-text check보다 넓은 parse 결과를 보여 줄 수 있지만 Namespace admission, effective transformer behavior in an overlay, controller reconciliation 또는 cluster state의 증거는 아닙니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | base text의 top-level `namespace:`와 네 resource의 explicit scope를 비교한다 | 의도된 example 변경이면 check·test·문서를 함께 갱신하고 apply하지 않는다. |
| overlay에서 namespace transformer가 필요함 | transform 대상, overlay precedence, Namespace handling을 별도 설계한다 | 승인된 configuration/provenance 절차로 인계하며 이 base에 실제 environment 값을 넣지 않는다. |
| render가 성공했으므로 namespace가 존재한다고 생각함 | render와 API admission·object existence가 다름을 확인한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 admitted-object evidence를 수집한다. |
| 정책 격리가 궁금함 | text check가 RBAC, quota, NetworkPolicy, scheduling을 증명하지 않음을 기록한다 | policy owner와 runtime evidence를 별도로 검토한다. |

## 6. 완료 체크리스트

- [ ] base Kustomization의 `namespace:` 부재와 resource별 explicit namespace 선언을 구분했다.
- [ ] `base_kustomization_uses_explicit_example_resource_namespaces`가 local text check임을 설명할 수 있다.
- [ ] namespace transformer input과 rendered/admitted object evidence를 혼동하지 않았다.
- [ ] Kubernetes API, controller reconciliation, Pod, endpoint, policy enforcement가 not verified임을 유지했다.
- [ ] 실제 namespace, Secret, credential, image, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

이 base의 explicit example namespace 모양은 검토 가능한 source-text 계약입니다. `true`는 현재 base가 namespace transformer field를 갖지 않고 네 namespaced example resource가 같은 placeholder scope를 적는다는 뜻뿐입니다. Kustomize transform, object creation, Kubernetes API admission, controller behavior와 deployment는 not verified이므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
