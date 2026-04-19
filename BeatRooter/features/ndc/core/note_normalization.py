from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from typing import Any

from features.beatnote.core.beatnote_model import BeatNote


@dataclass(frozen=True)
class NormalizedNoteRecord:
    note_id: str
    project_id: str
    note_scope: str
    title: str
    body_markdown_like: str
    body_plaintext: str
    category: str
    tags: tuple[str, ...]
    source_ref: str
    linked_node_id: str | None
    created_at: str
    updated_at: str
    chronology_key: str


@dataclass(frozen=True)
class NormalizedNoteChunk:
    chunk_id: str
    note_id: str
    chunk_index: int
    text: str
    char_count: int
    metadata: dict[str, Any]


@dataclass(frozen=True)
class NormalizedNoteBundle:
    record: NormalizedNoteRecord
    chunks: tuple[NormalizedNoteChunk, ...]


def build_normalized_note_bundle(
    note: BeatNote,
    context: dict[str, Any],
    *,
    max_chars: int = 900,
) -> NormalizedNoteBundle:
    plaintext = html_to_plaintext(note.content)
    record = NormalizedNoteRecord(
        note_id=note.id,
        project_id=str(context.get("project_id") or "").strip() or "beatnote-standalone",
        note_scope=str(context.get("note_scope") or "").strip() or "standalone",
        title=note.title,
        body_markdown_like=plaintext,
        body_plaintext=plaintext,
        category=note.category,
        tags=tuple(note.tags),
        source_ref=str(context.get("source_ref") or "").strip() or "beatnote_service",
        linked_node_id=str(context.get("linked_node_id") or "").strip() or None,
        created_at=note.createdAt,
        updated_at=note.updatedAt,
        chronology_key=f"{note.updatedAt}:{note.id}",
    )
    chunks = tuple(chunk_note_record(record, max_chars=max_chars))
    return NormalizedNoteBundle(record=record, chunks=chunks)


def chunk_note_record(record: NormalizedNoteRecord, *, max_chars: int = 900) -> list[NormalizedNoteChunk]:
    text = record.body_plaintext.strip()
    if not text:
        text = record.title.strip()

    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()] or [text]
    chunks: list[NormalizedNoteChunk] = []
    current_parts: list[str] = []
    current_len = 0

    def flush_chunk():
        nonlocal current_parts, current_len
        if not current_parts:
            return
        chunk_index = len(chunks)
        chunk_text = "\n\n".join(current_parts).strip()
        chunks.append(
            NormalizedNoteChunk(
                chunk_id=f"{record.note_id}:chunk:{chunk_index}",
                note_id=record.note_id,
                chunk_index=chunk_index,
                text=chunk_text,
                char_count=len(chunk_text),
                metadata={
                    "project_id": record.project_id,
                    "note_scope": record.note_scope,
                    "category": record.category,
                    "tags": list(record.tags),
                    "source_ref": record.source_ref,
                    "linked_node_id": record.linked_node_id,
                    "updated_at": record.updated_at,
                },
            )
        )
        current_parts = []
        current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph)
        if current_parts and current_len + 2 + paragraph_len > max_chars:
            flush_chunk()

        if paragraph_len > max_chars:
            for piece in _split_long_text(paragraph, max_chars=max_chars):
                if current_parts:
                    flush_chunk()
                current_parts = [piece]
                current_len = len(piece)
                flush_chunk()
            continue

        current_parts.append(paragraph)
        current_len = len("\n\n".join(current_parts))

    flush_chunk()
    return chunks


def html_to_plaintext(raw_html: str) -> str:
    text = str(raw_html or "")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p\s*>", "\n\n", text)
    text = re.sub(r"(?i)</li\s*>", "\n", text)
    text = re.sub(r"(?i)<li\s*>", "- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_long_text(text: str, *, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return [text[:max_chars]]

    parts: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            parts.append(current)
            current = word
        else:
            parts.append(word[:max_chars])
            current = word[max_chars:]
    if current:
        parts.append(current)
    return parts
