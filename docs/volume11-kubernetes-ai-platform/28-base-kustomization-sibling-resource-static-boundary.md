# Base Kustomization sibling resource: 정확한 local 파일명의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- base `kustomization.yaml`의 resource entry가 의도한 다섯 sibling example 파일명과 정확히 일치하는지 읽는다.
- `base_kustomization_resource_entries_are_exact_local_example_filenames`가 local source-text check임을 설명한다.
- 파일명 문자열, Kustomize resolution/render, Kubernetes object·controller 동작을 서로 다른 증거로 구분한다.

## 2. 정적 계약의 범위

`k8s/volume11/kustomization.yaml`의 `resources:` 아래 entry는 현재 다음 순서의 정확한 파일명만 가집니다.

```text
namespace.yaml
configmap.yaml
deployment.yaml
service.yaml
ingress.yaml
```

이 check는 들여쓰기 두 칸으로 시작하는 list entry를 local UTF-8 text에서 읽어 tuple로 비교합니다. 각 entry에는 `/` 또는 `\` separator가 없으므로 이 작은 base가 `batch/`, `storage/`, `autoscaling/`, parent path 또는 다른 directory를 resource entry로 선언하지 않는다는 문자열 계약을 검토합니다.

> [!WARNING]
> 이는 filename text의 제한된 계약입니다. 실제 filesystem target 존재·권한·symlink, Kustomize parsing 또는 resource resolution/render, Kubernetes API admission, Namespace/object 존재, controller reconciliation, image pull, Pod 실행, network traffic 또는 deployment를 증명하지 않습니다. runtime evidence는 **not verified**이며 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 왜 exact list를 읽는가

앞 장의 core-resource check는 필요한 다섯 entry와 알려진 optional example entry의 부재를 읽습니다. 이 장의 check는 추가 entry도 허용하지 않도록 전체 list를 비교합니다. 따라서 학습용 base에 우연히 다른 local file, relative directory 또는 optional lesson set이 포함되는 text 변경을 review에서 드러낼 수 있습니다.

그러나 exact filename list가 Kustomize가 해당 파일을 열었다는 뜻은 아닙니다. Kustomize version과 loader behavior, filesystem case sensitivity, overlay composition, YAML validity와 rendered object는 별도 evidence입니다. 이 lesson은 remote URL, 실제 path, kubeconfig, Secret 또는 credential을 추가하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.base_kustomization_resource_entries_are_exact_local_example_filenames`가 `true`인지 확인합니다. review는 local text만 읽으며 filesystem 밖의 경로를 resolve하거나 Docker daemon, Kubernetes API, network, container를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_base_kustomization_sibling_resources.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 source text와 문서만 검사합니다. Kustomize resolution 실행, `kubectl apply`, resource 생성, image build/pull, container execution, Kubernetes API connection, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

이 명령은 별도의 local YAML render 확인입니다. 성공하더라도 filesystem provenance, API admission, controller reconciliation 또는 cluster state의 증거는 아닙니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | `resources:` entry의 순서·이름·separator를 base text와 비교한다 | 의도된 example 변경이면 Kustomization·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| optional lesson resource를 base에 넣고 싶음 | base의 purpose와 optional set의 분리 책임을 확인한다 | 별도 local lesson Kustomization을 유지하거나 승인된 design review로 인계한다. |
| render가 성공했으므로 file/object가 존재한다고 생각함 | render, filesystem resolution, API admission·object existence가 다름을 기록한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 필요한 evidence를 수집한다. |
| path traversal 안전성이 보장된다고 생각함 | 이 check가 현재 filename text에서 separator만 배제함을 확인한다 | loader·filesystem security와 provenance는 별도 security review에서 검증한다. |

## 6. 완료 체크리스트

- [ ] base resource entry가 정확한 다섯 sibling example 파일명임을 확인했다.
- [ ] `base_kustomization_resource_entries_are_exact_local_example_filenames`가 local text check임을 설명할 수 있다.
- [ ] exact filename text가 filesystem resolution, Kustomize render 또는 object creation 증거가 아님을 구분했다.
- [ ] Kubernetes API, controller reconciliation, Pod, network와 deployment가 not verified임을 유지했다.
- [ ] 실제 path, Secret, credential, image, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

정확한 sibling filename list는 작은 base의 검토 가능한 source-text 계약입니다. `true`는 현재 다섯 entry가 예상 순서와 이름이며 path separator가 없다는 뜻뿐입니다. filesystem resolution, Kustomize behavior, Kubernetes API admission, controller reconciliation와 deployment는 not verified이므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.