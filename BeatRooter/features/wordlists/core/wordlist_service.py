from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import requests


class WordlistValidationError(ValueError):
    """Raised when a wordlist node does not contain a valid line-based wordlist."""


WORDLIST_KIND_OPTIONS = (
    "generic",
    "passwords",
    "directories",
    "subdomains",
    "usernames",
)

WORDLIST_PRESET_SOURCES = (
    {
        "key": "top_passwords_100k",
        "name": "Top Passwords 100k",
        "kind": "passwords",
        "description": "Lista pública com 100 mil passwords comuns.",
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/xato-net-10-million-passwords-100000.txt",
    },
    {
        "key": "raft_dirs_small",
        "name": "RAFT Directories Small",
        "kind": "directories",
        "description": "Entradas pequenas para enumeração de diretórios e ficheiros.",
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/raft-small-directories.txt",
    },
    {
        "key": "directory_list_small",
        "name": "Directory List 2.3 Small",
        "kind": "directories",
        "description": "Lista clássica para brute force de paths Web.",
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-small.txt",
    },
    {
        "key": "subdomains_top_5000",
        "name": "Subdomains Top 5000",
        "kind": "subdomains",
        "description": "Labels e subdomínios comuns para descoberta DNS.",
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt",
    },
)


class WordlistService:
    MAX_ENTRIES = 50000
    MAX_TOTAL_CHARS = 2_000_000
    PREVIEW_ENTRIES = 6
    REQUEST_TIMEOUT = 20
    INLINE_ENTRY_LIMIT = 1000
    INLINE_CHAR_LIMIT = 12000
    EXTERNALIZE_SOURCE_MODES = {"remote_preset", "imported_file"}
    _DIRECTORY_RE = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@%/ -]+$")
    _SUBDOMAIN_RE = re.compile(r"^[A-Za-z0-9.-]+$")
    _USERNAME_RE = re.compile(r"^[^\s:]+$")

    @classmethod
    def get_preset_sources(cls) -> tuple[dict, ...]:
        return WORDLIST_PRESET_SOURCES

    @classmethod
    def get_preset_source(cls, preset_key: str) -> dict | None:
        normalized = str(preset_key or "").strip().lower()
        for preset in WORDLIST_PRESET_SOURCES:
            if preset["key"] == normalized:
                return dict(preset)
        return None

    @classmethod
    def validate_kind(cls, raw_kind: str) -> str:
        kind = str(raw_kind or "generic").strip().lower()
        if kind not in WORDLIST_KIND_OPTIONS:
            return "generic"
        return kind

    @classmethod
    def normalize_text(
        cls,
        raw_text: str,
        *,
        kind: str = "generic",
        truncate: bool = False,
    ) -> dict:
        normalized_kind = cls.validate_kind(kind)
        text = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
        if "\x00" in text:
            raise WordlistValidationError("A wordlist deve ser plain text e nao pode conter bytes nulos.")

        raw_lines = text.split("\n")
        entries: list[str] = []
        seen: set[str] = set()
        total_chars = 0
        truncated = False

        for raw_line in raw_lines:
            entry = str(raw_line).strip()
            if not entry:
                continue
            if entry.startswith("#"):
                continue
            cls._validate_entry(entry, normalized_kind)

            entry_key = entry.casefold()
            if entry_key in seen:
                continue

            next_total = total_chars + len(entry) + 1
            if len(entries) >= cls.MAX_ENTRIES or next_total > cls.MAX_TOTAL_CHARS:
                if truncate:
                    truncated = True
                    break
                raise WordlistValidationError(
                    f"A wordlist suporta no maximo {cls.MAX_ENTRIES} entradas e {cls.MAX_TOTAL_CHARS} caracteres."
                )

            entries.append(entry)
            seen.add(entry_key)
            total_chars = next_total

        if not entries:
            raise WordlistValidationError("A wordlist tem de ter pelo menos uma entrada valida.")

        normalized_text = "\n".join(entries)
        preview_entries = ", ".join(entries[: cls.PREVIEW_ENTRIES])
        message = f"{len(entries)} entrad{'a' if len(entries) == 1 else 'as'} validadas."
        if truncated:
            message += f" Importacao limitada as primeiras {len(entries)} entradas."

        return {
            "kind": normalized_kind,
            "content": normalized_text,
            "entries": entries,
            "entry_count": len(entries),
            "preview_entries": preview_entries,
            "validation_message": message,
            "truncated": truncated,
        }

    @classmethod
    def inspect_node_data(cls, node_data: dict) -> dict:
        data = dict(node_data or {})
        kind = cls.validate_kind(data.get("wordlist_kind", "generic"))
        content = cls.resolve_node_content(data)
        try:
            payload = cls.normalize_text(content, kind=kind, truncate=False)
            return {
                "valid": True,
                "reason": payload["validation_message"],
                **payload,
            }
        except WordlistValidationError as exc:
            return {
                "valid": False,
                "kind": kind,
                "content": content,
                "entries": [],
                "entry_count": 0,
                "preview_entries": "",
                "validation_message": str(exc),
                "reason": str(exc),
                "truncated": False,
            }

    @classmethod
    def apply_payload_to_node_data(
        cls,
        node_data: dict,
        payload: dict,
        *,
        source_mode: str | None = None,
        source_label: str | None = None,
        source_path: str | None = None,
        source_url: str | None = None,
        source_note_id: str | None = None,
    ) -> dict:
        node_data["wordlist_kind"] = payload["kind"]
        node_data["content"] = payload["content"]
        node_data["entry_count"] = payload["entry_count"]
        node_data["preview_entries"] = payload["preview_entries"]
        node_data["validation_message"] = payload["validation_message"]
        node_data["content_storage"] = "inline"
        node_data["external_content_path"] = ""
        node_data["external_content_relative_path"] = ""
        if source_mode is not None:
            node_data["source_mode"] = source_mode
        if source_label is not None:
            node_data["source_label"] = source_label
        if source_path is not None:
            node_data["source_path"] = source_path
        if source_url is not None:
            node_data["source_url"] = source_url
        if source_note_id is not None:
            node_data["source_note_id"] = source_note_id
        return node_data

    @classmethod
    def import_from_file(cls, file_path: str, *, kind: str = "generic") -> dict:
        path = Path(str(file_path or "").strip())
        if not path.exists() or not path.is_file():
            raise WordlistValidationError("O ficheiro de wordlist nao existe.")

        raw_bytes = path.read_bytes()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1")

        payload = cls.normalize_text(text, kind=kind, truncate=True)
        payload["source_path"] = str(path)
        return payload

    @classmethod
    def import_from_preset(cls, preset_key: str) -> tuple[dict, dict]:
        preset = cls.get_preset_source(preset_key)
        if not preset:
            raise WordlistValidationError("Preset de wordlist desconhecido.")

        response = requests.get(preset["url"], timeout=cls.REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = cls.normalize_text(response.text, kind=preset["kind"], truncate=True)
        payload["source_url"] = preset["url"]
        return payload, preset

    @classmethod
    def materialize_node_to_temp(cls, node_id: str, node_data: dict) -> str:
        external_path = Path(str(node_data.get("external_content_path", "") or "").strip())
        if external_path.exists() and external_path.is_file():
            return str(external_path)

        inspection = cls.inspect_node_data(node_data)
        if not inspection["valid"]:
            raise WordlistValidationError(inspection["reason"])

        safe_node_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(node_id or "wordlist")).strip("_") or "wordlist"
        digest = hashlib.sha1(inspection["content"].encode("utf-8")).hexdigest()[:12]
        temp_dir = Path(tempfile.gettempdir()) / "beatrooter_wordlists"
        temp_dir.mkdir(parents=True, exist_ok=True)
        file_path = temp_dir / f"{safe_node_id}_{digest}.txt"
        file_path.write_text(inspection["content"], encoding="utf-8")
        return str(file_path)

    @classmethod
    def resolve_node_content(cls, node_data: dict[str, Any]) -> str:
        data = dict(node_data or {})
        inline_content = str(data.get("content", "") or "")
        if inline_content.strip():
            return inline_content

        external_path = str(data.get("external_content_path", "") or "").strip()
        if external_path:
            return cls._read_text_file(external_path)
        return ""

    @classmethod
    def ensure_node_content_loaded(cls, node_data: dict[str, Any]) -> str:
        content = cls.resolve_node_content(node_data)
        if content and not str(node_data.get("content", "") or "").strip():
            node_data["content"] = content
        return content

    @classmethod
    def should_externalize_node(cls, node_data: dict[str, Any]) -> bool:
        data = dict(node_data or {})
        source_mode = str(data.get("source_mode", "") or "").strip().lower()
        if source_mode not in cls.EXTERNALIZE_SOURCE_MODES:
            return False

        inspection = cls.inspect_node_data(data)
        if not inspection["valid"]:
            return False

        return (
            inspection["entry_count"] > cls.INLINE_ENTRY_LIMIT
            or len(inspection["content"]) > cls.INLINE_CHAR_LIMIT
        )

    @classmethod
    def prepare_node_data_for_save(
        cls,
        node_id: str,
        node_data: dict[str, Any],
        project_filename: str,
    ) -> dict[str, Any]:
        serialized = dict(node_data or {})

        if cls.should_externalize_node(serialized):
            external_relative_path, external_absolute_path = cls._persist_external_wordlist(
                node_id,
                serialized,
                project_filename,
            )
            serialized["content_storage"] = "external"
            serialized["external_content_relative_path"] = external_relative_path
            serialized["external_content_path"] = external_absolute_path
            serialized["content"] = ""
            return serialized

        serialized["content_storage"] = "inline"
        serialized["external_content_relative_path"] = ""
        serialized["external_content_path"] = ""
        return serialized

    @classmethod
    def hydrate_node_data_after_load(
        cls,
        node_data: dict[str, Any],
        project_filename: str,
    ) -> dict[str, Any]:
        hydrated = dict(node_data or {})
        relative_path = str(hydrated.get("external_content_relative_path", "") or "").strip()
        if relative_path:
            hydrated["external_content_path"] = str((Path(project_filename).resolve().parent / relative_path).resolve())
            hydrated.setdefault("content_storage", "external")
        else:
            hydrated["external_content_path"] = ""
            hydrated.setdefault("content_storage", "inline")
        return hydrated

    @classmethod
    def _persist_external_wordlist(
        cls,
        node_id: str,
        node_data: dict[str, Any],
        project_filename: str,
    ) -> tuple[str, str]:
        inspection = cls.inspect_node_data(node_data)
        if not inspection["valid"]:
            raise WordlistValidationError(inspection["reason"])

        project_path = Path(project_filename).resolve()
        assets_dir = project_path.parent / f"{project_path.stem}.assets" / "wordlists"
        assets_dir.mkdir(parents=True, exist_ok=True)

        safe_node_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(node_id or "wordlist")).strip("_") or "wordlist"
        digest = hashlib.sha1(inspection["content"].encode("utf-8")).hexdigest()[:12]
        file_name = f"{safe_node_id}_{digest}.txt"
        absolute_path = assets_dir / file_name
        absolute_path.write_text(inspection["content"], encoding="utf-8")

        relative_path = os.path.relpath(absolute_path, project_path.parent)
        return relative_path, str(absolute_path)

    @staticmethod
    def _read_text_file(file_path: str) -> str:
        path = Path(str(file_path or "").strip())
        if not path.exists() or not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")

    @classmethod
    def _validate_entry(cls, entry: str, kind: str):
        if len(entry) > 512:
            raise WordlistValidationError("Cada entrada da wordlist tem de ter no maximo 512 caracteres.")
        if "\t" in entry:
            raise WordlistValidationError("Cada entrada deve ocupar uma linha e nao pode conter tabulacoes.")

        lowered = entry.lower()
        if lowered.startswith(("http://", "https://")):
            raise WordlistValidationError("As entradas nao podem incluir URLs completas.")
        if "<html" in lowered or "<body" in lowered or "</" in lowered:
            raise WordlistValidationError("A wordlist nao pode conter HTML ou texto formatado.")

        if kind == "directories":
            if any(token in entry for token in ("?", "#")):
                raise WordlistValidationError("Entradas de diretorios nao podem conter query string ou fragmentos.")
            if not cls._DIRECTORY_RE.fullmatch(entry):
                raise WordlistValidationError("Entradas de diretorios so podem conter paths simples.")
        elif kind == "subdomains":
            if "/" in entry or ":" in entry or "_" in entry or " " in entry:
                raise WordlistValidationError("Wordlists de subdominios so aceitam labels e nomes DNS.")
            if not cls._SUBDOMAIN_RE.fullmatch(entry):
                raise WordlistValidationError("Entradas de subdominios contem caracteres invalidos.")
        elif kind == "usernames":
            if not cls._USERNAME_RE.fullmatch(entry):
                raise WordlistValidationError("Usernames nao podem conter espacos ou separadores ':' .")
