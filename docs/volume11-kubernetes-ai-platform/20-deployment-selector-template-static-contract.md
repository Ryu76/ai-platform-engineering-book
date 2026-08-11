# Deployment Selector: Pod template label 불변식의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Deployment `spec.selector.matchLabels`와 `spec.template.metadata.labels`의 책임을 구분한다.
- 예제 `app.kubernetes.io/name: ai-platform-api`의 정적 일치를 읽는다.
- `deployment_selector_matches_template_app_label`가 local text check임을 설명한다.
- selector 선언과 ReplicaSet 생성·Pod 관리·rollout 성공 증거를 혼동하지 않는다.

## 2. 왜 필요한가

Deployment의 selector는 자신이 관리하려는 Pod를 식별하는 선언이고, Pod template label은 생성될 Pod에 붙이려는 선언입니다. template label이 selector와 일치하지 않으면 Kubernetes는 Deployment를 유효한 workload로 다룰 수 없습니다. selector는 일반적으로 immutable이므로 workload label 설계는 처음부터 명확해야 합니다.

이 Volume의 placeholder API는 `app.kubernetes.io/name: ai-platform-api`를 Deployment selector와 Pod template label에 함께 선언합니다. 이 반복은 변경 전 source review에서 확인할 좁은 정적 계약입니다.

> [!WARNING]
> 이 장은 `k8s/volume11/deployment.yaml`의 local UTF-8 source text만 읽습니다. `example.invalid/ai-platform-api:0.1.0`은 실행 불가능한 placeholder image입니다. local review와 Kustomize render는 Pod creation, admission, Deployment controller, ReplicaSet, rollout, readiness, image pull, container execution을 검증하지 않습니다. Kubernetes API connection과 deployment가 금지된 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 핵심 개념

- **Deployment selector:** `spec.selector.matchLabels`입니다. Deployment가 관리 대상으로 식별하려는 label 조건입니다.
- **Pod template label:** `spec.template.metadata.labels`입니다. Deployment가 만들 Pod에 선언하려는 label입니다.
- **정적 일치:** local source text에 같은 key/value가 있다는 뜻입니다. API server validation이나 controller reconciliation 결과가 아닙니다.
- **Immutable selector:** 이미 생성된 Deployment의 selector 변경에는 제약이 있습니다. 이 장은 그 제약이 live cluster에서 적용됐다는 증거를 제공하지 않습니다.
- **Controller evidence:** admitted Deployment, ReplicaSet, Pod owner reference, available condition, Event를 함께 확인한 결과입니다. 이 장의 범위 밖입니다.

## 4. 동작 구조

```text
local source text only

Deployment
  spec.selector.matchLabels
    app.kubernetes.io/name: ai-platform-api
                    │
                    │ same declared key/value
                    ▼
  spec.template.metadata.labels
    app.kubernetes.io/name: ai-platform-api

render_only_artifact_checks()
  └── declaration text shape: true | false

API validation, controller reconciliation, ReplicaSet, Pod creation,
owner references, readiness, rollout ── not verified
```

이 계약은 Service selector를 검사하지 않습니다. Service가 traffic 후보를 선택하는 별도 책임은 [19장](19-service-selector-static-contract.md)에서 다룹니다. 여기서는 하나의 Deployment 안에서 selector와 template label이 같은 예제인지에만 집중합니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/deployment.yaml` | placeholder API의 Deployment selector와 Pod template label 선언 |
| `src/ai_platform/api/operations_review.py` | local text check `deployment_selector_matches_template_app_label` |
| `tests/integration/test_volume11_deployment_selector.py` | selector/template 선언과 controller-evidence 경계 검사 |
| `examples/volume11/local_operations_review_demo.py` | deterministic local-only review JSON |

실습에는 Python과 `uv`가 필요합니다. 선택적으로 `kubectl` CLI가 있으면 local Kustomize render를 할 수 있습니다. kubeconfig, cluster, registry, Secret, credential, 실제 image는 필요하지 않으며 사용하지 않습니다.

## 6. 단계별 실습

### 6.1 local artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력의 `artifact_checks.deployment_selector_matches_template_app_label`가 `true`인지 확인합니다. check는 하나의 local Deployment text에서 selector와 template label의 예제 key/value를 찾을 뿐입니다. Docker daemon, Kubernetes API, controller, network를 호출하지 않습니다.

### 6.2 오프라인 계약 테스트 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_deployment_selector.py -q
```

테스트는 placeholder image와 source text 선언을 검토합니다. image pull, Deployment 생성, ReplicaSet 생성, Pod scheduling, Kubernetes API 호출 또는 deployment를 실행하지 않습니다.

### 6.3 연결 없이 Manifest 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

rendered YAML의 `spec.selector.matchLabels`와 `spec.template.metadata.labels`에서 같은 key/value를 읽습니다. 이 명령은 local YAML render일 뿐 API validation, controller reconciliation, Pod creation, rollout, cluster resource를 만들지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 7. 코드와 Manifest 설명

