# Ingress backend reference: Service HTTP 연결의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Ingress backend와 Service의 이름·명명된 포트가 맡는 선언 책임을 구분한다.
- 동일한 example namespace 안의 `ai-platform-api`와 `http` 참조를 local source text에서 읽는다.
- `ingress_references_service_named_http_port_in_declared_namespace`가 정적 text check임을 설명한다.
- Ingress controller, EndpointSlice, TLS, DNS, HTTP traffic delivery를 실행 증거로 추정하지 않는다.

## 2. 정적 계약의 범위

`k8s/volume11/ingress.yaml`은 `ai-platform-example` namespace에서 backend Service `ai-platform-api`의 명명된 `http` 포트를 참조합니다. `k8s/volume11/service.yaml`은 같은 namespace에서 `port: 80`을 container-facing `targetPort: http`에 선언합니다. 이 관계는 변경 전에 사람이 검토할 수 있는 placeholder source-text 계약입니다.

> [!WARNING]
> 이 장은 local UTF-8 파일만 읽습니다. `api.volume11.example.invalid` 및 `example-ingress-class`는 실행 불가능한 placeholder이고 TLS Secret은 선언하지 않습니다. local review와 Kustomize render는 Kubernetes API admission, Ingress controller reconciliation, Service object 존재, selector evaluation, EndpointSlice membership, DNS, TLS, network policy, container listener 또는 HTTP traffic delivery를 검증하지 않습니다. Kubernetes API connection과 deployment가 금지된 현재 범위에서는 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 관계 읽기

```text
local source text only

ingress.yaml                            service.yaml
metadata.namespace: ai-platform-example  metadata.namespace: ai-platform-example
backend.service.name: ai-platform-api ── metadata.name: ai-platform-api
backend.service.port.name: http ──────── spec.ports[].name: http
                                         spec.ports[].targetPort: http

Ingress controller, EndpointSlice, DNS, TLS, network traffic ── not verified
```

Ingress backend의 `service.name`과 `service.port.name`은 Controller가 해석할 대상의 선언입니다. Service가 API에 존재하는지, selector가 ready Pod를 찾는지, EndpointSlice가 생겼는지, Controller가 rule을 수용했는지, DNS·TLS가 준비됐는지, 요청이 container listener까지 도달하는지는 이 source text만으로 알 수 없습니다. 이 계약은 Secret, credential 또는 실제 endpoint를 읽거나 저장하지 않습니다.

## 4. local-only 실습

### 4.1 artifact review 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/local_operations_review_demo.py
```

출력의 `artifact_checks.ingress_references_service_named_http_port_in_declared_namespace`가 `true`인지 확인합니다. check는 local Ingress/Service namespace, backend Service name, named port, Service `targetPort` 문자열만 읽습니다. Docker daemon, Kubernetes API, network, container를 호출하지 않습니다.

### 4.2 오프라인 계약 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_ingress_backend_reference.py -q
```

테스트는 source text를 검사합니다. Ingress controller 설치, Service 또는 EndpointSlice 생성, DNS lookup, TLS 처리, image build, container execution 또는 deployment를 실행하지 않습니다.

### 4.3 연결 없는 YAML render

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

rendered YAML에서 Ingress backend Service 이름·named port와 Service의 `targetPort: http`를 읽습니다. 이는 local render일 뿐 Kubernetes API에 연결하거나 object를 만들지 않습니다. `kubectl apply`로 바꾸지 않습니다.

## 5. 오류 해결과 운영 전 질문

| 증상 | local 확인 | 안전한 처리 |
|---|---|---|
| review key가 `false` | 양쪽 namespace, backend Service name, named port, Service targetPort를 읽는다 | 의도된 예제 변경이면 check·test·문서를 함께 갱신하고 apply하지 않는다. |
| backend Service name이 다름 | Ingress `backend.service.name`과 Service metadata name을 비교한다 | source text의 이름을 일치시키고 Controller routing 성공으로 주장하지 않는다. |
| 포트 이름이 다름 | Ingress port name과 Service `ports[].name`·`targetPort`를 비교한다 | 명명된 port 계약을 함께 수정하고 EndpointSlice 또는 traffic success로 해석하지 않는다. |
| 실제 host가 열리지 않음 | `example.invalid`와 placeholder IngressClass임을 확인한다 | 예상된 보호 동작이다. DNS, TLS, Controller를 이 학습 범위에서 구성하지 않는다. |
| policy 또는 routing 영향이 궁금함 | controller, RBAC, NetworkPolicy, EndpointSlice가 not verified임을 유지한다 | cluster에 연결하지 말고 승인된 운영 절차의 evidence owner에게 인계한다. |

## 6. 완료 체크리스트

- [ ] Ingress backend와 Service named port의 책임을 구분했다.
- [ ] `ai-platform-api`, `http`, `ai-platform-example`의 정적 관계를 읽었다.
- [ ] `ingress_references_service_named_http_port_in_declared_namespace`가 local file check임을 설명할 수 있다.
- [ ] Ingress controller, EndpointSlice, DNS, TLS, traffic delivery가 not verified임을 유지했다.
- [ ] 실제 Secret, credential, Kubernetes API connection, image build, container 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 7. 핵심 정리

같은 example namespace의 Ingress backend Service name·named port와 Service port 선언은 검토 가능한 정적 계약입니다. `true` 결과는 local placeholder text가 예상 모양이라는 뜻일 뿐 controller reconciliation, endpoint 생성 또는 HTTP traffic delivery의 증거가 아닙니다. 실행 증거가 없으므로 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
