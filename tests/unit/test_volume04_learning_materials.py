"""Volume 04 학습 자료의 링크와 completion/handoff 구조를 검증한다."""
from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS_DIRECTORY = REPOSITORY_ROOT / "docs" / "volume04-embedding-vector-db"
CHAPTER_FILENAMES = (
    "01-learning-objectives.md",
    "02-local-collection-payload-search.md",
    "03-retrieval-quality-no-answer.md",
    "04-reindex-lifecycle-mini-project.md",
    "05-vector-db-migration-contracts.md",
    "06-completion-checklist-rag-handoff.md",
)


def test_volume04_chapters_have_all_learning_sections() -> None:
    """각 Volume 04 장은 재현 가능한 14개 학습 섹션을 제공해야 한다."""
    expected_sections = [f"## {number}." for number in range(1, 15)]

    for filename in CHAPTER_FILENAMES:
        chapter = (DOCUMENTS_DIRECTORY / filename).read_text(encoding="utf-8")
        actual_sections = re.findall(r"^## (\d+)\. ", chapter, flags=re.MULTILINE)

        assert actual_sections == [str(number) for number in range(1, 15)]
        for section in expected_sections:
            assert section in chapter


def test_readme_links_all_chapters_examples_and_volume04_tests() -> None:
    """빠른 시작과 장 목록이 이 권의 결정적 결과물을 가리켜야 한다."""
    readme = (DOCUMENTS_DIRECTORY / "README.md").read_text(encoding="utf-8")

    for filename in CHAPTER_FILENAMES:
        assert filename in readme
    for example_name in (
        "embedding_similarity.py",
        "vector_store_search.py",
        "retrieval_quality.py",
        "reindex_lifecycle.py",
    ):
        assert (REPOSITORY_ROOT / "examples" / "volume04" / example_name).is_file()
        assert f"examples/volume04/{example_name}" in readme
    for test_name in (
        "test_volume04_embedding_service.py",
        "test_volume04_vector_store.py",
        "test_volume04_retrieval_evaluation.py",
        "test_volume04_reindex_lifecycle.py",
        "test_volume04_learning_materials.py",
    ):
        assert (REPOSITORY_ROOT / "tests" / "unit" / test_name).is_file()
        assert test_name in readme


def test_completion_handoff_keeps_unverified_database_work_explicit() -> None:
    """실제 Qdrant 증거 전에는 완료 표식과 cron pause를 주장하면 안 된다."""
    handoff = (DOCUMENTS_DIRECTORY / "06-completion-checklist-rag-handoff.md").read_text(
        encoding="utf-8"
    )
    progress = (DOCUMENTS_DIRECTORY / "PROGRESS.md").read_text(encoding="utf-8")

    assert "- [ ] pinned Qdrant image" in handoff
    assert "현재는 6절이 미완료이므로 완료 표식을 추가하거나 cron을 pause하지 않습니다." in handoff
    assert "- 완료 표식: `VOLUME04_COMPLETE` 미설정" in progress
