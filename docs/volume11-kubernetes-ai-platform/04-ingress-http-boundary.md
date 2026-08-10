# Ingress HTTP 경계: Service로 안전하게 연결하기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Ingress가 외부 HTTP 요청을 Kubernetes `Service`로 전달하는 선언 경계임을 설명한다.
- `host`, `path`, `pathType`, Service 이름과 명명된 포트가 함께 라우팅 계약을 만드는 방식을 읽는다.
- `IngressClass`와 실제 Ingress Controller의 운영 책임을 Manifest의 HTTP 규칙과 분리한다.
- 예제 호스트와 자리표시자만 포함한 Manifest를 클러스터 연결 없이 로컬에서 렌더링한다.

## 2. 왜 필요한가

Pod IP는 교체될 수 있고 Deployment는 Pod 집합을 유지할 뿐 HTTP 진입점을 제공하지 않습니다. `Service`는 안정적인 내부 대상 이름과 포트를 제공하며, Ingress는 HTTP의 호스트와 경로를 해당 Service로 라우팅하는 선언입니다.

하지만 Ingress YAML 하나로 인터넷 노출, DNS, TLS, 인증, WAF, 네트워크 정책 또는 Ingress Controller가 자동으로 구성되지는 않습니다. 이 장은 그 경계만 학습하기 위해 `example.invalid` 도메인과 `example-ingress-class`를 사용합니다. 실제 주소, 인증서, Secret 이름, 조직의 Controller 이름은 저장하지 않습니다.

> [!WARNING]
> `k8s/volume11/ingress.yaml`은 **로컬 렌더링용 학습 Manifest**입니다. `kubectl apply`, `kubectl create`, 실제 DNS 설정, 인증서 발급, Controller 설치를 실행하지 마세요. `example-ingress-class`와 `api.volume11.example.invalid`는 의도적으로 실제 운영 연결점이 아닌 자리표시자입니다.

## 3. 핵심 개념

- **Ingress:** HTTP/HTTPS 요청의 호스트와 경로를 Kubernetes Service backend에 매핑하는 API 객체입니다.
- **IngressClass:** 어떤 Controller가 Ingress를 구현할지 식별하는 이름입니다. 이 예제는 실제 Controller를 선택하지 않는 자리표시자를 사용합니다.
- **Service backend:** Ingress가 전달할 Service 이름과 포트입니다. 이 장에서는 `ai-platform-api`의 명명된 `http` 포트를 참조합니다.
- **`Prefix` path:** `/`로 시작하는 경로에 적용되는 경로 일치 방식입니다. 세부 경로의 우선순위는 Controller와 Kubernetes Ingress 규칙을 함께 검토해야 합니다.
- **예제 도메인:** `example.invalid`는 문서와 테스트용으로 예약된 비실행 도메인입니다. 운영 DNS 이름이나 IP 주소가 아닙니다.

## 4. 동작 구조

```text
HTTP Host: api.volume11.example.invalid
HTTP Path: /  (Prefix)
                 │
                 ▼
Ingress: ai-platform-api
  ingressClassName: example-ingress-class  ── Controller 설치·선택은 이 예제 밖
                 │
                 ▼
Service: ai-platform-api : http
  type: ClusterIP
                 │
                 ▼
Deployment Pods: ai-platform-api

TLS Secret, DNS 레코드, 실제 Controller, 클러스터 적용: 이 slice에 없음
```

`ingress.yaml`은 Service의 `name: ai-platform-api`와 `port.name: http`을 정확히 참조합니다. Service는 다시 `app.kubernetes.io/name: ai-platform-api` selector로 Pod를 선택합니다. 이 이름 연결은 YAML을 읽고 Kustomize로 렌더링할 수 있지만, Controller가 없으면 HTTP 트래픽을 실제로 처리하지 않습니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/ingress.yaml` | 예제 호스트·IngressClass·HTTP Prefix backend 선언 |
| `k8s/volume11/service.yaml` | Ingress가 참조하는 내부 ClusterIP Service와 `http` 포트 |
| `k8s/volume11/kustomization.yaml` | Ingress를 포함하는 로컬 렌더링 집합 |
| `k8s/volume11/secret.example.yaml` | 기본 적용 집합에서 제외된 Secret 자리표시자 |
| `tests/integration/test_volume11_health_artifacts.py` | 예제 경계와 Service 연결을 검사하는 오프라인 테스트 |

Python과 `uv`가 필요합니다. 6.1에는 `kubectl` CLI가 필요하지만 kubeconfig, 클러스터, Ingress Controller는 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 Kustomize를 로컬에서 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

출력에서 `kind: Ingress`, `host: api.volume11.example.invalid`, `ingressClassName: example-ingress-class`, backend Service `ai-platform-api`, 포트 `http`를 확인합니다. 이 명령은 파일을 로컬에서 조합할 뿐 API 서버에 연결하거나 리소스를 만들지 않습니다.

### 6.2 HTTP 경계 계약을 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 Ingress API 버전, 예제 IngressClass·호스트, `/` Prefix 규칙, Service 이름·포트 연결, TLS Secret과 인증 관련 값의 부재를 검사합니다. 컨테이너를 시작하거나 클러스터에 적용하거나 배포하지 않습니다.

## 7. Manifest 설명

`networking.k8s.io/v1`은 현재 Kubernetes Ingress API 버전입니다. backend에는 이전 API의 문자열 포트가 아니라 `service.name`과 `service.port.name`을 명시합니다. 명명된 `http` 포트를 사용하면 Service의 포트 계약을 문서화할 수 있고, Deployment의 컨테이너 포트와도 Service가 연결됩니다.

`path: /`와 `pathType: Prefix`는 이 작은 API 예제의 모든 HTTP 경로를 같은 backend에 전달하는 출발점입니다. 이는 접근 제어 정책이 아닙니다. `/livez`, `/readyz` 같은 운영 경로를 외부에 노출할지, 별도 경로 규칙·인증·제한을 둘지는 운영 요구사항과 Controller 기능을 검토해 결정합니다.

이 Manifest는 `tls:` 및 `secretName:`을 의도적으로 포함하지 않습니다. TLS 종료, 인증서 발급과 회전, DNS 소유권, Controller별 annotation, rate limit, 인증은 환경별 승인 절차와 별도 보안 설계가 필요합니다. 학습 파일에 실제 Secret 이름조차 넣지 않는 이유는 이름도 운영 구조를 노출할 수 있기 때문입니다.

## 8. 정상 실행 결과

6.1의 렌더링 출력에는 대략 다음 구조가 포함됩니다.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
spec:
  ingressClassName: example-ingress-class
  rules:
    - host: api.volume11.example.invalid
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ai-platform-api
                port:
                  name: http
```

