"""고정 로컬 질의로 RAG 검색 품질을 재현 가능하게 평가한다.

이 모듈은 네트워크, 제공자 SDK, 생성 모델 또는 실시간 데이터를 사용하지 않는다.
호출자가 제공한 작은 고정 평가 세트와 ``SearchableIndex``만 사용해 검색 결과의
Recall@k, Hit rate, MRR을 계산한다. 문서 원문이나 생성 답변을 결과에 복사하지 않아
평가 산출물은 테스트 가능한 청크 식별자와 집계 지표만 포함한다.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from ai_platform.rag.retrieval import RagConfigurationError, SearchableIndex, SearchHit


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    """하나 이상의 기대 근거 청크를 갖는 고정 로컬 검색 평가 질의다."""

    case_id: str
    query: str
    expected_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise RagConfigurationError("evaluation case_id must be a non-empty string")
        if not isinstance(self.query, str) or not self.query.strip():
            raise RagConfigurationError("evaluation query must be a non-empty string")
        if not isinstance(self.expected_chunk_ids, tuple) or not self.expected_chunk_ids:
            raise RagConfigurationError("evaluation expected_chunk_ids must be a non-empty tuple")
        if any(
            not isinstance(chunk_id, str) or not chunk_id.strip()
            for chunk_id in self.expected_chunk_ids
        ):
            raise RagConfigurationError(
                "evaluation expected_chunk_ids must contain non-empty strings"
            )
        if len(set(self.expected_chunk_ids)) != len(self.expected_chunk_ids):
            raise RagConfigurationError("evaluation expected_chunk_ids must not contain duplicates")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationConfig:
    """재현 가능한 고정 질의 평가의 반환 근거 수와 최대 사례 수다."""

    top_k: int = 3
    max_cases: int = 100

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("top_k", self.top_k, 20),
            ("max_cases", self.max_cases, 1_000),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise RagConfigurationError(
                    f"evaluation {field_name} must be an integer between 1 and {maximum}"
                )


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationSetLoadingConfig:
    """명시한 로컬 JSON 평가 세트 파일의 크기와 사례 수 제한이다."""

    max_file_bytes: int = 100_000
    max_cases: int = 100

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("max_file_bytes", self.max_file_bytes, 1_000_000),
            ("max_cases", self.max_cases, 1_000),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise RagConfigurationError(
                    f"evaluation set {field_name} must be an integer between 1 and {maximum}"
                )


class LocalRetrievalEvaluationSetLoader:
    """허용된 로컬 루트 아래의 고정 JSON 평가 사례만 읽는다.

    이 경계는 디렉터리를 탐색하거나 네트워크·제공자 SDK를 사용하지 않는다. 호출자가
    지정한 UTF-8 ``.json`` 파일 하나만 읽고, 파일 크기·경로·JSON 구조·중복 키·사례
    식별자를 검증한 뒤 ``RetrievalEvaluationCase`` tuple로 변환한다.
    """

    def __init__(
        self,
        *,
        root: Path,
        config: RetrievalEvaluationSetLoadingConfig | None = None,
    ) -> None:
        if not isinstance(root, Path):
            raise RagConfigurationError("evaluation set root must be a pathlib.Path")
        if not root.is_dir():
            raise RagConfigurationError("evaluation set root must be an existing directory")
        self._root = root.resolve()
        self._config = config or RetrievalEvaluationSetLoadingConfig()

    def load(self, relative_path: Path) -> tuple[RetrievalEvaluationCase, ...]:
        """고정 JSON 사례 파일을 검증된 평가 사례 tuple로 반환한다."""
        candidate = self._resolve_path(relative_path)
        try:
            raw_bytes = candidate.read_bytes()
        except OSError as error:
            raise RagConfigurationError("evaluation set file could not be read") from error
        if not raw_bytes:
            raise RagConfigurationError("evaluation set file must not be empty")
        if len(raw_bytes) > self._config.max_file_bytes:
            raise RagConfigurationError("evaluation set file exceeds the configured size limit")
        try:
            payload = json.loads(
                raw_bytes.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_nonstandard_json_constant,
            )
        except UnicodeDecodeError as error:
            raise RagConfigurationError("evaluation set file must be UTF-8 encoded") from error
        except (json.JSONDecodeError, ValueError) as error:
            raise RagConfigurationError("evaluation set file must contain valid JSON") from error
        return self._validated_cases(payload)

    def _resolve_path(self, relative_path: Path) -> Path:
        if not isinstance(relative_path, Path):
            raise RagConfigurationError("evaluation set relative_path must be a pathlib.Path")
        if relative_path.is_absolute() or not relative_path.parts:
            raise RagConfigurationError(
                "evaluation set relative_path must be a non-empty relative path"
            )
        if relative_path.suffix.casefold() != ".json":
            raise RagConfigurationError("only JSON evaluation set files (.json) are supported")
        candidate = (self._root / relative_path).resolve()
        if not candidate.is_relative_to(self._root):
            raise RagConfigurationError("evaluation set relative_path must stay within root")
        if not candidate.is_file():
            raise RagConfigurationError("evaluation set file does not exist")
        return candidate

    def _validated_cases(self, payload: object) -> tuple[RetrievalEvaluationCase, ...]:
        if not isinstance(payload, dict):
            raise RagConfigurationError("evaluation set JSON root must be an object")
        if set(payload) != {"cases"}:
            raise RagConfigurationError("evaluation set JSON root must contain only cases")
        raw_cases = payload["cases"]
        if not isinstance(raw_cases, list):
            raise RagConfigurationError("evaluation set cases must be an array")
        if not raw_cases:
            raise RagConfigurationError("evaluation set must contain at least one case")
        if len(raw_cases) > self._config.max_cases:
            raise RagConfigurationError("evaluation set contains more cases than configured")

        cases = tuple(self._case_from_json(raw_case) for raw_case in raw_cases)
        case_ids = [case.case_id for case in cases]
        if len(set(case_ids)) != len(case_ids):
            raise RagConfigurationError("evaluation set case_id values must be unique")
        return cases

    @staticmethod
    def _case_from_json(raw_case: object) -> RetrievalEvaluationCase:
        if not isinstance(raw_case, dict):
            raise RagConfigurationError("evaluation set cases must be objects")
        if set(raw_case) != {"case_id", "query", "expected_chunk_ids"}:
            raise RagConfigurationError(
                "evaluation set cases must contain only case_id, query, and expected_chunk_ids"
            )
        case_id = raw_case["case_id"]
        query = raw_case["query"]
        expected_chunk_ids = raw_case["expected_chunk_ids"]
        if not isinstance(case_id, str) or not isinstance(query, str):
            raise RagConfigurationError("evaluation set case_id and query must be strings")
        if not isinstance(expected_chunk_ids, list):
            raise RagConfigurationError("evaluation set expected_chunk_ids must be an array")
        if not all(isinstance(chunk_id, str) for chunk_id in expected_chunk_ids):
            raise RagConfigurationError("evaluation set expected_chunk_ids must contain strings")
        return RetrievalEvaluationCase(
            case_id=case_id,
            query=query,
            expected_chunk_ids=tuple(expected_chunk_ids),
        )


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """중복 키를 덮어쓰지 않아 파일 기반 평가 정의가 모호해지지 않게 한다."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_nonstandard_json_constant(value: str) -> NoReturn:
    """표준 JSON에 없는 NaN/Infinity 상수를 거부한다."""
    raise ValueError(f"non-standard JSON constant: {value}")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationResult:
    """한 고정 질의의 검색 순위와 근거 회수 지표다."""

    case_id: str
    query: str
    expected_chunk_ids: tuple[str, ...]
    retrieved_chunk_ids: tuple[str, ...]
    first_relevant_rank: int | None
    recall_at_k: float
    reciprocal_rank: float

    @property
    def passed(self) -> bool:
        """상위 k 안에 기대 근거가 하나 이상 있으면 참이다."""
        return self.first_relevant_rank is not None

    def to_payload(self) -> dict[str, object]:
        """원문·생성 답변 없이 JSON 호환 평가 결과를 반환한다."""
        return {
            "case_id": self.case_id,
            "expected_chunk_ids": list(self.expected_chunk_ids),
            "retrieved_chunk_ids": list(self.retrieved_chunk_ids),
            "first_relevant_rank": self.first_relevant_rank,
            "passed": self.passed,
            "recall_at_k": self.recall_at_k,
            "reciprocal_rank": self.reciprocal_rank,
        }


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationReport:
    """고정 평가 세트 전체의 Recall@k·Hit rate·MRR 집계다."""

    top_k: int
    results: tuple[RetrievalEvaluationResult, ...]
    recall_at_k: float
    hit_rate: float
    mean_reciprocal_rank: float

    @property
    def evaluated_cases(self) -> int:
        """평가된 고정 질의 수를 반환한다."""
        return len(self.results)

    def to_payload(self) -> dict[str, object]:
        """프레임워크 없이 기록·비교할 수 있는 JSON 호환 평가 보고서를 반환한다."""
        return {
            "top_k": self.top_k,
            "evaluated_cases": self.evaluated_cases,
            "recall_at_k": self.recall_at_k,
            "hit_rate": self.hit_rate,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
            "results": [result.to_payload() for result in self.results],
        }


