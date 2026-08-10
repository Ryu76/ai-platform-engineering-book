# Docker Compose 의존 서비스 토폴로지: 실행 전 경계 확인

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Docker Compose에서 API, Qdrant, Redis, PostgreSQL의 논리적 연결 구조를 읽는다.
- `depends_on`의 시작 순서와 API readiness의 준비 판단을 구분한다.
- 외부에 공개하지 않는 내부 네트워크와 컨테이너 간 포트 노출의 의미를 구분한다.
- 실제 이미지, 비밀값, 컨테이너 실행 없이 Compose 구성을 로컬에서 해석한다.

## 2. 왜 필요한가

AI API는 벡터 검색, 캐시, 관계형 데이터 저장소 같은 여러 의존 서비스를 함께 사용할 수 있습니다. 개발 환경에서 이들을 한 Compose 파일에 놓으면 어떤 서비스가 필요한지 이해하기 쉽습니다. 하지만 Compose가 서비스를 시작하는 순서가 각 서비스가 요청을 처리할 준비가 되었다는 보장은 아닙니다.

이 장의 파일은 의도적으로 실행 가능한 인프라 구성이 아닙니다. 모든 이미지가 `example.invalid` 자리표시자이고 PostgreSQL 초기화 값이나 인증 정보도 없습니다. 따라서 실수로 `up`을 실행해 실제 데이터나 네트워크를 만들지 않으면서도 토폴로지를 검토할 수 있습니다.

> [!WARNING]
> `docker/volume11/compose.dependencies.yaml`에 `docker compose up`, `pull`, `build`을 실행하지 마세요. 이 교재 slice의 검증 범위는 `docker compose ... config`를 통한 로컬 구문·구조 확인뿐입니다. 승인된 환경에서 실제 이미지를 선택할 때도 접속 문자열, 사용자 이름, 암호, 토큰을 교재 파일에 저장하지 않습니다.

## 3. 핵심 개념

- **Docker Compose:** 여러 컨테이너의 이미지, 환경 변수, 네트워크, 시작 관계를 한 YAML 파일에 선언하는 도구입니다.
- **서비스 토폴로지(topology):** 어떤 서비스가 어떤 경계 안에서 함께 동작하는지를 나타낸 구조입니다. 이 장에서는 API와 세 의존 서비스의 관계만 설명합니다.
- **`depends_on`:** Compose가 서비스를 시작하는 순서를 표현합니다. `service_started`는 프로세스 시작을 뜻할 뿐 질의 처리 가능 상태를 검증하지 않습니다.
- **내부 네트워크(internal network):** 이 예제에서 호스트로 노출되지 않고 Compose 서비스 사이의 통신 경계만 나타내는 네트워크입니다.
- **`expose`:** Compose 네트워크 안에서 사용할 수 있는 컨테이너 포트를 설명합니다. `ports`와 달리 호스트 포트를 게시하지 않습니다.
- **자리표시자 이미지(placeholder image):** `example.invalid/...`처럼 실제 레지스트리에서 가져올 수 없도록 만든 문서용 이미지 이름입니다.

## 4. 동작 구조

```text
                    ai-platform-internal (internal: true)
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ai-platform-api                                                 │
│     │ depends_on: service_started                                │
│     ├──────────────► qdrant  (example.invalid, expose 6333)     │
│     ├──────────────► redis   (example.invalid, expose 6379)     │
│     └──────────────► postgresql (example.invalid, expose 5432)  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

API readiness: 비밀 없는 학습용 이름 라벨을 오프라인 비교
실제 연결 검사: 이 파일에 없음
호스트 게시 포트: 없음
컨테이너 실행: 이 장의 검증 범위 밖
```

`depends_on`은 API보다 의존 서비스의 시작을 먼저 요청하는 선언입니다. 의존성이 준비되었는지는 [ConfigMap과 의존성 readiness 정책 분리](02-configmap-dependency-readiness.md)의 주입 가능한 검사 경계에서 별도로 다룹니다. 이 Compose 파일의 `AI_PLATFORM_READY_DEPENDENCIES`도 실제 상태를 탐지하지 않는 학습용 라벨입니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `docker/volume11/compose.dependencies.yaml` | 자리표시자 이미지로 만든 API·Qdrant·Redis·PostgreSQL 토폴로지 |
| `docker/volume11/compose.health.yaml` | API 단독 healthcheck Compose 예제 |
| `src/ai_platform/api/dependencies.py` | 네트워크 연결 없이 readiness 정책을 비교하는 코드 |
| `examples/volume11/dependency_readiness_demo.py` | 포트·Docker·클러스터를 사용하지 않는 정책 데모 |
| `tests/integration/test_volume11_health_artifacts.py` | Compose 토폴로지의 안전한 경계를 확인하는 테스트 |

