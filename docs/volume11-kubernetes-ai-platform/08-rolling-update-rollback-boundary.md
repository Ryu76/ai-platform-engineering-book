# Rolling Update와 Rollback: Deployment revision 경계 읽기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Deployment의 `RollingUpdate` 전략이 새 ReplicaSet으로 점진적으로 교체하는 방식을 설명한다.
- `maxUnavailable`, `maxSurge`, `progressDeadlineSeconds`, `revisionHistoryLimit`의 책임을 구분한다.
- rollback은 적용된 Deployment의 revision을 대상으로 하는 운영 작업임을 설명한다.
- 실제 이미지, cluster 또는 rollout 없이 Manifest 계약을 로컬에서 검증한다.

## 2. 왜 필요한가

AI API를 새 버전으로 바꿀 때 기존 Pod를 모두 동시에 없애면 요청이 끊기거나 readiness가 아직 끝나지 않은 새 Pod로 트래픽이 갈 위험이 있습니다. Deployment의 Rolling Update는 새 Pod와 기존 Pod의 수를 일정 범위 안에서 조절하도록 controller에 정책을 제공합니다.

그러나 YAML에 전략을 선언했다고 안전한 배포나 복구가 보장되지는 않습니다. 새 이미지의 호환성, migration, 모델 warm-up, readiness, Service endpoint 전파, 관측 경보, 변경 승인과 의존 서비스의 버전 호환성은 모두 별도 검토 대상입니다. rollback 역시 명령 한 줄로 끝나는 일반적인 취소 기능이 아니라, 이미 적용되어 revision이 만들어진 workload와 그 주변의 데이터·호환성 상태를 되돌리는 운영 판단입니다.

이 장은 기본 `k8s/volume11/deployment.yaml`에 있는 비실행용 `example.invalid/ai-platform-api:0.1.0` 이미지와 rollout 계약만 읽습니다. 실제 이미지 교체, rollout 실행, rollback 실행, 클러스터 적용을 하지 않습니다.

> [!WARNING]
> 이 slice의 `kubectl kustomize`는 로컬 YAML 조합 전용입니다. `kubectl apply`, `kubectl set image`, `kubectl rollout restart`, `kubectl rollout status`, `kubectl rollout undo`를 실행하지 마세요. 이 저장소에는 revision을 만들 Kubernetes API server, 승인된 이미지, 실제 namespace 또는 rollback 대상이 없습니다.

## 3. 핵심 개념

- **Deployment:** 동일한 Pod template을 원하는 수만큼 유지하고 변경 시 ReplicaSet을 조정하는 Kubernetes workload controller입니다.
- **RollingUpdate:** 기존 ReplicaSet을 한 번에 삭제하지 않고 새 ReplicaSet을 늘리면서 이전 ReplicaSet을 줄이는 Deployment 전략입니다.
- **`maxUnavailable: 0`:** update 중 원하는 replica 수에서 unavailable Pod를 허용하지 않도록 요청하는 예제 경계입니다. cluster capacity나 readiness 실패 때문에 항상 무중단이 보장되는 것은 아닙니다.
- **`maxSurge: 1`:** update 중 원하는 replica 수보다 최대 한 개의 추가 Pod를 허용하도록 요청하는 예제 경계입니다. quota, node capacity, 이미지 pull, admission policy가 이를 실제로 가능하게 하는지는 별도입니다.
- **`progressDeadlineSeconds: 120`:** Deployment가 진행되지 않는 상태를 판단하는 시간 경계입니다. 이를 넘었다고 controller가 자동 rollback하거나 원인을 해결하지는 않습니다.
- **`revisionHistoryLimit: 2`:** 이전 ReplicaSet revision을 최대 두 개까지 보존하도록 요청하는 정리 정책입니다. 보존된 revision이 데이터 migration, Secret, ConfigMap, 외부 API 계약까지 되돌려 주지는 않습니다.
- **rollback:** 적용된 Deployment가 기록한 이전 revision을 다시 선택하는 cluster-side 작업입니다. 이 로컬 Manifest 렌더링만으로는 revision이 생성되지 않습니다.

## 4. 동작 구조

```text
로컬 파일: k8s/volume11/deployment.yaml
  image: example.invalid/ai-platform-api:0.1.0  ─── 비실행용 자리표시자
  replicas: 2
  strategy: RollingUpdate
    maxUnavailable: 0
    maxSurge: 1
  progressDeadlineSeconds: 120
  revisionHistoryLimit: 2
        │
        ▼
kubectl kustomize k8s/volume11  ─── 로컬 렌더링만 수행
        │
        ▼
Deployment YAML 출력 (revision, Pod, ReplicaSet, Event는 생성되지 않음)

클러스터 적용 / 실제 image 변경 / rollout / rollback: 이 slice 범위 밖
```

