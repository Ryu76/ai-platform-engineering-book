"""Volume 10의 작성 완료 장과 결정론적 평가 산출물 연결을 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume10-evaluation"

REQUIRED_SECTIONS = (
    "## 1. 학습 목표",
    "## 2. 왜 필요한가",
    "## 3. 핵심 개념",
    "## 4. 동작 구조",
    "## 5. 실습 환경",
    "## 6. 단계별 실습",
    "## 7. 코드 설명",
    "## 8. 정상 실행 결과",
    "## 9. 오류 해결",
    "## 10. 응용 실습",
    "## 11. 실무 적용",
    "## 12. 과제",
    "## 13. 완료 체크리스트",
    "## 14. 핵심 정리",
)


def test_volume10_first_chapter_connects_fixed_dataset_to_verified_artifacts() -> None:
    """첫 장은 PRD 장 구조와 실제 오프라인 검색 평가 경로를 제공해야 한다."""
    chapter = (VOLUME / "01-learning-objectives.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")
    expected_artifacts = (
        ROOT / "src" / "ai_platform" / "evaluation" / "datasets.py",
        ROOT / "src" / "ai_platform" / "evaluation" / "retrieval_metrics.py",
        ROOT / "examples" / "volume10" / "retrieval_quality.py",
        ROOT / "tests" / "evaluation" / "test_retrieval_metrics.py",
    )

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "uv run python examples/volume10/retrieval_quality.py" in chapter
    assert "uv run pytest tests/evaluation/test_retrieval_metrics.py -q" in chapter
    assert "네트워크와 API 키를 사용하지 않습니다" in chapter
    assert "Recall@3: 0.750000" in chapter
    assert all(artifact.is_file() for artifact in expected_artifacts)
    assert "](01-learning-objectives.md)" in readme
    assert "](PROGRESS.md)" in readme


def test_volume10_second_chapter_connects_versioned_labels_to_verified_artifacts() -> None:
    """골든 데이터셋 장은 라벨·no-answer·버전 계약과 로컬 실행 경로를 제공해야 한다."""
    chapter = (VOLUME / "02-golden-dataset.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")
    expected_artifacts = (
        ROOT / "src" / "ai_platform" / "evaluation" / "golden_dataset.py",
        ROOT / "src" / "ai_platform" / "evaluation" / "datasets.py",
        ROOT / "examples" / "volume10" / "golden_dataset_audit.py",
        ROOT / "tests" / "evaluation" / "test_golden_dataset.py",
    )

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "uv run python examples/volume10/golden_dataset_audit.py" in chapter
    assert "uv run pytest tests/evaluation/test_golden_dataset.py -q" in chapter
    assert "no-answer" in chapter
    assert "Version: 1.0.0" in chapter
    assert "네트워크, 시계, 난수에 의존하지 않습니다" in chapter
    assert all(artifact.is_file() for artifact in expected_artifacts)
    assert "](02-golden-dataset.md)" in readme


def test_volume10_third_chapter_connects_failure_analysis_to_verified_artifacts() -> None:
    """검색 품질 장은 사례별 실패 분석과 결정론적 실행 경로를 제공해야 한다."""
    chapter = (VOLUME / "03-retrieval-quality.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")
    expected_artifacts = (
        ROOT / "src" / "ai_platform" / "evaluation" / "retrieval_metrics.py",
        ROOT / "examples" / "volume10" / "retrieval_failure_analysis.py",
        ROOT / "tests" / "evaluation" / "test_retrieval_metrics.py",
    )

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "uv run python examples/volume10/retrieval_failure_analysis.py" in chapter
    assert "uv run pytest tests/evaluation/test_retrieval_metrics.py -q" in chapter
    assert "benefits-enrollment" in chapter
    assert "first_rank=none" in chapter
    assert "네트워크, 시계, 난수, 라이브 모델 상태에 의존하지 않습니다" in chapter
    assert all(artifact.is_file() for artifact in expected_artifacts)
    assert "](03-retrieval-quality.md)" in readme


def test_volume10_fourth_chapter_connects_answer_quality_to_verified_artifacts() -> None:
    """답변 품질 장은 보류·환각·인용의 고정 평가와 로컬 실행 경로를 제공해야 한다."""
    chapter = (VOLUME / "04-answer-quality.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")
    expected_artifacts = (
        ROOT / "src" / "ai_platform" / "evaluation" / "answer_metrics.py",
        ROOT / "src" / "ai_platform" / "evaluation" / "datasets.py",
        ROOT / "examples" / "volume10" / "answer_quality.py",
        ROOT / "tests" / "evaluation" / "test_answer_metrics.py",
    )

    assert all(section in chapter for section in REQUIRED_SECTIONS)
    assert "uv run python examples/volume10/answer_quality.py" in chapter
    assert "uv run pytest tests/evaluation/test_answer_metrics.py -q" in chapter
    assert "office-parking" in chapter
    assert "Hallucination rate: 0.166667" in chapter
    assert (
        "LLM API · LLM-as-a-Judge · Vector DB · 네트워크 · 시계 · 난수 ── 사용하지 않음"
        in chapter
    )
    assert all(artifact.is_file() for artifact in expected_artifacts)
    assert "](04-answer-quality.md)" in readme
