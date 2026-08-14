# Batch Kustomization local bundle: 두 resource source-text의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `k8s/volume11/batch/kustomization.yaml`이 Job과 suspended CronJob을 위한 별도 local bundle임을 읽는다.
- `batch_kustomization_is_the_canonical_local_two_resource_lesson_bundle`가 local source-text equality check임을 설명한다.
- bundle source text, Kustomize parse/render, Job/CronJob controller 동작을 서로 다른 증거로 구분한다.

## 2. 정적 계약의 범위

`k8s/volume11/batch/kustomization.yaml`은 현재 다음 UTF-8 source text와 정확히 일치해야 합니다.

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
# Local render-only batch lesson. It is intentionally separate from ../kustomization.yaml.
resources:
  - job.yaml
  - cronjob.yaml
```

`batch_kustomization_is_the_canonical_local_two_resource_lesson_bundle`는 위 문자열과 파일 전체를 비교합니다. 따라서 API/version header, 분리 이유를 설명하는 comment, `resources:` block, 두 sibling filename의 순서, 들여쓰기, 빈 줄이 바뀌거나 다른 top-level field·resource가 추가되면 `false`입니다. 이는 batch lesson source layout이 base API bundle과 분리되어 있고 local `job.yaml`과 `cronjob.yaml`만 선언한다는 교육용 계약입니다.

> [!WARNING]
> 이 check는 local source text의 완전 일치만 확인합니다. YAML validity, Kustomize parse 또는 resource resolution/render, filesystem target 존재·권한·symlink, Kubernetes API admission, Job/CronJob object 존재, scheduler·Job/CronJob controller reconciliation, schedule 평가, Pod 생성, image pull, command 실행, data effect, network traffic 또는 deployment를 증명하지 않습니다. runtime evidence는 **not verified**이며 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 별도 bundle을 읽는 이유

기본 `k8s/volume11/kustomization.yaml`은 Namespace, ConfigMap, Deployment, Service, Ingress만 가진 작은 API 예제입니다. batch bundle은 한 번 완료하는 Job과 `suspend: true` CronJob을 그 기본 bundle에 섞지 않고 local render 대상으로만 묶습니다.

두 entry가 source text에 있다는 사실은 Job 또는 CronJob이 안전하다는 판정이 아닙니다. 특히 `suspend: true`는 controller가 실제로 새 Job 생성을 멈췄다는 증거가 아니며, `example.invalid` image도 pull 시도·Pod 실행·데이터 변경이 없었다는 증거가 아닙니다. 운영에서 bundle을 바꾸려면 실제 명령, 승인된 입력, Secret, service account, image provenance, rollback, scheduling과 data-effect evidence를 별도로 검토해야 합니다. 이 lesson에는 실제 path, kubeconfig, Secret, credential 또는 remote resource를 추가하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.batch_kustomization_is_the_canonical_local_two_resource_lesson_bundle`가 `true`인지 확인합니다. review는 local text만 읽으며 Docker daemon, Kubernetes API, network, container 또는 filesystem 밖 path를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_batch_kustomization_local_bundle.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 source text와 문서만 검사합니다. Kustomize render, `kubectl apply`, resource 생성, image build/pull, container execution, Kubernetes API connection, scheduled execution, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11/batch
```

이 명령은 별도의 local YAML render 확인입니다. 성공하더라도 canonical text equality가 YAML parse, filesystem provenance, API admission, controller reconciliation, schedule 실행 또는 cluster state를 대체하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | canonical block과 file 전체의 comment·header·entry·공백을 비교한다 | 의도된 example 변경이면 Kustomization·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| `job.yaml`과 `cronjob.yaml` 외 entry가 보임 | 기본 API bundle에 포함될 수 있는 resource인지 확인한다 | local-only lesson scope를 다시 검토하고 runtime 영향은 별도 evidence로 남긴다. |
| render가 성공했으므로 Job이 실행되었다고 생각함 | source equality, render, API admission·controller state가 다름을 기록한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 필요한 evidence를 수집한다. |
| `suspend: true`가 실행 방지를 증명한다고 생각함 | 이 check는 Python local text comparison임을 확인한다 | controller behavior, scheduling, image policy와 data effect는 별도 security·operations review에서 검증한다. |

## 6. 완료 체크리스트

- [ ] batch file이 canonical header, 분리 comment, 두 resource entry만 가진다는 source-text 계약을 확인했다.
- [ ] `batch_kustomization_is_the_canonical_local_two_resource_lesson_bundle`가 local equality check임을 설명할 수 있다.
- [ ] check 성공이 YAML parse, Kustomize render, Job/CronJob controller 실행 또는 image pull을 뜻하지 않음을 구분했다.
- [ ] Kubernetes API, scheduler, controller, Pod, network와 deployment가 not verified임을 유지했다.
- [ ] 실제 path, Secret, credential, image, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

canonical batch bundle equality는 Job과 suspended CronJob을 base API example에서 분리하는 검토 가능한 source-text 계약입니다. `true`는 현재 file 전체가 예상 header·comment·두 sibling resource entry에 정확히 일치한다는 뜻뿐입니다. YAML parsing, Kustomize behavior, Kubernetes API admission, controller reconciliation, scheduled execution과 deployment는 not verified이므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
