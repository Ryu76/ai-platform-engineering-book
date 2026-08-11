# Volume 11 운영 전 체크리스트·용어집·인계 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Volume 11의 local-only artifact와 운영 승인 대상의 경계를 한 장의 인계표로 요약한다.
- health, readiness, Compose, Kubernetes manifest, correlation, telemetry의 증거가 각각 무엇을 확인하는지 구분한다.
- 실행 전 승인에 필요한 owner, 입력, 종료 기준을 실제 환경 값 없이 기록한다.
- 용어가 비슷해 보여도 서로 다른 책임을 가진 liveness, readiness, exporter failure, render-only를 구분한다.
- 이 교재의 offline 검증 성공을 deployment approval 또는 PRD 완료 선언으로 오해하지 않는다.

## 2. 이 장의 범위

이 장은 앞선 12개 장의 artifact를 **읽고 인계하는 문서**입니다. 새 API, container, listener, image, Secret, telemetry backend, account, endpoint 또는 Kubernetes resource를 만들지 않습니다. 모든 이름·값은 `example.invalid`, `placeholder-*`, `sample-*` 같은 예제뿐입니다.

> [!WARNING]
> 이 장은 `docker compose up`, image pull/build, `kubectl get`, `kubectl logs`, `kubectl apply`, rollout, rollback, alert 생성, on-call 호출, telemetry backend query, Secret 작성, credential 사용, cluster 연결 또는 deployment를 실행하지 않습니다. 아래 checklist의 완료 표시는 승인된 운영 절차의 증거가 아니라 학습자가 검토할 질문입니다.

## 3. Volume artifact 인계표

| 영역 | local artifact | 이 Volume에서 확인한 작은 증거 | 운영 전 별도 확인할 사실 |
|---|---|---|---|
| process health | `src/ai_platform/api/health.py`, `examples/volume11/health_probe_demo.py` | `/livez`와 `/readyz`가 in-memory WSGI에서 분리된 HTTP 결과를 낸다. | process lifecycle, probe timing, traffic 영향, customer impact |
| dependency readiness | `src/ai_platform/api/dependencies.py`, `examples/volume11/dependency_readiness_demo.py` | injected policy가 required dependency 결과를 합성한다. | real DNS, TLS, credential, timeout, dependency SLO, data integrity |
| image and Compose topology | `docker/volume11/Dockerfile`, `docker/volume11/compose.health.yaml`, `docker/volume11/compose.dependencies.yaml` | Compose text가 placeholder image와 internal topology를 선언한다. | image provenance, build, pull, container execution, network and startup behavior |
| base Kubernetes contract | `k8s/volume11/deployment.yaml`, `service.yaml`, `ingress.yaml`, `configmap.yaml` | render-only YAML이 example image, distinct probes, ClusterIP, placeholder ingress를 선언한다. | API compatibility, admission, RBAC, scheduling, DNS, TLS, Service endpoints |
| optional Kubernetes contract | `k8s/volume11/secret.example.yaml`, `batch/`, `storage/`, `autoscaling/` | Secret example은 base set에서 제외되고 batch/PVC/HPA는 separate placeholder sets다. | approved Secret reference, scheduler, storage binding, metric pipeline, capacity, cost |
| update boundary | `k8s/volume11/deployment.yaml` | RollingUpdate, progress deadline, revision-history values가 local text/render에 있다. | rollout safety, migration compatibility, rollback side effects, image availability |
| correlation and telemetry | `src/ai_platform/api/correlation.py`, `telemetry.py`, `examples/volume11/correlation_logging_demo.py`, `telemetry_boundary_demo.py` | allow-list schema와 exporter failure isolation을 process-local callback으로 확인한다. | collector/backend delivery, sampling, retention, access control, alert action |
| integrated review | `src/ai_platform/api/operations_review.py`, `examples/volume11/local_operations_review_demo.py` | in-memory probe result와 artifact text check가 deterministic JSON으로 요약된다. | container execution, dependency connectivity, telemetry backend delivery, Kubernetes cluster deployment |

이 표의 “확인한 작은 증거”는 **이 repository에서 실제 실행한 local contract**에 한정됩니다. 오른쪽 열의 사실은 비어 있거나 false인 것이 아니라, 이 학습 artifact가 증명하지 않는 대상입니다.

