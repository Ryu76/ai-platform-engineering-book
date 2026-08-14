# Base Kustomization canonical block: 전체 source-text의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 학습용 base `kustomization.yaml` 전체가 의도한 작은 canonical resource block인지 읽는다.
- `base_kustomization_is_the_canonical_example_resource_block`가 local source-text equality check임을 설명한다.
- source text의 정확한 일치, Kustomize parse/render, Kubernetes object·controller 동작을 서로 다른 증거로 구분한다.

## 2. 정적 계약의 범위

`k8s/volume11/kustomization.yaml`은 현재 다음 UTF-8 source text와 정확히 일치해야 합니다.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - configmap.yaml
  - deployment.yaml
  - service.yaml
  - ingress.yaml
```

이 check는 예상 문자열과 파일 전체를 비교합니다. 따라서 허용되지 않은 top-level field, 다른 resource block, comment, 빈 줄, 들여쓰기 또는 순서 변경도 `false`가 됩니다. 작은 예제 base가 다섯 sibling manifest만 선언하는 교육용 source layout인지 검토하는 계약입니다.

> [!WARNING]
> 이는 local source text의 완전 일치만 확인합니다. YAML validity, Kustomize parse 또는 resource resolution/render, filesystem target 존재·권한·symlink, Kubernetes API admission, Namespace/object 존재, controller reconciliation, image pull, Pod 실행, network traffic 또는 deployment를 증명하지 않습니다. runtime evidence는 **not verified**이며 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 왜 전체 block을 읽는가

앞 장의 exact sibling filename check는 `resources:` 아래 entry tuple과 path separator 부재를 검사합니다. 이 장은 그보다 좁게, 파일 전체가 canonical header와 하나의 resource block뿐인지 검사합니다. 예를 들어 생성기, patch, image transform 또는 별도 top-level field가 우연히 추가되면 filename list가 그대로여도 이 equality check는 실패합니다.

그 실패는 변경이 위험하거나 Kubernetes에서 거부된다는 판정이 아닙니다. 교육용 최소 base에서 벗어난 source-text 변경을 review 대상으로 올린다는 신호일 뿐입니다. 변경 의도가 있으면 design review에서 Kustomize version·loader·overlay·rendered object와 운영 책임을 별도로 평가합니다. 이 lesson은 remote URL, 실제 path, kubeconfig, Secret 또는 credential을 추가하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.base_kustomization_is_the_canonical_example_resource_block`가 `true`인지 확인합니다. review는 local text만 읽으며 Docker daemon, Kubernetes API, network, container 또는 filesystem 밖 path를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_base_kustomization_canonical_block.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 source text와 문서만 검사합니다. Kustomize render, `kubectl apply`, resource 생성, image build/pull, container execution, Kubernetes API connection, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

이 명령은 별도의 local YAML render 확인입니다. 성공하더라도 canonical text equality가 YAML parse, filesystem provenance, API admission, controller reconciliation 또는 cluster state를 대체하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | canonical block과 file 전체의 header·entry·공백을 비교한다 | 의도된 example 변경이면 Kustomization·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| resource list는 같지만 check가 실패함 | top-level field, comment, 빈 줄, indentation, 순서를 확인한다 | 필요한 변화인지 review하고 parse/render 영향은 별도 evidence로 남긴다. |
| render가 성공했으므로 object가 존재한다고 생각함 | source equality, render, API admission·object existence가 다름을 기록한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 필요한 evidence를 수집한다. |
| strict equality가 Kustomize policy를 강제한다고 생각함 | 이 check는 Python local text comparison임을 확인한다 | admission, RBAC, policy와 controller behavior는 별도 security·operations review에서 검증한다. |

## 6. 완료 체크리스트

- [ ] base file이 canonical header와 다섯 resource entry만 가진다는 source-text 계약을 확인했다.
- [ ] `base_kustomization_is_the_canonical_example_resource_block`가 local equality check임을 설명할 수 있다.
- [ ] check 실패가 YAML parse, Kustomize render 또는 Kubernetes rejection을 뜻하지 않음을 구분했다.
- [ ] Kubernetes API, controller reconciliation, Pod, network와 deployment가 not verified임을 유지했다.
- [ ] 실제 path, Secret, credential, image, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

canonical base block equality는 학습용 최소 Kustomization의 검토 가능한 source-text 계약입니다. `true`는 현재 file 전체가 예상 header와 다섯 sibling resource entry에 정확히 일치한다는 뜻뿐입니다. YAML parsing, Kustomize behavior, Kubernetes API admission, controller reconciliation와 deployment는 not verified이므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.