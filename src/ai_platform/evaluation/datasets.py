"""Volume 10 실습에서 공통으로 쓰는 고정·버전 관리 골든 데이터셋."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ai_platform.evaluation.answer_metrics import AnswerCase, RecordedAnswer
from ai_platform.evaluation.golden_dataset import GoldenCase, GoldenDataset
from ai_platform.evaluation.retrieval_metrics import RetrievalCase
from ai_platform.evaluation.usage_metrics import RecordedUsage, TokenPricing, UsageCase
from ai_platform.evaluation.workflow_metrics import RecordedWorkflow, WorkflowCase

FIXED_GOLDEN_DATASET = GoldenDataset(
    dataset_id="volume10-support-policy",
    version="1.0.0",
    cases=(
        GoldenCase(
            case_id="access-reset",
            query="비밀번호를 잊었을 때 계정 접근을 복구하는 절차는 무엇인가요?",
            category="identity",
            expected_response="answer",
            relevant_document_ids=("identity-access",),
            label_rationale="계정 복구 절차는 identity-access 정책에만 정의되어 있다.",
            source_reference="policy-catalog-v1:identity-access",
        ),
        GoldenCase(
            case_id="expense-receipt",
            query="출장 식비 영수증을 제출하는 규정은 어디에 있나요?",
            category="finance",
            expected_response="answer",
            relevant_document_ids=("finance-expense",),
            label_rationale="출장 경비와 영수증 제출 규칙의 기준 문서는 finance-expense다.",
            source_reference="policy-catalog-v1:finance-expense",
        ),
        GoldenCase(
            case_id="incident-response",
            query="의심스러운 로그인 알림을 받았을 때의 초기 대응 절차는 무엇인가요?",
            category="security",
            expected_response="answer",
            relevant_document_ids=("security-incident", "operations-runbook"),
            label_rationale="보안 신고와 초기 운영 절차 두 문서를 모두 근거로 삼는다.",
            source_reference="policy-catalog-v1:security-incident,operations-runbook",
        ),
        GoldenCase(
            case_id="benefits-enrollment",
            query="복지 제도 가입 기간과 신청 방법을 알려 주세요.",
            category="people",
            expected_response="answer",
            relevant_document_ids=("people-benefits",),
            label_rationale="복지 가입 기간과 신청 흐름은 people-benefits에 정의되어 있다.",
            source_reference="policy-catalog-v1:people-benefits",
        ),
        GoldenCase(
            case_id="office-parking",
            query="사무실 주차권을 신청하려면 어떻게 해야 하나요?",
            category="facilities",
            expected_response="abstain",
            relevant_document_ids=(),
            label_rationale="고정 정책 카탈로그에는 사무실 주차권 정책이 포함되지 않는다.",
            source_reference="policy-catalog-v1:intentional-absence",
        ),
    ),
)
"""공개 가능한 고정 사례와 라벨 근거; 버전 변경 없이는 기준 비교를 바꾸지 않는다."""

FIXED_RETRIEVAL_CASES: tuple[RetrievalCase, ...] = tuple(
    RetrievalCase(case.case_id, case.query, case.relevant_document_ids)
    for case in FIXED_GOLDEN_DATASET.cases
    if case.expected_response == "answer"
)
"""검색 지표의 양성 정답 사례만 선택한 고정 부분집합; no-answer는 별도 정확도로 평가한다."""

FIXED_RETRIEVAL_RESULTS_AT_3: Mapping[str, Sequence[str]] = {
    "access-reset": ("identity-access", "service-overview", "security-incident"),
    "expense-receipt": ("people-benefits", "finance-expense", "service-overview"),
    "incident-response": ("operations-runbook", "security-incident", "identity-access"),
    "benefits-enrollment": ("finance-expense", "service-overview", "identity-access"),
}
"""동일한 구현에서 기록한 고정 Top-3 결과; 지표 설명과 회귀 테스트에 사용한다."""


FIXED_ANSWER_CASES: tuple[AnswerCase, ...] = (
    AnswerCase(
        case_id="access-reset",
        expected_response="answer",
        supported_fact_ids=("reset-identity-verification",),
        allowed_citation_document_ids=("identity-access",),
    ),
    AnswerCase(
        case_id="expense-receipt",
        expected_response="answer",
        supported_fact_ids=("submit-itemized-receipt",),
        allowed_citation_document_ids=("finance-expense",),
    ),
    AnswerCase(
        case_id="incident-response",
        expected_response="answer",
        supported_fact_ids=("report-suspicious-login", "follow-initial-response-runbook"),
        allowed_citation_document_ids=("security-incident", "operations-runbook"),
    ),
    AnswerCase(
        case_id="benefits-enrollment",
        expected_response="answer",
        supported_fact_ids=("follow-benefits-enrollment-window",),
        allowed_citation_document_ids=("people-benefits",),
    ),
    AnswerCase(
        case_id="office-parking",
        expected_response="abstain",
        supported_fact_ids=(),
        allowed_citation_document_ids=(),
    ),
)
"""고정 골든 사례에서 유도한 답변 행동·사실·인용의 공개 라벨 계약이다."""


FIXED_RECORDED_ANSWERS: Mapping[str, RecordedAnswer] = {
    "access-reset": RecordedAnswer(
        case_id="access-reset",
        response_mode="answer",
        asserted_fact_ids=("reset-identity-verification",),
        cited_document_ids=("identity-access",),
    ),
    "expense-receipt": RecordedAnswer(
        case_id="expense-receipt",
        response_mode="answer",
        asserted_fact_ids=("submit-itemized-receipt",),
        cited_document_ids=("finance-expense",),
    ),
    "incident-response": RecordedAnswer(
        case_id="incident-response",
        response_mode="answer",
        asserted_fact_ids=("report-suspicious-login", "follow-initial-response-runbook"),
        cited_document_ids=("security-incident", "operations-runbook"),
    ),
    "benefits-enrollment": RecordedAnswer(
        case_id="benefits-enrollment",
        response_mode="answer",
        asserted_fact_ids=("follow-benefits-enrollment-window",),
        cited_document_ids=("identity-access",),
    ),
    "office-parking": RecordedAnswer(
        case_id="office-parking",
        response_mode="answer",
        asserted_fact_ids=("parking-pass-application-is-available",),
        cited_document_ids=("service-overview",),
    ),
}
"""교육용으로 기록한 고정 답변; 보류 실패와 부정확한 인용을 의도적으로 포함한다."""


FIXED_WORKFLOW_CASES: tuple[WorkflowCase, ...] = (
    WorkflowCase(
        case_id="access-reset",
        expected_route="identity",
        expected_response="answer",
        required_task_ids=("verify-identity-and-reset-access",),
    ),
    WorkflowCase(
        case_id="expense-receipt",
        expected_route="finance",
        expected_response="answer",
        required_task_ids=("provide-itemized-receipt-submission-rule",),
    ),
    WorkflowCase(
        case_id="incident-response",
        expected_route="security",
        expected_response="answer",
        required_task_ids=("report-suspicious-login", "start-initial-response-runbook"),
    ),
    WorkflowCase(
        case_id="benefits-enrollment",
        expected_route="people",
        expected_response="answer",
        required_task_ids=("provide-enrollment-window-and-application-flow",),
    ),
    WorkflowCase(
        case_id="office-parking",
        expected_route="abstain",
        expected_response="abstain",
        required_task_ids=(),
    ),
)
"""골든 사례와 같은 ID를 쓰는 고정 Router 선택·Agent 필수 작업 계약이다."""


FIXED_RECORDED_WORKFLOWS: Mapping[str, RecordedWorkflow] = {
    "access-reset": RecordedWorkflow(
        case_id="access-reset",
        selected_route="identity",
        response_mode="answer",
        completed_task_ids=("verify-identity-and-reset-access",),
    ),
    "expense-receipt": RecordedWorkflow(
        case_id="expense-receipt",
        selected_route="finance",
        response_mode="answer",
        completed_task_ids=("provide-itemized-receipt-submission-rule",),
    ),
    "incident-response": RecordedWorkflow(
        case_id="incident-response",
        selected_route="security",
        response_mode="answer",
        completed_task_ids=("report-suspicious-login", "start-initial-response-runbook"),
    ),
    "benefits-enrollment": RecordedWorkflow(
        case_id="benefits-enrollment",
        selected_route="people",
        response_mode="answer",
        completed_task_ids=(),
    ),
    "office-parking": RecordedWorkflow(
        case_id="office-parking",
        selected_route="facilities",
        response_mode="answer",
        completed_task_ids=("issue-parking-pass",),
    ),
}
"""교육용 고정 실행 기록; 미완료 작업과 no-answer 라우팅·행동 실패를 포함한다."""


FIXED_USAGE_CASES: tuple[UsageCase, ...] = tuple(
    UsageCase(case.case_id) for case in FIXED_GOLDEN_DATASET.cases
)
"""골든 데이터셋과 동일한 ID를 쓰는 고정 사용량 평가 사례다."""


FIXED_TOKEN_PRICING = TokenPricing(
    input_micro_usd_per_token=2,
    output_micro_usd_per_token=8,
)
"""교육용 고정 단가; 입력·출력 토큰당 각각 2·8 마이크로 USD다."""


FIXED_RECORDED_USAGE: Mapping[str, RecordedUsage] = {
    "access-reset": RecordedUsage("access-reset", 120, 140, 90),
    "expense-receipt": RecordedUsage("expense-receipt", 210, 180, 110),
    "incident-response": RecordedUsage("incident-response", 180, 220, 130),
    "benefits-enrollment": RecordedUsage("benefits-enrollment", 340, 160, 100),
    "office-parking": RecordedUsage("office-parking", 70, 80, 30),
}
"""라이브 시계·모델 SDK 없이 검토하는 고정 latency(ms)·입출력 토큰 기록이다."""