`replicas: 2`, `maxUnavailable: 0`, `maxSurge: 1` 조합은 update 중 controller가 목표 replica보다 최대 하나 많은 Pod를 만들 수 있다는 정책 예시입니다. 이것은 자원 예약이나 사용자 요청 성공률을 수학적으로 보장하지 않습니다. 새 Pod가 readiness에 실패하거나 node에 배치되지 않으면 update는 진행 deadline을 넘을 수 있습니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/deployment.yaml` | 예제 이미지, probe, resource request와 Rolling Update 계약을 가진 Deployment |
| `k8s/volume11/kustomization.yaml` | Namespace, ConfigMap, Deployment, Service, Ingress를 조합하는 기본 로컬 렌더링 집합 |
| `tests/integration/test_volume11_health_artifacts.py` | update 전략, revision 보존, 자리표시자와 비밀값 부재를 검사하는 오프라인 테스트 |
| `docs/volume11-kubernetes-ai-platform/07-hpa-cpu-scaling-boundary.md` | replica 수를 조절하는 HPA 계약과 이 Deployment 전략의 책임 경계를 비교하는 이전 장 |

6.1에는 `kubectl` CLI가 필요합니다. kubeconfig, Kubernetes cluster, container runtime, registry 접근, 실제 이미지 또는 Secret은 필요하지 않습니다. 6.2에는 Python과 `uv`가 필요합니다.

## 6. 단계별 실습

### 6.1 기본 Deployment를 로컬에서 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

출력에서 `kind: Deployment`, `image: example.invalid/ai-platform-api:0.1.0`, `type: RollingUpdate`, `maxUnavailable: 0`, `maxSurge: 1`, `progressDeadlineSeconds: 120`, `revisionHistoryLimit: 2`를 확인합니다. 이 명령은 로컬 파일을 조합할 뿐 API server에 연결하지 않으므로 Pod, ReplicaSet, revision 또는 Event를 만들지 않습니다. 명령을 `apply`로 바꾸지 마세요.

### 6.2 계약을 오프라인 테스트로 확인

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 예제 이미지, Rolling Update 전략, unavailable/surge 범위, revision 보존 수, 진행 deadline과 Secret·토큰·암호·실행 중인 restart annotation 부재를 검사합니다. 컨테이너를 시작하거나 registry에 연결하거나 Deployment를 생성하지 않습니다.

## 7. 코드와 Manifest 설명

`strategy.type: RollingUpdate`는 Deployment controller에 점진 교체 전략을 선택하게 합니다. `rollingUpdate.maxUnavailable: 0`과 `rollingUpdate.maxSurge: 1`은 교체 중 Pod 수 변화의 정책 범위입니다. 이 값은 Deployment의 `spec`에 있고 container command나 환경 변수에는 없습니다.

`revisionHistoryLimit: 2`는 controller가 이전 ReplicaSet을 계속 무한히 보관하지 않도록 합니다. 반면 `progressDeadlineSeconds: 120`은 rollout 진행을 기다리는 시간 경계입니다. 둘 다 적용 후 controller가 해석하는 값이며, `kubectl kustomize`만으로는 그 동작을 재현하거나 검증할 수 없습니다.

이 Manifest는 기존 `/readyz` readiness probe를 유지합니다. Rolling Update 정책은 readiness probe 자체를 대체하지 않습니다. 새 Pod가 Service endpoint에 들어갈 시점과 liveness에 따른 재시작 책임도 구분해서 검토해야 합니다.

## 8. 정상 실행 결과

6.1 출력에는 대략 다음 구조가 포함됩니다.

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  replicas: 2
  revisionHistoryLimit: 2
  progressDeadlineSeconds: 120
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
```

이 출력에는 새 ReplicaSet 이름, revision 번호, `ProgressDeadlineExceeded` condition, `kubectl rollout` 결과 또는 실제 image digest가 없어야 합니다. 6.2는 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `kubectl kustomize`를 찾을 수 없음 | `kubectl` CLI가 설치되지 않았을 수 있습니다. | 6.2의 Python 테스트를 먼저 실행하고, 승인된 개발 환경에 CLI를 설치한 뒤 6.1의 로컬 렌더링만 다시 실행합니다. |
| YAML 출력에 `RollingUpdate`가 없음 | `deployment.yaml`의 `strategy` 블록이 지워졌거나 들여쓰기가 바뀌었을 수 있습니다. | `type: RollingUpdate`, `maxUnavailable: 0`, `maxSurge: 1`을 복원하고 다시 렌더링·테스트합니다. |
| 실제 환경에서 rollout이 deadline을 넘김 | readiness, scheduler capacity, image pull, quota, admission 또는 application startup이 원인일 수 있습니다. | 이 slice에서 cluster를 변경하지 말고, 승인된 운영 절차에서 Event, Deployment condition, Pod 상태, resource와 image provenance를 조사합니다. |
| rollback 후에도 오류가 지속됨 | 이전 Pod template만 복원됐고 migration, ConfigMap, Secret, 외부 API 또는 데이터 상태는 복원되지 않았을 수 있습니다. | 승인된 incident 절차에 따라 호환성·데이터 복구·트래픽·관측 증거를 확인합니다. 이 저장소의 예제로 rollback 명령을 실행하지 않습니다. |

