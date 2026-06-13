"""Structural chunking for legal documents."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    article_ref: str
    text: str
    chunk_index: int


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def chunk_by_section(text: str, label: str = "Section") -> list[TextChunk]:
    pattern = re.compile(rf"(?=^{label} \d+\s*$)", re.MULTILINE)
    parts = pattern.split(text)
    chunks: list[TextChunk] = []
    index = 0
    for part in parts:
        part = part.strip()
        if len(part) < 100:
            continue
        match = re.match(rf"^{label} (\d+)", part)
        ref = f"{label} {match.group(1)}" if match else f"{label} block {index + 1}"
        chunks.append(TextChunk(article_ref=ref, text=part, chunk_index=index))
        index += 1
    return chunks


def chunk_by_article(text: str) -> list[TextChunk]:
    return chunk_by_section(text, label="Article")


def chunk_by_paragraph(text: str) -> list[TextChunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) >= 80]
    return [
        TextChunk(article_ref=f"Paragraph {i + 1}", text=para, chunk_index=i)
        for i, para in enumerate(paragraphs)
    ]


def chunk_guide_subsections(text: str, max_chunks: int = 30) -> list[TextChunk]:
    # Skip table of contents — substantive guide content starts around part I.
    start = text.find("I.  General principles and applicability")
    if start == -1:
        start = 5000
    body = text[start:]

    pattern = re.compile(r"(?=^[A-Z]\.\s+[A-Z])", re.MULTILINE)
    parts = pattern.split(body)
    chunks: list[TextChunk] = []
    index = 0
    for part in parts:
        part = part.strip()
        if len(part) < 150:
            continue
        match = re.match(r"^([A-Z]\.\s+[^\n]+)", part)
        ref = match.group(1).strip() if match else f"Subsection {index + 1}"
        ref = re.sub(r"\s+\.{3,}.*$", "", ref)
        chunks.append(TextChunk(article_ref=ref, text=part[:4000], chunk_index=index))
        index += 1
        if len(chunks) >= max_chunks:
            break
    return chunks


def chunk_document(text: str, strategy: str, max_chunks: int | None = None) -> list[TextChunk]:
    if strategy == "section":
        chunks = chunk_by_section(text)
    elif strategy == "article":
        chunks = chunk_by_article(text)
    elif strategy == "paragraph":
        chunks = chunk_by_paragraph(text)
    elif strategy == "guide_subsection":
        chunks = chunk_guide_subsections(text, max_chunks=max_chunks or 30)
    else:
        chunks = chunk_by_paragraph(text)

    if max_chunks is not None:
        chunks = chunks[:max_chunks]
    return chunks
