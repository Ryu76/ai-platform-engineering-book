# Telemetry 데이터 최소화와 exporter failure 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- metric label과 trace attribute를 작은 allow-list로 제한하는 이유를 설명한다.
- request ID, raw path, query string, body, header, 환경 값과 오류 상세를 telemetry payload에서 제외한다.
- `exporter failure`가 health probe의 HTTP 결과를 바꾸지 않아야 하는 경계를 확인한다.
- collector, metric endpoint, trace exporter, backend 또는 cluster 없이 메모리 기반 예제를 검증한다.

## 2. 왜 데이터 최소화가 필요한가

Metric label은 가능한 값의 수가 작고 예측 가능해야 합니다. request ID, raw URL, 사용자 입력, tenant ID처럼 요청마다 바뀔 수 있는 값을 label로 넣으면 cardinality와 저장·조회 비용이 빠르게 늘고, 민감한 입력이 관측 시스템에 복제될 수 있습니다. Trace attribute도 같은 위험을 가집니다.

이 slice는 health probe 완료 뒤 로컬 JSON payload 하나를 만들되, route는 `/livez`, `/readyz`, `unmatched` 중 하나로 분류하고 status는 `2xx`·`4xx`·`5xx` 같은 class로만 metric label에 둡니다. trace 모양의 `span`에도 `http.route`와 `http.response.status_code`만 둡니다. 이는 학습용 schema이며 OpenTelemetry protocol, exporter protocol 또는 운영 telemetry 표준이 아닙니다.

> [!WARNING]
> 이 slice는 외부 telemetry를 전송하지 않습니다. `TelemetryExporter`는 테스트와 예제에서 주입하는 process 내부 callback일 뿐입니다. collector, telemetry backend, metric endpoint, trace exporter, URL, credential, queue, retry worker, `kubectl apply`, cluster 연결 또는 deployment를 실행하지 마세요.

## 3. 최소 schema

`src/ai_platform/api/telemetry.py`의 `probe_telemetry_event()`는 아래의 고정 JSON만 만듭니다.

```json
{"event":"probe_telemetry","metric":{"name":"http_server_requests_total","labels":{"route":"/livez","status_class":"2xx"}},"span":{"name":"health_probe","attributes":{"http.route":"/livez","http.response.status_code":200}}}
```

| 영역 | 허용 field | 제외하는 값 |
|---|---|---|
| metric | 고정 name, route 분류, HTTP status class | request ID, raw path, query, body, user/tenant 값, dependency 이름 |
| span | 고정 name, allow-list route, HTTP status code | trace ID, correlation ID, arbitrary header, remote address, 환경 값, exception text |
| delivery | 주입 callback의 성공/실패 boolean | endpoint, credential, retry payload, failure message |

`unmatched`는 알 수 없는 path의 원문을 보관하지 않는 분류 값입니다. status code는 100~599만 허용하며, metric에는 개별 code가 아닌 class만 넣습니다. 이 경계는 정확한 운영 dimension의 완전한 목록이 아니라, 새 field를 추가하기 전에 privacy·cardinality 검토를 요구하는 최소 예제입니다.

## 4. exporter failure 격리

`publish_probe_telemetry()`는 exporter가 없으면 `False`를 반환합니다. callback이 예외를 던져도 예외를 다시 던지거나 상세를 log에 쓰지 않고 `False`를 반환합니다. `HealthApplication`은 이 함수를 response 상태를 결정한 뒤 호출합니다. 따라서 observability delivery가 실패해도 readiness가 `True`인 `/readyz`는 계속 `200 OK`를 반환합니다.

이것은 exporter failure를 무시해도 된다는 뜻이 아닙니다. 실제 운영에서는 delivery failure에 대한 제한된 내부 측정, backpressure, bounded queue, sampling, retry/circuit-breaker 정책, data loss 허용 범위, alert ownership을 별도 설계·승인해야 합니다. 이 저장소의 예제에는 그런 runtime 구성이나 backend 연결을 넣지 않습니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `src/ai_platform/api/telemetry.py` | 최소 metric/span JSON schema와 failure-isolated callback 경계 |
| `src/ai_platform/api/health.py` | 완료된 health response와 optional local telemetry callback 연결 |
| `examples/volume11/telemetry_boundary_demo.py` | 메모리 WSGI, stdout collector, 실패 callback을 사용하는 예제 |
| `tests/unit/test_volume11_telemetry.py` | schema 최소화, status 범위, correlation label 부재, failure 격리 검사 |
| `tests/integration/test_volume11_health_artifacts.py` | 예제가 network나 telemetry backend 없이 실행됨을 검사 |

