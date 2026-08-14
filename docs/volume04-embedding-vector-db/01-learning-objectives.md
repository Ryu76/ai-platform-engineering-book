# 01. 벡터와 결정적 로컬 임베딩 시작하기

## 1. 학습 목표

이 장을 마치면 텍스트를 dense vector로 바꾸는 목적을 설명하고, 같은 입력이 항상 같은 벡터를 만드는 로컬 임베딩으로 문장 유사도를 계산할 수 있습니다. 또한 cosine similarity, dot product, Euclidean distance가 각각 무엇을 비교하는지 구분할 수 있습니다.

## 2. 왜 필요한가

키워드 검색은 같은 단어가 있어야 문서를 찾습니다. 예를 들어 사용자가 `API 오류 처리`를 찾을 때 문서가 `예외와 재시도`라고만 표현하면 단순 문자열 일치만으로는 놓칠 수 있습니다. 임베딩(embedding)은 텍스트를 숫자 벡터로 변환해 문서와 질의를 같은 공간에서 비교할 수 있게 합니다.

이 장의 모델은 학습된 의미 모델 대신 고정 해시를 사용합니다. 따라서 뜻이 비슷한 서로 다른 단어를 이해하지는 못합니다. 다만 외부 API, 모델 파일, GPU 없이도 벡터의 차원·정규화·유사도 계산 흐름을 정확히 재현할 수 있습니다.

## 3. 핵심 개념

- **벡터(vector)**: 여러 숫자를 순서대로 담은 값입니다. `[0.2, -0.1, 0.7]`은 3차원 벡터입니다.
- **차원(dimension)**: 벡터에 든 숫자의 개수입니다. 비교하는 두 벡터는 반드시 같은 차원이어야 합니다.
- **Dense vector**: 대부분의 위치에 값이 있는 고정 길이 배열입니다. 이 장의 출력이 이에 해당합니다.
- **Sparse vector**: 대부분이 0이고, 값이 있는 위치만 `(index, value)`로 저장하는 표현입니다. 키워드 기반 검색이나 hybrid search에서 유용합니다.
- **문서 임베딩(document embedding)**: 저장할 문서를 벡터로 변환한 결과입니다.
- **질의 임베딩(query embedding)**: 사용자의 검색 질문을 같은 모델과 차원으로 변환한 결과입니다.
- **Cosine similarity**: 두 벡터가 가리키는 방향의 유사도입니다. 1에 가까울수록 방향이 비슷합니다.
- **Dot product**: 같은 위치의 값을 곱해 합친 값입니다. 벡터 길이도 점수에 반영됩니다.
- **Euclidean distance**: 두 점 사이의 직선 거리입니다. 작을수록 가깝습니다.

> [!NOTE]
> 이 예제는 각 벡터를 L2 정규화합니다. 이 상태에서는 cosine similarity가 문서의 길이보다 벡터 방향을 비교하게 됩니다.

## 4. 동작 구조

```text
문서 "Python API 오류 처리" ─┐
                              ├─> DeterministicEmbeddingModel ─> 64차원 dense vector
질의 "API 오류 처리 방법" ────┘                                      │
                                                                      ▼
                                                        cosine similarity 점수
                                                                      │
                                                                      ▼
                                                            높은 점수부터 정렬
```

문서와 질의는 같은 `DeterministicEmbeddingModel(dimensions=64)`를 사용해야 합니다. 모델 또는 차원이 다르면 한 좌표가 같은 특징을 뜻한다는 보장이 없어 비교할 수 없습니다.

## 5. 실습 환경

- Python 3.12 이상과 `uv`가 필요합니다.
- 실행 위치는 **저장소 루트**입니다.
- 사용할 파일은 `examples/volume04/embedding_similarity.py`입니다.
- 이 장은 인터넷 연결, Docker, Qdrant, API 키를 사용하지 않습니다.

