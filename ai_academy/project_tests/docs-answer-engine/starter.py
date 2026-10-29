"""Starter contract for the Docs Answer Engine project."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    index: int


def chunk_document(text: str, source: str, size: int = 200, overlap: int = 40) -> list[Chunk]:
    """Split a document into overlapping chunks.

    Every non-empty chunk needs a source and an index. The final chunk must
    include the end of the document.
    """
    raise NotImplementedError("Implement structure-aware chunking")


def retrieve(query: str, chunks: list[Chunk], k: int = 3) -> list[Chunk]:
    """Return the k most relevant chunks for a query.

    A lexical baseline is enough for this test: rank by keyword overlap.
    """
    raise NotImplementedError("Implement retrieval")


def validate_citations(citations: list[int], chunks: list[Chunk]) -> bool:
    """Return True only when every citation is a valid chunk index."""
    raise NotImplementedError("Validate citation indexes")


def answer_with_citations(question: str, chunks: list[Chunk], llm=None) -> dict:
    """Return ``{"answer": str, "citations": list[int]}``.

    If no chunk is relevant, return an empty answer and no citations. If an
    ``llm`` callable is supplied, use it to draft the answer; otherwise use a
    deterministic extractive fallback.
    """
    raise NotImplementedError("Implement grounded answering")
