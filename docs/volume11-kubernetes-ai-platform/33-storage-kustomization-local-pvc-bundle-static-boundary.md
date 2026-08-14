# Storage Kustomization local bundle: PVC source-text의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `k8s/volume11/storage/kustomization.yaml`이 placeholder PVC를 위한 별도 local bundle임을 읽는다.
- `storage_kustomization_is_the_canonical_local_pvc_lesson_bundle`가 local source-text equality check임을 설명한다.
- bundle source text, Kustomize parse/render, PVC provisioning·binding 동작을 서로 다른 증거로 구분한다.

## 2. 정적 계약의 범위

`k8s/volume11/storage/kustomization.yaml`은 현재 다음 UTF-8 source text와 정확히 일치해야 합니다.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
# Local render-only storage lesson. It is intentionally separate from ../kustomization.yaml.
resources:
  - pvc.yaml
```

`storage_kustomization_is_the_canonical_local_pvc_lesson_bundle`는 위 문자열과 파일 전체를 비교합니다. 따라서 API/version header, base bundle과 분리되는 이유를 설명하는 comment, `resources:` block, 하나의 sibling filename, 들여쓰기 또는 빈 줄이 바뀌거나 다른 top-level field·resource가 추가되면 `false`입니다. 이는 storage lesson source layout이 base API bundle과 분리되어 있고 local `pvc.yaml`만 선언한다는 교육용 계약입니다.

> [!WARNING]
> 이 check는 local source text의 완전 일치만 확인합니다. YAML validity, Kustomize parse 또는 resource resolution/render, filesystem target 존재·권한·symlink, Kubernetes API admission, PVC object 존재, StorageClass selection, PV provisioning·binding, access-mode enforcement, volume attach/mount, data persistence, network traffic 또는 deployment를 증명하지 않습니다. runtime evidence는 **not verified**이며 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 별도 bundle을 읽는 이유

기본 `k8s/volume11/kustomization.yaml`은 Namespace, ConfigMap, Deployment, Service, Ingress만 가진 작은 API 예제입니다. storage bundle은 `example-storage-class`를 가진 placeholder PVC를 그 기본 bundle에 섞지 않고 local render 대상으로만 묶습니다.

`pvc.yaml` entry가 source text에 있다는 사실은 PVC가 provision되거나 bind되었다는 판정이 아닙니다. `ReadWriteOnce`, `Filesystem`, `1Gi`와 `example-storage-class`도 controller·CSI driver·storage backend가 실제로 그 요청을 수용하거나 data를 보존했다는 증거가 아닙니다. 운영에서 bundle을 바꾸려면 승인된 StorageClass, encryption, retention, backup/restore, access pattern, quota, cost, data classification과 migration evidence를 별도로 검토해야 합니다. 이 lesson에는 실제 storage endpoint, Secret, credential, cluster path 또는 remote resource를 추가하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.storage_kustomization_is_the_canonical_local_pvc_lesson_bundle`가 `true`인지 확인합니다. review는 local text만 읽으며 Docker daemon, Kubernetes API, network, container 또는 filesystem 밖 path를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_storage_kustomization_local_bundle.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 source text와 문서만 검사합니다. Kustomize render, `kubectl apply`, PVC/PV 생성·binding, StorageClass provisioning, data write, image build/pull, container execution, Kubernetes API connection, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11/storage
```

이 명령은 별도의 local YAML render 확인입니다. 성공하더라도 canonical text equality가 YAML parse, filesystem provenance, API admission, storage controller reconciliation, PVC binding 또는 cluster state를 대체하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | canonical block과 file 전체의 comment·header·entry·공백을 비교한다 | 의도된 example 변경이면 Kustomization·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| `pvc.yaml` 외 entry가 보임 | 기본 API bundle에 포함될 수 있는 resource인지 확인한다 | local-only lesson scope를 다시 검토하고 provisioning/runtime 영향은 별도 evidence로 남긴다. |
| render가 성공했으므로 volume이 bind되었다고 생각함 | source equality, render, API admission·storage controller state가 다름을 기록한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 필요한 evidence를 수집한다. |
| `example-storage-class`가 안전한 storage를 뜻한다고 생각함 | placeholder는 실재 StorageClass·backend를 지시하지 않는다는 점을 확인한다 | class policy, encryption, backup, retention, access와 data effect는 별도 security·operations review에서 검증한다. |

## 6. 완료 체크리스트

- [ ] storage file이 canonical header, 분리 comment, 하나의 PVC resource entry만 가진다는 source-text 계약을 확인했다.
- [ ] `storage_kustomization_is_the_canonical_local_pvc_lesson_bundle`가 local equality check임을 설명할 수 있다.
- [ ] check 성공이 YAML parse, Kustomize render, PVC provisioning/binding 또는 data persistence를 뜻하지 않음을 구분했다.
- [ ] Kubernetes API, storage controller, CSI driver, volume mount, data effect와 deployment가 not verified임을 유지했다.
- [ ] 실제 StorageClass, Secret, credential, storage endpoint, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

canonical storage bundle equality는 placeholder PVC를 base API example에서 분리하는 검토 가능한 source-text 계약입니다. `true`는 현재 file 전체가 예상 header·comment·하나의 sibling PVC resource entry에 정확히 일치한다는 뜻뿐입니다. YAML parsing, Kustomize behavior, Kubernetes API admission, storage provisioning/binding, data persistence와 deployment는 not verified이므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
