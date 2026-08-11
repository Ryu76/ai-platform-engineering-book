"""Volume 04의 결정적 local mock 삭제·재색인 미니 프로젝트 테스트."""

from __future__ import annotations

import pytest

from ai_platform.embeddings import (
    ReindexLifecycleError,
    ReindexLifecycleReport,
    RetrievalMetrics,
    run_reindex_lifecycle,
)


def _report(
    *,
    initial_ranked_ids: tuple[str, ...] = ("retry-guide",),
    initial_metrics: object | None = None,
    deleted_count: int | bool = 1,
    collection_size_after_delete: int | bool = 2,
    collection_size: int | bool = 3,
    reindexed_version: int | bool = 2,
) -> ReindexLifecycleReport:
    """보고서 생성 시 public lifecycle 입력 계약을 집중적으로 검증한다."""
    return ReindexLifecycleReport(
        initial_ranked_ids=initial_ranked_ids,
        ranked_ids_after_delete=("docker-guide",),
        reindexed_ranked_ids=("retry-guide",),
        initial_metrics=(
            RetrievalMetrics(1.0, 1.0, 1.0, True) if initial_metrics is None else initial_metrics
        ),  # type: ignore[arg-type]
        reindexed_metrics=RetrievalMetrics(1.0, 1.0, 1.0, True),
        deleted_count=deleted_count,
        collection_size_after_delete=collection_size_after_delete,
        collection_size=collection_size,
        reindexed_version=reindexed_version,
    )


def test_reindex_lifecycle_removes_stale_point_and_restores_it_with_new_metadata() -> None:
    """삭제 뒤 stale ID가 사라지고 재색인 뒤 새 version의 같은 ID가 복구되어야 한다."""
    report = run_reindex_lifecycle()

    assert report.initial_ranked_ids[0] == "retry-guide"
    assert report.initial_metrics == RetrievalMetrics(1.0, 1.0, 1.0, True)
    assert report.deleted_count == 1
    assert report.collection_size_after_delete == 2
    assert "retry-guide" not in report.ranked_ids_after_delete
    assert report.reindexed_ranked_ids == ("retry-guide",)
    assert report.reindexed_metrics == RetrievalMetrics(1.0, 1.0, 1.0, True)
    assert report.reindexed_version == 2
    assert report.collection_size == 3


def test_reindex_lifecycle_is_deterministic_between_runs() -> None:
    """고정 문서와 local mock은 같은 lifecycle 보고서를 반복 생성해야 한다."""
    assert run_reindex_lifecycle() == run_reindex_lifecycle()


def test_reindex_report_rejects_mutable_or_invalid_public_state() -> None:
    """직접 만든 보고서도 mutable 순위, 잘못된 metrics와 카운터를 허용하면 안 된다."""
    with pytest.raises(ReindexLifecycleError, match="tuple"):
        _report(initial_ranked_ids=["retry-guide"])  # type: ignore[arg-type]
    with pytest.raises(ReindexLifecycleError, match="duplicates"):
        _report(initial_ranked_ids=("retry-guide", "retry-guide"))
    with pytest.raises(ReindexLifecycleError, match="initial_metrics"):
        _report(initial_metrics=object())
    with pytest.raises(ReindexLifecycleError, match="deleted_count"):
        _report(deleted_count=True)
    with pytest.raises(ReindexLifecycleError, match="reindexed_version"):
        _report(reindexed_version=0)