class RetrievalEvaluator:
    """주입된 로컬 검색기를 고정 기대 청크 ID로 평가한다.

    생성기를 호출하지 않고 ``search``만 실행한다. 검색기가 반환하는 값도 다시 검증해
    tuple 이외 값, 요청보다 많은 결과, ``SearchHit`` 이외 값, 중복 청크 ID를 평가
    지표에 반영하지 않는다. 검색기 내부 오류는 숨기지 않고 호출자에게 전파한다.
    """

    def __init__(
        self, *, index: SearchableIndex, config: RetrievalEvaluationConfig | None = None
    ) -> None:
        if not hasattr(index, "search"):
            raise RagConfigurationError("index must provide a search method")
        self._index = index
        self._config = config or RetrievalEvaluationConfig()

    def evaluate(self, cases: Iterable[RetrievalEvaluationCase]) -> RetrievalEvaluationReport:
        """명시한 고정 사례만 평가하고 마이크로 Recall@k·Hit rate·MRR을 반환한다."""
        evaluation_cases = self._validated_cases(cases)
        results = tuple(self._evaluate_case(case) for case in evaluation_cases)
        expected_count = sum(len(result.expected_chunk_ids) for result in results)
        recovered_count = sum(
            len(set(result.expected_chunk_ids).intersection(result.retrieved_chunk_ids))
            for result in results
        )
        hit_count = sum(result.passed for result in results)
        return RetrievalEvaluationReport(
            top_k=self._config.top_k,
            results=results,
            recall_at_k=recovered_count / expected_count,
            hit_rate=hit_count / len(results),
            mean_reciprocal_rank=sum(result.reciprocal_rank for result in results) / len(results),
        )

    def _validated_cases(
        self, cases: Iterable[RetrievalEvaluationCase]
    ) -> tuple[RetrievalEvaluationCase, ...]:
        try:
            evaluation_cases = tuple(cases)
        except TypeError as error:
            raise RagConfigurationError(
                "evaluation cases must be an iterable of RetrievalEvaluationCase values"
            ) from error
        if not evaluation_cases:
            raise RagConfigurationError("at least one evaluation case is required")
        if len(evaluation_cases) > self._config.max_cases:
            raise RagConfigurationError("evaluation received more cases than configured")
        if any(not isinstance(case, RetrievalEvaluationCase) for case in evaluation_cases):
            raise RagConfigurationError("evaluation cases must be RetrievalEvaluationCase values")
        case_ids = [case.case_id for case in evaluation_cases]
        if len(set(case_ids)) != len(case_ids):
            raise RagConfigurationError("evaluation case_id values must be unique")
        return evaluation_cases

    def _evaluate_case(self, case: RetrievalEvaluationCase) -> RetrievalEvaluationResult:
        hits = self._validated_hits(self._index.search(case.query, top_k=self._config.top_k))
        retrieved_chunk_ids = tuple(hit.chunk.chunk_id for hit in hits)
        expected_chunk_ids = set(case.expected_chunk_ids)
        first_relevant_rank = next(
            (
                rank
                for rank, chunk_id in enumerate(retrieved_chunk_ids, start=1)
                if chunk_id in expected_chunk_ids
            ),
            None,
        )
        recovered_count = len(expected_chunk_ids.intersection(retrieved_chunk_ids))
        return RetrievalEvaluationResult(
            case_id=case.case_id,
            query=case.query,
            expected_chunk_ids=case.expected_chunk_ids,
            retrieved_chunk_ids=retrieved_chunk_ids,
            first_relevant_rank=first_relevant_rank,
            recall_at_k=recovered_count / len(expected_chunk_ids),
            reciprocal_rank=0.0 if first_relevant_rank is None else 1.0 / first_relevant_rank,
        )

    def _validated_hits(self, hits: tuple[SearchHit, ...]) -> tuple[SearchHit, ...]:
        if not isinstance(hits, tuple):
            raise RagConfigurationError("index must return a tuple of SearchHit values")
        if len(hits) > self._config.top_k:
            raise RagConfigurationError("index returned more hits than requested")
        chunk_ids: set[str] = set()
        for hit in hits:
            if not isinstance(hit, SearchHit):
                raise RagConfigurationError("index must return SearchHit values")
            if hit.chunk.chunk_id in chunk_ids:
                raise RagConfigurationError("index must not return duplicate hit chunk IDs")
            chunk_ids.add(hit.chunk.chunk_id)
        return hits


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationBaselineCase:
    """회귀 비교에서 동일한 기대 근거를 확인하기 위한 고정 사례 참조다."""

    case_id: str
    query: str
    expected_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise RagConfigurationError("baseline case_id must be a non-empty string")
        if not isinstance(self.query, str) or not self.query.strip():
            raise RagConfigurationError("baseline query must be a non-empty string")
        if not isinstance(self.expected_chunk_ids, tuple) or not self.expected_chunk_ids:
            raise RagConfigurationError("baseline expected_chunk_ids must be a non-empty tuple")
        if any(
            not isinstance(chunk_id, str) or not chunk_id.strip()
            for chunk_id in self.expected_chunk_ids
        ):
            raise RagConfigurationError(
                "baseline expected_chunk_ids must contain non-empty strings"
            )
        if len(set(self.expected_chunk_ids)) != len(self.expected_chunk_ids):
            raise RagConfigurationError("baseline expected_chunk_ids must not contain duplicates")


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationBaseline:
    """같은 고정 평가 세트에서 허용 가능한 검색 품질 기준선이다."""

    top_k: int
    cases: tuple[RetrievalEvaluationBaselineCase, ...]
    recall_at_k: float
    hit_rate: float
    mean_reciprocal_rank: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.top_k, bool)
            or not isinstance(self.top_k, int)
            or not 1 <= self.top_k <= 20
        ):
            raise RagConfigurationError("baseline top_k must be an integer between 1 and 20")
        if not isinstance(self.cases, tuple) or not self.cases:
            raise RagConfigurationError("baseline cases must be a non-empty tuple")
        if any(not isinstance(case, RetrievalEvaluationBaselineCase) for case in self.cases):
            raise RagConfigurationError(
                "baseline cases must contain RetrievalEvaluationBaselineCase values"
            )
        case_ids = [case.case_id for case in self.cases]
        if len(set(case_ids)) != len(case_ids):
            raise RagConfigurationError("baseline case_id values must be unique")
        for field_name, value in (
            ("recall_at_k", self.recall_at_k),
            ("hit_rate", self.hit_rate),
            ("mean_reciprocal_rank", self.mean_reciprocal_rank),
        ):
            _validate_unit_interval_score(field_name=field_name, value=value)

    @classmethod
    def from_report(cls, report: RetrievalEvaluationReport) -> RetrievalEvaluationBaseline:
        """검증된 현재 보고서를 이후의 결정론적 회귀 기준선으로 고정한다."""
        _validate_evaluation_report(report)
        return cls(
            top_k=report.top_k,
            cases=tuple(
                RetrievalEvaluationBaselineCase(
                    case_id=result.case_id,
                    query=result.query,
                    expected_chunk_ids=result.expected_chunk_ids,
                )
                for result in report.results
            ),
            recall_at_k=report.recall_at_k,
            hit_rate=report.hit_rate,
            mean_reciprocal_rank=report.mean_reciprocal_rank,
        )

    def to_payload(self) -> dict[str, object]:
        """질의·원문 없이 고정 기준선의 호환성 정보와 집계 점수를 반환한다."""
        return {
            "top_k": self.top_k,
            "cases": [
                {
                    "case_id": case.case_id,
                    "expected_chunk_ids": list(case.expected_chunk_ids),
                }
                for case in self.cases
            ],
            "recall_at_k": self.recall_at_k,
            "hit_rate": self.hit_rate,
            "mean_reciprocal_rank": self.mean_reciprocal_rank,
        }


