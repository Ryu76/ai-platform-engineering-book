# AI 서비스 장애 대응과 관측 비용: 증거·결정·중단 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- health probe, 구조화 로그, 최소 telemetry가 장애를 자동으로 해결하지 않는 이유를 설명한다.
- 증거 수집, 영향 판단, 완화, 복구 검증, 사후 검토를 서로 다른 runbook 단계로 구분한다.
- readiness 실패와 exporter failure를 같은 원인으로 단정하지 않는 방법을 설명한다.
- cardinality, trace sampling, log volume, retention이 관측 비용과 privacy 위험을 함께 바꾸는 이유를 설명한다.
- 실제 alert, on-call, telemetry backend, cluster 또는 deployment 없이 예제 증거로 runbook 경계를 검토한다.

## 2. 왜 장애 대응과 비용을 함께 다루는가

AI API의 오류율이나 지연 시간이 올라갈 때 관측 데이터는 판단을 돕지만, 데이터가 많다고 판단이 자동화되지는 않습니다. `/livez`는 process가 응답할 수 있는지, `/readyz`는 이 예제의 injected readiness policy가 통과하는지만 말합니다. 둘 다 모델 품질, 인덱스 최신성, 외부 dependency의 실제 상태, 사용자 영향, capacity, 보안 사고 여부를 확정하지 않습니다.

또한 관측 데이터를 무제한으로 모으면 incident 중에는 검색할 정보가 늘어나는 것처럼 보여도 평상시 저장·전송·색인 비용, privacy 노출 범위, alert 피로가 커질 수 있습니다. Slice 09와 10의 request correlation 및 최소 telemetry는 **무엇을 기록하지 않을지**를 보여 주는 학습 경계입니다. 이 장은 그 경계를 바꾸거나 실제 운영 pipeline을 추가하지 않고, 증거와 비용에 근거한 의사결정표를 작성하는 방법만 다룹니다.

> [!WARNING]
> 이 slice는 runbook 문서와 오프라인 테스트만 제공합니다. `kubectl get`, `kubectl logs`, `kubectl describe`, `kubectl apply`, rollout, rollback, alert 생성, pager 설정, telemetry exporter·collector·backend 구성, 실제 query 실행, account·credential·endpoint·cluster 연결 또는 deployment를 실행하지 마세요. 아래의 모든 시간, threshold, 비용, 서비스 이름은 승인되지 않은 예제 값입니다.

## 3. 관측 신호의 책임 경계

| 신호 | 이 Volume 예제가 말해 주는 것 | 말해 주지 않는 것 | incident에서의 안전한 해석 |
|---|---|---|---|
| `/livez` 200 | WSGI process가 liveness response를 만들었다. | dependency, 모델 결과, 사용자 요청 성공, capacity | process가 살아 있다는 작은 증거로만 기록한다. |
| `/readyz` 200 또는 503 | 주입된 readiness policy가 현재 통과 또는 실패했다. | 실제 network dependency의 원인·복구, data integrity, 모든 사용자 영향 | policy 결과와 그 시각을 다른 증거와 분리해 적는다. |
| `http_request_completed` | allow-list route, status, request ID가 한 요청 완료 event에 연결됐다. | raw request, body, tenant, root cause | 동일 request ID가 있다고 인과 관계를 단정하지 않는다. |
| `probe_telemetry` | allow-list route와 HTTP status class/code의 local schema가 만들어졌다. | backend delivery, SLO, trace graph, raw path | status 추세를 위한 후보 증거로만 취급한다. |
| exporter callback 결과 | local callback이 성공 또는 실패했다. | application readiness, backend availability, retry 결과 | exporter failure를 readiness failure로 승격하지 않는다. |

이 표의 신호는 서로 대체되지 않습니다. 예를 들어 `/readyz`가 503인데 exporter도 실패했다면 먼저 response의 readiness policy 결과와 telemetry delivery failure를 별도 사건으로 적습니다. 반대로 `/readyz`가 200이고 exporter가 실패해도 Slice 10의 계약상 probe availability는 유지됩니다. 실제 공통 원인을 찾으려면 승인된 환경의 시간 동기화, 접근 제어된 증거, 담당자 검토가 필요합니다.

## 4. 예제 incident runbook의 단계

다음 순서는 실제 명령 목록이 아니라, 운영 승인 전 runbook에 넣을 **결정 단계**입니다. 각 단계는 입력, 담당 역할, 종료 조건을 명확히 해야 합니다.

