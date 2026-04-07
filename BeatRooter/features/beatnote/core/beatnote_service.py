from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from PyQt6.QtCore import QSettings

from features.beatnote.core.beatnote_model import (
    BEATNOTE_CATEGORIES,
    BEATNOTE_CATEGORY_STORAGE_KEY,
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
        uuid_factory: Callable[[], str] | None = None,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings or QSettings("BeatRooter", "BeatRooter")
        self.storage_key = storage_key
        self.category_storage_key = category_storage_key
        self.uuid_factory = uuid_factory or (lambda: str(uuid4()))
        self.now_factory = now_factory or (lambda: datetime.now(timezone.utc))

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
        return note

    def update(self, note_id: str, patch: dict[str, Any]) -> BeatNote:
        notes = self._read_notes()
        now = self._timestamp_now()

        for index, note in enumerate(notes):
            if note.id != note_id:
                continue
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
            return normalized

        raise BeatNoteNotFoundError(f"BeatNote '{note_id}' was not found.")

    def delete(self, note_id: str) -> BeatNote:
        notes = self._read_notes()
        for index, note in enumerate(notes):
            if note.id == note_id:
                deleted_note = notes.pop(index)
                self._write_notes(notes)
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
        return sort_beatnotes(notes)

    def _timestamp_now(self) -> str:
        return self.now_factory().astimezone(timezone.utc).isoformat()

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
