# 구조화된 request correlation logging: 관측 경계를 로컬에서 읽기

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 요청 correlation ID가 응답과 구조화된 완료 로그를 연결하는 방법을 설명한다.
- 허용된 `X-Request-ID` 형식과 서버 생성 ID의 차이를 구분한다.
- JSON 로그에서 이벤트명, route 분류, HTTP 상태 코드만 기록하는 이유를 설명한다.
- telemetry backend, trace exporter, metric endpoint, cluster 없이 메모리 기반 예제를 검증한다.

## 2. 왜 필요한가

AI API의 health 요청처럼 짧은 요청도 여러 로그 사이에서 같은 요청을 찾아야 할 때가 있습니다. 이 slice는 `X-Request-ID`를 응답에 돌려주고 같은 값을 한 개의 `http_request_completed` JSON 이벤트에 기록하는 최소 correlation 계약을 제공합니다.

그러나 correlation ID가 관측성 전체는 아닙니다. 이 코드에는 OpenTelemetry SDK, trace exporter, logging collector, dashboard, metric scrape endpoint, 외부 URL, credential 또는 Kubernetes 연결이 없습니다. 로그 한 줄은 latency SLO, 오류 원인, dependency health, 비용, alert 또는 incident 대응을 보장하지 않습니다.

입력값을 그대로 로그에 쓰면 query string, body, 비밀값 또는 개인 정보가 로그로 흘러갈 수 있습니다. 따라서 이 예제는 길이와 문자 집합이 제한된 `X-Request-ID`만 수용하고, 그 밖의 값은 새 ID로 바꿉니다. 알려진 `/livez`와 `/readyz`만 route로 기록합니다. 그 외 path는 원문 대신 `unmatched`로 분류합니다.

> [!WARNING]
> 이 slice는 로컬 Python 표준 라이브러리 logging과 메모리 WSGI 호출만 사용합니다. logging backend 연결, log collector 설치, trace·metric exporter 설정, endpoint 추가, `kubectl apply`, cluster 연결 또는 deployment를 실행하지 마세요.

## 3. 핵심 개념

- **correlation ID:** 하나의 요청과 그 요청의 응답·로그를 연결하는 불투명 식별자입니다. 사용자·세션·Secret의 대체물이 아닙니다.
- **`X-Request-ID`:** 이 예제에서 수용하거나 응답에 반환하는 HTTP header 이름입니다. 값은 영문·숫자로 시작하고 영문·숫자·`.`·`_`·`-`로만 이루어진 1~64자여야 합니다.
- **서버 생성 ID:** header가 없거나 형식에 맞지 않을 때 `uuid4().hex`로 만드는 불투명 ID입니다. 예제의 factory는 테스트를 위해 주입할 수 있습니다.
- **구조화된 로그:** JSON object처럼 고정 key를 가진 로그입니다. 이 slice의 key는 `event`, `request_id`, `route`, `status_code`뿐입니다.
- **route 분류:** 원본 path를 보관하지 않고 알려진 probe route 또는 `unmatched`만 기록하는 privacy 경계입니다.

## 4. 로컬 이벤트 흐름

```text
메모리 WSGI 요청
  HTTP_X_REQUEST_ID: client-example-11
          |
          v
형식 검사 (1~64자 allow-list)
          |
          +-- 통과 --> response X-Request-ID: client-example-11
          |
          +-- 없음/실패 --> uuid4().hex 또는 주입된 example ID 생성
                                  |
                                  v
GET /livez 또는 GET /readyz 처리
                                  |
                                  v
{"event":"http_request_completed","request_id":"...","route":"/livez","status_code":200}

query string / body / 임의 header / 예외 상세 / telemetry backend / network: 기록하거나 연결하지 않음
```

`request_id`는 correlation을 위한 값이지 신뢰된 인증 정보가 아닙니다. 허용 형식의 client 값도 요청 경로를 잇는 표식일 뿐이며 권한 부여, tenant 판별, 감사 보존 정책에 사용하면 안 됩니다. 운영에서 외부 요청 ID를 수용할지, proxy가 새로 만들지, 보존 기간과 접근 통제를 어떻게 할지는 별도의 보안·privacy 검토가 필요합니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `src/ai_platform/api/correlation.py` | allow-list 검사, 서버 생성 ID, JSON 완료 이벤트 형식 |
| `src/ai_platform/api/health.py` | 응답 header와 완료 로그를 같은 correlation ID로 연결하는 WSGI API |
| `examples/volume11/correlation_logging_demo.py` | TCP listener 없이 accepted/generated/rejected 경우를 출력하는 예제 |
| `tests/unit/test_volume11_health.py` | response header, JSON event, 원본 path·잘못된 header 미기록을 검사하는 단위 테스트 |
| `tests/integration/test_volume11_health_artifacts.py` | 예제 스크립트가 network나 telemetry backend 없이 실행되는지 검사 |

