# Job과 CronJob: 완료·재시도·중복 실행 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- 요청을 계속 처리하는 Deployment와 끝나는 작업을 실행하는 Job의 책임을 구분한다.
- `backoffLimit`, `activeDeadlineSeconds`, `restartPolicy: Never`가 실패·재시도 경계를 만드는 방식을 설명한다.
- CronJob의 `suspend`, `concurrencyPolicy`, 작업 이력 제한이 예약 작업의 중복·누적 위험을 어떻게 줄이는지 읽는다.
- 자리표시자 이미지와 Kustomize 로컬 렌더링만으로 Job/CronJob 형상을 오프라인 검증한다.

## 2. 왜 필요한가

AI Platform에는 API처럼 계속 살아 있어야 하는 프로세스뿐 아니라, 임시 인덱스 점검, 허용된 데이터 정리, 보고서 준비처럼 **성공 또는 실패로 끝나야 하는 작업**도 있습니다. 이를 Deployment로 실행하면 완료 뒤에도 Pod가 다시 유지되어 실행 횟수와 종료 기준을 파악하기 어렵습니다. Job은 완료 횟수와 실패 재시도 횟수를 선언하고, CronJob은 그 Job을 예약합니다.

하지만 Job 또는 CronJob YAML만으로 안전한 운영 작업이 되지는 않습니다. 작업 명령이 데이터에 미치는 영향, 입력의 승인, 권한, 실제 이미지, Secret, 네트워크, 모니터링, 복구 절차는 별도 운영 설계가 필요합니다. 이 장의 두 Manifest는 `example.invalid` 이미지와 출력 전용 명령만 사용하고 기본 Kustomize 집합에서도 제외합니다. 따라서 실제 작업, 클러스터 연결, 데이터 변경, 예약 실행을 만들지 않습니다.

> [!WARNING]
> `k8s/volume11/batch/`는 **로컬 렌더링용 학습 Manifest** 집합입니다. `kubectl apply`, `kubectl create`, 실제 CronJob 활성화, 이미지 교체, 클러스터 연결을 실행하지 마세요. CronJob은 `suspend: true`이며, 두 이미지 모두 의도적으로 가져올 수 없는 자리표시자입니다.

## 3. 핵심 개념

- **Job:** 지정한 완료 횟수에 도달하면 끝나는 Pod 작업을 관리하는 Kubernetes 객체입니다.
- **CronJob:** 정해진 schedule에 따라 Job을 만들 수 있는 예약 객체입니다. 이 예제는 `suspend: true`로 새 Job 생성을 막습니다.
- **`backoffLimit`:** 실패한 Pod 실행을 다시 시도할 수 있는 상한입니다. 무제한 재시도를 의미하지 않습니다.
- **`activeDeadlineSeconds`:** Job이 실행될 수 있는 전체 시간 상한입니다. 장기 정지나 무한 대기를 막는 한 겹의 경계입니다.
- **`restartPolicy: Never`:** 같은 Pod 안에서 컨테이너를 재시작하지 않고, 실패한 Pod의 재시도 관리를 Job controller에 맡깁니다.
- **`concurrencyPolicy: Forbid`:** 이전 예약 Job이 아직 끝나지 않았으면 CronJob이 겹치는 새 실행을 만들지 않도록 요청합니다.
- **`ttlSecondsAfterFinished`:** 끝난 Job을 일정 시간 후 정리하도록 요청하는 보존 경계입니다. 실제 클러스터의 TTL controller와 보존 정책은 별도 확인이 필요합니다.

## 4. 동작 구조