## 4. 운영 전 의사결정 checklist

다음 checklist는 운영 환경의 실행 명령이 아닙니다. 각 행은 승인된 change/incident/security 절차에서 owner가 evidence와 종료 기준을 채우기 위한 틀입니다.

| 결정 영역 | 인계 질문 | 최소 evidence 예시 | owner 역할 | 종료 기준 |
|---|---|---|---|---|
| image provenance | placeholder image를 승인된 immutable artifact로 어떻게 대체·추적할 것인가? | approved build record와 vulnerability review reference | platform/security | provenance와 change approval이 연결됨 |
| configuration and secrets | ConfigMap 정책과 Secret reference를 어떻게 분리할 것인가? | redacted configuration contract와 Secret access review | platform/security | Secret value가 source·log·manifest에 없고 access owner가 지정됨 |
| health semantics | liveness와 readiness가 어떤 실패를 각각 반영하는가? | probe contract, timeout/failure rationale, false-positive review | service/platform | restart와 traffic exclusion의 조건이 구분됨 |
| dependency policy | required dependency의 timeout, failure class, fallback, data-integrity 위험은 무엇인가? | dependency contract and dependency owner acknowledgement | service/data | unknown failure를 ready로 처리하지 않는 policy가 승인됨 |
| capacity and updates | requests/limits, HPA metric source, rollout/rollback compatibility는 검토됐는가? | capacity model, migration plan, rollback impact review | platform/service | safe change and stop criteria가 기록됨 |
| observability privacy and cost | 어떤 signal을 수집하지 않으며 cardinality, sampling, retention은 누가 승인하는가? | schema review, budget, access and deletion policy | SRE/privacy/data | action owner와 cost/privacy bound가 존재함 |
| incident response | detection, impact classification, mitigation, recovery, handoff는 어떻게 분리되는가? | runbook, escalation roles, recovery evidence plan | operations/service | incomplete recovery와 follow-up owner가 기록됨 |
| customer and data impact | API availability 외에 model quality, data freshness, queued work, customer impact를 어떻게 확인하는가? | approved impact criteria and communication ownership | product/service/data | unknowns and confirmed facts are separated |

### 4.1 완료 표시를 안전하게 해석하기

- `[x]`는 **승인된 운영 시스템에서 증거와 owner가 확인되었다**는 뜻으로만 사용합니다.
- `[ ]`는 아직 검토하지 않은 질문입니다. 이 학습 repository의 테스트가 통과해도 자동으로 `[x]`가 되지 않습니다.
- `not verified`, `unknown`, `not applicable`은 서로 다릅니다. 어느 것을 선택했는지와 근거를 인계 기록에 남깁니다.
- raw request input, request ID, user/tenant identifier, token, password, endpoint, cluster address, exception detail을 checklist evidence에 복사하지 않습니다.

## 5. 용어집

| 용어 | 이 Volume에서의 뜻 | 혼동하면 안 되는 것 |
|---|---|---|
| **liveness** | process가 liveness response를 만들 수 있는지에 대한 작은 health signal | dependency가 정상인지, request가 성공하는지, model quality가 좋은지 |
| **readiness** | 이 예제의 injected readiness policy가 새 traffic 수신 가능으로 판단하는 signal | liveness, all customer impact, external dependency root cause |
| **dependency readiness policy** | required dependency 결과를 readiness 판단으로 합성하는 코드 계약 | 실제 connection, authentication, DNS, TLS, production dependency health |
| **render-only** | YAML 또는 Compose를 local text/config/render로 읽고 resource를 만들지 않는 경계 | server-side validation, admission, scheduling, container start, deployment |
| **placeholder** | 의도적으로 실행에 쓰지 않는 example name/value; 예: `example.invalid` | approved image, Secret, storage class, ingress class, live endpoint |
| **base apply set** | `k8s/volume11/kustomization.yaml`이 local render 대상으로 가리키는 교육용 집합 | 실제 apply approval 또는 all optional artifacts |
| **optional artifact set** | batch, storage, autoscaling처럼 base와 분리된 학습용 Kustomize 집합 | base Deployment에 자동으로 연결되거나 실행되는 resource |
| **correlation ID** | allow-list header 또는 generated ID로 response와 one completion event를 연결하는 식별자 | telemetry label, incident note에 복사할 customer identifier |
| **low cardinality** | allow-list route와 status class처럼 값의 수를 제한한 telemetry dimension | 모든 path/query/user/error detail을 label로 담는 방식 |
| **telemetry exporter** | local event를 callback으로 전달하는 경계 | backend delivery 보장, retry queue, metric endpoint, trace collector |
| **exporter failure isolation** | exporter callback 예외가 ready probe response를 unavailable로 바꾸지 않는 계약 | exporter가 healthy이거나 application/customer impact가 없음 |
| **revision history** | Deployment update revision을 보존하기 위한 declared setting | data migration, queue, cache, external side effect의 rollback |
| **recovery verification** | availability, data, customer impact, queued work를 분리해 정상 여부를 검토하는 단계 | signal 하나가 정상인 것을 complete recovery로 단정하는 행위 |

