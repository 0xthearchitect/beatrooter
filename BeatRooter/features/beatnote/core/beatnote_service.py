from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from PyQt6.QtCore import QSettings

from features.beatnote.core.beatnote_model import (
    BEATNOTE_CATEGORIES,
    BEATNOTE_CATEGORY_STORAGE_KEY,
    BEATNOTE_CONTEXT_STORAGE_KEY,
    BEATNOTE_STORAGE_KEY,
    BeatNote,
    BeatNoteValidationError,
    category_label,
    deserialize_note,
    normalize_category,
    ordered_categories,
    sort_beatnotes,
    validate_note_input,
)
from features.ndc.core.integration import get_default_ndc_runtime
from features.ndc.core.runtime import NDCClientRuntime
from features.ndc.core.schema import NotePayload


class BeatNoteServiceError(RuntimeError):
    """Raised when BeatNote persistence fails."""


class BeatNoteNotFoundError(BeatNoteServiceError):
    """Raised when an operation targets an unknown BeatNote id."""


class BeatNoteService:
    def __init__(
        self,
        *,
        settings: Any | None = None,
        storage_key: str = BEATNOTE_STORAGE_KEY,
        category_storage_key: str = BEATNOTE_CATEGORY_STORAGE_KEY,
        note_context_storage_key: str = BEATNOTE_CONTEXT_STORAGE_KEY,
        uuid_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
        ndc_runtime: NDCClientRuntime | None = None,
        ndc_context_provider: Callable[[], dict[str, Any] | None] | None = None,
    ) -> None:
        self.settings = settings or QSettings("BeatRooter", "BeatRooter")
        self.storage_key = storage_key
        self.category_storage_key = category_storage_key
        self.note_context_storage_key = note_context_storage_key
        self.uuid_factory = uuid_factory or (lambda: str(uuid4()))
        self.now_factory = now_factory or (lambda: datetime.now(timezone.utc))
        self.ndc_runtime = ndc_runtime or get_default_ndc_runtime()
        self.ndc_context_provider = ndc_context_provider or self._default_ndc_context

    def list(self) -> list[BeatNote]:
        return sort_beatnotes(self._read_notes())

    def list_categories(self) -> list[str]:
        note_categories = [note.category for note in self._read_notes()]
        custom_categories = self._read_categories()
        return ordered_categories((*BEATNOTE_CATEGORIES, *custom_categories, *note_categories))

    def create_category(self, raw_category: Any) -> str:
        category = normalize_category(raw_category)
        existing = self.list_categories()

        if any(
            existing_category.casefold() == category.casefold()
            or category_label(existing_category).casefold() == category.casefold()
            for existing_category in existing
        ):
            raise BeatNoteServiceError(f"Category '{category_label(category)}' already exists.")

        custom_categories = self._read_categories()
        custom_categories.append(category)
        self._write_categories(ordered_categories(custom_categories))
        return category

    def rename_category(self, old_category: Any, new_category: Any) -> str:
        source = normalize_category(old_category)
        target = normalize_category(new_category)

        if source in BEATNOTE_CATEGORIES:
            raise BeatNoteServiceError("Built-in categories cannot be renamed.")
        if source.casefold() == target.casefold():
            return source

        existing = self.list_categories()
        if any(
            existing_category.casefold() == target.casefold()
            or category_label(existing_category).casefold() == target.casefold()
            for existing_category in existing
        ):
            raise BeatNoteServiceError(f"Category '{category_label(target)}' already exists.")

        notes = self._read_notes()
        updated_notes: list[BeatNote] = []
        for note in notes:
            if note.category.casefold() == source.casefold():
                updated_notes.append(
                    BeatNote(
                        id=note.id,
                        title=note.title,
                        content=note.content,
                        category=target,
                        tags=note.tags,
                        pinned=note.pinned,
                        icon=note.icon,
                        color=note.color,
                        createdAt=note.createdAt,
                        updatedAt=self._timestamp_now(),
                    )
                )
            else:
                updated_notes.append(note)

        custom_categories = [
            target if category.casefold() == source.casefold() else category
            for category in self._read_categories()
        ]
        self._write_notes(updated_notes)
        self._write_categories(ordered_categories(custom_categories))
        return target

    def delete_category(self, raw_category: Any, *, replacement_category: Any) -> str:
        category = normalize_category(raw_category)
        replacement = normalize_category(replacement_category)

        if category in BEATNOTE_CATEGORIES:
            raise BeatNoteServiceError("Built-in categories cannot be deleted.")
        if category.casefold() == replacement.casefold():
            raise BeatNoteServiceError("Replacement category must be different.")

        custom_categories = self._read_categories()
        if not any(existing.casefold() == category.casefold() for existing in custom_categories):
            raise BeatNoteServiceError(f"Category '{category_label(category)}' was not found.")

        notes = self._read_notes()
        updated_notes: list[BeatNote] = []
        for note in notes:
            if note.category.casefold() == category.casefold():
                updated_notes.append(
                    BeatNote(
                        id=note.id,
                        title=note.title,
                        content=note.content,
                        category=replacement,
                        tags=note.tags,
                        pinned=note.pinned,
                        icon=note.icon,
                        color=note.color,
                        createdAt=note.createdAt,
                        updatedAt=self._timestamp_now(),
                    )
                )
            else:
                updated_notes.append(note)

        remaining_categories = [
            existing for existing in custom_categories if existing.casefold() != category.casefold()
        ]
        self._write_notes(updated_notes)
        self._write_categories(ordered_categories(remaining_categories))
        return replacement

    def create(self, payload: dict[str, Any]) -> BeatNote:
        normalized = validate_note_input(payload)
        now = self._timestamp_now()
        note = BeatNote(
            id=self.uuid_factory(),
            title=normalized["title"],
            content=normalized["content"],
            category=normalized["category"],
            tags=normalized["tags"],
            pinned=normalized["pinned"],
            icon=normalized["icon"],
            color=normalized["color"],
            createdAt=now,
            updatedAt=now,
        )
        notes = self._read_notes()
        notes.append(note)
        self._write_notes(notes)
        self._persist_note_context(note.id, self.ndc_context_provider() or self._default_ndc_context())
        self._emit_ndc_note_event("created", note)
        return note

    def update(self, note_id: str, patch: dict[str, Any]) -> BeatNote:
        notes = self._read_notes()
        now = self._timestamp_now()

        for index, note in enumerate(notes):
            if note.id != note_id:
                continue
            previous_tags = list(note.tags)
            merged = {
                "id": note.id,
                "title": patch.get("title", note.title),
                "content": patch.get("content", note.content),
                "category": patch.get("category", note.category),
                "tags": patch.get("tags", note.tags),
                "pinned": patch.get("pinned", note.pinned),
                "icon": patch.get("icon", note.icon),
                "color": patch.get("color", note.color),
                "createdAt": note.createdAt,
                "updatedAt": now,
            }
            normalized = deserialize_note(merged)
            notes[index] = normalized
            self._write_notes(notes)
            self._persist_note_context(
                note.id,
                self._merged_note_context(
                    self._resolve_note_context(note.id),
                    self.ndc_context_provider() or {},
                ),
            )
            self._emit_ndc_note_event("updated", normalized)
            if previous_tags != list(normalized.tags):
                self._emit_ndc_note_event("tags_changed", normalized)
            return normalized

        raise BeatNoteNotFoundError(f"BeatNote '{note_id}' was not found.")

    def delete(self, note_id: str) -> BeatNote:
        notes = self._read_notes()
        for index, note in enumerate(notes):
            if note.id == note_id:
                deleted_note = notes.pop(index)
                self._write_notes(notes)
                self._emit_ndc_note_event("deleted", deleted_note)
                self._remove_note_context(note_id)
                return deleted_note
        raise BeatNoteNotFoundError(f"BeatNote '{note_id}' was not found.")

    def duplicate(self, note_id: str) -> BeatNote:
        notes = self._read_notes()
        for note in notes:
            if note.id != note_id:
                continue
            duplicate_title = f"{note.title} copy"
            return self.create(
                {
                    "title": duplicate_title,
                    "content": note.content,
                    "category": note.category,
                    "tags": note.tags,
                    "pinned": note.pinned,
                    "icon": note.icon,
                    "color": note.color,
                }
            )
        raise BeatNoteNotFoundError(f"BeatNote '{note_id}' was not found.")

    def export_notes(self) -> list[dict[str, Any]]:
        return [note.to_dict() for note in self.list()]

    def import_notes(self, raw_notes: list[dict[str, Any]], *, replace: bool = True) -> list[BeatNote]:
        if not isinstance(raw_notes, list):
            raise BeatNoteServiceError("Imported BeatNotes payload must be a list.")

        imported: list[BeatNote] = []
        existing_notes = [] if replace else self._read_notes()

        for raw_note in raw_notes:
            if not isinstance(raw_note, dict):
                continue

            note_id = str(raw_note.get("id", "") or "").strip() or self.uuid_factory()
            timestamp = self._timestamp_now()
            candidate = {
                "id": note_id,
                "title": raw_note.get("title", ""),
                "content": raw_note.get("content", ""),
                "category": raw_note.get("category", "idea"),
                "tags": raw_note.get("tags", []),
                "pinned": raw_note.get("pinned", False),
                "icon": raw_note.get("icon", "note"),
                "color": raw_note.get("color", "#2D8CFF"),
                "createdAt": raw_note.get("createdAt", timestamp),
                "updatedAt": raw_note.get("updatedAt", timestamp),
            }
            try:
                imported.append(deserialize_note(candidate))
            except BeatNoteValidationError as exc:
                raise BeatNoteServiceError(f"Invalid BeatNote in imported payload: {exc}") from exc

        notes = imported if replace else existing_notes + imported
        self._write_notes(notes)
        note_contexts = self._read_note_contexts()
        default_context = self.ndc_context_provider() or self._default_ndc_context()
        normalized_contexts = {
            note.id: self._normalized_note_context(default_context)
            for note in notes
        }
        if not replace:
            normalized_contexts = {
                **{note_id: ctx for note_id, ctx in note_contexts.items() if note_id in {note.id for note in existing_notes}},
                **normalized_contexts,
            }
        self._write_note_contexts(normalized_contexts)
        return sort_beatnotes(notes)

    def _timestamp_now(self) -> str:
        return self.now_factory().astimezone(timezone.utc).isoformat()

    def _default_ndc_context(self) -> dict[str, Any]:
        return {
            "project_id": "beatnote-standalone",
            "note_scope": "standalone",
            "source_ref": "beatnote_service",
        }

    def link_note_to_node(
        self,
        note_id: str,
        *,
        project_id: str,
        node_id: str,
        source_ref: str = "beatroot_canvas.node_association",
    ) -> BeatNote:
        note = self._find_note_or_raise(note_id)
        context = {
            "project_id": project_id,
            "note_scope": "node",
            "linked_node_id": node_id,
            "source_ref": source_ref,
        }
        self._persist_note_context(note_id, context)
        self._emit_ndc_note_event("linked", note, context_override=context)
        return note

    def unlink_note_from_node(
        self,
        note_id: str,
        *,
        project_id: str,
        source_ref: str = "beatroot_canvas.node_association",
    ) -> BeatNote:
        note = self._find_note_or_raise(note_id)
        context = {
            "project_id": project_id,
            "note_scope": "project",
            "source_ref": source_ref,
        }
        previous_context = self._resolve_note_context(note_id)
        self._persist_note_context(note_id, context)
        self._emit_ndc_note_event("unlinked", note, context_override=previous_context)
        return note

    def _emit_ndc_note_event(
        self,
        action: str,
        note: BeatNote,
        *,
        context_override: dict[str, Any] | None = None,
    ) -> None:
        context = context_override or self._resolve_note_context(note.id)
        project_id = str(context.get("project_id") or "").strip() or "beatnote-standalone"
        note_scope = str(context.get("note_scope") or "").strip() or "standalone"
        source_ref = str(context.get("source_ref") or "").strip() or "beatnote_service"
        linked_node_id = context.get("linked_node_id")
        note_format = str(context.get("format") or "").strip() or "html"

        payload = NotePayload(
            note_id=note.id,
            title=note.title,
            body=note.content,
            note_scope=note_scope,
            format=note_format,
            category=note.category,
            tags=tuple(note.tags),
            linked_node_id=str(linked_node_id).strip() if linked_node_id else None,
            source_ref=source_ref,
            created_at=note.createdAt,
            updated_at=note.updatedAt,
        )

        try:
            self.ndc_runtime.enqueue_event(
                family="note",
                action=action,
                project_id=project_id,
                payload=payload,
            )
        except Exception:
            return

    def _resolve_note_context(self, note_id: str) -> dict[str, Any]:
        contexts = self._read_note_contexts()
        stored = contexts.get(note_id)
        if stored:
            return stored
        return self._normalized_note_context(self.ndc_context_provider() or self._default_ndc_context())

    def _persist_note_context(self, note_id: str, context: dict[str, Any]) -> None:
        contexts = self._read_note_contexts()
        contexts[note_id] = self._normalized_note_context(context)
        self._write_note_contexts(contexts)

    def _remove_note_context(self, note_id: str) -> None:
        contexts = self._read_note_contexts()
        if note_id in contexts:
            contexts.pop(note_id, None)
            self._write_note_contexts(contexts)

    def _normalized_note_context(self, raw_context: dict[str, Any] | None) -> dict[str, Any]:
        context = dict(raw_context or {})
        normalized = {
            "project_id": str(context.get("project_id") or "").strip() or "beatnote-standalone",
            "note_scope": str(context.get("note_scope") or "").strip() or "standalone",
            "source_ref": str(context.get("source_ref") or "").strip() or "beatnote_service",
        }
        linked_node_id = str(context.get("linked_node_id") or "").strip()
        if linked_node_id:
            normalized["linked_node_id"] = linked_node_id
        return normalized

    def _merged_note_context(
        self,
        existing_context: dict[str, Any] | None,
        new_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        existing = self._normalized_note_context(existing_context)
        incoming = self._normalized_note_context(new_context)

        if existing.get("note_scope") == "node" and not incoming.get("linked_node_id"):
            incoming["note_scope"] = "node"
            incoming["linked_node_id"] = existing.get("linked_node_id")

        if existing.get("linked_node_id") and not incoming.get("linked_node_id"):
            incoming["linked_node_id"] = existing["linked_node_id"]

        if existing.get("source_ref") and incoming.get("source_ref") == "beatnote_service":
            incoming["source_ref"] = existing["source_ref"]

        if existing.get("project_id") and incoming.get("project_id") == "beatnote-standalone":
            incoming["project_id"] = existing["project_id"]

        return incoming

    def _find_note_or_raise(self, note_id: str) -> BeatNote:
        for note in self._read_notes():
            if note.id == note_id:
                return note
        raise BeatNoteNotFoundError(f"BeatNote '{note_id}' was not found.")

    def _read_note_contexts(self) -> dict[str, dict[str, Any]]:
        try:
            raw_payload = self.settings.value(self.note_context_storage_key, "", type=str)
        except TypeError:
            raw_payload = self.settings.value(self.note_context_storage_key, "")
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to read BeatNote contexts: {exc}") from exc

        if not raw_payload:
            return {}

        try:
            decoded = json.loads(raw_payload)
        except json.JSONDecodeError:
            return {}
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to decode BeatNote contexts: {exc}") from exc

        if not isinstance(decoded, dict):
            return {}

        contexts: dict[str, dict[str, Any]] = {}
        for note_id, raw_context in decoded.items():
            clean_note_id = str(note_id or "").strip()
            if not clean_note_id or not isinstance(raw_context, dict):
                continue
            contexts[clean_note_id] = self._normalized_note_context(raw_context)
        return contexts

    def _write_note_contexts(self, contexts: dict[str, dict[str, Any]]) -> None:
        try:
            serialized = json.dumps(contexts, ensure_ascii=False, sort_keys=True)
            self.settings.setValue(self.note_context_storage_key, serialized)
            sync = getattr(self.settings, "sync", None)
            if callable(sync):
                sync()
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to persist BeatNote contexts: {exc}") from exc

    def _read_categories(self) -> list[str]:
        try:
            raw_payload = self.settings.value(self.category_storage_key, "", type=str)
        except TypeError:
            raw_payload = self.settings.value(self.category_storage_key, "")
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to read BeatNote categories: {exc}") from exc

        if not raw_payload:
            return []

        try:
            decoded = json.loads(raw_payload)
        except json.JSONDecodeError:
            return []
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to decode BeatNote categories: {exc}") from exc

        if not isinstance(decoded, list):
            return []

        categories: list[str] = []
        for raw_category in decoded:
            try:
                categories.append(normalize_category(raw_category))
            except BeatNoteValidationError:
                continue
        return ordered_categories(categories)

    def _read_notes(self) -> list[BeatNote]:
        try:
            raw_payload = self.settings.value(self.storage_key, "", type=str)
        except TypeError:
            raw_payload = self.settings.value(self.storage_key, "")
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to read BeatNotes: {exc}") from exc

        if not raw_payload:
            return []

        try:
            decoded = json.loads(raw_payload)
        except json.JSONDecodeError:
            return []
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to decode BeatNotes: {exc}") from exc

        if isinstance(decoded, dict):
            decoded = decoded.get("notes", [])
        if not isinstance(decoded, list):
            return []

        notes: list[BeatNote] = []
        for raw_note in decoded:
            if not isinstance(raw_note, dict):
                continue
            try:
                notes.append(deserialize_note(raw_note))
            except BeatNoteValidationError:
                continue
        return notes

    def _write_notes(self, notes: list[BeatNote]) -> None:
        payload = json.dumps([note.to_dict() for note in notes], ensure_ascii=False)
        try:
            self.settings.setValue(self.storage_key, payload)
            sync_method = getattr(self.settings, "sync", None)
            if callable(sync_method):
                sync_method()
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to persist BeatNotes: {exc}") from exc

    def _write_categories(self, categories: list[str]) -> None:
        payload = json.dumps(categories, ensure_ascii=False)
        try:
            self.settings.setValue(self.category_storage_key, payload)
            sync_method = getattr(self.settings, "sync", None)
            if callable(sync_method):
                sync_method()
        except Exception as exc:
            raise BeatNoteServiceError(f"Failed to persist BeatNote categories: {exc}") from exc