Python과 `uv`만 필요합니다. Kubernetes cluster, kubeconfig, container runtime, telemetry vendor, collector, endpoint, API key, token, password 또는 Secret은 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 로컬 telemetry boundary 예제 실행

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume11/telemetry_boundary_demo.py
```

첫 JSON 줄은 `/livez`의 최소 schema입니다. 이어지는 `local-export 200 OK`는 stdout list callback이 event를 받은 것을 보입니다. 마지막 `exporter-failure-isolated 200 OK`는 의도적으로 실패하는 callback 뒤에도 `/readyz` response가 성공함을 보입니다.

명령은 TCP listener를 열지 않고 `wsgiref` testing dictionary로 WSGI application을 호출합니다. stdout callback은 collector나 backend가 아니며 실제 metric endpoint 또는 trace exporter를 구성하지 않습니다.

### 6.2 Volume 11 오프라인 테스트 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/unit/test_volume11_telemetry.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 raw input이 `unmatched`로 바뀌는지, request ID가 telemetry label/attribute에 없는지, 잘못된 HTTP status가 거절되는지, exporter failure의 detail이 log에 남지 않고 response가 유지되는지 확인합니다. network, collector, metric endpoint, trace backend, Secret 또는 Kubernetes resource를 만들지 않습니다.

## 7. 코드 경계 설명

`probe_telemetry_event()`은 raw path 대신 allow-list route를 사용합니다. `status_class`는 integer status code에서 계산하지만 individual status code를 metric label로 만들지 않습니다. span의 status code도 제한된 HTTP result이며 request ID와 결합하지 않습니다.

`publish_probe_telemetry()`는 event를 만들고 주입된 callback을 한 번만 호출합니다. callback 내부의 `Exception`은 `False`로 바뀌며 exception text와 event payload는 log에 적지 않습니다. `BaseException` 계열을 숨기지 않으므로 process interruption 같은 제어 흐름은 억제하지 않습니다.

`HealthApplication`의 telemetry exporter 기본값은 `None`입니다. 따라서 기존 API는 delivery를 시도하지 않습니다. 예제와 테스트만 memory collector 또는 failure callback을 명시적으로 주입합니다. response의 `X-Request-ID`와 기존 구조화 completion log는 Slice 09의 correlation 용도이고, 새 metric/trace payload에는 포함하지 않습니다.

## 8. 정상 실행 결과

6.1 출력에는 다음처럼 allow-list route와 status class만 포함되어야 합니다.

```text
{"event":"probe_telemetry","metric":{"name":"http_server_requests_total","labels":{"route":"/livez","status_class":"2xx"}},"span":{"name":"health_probe","attributes":{"http.route":"/livez","http.response.status_code":200}}}
local-export 200 OK response-request-id=client-correlation-not-telemetry-label
exporter-failure-isolated 200 OK response-request-id=client-correlation-not-telemetry-label
```

첫 JSON에는 `client-correlation-not-telemetry-label`, raw request path, query string, body, endpoint, credential 또는 exporter exception detail이 없어야 합니다. 둘째·셋째 줄의 response header는 correlation 계약의 일부일 뿐 telemetry dimension이 아닙니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `ValueError: status_code must be an HTTP status code` | 직접 helper에 100~599 밖의 값을 전달했을 수 있습니다. | HTTP response status만 전달하고 임의 상태를 metric label로 사용하지 마세요. |
| event에 raw path가 필요해 보임 | route debugging 요구가 schema에 섞였을 수 있습니다. | raw path를 추가하지 말고 운영 환경의 접근 제어·redaction·retention을 포함한 별도 설계를 검토하세요. |
| exporter failure가 보이지 않음 | 이 slice는 failure detail을 stdout/log에 기록하지 않습니다. | local boolean 결과만 테스트하고, 실제 failure monitoring은 승인된 운영 설계에서 ownership과 privacy 경계를 정의하세요. |
| backend에 metric/trace가 없음 | 예제에는 backend, collector, metric endpoint가 없습니다. | 이 slice에서 exporter나 endpoint를 추가하지 마세요. 승인된 환경에서 별도 integration을 계획하세요. |

## 10. 운영 전 검토 경계

실제 telemetry를 설계하기 전 다음을 승인된 환경에서 검토합니다.

1. metric label과 trace attribute 각각의 cardinality budget, PII/Secret 분류, raw URL/header/body 금지 규칙
2. correlation ID, trace ID, user/tenant ID, idempotency key를 telemetry dimension으로 사용할 수 있는지와 retention/access control
3. trace sampling, metric aggregation, log redaction, schema versioning, 삭제 요구와 비용 한도
4. exporter failure, collector backpressure, bounded queue, retry, circuit breaker, drop policy, data loss signal과 alert owner
5. health/readiness가 observability backend 상태에 의존하지 않는지 및 incident runbook
6. vendor endpoint, TLS, credential, network egress, cluster policy와 deployment 승인 절차

이 저장소에는 실제 collector 주소, vendor, endpoint, account, credential, Secret, cluster 이름 또는 deployment 설정을 저장하지 않습니다.

## 11. 완료 체크리스트

- [ ] metric label과 trace attribute가 raw request input을 포함하지 않음을 확인했다.
- [ ] `unmatched` route와 status class가 low-cardinality 분류임을 설명할 수 있다.
- [ ] correlation ID가 telemetry label/attribute에 없음을 확인했다.
- [ ] exporter failure가 exception detail을 기록하지 않고 health response를 바꾸지 않음을 확인했다.
- [ ] 예제와 Volume 11 오프라인 테스트를 실행했다.
- [ ] collector, metric endpoint, exporter backend, Secret, cluster 연결 또는 deployment를 만들지 않았다.

## 12. 핵심 정리

이 slice는 health probe telemetry를 고정 name, allow-list route, status class/code만 가진 local JSON schema로 제한했습니다. request ID와 raw request input을 dimension으로 삼지 않았고, injected exporter callback의 failure가 probe availability를 바꾸거나 exception detail을 기록하지 않도록 분리했습니다. 실제 collector·backend·retry·alert·비용·privacy 정책은 운영 승인 환경에서 별도의 설계와 검증이 필요합니다.