Python과 `uv`가 필요합니다. 6.1의 구성 렌더링에는 Docker Compose CLI가 필요하지만 Docker Desktop을 시작하거나 컨테이너 엔진에 연결할 필요는 없습니다.

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
cd ~/projects/ai-platform-engineering-book
uv sync --all-groups
```

Windows에서 Git Bash 또는 Docker Desktop 터미널을 사용한다면 같은 저장소 루트에서 실행합니다. 이 장은 Docker 컨테이너를 만들지 않습니다.

## 6. 단계별 실습

### 6.1 Compose 구조를 실행 없이 렌더링

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
docker compose -f docker/volume11/compose.dependencies.yaml config --no-interpolate
```

`config`는 YAML을 합성하고 Compose 문법을 확인합니다. `--no-interpolate`는 환경 변수 치환도 하지 않도록 고정합니다. 출력에서 네 서비스, `ai-platform-internal`, 세 `example.invalid` 의존 이미지, 호스트 `ports` 항목이 없는지 확인합니다. 이 명령은 `up`, `pull`, `build`와 달리 컨테이너·이미지·네트워크·볼륨을 생성하지 않습니다.

### 6.2 API의 readiness 정책을 메모리에서 확인

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run python examples/volume11/dependency_readiness_demo.py
```

이 명령은 Qdrant, Redis, PostgreSQL이라는 논리 이름에 로컬 함수를 주입합니다. Docker 서비스 이름, 실제 주소, 포트, 계정, 인증 정보는 읽지 않습니다.

### 6.3 Volume 11 경계를 테스트

```bash
# 실행 위치: WSL Ubuntu 또는 Linux 터미널, 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 Compose 파일에 네 서비스와 내부 네트워크가 선언되어 있는지, 이미지가 모두 자리표시자인지, 인증 관련 환경 변수가 없는지 검사합니다. 컨테이너를 시작하거나 Kubernetes 클러스터에 적용하거나 외부 서비스에 연결하지 않습니다.

## 7. 코드와 Compose 설명

`api` 서비스에는 이미 배운 `AI_PLATFORM_READY`, `AI_PLATFORM_REQUIRED_DEPENDENCIES`, `AI_PLATFORM_READY_DEPENDENCIES`만 들어 있습니다. 이 값은 ConfigMap 스타일의 비밀 없는 교육용 정책입니다. 연결 주소나 인증 값은 의도적으로 없습니다.

Qdrant, Redis, PostgreSQL은 각각 `expose`로 컨테이너 내부 포트만 설명합니다. `ports`를 쓰지 않았으므로 호스트 포트를 열지 않습니다. 세 이미지 모두 `example.invalid`를 사용하므로 이 파일은 실제 서비스를 실행할 준비가 되어 있지 않습니다.

`ai-platform-internal`의 `internal: true`는 학습용 서비스 경계를 표현합니다. 실제 네트워크 격리 수준, NetworkPolicy, 방화벽 규칙은 Docker Compose 선언 하나로 충분하지 않습니다. Kubernetes에서의 경계는 이후 Manifest 장에서 별도로 검토해야 합니다.

## 8. 정상 실행 결과

6.1의 출력에는 다음 항목이 포함되어야 합니다.

```text
services:
  api:
  qdrant:
  redis:
  postgresql:
networks:
  ai-platform-internal:
    internal: true
```

각 서비스의 이미지에는 `example.invalid/` 접두사가 보입니다. 호스트에 게시할 `ports:` 항목은 출력되지 않아야 합니다. 6.2에는 다음 결과가 포함됩니다.

```text
all-required-dependencies-ready True
redis-unavailable False
```

6.3은 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다.

