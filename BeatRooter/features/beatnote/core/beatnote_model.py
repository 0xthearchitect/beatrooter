from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import re
from typing import Any, Iterable


BeatNoteCategory = str

BEATNOTE_CATEGORIES: tuple[BeatNoteCategory, ...] = (
    "objective",
    "recon",
    "infrastructure",
    "vulnerability",
    "credentials",
    "payload",
    "pivoting",
    "opsec",
    "evidence",
    "todo",
    "reporting",
    "other",
)

BEATNOTE_CATEGORY_LABELS: dict[BeatNoteCategory, str] = {
    "objective": "Objectives",
    "recon": "Recon",
    "infrastructure": "Infrastructure",
    "vulnerability": "Vulnerabilities",
    "credentials": "Credentials",
    "payload": "Payloads",
    "pivoting": "Pivoting",
    "opsec": "OpSec",
    "evidence": "Evidence",
    "todo": "Tasks",
    "reporting": "Reporting",
    "other": "Other",
}

LEGACY_BEATNOTE_CATEGORY_MAP: dict[str, BeatNoteCategory] = {
    "idea": "objective",
    "drums": "recon",
    "melody": "infrastructure",
    "bass": "credentials",
    "mix": "vulnerability",
    "master": "reporting",
    "reference": "evidence",
}

BEATNOTE_STORAGE_KEY = "beatrooter.beatnotes.v1"
BEATNOTE_CATEGORY_STORAGE_KEY = "beatrooter.beatnote_categories.v1"
BEATNOTE_TITLE_MAX_LENGTH = 120
BEATNOTE_CONTENT_MAX_LENGTH = 5000
BEATNOTE_TAG_MAX_LENGTH = 32
BEATNOTE_TAG_MAX_COUNT = 12
BEATNOTE_CATEGORY_MAX_LENGTH = 40
BEATNOTE_ICON_OPTIONS: tuple[str, ...] = (
    "note",
    "target",
    "vulnerability",
    "credentials",
    "payload",
    "network",
    "web",
    "evidence",
    "host",
    "domain",
    "user",
    "ip",
    "exploit",
    "command",
)
BEATNOTE_ICON_LABELS: dict[str, str] = {
    "note": "Note",
    "target": "Target",
    "vulnerability": "Vulnerability",
    "credentials": "Credentials",
    "payload": "Payload",
    "network": "Network",
    "web": "Web",
    "evidence": "Evidence",
    "host": "Host",
    "domain": "Domain",
    "user": "User",
    "ip": "IP",
    "exploit": "Exploit",
    "command": "Command",
}
BEATNOTE_ICON_ASSETS: dict[str, str] = {
    "note": "icons/node/Notes.svg",
    "target": "icons/node/Target Person.svg",
    "vulnerability": "icons/node/Vulnerability.svg",
    "credentials": "icons/node/Credential.svg",
    "payload": "icons/node/Payload.svg",
    "network": "icons/node/Network Range.svg",
    "web": "icons/node/Web Application.svg",
    "evidence": "icons/node/Screenshot.svg",
    "host": "icons/node/Host.svg",
    "domain": "icons/node/Domain.svg",
    "user": "icons/node/User.svg",
    "ip": "icons/node/IP.svg",
    "exploit": "icons/node/Exploit.svg",
    "command": "icons/node/Command.svg",
}
LEGACY_BEATNOTE_ICON_MAP: dict[str, str] = {
    "📝": "note",
}
BEATNOTE_DEFAULT_ICON = "note"
BEATNOTE_DEFAULT_COLOR = "#2D8CFF"
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class BeatNoteValidationError(ValueError):
    """Raised when BeatNote input does not satisfy the domain rules."""


@dataclass(frozen=True)
class BeatNote:
    id: str
    title: str
    content: str
    category: BeatNoteCategory
    tags: list[str]
    pinned: bool
    icon: str
    color: str
    createdAt: str
    updatedAt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_tags(raw_tags: str | Iterable[str] | None) -> list[str]:
    if raw_tags is None:
        return []

    if isinstance(raw_tags, str):
        tag_values = raw_tags.split(",")
    else:
        tag_values = list(raw_tags)

    normalized: list[str] = []
    seen: set[str] = set()

    for raw_tag in tag_values:
        clean_tag = str(raw_tag or "").strip()
        if not clean_tag:
            continue
        if len(clean_tag) > BEATNOTE_TAG_MAX_LENGTH:
            raise BeatNoteValidationError(
                f"Each tag must be at most {BEATNOTE_TAG_MAX_LENGTH} characters."
            )
        tag_key = clean_tag.casefold()
        if tag_key in seen:
            continue
        normalized.append(clean_tag)
        seen.add(tag_key)

    if len(normalized) > BEATNOTE_TAG_MAX_COUNT:
        raise BeatNoteValidationError(
            f"You can add up to {BEATNOTE_TAG_MAX_COUNT} tags per BeatNote."
        )

    return normalized


