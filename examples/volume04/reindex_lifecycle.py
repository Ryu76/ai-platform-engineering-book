"""Volume 04 local mock에서 삭제와 재색인 lifecycle을 실행한다."""
from __future__ import annotations

from ai_platform.embeddings import run_reindex_lifecycle


def main() -> None:
    """외부 서비스 없이 삭제 전후와 재색인 뒤의 검색 상태를 출력한다."""
    report = run_reindex_lifecycle()

    print("initial_ranked_ids=" + ",".join(report.initial_ranked_ids))
    print(
        f"deleted_count={report.deleted_count}; "
        f"collection_size_after_delete={report.collection_size_after_delete}"
    )
    print("ranked_ids_after_delete=" + ",".join(report.ranked_ids_after_delete))
    print("reindexed_ranked_ids=" + ",".join(report.reindexed_ranked_ids))
    print(
        f"reindexed_version={report.reindexed_version}; "
        f"collection_size={report.collection_size}; "
        f"top_1_recovered={report.reindexed_metrics.hit_at_k}"
    )


if __name__ == "__main__":
    main()