`render_only_artifact_checks()`는 Deployment를 UTF-8 text로 읽습니다. `deployment_selector_matches_template_app_label`는 다음의 좁은 teaching contract를 확인합니다.

1. Deployment selector `matchLabels`에 `app.kubernetes.io/name: ai-platform-api`가 있다.
2. Deployment Pod template labels에 같은 `app.kubernetes.io/name: ai-platform-api`가 있다.

구현은 YAML parser나 Kubernetes client를 사용하지 않습니다. 따라서 `true`는 local example의 text shape가 의도대로라는 뜻입니다. API server가 immutable selector 규칙을 검증했는지, controller가 ReplicaSet을 만들었는지, Pod owner reference가 맞는지, readiness가 true인지, rollout이 완료됐는지는 뜻하지 않습니다.

## 8. 정상 실행 결과

6.1의 JSON에는 다음 모양의 field가 포함됩니다.

```json
{"artifact_checks":{"deployment_selector_matches_template_app_label":true}}
```

실제 출력에는 다른 local artifact check도 포함됩니다. 6.2는 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다. 6.3의 rendered YAML에는 selector와 template label이 보이지만 ReplicaSet 이름, Pod UID, owner reference, condition, Event는 나타나지 않아야 합니다.

## 9. 오류 해결

| 증상 | local 확인 | 안전한 해결 |
|---|---|---|
| review key가 `false` | selector와 template label의 key/value를 각각 읽는다 | 의도된 구조 변경이면 local check, test, 문서를 함께 갱신한다. cluster에 apply하지 않는다. |
| metadata label은 있지만 template label이 없음 | Deployment metadata와 Pod template metadata는 다른 위치임을 확인한다 | selector가 참조하는 label을 template에 명시한다. |
| selector value가 다름 | key뿐 아니라 value까지 비교한다 | API, worker, batch 역할 label을 무심코 복사하지 않는다. |
| `kubectl kustomize`를 찾을 수 없음 | CLI 설치 여부를 확인한다 | Python local review와 pytest를 먼저 실행한다. cluster를 만들거나 연결하지 않는다. |
| immutable selector 변경 영향이 궁금함 | text check가 live update 정책을 증명하지 않음을 기록한다 | 승인된 환경에서 migration·replacement·rollback plan과 controller evidence를 별도로 검토한다. |

## 10. 응용 실습

1. API, worker, maintenance Job이 있는 가상 Platform의 Deployment selector와 template label 표를 작성합니다.
2. selector만 바꾸는 가상 변경과 template label만 바꾸는 가상 변경의 source review 위험을 적습니다.
3. selector mismatch, image pull failure, readiness failure, rollout deadline을 서로 다른 가설로 둔 triage 표를 작성합니다. 실제 cluster name, endpoint, credential, user data는 넣지 않습니다.

## 11. 실무 적용

운영 Deployment에서는 selector의 immutable 특성, label taxonomy, PodDisruptionBudget·NetworkPolicy·Service selector와의 compatibility, migration path를 함께 검토합니다. rollout 전에는 approved image provenance, admitted object, ReplicaSet revision, Pod owner reference, readiness, availability condition, rollback plan을 분리해 evidence를 수집합니다. log나 label에는 credential, raw request body, 개인 endpoint를 넣지 않습니다.

## 12. 과제

- **기본:** Deployment selector와 Pod template label이 각각 답하는 질문을 한 문장으로 작성합니다.
- **응용:** API와 worker가 있는 가상 Platform의 selector/template label 표와 변경 review plan을 작성합니다. 실제 Manifest를 적용하지 않습니다.
- **심화:** immutable selector migration, image failure, readiness failure, deadline 초과를 구분하는 investigation plan을 작성합니다. 각 행에 필요한 evidence source와 approval owner를 적고 actual cluster command나 credential은 넣지 않습니다.

## 13. 완료 체크리스트

- [ ] Deployment selector와 Pod template label의 위치와 책임을 읽었다.
- [ ] `app.kubernetes.io/name: ai-platform-api`의 key/value 일치를 확인했다.
- [ ] `deployment_selector_matches_template_app_label`가 local text check일 뿐임을 설명할 수 있다.
- [ ] selector immutable 제약과 static check의 차이를 설명할 수 있다.
- [ ] ReplicaSet, Pod creation, readiness, rollout이 `not verified`임을 유지했다.
- [ ] 실제 Secret, credential, Kubernetes API connection 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 14. 핵심 정리

Deployment selector와 Pod template label의 같은 key/value는 하나의 workload 안에서 사람이 읽을 수 있는 정적 계약입니다. 이 Volume은 placeholder Deployment source text를 local review, pytest, Kustomize render로만 확인합니다. API validation, controller reconciliation, ReplicaSet, Pod creation, readiness, rollout은 증명하지 않았으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
