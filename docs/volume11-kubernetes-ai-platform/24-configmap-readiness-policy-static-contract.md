# ConfigMap readiness policy: 비밀 없는 환경 키의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- ConfigMap의 비밀 없는 dependency-name 정책과 애플리케이션 환경 변수 이름을 구분한다.
- `AI_PLATFORM_REQUIRED_DEPENDENCIES`와 `AI_PLATFORM_READY_DEPENDENCIES`의 example 값이 local source text에서 같은 정책을 표현함을 읽는다.
- `configmap_declares_nonsecret_readiness_policy_names`가 정적 text check임을 설명한다.
- ConfigMap 주입, 환경 변수 해석, dependency connectivity, `/readyz` runtime 결과를 실행 증거로 추정하지 않는다.

## 2. 정적 계약의 범위

`k8s/volume11/configmap.yaml`은 `ai-platform-example` namespace에 비밀 없는 `ai-platform-api-config`를 선언합니다. 그 안의 `AI_PLATFORM_REQUIRED_DEPENDENCIES`와 `AI_PLATFORM_READY_DEPENDENCIES`는 모두 `qdrant,redis,postgresql`이라는 example dependency-name 목록입니다. `src/ai_platform/api/dependencies.py`는 같은 두 환경 변수 이름을 읽어 문자열 목록을 정책으로 해석합니다.

> [!WARNING]
> 이 장은 local UTF-8 source file만 읽습니다. dependency 이름은 hostname, URL, credential 또는 연결 지시가 아닙니다. ConfigMap object 존재, admission, `envFrom` injection, process environment, policy evaluation, `/readyz` 호출, Qdrant·Redis·PostgreSQL connectivity, container execution, Kubernetes API connection은 검증하지 않습니다. 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 관계 읽기

```text
local source text only

configmap.yaml                                      dependencies.py
AI_PLATFORM_REQUIRED_DEPENDENCIES: qdrant,redis,postgresql ── required list key
AI_PLATFORM_READY_DEPENDENCIES:    qdrant,redis,postgresql ── ready list key

same example names ── policy declaration only

ConfigMap injection, getenv runtime values, /readyz, network connectivity ── not verified
```

`required` 목록은 readiness에서 필요하다고 선언한 dependency name이고, `ready` 목록은 example policy에서 준비됐다고 표시한 name입니다. 같은 목록이라는 source-text 계약은 교육용 ConfigMap과 Python parser의 이름이 함께 변경되는지 검토할 때 유용합니다.

그러나 YAML의 key/value가 실제 process environment에 들어갔는지, `getenv()`가 무엇을 반환했는지, dependency checker가 network를 호출했는지, readiness probe가 200을 반환했는지는 이 계약으로 알 수 없습니다. `dependencies.py`의 example policy 자체도 connection detail을 읽거나 network 요청을 만들지 않습니다.

## 4. local-only 실습

### 4.1 artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력에서 `artifact_checks.configmap_declares_nonsecret_readiness_policy_names`가 `true`인지 확인합니다. check는 local ConfigMap과 Python source의 두 환경 변수 이름 및 example 목록만 읽습니다. Docker daemon, Kubernetes API, environment injection, network, container를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_configmap_readiness_policy.py tests/integration/test_volume11_mini_project.py -q
```

테스트는 source text를 검사합니다. ConfigMap 생성, kubelet 주입, Pod 시작, DNS lookup, dependency connection, image build, container execution 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 YAML render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

rendered YAML에서 ConfigMap의 두 key와 example value를 읽습니다. 이는 local render일 뿐 Kubernetes API에 연결하거나 environment를 주입하지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | ConfigMap의 두 key와 Python의 `_REQUIRED_DEPENDENCIES_ENV`·`_READY_DEPENDENCIES_ENV`를 비교한다 | 의도된 예제 변경이면 ConfigMap·parser·check·test·문서를 함께 갱신하고 apply하지 않는다. |
| 두 목록이 다름 | example comma-separated name 목록을 비교한다 | 학습 의도가 “all ready”가 아니라면 차이를 문서화한다. 실제 장애 또는 connectivity 결과라고 주장하지 않는다. |
| URL이나 credential을 넣고 싶음 | 이 artifact는 name-only policy임을 확인한다 | endpoint와 credential을 추가하지 않는다. 승인된 운영 configuration 관리 절차로 인계한다. |
| `/readyz`가 실제로 어떤 값을 읽는지 궁금함 | injection, process environment, probe execution이 not verified임을 유지한다 | cluster에 연결하지 말고 승인된 환경에서 owner가 runtime evidence를 수집한다. |

## 6. 완료 체크리스트

- [ ] 두 ConfigMap key와 Python policy key의 책임을 구분했다.
- [ ] `qdrant,redis,postgresql`이 example name-only 정책임을 읽었다.
- [ ] `configmap_declares_nonsecret_readiness_policy_names`가 local file check임을 설명할 수 있다.
- [ ] ConfigMap injection, process environment, `/readyz`, dependency connectivity가 not verified임을 유지했다.
- [ ] 실제 Secret, credential, Kubernetes API connection, image build, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

ConfigMap의 비밀 없는 dependency-name 목록과 Python parser의 환경 변수 이름은 검토 가능한 정적 계약입니다. `true` 결과는 local placeholder text가 예상 모양이라는 뜻일 뿐 ConfigMap injection, environment evaluation, readiness success 또는 dependency connectivity의 증거가 아닙니다. 실행 증거가 없으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
