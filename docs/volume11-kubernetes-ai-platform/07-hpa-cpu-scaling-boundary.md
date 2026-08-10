# HPA: CPU 기반 확장 계약을 오프라인으로 읽기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `HorizontalPodAutoscaler`(HPA)가 Pod 수를 조절하는 controller임을 설명한다.
- `minReplicas`, `maxReplicas`, CPU `averageUtilization`이 만드는 확장 범위를 읽는다.
- HPA의 CPU 비율이 컨테이너 CPU request를 기준으로 계산된다는 점을 구분한다.
- metrics server, 부하 생성, 실제 Deployment 또는 클러스터 없이 Manifest를 로컬에서 검증한다.

## 2. 왜 필요한가

AI API의 요청량은 일정하지 않을 수 있습니다. HPA는 관측한 metric을 바탕으로 Deployment 같은 scale 대상의 replica 수를 범위 안에서 바꾸도록 Kubernetes에 요청합니다. 그러나 HPA YAML만으로 용량 계획, 지연 시간 목표, 모델 서버의 동시성 한계, 비용 통제, scale-out 가능성이 해결되지는 않습니다.

이 장은 의도적으로 `ai-platform-api-example`이라는 **존재하지 않는 예제 Deployment 이름**만 참조합니다. `k8s/volume11/autoscaling/`은 기본 Kustomize 집합에서 분리되어 있으며, 실제 metrics API·부하 도구·Secret·주소·이미지를 포함하지 않습니다. 그러므로 로컬 렌더링으로 정책 형상만 읽을 수 있고, 이 교재의 기본 API 예제나 실제 워크로드의 replica 수를 바꾸지 않습니다.

> [!WARNING]
> `k8s/volume11/autoscaling/`은 **로컬 렌더링 전용 학습 Manifest**입니다. `kubectl apply`, `kubectl create`, metrics server 설치, 부하 생성, 실제 Deployment 이름으로의 변경, 클러스터 연결을 실행하지 마세요. HPA가 올바르게 동작하는지 여부는 실제 운영 승인 환경의 metrics pipeline과 workload 특성에 달려 있습니다.

## 3. 핵심 개념

- **HPA:** metric을 관찰하여 scale 대상의 desired replica 수를 계산하는 Kubernetes controller입니다.
- **`scaleTargetRef`:** HPA가 조절하려고 하는 API version, kind, 이름의 참조입니다. 이 예제 이름은 의도적으로 base Deployment와 다릅니다.
- **`minReplicas`:** controller가 축소할 때 요청하는 하한입니다. 항상 가용성을 보장하는 값은 아닙니다.
- **`maxReplicas`:** controller가 확장할 때 요청하는 상한입니다. 이 값만으로 quota·노드 용량·비용 상한이 보장되지는 않습니다.
- **CPU `averageUtilization`:** Pod의 실제 CPU 사용량을 각 컨테이너 CPU request에 대한 비율로 읽는 resource metric target입니다. request가 없거나 metric을 가져올 수 없으면 기대한 계산이 되지 않을 수 있습니다.
- **metrics pipeline:** metrics server, 권한, 수집 지연과 누락을 포함해 HPA가 metric을 읽는 운영 경로입니다. 이 slice에는 없습니다.

## 4. 예제 확장 계약

```text
별도 로컬 렌더링 집합: k8s/volume11/autoscaling/

HorizontalPodAutoscaler: ai-platform-api-example
  scaleTargetRef: Deployment/ai-platform-api-example ── 존재하지 않는 예제 참조
  minReplicas: 2 ─────────────────────────────────────── 축소 하한 예시
  maxReplicas: 5 ─────────────────────────────────────── 확장 상한 예시
  cpu averageUtilization: 70 ─────────────────────────── CPU request 대비 목표 비율

기본 k8s/volume11/kustomization.yaml: HPA 미포함
metrics server / 실제 target Deployment / 부하 생성 / 클러스터 적용: 이 slice에 없음
```

`averageUtilization: 70`은 CPU 사용량이 언제나 70m이라는 뜻이 아닙니다. HPA resource metric의 utilization은 request에 대한 비율입니다. 예를 들어, 운영에서 각 Pod에 CPU request가 100m라고 **가정**하면 70% target은 평균 70m에 해당할 수 있습니다. request가 200m라면 같은 70%는 평균 140m에 해당할 수 있습니다. 이 수치는 이 예제에 request나 workload를 추가하라는 지시가 아니며, 실제 request와 target은 부하 시험 및 비용 검토로 정해야 합니다.

HPA는 원하는 replica 수를 조절할 뿐입니다. 새 Pod가 readiness를 통과하는 시간, 모델 파일의 cold start, node autoscaler, namespace quota, PodDisruptionBudget, downstream Qdrant·Redis·PostgreSQL 병목, 요청 queueing은 별도 책임입니다. 따라서 CPU 확장 정책을 latency SLO나 장애 복구 보장으로 해석하지 마세요.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/autoscaling/hpa.yaml` | 예제 target, 2~5 replica 범위, CPU 70% target을 가진 HPA |
| `k8s/volume11/autoscaling/kustomization.yaml` | HPA만 조합하는 별도 로컬 렌더링 집합 |
| `k8s/volume11/kustomization.yaml` | 안전을 위해 HPA를 포함하지 않는 기본 API 렌더링 집합 |
| `k8s/volume11/deployment.yaml` | CPU request가 명시된 기존 API 예제; HPA target이 아님 |
| `tests/integration/test_volume11_health_artifacts.py` | HPA placeholder target·범위·분리 경계를 검사하는 오프라인 테스트 |

Python과 `uv`가 필요합니다. 6.1에는 `kubectl` CLI가 필요하지만 kubeconfig, Kubernetes 클러스터, metrics server 또는 실행 중인 Pod는 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 HPA Manifest를 로컬에서 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11/autoscaling
```

