"""Volume 10의 첫 장과 결정론적 검색 평가 산출물의 연결을 검사한다."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOLUME = ROOT / "docs" / "volume10-evaluation"


def test_volume10_first_chapter_connects_fixed_dataset_to_verified_artifacts() -> None:
    """학습 목표 장은 PRD 장 구조와 실제 오프라인 평가 경로를 제공해야 한다."""
    chapter = (VOLUME / "01-learning-objectives.md").read_text(encoding="utf-8")
    readme = (VOLUME / "README.md").read_text(encoding="utf-8")

    required_sections = (
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
    expected_artifacts = (
        ROOT / "src" / "ai_platform" / "evaluation" / "datasets.py",
        ROOT / "src" / "ai_platform" / "evaluation" / "retrieval_metrics.py",
        ROOT / "examples" / "volume10" / "retrieval_quality.py",
        ROOT / "tests" / "evaluation" / "test_retrieval_metrics.py",
    )

    assert all(section in chapter for section in required_sections)
    assert "uv run python examples/volume10/retrieval_quality.py" in chapter
    assert "uv run pytest tests/evaluation/test_retrieval_metrics.py -q" in chapter
    assert "네트워크와 API 키를 사용하지 않습니다" in chapter
    assert "Recall@3: 0.750000" in chapter
    assert all(artifact.is_file() for artifact in expected_artifacts)
    assert "](01-learning-objectives.md)" in readme
    assert "](PROGRESS.md)" in readme
