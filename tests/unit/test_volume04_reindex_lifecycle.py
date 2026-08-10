"""Volume 04의 결정적 local mock 삭제·재색인 미니 프로젝트 테스트."""
from __future__ import annotations

from ai_platform.embeddings import RetrievalMetrics, run_reindex_lifecycle


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