```text
탐지 후보
  │  (예제: error-rate signal 또는 readiness failure report)
  ▼
영향 분류 ── 영향이 확인되지 않음 ──▶ 관찰 계속 / 종료 근거 기록
  │
  ▼
증거 보존 ── 민감 데이터 가능성 ──▶ 접근 제한된 사고 절차로 이관
  │
  ▼
완화 결정 ── 변경 위험이 큼 ──▶ 승인자와 rollback·데이터 호환성 검토
  │
  ▼
복구 검증 ── 신호 불일치 ──▶ 가설을 재분류하고 추가 증거 요청
  │
  ▼
사후 검토와 비용·보존 정책 갱신
```

### 4.1 탐지와 영향 분류

탐지는 incident의 시작 후보이지 원인 판정이 아닙니다. 예를 들어 `5xx` 비율 증가, `/readyz` 503, latency 증가, telemetry delivery failure는 각각 다른 trigger입니다. 승인된 runbook은 다음을 기록해야 합니다.

1. 관찰 시작 시각과 신호의 정의·집계 구간
2. 영향을 받은 것으로 **확인된** 사용자 경로 또는 기능과 아직 확인되지 않은 범위
3. customer impact, data integrity, security 가능성을 구분한 severity 기준
4. incident commander, technical lead, communications owner와 escalation 조건
5. false positive 또는 duplicate alert를 종료할 증거

이 저장소에서는 실제 route, 사용자, tenant, ticket ID, pager 대상, cluster 이름을 넣지 않습니다. 예제 표에는 `example-checkout-flow`, `placeholder-severity`, `sample-window`처럼 식별 불가능한 자리표시자만 사용합니다.

### 4.2 증거 보존과 가설 분리

증거는 원본 요청이나 비밀값을 복사하는 행위가 아닙니다. 필요한 최소 증거, 얻은 시각, 출처, 접근 권한, redaction 여부를 기록합니다. 한 신호에서 나온 가설은 서로 분리합니다.

| 예제 증거 | 가능한 가설 | 이 증거만으로 확정할 수 없는 것 | 다음 결정 질문 |
|---|---|---|---|
| sample window에서 `5xx` class 증가 | API 또는 dependency 경로가 실패 중일 수 있다. | 어떤 request, tenant, model 또는 dependency가 원인인지 | 사용자 영향과 readiness policy 결과가 같은 시간에 변했는가? |
| `/readyz`가 503 | required readiness check가 false일 수 있다. | network failure, credential, data corruption, Pod 상태 | policy 입력과 dependency contract를 승인된 절차에서 확인할 필요가 있는가? |
| exporter callback failure | 관측 delivery 경로가 실패했을 수 있다. | API가 unavailable인지, backend가 실제로 down인지 | availability와 delivery incident를 분리해 owner에게 보낼 것인가? |
| latency percentile 상승 | workload, queue, model warm-up 또는 downstream 대기가 늘었을 수 있다. | exact root cause, 안전한 rollback 여부 | capacity·변경 이력·dependency SLO를 별도 증거로 확인할 것인가? |

request ID, raw path, query, body, header, token, password, exception text를 일반 incident note나 metric label로 복사하지 않습니다. 승인된 incident 시스템이 별도 접근 제어와 보존 정책을 제공하더라도 필요한 범위와 redaction 기준은 security/privacy owner가 정해야 합니다.

### 4.3 완화와 변경 통제

완화는 원인 제거와 같지 않을 수 있습니다. traffic 제한, feature disable, dependency failover, capacity 조정, rollback, data restore는 각각 다른 위험과 승인 조건을 가집니다. 특히 Slice 08의 Deployment revision rollback은 Pod template 선택을 바꾸는 cluster-side 작업일 뿐 migration, cache, index, queue, external side effect를 되돌리지 않습니다.

승인된 runbook에는 적어도 다음을 포함합니다.

- 변경하지 않고 관찰할 기준과 관찰 책임자
- 변경 전 확인할 compatibility, data integrity, capacity, security 영향
- 변경을 승인할 역할, 중지 조건, 되돌림 기준
- concurrent incident 또는 active rollout과 충돌하는지 확인하는 절차
- customer communication의 사실·추정 구분과 업데이트 주기

이 교육 저장소에는 실행 가능한 rollback target, namespace, image digest, registry, change command를 추가하지 않습니다. `example.invalid` image와 placeholder Manifest도 실제 완화 수단이 아닙니다.

### 4.4 복구 검증과 종료

