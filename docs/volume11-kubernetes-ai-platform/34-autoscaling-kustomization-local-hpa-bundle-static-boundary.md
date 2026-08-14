# Autoscaling Kustomization local bundle: HPA source-text의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `k8s/volume11/autoscaling/kustomization.yaml`이 placeholder HPA만 조합하는 별도 local bundle임을 읽는다.
- `autoscaling_kustomization_is_the_canonical_local_hpa_lesson_bundle`가 local source-text equality check임을 설명한다.
- bundle source text, Kustomize parse/render, HPA controller의 scale 동작을 서로 다른 증거로 구분한다.

## 2. 정적 계약의 범위

`k8s/volume11/autoscaling/kustomization.yaml`은 현재 다음 UTF-8 source text와 정확히 일치해야 합니다.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - hpa.yaml
```

`autoscaling_kustomization_is_the_canonical_local_hpa_lesson_bundle`는 위 문자열과 파일 전체를 비교합니다. 따라서 API/version header, `resources:` block, 하나의 sibling filename, 들여쓰기 또는 빈 줄이 바뀌거나 다른 top-level field·resource가 추가되면 `false`입니다. 이는 autoscaling lesson source layout이 base API bundle과 분리되어 있고 local `hpa.yaml`만 선언한다는 교육용 계약입니다.

> [!WARNING]
> 이 check는 local source text의 완전 일치만 확인합니다. YAML validity, Kustomize parse 또는 resource resolution/render, filesystem target 존재·권한·symlink, Kubernetes API admission, HPA object 존재, metrics API availability, HPA controller의 target resolution·desired replica 계산·scale action, Deployment/Pod 생성, CPU measurement, network traffic 또는 deployment를 증명하지 않습니다. runtime evidence는 **not verified**이며 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 별도 bundle을 읽는 이유

기본 `k8s/volume11/kustomization.yaml`은 Namespace, ConfigMap, Deployment, Service, Ingress만 가진 작은 API 예제입니다. autoscaling bundle은 존재하지 않는 `ai-platform-api-example` target과 CPU 70% 목표를 가진 placeholder HPA를 그 기본 bundle에 섞지 않고 local render 대상으로만 묶습니다.

`hpa.yaml` entry가 source text에 있다는 사실은 HPA가 만들어졌거나 target Deployment를 찾았다는 판정이 아닙니다. `minReplicas: 2`, `maxReplicas: 5`, `averageUtilization: 70`도 metrics server가 CPU 값을 제공하거나 controller가 replica를 계산·변경했다는 증거가 아닙니다. 운영에서 bundle을 바꾸려면 승인된 target, workload request, metrics freshness, scale behavior, quota, node capacity, cost, alert와 rollback evidence를 별도로 검토해야 합니다. 이 lesson에는 실제 cluster endpoint, Secret, credential, remote resource 또는 실행 중인 workload를 추가하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.autoscaling_kustomization_is_the_canonical_local_hpa_lesson_bundle`가 `true`인지 확인합니다. review는 local text만 읽으며 Docker daemon, Kubernetes API, network, container 또는 filesystem 밖 path를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_autoscaling_kustomization_local_bundle.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 source text와 문서만 검사합니다. Kustomize render, `kubectl apply`, HPA/Deployment/Pod 생성, metrics server query, CPU measurement, image build/pull, container execution, Kubernetes API connection, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11/autoscaling
```

이 명령은 별도의 local YAML render 확인입니다. 성공하더라도 canonical text equality가 YAML parse, filesystem provenance, API admission, metrics pipeline, HPA controller reconciliation 또는 cluster state를 대체하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | canonical block과 file 전체의 header·entry·공백을 비교한다 | 의도된 example 변경이면 Kustomization·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| `hpa.yaml` 외 entry가 보임 | 기본 API bundle에 포함될 수 있는 resource인지 확인한다 | local-only lesson scope를 다시 검토하고 controller/runtime 영향은 별도 evidence로 남긴다. |
| render가 성공했으므로 autoscaling이 동작한다고 생각함 | source equality, render, API admission·metrics/controller state가 다름을 기록한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 필요한 evidence를 수집한다. |
| `ai-platform-api-example`이 실제 target을 뜻한다고 생각함 | placeholder는 base Deployment나 운영 workload를 지시하지 않는다는 점을 확인한다 | target, metrics, capacity, cost와 rollback은 별도 security·operations review에서 검증한다. |

## 6. 완료 체크리스트

- [ ] autoscaling file이 canonical header와 하나의 HPA resource entry만 가진다는 source-text 계약을 확인했다.
- [ ] `autoscaling_kustomization_is_the_canonical_local_hpa_lesson_bundle`가 local equality check임을 설명할 수 있다.
- [ ] check 성공이 YAML parse, Kustomize render, metrics API 또는 HPA scale action을 뜻하지 않음을 구분했다.
- [ ] Kubernetes API, metrics server, HPA controller, target Deployment/Pod, CPU measurement와 deployment가 not verified임을 유지했다.
- [ ] 실제 target, cluster endpoint, Secret, credential, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

canonical autoscaling bundle equality는 placeholder HPA를 base API example에서 분리하는 검토 가능한 source-text 계약입니다. `true`는 현재 file 전체가 예상 header·하나의 sibling HPA resource entry에 정확히 일치한다는 뜻뿐입니다. YAML parsing, Kustomize behavior, Kubernetes API admission, metrics pipeline, HPA reconciliation·scale action과 deployment는 not verified이므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
