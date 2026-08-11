# 06. 결정론적 Mock script 고정

## 학습 목표

오프라인 Mock은 테스트 편의를 위한 fallback 생성기가 아니라, 호출 순서와 최대 호출 수를 드러내는 **고정된 유한 script**여야 합니다. 이 장은 `DeterministicMockAgent`, `DeterministicMockCoordinator`, `DeterministicMockWorker`, `DeterministicMockConflictAgent`가 응답·계획·제안 script를 구성 단계에서 immutable tuple로만 받게 하여, workflow 실행 중 외부 코드가 list를 변경하거나 응답을 추가할 수 없게 하는 방법을 다룹니다.

## 안전 경계

- 모든 결정론적 Mock의 script는 비어 있지 않은 `tuple`이어야 한다. list 등 mutable sequence는 `WorkflowConfigurationError`로 거절된다.
- 역할 이름은 비어 있지 않은 문자열이어야 한다. 문자열이 아닌 값은 `AttributeError`가 아니라 구성 오류로 fail-closed한다.
- tuple은 호출 순서와 script 길이를 실행 전에 고정한다. script가 소진되면 Mock은 fallback, 재생성, 추가 호출 없이 `AgentProtocolError`를 낸다.
- 이 규칙은 script **컨테이너**의 불변성을 보장한다. 각 항목의 `AgentResponse`, `WorkerResponse`, `DelegationPlan`, `ConflictProposal` 형식과 내용은 기존 workflow의 실행 시점 protocol 검증이 담당한다.
- 사람 승인은 그대로 별도 경계다. immutable Mock도 `PENDING`에서 QA·Worker·DevOps를 실행할 수 없고, 영향 있는 다음 단계에는 명시적 `APPROVED`가 필요하다.

## 왜 구성 단계에서 중단하는가

가변 list를 script로 허용하면 이미 구성된 테스트 경계에 응답을 append하거나 순서를 바꿀 수 있습니다. 그러면 재작업/재시도/충돌 round의 실제 상한이 실행 중 달라져, "결정론적"이라는 이름과 audit trail이 가리키는 호출 수가 일치하지 않습니다. 생성자에서 tuple만 허용하면 실행 전 호출 예산이 고정되고, script가 부족한 경우도 눈에 보이는 fail-closed 오류로 남습니다.

## 오프라인 검증

저장소 루트에서 다음을 실행합니다.

```bash
uv run pytest tests/volume07/test_immutable_mock_scripts.py -q
```

전체 Volume 07 계약 검증은 다음과 같습니다.

```bash
uv run pytest tests/volume07 -q
```

두 명령 모두 네트워크, live API, secret, 도구 실행, 배포를 사용하지 않습니다.

## 핵심 정리

안전한 다중 Agent 실습은 (1) immutable deterministic Mock script로 호출 예산을 고정하고, (2) bounded loop와 protocol 검증으로 잘못된 출력을 중단하고, (3) 사람 승인 후에만 다음 영향을 주는 단계를 실행합니다. Mock script 자체가 가변이면 첫 번째 보장이 무너지므로 구성 단계에서 거절해야 합니다.