신호 하나가 정상으로 돌아왔다고 incident를 즉시 종료하면 partial recovery를 놓칠 수 있습니다. 종료 전에 SLO/SLI, readiness, error class, latency, dependency contract, data integrity, queued work, customer impact를 해당 서비스의 승인된 기준으로 구분해 확인해야 합니다. 정상 기간의 길이, sample size, signal freshness, known blind spot도 기록합니다.

복구 검증은 exporter delivery 성공 여부와 API 복구를 분리합니다. exporter가 실패해도 health probe가 살아 있는 Slice 10의 계약은 유효합니다. 반대로 exporter가 성공해도 사용자 요청이 성공했다는 증거는 아닙니다. 미해결 위험, 관찰 owner, 후속 deadline을 인계한 뒤에만 incident를 종료합니다.

## 5. 관측 비용과 privacy budget

관측 비용은 단순한 backend 청구서가 아닙니다. event 수, label cardinality, trace sampling, log payload 크기, retention, index, cross-region egress, query concurrency, access control, incident 대응 시간이 함께 영향을 줍니다. privacy 위험도 raw input과 identifier가 더 오래·더 넓게 복제될수록 증가합니다.

| 비용 driver | 안전한 예제 경계 | 운영 전 승인 질문 |
|---|---|---|
| metric labels | route allow-list와 status class만 사용 | label 조합의 최대 수와 cardinality budget은 얼마인가? |
| trace attributes | status code와 allow-list route만 사용 | trace ID·user/tenant ID·raw URL을 금지하거나 보호하는 규칙은 무엇인가? |
| logs | 완료 event의 작은 고정 schema | body/header/exception의 redaction, indexing, access는 어떻게 통제하는가? |
| sampling | 이 예제에는 sampling 없음 | head/tail sampling 기준, bias, error case 보존률, 비용 상한은 무엇인가? |
| retention | 이 예제에는 저장 backend 없음 | signal별 최소 보존 기간, deletion, legal hold, access review 기준은 무엇인가? |
| delivery | process-local callback만 사용 | queue, retry, drop, backpressure, egress, vendor 비용의 owner와 budget은 누구인가? |

### 5.1 budget을 문장으로 먼저 정하기

구체적 숫자를 config에 바로 넣기 전에 다음처럼 검토 가능한 문장을 작성합니다.

- **Cardinality:** “새 label은 예상 값의 수, 값 출처, 폭증 시 차단 방법, owner를 검토한 뒤에만 승인한다.”
- **Payload:** “raw URL, query, body, credential, user/tenant identifier, exception detail은 기본 telemetry schema에 넣지 않는다.”
- **Sampling:** “sample rate는 error/latency 가시성 손실과 예상 ingest 비용을 함께 검토하고 변경 이력을 남긴다.”
- **Retention:** “signal 유형별 보존 기간과 접근 역할을 최소화하고, 삭제·legal hold 절차를 분리한다.”
- **Alerting:** “새 alert는 action owner, severity, deduplication, escalation, false-positive 종료 기준이 없으면 활성화하지 않는다.”

이 문장들은 policy 초안이지 production default가 아닙니다. 실제 numeric budget, vendor 가격, data classification, compliance retention은 조직의 승인된 정보로 별도 관리해야 하며 이 repository에 저장하지 않습니다.

### 5.2 비용 사고도 incident로 취급하기

cardinality 급증, log storm, trace burst, retry loop, query fan-out은 availability가 정상이어도 비용·privacy incident가 될 수 있습니다. runbook은 다음의 안전 장치를 미리 정합니다.

1. ingest volume 또는 cardinality 증가를 누가 감지하고 owner에게 전달하는지
2. high-cardinality field를 어떻게 차단·redact하고, 그 변경이 debugging에 주는 blind spot을 어떻게 기록하는지
3. sampling 또는 retention을 줄일 때 investigation, audit, legal 요구와 어떻게 충돌 검토하는지
4. collector/backpressure failure를 application health와 분리하면서 data-loss signal을 어디에 남기는지
5. budget 초과 시 incident commander, finance/platform/privacy owner가 어떤 근거로 임시 조치를 승인하는지

여기에는 실제 rate limit, backend query, vendor account, API key, token, storage location을 넣지 않습니다.

## 6. 오프라인 검토 실습

### 6.1 예제 증거 매트릭스 읽기

다음 표는 **가상의** sample만 사용합니다. 숫자는 alert threshold나 SLO가 아닙니다.