## 10. 응용 실습

실제 값을 적용하지 말고 다음 질문에 대한 검토표를 작성합니다.

1. API의 readiness 시간이 길어질 때 `progressDeadlineSeconds`를 어떻게 근거와 함께 정할지 적습니다.
2. `maxSurge: 1`이 node capacity와 비용에 미치는 영향을 계산이 아닌 관측·승인 항목으로 정리합니다.
3. schema migration이 있는 변경에서 Pod template rollback만으로 충분하지 않은 이유를 설명합니다.
4. HPA가 동시에 replica 수를 변경할 때 Deployment update 정책과 capacity 계획이 충돌할 수 있는 조건을 찾습니다.

검토표에는 실제 cluster 이름, namespace, registry URL, image digest, 사용자 데이터나 인증 정보를 넣지 않습니다.

## 11. 실무 적용

승인된 환경에서 rollout 또는 rollback을 검토하기 전에 다음을 확인합니다.

1. immutable image digest, SBOM·취약점 검토, 애플리케이션과 dependency의 호환성 증거
2. Pod startup, model warm-up, `/readyz` 통과 시간과 Service endpoint 전파 지연
3. `maxSurge`가 필요한 CPU·메모리와 namespace quota, node capacity, autoscaler 비용에 미치는 영향
4. migration, cache, queue, index, 외부 side effect가 이전 revision과 호환되는지
5. progress deadline 초과, partial availability, bad revision에서의 alert, 승인자, 중단·복구 기준
6. rollback이 가능하다는 가정 대신 rollback 후 검증할 SLO, error rate, latency, 데이터 무결성 지표

운영에서 참고할 수 있는 명령 형태로 `kubectl rollout undo deployment/<name>`가 알려져 있어도, 그것은 현재 slice에서 실행할 명령이 아닙니다. 실제 namespace·revision·승인 절차와 관측 증거 없이는 사용하지 않습니다.

## 12. 과제

- **기본:** `maxUnavailable`, `maxSurge`, `progressDeadlineSeconds`, `revisionHistoryLimit`의 역할을 각각 한 문장으로 설명합니다.
- **응용:** replicas 2인 서비스에서 update 중 일시적으로 생길 수 있는 Pod 수 범위를 이 예제의 정책으로 설명하고, scheduler가 이를 보장하지 않는 이유를 적습니다.
- **심화:** 데이터 migration을 포함한 변경에 대해 application revision rollback, 데이터 복구, traffic 차단을 구분한 incident runbook 초안을 작성합니다. 실제 command, cluster 주소, credential은 쓰지 않습니다.

## 13. 완료 체크리스트

- [ ] `RollingUpdate`가 기존과 새 ReplicaSet을 점진 교체하는 전략임을 설명할 수 있다.
- [ ] `maxUnavailable: 0`과 `maxSurge: 1`이 가용성이나 용량을 자동 보장하지 않음을 설명할 수 있다.
- [ ] `progressDeadlineSeconds: 120`과 `revisionHistoryLimit: 2`의 다른 책임을 구분했다.
- [ ] `kubectl kustomize k8s/volume11`로만 Deployment 형상을 로컬 렌더링했다.
- [ ] Volume 11 오프라인 테스트가 통과했다.
- [ ] 실제 이미지 교체, rollout 실행, rollback 실행, 클러스터 적용을 하지 않았다.
- [ ] 실제 Secret, registry, cluster 주소, namespace, 인증 정보를 저장하지 않았다.

## 14. 핵심 정리

Rolling Update는 새 Pod와 이전 Pod를 점진적으로 교체하도록 Deployment controller에 주는 정책입니다. 이 장은 `example.invalid` 이미지의 정적 예제에 `maxUnavailable: 0`, `maxSurge: 1`, 120초 진행 deadline, 두 개의 revision 보존 계약만 추가하고 로컬에서 검증했습니다. 적용된 revision의 rollback, 실제 이미지 변경, data migration, SLO 검증과 incident 대응은 승인을 받은 운영 환경에서 별도 증거와 절차로 다뤄야 합니다.
