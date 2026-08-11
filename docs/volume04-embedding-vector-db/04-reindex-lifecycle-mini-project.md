# 04. 삭제와 재색인 미니 프로젝트

## 1. 학습 목표

이 장을 마치면 문서가 변경되거나 폐기될 때 기존 point를 삭제하고, 같은 안정적인 ID로 새 vector와 metadata를 다시 저장하는 이유를 설명할 수 있습니다. 또한 삭제 전후와 재색인 뒤의 검색 결과를 결정적 local mock으로 검증할 수 있습니다.

## 2. 왜 필요한가

벡터 데이터베이스는 한 번 저장하면 끝나는 파일 보관함이 아닙니다. 문서의 오류가 수정되거나 정책이 바뀌면 이전 vector는 오래된 내용을 계속 검색 결과로 반환할 수 있습니다. 새 point를 다른 ID로 계속 추가하면 같은 문서의 여러 버전이 경쟁하고, 사용자는 어느 결과가 최신인지 알기 어렵습니다.

이 미니 프로젝트는 `retry-guide`를 삭제한 뒤 version 2로 재색인합니다. 검색 대상에서 폐기된 point가 사라졌는지와 같은 ID가 새 metadata로 복구되는지를 함께 확인합니다.

> [!WARNING]
> 이 실습의 `InMemoryVectorStore`와 해시 기반 embedding은 Qdrant 또는 운영용 임베딩 모델의 대체품이 아닙니다. 네트워크 없이 lifecycle 계약을 재현하는 local mock입니다.

## 3. 핵심 개념

- **stale vector(오래된 vector)**: 원문이 바뀌었는데 과거 텍스트로 계산되어 남아 있는 vector입니다.
- **삭제(delete)**: 더 이상 검색되면 안 되는 point를 collection에서 제거합니다.
- **재색인(reindex)**: 최신 원문을 다시 embedding하고 vector와 payload를 저장하는 작업입니다.
- **stable point ID**: 문서의 정체성을 나타내는 변하지 않는 ID입니다. 이 예제에서는 `retry-guide`입니다.
- **upsert**: 같은 ID가 있으면 교체하고 없으면 생성하는 저장 동작입니다.
- **version metadata**: 검색 결과가 어느 문서 버전인지 식별하는 payload입니다.

## 4. 동작 구조

```text
version 1 문서 ─> embedding ─> retry-guide (version=1) ─> 검색 결과
                                      │
                                      ├─> delete(retry-guide)
                                      │        │
                                      │        └─> stale point가 검색에서 제거됨
                                      ▼
version 2 문서 ─> embedding ─> upsert(retry-guide, version=2) ─> 최신 검색 결과
```

삭제와 재색인의 중간 상태를 분리해서 확인하면, 삭제가 누락되었는지, 최신 metadata가 반영되지 않았는지, 검색 filter가 잘못되었는지를 각각 찾을 수 있습니다.

## 5. 실습 환경

모든 명령은 **저장소 루트의 Windows PowerShell, Git Bash 또는 WSL 터미널**에서 실행합니다. Python 3.12 이상과 `uv`가 필요합니다.

- 실행 코드: `src/ai_platform/embeddings/reindex_lifecycle.py`
- 실행 예제: `examples/volume04/reindex_lifecycle.py`
- 테스트: `tests/unit/test_volume04_reindex_lifecycle.py`

이 slice는 네트워크, API 키, 외부 모델 다운로드, Docker, Qdrant 서버를 사용하지 않습니다. 환경이 없으면 저장소 루트에서 `uv sync --group dev`를 실행한 뒤 아래 명령을 다시 실행합니다.

## 6. 단계별 실습

1. `run_reindex_lifecycle`은 version 1의 `retry-guide`와 관련 없는 두 문서를 local collection에 저장합니다.
2. version 1 질의로 검색하고 안정적인 ID 기준 top-1 지표를 계산합니다.
3. `delete("platform_docs", ["retry-guide"])`로 오래된 point 하나를 제거합니다.
4. 삭제 뒤 같은 질의를 다시 검색해 `retry-guide`가 결과에 없는지 확인합니다.
5. `Python API 오류 처리와 지수 백오프 재시도 전략`을 version 2 원문으로 embedding합니다.
6. 같은 `retry-guide` ID와 `version=2` payload로 upsert합니다.
7. `metadata_filter={"version": 2}`로 최신 point만 검색하고 top-1 회복을 평가합니다.

```bash
# 실행 위치: 저장소 루트
uv run python examples/volume04/reindex_lifecycle.py
uv run pytest tests/unit/test_volume04_reindex_lifecycle.py -q
```

첫 명령은 lifecycle 상태를 출력합니다. 두 번째 명령은 stale ID 제거, 재색인된 version, 검색 품질 회복, 반복 실행 재현성을 검증합니다.

## 7. 코드 설명

`run_reindex_lifecycle`은 예제와 테스트가 공유하는 단일 workflow입니다. `ReindexLifecycleReport`는 각 단계의 순위 ID, 삭제 수, collection 크기, version, top-1 지표를 불변 값으로 반환합니다. 보고서를 직접 만들 때도 순위는 caller가 바꿀 수 없는 중복 없는 `tuple[str, ...]`, 지표는 `RetrievalMetrics`, 삭제 수·크기는 bool이 아닌 0 이상의 정수, version은 양의 정수여야 합니다. 따라서 출력 문자열만 검사하지 않고 lifecycle의 상태 전이를 단위 테스트할 수 있습니다.