출력에서 `autoscaling/v2`, `HorizontalPodAutoscaler`, `Deployment` target `ai-platform-api-example`, `minReplicas: 2`, `maxReplicas: 5`, `averageUtilization: 70`을 확인합니다. `kubectl kustomize`는 파일을 로컬에서 조합할 뿐 API server에 연결하거나 HPA를 만들고 replica를 변경하지 않습니다. **명령을 `apply`나 `create`로 바꾸지 마세요.**

### 6.2 기본 API 집합에서 HPA가 제외됐는지 확인

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

출력에는 Namespace, ConfigMap, Deployment, Service, Ingress만 있고 `kind: HorizontalPodAutoscaler`는 없어야 합니다. 기본 API 예제 Deployment 이름은 `ai-platform-api`인 반면 HPA 예제 target은 `ai-platform-api-example`입니다. 이 이중 경계는 문서용 autoscaling 계약이 기본 렌더링 집합의 replica 수를 바꾸지 않게 합니다.

### 6.3 Volume 11 HPA 경계를 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 API version/kind, 예제 namespace와 target, min/max 범위, CPU resource utilization target, base Kustomize 집합에서의 제외 및 Secret·토큰·암호·주소 부재를 검사합니다. metrics를 수집하거나 Deployment·Pod·HPA·컨테이너·클러스터 리소스를 만들지 않습니다.

## 7. 운영 전 검토 경계

실제 autoscaling 변경은 다음 증거를 승인된 환경에서 검토한 뒤에만 다뤄야 합니다.

1. target Deployment의 모든 관련 컨테이너 request와 CPU throttling·memory pressure 관측치
2. metrics server의 수집 가능 여부, 지연, 권한, metric 누락 시 controller 행동
3. representative request mix에서의 replica별 throughput, p95/p99 latency, cold start와 readiness 시간
4. max replica가 namespace quota, node capacity, cluster autoscaler, 비용 경보와 충돌하지 않는지
5. scale-out이 의존 서비스의 connection pool, rate limit, queue, storage와 데이터 일관성에 주는 영향
6. scale 정책 변경, 잘못된 target, metric 장애 때 rollback·alert·incident 책임자

이 학습 slice에는 실제 이름, metric 값, dashboard URL, 클러스터 주소, 인증 정보, 부하 데이터 또는 승인 기록을 저장하지 않습니다.

## 8. 정상 실행 결과

6.1의 렌더링 출력에는 대략 다음 구조가 포함됩니다.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-platform-api-example
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

6.2 출력에는 `kind: HorizontalPodAutoscaler`가 없어야 합니다. 두 명령은 YAML의 로컬 조합일 뿐이며 metric 값, current/desired replicas, event 또는 scale action을 표시하지 않습니다. 6.3은 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `kubectl kustomize`를 찾을 수 없음 | `kubectl` CLI가 설치되지 않았을 수 있습니다. | Python 테스트를 먼저 실행하고, 승인된 CLI 설치 후 6.1의 로컬 렌더링만 다시 실행합니다. |
| `minReplicas`가 `maxReplicas`보다 큼 | YAML 값이 바뀌어 범위가 역전됐을 수 있습니다. | 예제의 2~5 범위를 복원하고 다시 렌더링·테스트합니다. |
| 실제 cluster에서 CPU metric이 없음 | metrics pipeline 또는 request가 준비되지 않았을 수 있습니다. | 이 slice에서 cluster를 변경하지 말고, 승인된 운영 절차에서 metrics server와 target resource request를 검토합니다. |
| HPA가 base 출력에 나타남 | base Kustomization에 autoscaling 경로가 추가됐을 수 있습니다. | `k8s/volume11/kustomization.yaml`에서 autoscaling을 제거하고 분리 경계를 복원합니다. |

## 10. 완료 체크리스트

- [ ] HPA가 desired replica를 계산하는 controller임을 설명할 수 있다.
- [ ] `minReplicas: 2`, `maxReplicas: 5`, CPU 70% target의 범위를 확인했다.
- [ ] CPU utilization이 CPU request에 대한 비율임을 구분했다.
- [ ] 예제 target이 base Deployment와 의도적으로 다름을 확인했다.
- [ ] `kubectl kustomize k8s/volume11/autoscaling`로만 HPA 형상을 로컬 렌더링했고 base 집합에서 HPA가 없음을 확인했다.
- [ ] Volume 11 테스트가 통과했다.
- [ ] 실제 cluster, metrics server, 부하, Deployment, Secret, 인증 정보를 만들거나 저장하지 않았다.

## 11. 핵심 정리

HPA는 metric으로 replica 수를 조절하는 controller이고, CPU utilization target은 request 대비 비율입니다. 이 장은 존재하지 않는 `ai-platform-api-example` target, 2~5 replica 범위와 CPU 70% target만 가진 별도 Kustomize 집합을 오프라인으로 검증했습니다. 실제 metric 수집, 부하 시험, capacity·cost 계획, 업데이트·rollback 정책은 다음 운영 설계에서 검증해야 합니다.