출력에 실제 도메인, IP 주소, TLS Secret, 인증 토큰 또는 암호는 없어야 합니다. 6.2는 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `kubectl kustomize`를 찾을 수 없음 | `kubectl` CLI가 설치되지 않았을 수 있습니다. | Python 테스트는 먼저 실행하고, 승인된 CLI 설치 후 6.1의 로컬 렌더링만 다시 실행합니다. |
| 렌더링에서 Service 이름·포트가 다름 | Ingress backend와 Service 계약이 달라졌을 수 있습니다. | `ai-platform-api`와 명명된 `http` 포트를 함께 맞추고 테스트를 다시 실행합니다. |
| 브라우저에서 호스트가 열리지 않음 | `example.invalid`는 실제 DNS가 아니며 Controller도 설치하지 않았습니다. | 예상된 보호 동작입니다. DNS나 Controller를 이 학습 slice에서 구성하지 마세요. |
| 실제 환경에서 404 또는 Controller 미처리 | Controller, IngressClass, DNS, backend readiness의 운영 구성이 누락되었을 수 있습니다. | 조직의 승인된 플랫폼 절차에서 Controller 로그·클래스·DNS·Service endpoint를 검토합니다. 이 예제를 운영 값으로 바꾸지 마세요. |

## 10. 응용 실습

1. `/` Prefix 규칙과 `/v1` Prefix 규칙을 함께 쓸 때 예상 경로 표를 작성합니다. Manifest에는 실제 운영 도메인을 넣지 않습니다.
2. 공개 API, 내부 API, 상태 확인 경로를 같은 Ingress에 둘지 분리할지 위협 모델과 관찰성 관점에서 비교합니다.
3. 실제 환경에 TLS가 필요할 때 인증서 수명 주기, Secret 접근 권한, DNS 검증, 롤백 책임을 어느 팀이 갖는지 설계합니다. 실제 이름이나 값을 기록하지 않습니다.

## 11. 실무 적용

운영 Ingress에는 Controller의 공급망, 허용된 IngressClass, Namespace 격리, DNS 소유권, TLS 정책, HTTP 헤더 처리, 요청 크기·시간 제한, rate limit, 인증·인가, access log 개인정보 처리, DDoS 완화와 NetworkPolicy를 함께 검토해야 합니다. Controller annotation은 구현마다 의미가 달라 이식성과 보안 검토가 필요합니다.

backend가 준비되지 않았을 때의 동작도 중요합니다. Ingress는 Service와 endpoint에 전달할 뿐 `/readyz` 정책을 대신 판단하지 않습니다. [Health Probe 장](01-health-probes.md)의 liveness/readiness 분리와 [ConfigMap readiness 장](02-configmap-dependency-readiness.md)의 필수 의존성 정책을 서비스 운영 기준으로 유지해야 합니다.

## 12. 완료 체크리스트

- [ ] Ingress의 host/path 규칙과 Service backend의 책임을 구분할 수 있다.
- [ ] `ai-platform-api` Service의 `http` 포트를 참조함을 확인했다.
- [ ] `example-ingress-class`와 `example.invalid`가 비운영용 자리표시자임을 확인했다.
- [ ] `kubectl kustomize k8s/volume11`로만 Manifest를 로컬 렌더링했다.
- [ ] Volume 11 테스트가 통과했다.
- [ ] 실제 클러스터에 적용하거나 배포하지 않았고, DNS·TLS·Secret·Controller 설정을 저장하지 않았다.

## 13. 핵심 정리

Ingress는 HTTP 요청을 안정적인 Service 이름과 포트로 연결하는 선언 경계입니다. 이 장은 실제 Controller나 외부 연결을 만들지 않고 `example.invalid` 호스트, `example-ingress-class`, ClusterIP Service의 명명된 `http` 포트만 검증했습니다. 다음 Kubernetes 객체 실습에서는 배치 작업, 저장소, 확장 정책과 안전한 업데이트 경계를 추가합니다.
