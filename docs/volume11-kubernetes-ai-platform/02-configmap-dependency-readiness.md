# ConfigMap과 의존성 readiness 정책 분리

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- ConfigMap에는 비밀이 아닌 readiness 정책만 넣고 Secret과 분리한다.
- API 자체 준비 상태와 Qdrant·Redis·PostgreSQL 같은 필수 의존성의 준비 상태를 구분한다.
- 네트워크 없이 주입한 검사 함수로 readiness 실패와 예외를 재현한다.
- 예제 Secret Manifest가 실제 Secret이 아니며 기본 적용 대상에서 제외됨을 확인한다.

## 2. 왜 필요한가

설정값과 인증 정보는 수명 주기와 접근 권한이 다릅니다. `AI_PLATFORM_REQUIRED_DEPENDENCIES`처럼 어떤 구성 요소가 필수인지 나타내는 정책은 ConfigMap에 둘 수 있습니다. 반면 접속 문자열, 토큰, 암호는 ConfigMap에도 예제 코드에도 넣지 않아야 합니다.

API가 실행 중이어도 필수 의존성 검사가 실패하면 `/readyz`는 `503`을 반환해야 합니다. 그러나 그 실패는 `/livez` 실패와 같지 않습니다. 또한 readiness 응답에 접속 주소, 오류 원문, 인증 정보를 넣으면 상태 확인 자체가 정보 노출 경로가 됩니다.

> [!WARNING]
> `k8s/volume11/secret.example.yaml`은 **적용 가능한 Secret이 아닙니다**. 값은 `REPLACE_WITH_APPROVED_SECRET_REFERENCE`라는 자리표시자뿐이며 `kustomization.yaml`에서 의도적으로 제외했습니다. 실제 값, base64 인코딩한 값, 레지스트리 주소, 클러스터 정보는 이 저장소에 추가하지 마세요.

## 3. 핵심 개념

- **ConfigMap:** 공개해도 되는 비밀이 아닌 설정입니다. 이 예제에서는 준비 정책의 이름 목록만 저장합니다.
- **Secret:** 인증 정보 등 제한해야 할 값의 Kubernetes 객체입니다. 이 장은 형태와 분리 원칙만 보여 주며 실제 값을 만들거나 적용하지 않습니다.
- **필수 의존성(required dependency):** 준비되지 않으면 새 API 요청을 받을 수 없다고 팀이 결정한 구성 요소입니다. 그 결정은 서비스마다 다릅니다.
- **의존성 검사(dependency check):** 실제 환경에서는 Timeout과 최소 권한을 가진 검사입니다. 이 장의 `DependencyReadiness`는 검사 함수를 주입받을 뿐 네트워크에 연결하지 않습니다.
- **실패 닫힘(fail closed):** 필요한 검사 함수가 빠졌거나 검사에서 예외가 나면 ready로 표시하지 않는 동작입니다.

## 4. 동작 구조

```text
ConfigMap (비밀 아님)
  ├─ AI_PLATFORM_READY=true
  ├─ AI_PLATFORM_REQUIRED_DEPENDENCIES=qdrant,redis,postgresql
  └─ AI_PLATFORM_READY_DEPENDENCIES=qdrant,redis,postgresql  [학습용 상태 라벨]
                         │
                         ▼
readiness_from_environment() ── 정책 라벨만 비교, 네트워크 호출 없음
                         │
                         ▼
HealthApplication /readyz ── 200 또는 503, 상세 원인은 응답에 넣지 않음

실제 검사로 확장할 때
DependencyReadiness(required, injected_checks)
  └─ 주입한 함수가 false 또는 예외 → false

Secret 예제: 자리표시자만 존재 ── kustomization.yaml에 미포함 ── 적용하지 않음
```

