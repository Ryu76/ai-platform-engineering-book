# ConfigMap reference: Deployment 환경 주입의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `ConfigMap` 데이터와 Deployment `envFrom.configMapRef`의 책임을 구분한다.
- 동일한 example namespace 안의 `ai-platform-api-config` 선언과 참조를 local source text에서 읽는다.
- `deployment_references_example_configmap_in_its_declared_namespace`가 정적 text check임을 설명한다.
- ConfigMap injection, 환경 변수, readiness 결과를 실행 증거로 추정하지 않는다.

## 2. 정적 계약의 범위

`k8s/volume11/configmap.yaml`은 `ai-platform-example` namespace에 non-secret `ai-platform-api-config`를 선언합니다. `k8s/volume11/deployment.yaml`은 같은 namespace에서 `envFrom.configMapRef.name: ai-platform-api-config`를 선언합니다. 이 관계는 사람이 변경 전에 확인할 수 있는 placeholder source-text 계약입니다.

> [!WARNING]
> 이 장은 local UTF-8 파일만 읽습니다. `example.invalid/ai-platform-api:0.1.0`은 실행 불가능한 placeholder image이며, `AI_PLATFORM_READY`와 dependency 목록은 예제 정책 값입니다. local review와 Kustomize render는 Kubernetes API admission, object 존재, ConfigMap injection, environment construction, kubelet, process startup, readiness, dependency connectivity를 검증하지 않습니다. Kubernetes API connection과 deployment가 금지된 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 관계 읽기

```text
local source text only

configmap.yaml                         deployment.yaml
metadata.namespace: ai-platform-example  metadata.namespace: ai-platform-example
metadata.name: ai-platform-api-config ── envFrom.configMapRef.name
                                                │
                                                └── declaration text shape: true | false

ConfigMap injection, runtime environment, process behavior, readiness ── not verified
```

`envFrom`은 ConfigMap key를 container environment로 만들겠다는 Deployment 선언입니다. ConfigMap key가 존재하는지, value가 admission 이후에도 같은지, environment가 구성됐는지, application이 값을 파싱했는지, `/readyz` 결과가 기대와 같은지는 이 declaration만으로 알 수 없습니다. `Secret` 예제는 base set에 포함되지 않으며 이 계약은 credential을 읽거나 저장하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력의 `artifact_checks.deployment_references_example_configmap_in_its_declared_namespace`가 `true`인지 확인합니다. check는 local ConfigMap name/namespace와 Deployment namespace/reference 문자열만 읽습니다. Docker daemon, Kubernetes API, network, container를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_configmap_reference.py -q
```

테스트는 source text를 검사합니다. ConfigMap 생성, Pod 생성, ConfigMap injection, 실제 environment 확인, image build, container execution 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 YAML render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

rendered YAML에서 ConfigMap과 Deployment의 example namespace, `configMapRef` name을 읽습니다. 이는 local render일 뿐 Kubernetes API에 연결하거나 object를 만들지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | ConfigMap name, 양쪽 namespace, `envFrom.configMapRef.name`을 읽는다 | 의도된 예제 변경이면 check·test·문서를 함께 갱신하고 apply하지 않는다. |
| 참조 name이 다름 | ConfigMap metadata name과 Deployment reference를 비교한다 | source text의 이름을 일치시키고 runtime injection 성공으로 주장하지 않는다. |
| value 변경의 영향이 궁금함 | local text가 environment 또는 process behavior를 증명하지 않음을 기록한다 | 승인된 환경에서 config owner와 rollout·readiness·rollback evidence를 별도 검토한다. |
| policy/admission 영향이 궁금함 | Namespace, RBAC, quota, policy가 not verified임을 유지한다 | cluster에 연결하지 말고 승인된 운영 절차의 evidence owner에게 인계한다. |

## 6. 완료 체크리스트

- [ ] ConfigMap data와 Deployment reference의 책임을 구분했다.
- [ ] `ai-platform-api-config`와 `ai-platform-example`의 정적 관계를 읽었다.
- [ ] `deployment_references_example_configmap_in_its_declared_namespace`가 local file check임을 설명할 수 있다.
- [ ] ConfigMap injection, runtime environment, readiness, dependency connectivity가 not verified임을 유지했다.
- [ ] 실제 Secret, credential, Kubernetes API connection, image build, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

같은 example namespace의 ConfigMap name과 Deployment `configMapRef`는 검토 가능한 정적 계약입니다. `true` 결과는 local placeholder text가 예상 모양이라는 뜻일 뿐 ConfigMap injection 또는 application behavior의 증거가 아닙니다. 실행 증거가 없으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.