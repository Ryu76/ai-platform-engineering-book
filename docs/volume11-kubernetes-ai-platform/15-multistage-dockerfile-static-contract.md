# Multi-stage Dockerfile: source stage와 runtime stage의 정적 계약

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Multi-stage build에서 source stage와 runtime stage가 맡는 책임을 구분한다.
- runtime image에 필요한 파일만 `COPY --from`으로 전달하는 Dockerfile 계약을 읽는다.
- non-root 실행, runtime 환경 변수, health endpoint가 서로 다른 보안·운영 질문에 답한다는 점을 설명한다.
- Dockerfile text 또는 Compose config 검증과 실제 image build·container 실행을 혼동하지 않는다.

## 2. 왜 필요한가

컨테이너 이미지는 빌드 도구, 테스트 산출물, 개발용 파일을 모두 runtime에 넣기 쉽습니다. 필요한 파일을 별도 stage에 모은 뒤 runtime stage로 명시적으로 복사하면, runtime에 전달할 경로를 검토할 수 있습니다.

이 Volume의 `Dockerfile`은 source file만 별도 stage에서 준비하고 runtime stage로 전달하는 **학습용 정적 계약**입니다. 의존성 설치, package build, image registry publish는 포함하지 않습니다. 따라서 이 예제는 multi-stage syntax와 파일 경계를 가르치지만, image 크기·취약점·SBOM·실행 성공을 증명하지는 않습니다.

> [!WARNING]
> `docker compose config`와 repository test는 Docker daemon으로 image를 build하거나 container를 시작하지 않습니다. `docker build`, `docker compose up`, image pull/push, registry login은 이 local-only 실습 범위 밖입니다. 실제 image build·실행 결과를 확인하지 않았으므로 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 핵심 개념

| 개념 | 이 예제의 역할 | 이 예제가 보장하지 않는 것 |
|---|---|---|
| source stage | `src/ai_platform`을 `/build/ai_platform`에 복사하는 중간 파일 경계 | source가 compile되었거나 테스트를 통과했다는 사실 |
| runtime stage | 새 `python:3.12-slim` stage에서 API source만 받는 실행 후보 | image가 build/pull/run된 사실 |
| `COPY --from=source` | source stage의 지정 경로만 runtime stage로 전달 | source tree에 비밀값이 없다는 전체 보안 판정 |
| non-root user | runtime command가 `appuser`로 실행되도록 선언 | host/cluster privilege, filesystem write, admission policy |
| `PYTHONPATH=/app/src` | 복사한 Python package를 module command가 찾을 경로로 선언 | module import 또는 HTTP listener가 실제로 동작한다는 사실 |

## 4. 동작 구조

```text
build context (local source only)
        |
        v
+---------------------------+
| source stage              |
| /build/ai_platform        |
+---------------------------+
        | COPY --from=source
        v
+---------------------------+
| runtime stage             |
| /app/src/ai_platform      |
| USER appuser              |
| CMD python -m ...server   |
+---------------------------+
```

두 stage는 같은 base image tag를 사용하지만 파일시스템은 별개입니다. runtime stage는 `COPY --from=source`로 지정한 package directory만 받습니다. 이 diagram은 Docker build가 성공했다는 실행 기록이 아니라, Dockerfile이 표현하는 파일 흐름입니다.

## 5. 실습 환경

- Dockerfile: `docker/volume11/Dockerfile`
- Compose 구문 확인 대상: `docker/volume11/compose.health.yaml`
- 정적 contract review: `src/ai_platform/api/operations_review.py`
- 테스트: `tests/integration/test_volume11_mini_project.py`, `tests/integration/test_volume11_health_artifacts.py`

모든 예제는 저장소에 있는 source와 `example.invalid` placeholder만 사용합니다. API key, registry credential, Secret 값, live endpoint, cluster address를 추가하지 않습니다.

## 6. 단계별 실습

### 6.1 Dockerfile의 stage 경계 읽기

실행 위치는 **저장소 루트**입니다.

```bash
uv run python examples/volume11/local_operations_review_demo.py
```

이 명령은 in-memory health probe와 local file read만 수행합니다. 출력의 `artifact_checks.dockerfile_is_multistage_and_nonroot`가 `true`이면 다음 문자열 계약을 확인했다는 뜻입니다.

1. `AS source`와 `AS runtime`이라는 두 `FROM` stage가 있다.
2. runtime stage가 `COPY --from=source`로 package directory를 받는다.
3. runtime command 전에 `USER appuser`가 선언되어 있다.

정상 결과는 JSON의 해당 check가 `true`인 것입니다. 이 결과는 Docker daemon, network, image layer 또는 container 상태를 포함하지 않습니다.

### 6.2 Compose config를 parse-only로 확인하기

실행 위치는 **저장소 루트의 Docker CLI 환경**입니다.

```bash
docker compose -f docker/volume11/compose.health.yaml config --no-interpolate
```

이 명령은 Compose file을 local configuration으로 해석합니다. `build.context`, `build.dockerfile`, `AI_PLATFORM_READY`, `healthcheck`가 출력에 나타나는지 확인합니다. `up`, `pull`, `build`, `push`를 붙이지 않습니다.

정상 결과는 Compose 설정 text가 출력되고 새 container·network·volume이 생기지 않는 것입니다. Docker daemon 정책 또는 CLI 버전에 따라 config parsing 자체가 실패하면 Dockerfile의 실행 가능성을 추정하지 말고 CLI version과 Compose syntax를 별도 확인합니다.

### 6.3 Volume 11 정적 contract를 테스트하기

실행 위치는 **저장소 루트**입니다.

```bash
uv run pytest tests/integration/test_volume11_health_artifacts.py tests/integration/test_volume11_mini_project.py -q
```

