# Base Kustomization: 예제 core resource 목록의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- base `kustomization.yaml`의 resource 목록과 별도 optional 학습 집합을 구분한다.
- `namespace.yaml`, `configmap.yaml`, `deployment.yaml`, `service.yaml`, `ingress.yaml`의 example core resource 선언을 읽는다.
- `base_kustomization_declares_only_example_core_resources`가 local source-text check임을 설명한다.
- Kustomize render, object 생성, controller reconciliation, Pod 실행을 같은 증거로 혼동하지 않는다.

## 2. 정적 계약의 범위

`k8s/volume11/kustomization.yaml`은 다음 다섯 local file만 base resource로 선언합니다.

```text
namespace.yaml
configmap.yaml
deployment.yaml
service.yaml
ingress.yaml
```

`secret.example.yaml`은 base에서 제외됩니다. `batch/`, `storage/`, `autoscaling/`은 각각 별도 Kustomize 학습 집합이므로 base resource 목록에 포함하지 않습니다. 모든 core manifest는 `ai-platform-example`, `example.invalid`, `example-ingress-class`처럼 예제 또는 placeholder만 사용합니다.

> [!WARNING]
> 이 계약은 local UTF-8 file text만 읽습니다. resource 목록은 Kustomize가 실제로 parse하거나 render했다는 증거가 아니며 Namespace·ConfigMap·Deployment·Service·Ingress object 존재, admission, controller reconciliation, image pull, Pod 실행, endpoint 생성, network traffic, Kubernetes API connection 또는 deployment를 검증하지 않습니다. 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 관계 읽기

```text
k8s/volume11/kustomization.yaml (local text only)
  ├── namespace.yaml
  ├── configmap.yaml
  ├── deployment.yaml
  ├── service.yaml
  └── ingress.yaml

secret.example.yaml, batch/, storage/, autoscaling/ ── excluded from base declaration

render, apply, reconciliation, containers, cluster state ── not verified
```

이 목록은 base 교육 artifact의 경계를 빠르게 검토하는 용도입니다. `secret.example.yaml`이 base에 없다는 사실은 Secret이 없거나 안전하다는 보장이 아니며, optional 집합이 제외됐다는 사실도 Kubernetes가 어떤 resource를 만들지에 대한 실행 증거가 아닙니다.

## 4. local-only 실습

### 4.1 artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.base_kustomization_declares_only_example_core_resources`가 `true`인지 확인합니다. check는 local base Kustomization text에 다섯 resource entry가 있고 Secret example·optional directory entry가 없는지만 봅니다. Docker daemon, Kubernetes API, filesystem 밖의 경로, network, container를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_base_kustomization_resources.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 local source text와 문서만 검사합니다. `kubectl apply`, resource 생성, Secret 주입, image build, container execution, cluster connection, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 YAML render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

이는 별도의 local render 확인입니다. 성공하더라도 Kubernetes API connection, object admission, controller reconciliation 또는 실제 cluster state를 증명하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | 다섯 base file entry의 spelling과 optional directory entry를 비교한다 | 의도된 예제 변경이면 Kustomization·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| optional artifact가 base에 들어감 | `batch/`, `storage/`, `autoscaling/`이 별도 학습 집합인지 확인한다 | base와 optional lesson의 책임을 다시 분리한다. 실행 결과라고 주장하지 않는다. |
| Secret을 base에 넣고 싶음 | `secret.example.yaml`은 적용하지 않는 placeholder임을 확인한다 | 실제 Secret·credential을 저장하지 말고 승인된 운영 configuration 절차로 인계한다. |
| render가 성공했으므로 배포됐다고 생각함 | render와 API admission·reconciliation이 다름을 확인한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 runtime evidence를 수집한다. |

## 6. 완료 체크리스트

- [ ] 다섯 base resource와 optional 학습 집합을 구분했다.
- [ ] `base_kustomization_declares_only_example_core_resources`가 local file check임을 설명할 수 있다.
- [ ] `secret.example.yaml` exclusion이 Secret safety 또는 object 부재의 증거가 아님을 이해했다.
- [ ] render, controller reconciliation, Pod 실행, cluster state가 not verified임을 유지했다.
- [ ] 실제 Secret, credential, Kubernetes API connection, image build, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

Base Kustomization의 다섯 example core resource entry와 optional artifact exclusion은 검토 가능한 정적 계약입니다. `true` 결과는 local placeholder text가 예상 모양이라는 뜻일 뿐 render success, object creation, controller behavior 또는 deployment의 증거가 아닙니다. 실행 증거가 없으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