## 6. 인계 패킷 템플릿

승인된 운영 문서에는 아래처럼 placeholder만 든 요약을 작성할 수 있습니다. 이 repository에는 실제 ticket, account, endpoint, cluster name, Secret reference를 넣지 않습니다.

```yaml
handoff:
  service: placeholder-service
  scope: approved-environment-only
  change_reference: placeholder-change-reference
  owners:
    platform: placeholder-platform-owner
    service: placeholder-service-owner
    security_privacy: placeholder-security-owner
    operations: placeholder-operations-owner
  evidence:
    health_contract: approved-reference-required
    dependency_contract: approved-reference-required
    image_provenance: approved-reference-required
    observability_budget: approved-reference-required
    recovery_plan: approved-reference-required
  unknowns:
    - placeholder-unverified-item
  prohibited_in_this_repository:
    - secret-values
    - credentials
    - customer-request-data
    - live-cluster-addresses
```

이 YAML은 schema나 deployment input이 아니라 문서 구조 예시입니다. `approved-reference-required`는 검증 완료를 뜻하지 않으며, 실제 참조는 접근 제어된 시스템에서 관리합니다.

## 7. 오프라인 검증 인계

저장소 루트에서 다음 테스트는 Volume 11의 local contract와 artifact boundary를 확인합니다.

```bash
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/unit/test_volume11_telemetry.py tests/integration/test_volume11_health_artifacts.py tests/integration/test_volume11_mini_project.py -q
```

선택적으로 다음 명령은 local render/config만 수행합니다.

```bash
docker compose -f docker/volume11/compose.dependencies.yaml config --no-interpolate
kubectl kustomize k8s/volume11
kubectl kustomize k8s/volume11/batch
kubectl kustomize k8s/volume11/storage
kubectl kustomize k8s/volume11/autoscaling
```

이 명령들은 alert, on-call, container, image pull/build, Secret, credential, telemetry backend, Kubernetes API 또는 deployment를 만들지 않습니다. 특히 local test success는 PRD Definition of Done 또는 production readiness의 자동 충족 선언이 아닙니다.

## 8. 최종 검토 checklist

- [ ] 각 artifact의 local evidence와 운영 전 별도 evidence를 표 3에서 분리했다.
- [ ] image, configuration/Secret, health, dependency, capacity/update, observability, incident, customer/data impact owner를 지정했다.
- [ ] liveness, readiness, exporter failure, render-only, placeholder의 용어 차이를 설명할 수 있다.
- [ ] current unknown과 `not verified`를 success claim으로 바꾸지 않았다.
- [ ] actual Secret, credential, customer request data, live endpoint, cluster address를 이 학습 repository에 저장하지 않았다.
- [ ] actual cluster, alert, on-call, telemetry backend 또는 deployment를 실행하지 않았다.
- [ ] local-only test 결과와 approved-environment evidence를 별도 인계 시스템에서 연결할 계획을 세웠다.

## 9. 핵심 정리

Volume 11은 Kubernetes AI 운영의 작은 contract를 offline artifact로 읽는 법을 다룹니다. health 응답, dependency policy, placeholder Manifest, process-local observability, update settings가 모두 유용한 증거이지만 서로 다른 질문에만 답합니다. 안전한 인계는 각각의 증거·unknown·owner·종료 기준을 분리하고, local validation을 deployment approval 또는 PRD 완료 선언으로 확장하지 않는 데서 시작합니다.