def validate_note_input(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "") or "").strip()
    if not title:
        raise BeatNoteValidationError("Title is required.")
    if len(title) > BEATNOTE_TITLE_MAX_LENGTH:
        raise BeatNoteValidationError(
            f"Title must be at most {BEATNOTE_TITLE_MAX_LENGTH} characters."
        )

    content = str(payload.get("content", "") or "").replace("\r\n", "\n")
    if len(content) > BEATNOTE_CONTENT_MAX_LENGTH:
        raise BeatNoteValidationError(
            f"Content must be at most {BEATNOTE_CONTENT_MAX_LENGTH} characters."
        )

    category = normalize_category(payload.get("category", "objective"))

    normalized = {
        "title": title,
        "content": content,
        "category": category,
        "tags": normalize_tags(payload.get("tags")),
        "pinned": bool(payload.get("pinned", False)),
        "icon": normalize_icon(payload.get("icon", BEATNOTE_DEFAULT_ICON)),
        "color": normalize_color(payload.get("color", BEATNOTE_DEFAULT_COLOR)),
    }
    return normalized


def normalize_category(raw_category: Any) -> str:
    category = str(raw_category or "").strip()
    if not category:
        return "objective"
    category = LEGACY_BEATNOTE_CATEGORY_MAP.get(category, category)
    category = re.sub(r"\s+", " ", category).strip()
    if not category:
        return "objective"
    if len(category) > BEATNOTE_CATEGORY_MAX_LENGTH:
        raise BeatNoteValidationError(
            f"Category must be at most {BEATNOTE_CATEGORY_MAX_LENGTH} characters."
        )
    if any(char in category for char in ("\n", "\r", "\t")):
        raise BeatNoteValidationError("Category must be a single line.")
    return category


def category_label(category: str) -> str:
    clean_category = str(category or "").strip()
    if not clean_category:
        return "Other"
    return BEATNOTE_CATEGORY_LABELS.get(clean_category, clean_category)


def ordered_categories(categories: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []

    for category in categories:
        clean_category = normalize_category(category)
        key = clean_category.casefold()
        if key in seen:
            continue
        normalized.append(clean_category)
        seen.add(key)

    builtin_positions = {category: index for index, category in enumerate(BEATNOTE_CATEGORIES)}
    return sorted(
        normalized,
        key=lambda category: (
            0 if category in builtin_positions else 1,
            builtin_positions.get(category, 10_000),
            category_label(category).casefold(),
        ),
    )


def normalize_icon(raw_icon: Any) -> str:
    icon = str(raw_icon or "").strip()
    if not icon:
        return BEATNOTE_DEFAULT_ICON
    icon = LEGACY_BEATNOTE_ICON_MAP.get(icon, icon)
    if icon not in BEATNOTE_ICON_OPTIONS:
        return BEATNOTE_DEFAULT_ICON
    return icon


def normalize_color(raw_color: Any) -> str:
    color = str(raw_color or "").strip()
    if not color:
        return BEATNOTE_DEFAULT_COLOR
    if not HEX_COLOR_RE.match(color):
        raise BeatNoteValidationError("Color must be a valid hex value like #2D8CFF.")
    return color.upper()


def deserialize_note(raw_note: dict[str, Any]) -> BeatNote:
    validated = validate_note_input(raw_note)
    note_id = str(raw_note.get("id", "") or "").strip()
    if not note_id:
        raise BeatNoteValidationError("BeatNote id is required.")

    created_at = str(raw_note.get("createdAt", "") or "").strip()
    updated_at = str(raw_note.get("updatedAt", "") or "").strip()
    if not created_at or not updated_at:
        raise BeatNoteValidationError("BeatNote timestamps are required.")

    return BeatNote(
        id=note_id,
        title=validated["title"],
        content=validated["content"],
        category=validated["category"],
        tags=validated["tags"],
        pinned=validated["pinned"],
        icon=validated["icon"],
        color=validated["color"],
        createdAt=created_at,
        updatedAt=updated_at,
    )


def _parse_iso(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def sort_beatnotes(notes: Iterable[BeatNote]) -> list[BeatNote]:
    return sorted(
        notes,
        key=lambda note: (
            0 if note.pinned else 1,
            -_parse_iso(note.updatedAt).timestamp(),
        ),
    )


def filter_beatnotes(
    notes: Iterable[BeatNote],
    *,
    search_text: str = "",
    category: str = "all",
    pinned_only: bool = False,
) -> list[BeatNote]:
    search_value = (search_text or "").strip().casefold()
    filtered: list[BeatNote] = []

    for note in notes:
        if pinned_only and not note.pinned:
            continue
        if category not in ("", "all") and note.category != category:
            continue
        if search_value:
            haystack = f"{note.title}\n{note.content}".casefold()
            if search_value not in haystack:
                continue
        filtered.append(note)

    return sort_beatnotes(filtered)