## 9. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `docker compose`를 찾을 수 없음 | Docker Compose CLI가 설치되지 않았을 수 있습니다. | Python 데모와 테스트를 먼저 실행하고, Docker Desktop 또는 Compose CLI 설치 후 6.1만 다시 실행합니다. |
| `config`에서 YAML 오류 | 들여쓰기 또는 Compose 키 이름이 바뀌었을 수 있습니다. | 원본 파일의 서비스·네트워크 수준 들여쓰기를 복원하고 `config --no-interpolate`로 다시 확인합니다. |
| `up`에서 이미지 pull 오류 | `example.invalid`는 일부러 가져올 수 없는 자리표시자입니다. | 예상된 보호 동작입니다. `up`을 재시도하거나 실제 이미지 이름을 이 교재 파일에 넣지 마세요. |
| API가 준비되지 않음 | readiness 라벨의 required 목록과 ready 목록이 다를 수 있습니다. | [이전 장](02-configmap-dependency-readiness.md)의 비밀 없는 이름 라벨을 비교합니다. 실제 연결 정보를 추가하지 마세요. |
| 호스트에서 의존 서비스에 연결할 수 없음 | 이 파일은 `ports`를 게시하지 않고 실행도 하지 않습니다. | 이 slice에서는 예상된 결과입니다. 승인된 별도 운영 절차에서 노출 요구사항과 보안 정책을 검토합니다. |

## 10. 응용 실습

1. 세 의존 서비스 중 API 기능에 필수인 것과 선택적인 것을 표로 분류합니다. 실제 호스트·계정·접속 문자열은 쓰지 않습니다.
2. `service_started`만으로 충분하지 않은 이유를 각 서비스의 초기화 조건과 연결해 설명합니다.
3. 새 선택 의존 서비스를 추가한다고 가정하고, 내부 네트워크 참여 여부, readiness 영향, 관찰 지표를 설계합니다. Compose 파일을 실행하지 않습니다.

## 11. 실무 적용

실제 Compose 통합 환경에서는 이미지 버전 고정, 이미지 공급망 검토, 최소 권한 실행, 저장소 수명 주기, 데이터 백업, 제한된 네트워크 접근, 서비스별 healthcheck를 검토합니다. PostgreSQL 같은 상태 저장 서비스는 특히 초기화·권한·복구 정책을 승인된 Secret 및 운영 절차와 함께 다뤄야 합니다.

Compose의 `depends_on`을 가용성 보장으로 해석하면 안 됩니다. API는 짧은 Timeout을 사용한 제한된 readiness 검사, 실패 분류, 관찰 지표를 갖춰야 합니다. liveness에 외부 의존성 실패를 섞지 않는 원칙은 [Health Probe 장](01-health-probes.md)과 같습니다.

## 12. 과제

- **기본:** `expose`와 `ports`의 차이를 한 문장씩 설명하고, 이 파일이 호스트 포트를 열지 않는 이유를 작성합니다.
- **응용:** Qdrant, Redis, PostgreSQL 각각에 대해 시작됨과 준비됨을 구분하는 확인 기준을 제안합니다. 인증 정보는 적지 않습니다.
- **심화:** API가 일부 의존성 없이 제한 기능을 제공할 수 있다면 필수·선택 의존성 정책, readiness, 사용자 오류 응답, 경보 기준을 설계합니다.

## 13. 완료 체크리스트

- [ ] API, Qdrant, Redis, PostgreSQL의 논리적 역할을 구분할 수 있다.
- [ ] `depends_on`의 시작 순서와 readiness의 준비 판단이 다름을 설명할 수 있다.
- [ ] `expose`가 호스트 포트를 게시하지 않음을 확인했다.
- [ ] 모든 서비스 이미지가 `example.invalid` 자리표시자임을 확인했다.
- [ ] `docker compose ... config --no-interpolate`로만 구조를 해석했다.
- [ ] `uv run python examples/volume11/dependency_readiness_demo.py`를 실행했다.
- [ ] Volume 11 테스트가 통과했다.
- [ ] 컨테이너를 시작하거나 클러스터에 적용하거나 실제 비밀·접속 정보를 저장하지 않았다.

## 14. 핵심 정리

Compose 토폴로지는 여러 AI Platform 구성 요소의 관계를 보여 주지만, 시작 순서만으로 준비 상태를 보장하지 않습니다. 이 장은 API, Qdrant, Redis, PostgreSQL을 내부 네트워크에 배치한 형태를 `example.invalid` 이미지로만 선언했습니다. 따라서 실제 컨테이너나 데이터를 만들지 않고도 서비스 경계와 readiness 책임을 검토할 수 있습니다. 다음 Kubernetes 객체 실습에서는 이 경계를 Ingress, 저장소, 배치 작업, 확장 정책과 연결합니다.