```text
한 번 실행하는 형상 (job.yaml)

Job: ai-platform-maintenance-once
  completions: 1 ─────► 성공 1회면 완료
  backoffLimit: 2 ─────► 실패 재시도 상한
  activeDeadlineSeconds: 120 ─────► 전체 실행 시간 상한
  restartPolicy: Never ─────► Pod 안 무한 재시작 없음
  image: example.invalid/... ─────► 실제 실행 불가 자리표시자

예약 형상 (cronjob.yaml)

CronJob: ai-platform-maintenance-scheduled
  schedule: "0 3 * * *" (예시 시간)
  suspend: true ─────► 이 학습 Manifest에서는 Job을 만들지 않음
  concurrencyPolicy: Forbid ─────► 이전 실행과 중복 금지 요청
  jobTemplate ─────► backoffLimit: 1, activeDeadlineSeconds: 120

기본 k8s/volume11/kustomization.yaml: Job/CronJob 미포함
클러스터 적용, 실제 이미지, Secret, 데이터 접근: 이 slice에 없음
```

Job은 `completions: 1`, `parallelism: 1`로 한 번의 성공을 목표로 합니다. 실패하면 controller가 최대 `backoffLimit: 2` 범위에서 새 Pod를 시도할 수 있지만, `activeDeadlineSeconds: 120`을 넘겨 계속 실행되지는 않습니다. 이는 작업 자체가 멱등성(idempotency)을 가진다는 보장이 아닙니다. 재시도되더라도 결과가 중복되지 않게 만드는 책임은 작업 로직과 승인된 저장소 설계에 있습니다.

CronJob은 같은 작업 형상을 `jobTemplate`에 보관합니다. 예제 schedule은 읽기용일 뿐이며 `suspend: true`가 우선하므로 이 Manifest로는 예약 Job이 생성되지 않습니다. 실제 환경에서 suspend를 해제하기 전에는 시간대, 중복 실행, 작업 최대 시간, 실패 경보, 결과 보존, 롤백 가능성을 승인 절차에서 검토해야 합니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/batch/job.yaml` | 한 번 완료하는 maintenance Job의 예제 형상 |
| `k8s/volume11/batch/cronjob.yaml` | suspend된 예약 maintenance Job의 예제 형상 |
| `k8s/volume11/batch/kustomization.yaml` | Job/CronJob만 조합하는 로컬 렌더링 집합 |
| `k8s/volume11/kustomization.yaml` | 안전을 위해 Job/CronJob을 포함하지 않는 기본 렌더링 집합 |
| `k8s/volume11/deployment.yaml` | 요청을 계속 처리하는 API Deployment와 비교할 대상 |
| `tests/integration/test_volume11_health_artifacts.py` | 배치 작업의 placeholder·재시도·중복 방지 경계를 검사하는 오프라인 테스트 |

Python과 `uv`가 필요합니다. 6.1에는 `kubectl` CLI가 필요하지만 kubeconfig, Kubernetes 클러스터, 실제 controller는 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 배치 Manifest를 로컬에서 렌더링

```bash
# 실행 위치: 저장소 루트의 WSL Ubuntu 또는 Linux 터미널
kubectl kustomize k8s/volume11/batch
```

`kubectl kustomize`는 API 서버에 리소스를 만들지 않고 로컬에서 YAML 파일을 조합합니다. 출력에서 `kind: Job` 또는 `kind: CronJob`, `example.invalid/ai-platform-maintenance:0.1.0`, Job의 `backoffLimit`, CronJob의 `suspend: true`와 `concurrencyPolicy: Forbid`를 확인합니다. **명령을 `apply`나 `create`로 바꾸지 마세요.**

### 6.2 기본 API 집합에 배치 작업이 없는지 로컬 렌더링

```bash
# 실행 위치: 저장소 루트의 WSL Ubuntu 또는 Linux 터미널
kubectl kustomize k8s/volume11
```

출력에는 기존 Namespace, ConfigMap, Deployment, Service, Ingress만 포함됩니다. `kind: Job`과 `kind: CronJob`은 없어야 합니다. 이 분리는 학습자가 기본 API 형상을 로컬에서 읽을 때 배치 작업이 실수로 적용 집합에 섞이지 않게 합니다. `kustomize`는 파일을 조합할 뿐 클러스터에 연결하거나 리소스를 생성하지 않습니다.

### 6.3 Volume 11 경계를 테스트

```bash
# 실행 위치: 저장소 루트의 WSL Ubuntu 또는 Linux 터미널
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 두 Manifest가 `batch/v1` 객체인지, 이미지가 자리표시자인지, Job의 완료·재시도·시간 경계가 있는지, CronJob이 suspend 상태이며 중복을 금지하는지, Secret·토큰·암호·호스트 주소가 없는지 검사합니다. Pod, 컨테이너, 예약 작업, 클러스터 리소스는 만들지 않습니다.

