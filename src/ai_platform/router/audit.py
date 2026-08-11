"""원문을 보관하지 않는 Router 감사 record의 경계를 검증한다."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Final

from ai_platform.router.base import RoutingConfigurationError


class UnsafeRouterAuditRecordError(RoutingConfigurationError):
    """Router 감사 record가 허용되지 않은 필드나 민감한 값을 포함할 때 발생한다."""


_SAFE_AUDIT_FIELD_NAMES: Final = frozenset(
    {
        "api",
        "attempted_policy_names",
        "attempted_stage_names",
        "body",
        "classifier_confidence",
        "classifier_name",
        "confidence",
        "decision",
        "error_code",
        "escalation_count",
        "estimated_cost",
        "estimated_latency_ms",
        "fallback_count",
        "fallback_router_name",
        "intent",
        "llm_classifier_confidence",
        "matched_keywords",
        "multi_stage_router_name",
        "outcome",
        "policy_name",
        "reason",
        "request_id",
        "rule_name",
        "rule_router_name",
        "semantic_similarity",
        "stage_name",
        "stage_target_kind",
        "status_code",
        "target_kind",
        "target_name",
    }
)


def validate_router_audit_record(
    record: Mapping[str, object], *, sensitive_values: Iterable[str] = ()
) -> None:
    """감사 record가 JSON 가능 allowlist이고 원문을 포함하지 않는지 검증한다.

    ``sensitive_values``에는 이 결정에 사용한 사용자 원문처럼 출력에 다시 나타나면
    안 되는 값을 전달한다. 빈 값은 검색 범위가 모호하므로 허용하지 않는다.
    """
    if not isinstance(record, Mapping):
        raise UnsafeRouterAuditRecordError("router audit record must be a mapping")
    normalized_sensitive_values = _normalize_sensitive_values(sensitive_values)
    _validate_mapping(record, normalized_sensitive_values)
    try:
        json.dumps(record, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise UnsafeRouterAuditRecordError(
            "router audit record must be strict JSON serializable"
        ) from error


def _normalize_sensitive_values(sensitive_values: Iterable[str]) -> tuple[str, ...]:
    """원문 누락·중복 없이 비교할 수 있는 값 집합을 만든다."""
    if isinstance(sensitive_values, str):
        raise UnsafeRouterAuditRecordError("sensitive audit values must be an iterable of strings")
    try:
        values = tuple(sensitive_values)
    except TypeError as error:
        raise UnsafeRouterAuditRecordError(
            "sensitive audit values must be an iterable of strings"
        ) from error
    for value in values:
        if not isinstance(value, str) or not value:
            raise UnsafeRouterAuditRecordError("sensitive audit values must be nonempty strings")
    if len(values) != len(set(values)):
        raise UnsafeRouterAuditRecordError("sensitive audit values must be unique")
    return values


def _validate_mapping(record: Mapping[str, object], sensitive_values: tuple[str, ...]) -> None:
    """중첩 dict를 포함해 field allowlist와 각 JSON 값을 확인한다."""
    for key, value in record.items():
        if not isinstance(key, str) or key not in _SAFE_AUDIT_FIELD_NAMES:
            raise UnsafeRouterAuditRecordError("router audit record contains an unsafe field")
        _validate_value(value, sensitive_values)


def _validate_value(value: object, sensitive_values: tuple[str, ...]) -> None:
    """재귀적으로 JSON 기본형과 민감한 문자열 비노출을 확인한다."""
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if any(sensitive_value in value for sensitive_value in sensitive_values):
            raise UnsafeRouterAuditRecordError("router audit record contains a sensitive value")
        return
    if isinstance(value, Mapping):
        _validate_mapping(value, sensitive_values)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_value(item, sensitive_values)
        return
    raise UnsafeRouterAuditRecordError("router audit record contains a non-JSON value")