이 테스트는 multi-stage/non-root 문자열 계약, placeholder image, probe 분리, local-only report를 확인합니다. image를 만들거나 registry와 통신하지 않습니다.

## 7. 코드 설명

`Dockerfile`의 source stage는 project 전체가 아니라 `src/ai_platform`만 `/build/ai_platform`에 복사합니다. runtime stage는 독립된 base에서 `PYTHONPATH=/app/src`를 선언하고, numeric UID `10001`을 가진 `appuser`를 만든 뒤 source stage의 package directory를 `/app/src/ai_platform`로 복사합니다.

`COPY --chown=10001:10001`은 runtime package 파일을 non-root user가 읽을 수 있는 ownership으로 둡니다. `readOnlyRootFilesystem: true` Kubernetes contract와 함께 읽을 때에도, application이 runtime에 쓰기 가능한 임시 경로·cache·upload storage를 필요로 하는지 별도 설계가 필요합니다. 이 Dockerfile이 그런 경로를 제공하지는 않습니다.

## 8. 정상 실행 결과

local review JSON에는 아래처럼 Dockerfile 계약만 나타납니다.

```json
{"artifact_checks":{"dockerfile_is_multistage_and_nonroot":true},"scope":"local-only"}
```

실제 출력에는 다른 artifact check도 함께 포함됩니다. `true`는 local source text가 예상된 stage·copy·user contract를 포함한다는 뜻입니다. image digest, layer size, package vulnerability, process startup, `/livez` HTTP response는 이 결과에 포함되지 않습니다.

## 9. 오류 해결

| 증상 | 원인 후보 | 확인 방법 | 해결 방향 |
|---|---|---|---|
| Dockerfile contract check가 `false` | stage name, `COPY --from`, 또는 `USER`가 변경됨 | `docker/volume11/Dockerfile`의 stage와 copy source를 읽는다 | source/runtime 경계를 의도적으로 변경했다면 test·문서·review contract를 함께 갱신한다 |
| `docker compose ... config`가 실패 | Docker Compose CLI가 없거나 syntax를 지원하지 않음 | `docker compose version`으로 local CLI 정보를 확인한다 | Compose CLI를 설치·업데이트한 뒤 parse-only command를 다시 실행한다. `up`으로 우회하지 않는다 |
| non-root인데 write 오류가 예상됨 | runtime filesystem과 application write 요구가 맞지 않음 | cache, upload, temporary file 요구를 설계 검토에서 분리한다 | 승인된 환경에서 writable volume/path와 security policy를 설계·검증한다. 이 예제에 host path나 credential을 넣지 않는다 |
| build가 될 것이라고 단정하고 싶음 | text contract와 execution evidence를 혼동함 | `not_verified`에 `image build`가 남아 있는지 확인한다 | 승인된 별도 환경에서 build/provenance/scan/run evidence를 확보할 때까지 `not verified`를 유지한다 |

## 10. 응용 실습

다음은 실제 실행하지 않는 설계 과제입니다.

1. source stage에 어떤 generated artifact를 전달할지 표로 정의하고, runtime에 필요하지 않은 경로를 구분합니다.
2. runtime user가 써야 하는 cache 또는 temporary directory가 있는지 application별로 찾고, owner·retention·data sensitivity를 기록합니다.
3. approved build 환경에서 확인할 provenance, digest, scan, license, startup, health evidence를 각각 다른 checklist 항목으로 작성합니다.

과제 답안에는 실제 registry hostname, image digest, account, token, Secret 값을 넣지 않고 `placeholder-*` 예시만 사용합니다.

## 11. 실무 적용

Multi-stage Dockerfile은 supply-chain 안전성의 한 부분일 뿐입니다. 실제 운영에서는 pinned base image, dependency lock, reproducible build, SBOM, signature/provenance, vulnerability review, runtime security policy, resource limit, health semantics를 함께 검토해야 합니다.

또한 image가 build된 사실과 deployment가 안전한 사실은 다릅니다. admission, service account/RBAC, Secret injection, network policy, image pull policy, rollout safety, data migration, rollback side effect는 Kubernetes 승인 절차에서 별도 evidence를 요구합니다.

## 12. 과제

- **기본:** source stage와 runtime stage가 전달하는 경로를 ASCII diagram으로 다시 그립니다.
- **응용:** API가 temporary file을 필요로 한다고 가정하고, runtime filesystem·volume·data retention에 필요한 승인 질문을 작성합니다.
- **심화:** build, scan, sign, publish, deploy를 별도 evidence 단계로 나누고, 어느 단계도 다른 단계의 success claim을 대체하지 않는 이유를 설명합니다.

## 13. 완료 체크리스트

- [ ] source stage와 runtime stage의 파일 경계를 설명할 수 있다.
- [ ] `COPY --from`이 runtime image execution evidence가 아님을 설명할 수 있다.
- [ ] non-root user와 read-only filesystem의 책임을 구분했다.
- [ ] Compose config와 `docker compose up`의 side effect 차이를 설명할 수 있다.
- [ ] 실제 credential, registry, image digest, Secret, cluster 주소를 예제에 넣지 않았다.
- [ ] `image build`와 container execution이 현재 `not verified`임을 유지했다.
- [ ] local test 성공을 PRD Volume DoD 완료로 선언하지 않았다.

## 14. 핵심 정리

이 Volume의 multi-stage Dockerfile은 source-to-runtime 파일 전달과 non-root runtime 선언을 정적으로 학습하는 artifact입니다. local review와 Compose config는 이 contract를 읽을 수 있지만 image build, scan, provenance, container startup, deployment를 확인하지 않습니다. artifact check의 `true`와 운영 evidence의 `not verified`를 함께 유지하는 것이 안전한 컨테이너 운영 학습의 핵심입니다.
