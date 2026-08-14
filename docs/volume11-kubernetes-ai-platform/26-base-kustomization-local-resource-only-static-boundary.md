# Base Kustomization local-only: 원격 참조·생성기 없는 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- base `kustomization.yaml`이 local example resource entry만 가진 source-text 계약인지 읽는다.
- remote base, component, generator, image transform, patch, transformer가 없는 현재 예제 경계를 구분한다.
- `base_kustomization_is_local_resource_only_example_contract`가 local text check임을 설명한다.
- Kustomize input resolution·render와 Kubernetes controller 행동을 같은 증거로 혼동하지 않는다.

## 2. 정적 계약의 범위

`k8s/volume11/kustomization.yaml`은 Kustomization API/version, `resources:`와 다섯 local example resource entry를 선언합니다. 현재 base text에는 다음 항목이 없습니다.

```text
remote URL (http://, https://, git::)
bases:, components:
generators:, configMapGenerator:, secretGenerator:
images:, patches:, patchesStrategicMerge:, transformers:
```

이는 의도적으로 작은 학습 artifact입니다. `secret.example.yaml`은 여전히 base에서 제외되고, `batch/`·`storage/`·`autoscaling/`은 별도의 local lesson 집합입니다. manifest의 image·host·IngressClass·StorageClass는 예제 또는 placeholder이며 실제 Secret·credential·remote repository를 포함하지 않습니다.

> [!WARNING]
> 이 계약은 local UTF-8 base Kustomization text만 읽습니다. remote base 또는 generator keyword가 없다는 결과는 Kustomize parse/input resolution/render 성공, filesystem 경로 접근, generated object, Secret 안전성, Kubernetes API connection, admission, controller reconciliation, image pull, Pod 실행, network traffic 또는 deployment를 증명하지 않습니다. 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 관계 읽기

```text
k8s/volume11/kustomization.yaml (local text only)
  └── resources: five local example file names

remote base/component/generator/transform/patch input ── absent from this text
Kustomize resolution/render, API admission, controller reconciliation ── not verified
```

부재 검사는 현재 파일의 제한된 문자열 계약입니다. 미래에 remote base, generator 또는 patch가 필요해지면 그 입력의 provenance, review와 execution boundary를 별도로 설계해야 합니다. 이 check가 remote input이 안전하거나 실행 불가능하다고 보장하지는 않습니다.

## 4. local-only 실습

### 4.1 artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.base_kustomization_is_local_resource_only_example_contract`가 `true`인지 확인합니다. check는 local Kustomization text의 required header와 excluded keyword만 읽습니다. Git fetch, remote base resolution, generator 실행, Docker daemon, Kubernetes API, network, container를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_base_kustomization_local_only.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 local source text와 문서만 검사합니다. remote repository access, `kubectl apply`, object 생성, image build, container execution, cluster connection, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 YAML render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

이는 별도의 local render 확인입니다. 성공하더라도 remote input resolution의 안전성, Kubernetes API connection, object admission, controller reconciliation 또는 실제 cluster state를 증명하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | header, `resources:`, excluded keyword spelling을 base text에서 비교한다 | 의도된 예제 변경이면 Kustomization·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| remote base가 필요해 보임 | input URL, revision pin, owner와 review evidence가 있는지 별도로 확인한다 | 이 학습 base에 URL이나 credential을 넣지 말고 승인된 dependency/provenance 절차로 인계한다. |
| generator로 설정을 만들고 싶음 | generator output, non-secret input과 Secret handling 책임을 구분한다 | 실제 Secret·credential을 저장하지 말고 승인된 운영 configuration 절차를 사용한다. |
| render가 성공했으므로 배포됐다고 생각함 | render와 API admission·controller reconciliation이 다름을 확인한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 runtime evidence를 수집한다. |

## 6. 완료 체크리스트

- [ ] local `resources:` text와 remote/generator/transform input 부재를 구분했다.
- [ ] `base_kustomization_is_local_resource_only_example_contract`가 local file check임을 설명할 수 있다.
- [ ] keyword 부재가 remote input 안전성, Kustomize render 또는 object 부재의 증거가 아님을 이해했다.
- [ ] render, controller reconciliation, Pod 실행, cluster state가 not verified임을 유지했다.
- [ ] 실제 remote repository, Secret, credential, Kubernetes API connection, image build, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

Base Kustomization의 local resource-only 모양은 검토 가능한 정적 계약입니다. `true` 결과는 현재 placeholder source text에 remote input과 generator/transform keyword가 없다는 뜻일 뿐 Kustomize input resolution, render, object creation, controller behavior 또는 deployment의 증거가 아닙니다. 실행 증거가 없으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
