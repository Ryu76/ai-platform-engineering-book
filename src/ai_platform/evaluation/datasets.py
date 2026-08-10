"""Volume 10 실습에서 공통으로 쓰는 고정 골든 데이터셋."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ai_platform.evaluation.retrieval_metrics import RetrievalCase

FIXED_RETRIEVAL_CASES: tuple[RetrievalCase, ...] = (
    RetrievalCase(
        case_id="access-reset",
        query="비밀번호를 잊었을 때 계정 접근을 복구하는 절차는 무엇인가요?",
        relevant_document_ids=("identity-access",),
    ),
    RetrievalCase(
        case_id="expense-receipt",
        query="출장 식비 영수증을 제출하는 규정은 어디에 있나요?",
        relevant_document_ids=("finance-expense",),
    ),
    RetrievalCase(
        case_id="incident-response",
        query="의심스러운 로그인 알림을 받았을 때의 초기 대응 절차는 무엇인가요?",
        relevant_document_ids=("security-incident", "operations-runbook"),
    ),
    RetrievalCase(
        case_id="benefits-enrollment",
        query="복지 제도 가입 기간과 신청 방법을 알려 주세요.",
        relevant_document_ids=("people-benefits",),
    ),
)
"""변하지 않는 질의·정답 문서 쌍; 외부 문서나 API에서 읽지 않는다."""

FIXED_RETRIEVAL_RESULTS_AT_3: Mapping[str, Sequence[str]] = {
    "access-reset": ("identity-access", "service-overview", "security-incident"),
    "expense-receipt": ("people-benefits", "finance-expense", "service-overview"),
    "incident-response": ("operations-runbook", "security-incident", "identity-access"),
    "benefits-enrollment": ("finance-expense", "service-overview", "identity-access"),
}
"""동일한 구현에서 기록한 고정 Top-3 결과; 지표 설명과 회귀 테스트에 사용한다."""