초기 검색과 재색인 검색은 모두 `evaluate_ranking(..., {"retry-guide"}, k=1)`로 평가합니다. 삭제 단계에서는 정답 ID가 결과에 없어야 하므로 순위 목록에서 `retry-guide`의 부재를 직접 확인합니다. 실제 no-answer 정책은 검색 점수뿐 아니라 문서 최신성, 출처, ACL을 함께 검토해야 합니다.

## 8. 정상 실행 결과

고정 입력에서 예제는 다음과 같은 결과를 출력합니다.

```text
initial_ranked_ids=retry-guide,docker-guide,vector-guide
deleted_count=1; collection_size_after_delete=2
ranked_ids_after_delete=docker-guide,vector-guide
reindexed_ranked_ids=retry-guide
reindexed_version=2; collection_size=3; top_1_recovered=True
```

첫 줄의 `retry-guide`는 version 1 검색이 성공했음을 뜻합니다. 삭제 뒤 세 번째 줄에는 이 ID가 없습니다. 마지막 두 줄은 version 2로 같은 ID를 다시 색인했고 collection 크기가 원래의 3으로 회복되었음을 보여 줍니다.

## 9. 오류 해결

| 증상 | 가능한 원인 | 확인 및 해결 |
|---|---|---|
| `retry-guide`가 삭제 뒤에도 보임 | 삭제 대상 ID가 다르거나 검색을 삭제 전에 수행함 | stable ID를 확인하고 `delete` 뒤에 새 `search`를 실행합니다. |
| collection 크기가 4가 됨 | 새 버전에 다른 ID를 사용함 | 문서 정체성에는 같은 ID를 사용하고 version은 payload로 관리합니다. |
| `reindexed_ranked_ids`가 비어 있음 | `version=2` filter와 payload가 맞지 않음 | upsert payload와 filter의 key/value를 함께 점검합니다. |
| `ReindexLifecycleError` | 수동으로 만든 보고서에 list 순위, 중복 ID, 잘못된 metric·count·version을 넣음 | 순위는 중복 없는 tuple로, 지표는 `RetrievalMetrics`로, count는 0 이상의 정수로, version은 양의 정수로 만듭니다. |
| `VectorDimensionError` | document와 query가 다른 차원 또는 다른 모델 공간을 사용함 | collection vector size와 embedding model dimensions를 동일하게 맞춥니다. |
| 결과 순서가 다름 | 운영 DB의 동점·index 동작이 local mock과 다름 | 운영 이행 전 stable ID, filter, score 정책으로 별도 통합 테스트를 작성합니다. |

## 10. 응용 실습

문서 두 개를 version 2로 바꾸고, 한 batch의 vector가 잘못되었을 때 어느 문서도 부분 저장되지 않는지 확인합니다. 그다음 `state="archived"` payload를 추가하고 published 문서만 검색하도록 filter를 확장합니다. 이 local mock에서는 scalar equality filter만 제공하므로 복잡한 운영 filter는 DB별 계약으로 별도 검증해야 합니다.

## 11. 실무 적용

운영에서는 원문의 content hash, source URI, 문서 버전, 색인 시각, embedding model 이름과 dimension을 metadata 또는 별도 catalog에 기록합니다. 수집 작업은 삭제 목록과 재색인 목록을 분리해 재시도 가능하게 만들고, batch별 성공·실패 수를 관측합니다. ACL과 테넌트 filter는 vector search **전에** 후보를 제한해야 하며, 삭제된 문서 원문이나 민감한 payload를 불필요하게 로그에 남기면 안 됩니다.

Qdrant 같은 실제 DB에 이행할 때는 delete와 upsert의 실패 재시도, collection alias 전환, index 준비 상태, payload index, backup과 rollback을 DB 문서와 통합 테스트로 검증합니다. 이 slice에서는 외부 서비스를 실행하지 않습니다.

## 12. 과제

- **기본**: version 1과 version 2의 `retry-guide` payload를 비교하는 테스트를 추가합니다.
- **응용**: 두 ID를 삭제할 때 실제 삭제 수와 남은 collection 크기를 검증합니다.
- **심화**: source URI와 content hash가 바뀐 문서만 재색인할 수 있도록 입력 manifest의 계약을 설계하고, 실패한 batch의 재시도 정책을 문서화합니다.

## 13. 완료 체크리스트

- [x] 삭제하지 않은 오래된 vector가 만드는 문제를 설명할 수 있다.
- [x] stable point ID와 version metadata의 역할을 구분했다.
- [x] 결정적 local mock으로 삭제 뒤 stale ID가 사라짐을 실행했다.
- [x] 같은 ID를 version 2 vector와 payload로 재색인했다.
- [x] 삭제 수, collection 크기, 최신 metadata filter, 검색 회복을 테스트했다.
- [x] 외부 API, 비밀값, Docker, 외부 모델 다운로드 없이 실행했다.
- [ ] 운영 DB의 삭제·재색인 장애 복구와 alias 전환을 통합 환경에서 검증한다.

## 14. 핵심 정리

문서의 ID는 정체성을, vector는 현재 텍스트의 표현을, payload의 version은 색인된 상태를 나타냅니다. 삭제와 재색인을 분리해 검증하면 stale vector가 검색 결과에 남는 문제를 조기에 발견할 수 있습니다. 다음 권의 RAG는 이 lifecycle 경계를 이용해 최신 chunk만 검색 근거로 사용할 수 있습니다.
