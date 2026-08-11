"""고정 후보 결과를 기준선과 비교해 결정론적 회귀 리포트를 출력한다."""
from __future__ import annotations

from ai_platform.evaluation import (
    FIXED_BASELINE_SNAPSHOT,
    FIXED_CANDIDATE_SNAPSHOT,
    FIXED_REGRESSION_POLICIES,
    compare_snapshots,
)


def main() -> None:
    """고정 골든 계약의 후보 승인 여부와 각 지표 차이를 출력한다."""
    report = compare_snapshots(
        FIXED_BASELINE_SNAPSHOT, FIXED_CANDIDATE_SNAPSHOT, FIXED_REGRESSION_POLICIES
    )
    print(f"Dataset: {report.dataset_id}@{report.dataset_version}")
    print(f"Evaluation cases: {report.cases_evaluated}")
    print(f"Decision: {'APPROVE' if report.is_approved else 'REJECT'}")
    for result in report.metric_results:
        print(
            f"{result.metric_id}: baseline={result.baseline_value:.6f}; "
            f"candidate={result.candidate_value:.6f}; delta={result.delta:+.6f}; "
            f"allowed_degradation={result.allowed_degradation:.6f}; status={result.status}"
        )


if __name__ == "__main__":
    main()