`AI_PLATFORM_READY_DEPENDENCIES`는 의존성의 실제 상태를 발견하는 기능이 아닙니다. 실습에서 ConfigMap 정책이 readiness 결과에 어떤 영향을 주는지 재현하는 비밀 없는 상태 라벨입니다. 실제 DB나 캐시 상태 확인은 다음 단계에서 명시적인 Timeout과 관찰성 설계를 갖춘 함수로 주입합니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `src/ai_platform/api/dependencies.py` | 정책 이름 파싱과 주입 가능한 `DependencyReadiness` |
| `src/ai_platform/api/health.py` | 환경 정책과 `/readyz` HTTP 계약 연결 |
| `examples/volume11/dependency_readiness_demo.py` | 포트·Docker·네트워크 없이 두 검사 결과를 출력 |
| `k8s/volume11/configmap.yaml` | 비밀 없는 예제 readiness 정책 |
| `k8s/volume11/secret.example.yaml` | 적용 대상이 아닌 Secret 모양의 자리표시자 |
| `tests/unit/test_volume11_dependencies.py` | 실패·예외·정책 형식 경계 테스트 |

Python과 `uv`만 필요합니다. Docker, Qdrant, Redis, PostgreSQL, Kubernetes 클러스터, API 키는 필요하지 않습니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
uv sync --all-groups
```

Windows에서 WSL을 사용한다면 저장소의 `/mnt/c/...` 경로로 이동한 뒤 같은 명령을 실행합니다.

## 6. 단계별 실습

### 6.1 주입한 검사 함수로 정책 확인

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume11/dependency_readiness_demo.py
```

이 명령은 세 개의 이름 라벨에 `True` 또는 `False`를 반환하는 로컬 함수를 주입합니다. 포트를 열거나 외부 서비스를 연결하지 않습니다.

### 6.2 readiness 계약과 ConfigMap 형태를 함께 검증

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 누락된 검사 함수, 검사 중 `TimeoutError`, 중복된 환경 라벨을 실패로 처리하는지 확인합니다. 또한 Secret 예제가 Kustomize 기본 적용 목록에 없고 자리표시자만 가지는지 검사합니다. 테스트는 클러스터에 적용하거나 배포하지 않습니다.