| sample window | probe signal | telemetry delivery | customer-impact evidence | 결정 |
|---|---|---|---|---|
| `sample-a` | `/readyz` 200 | callback success | 없음 | 정상이라고 단정하지 말고 baseline 후보로만 기록 |
| `sample-b` | `/readyz` 503 | callback failure | 미확인 | readiness와 exporter 가설을 분리하고 영향 분류 진행 |
| `sample-c` | `/readyz` 200 | callback failure | 미확인 | telemetry delivery owner에게 별도 전달, API outage로 단정하지 않음 |
| `sample-d` | `/readyz` 503 | callback success | placeholder impact report | readiness policy, 사용자 영향, 변경 이력을 독립 증거로 검토 |

각 행에서 “확정 사실”, “가설”, “다음 확인”, “접근 제한 필요 여부”를 별도 칸에 작성합니다. request ID, raw input, 실제 서비스 이름, endpoint 또는 credential을 사용하지 않습니다.

### 6.2 Volume 11 오프라인 검사 실행

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/unit/test_volume11_telemetry.py tests/integration/test_volume11_health_artifacts.py -q
```

이 검사는 health/readiness, dependency policy, correlation logging, telemetry 최소화와 exporter failure 격리 계약을 확인합니다. 실제 alert를 만들거나 backend query를 보내거나 cluster에 연결하거나 resource를 생성하지 않습니다.

## 7. 오류 해결

| 증상 | 원인 확인 | 안전한 다음 단계 |
|---|---|---|
| readiness failure를 곧바로 dependency outage로 기록함 | readiness policy가 어떤 입력을 검사했는지와 실제 dependency 상태를 혼동했을 수 있다. | policy result와 external evidence를 분리하고 승인된 runbook으로 escalation한다. |
| exporter failure를 API outage로 기록함 | Slice 10은 exporter failure가 probe response를 바꾸지 않도록 설계했다. | observability delivery incident와 application availability incident의 owner·영향을 분리한다. |
| incident note에 raw request를 붙이고 싶음 | debugging 필요와 최소 수집 경계가 충돌했을 수 있다. | 승인된 접근 제어·redaction·retention 절차를 확인하고 이 repository에는 넣지 않는다. |
| 새 metric label로 원인을 빨리 찾고 싶음 | cardinality와 privacy 비용이 검토되지 않았을 수 있다. | 값의 수, 데이터 분류, budget, owner, expiry를 먼저 검토한다. |
| rollback이 가장 빠른 답처럼 보임 | revision rollback과 data/side-effect 복구를 같은 것으로 취급했을 수 있다. | Slice 08의 compatibility·migration·복구 검증 경계를 따라 승인된 변경 절차로 이관한다. |

## 8. 운영 전 검토 체크리스트

- [ ] alert마다 signal 정의, aggregation window, action owner, severity, deduplication, escalation, 종료 기준을 기록했다.
- [ ] liveness, readiness, request completion, telemetry delivery가 서로 다른 증거임을 설명할 수 있다.
- [ ] customer impact, data integrity, security 가능성을 같은 severity 신호로 뭉개지 않고 구분했다.
- [ ] raw path/query/body/header, credential, request ID, user/tenant identifier, exception detail의 수집·복사 금지 경계를 검토했다.
- [ ] 새 label/attribute의 cardinality, privacy classification, expected volume, retention, access owner, expiry를 승인했다.
- [ ] sampling, retry, queue, drop, backpressure, data-loss signal이 availability health와 분리돼 있음을 확인했다.
- [ ] rollback 또는 capacity 변경 전에 compatibility, migration, queue/index/cache, security, customer communication을 검토했다.
- [ ] recovery window와 incomplete recovery의 인계 조건을 정했다.
- [ ] 실제 alert, on-call, backend, cluster, Secret, credential 또는 deployment를 이 교육 저장소에서 만들지 않았다.

## 9. 핵심 정리

장애 대응은 한 telemetry signal이나 한 Kubernetes command로 끝나는 작업이 아닙니다. 이 Volume의 local health, correlation, telemetry 계약은 작고 privacy-aware한 증거를 만들며, exporter failure는 probe availability와 분리됩니다. 운영 runbook은 영향 분류·증거 보존·변경 통제·복구 검증을 분리하고, observability의 cardinality·sampling·retention·delivery 비용을 privacy와 함께 승인해야 합니다. 실제 command, alert, backend, cluster 연결, deployment는 승인된 운영 환경과 절차에서만 다룹니다.