@dataclass(frozen=True, slots=True)
class RetrievalRegressionPolicy:
    """기준선보다 낮아질 수 있는 각 검색 지표의 최대 폭이다."""

    maximum_recall_at_k_drop: float = 0.0
    maximum_hit_rate_drop: float = 0.0
    maximum_mean_reciprocal_rank_drop: float = 0.0

    def __post_init__(self) -> None:
        for field_name, value in (
            ("maximum_recall_at_k_drop", self.maximum_recall_at_k_drop),
            ("maximum_hit_rate_drop", self.maximum_hit_rate_drop),
            (
                "maximum_mean_reciprocal_rank_drop",
                self.maximum_mean_reciprocal_rank_drop,
            ),
        ):
            _validate_unit_interval_score(field_name=field_name, value=value)


@dataclass(frozen=True, slots=True)
class RetrievalRegressionBaselineLoadingConfig:
    """명시한 로컬 기준선·정책 JSON 파일의 크기와 사례 수 제한이다."""

    max_file_bytes: int = 100_000
    max_cases: int = 100

    def __post_init__(self) -> None:
        for field_name, value, maximum in (
            ("max_file_bytes", self.max_file_bytes, 1_000_000),
            ("max_cases", self.max_cases, 1_000),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise RagConfigurationError(
                    f"regression baseline {field_name} must be an integer between 1 and {maximum}"
                )


@dataclass(frozen=True, slots=True)
class RetrievalRegressionBaselineFile:
    """로컬 파일에서 함께 검증한 기준선과 회귀 정책이다."""

    baseline: RetrievalEvaluationBaseline
    policy: RetrievalRegressionPolicy


class LocalRetrievalRegressionBaselineLoader:
    """허용된 로컬 루트 아래의 고정 기준선·정책 JSON 하나만 읽는다.

    이 경계는 자동 탐색·검색·생성·네트워크·제공자 SDK를 사용하지 않는다. 호출자가
    명시한 파일을 UTF-8 및 엄격한 JSON 스키마로 검증하여, 서로 다른 사례나 모호한
    정책을 이전 검색 품질 기준선으로 기록하지 못하게 한다.
    """

    def __init__(
        self,
        *,
        root: Path,
        config: RetrievalRegressionBaselineLoadingConfig | None = None,
    ) -> None:
        if not isinstance(root, Path):
            raise RagConfigurationError("regression baseline root must be a pathlib.Path")
        if not root.is_dir():
            raise RagConfigurationError("regression baseline root must be an existing directory")
        self._root = root.resolve()
        self._config = config or RetrievalRegressionBaselineLoadingConfig()

    def load(self, relative_path: Path) -> RetrievalRegressionBaselineFile:
        """엄격히 검증한 고정 기준선과 회귀 정책을 반환한다."""
        candidate = self._resolve_path(relative_path)
        try:
            raw_bytes = candidate.read_bytes()
        except OSError as error:
            raise RagConfigurationError("regression baseline file could not be read") from error
        if not raw_bytes:
            raise RagConfigurationError("regression baseline file must not be empty")
        if len(raw_bytes) > self._config.max_file_bytes:
            raise RagConfigurationError(
                "regression baseline file exceeds the configured size limit"
            )
        try:
            payload = json.loads(
                raw_bytes.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_nonstandard_json_constant,
            )
        except UnicodeDecodeError as error:
            raise RagConfigurationError("regression baseline file must be UTF-8 encoded") from error
        except (json.JSONDecodeError, ValueError) as error:
            raise RagConfigurationError(
                "regression baseline file must contain valid JSON"
            ) from error
        return self._validated_file(payload)

    def _resolve_path(self, relative_path: Path) -> Path:
        if not isinstance(relative_path, Path):
            raise RagConfigurationError("regression baseline relative_path must be a pathlib.Path")
        if relative_path.is_absolute() or not relative_path.parts:
            raise RagConfigurationError(
                "regression baseline relative_path must be a non-empty relative path"
            )
        if relative_path.suffix.casefold() != ".json":
            raise RagConfigurationError("only JSON regression baseline files (.json) are supported")
        candidate = (self._root / relative_path).resolve()
        if not candidate.is_relative_to(self._root):
            raise RagConfigurationError("regression baseline relative_path must stay within root")
        if not candidate.is_file():
            raise RagConfigurationError("regression baseline file does not exist")
        return candidate

    def _validated_file(self, payload: object) -> RetrievalRegressionBaselineFile:
        if not isinstance(payload, dict):
            raise RagConfigurationError("regression baseline JSON root must be an object")
        if set(payload) != {"baseline", "policy"}:
            raise RagConfigurationError(
                "regression baseline JSON root must contain only baseline and policy"
            )
        baseline = self._baseline_from_json(payload["baseline"])
        policy = self._policy_from_json(payload["policy"])
        return RetrievalRegressionBaselineFile(baseline=baseline, policy=policy)

    def _baseline_from_json(self, raw_baseline: object) -> RetrievalEvaluationBaseline:
        if not isinstance(raw_baseline, dict):
            raise RagConfigurationError("regression baseline must be an object")
        required_fields = {
            "top_k",
            "cases",
            "recall_at_k",
            "hit_rate",
            "mean_reciprocal_rank",
        }
        if set(raw_baseline) != required_fields:
            raise RagConfigurationError(
                "regression baseline contains unsupported or missing fields"
            )
        raw_cases = raw_baseline["cases"]
        if not isinstance(raw_cases, list) or not raw_cases:
            raise RagConfigurationError("regression baseline cases must be a non-empty array")
        if len(raw_cases) > self._config.max_cases:
            raise RagConfigurationError("regression baseline contains more cases than configured")
        cases = tuple(self._baseline_case_from_json(raw_case) for raw_case in raw_cases)
        return RetrievalEvaluationBaseline(
            top_k=raw_baseline["top_k"],
            cases=cases,
            recall_at_k=raw_baseline["recall_at_k"],
            hit_rate=raw_baseline["hit_rate"],
            mean_reciprocal_rank=raw_baseline["mean_reciprocal_rank"],
        )

    @staticmethod
    def _baseline_case_from_json(raw_case: object) -> RetrievalEvaluationBaselineCase:
        if not isinstance(raw_case, dict):
            raise RagConfigurationError("regression baseline cases must be objects")
        if set(raw_case) != {"case_id", "query", "expected_chunk_ids"}:
            raise RagConfigurationError(
                "regression baseline cases must contain only case_id, query, and expected_chunk_ids"
            )
        expected_chunk_ids = raw_case["expected_chunk_ids"]
        if not isinstance(expected_chunk_ids, list):
            raise RagConfigurationError("regression baseline expected_chunk_ids must be an array")
        if not all(isinstance(chunk_id, str) for chunk_id in expected_chunk_ids):
            raise RagConfigurationError(
                "regression baseline expected_chunk_ids must contain strings"
            )
        return RetrievalEvaluationBaselineCase(
            case_id=raw_case["case_id"],
            query=raw_case["query"],
            expected_chunk_ids=tuple(expected_chunk_ids),
        )

    @staticmethod
    def _policy_from_json(raw_policy: object) -> RetrievalRegressionPolicy:
        if not isinstance(raw_policy, dict):
            raise RagConfigurationError("regression policy must be an object")
        required_fields = {
            "maximum_recall_at_k_drop",
            "maximum_hit_rate_drop",
            "maximum_mean_reciprocal_rank_drop",
        }
        if set(raw_policy) != required_fields:
            raise RagConfigurationError("regression policy contains unsupported or missing fields")
        return RetrievalRegressionPolicy(
            maximum_recall_at_k_drop=raw_policy["maximum_recall_at_k_drop"],
            maximum_hit_rate_drop=raw_policy["maximum_hit_rate_drop"],
            maximum_mean_reciprocal_rank_drop=raw_policy["maximum_mean_reciprocal_rank_drop"],
        )


@dataclass(frozen=True, slots=True)
class RetrievalRegressionMetricResult:
    """한 집계 지표의 기준선·현재 값·허용 하락 폭을 기록한다."""

    name: str
    baseline_score: float
    current_score: float
    drop: float
    maximum_drop: float

    @property
    def passed(self) -> bool:
        """현재 값이 정책이 허용하는 기준선 하락 범위 안에 있으면 참이다."""
        return self.drop <= self.maximum_drop

    def to_payload(self) -> dict[str, object]:
        """JSON 호환 단일 지표 회귀 판정 결과를 반환한다."""
        return {
            "name": self.name,
            "baseline_score": self.baseline_score,
            "current_score": self.current_score,
            "drop": self.drop,
            "maximum_drop": self.maximum_drop,
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class RetrievalRegressionDecision:
    """동일한 고정 평가 세트에 대한 전체 결정론적 회귀 판정이다."""

    top_k: int
    evaluated_cases: int
    metrics: tuple[RetrievalRegressionMetricResult, ...]

    @property
    def passed(self) -> bool:
        """모든 집계 지표가 정책을 통과했는지 반환한다."""
        return all(metric.passed for metric in self.metrics)

    def to_payload(self) -> dict[str, object]:
        """원문·질의·생성 답변 없이 JSON 호환 회귀 판정을 반환한다."""
        return {
            "top_k": self.top_k,
            "evaluated_cases": self.evaluated_cases,
            "passed": self.passed,
            "metrics": [metric.to_payload() for metric in self.metrics],
        }


class RetrievalRegressionChecker:
    """호환되는 고정 평가 보고서를 기준선 및 하락 허용 폭과 비교한다.

    기준선과 현재 보고서는 ``top_k`` 및 사례 순서·ID·질문·기대 청크 ID가 모두 같아야 한다.
    따라서 서로 다른 데이터셋 또는 다른 관련성 정의를 품질 개선/저하로 오인하지 않는다.
    이 경계는 로컬 보고서만 비교하며 검색·생성·네트워크·제공자 SDK를 호출하지 않는다.
    """

    def __init__(
        self,
        *,
        baseline: RetrievalEvaluationBaseline,
        policy: RetrievalRegressionPolicy | None = None,
    ) -> None:
        if not isinstance(baseline, RetrievalEvaluationBaseline):
            raise RagConfigurationError("baseline must be a RetrievalEvaluationBaseline")
        self._baseline = baseline
        self._policy = policy or RetrievalRegressionPolicy()

    def evaluate(self, report: RetrievalEvaluationReport) -> RetrievalRegressionDecision:
        """현재 보고서가 같은 기준선의 품질 하락 정책을 통과하는지 판정한다."""
        _validate_evaluation_report(report)
        current_cases = tuple(
            RetrievalEvaluationBaselineCase(
                case_id=result.case_id,
                query=result.query,
                expected_chunk_ids=result.expected_chunk_ids,
            )
            for result in report.results
        )
        if report.top_k != self._baseline.top_k:
            raise RagConfigurationError("regression report top_k must match the baseline")
        if current_cases != self._baseline.cases:
            raise RagConfigurationError(
                "regression report cases must match the baseline case order and expected chunk IDs"
            )
        return RetrievalRegressionDecision(
            top_k=report.top_k,
            evaluated_cases=report.evaluated_cases,
            metrics=(
                self._metric_result(
                    name="recall_at_k",
                    baseline_score=self._baseline.recall_at_k,
                    current_score=report.recall_at_k,
                    maximum_drop=self._policy.maximum_recall_at_k_drop,
                ),
                self._metric_result(
                    name="hit_rate",
                    baseline_score=self._baseline.hit_rate,
                    current_score=report.hit_rate,
                    maximum_drop=self._policy.maximum_hit_rate_drop,
                ),
                self._metric_result(
                    name="mean_reciprocal_rank",
                    baseline_score=self._baseline.mean_reciprocal_rank,
                    current_score=report.mean_reciprocal_rank,
                    maximum_drop=self._policy.maximum_mean_reciprocal_rank_drop,
                ),
            ),
        )

    @staticmethod
    def _metric_result(
        *, name: str, baseline_score: float, current_score: float, maximum_drop: float
    ) -> RetrievalRegressionMetricResult:
        return RetrievalRegressionMetricResult(
            name=name,
            baseline_score=baseline_score,
            current_score=current_score,
            drop=max(0.0, baseline_score - current_score),
            maximum_drop=maximum_drop,
        )


def _validate_unit_interval_score(*, field_name: str, value: object) -> None:
    """점수와 허용 하락 폭이 유한한 0~1 수인지 확인한다."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
    ):
        raise RagConfigurationError(f"{field_name} must be a finite number between 0 and 1")


def _validate_evaluation_report(report: object) -> None:
    """직접 생성된 보고서가 비교 계약을 우회하지 못하게 최소 불변식을 확인한다."""
    if not isinstance(report, RetrievalEvaluationReport):
        raise RagConfigurationError("regression report must be a RetrievalEvaluationReport")
    if (
        isinstance(report.top_k, bool)
        or not isinstance(report.top_k, int)
        or not 1 <= report.top_k <= 20
    ):
        raise RagConfigurationError("regression report top_k must be an integer between 1 and 20")
    if not isinstance(report.results, tuple) or not report.results:
        raise RagConfigurationError("regression report results must be a non-empty tuple")
    if any(not isinstance(result, RetrievalEvaluationResult) for result in report.results):
        raise RagConfigurationError(
            "regression report results must contain RetrievalEvaluationResult values"
        )
    case_ids = [result.case_id for result in report.results]
    if len(set(case_ids)) != len(case_ids):
        raise RagConfigurationError("regression report case_id values must be unique")
    for field_name, value in (
        ("regression report recall_at_k", report.recall_at_k),
        ("regression report hit_rate", report.hit_rate),
        ("regression report mean_reciprocal_rank", report.mean_reciprocal_rank),
    ):
        _validate_unit_interval_score(field_name=field_name, value=value)