```bash
# 실행 위치: 저장소 루트의 Windows PowerShell, Git Bash 또는 WSL 터미널
uv run python examples/volume04/embedding_similarity.py
```

`uv run`은 프로젝트의 Python 환경에서 예제를 실행합니다. 환경이 준비되지 않았다면 `uv sync --group dev`로 개발 의존성을 설치한 뒤 다시 실행합니다.

## 6. 단계별 실습

1. `examples/volume04/embedding_similarity.py`에서 `query`와 `documents`를 확인합니다.
2. `DeterministicEmbeddingModel(dimensions=64)`가 입력 하나당 64개 숫자를 만들도록 합니다.
3. 질의를 `embed_one`으로 변환합니다.
4. 각 문서를 같은 모델로 변환합니다.
5. `cosine_similarity` 점수를 계산하고 내림차순으로 정렬합니다.

다음 명령으로 구현 계약도 확인합니다.

```bash
# 실행 위치: 저장소 루트의 Windows PowerShell, Git Bash 또는 WSL 터미널
uv run pytest tests/unit/test_volume04_embedding_service.py -q
```

## 7. 코드 설명

`DeterministicEmbeddingModel`은 텍스트를 소문자 토큰으로 나누고, 각 토큰의 SHA-256 결과를 차원 위치와 부호로 바꿉니다. SHA-256은 입력이 같으면 항상 같은 결과를 내므로 테스트가 재현됩니다. 토큰의 값을 더한 다음 L2 정규화합니다. 단일 텍스트에는 `embed_one(text)`를 쓰고, `embed(texts)`에는 비어 있지 않은 문자열 sequence만 전달합니다. 문자열 자체는 Python에서 sequence이지만 여러 문서 batch가 아니므로 `embed("문서 하나")`처럼 전달하지 않습니다.

`cosine_similarity`는 다음 식으로 계산합니다.

```text
cosine(A, B) = dot(A, B) / (||A|| × ||B||)
```

`dot_product`는 각 vector를 최대 절댓값으로 scale한 뒤 `math.fsum`으로 보상 합산하고 최종값만 다시 scale합니다. 따라서 `[1e16, 1, -1e16]`처럼 큰 양·음 항이 상쇄될 때 일반적인 순차 합산이 버릴 수 있는 작은 유한 잔차를 보존하며, `[1e308, 1e308] · [1e308, -1e308]`도 intermediate `+/-inf` 때문에 실패하지 않고 `0.0`으로 계산합니다. 내적은 zero vector에도 정의되므로 한쪽이 zero vector이면 scale을 시도하지 않고 `0.0`을 반환합니다. `euclidean_distance`는 위치별 차이의 직선 거리를 계산하며, `math.hypot`의 내부 scale을 사용하므로 `sqrt(sum(delta ** 2))`처럼 `1e308`의 유한 component를 먼저 제곱해 overflow하지 않습니다. `cosine_similarity`도 먼저 각 vector를 최대 절댓값으로 scale한 뒤 norm과 방향 score를 계산합니다. 따라서 `1e308`처럼 유한하지만 큰 component도 중간 제곱·dot product overflow 없이 비교합니다. 부동소수점 반올림으로 동일한 정규화 vector가 `1.0000000000000002`처럼 계산되더라도 결과를 닫힌 범위 `[-1.0, 1.0]`로 제한합니다. 구현은 빈 벡터, 문자열 container, bool·`NaN`·무한대를 포함한 비유한 수치, 차원 불일치, cosine의 zero vector를 예외로 거부합니다.

## 8. 정상 실행 결과

출력의 첫 줄은 다음 형식입니다.

```text
query_dimensions=64
```

그 뒤에 점수와 문서가 높은 점수부터 표시됩니다. `Python API 오류 처리와 재시도 전략` 문서는 질의와 토큰을 공유하므로 이 고정 입력에서는 첫 순위여야 합니다. 점수의 마지막 자리 대신 **순위, 차원, 반복 실행의 동일성**을 확인합니다.

