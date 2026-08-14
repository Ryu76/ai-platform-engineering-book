# Job canonical placeholder completion boundary: 전체 source-text의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `k8s/volume11/batch/job.yaml` 전체가 한 번 완료하는 local-only 예제 Job인지 읽는다.
- `job_is_the_canonical_local_placeholder_completion_boundary`가 local source-text equality check임을 설명한다.
- source text, YAML/Kustomize 처리, Job controller의 완료·재시도 동작을 서로 다른 증거로 구분한다.

## 2. 정적 계약의 범위

`k8s/volume11/batch/job.yaml`은 현재 다음 UTF-8 source text와 정확히 일치해야 합니다.

```yaml
# Local-only teaching manifest. The image is deliberately not pullable; do not apply it.
apiVersion: batch/v1
kind: Job
metadata:
  name: ai-platform-maintenance-once
  namespace: ai-platform-example
  labels:
    app.kubernetes.io/name: ai-platform-maintenance
    app.kubernetes.io/part-of: ai-platform-example
    app.kubernetes.io/component: batch
spec:
  completions: 1
  parallelism: 1
  backoffLimit: 2
  activeDeadlineSeconds: 120
  ttlSecondsAfterFinished: 300
  template:
    metadata:
      labels:
        app.kubernetes.io/name: ai-platform-maintenance
        app.kubernetes.io/component: batch
    spec:
      restartPolicy: Never
      securityContext:
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: maintenance
          # Documentation-only placeholder. Do not replace outside an approved environment.
          image: example.invalid/ai-platform-maintenance:0.1.0
          imagePullPolicy: IfNotPresent
          command: ["python", "-c", "print('documentation-only maintenance placeholder')"]
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 10001
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              cpu: 100m
              memory: 128Mi
```

`job_is_the_canonical_local_placeholder_completion_boundary`는 위 문자열과 파일 전체를 비교합니다. header comment, API/kind, example name·namespace·labels, completion/retry/time/TTL 경계, Pod template, placeholder image·출력 전용 command, security context, resource request/limit의 순서·공백·들여쓰기까지 바뀌거나 다른 field가 추가되면 `false`입니다. 이는 한 번 완료하는 batch lesson의 검토 가능한 source layout 계약입니다.

> [!WARNING]
> 이 check는 local source text의 완전 일치만 확인합니다. YAML validity, Kustomize parse 또는 render, filesystem target 존재·권한·symlink, Kubernetes API admission, Job object 존재, Job controller의 Pod 생성·retry·completion·deadline·TTL 처리, image pull, command 실행, security enforcement, resource enforcement, data effect, network traffic 또는 deployment를 증명하지 않습니다. runtime evidence는 **not verified**이며 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 왜 전체 Job을 읽는가

앞 장의 batch Kustomization equality는 두 sibling resource가 분리된 bundle에 있다는 것을 읽습니다. 이 장은 그중 `job.yaml` 한 파일의 모든 선언이 고정된 placeholder completion boundary인지 확인합니다. 예를 들어 command, image, service account, environment, volume, host path, privilege, completion 또는 retry 값을 추가하면 source equality가 실패하여 교육용 형상 변경을 review 대상으로 드러냅니다.

이 실패는 Kubernetes가 해당 변경을 거부하거나 Job이 실행되었다는 판정이 아닙니다. 반대로 `true`도 `example.invalid` image를 pull하지 않았거나 command가 data effect를 만들지 않았다는 증거가 아닙니다. 실제 batch 작업에는 승인된 image provenance, 최소 권한, 입력 범위, Secret, network policy, idempotency key, audit, backup과 recovery evidence가 별도로 필요합니다. 이 lesson에는 실제 path, kubeconfig, Secret, credential 또는 remote resource를 추가하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.job_is_the_canonical_local_placeholder_completion_boundary`가 `true`인지 확인합니다. review는 local text만 읽으며 Docker daemon, Kubernetes API, network, container 또는 filesystem 밖 path를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_job_canonical_placeholder_completion.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 source text와 문서만 검사합니다. Kustomize render, `kubectl apply`, Job 생성, image build/pull, container execution, Kubernetes API connection, controller reconciliation, retry, completion, TTL cleanup, rollout, rollback 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11/batch
```

이 명령은 batch bundle의 별도 local YAML render 확인입니다. 성공하더라도 canonical Job equality가 filesystem provenance, API admission, Job controller behavior, image availability, command effect 또는 cluster state를 대체하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | canonical block과 file 전체의 comment·field·command·공백을 비교한다 | 의도된 example 변경이면 manifest·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| placeholder Job에 env, volume 또는 service account를 추가하고 싶음 | 새 입력·권한·mount가 local-only boundary를 바꾸는지 확인한다 | 실제 값·경로·credential을 넣지 말고 승인된 security/operations review로 인계한다. |
| render가 성공했으므로 Job이 완료되었다고 생각함 | source equality, render, API admission·controller completion이 다름을 기록한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 필요한 evidence를 수집한다. |
| `backoffLimit`이 안전한 재시도를 보장한다고 생각함 | 이 check가 Python local text comparison임을 확인한다 | idempotency, data effect, retry policy, audit와 recovery는 별도 검증한다. |

## 6. 완료 체크리스트

- [ ] Job file이 canonical placeholder comment·metadata·completion/retry/time·Pod template만 가진다는 source-text 계약을 확인했다.
- [ ] `job_is_the_canonical_local_placeholder_completion_boundary`가 local equality check임을 설명할 수 있다.
- [ ] check 성공이 YAML parse, Kustomize render, Job controller retry/completion 또는 image pull을 뜻하지 않음을 구분했다.
- [ ] Kubernetes API, Job controller, Pod, data effect, network와 deployment가 not verified임을 유지했다.
- [ ] 실제 path, Secret, credential, image, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

canonical Job equality는 완료·재시도·시간·placeholder security 경계를 한 local source file에서 검토하게 하는 교육용 계약입니다. `true`는 현재 file 전체가 예상 text에 정확히 일치한다는 뜻뿐입니다. YAML parsing, Kustomize behavior, Kubernetes API admission, Job controller reconciliation, Pod execution과 deployment는 not verified이므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