## 7. Manifest 설명

`job.yaml`의 `restartPolicy: Never`는 컨테이너가 실패할 때 같은 Pod에서 계속 재시작하는 대신 Job controller가 새 Pod를 만들도록 합니다. 따라서 `backoffLimit`은 작업의 실패 시도 횟수를 읽을 수 있는 명시적 상한이 됩니다. `ttlSecondsAfterFinished`는 완료된 예제 작업이 영구히 남지 않도록 하는 요청이지만, 실제 정리 동작은 클러스터 controller 지원과 정책에 달려 있습니다.

`cronjob.yaml`은 같은 보안 컨텍스트와 자원 상한을 `jobTemplate`에 둡니다. `suspend: true`는 schedule 문자열이 있어도 새 Job 생성을 멈춥니다. `concurrencyPolicy: Forbid`는 이전 작업이 길어졌을 때 겹치는 실행을 피하는 선언입니다. 이미 중복된 외부 효과를 되돌리거나, 수동으로 생성한 Job을 막거나, 작업 로직을 멱등하게 만들지는 않습니다.

두 파일은 `example.invalid/ai-platform-maintenance:0.1.0`과 출력 전용 placeholder 명령만 씁니다. 연결 주소, `env`, `envFrom`, Secret 참조, 서비스 계정 토큰, 인증서, 실제 데이터 명령은 넣지 않았습니다. 명령을 실제 maintenance 로직으로 바꾸는 일은 이 교재 범위 밖이며 조직의 코드 검토·권한 승인·Secret 관리·백업·복구 절차가 필요합니다.

## 8. 정상 실행 결과

6.1의 출력은 대략 다음 구조를 포함합니다.

```yaml
apiVersion: batch/v1
kind: Job
spec:
  completions: 1
  backoffLimit: 2
  activeDeadlineSeconds: 120
  template:
    spec:
      restartPolicy: Never
```

두 번째 출력에는 다음 CronJob 경계가 보입니다.

```yaml
apiVersion: batch/v1
kind: CronJob
spec:
  schedule: "0 3 * * *"
  suspend: true
  concurrencyPolicy: Forbid
```

6.2 출력에는 `kind: Job`이나 `kind: CronJob`이 없어야 합니다. 6.3은 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `kubectl kustomize`를 찾을 수 없음 | `kubectl` CLI가 설치되지 않았을 수 있습니다. | Python 테스트를 먼저 실행하고, 승인된 CLI 설치 후 6.1의 로컬 렌더링만 다시 실행합니다. |
| 렌더링에서 YAML 오류 | 들여쓰기, `batch/v1`, Job template의 `restartPolicy`가 바뀌었을 수 있습니다. | `batch/job.yaml` 또는 `batch/cronjob.yaml`의 `spec.template.spec` 구조를 복원하고 다시 렌더링합니다. |
| CronJob이 실제로 실행될까 우려됨 | 예제 파일의 `suspend` 값이 바뀌었을 수 있습니다. | `suspend: true`를 복원하고 클러스터에는 적용하지 않습니다. |
| 작업이 여러 번 실행됨 | 실제 운영 작업에서 retry, schedule, 수동 실행, 외부 시스템의 멱등성이 함께 검토되지 않았을 수 있습니다. | 승인된 운영 절차에서 작업 키·중복 방지·감사 로그·복구 계획을 설계합니다. 이 예제에 연결 정보나 실제 명령을 추가하지 마세요. |
| `example.invalid` 이미지를 가져올 수 없음 | 이미지가 의도적으로 비실행용 자리표시자입니다. | 예상된 보호 동작입니다. 이미지 pull이나 실제 이미지 이름 추가를 시도하지 마세요. |