### 6.3 Kubernetes YAML을 연결 없이 렌더링

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
kubectl kustomize k8s/volume11
```

출력에는 Namespace, ConfigMap, Deployment, Service만 있어야 합니다. `secret.example.yaml`은 `resources` 목록에 없으므로 출력되지 않습니다. 이 명령은 로컬 렌더링만 수행하며 API 서버에 연결하거나 리소스를 만들지 않습니다.

## 7. 코드 설명

`dependency_names_from_environment()`는 쉼표로 구분된 이름을 소문자로 정규화하고, 중복·공백 외 문자·슬래시가 포함된 이름을 거절합니다. 이 함수는 환경 변수에서 주소나 인증 정보를 읽지 않습니다.

`environment_dependency_readiness()`는 required 이름 집합이 학습용 ready 이름 집합의 부분 집합인지 비교합니다. 이를 통해 ConfigMap 변경이 readiness를 바꾸는 경계를 오프라인에서 설명할 수 있습니다. 실제 연결 검사가 아니라는 점이 중요합니다.

`DependencyReadiness`는 required 이름마다 주입된 함수를 하나씩 실행합니다. 결과가 `False`이거나 예외가 발생하면 `False`를 반환합니다. `HealthApplication`도 readiness 콜백 예외를 `503`으로 바꾸므로, 내부 예외 메시지가 HTTP 응답으로 전달되지 않습니다.

## 8. 정상 실행 결과

6.1의 출력에는 다음 두 줄이 포함됩니다.

```text
all-required-dependencies-ready True
redis-unavailable False
```

6.2는 `passed`로 끝나야 합니다. 6.3의 Kustomize 출력에는 `kind: ConfigMap`이 포함되지만 `kind: Secret`은 포함되지 않아야 합니다. 이는 Secret을 생성하거나 적용했다는 뜻이 아니라, 예제 기본 적용 집합에 없다는 뜻입니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `/readyz`가 `503` | required 라벨이 ready 라벨에 모두 포함되는지 확인합니다. | 학습용 ConfigMap의 이름 철자를 맞추거나, 실제 환경에서는 검사 정책을 검토합니다. Secret을 추가하지 마세요. |
| `must not contain duplicate dependency names` | 같은 이름이 두 번 들어갔습니다. | 목록에서 중복을 제거합니다. 중복을 조용히 무시하지 않습니다. |
| `names may contain only letters, digits, and hyphens` | URL·포트·경로를 정책 이름에 넣었을 수 있습니다. | `redis` 같은 논리 이름만 둡니다. 주소와 인증 정보는 이 예제에 넣지 않습니다. |
| `every required dependency needs an injected check` | 코드의 required 목록과 검사 맵이 다릅니다. | 모든 필수 이름에 제한된 Timeout을 가진 검사를 명시적으로 주입하도록 설계합니다. |
| Secret이 Kustomize 출력에 보임 | 예제 파일을 resources에 추가했을 수 있습니다. | `secret.example.yaml`을 기본 적용 목록에서 제거하고, 실제 값은 승인된 별도 Secret 절차로 관리합니다. |

## 10. 응용 실습

1. Qdrant, Redis, PostgreSQL 중 서비스 기능에 반드시 필요한 항목과 선택 항목을 표로 분류합니다. 실제 주소나 계정은 쓰지 않습니다.
2. 각 필수 항목에 대해 Timeout, 성공 기준, 실패 시 API 트래픽 보류 여부, 경보 지표를 설계합니다.
3. `DependencyReadiness`에 선택 의존성 실패는 readiness를 막지 않는 별도 정책을 설계합니다. 단, 코드에 네트워크 호출이나 비밀값을 추가하지 않습니다.

## 11. 실무 적용

실제 readiness 검사는 요청 경로에서 새 연결을 무제한으로 만들지 않아야 합니다. 짧은 Timeout, 동시성 제한, 캐시된 최근 결과, 의존성별 메트릭을 고려합니다. 모든 의존성을 readiness에 넣으면 사소한 기능 장애가 전체 API를 비준비 상태로 만들 수 있으므로, 필수 여부를 제품 요구사항으로 결정합니다.

ConfigMap과 Secret을 구분해도 로그와 오류 메시지에서 비밀이 새지 않도록 해야 합니다. Secret의 이름, 외부 참조 방법, 권한 부여, 회전, 승인·롤백은 조직의 보안 절차에 따라 별도로 관리합니다.

## 12. 과제

- **기본:** ConfigMap에 넣을 값과 Secret으로 관리할 값을 각각 세 가지씩 분류하고 이유를 적습니다.
- **응용:** 의존성이 준비되지 않았을 때 `503` 응답, 알림, 재시도, 수동 승인 중 무엇이 필요한지 표로 작성합니다.
- **심화:** 실제 의존성 검사의 Timeout 예산이 Probe의 `timeoutSeconds`보다 작아야 하는 이유와, 검사 결과 캐시가 필요한 상황을 설명합니다.

## 13. 완료 체크리스트

- [ ] ConfigMap의 정책 라벨과 Secret의 인증 정보를 구분할 수 있다.
- [ ] `DependencyReadiness`가 false와 예외를 모두 not-ready로 처리함을 테스트로 확인했다.
- [ ] `/readyz` 응답에 의존성 주소·오류 원문·비밀값을 넣지 않음을 확인했다.
- [ ] `uv run python examples/volume11/dependency_readiness_demo.py`를 실행했다.
- [ ] Volume 11 테스트 명령이 통과했다.
- [ ] `secret.example.yaml`이 자리표시자만 포함하고 Kustomize 기본 resources에 없음을 확인했다.
- [ ] 클러스터에 적용하거나 배포하지 않았고, 실제 Secret·접속 정보·개인정보를 저장하지 않았다.

## 14. 핵심 정리

ConfigMap은 readiness 정책처럼 비밀이 아닌 설정에 사용하고, Secret은 실제 값 없이 형태만 예시로 남겨 기본 적용 집합에서 제외할 수 있습니다. readiness는 API 실행 여부와 필수 의존성 정책을 함께 판단하지만 liveness와 합치지 않습니다. 이 장은 실제 연결 대신 주입한 검사와 오프라인 상태 라벨로 실패 경계를 검증했습니다.