Volume 04 단위 테스트 명령이 모두 통과해야 합니다. 실행 결과가 다르면 문서와 질의가 같은 모델 인스턴스 구성 및 같은 차원을 쓰는지 확인합니다.

## 9. 오류 해결

| 증상 | 원인 | 확인 및 해결 |
|---|---|---|
| `No module named ai_platform` | 저장소 루트 밖에서 실행했거나 프로젝트 환경을 쓰지 않음 | 저장소 루트로 이동한 뒤 `uv run python ...`을 사용합니다. |
| `dimensions must be ...` | 차원이 8 미만, 4096 초과, 또는 정수가 아님 | `8`부터 `4096` 사이의 정수를 전달합니다. |
| `text must contain ...` | 공백이나 기호만 있는 텍스트 | 문서와 질의에 글자 또는 숫자를 넣습니다. |
| `texts must be a non-empty sequence of strings` | batch API에 단일 문자열·bytes·빈 목록·비-sequence을 전달함 | 하나의 문서는 `embed_one`으로 처리하고, 여러 문서는 비어 있지 않은 `list[str]` 또는 `tuple[str, ...]`로 `embed`에 전달합니다. |
| `vectors must have the same dimension` | 문서와 질의에 다른 모델 차원을 사용함 | 저장과 검색에 같은 모델 설정을 사용합니다. |
| `vectors must contain only finite numbers` | vector에 `NaN`, 무한대, bool 또는 숫자가 아닌 값이 있음 | JSON number와 같은 유한 `int`/`float` 값만 전달합니다. |

## 10. 응용 실습

`documents`에 자신의 업무 문서 제목 세 개를 추가하고 질의를 하나 바꿉니다. 먼저 토큰을 공유하는 문서가 높은 순위인지 확인합니다. 이어서 `dimensions=128`로 바꾼 뒤에도 벡터 길이가 128이고 같은 입력의 결과가 반복 실행에서 같은지 테스트를 추가해 검증합니다.

## 11. 실무 적용

운영에서는 고정 해시 모델 대신 검증된 임베딩 모델을 선택합니다. 문서와 질의에 동일한 모델 버전, 차원, 전처리를 적용하고, 변경 시 기존 벡터를 재색인해야 합니다. metadata는 원문 ID, 출처, 권한, 생성 시각처럼 필터링과 추적에 필요한 값만 저장합니다. API 키와 문서 원문을 로그에 남기지 않습니다.

## 12. 과제

- **기본**: `cosine_similarity([1, 0], [0, 1])`와 `euclidean_distance([1, 0], [0, 1])`의 뜻을 주석으로 설명합니다.
- **응용**: 질의와 문서가 다른 차원일 때 예외가 발생하는 테스트를 작성합니다.
- **심화**: `EmbeddingModel` Protocol을 구현하는 다른 로컬 mock을 만들고, 같은 차원을 보장하는 이유를 README에 기록합니다.

## 13. 완료 체크리스트

- [x] 벡터와 차원을 설명할 수 있다.
- [x] dense vector와 sparse vector의 차이를 설명할 수 있다.
- [x] cosine, dot product, Euclidean distance의 역할을 구분할 수 있다.
- [x] API 키 없이 예제를 실행했다.
- [x] 문서와 질의에 같은 모델과 차원을 적용했다.
- [x] Volume 04 전용 단위 테스트를 실행했다.
- [ ] Qdrant collection에 vector와 metadata를 저장한다. 다음 장에서 완료합니다.

## 14. 핵심 정리

임베딩은 텍스트를 비교 가능한 숫자 벡터로 바꾸는 과정입니다. 검색은 문서와 질의를 같은 벡터 공간에 놓고 유사도 또는 거리를 계산해 순위를 매깁니다. 이 장의 결정적 로컬 mock은 그 흐름을 안전하게 검증합니다. 다음 slice에서는 이 벡터를 collection과 payload에 저장할 준비를 합니다.