Python과 `uv`만 필요합니다. kubeconfig, Kubernetes cluster, container runtime, telemetry collector, log backend, registry, URL 또는 credential은 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 메모리 기반 correlation 예제 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/correlation_logging_demo.py
```

출력에는 세 개의 JSON 완료 이벤트와 response header 확인 줄이 나타납니다. 첫 번째는 `client-example-11`을 수용합니다. 두 번째는 header가 없어서 `generated-example-11`을 생성합니다. 세 번째는 공백이 든 header를 수용하지 않고 `generated-after-invalid-11`으로 바꿉니다.

명령은 TCP port를 열거나 HTTP 요청을 보내지 않습니다. `wsgiref`의 테스트 환경 dictionary로 `HealthApplication`을 호출하며 logger는 현재 process stdout에만 연결합니다.

### 6.2 Volume 11 경계를 오프라인 테스트로 확인

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 허용된 client ID가 response와 JSON 로그에 같게 나타나는지, 잘못된 header가 생성 ID로 대체되는지, 임의 path가 `unmatched`가 되는지 확인합니다. query string, body, 실제 request header 값, dependency 오류 상세, Secret, telemetry 또는 cluster 리소스를 만들지 않습니다.

## 7. 코드 경계 설명

`request_id_from_environ()`은 WSGI `HTTP_X_REQUEST_ID`가 정규식 allow-list 전체와 일치할 때만 반환합니다. 값이 없거나 유효하지 않으면 factory에서 새 안전한 값을 받습니다. factory가 안전하지 않은 값을 반환하면 `ValueError`로 개발 중의 잘못된 주입을 드러냅니다. 기본 factory는 UUID hex만 만듭니다.

`request_completion_event()`는 다음 네 개의 field만 JSON으로 직렬화합니다.

```json
{"event":"http_request_completed","request_id":"client-example-11","route":"/livez","status_code":200}
```

`HealthApplication`은 응답이 정해진 뒤 `X-Request-ID` header를 붙이고 이 이벤트를 한 번 기록합니다. `route`에 raw path를 넣지 않으므로 알 수 없는 path의 사용자 입력이 로그에 남지 않습니다. 현재 API가 health probe 두 개뿐이므로 method, query, body, remote address, user agent, environment, exception message와 dependency 이름은 이벤트에 포함하지 않습니다.

이 설계는 로그 payload를 작고 예측 가능하게 유지하지만, 운영에 필요한 모든 audit field를 정의하지는 않습니다. 새로운 route나 식별자를 추가하기 전에는 PII 분류, header 신뢰 경계, log redaction, sampling, 보존, 접근 권한과 비용을 검토해야 합니다.

## 8. 정상 실행 결과

6.1의 첫 부분은 대략 다음과 같습니다.

```text
{"event":"http_request_completed","request_id":"client-example-11","route":"/livez","status_code":200}
accepted 200 OK response-request-id=client-example-11
```

이 출력에 endpoint URL, API key, token, password, request body, query string, trace ID, span ID, metric value 또는 collector address는 없어야 합니다. 6.2는 설치 환경에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| response ID가 client 값과 다름 | `X-Request-ID`가 공백·허용하지 않는 문자·65자 이상을 포함할 수 있습니다. | allow-list에 맞는 예제 값을 사용하거나 서버 생성 ID를 correlation 값으로 사용합니다. 형식 제한을 우회하지 마세요. |
| 로그의 route가 `unmatched` | health probe 이외의 path이거나 path 형식이 달라졌을 수 있습니다. | 현재 slice에서는 raw path를 로그에 추가하지 말고, 새 route의 privacy 검토와 테스트를 먼저 수행합니다. |
| JSON 로그가 backend에 없음 | 이 예제는 process stdout handler만 만들며 exporter·collector가 없습니다. | 이 slice에서 외부 backend를 설정하지 마세요. 승인된 운영 observability 설계에서 수집 경로를 별도로 검토합니다. |
| factory `ValueError` | 테스트용 factory가 안전한 ID 형식을 반환하지 않았습니다. | 영문·숫자로 시작하는 1~64자의 allow-list 값으로 고치거나 기본 factory를 사용합니다. |

## 10. 운영 전 검토 경계

실제 서비스에서 request correlation logging을 도입하기 전 다음을 승인된 환경에서 검토합니다.

1. ingress, gateway, application 중 어느 계층이 correlation ID를 생성·검증·전파하는지
2. client-supplied ID를 신뢰할 수 없는 입력으로 처리하는 정책과 header spoofing 경계
3. request, response, error, audit 로그별 PII·Secret redaction과 raw URL·body·header 보존 금지 규칙
4. log schema versioning, sampling, retention, access control, deletion 요구와 비용 한도
5. trace·metric·log의 correlation 방식, exporter failure, collector backpressure, alert와 incident runbook
6. request ID가 인증, 권한, tenant isolation, idempotency key 또는 compliance audit ID와 혼동되지 않는지

이 저장소에는 실제 endpoint, telemetry vendor, collector 주소, dashboard, credential, user data, cluster 이름 또는 deployment 설정을 저장하지 않습니다.

## 11. 완료 체크리스트

- [ ] correlation ID가 응답과 한 개의 완료 로그를 연결하는 표식임을 설명할 수 있다.
- [ ] 허용된 `X-Request-ID`와 서버 생성 ID의 경계를 확인했다.
- [ ] JSON event가 `event`, `request_id`, `route`, `status_code`만 기록함을 확인했다.
- [ ] 알 수 없는 path와 잘못된 header 원문이 로그에 기록되지 않음을 확인했다.
- [ ] 예제와 Volume 11 오프라인 테스트를 실행했다.
- [ ] telemetry backend, exporter, metric endpoint, Secret, cluster 연결 또는 deployment를 만들지 않았다.

## 12. 핵심 정리

구조화된 request correlation logging은 같은 요청의 응답과 로그를 작은 공통 ID로 잇는 출발점입니다. 이 장은 제한된 `X-Request-ID` 또는 서버 생성 UUID hex, allow-list route, HTTP 상태 코드만 가진 로컬 JSON 이벤트를 메모리 WSGI로 검증했습니다. 실운영 telemetry 수집, trace·metric correlation, privacy·retention·access control, alert와 incident 대응은 승인된 환경에서 별도의 설계·증거·검토가 필요합니다.
