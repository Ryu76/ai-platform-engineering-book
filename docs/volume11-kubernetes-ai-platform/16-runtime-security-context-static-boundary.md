# Runtime SecurityContext: 선언과 강제의 정적 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- Pod-level과 container-level `securityContext`가 표현하는 책임을 구분한다.
- 예제 Deployment의 seccomp, non-root, privilege escalation, Linux capability, read-only filesystem 선언을 읽는다.
- manifest text contract와 admission, kubelet, container runtime의 실제 강제를 혼동하지 않는다.
- 실행 증거 없이 `VOLUME11_COMPLETE=true`를 설정하지 않는 이유를 설명한다.

## 2. 이 예제의 범위

`k8s/volume11/deployment.yaml`은 `example.invalid/ai-platform-api:0.1.0`만 사용하는 교육용 Manifest입니다. `kubectl kustomize`와 local review는 파일을 렌더링하거나 읽을 뿐 Pod를 만들지 않습니다. 실제 Secret, ServiceAccount, registry credential, cluster address, host path를 추가하지 않습니다.

> [!WARNING]
> `securityContext` 선언은 admission 통과, kubelet 적용, seccomp profile 로드, container execution 또는 filesystem write 실패를 증명하지 않습니다. 이 작업에서는 cluster 연결과 deployment가 금지되어 있으므로 실제 강제 결과는 `not verified`입니다. 따라서 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.

## 3. 정적 계약 읽기

| 위치 | 선언 | local text에서 읽는 의도 | 이 예제가 보장하지 않는 것 |
|---|---|---|---|
| Pod `securityContext` | `seccompProfile.type: RuntimeDefault` | runtime-default seccomp profile 사용 의도 | 노드 runtime이 profile을 적용했다는 결과 |
| container `securityContext` | `runAsNonRoot: true`, `runAsUser: 10001` | non-root UID로 실행하도록 선언 | image의 user metadata, 실제 process UID, admission 결과 |
| container `securityContext` | `allowPrivilegeEscalation: false` | 실행 중 privilege gain을 허용하지 않는 의도 | kernel, runtime, workload 전체의 privilege proof |
| container `securityContext` | `capabilities.drop: ["ALL"]` | 기본 Linux capability를 추가하지 않는 최소 권한 경계 | binary가 필요한 capability 없이 동작한다는 결과 |
| container `securityContext` | `readOnlyRootFilesystem: true` | root filesystem write를 허용하지 않는 의도 | cache, temp file, upload path가 실제로 불필요하다는 결과 |

이 값은 방어 심층화의 일부입니다. NetworkPolicy, RBAC, image provenance, vulnerability review, Pod Security 또는 조직 admission policy를 대체하지 않습니다.

## 4. local-only 확인

실행 위치는 **저장소 루트**입니다.

```bash
uv run python examples/volume11/local_operations_review_demo.py
uv run pytest tests/integration/test_volume11_health_artifacts.py tests/integration/test_volume11_mini_project.py tests/integration/test_volume11_runtime_security.py -q
kubectl kustomize k8s/volume11
```

첫 명령은 local file read와 in-memory WSGI probe만 수행합니다. JSON의 `artifact_checks.deployment_declares_restricted_runtime_security`가 `true`이면 정해진 여섯 security declaration이 source text에 있다는 뜻입니다. 두 번째 명령은 같은 static contract와 `privileged: true`, `hostNetwork: true`, `hostPath:` 부재를 확인합니다. 마지막 명령은 local Kustomize render이며 Kubernetes API에 연결하거나 resource를 생성하지 않습니다.

## 5. 선언과 실행 증거의 구분

다음 항목은 이번 slice에서 확인하지 않습니다.

- 실제 image build, image pull, container execution과 process UID
- cluster admission 또는 Pod Security 정책의 accept/reject 결과
- seccomp syscall 차단, Linux capability 계산, privilege escalation 방지의 runtime 결과
- read-only filesystem에서 application startup, Python bytecode/cache, temporary file 요구
- ServiceAccount/RBAC, NetworkPolicy, Secret injection, node isolation, rollout 또는 deployment

특히 `readOnlyRootFilesystem: true`와 Dockerfile의 `PYTHONDONTWRITEBYTECODE=1`은 서로 다른 선언입니다. 전자는 Kubernetes container filesystem 정책이고 후자는 Python runtime의 bytecode write 동작입니다. 둘 다 있더라도 container startup이 성공했다는 증거는 아닙니다.

## 6. 검토 질문

1. application이 temporary file, model cache, upload, crash dump를 써야 하는가? 그렇다면 승인된 writable path의 owner, quota, retention, data sensitivity를 별도 설계한다.
2. UID `10001`이 image file ownership과 volume permission에 맞는가? build/runtime 검증 환경에서 별도 evidence를 확보한다.
3. 필요한 Linux capability가 있는가? 필요한 경우 최소 capability와 이유를 승인 기록으로 남기며 무조건 broad privilege를 추가하지 않는다.
4. namespace의 admission과 organization policy가 이 Manifest를 허용하는가? cluster policy 결과는 local YAML inspection으로 추정하지 않는다.

예제 답안에는 실제 cluster name, node 정보, registry, credential, user data를 넣지 않고 `placeholder-*`만 사용합니다.

## 7. 오류 해결 경계

| 증상 | local 확인 | 안전한 다음 단계 |
|---|---|---|
| local security check가 `false` | `deployment.yaml`의 exact declaration과 review key를 함께 읽는다 | 의도된 Manifest 변경이면 test, review, 문서를 함께 갱신한다 |
| 실제 workload가 filesystem write 오류를 보일 것으로 예상 | code의 cache/temp/write 요구를 분리해 검토한다 | 승인된 환경에서 최소 writable path와 retention policy를 검증한다; host path를 예제에 추가하지 않는다 |
| admission 거부가 예상됨 | 이 Volume의 local render는 admission을 호출하지 않음을 기록한다 | 승인된 cluster policy owner와 별도 검증한다; `kubectl apply`로 우회하지 않는다 |
| capability가 필요해 보임 | binary와 syscall 요구를 evidence로 분리한다 | broad `privileged` 대신 최소 capability를 security review에서 승인받는다 |

## 8. 완료 체크리스트

- [ ] Pod-level seccomp와 container-level securityContext의 범위를 구분했다.
- [ ] non-root UID, privilege escalation, dropped capabilities, read-only filesystem 선언을 읽었다.
- [ ] `deployment_declares_restricted_runtime_security`의 `true`가 text contract일 뿐임을 설명할 수 있다.
- [ ] actual container execution, admission, seccomp enforcement가 `not verified`임을 유지했다.
- [ ] 실제 Secret, credential, host path, cluster 연결 또는 deployment를 추가하지 않았다.
- [ ] local test 성공을 PRD Volume DoD 완료 선언으로 바꾸지 않았다.

## 9. 핵심 정리

이 Deployment는 안전한 기본값을 **선언**하는 placeholder artifact입니다. local review, pytest, Kustomize render는 declaration을 재현 가능하게 읽지만 runtime security enforcement를 증명하지 않습니다. admission과 container execution evidence가 없는 동안에는 `not verified`를 유지하고 `VOLUME11_COMPLETE=true`를 설정하지 않습니다.
