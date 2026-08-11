"""고정 기준선과 후보를 한 번에 실행해 결정론적 오프라인 평가 리포트를 출력한다."""
from __future__ import annotations

from ai_platform.evaluation import (
    FIXED_BASELINE_EVALUATION_INPUT,
    FIXED_CANDIDATE_EVALUATION_INPUT,
    FIXED_REGRESSION_POLICIES,
    compare_snapshots,
    format_offline_evaluation_report,
    run_offline_evaluation,
)


def main() -> None:
    """고정 데이터만 읽어 전체 평가와 회귀 결정을 사람이 읽을 수 있게 출력한다."""
    baseline = run_offline_evaluation(FIXED_BASELINE_EVALUATION_INPUT)
    candidate = run_offline_evaluation(FIXED_CANDIDATE_EVALUATION_INPUT)
    report = compare_snapshots(
        baseline.regression_snapshot(),
        candidate.regression_snapshot(),
        FIXED_REGRESSION_POLICIES,
    )
    print(format_offline_evaluation_report(baseline, candidate, report))


if __name__ == "__main__":
    main()