## 10. 응용 실습

1. 하루에 한 번 실행할 작업이 10분을 넘기면 어떤 `activeDeadlineSeconds`, 중복 정책, 실패 알림이 필요한지 설계합니다.
2. 동일한 인덱스 갱신 요청이 재시도되어도 결과가 두 번 반영되지 않게 하려면 작업 입력과 저장 결과에 어떤 식별자가 필요한지 설명합니다.
3. API Deployment의 liveness/readiness와 배치 Job의 완료/실패 판단을 표로 비교합니다. 실제 이미지나 연결 정보를 쓰지 않습니다.

## 11. 실무 적용

실제 AI 운영의 배치 작업은 모델·문서 색인, 오래된 데이터 정리, 평가 보고서 생성처럼 비용과 데이터 일관성에 직접 영향을 줄 수 있습니다. 따라서 실행 주체의 최소 권한, 입력 범위 승인, Secret 접근 분리, 네트워크 제한, 작업별 로그와 메트릭, 실패 경보, 재시도 지수 백오프, 중복 방지 키, 결과 검증, 백업·복구 계획을 함께 설계해야 합니다.

`concurrencyPolicy: Forbid`는 같은 CronJob에서 겹치는 예약을 줄이는 도구일 뿐 전역 잠금이 아닙니다. controller 중단, 수동 Job 생성, 여러 환경, 외부 큐의 재전달은 별도로 다뤄야 합니다. 마찬가지로 `backoffLimit`은 재시도 횟수 상한이지 안전한 재시도의 증명이 아닙니다. 상태를 바꾸는 작업은 멱등성·원자성·감사 가능성을 코드 수준에서 검증해야 합니다.

## 12. 과제

- **기본:** Job의 `restartPolicy: Never`와 `backoffLimit`이 각각 어느 controller의 행동과 관련되는지 한 문장씩 작성합니다.
- **응용:** CronJob을 활성화하기 전에 검토할 시간대, 실행 최대 시간, 중복 방지, 실패 경보, 결과 보존 항목을 체크리스트로 만듭니다.
- **심화:** 데이터 색인 작업에 대해 입력 버전, 실행 ID, 중복 방지 키, 실패 후 재개 기준, 롤백·복구 증거를 포함하는 멱등성 설계를 작성합니다. 실제 데이터·주소·인증 정보는 기록하지 않습니다.

## 13. 완료 체크리스트

- [ ] Deployment와 Job의 수명 주기 차이를 설명할 수 있다.
- [ ] Job의 `completions`, `backoffLimit`, `activeDeadlineSeconds`, `restartPolicy: Never`을 확인했다.
- [ ] CronJob이 `suspend: true`이고 `concurrencyPolicy: Forbid`임을 확인했다.
- [ ] 두 이미지가 `example.invalid` 자리표시자임을 확인했다.
- [ ] `kubectl kustomize k8s/volume11/batch`로만 배치 형상을 렌더링했고 기본 Kustomize 집합에 배치 작업이 없음을 확인했다.
- [ ] Volume 11 테스트가 통과했다.
- [ ] 실제 클러스터, 이미지, Secret, 데이터, 예약 실행을 만들거나 저장하지 않았다.

## 14. 핵심 정리

Job은 성공 횟수, 실패 재시도, 전체 실행 시간으로 끝나는 작업의 경계를 선언합니다. CronJob은 그 작업을 예약하지만, 이 학습 예제는 `suspend: true`와 `example.invalid` 이미지로 실행을 막고 `concurrencyPolicy: Forbid`로 중복 방지 의도를 보여 줍니다. 로컬 dry-run과 오프라인 테스트만으로 형상을 확인했으며, 다음 Kubernetes 객체 실습에서는 상태 저장소와 확장 정책의 안전한 경계를 다룹니다.
