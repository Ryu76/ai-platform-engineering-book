"""로컬 Markdown 입력을 검증하고 RAG용 출처 문서로 정제한다.

이 모듈은 네트워크, PDF 파서, 외부 저장소를 사용하지 않는다. 호출자가 허용한
로컬 루트 아래의 UTF-8 Markdown 파일만 읽고, 원문을 외부로 전송하지 않는다.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import quote

from ai_platform.rag.retrieval import RagConfigurationError, SourceDocument


class LocalMarkdownLoader:
    """허용된 루트의 Markdown 파일 하나를 재현 가능한 ``SourceDocument``로 읽는다."""

    def __init__(self, *, root: Path, source_uri_prefix: str = "local://volume05") -> None:
        """입력 루트와 출처 URI 접두사를 검증한다.

        ``root`` 밖의 경로와 심볼릭 링크를 통해 루트 밖을 가리키는 경로는 ``load``에서
        거부한다. 따라서 실습에서 의도하지 않은 로컬 파일을 읽지 않는다.
        """
        if not isinstance(root, Path):
            raise RagConfigurationError("root must be a pathlib.Path")
        if not root.is_dir():
            raise RagConfigurationError("root must be an existing directory")
        if not source_uri_prefix.strip():
            raise RagConfigurationError("source_uri_prefix must not be empty")
        self._root = root.resolve()
        self._source_uri_prefix = source_uri_prefix.rstrip("/")

    def load(self, relative_path: Path) -> SourceDocument:
        """상대 Markdown 경로를 읽어 정제된 본문과 안전한 메타데이터를 반환한다."""
        if not isinstance(relative_path, Path):
            raise RagConfigurationError("relative_path must be a pathlib.Path")
        if relative_path.is_absolute() or not relative_path.parts:
            raise RagConfigurationError("relative_path must be a non-empty relative path")
        if relative_path.suffix.casefold() not in {".md", ".markdown"}:
            raise RagConfigurationError("only Markdown files (.md or .markdown) are supported")

        candidate = (self._root / relative_path).resolve()
        if not candidate.is_relative_to(self._root):
            raise RagConfigurationError("relative_path must stay within root")
        if not candidate.is_file():
            raise RagConfigurationError("Markdown file does not exist")
        try:
            raw_content = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise RagConfigurationError("Markdown file must be UTF-8 encoded") from error

        content = clean_markdown(raw_content)
        if not content:
            raise RagConfigurationError("Markdown file has no usable content")
        normalized_relative_path = candidate.relative_to(self._root)
        return SourceDocument(
            document_id=f"local:{normalized_relative_path.as_posix()}",
            title=extract_markdown_title(content, fallback=normalized_relative_path.stem),
            source_uri=(
                f"{self._source_uri_prefix}/{quote(normalized_relative_path.as_posix(), safe='/')}"
            ),
            content=content,
        )

    def load_many(self, relative_paths: Iterable[Path]) -> tuple[SourceDocument, ...]:
        """명시한 Markdown 파일들을 중복 없이 문서 ID 순서로 읽는다.

        디렉터리를 재귀적으로 탐색하지 않는다. 호출자가 허용할 파일을 명시해야 하므로
        실습 루트에 임시 파일이 추가되어도 의도하지 않은 문서가 색인되지 않는다. 입력
        순서와 관계없이 문서 ID 순으로 반환해 이후 색인과 검색의 순서를 재현할 수 있다.
        """
        try:
            paths = tuple(relative_paths)
        except TypeError as error:
            raise RagConfigurationError(
                "relative_paths must be an iterable of pathlib.Path values"
            ) from error
        if not paths:
            raise RagConfigurationError("at least one Markdown path is required")

        documents = tuple(self.load(relative_path) for relative_path in paths)
        identifiers = [document.document_id for document in documents]
        if len(set(identifiers)) != len(identifiers):
            raise RagConfigurationError("Markdown paths must not resolve to the same document")
        return tuple(sorted(documents, key=lambda document: document.document_id))


def clean_markdown(markdown: str) -> str:
    """줄 끝·빈 줄·수평 공백을 정규화해 결정론적인 검색 입력을 만든다.

    줄바꿈은 보존하므로 문단 경계와 Markdown 제목은 유지한다. NUL 문자는 텍스트
    문서에 유효하지 않아 거부하고, BOM·CRLF·반복 공백은 로컬에서만 정제한다.
    """
    if not isinstance(markdown, str):
        raise RagConfigurationError("Markdown content must be text")
    if "\x00" in markdown:
        raise RagConfigurationError("Markdown content must not contain NUL characters")

    normalized = markdown.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[\t ]+", " ", line).rstrip() for line in normalized.split("\n")]
    cleaned_lines: list[str] = []
    previous_was_blank = False
    for line in lines:
        if not line:
            if not previous_was_blank and cleaned_lines:
                cleaned_lines.append("")
            previous_was_blank = True
            continue
        cleaned_lines.append(line)
        previous_was_blank = False
    return "\n".join(cleaned_lines).strip()


def extract_markdown_title(content: str, *, fallback: str) -> str:
    """첫 ATX 제목을 우선 사용하고, 없으면 정제된 파일명을 제목으로 사용한다."""
    for line in content.splitlines():
        match = re.fullmatch(r" {0,3}#{1,6} +(.*?)(?: +#*)?", line)
        if match and match.group(1).strip():
            return _clean_title(match.group(1))
    return _clean_title(fallback.replace("_", " ").replace("-", " "))


def _clean_title(value: str) -> str:
    """제목 메타데이터의 공백을 한 칸으로 줄이고 빈 값은 거부한다."""
    title = " ".join(value.split())
    if not title:
        raise RagConfigurationError("document title must not be empty")
    return title
