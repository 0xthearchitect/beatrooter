import copy
import os
import re
from pathlib import Path


class FlipperWorkspaceImporter:
    """Static helper that parses a Flipper workspace and returns normalized artifacts."""

    MAX_SCAN_FILES = 12000
    MAX_TEXT_READ_BYTES = 180000

    MODULE_ORDER = {
        "subghz": 0,
        "badusb": 1,
        "infrared": 2,
        "nfc": 3,
        "rfid": 4,
        "ibutton": 5,
        "wifi": 6,
        "logs": 7,
        "general": 8,
    }

    MODULE_LABELS = {
        "subghz": "Sub-GHz",
        "badusb": "BadUSB",
        "infrared": "Infrared",
        "nfc": "NFC",
        "rfid": "RFID",
        "ibutton": "iButton",
        "wifi": "WiFi Board",
        "logs": "Logs",
        "general": "General",
    }

    SCAN_SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules"}

    SUBGHZ_EXTENSIONS = {".sub"}
    INFRARED_EXTENSIONS = {".ir"}
    NFC_EXTENSIONS = {".nfc"}
    RFID_EXTENSIONS = {".rfid", ".lf"}
    IBUTTON_EXTENSIONS = {".ibtn", ".ibutton"}
    BADUSB_EXTENSIONS = {".txt", ".badusb", ".duck", ".ducky", ".script", ".ps1", ".bat", ".cmd", ".sh"}
    WIFI_ARTIFACT_EXTENSIONS = {".pcap", ".pcapng", ".cap", ".csv", ".json", ".txt", ".log"}
    LOG_EXTENSIONS = {".log", ".txt", ".csv", ".json"}

    DUCKY_KEYWORDS = {
        "rem",
        "delay",
        "string",
        "stringln",
        "enter",
        "ctrl",
        "alt",
        "shift",
        "gui",
        "windows",
        "menu",
        "tab",
        "escape",
        "space",
        "downarrow",
        "uparrow",
        "leftarrow",
        "rightarrow",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "f9",
        "f10",
        "f11",
        "f12",
    }

    WIFI_HINTS = {
        "wifi",
        "wi-fi",
        "marauder",
        "esp32",
        "deauth",
        "handshake",
        "wardrive",
        "sniff",
        "probe",
        "beacon",
        "wpa",
        "wlan",
        "pcap",
    }

    LOG_HINTS = {
        "log",
        "logs",
        "event",
        "events",
        "history",
        "trace",
        "attack",
        "session",
    }

    ATTACK_KEYWORDS = {
        "deauth": "deauthentication",
        "handshake": "handshake_capture",
        "evil twin": "evil_twin",
        "bruteforce": "bruteforce",
        "brute force": "bruteforce",
        "replay": "replay",
        "jam": "jamming",
        "spoof": "spoofing",
        "dos": "denial_of_service",
        "denial": "denial_of_service",
        "flood": "flood",
    }

    DEFAULT_NODE_TEMPLATES = [
        {
            "name": "Flipper Workspace",
            "node_type": "flipper_workspace",
            "color": "#0284c7",
            "symbol": "[FLIP]",
            "default_data": {
                "module": "workspace",
                "workspace_name": "",
                "workspace_path": "",
                "total_supported_files": 0,
                "modules_detected": "",
                "scan_timestamp": "",
                "notes": "",
            },
        },
        {
            "name": "Flipper Module",
            "node_type": "flipper_module",
            "color": "#0369a1",
            "symbol": "[MOD]",
            "default_data": {
                "module": "",
                "module_name": "",
                "artifact_count": 0,
                "workspace_ref": "",
                "notes": "",
            },
        },
        {
            "name": "Flipper Sub-GHz Signal",
            "node_type": "flipper_subghz_signal",
            "color": "#f97316",
            "symbol": "[SUBG]",
            "default_data": {
                "module": "subghz",
                "file_name": "",
                "relative_path": "",
                "frequency_hz": 0,
                "frequency_mhz": 0.0,
                "protocol": "unknown",
                "preset": "",
                "modulation": "unknown",
                "content_preview": "",
                "key_preview": "",
                "target_devices": "",
                "attack_surface": "",
                "key_material_present": False,
                "is_raw_capture": False,
                "risk_level": "medium",
                "notes": "",
            },
        },
        {
            "name": "Flipper BadUSB Script",
            "node_type": "flipper_badusb_script",
            "color": "#dc2626",
            "symbol": "[BUSB]",
            "default_data": {
                "module": "badusb",
                "file_name": "",
                "relative_path": "",
                "script_type": "automation",
                "objective": "",
                "target_os": "unknown",
                "line_count": 0,
                "command_count": 0,
                "common_commands": [],
                "binary_artifacts": [],
                "external_urls": [],
                "script_preview": "",
                "likely_requires_admin": False,
                "risk_level": "medium",
                "notes": "",
            },
        },
        {
            "name": "Flipper Infrared Signal",
            "node_type": "flipper_ir_signal",
            "color": "#7c3aed",
            "symbol": "[IR]",
            "default_data": {
                "module": "infrared",
                "file_name": "",
                "relative_path": "",
                "protocol": "unknown",
                "frequency_hz": 0,
                "duty_cycle": "",
                "address": "",
                "command": "",
                "content_preview": "",
                "target_device_type": "unknown",
                "transmit_profile": "unknown",
                "risk_level": "low",
                "notes": "",
            },
        },
        {
            "name": "Flipper NFC Dump",
            "node_type": "flipper_nfc_dump",
            "color": "#2563eb",
            "symbol": "[NFC]",
            "default_data": {
                "module": "nfc",
                "file_name": "",
                "relative_path": "",
                "technology": "unknown",
                "frequency_khz": 13560,
                "uid": "",
                "sak": "",
                "atqa": "",
                "protocol": "unknown",
                "content_preview": "",
                "memory_layout": "",
                "risk_level": "medium",
                "notes": "",
            },
        },
        {
            "name": "Flipper RFID Dump",
            "node_type": "flipper_rfid_dump",
            "color": "#0891b2",
            "symbol": "[RFID]",
            "default_data": {
                "module": "rfid",
                "file_name": "",
                "relative_path": "",
                "rfid_type": "unknown",
                "frequency_khz": 125,
                "key_value": "",
                "facility_code": "",
                "card_id": "",
                "bit_length": 0,
                "content_preview": "",
                "risk_level": "medium",
                "notes": "",
            },
        },
        {
            "name": "Flipper iButton Key",
            "node_type": "flipper_ibutton_key",
            "color": "#9333ea",
            "symbol": "[IBTN]",
            "default_data": {
                "module": "ibutton",
                "file_name": "",
                "relative_path": "",
                "ibutton_type": "unknown",
                "key_value": "",
                "content_preview": "",
                "risk_level": "medium",
                "notes": "",
            },
        },
        {
            "name": "Flipper WiFi Artifact",
            "node_type": "flipper_wifi_artifact",
            "color": "#0f766e",
            "symbol": "[WIFI]",
            "default_data": {
                "module": "wifi",
                "file_name": "",
                "relative_path": "",
                "artifact_kind": "unknown",
                "attack_indicators": [],
                "target_networks": 0,
                "deauth_events": 0,
                "handshake_events": 0,
                "attack_result": "unknown",
                "file_size_bytes": 0,
                "risk_level": "medium",
                "notes": "",
            },
        },
        {
            "name": "Flipper Log Artifact",
            "node_type": "flipper_log_artifact",
            "color": "#475569",
            "symbol": "[LOG]",
            "default_data": {
                "module": "logs",
                "file_name": "",
                "relative_path": "",
                "event_count": 0,
                "critical_events": 0,
                "attack_indicators": [],
                "attack_result": "unknown",
                "last_timestamp": "",
                "file_size_bytes": 0,
                "risk_level": "low",
                "notes": "",
            },
        },
        {
            "name": "Flipper File",
            "node_type": "flipper_file",
            "color": "#64748b",
            "symbol": "[FILE]",
            "default_data": {
                "module": "general",
                "file_name": "",
                "relative_path": "",
                "file_extension": "",
                "file_size_bytes": 0,
                "parser_status": "generic",
                "content_preview": "",
                "notes": "",
            },
        },
    ]

    @classmethod
    def get_default_templates(cls):
        return copy.deepcopy(cls.DEFAULT_NODE_TEMPLATES)

    @classmethod
    def get_module_label(cls, module_name: str) -> str:
        return cls.MODULE_LABELS.get(module_name, module_name.replace("_", " ").title())

    @classmethod
    def sorted_modules(cls, modules):
        return sorted(modules, key=lambda item: (cls.MODULE_ORDER.get(item, 99), item))

    @classmethod
    def parse_workspace(cls, workspace_path: str):
        workspace = Path(workspace_path).expanduser()
        if not workspace.exists() or not workspace.is_dir():
            raise ValueError("Invalid workspace path")

        artifacts = []
        module_counts = {}
        warnings = []
        scanned_files = 0

        stop_scan = False
        for current_root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d.lower() not in cls.SCAN_SKIP_DIRS]

            for filename in files:
                scanned_files += 1
                if scanned_files > cls.MAX_SCAN_FILES:
                    warnings.append(
                        f"Scan limit reached ({cls.MAX_SCAN_FILES} files). Remaining files were skipped."
                    )
                    stop_scan = True
                    break

                file_path = Path(current_root) / filename
                try:
                    relative_path = file_path.relative_to(workspace)
                except ValueError:
                    relative_path = file_path

                artifact = cls._parse_supported_file(file_path, relative_path)
                if not artifact:
                    continue

                artifacts.append(artifact)
                module = artifact.get("module", "general")
                module_counts[module] = module_counts.get(module, 0) + 1

            if stop_scan:
                break

        artifacts.sort(
            key=lambda item: (
                cls.MODULE_ORDER.get(item.get("module", "general"), 99),
                str(item.get("data", {}).get("relative_path", "")).lower(),
            )
        )

        return {
            "workspace_name": workspace.name,
            "workspace_path": str(workspace.resolve()),
            "scanned_files": scanned_files,
            "artifacts": artifacts,
            "module_counts": module_counts,
            "modules": cls.sorted_modules(module_counts.keys()),
            "warnings": warnings,
        }

    @classmethod
    def parse_file(cls, file_path: str, workspace_root: str = None):
        candidate = Path(file_path).expanduser()
        if not candidate.exists() or not candidate.is_file():
            return None

        relative_path = Path(candidate.name)
        if workspace_root:
            root_path = Path(workspace_root).expanduser()
            try:
                relative_path = candidate.relative_to(root_path)
            except ValueError:
                relative_path = Path(candidate.name)

        artifact = cls._parse_supported_file(candidate, relative_path)
        if artifact:
            return artifact
        return cls._parse_generic_file(candidate, relative_path)

    @classmethod
    def _parse_supported_file(cls, file_path: Path, relative_path: Path):
        module_hint = cls._detect_module_hint(relative_path)
        extension = file_path.suffix.lower()

        if extension in cls.SUBGHZ_EXTENSIONS:
            return cls._parse_subghz_file(file_path, relative_path)

        if extension in cls.INFRARED_EXTENSIONS:
            return cls._parse_infrared_file(file_path, relative_path)

        if extension in cls.NFC_EXTENSIONS:
            return cls._parse_nfc_file(file_path, relative_path)

        if extension in cls.RFID_EXTENSIONS:
            return cls._parse_rfid_file(file_path, relative_path)

        if extension in cls.IBUTTON_EXTENSIONS:
            return cls._parse_ibutton_file(file_path, relative_path)

        if module_hint == "badusb" and extension in cls.BADUSB_EXTENSIONS:
            return cls._parse_badusb_file(file_path, relative_path)

        if extension in cls.BADUSB_EXTENSIONS and cls._looks_like_badusb_script(file_path):
            return cls._parse_badusb_file(file_path, relative_path)

        if module_hint == "wifi" and extension in cls.WIFI_ARTIFACT_EXTENSIONS:
            return cls._parse_wifi_artifact(file_path, relative_path)

        if extension in cls.WIFI_ARTIFACT_EXTENSIONS and cls._looks_like_wifi_artifact(file_path, relative_path):
            return cls._parse_wifi_artifact(file_path, relative_path)

        if module_hint == "logs" and extension in cls.LOG_EXTENSIONS:
            return cls._parse_log_artifact(file_path, relative_path)

        if extension in cls.LOG_EXTENSIONS and cls._looks_like_log_artifact(file_path, relative_path):
            return cls._parse_log_artifact(file_path, relative_path)

        return None

    @classmethod
    def _detect_module_hint(cls, relative_path: Path) -> str:
        joined = "/".join(part.lower() for part in relative_path.parts)
        parts = {part.lower() for part in relative_path.parts}

        if "subghz" in parts or "sub_ghz" in parts:
            return "subghz"
        if "badusb" in parts:
            return "badusb"
        if "infrared" in parts:
            return "infrared"
        if "nfc" in parts:
            return "nfc"
        if "rfid" in parts or "lfrfid" in joined:
            return "rfid"
        if "ibutton" in parts or "ibutton" in joined:
            return "ibutton"
        if any(hint in joined for hint in cls.WIFI_HINTS):
            return "wifi"
        if any(hint in joined for hint in cls.LOG_HINTS):
            return "logs"
        return "general"

    @classmethod
    def _base_file_data(cls, file_path: Path, relative_path: Path, module: str) -> dict:
        file_size = cls._safe_file_size(file_path)
        return {
            "module": module,
            "file_name": file_path.name,
            "relative_path": str(relative_path),
            "file_size_bytes": file_size,
        }

    @classmethod
    def _parse_generic_file(cls, file_path: Path, relative_path: Path):
        module = cls._detect_module_hint(relative_path)
        extension = file_path.suffix.lower()
        text = cls._read_text_limited(file_path, max_bytes=6000)
        data = cls._base_file_data(file_path, relative_path, module)
        data.update(
            {
                "title": f"Flipper File {file_path.stem}",
                "summary": cls._join_summary_parts([module, extension or "no extension"]),
                "file_extension": extension,
                "parser_status": "generic",
                "content_preview": cls._compact_preview(text),
            }
        )
        return {
            "module": module,
            "node_type": "flipper_file",
            "display_name": file_path.name,
            "data": data,
        }

    @classmethod
    def _parse_subghz_file(cls, file_path: Path, relative_path: Path):
        text = cls._read_text_limited(file_path)
        metadata = cls._parse_key_value_lines(text)

        frequency_hz = cls._safe_int(metadata.get("frequency", "0"))
        frequency_mhz = round(frequency_hz / 1000000.0, 3) if frequency_hz > 0 else 0.0
        protocol = metadata.get("protocol", "unknown")
        preset = metadata.get("preset", "")

        target_devices = cls._infer_subghz_target_devices(frequency_mhz, protocol)
        attack_surface = cls._infer_subghz_attack_surface(protocol, target_devices)

        key_present = bool(metadata.get("key", "").strip())
        is_raw = "raw_data" in metadata or protocol.strip().lower() == "raw"
        modulation = cls._infer_modulation_from_preset(preset)
        risk_level = "high" if key_present else "medium"

        data = cls._base_file_data(file_path, relative_path, "subghz")
        data.update(
            {
                "title": f"Sub-GHz {file_path.stem}",
                "summary": f"{protocol or 'unknown'} @ {frequency_mhz:.3f} MHz" if frequency_mhz else protocol,
                "frequency_hz": frequency_hz,
                "frequency_mhz": frequency_mhz,
                "protocol": protocol,
                "preset": preset,
                "modulation": modulation,
                "content_preview": cls._compact_preview(text),
                "key_preview": metadata.get("key", "")[:48],
                "target_devices": target_devices,
                "attack_surface": attack_surface,
                "key_material_present": key_present,
                "is_raw_capture": is_raw,
                "risk_level": risk_level,
            }
        )

        return {
            "module": "subghz",
            "node_type": "flipper_subghz_signal",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _parse_badusb_file(cls, file_path: Path, relative_path: Path):
        text = cls._read_text_limited(file_path)
        lines = [line.rstrip() for line in text.splitlines()]

        command_tokens = []
        for line in lines:
            clean = line.strip()
            if not clean:
                continue
            token = clean.split()[0].lower()
            if token in cls.DUCKY_KEYWORDS:
                command_tokens.append(token)

        script_type, objective = cls._infer_badusb_intent(text)
        target_os = cls._infer_badusb_target_os(text)
        binaries = cls._extract_binary_artifacts(text)
        urls = cls._extract_urls(text)
        likely_requires_admin = cls._infer_requires_admin(text)

        risk_level = "medium"
        if script_type in {"credential_access", "destructive", "exfiltration"}:
            risk_level = "high"

        data = cls._base_file_data(file_path, relative_path, "badusb")
        data.update(
            {
                "title": f"BadUSB {file_path.stem}",
                "summary": objective,
                "script_type": script_type,
                "objective": objective,
                "target_os": target_os,
                "line_count": len(lines),
                "command_count": len(command_tokens),
                "common_commands": sorted(set(command_tokens))[:8],
                "binary_artifacts": binaries,
                "external_urls": urls,
                "script_preview": cls._compact_preview(text),
                "likely_requires_admin": likely_requires_admin,
                "risk_level": risk_level,
            }
        )

        return {
            "module": "badusb",
            "node_type": "flipper_badusb_script",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _parse_infrared_file(cls, file_path: Path, relative_path: Path):
        text = cls._read_text_limited(file_path)
        metadata = cls._parse_key_value_lines(text)

        protocol = metadata.get("protocol", "unknown")
        frequency_hz = cls._safe_int(metadata.get("frequency", "0"))
        duty_cycle = metadata.get("duty_cycle", "")
        address = metadata.get("address", "")
        command = metadata.get("command", "")

        target_device_type = cls._infer_ir_target_device(file_path.stem, command)
        transmit_profile = cls._infer_ir_profile(frequency_hz, duty_cycle)

        data = cls._base_file_data(file_path, relative_path, "infrared")
        data.update(
            {
                "title": f"Infrared {file_path.stem}",
                "summary": f"{protocol} for {target_device_type}",
                "protocol": protocol,
                "frequency_hz": frequency_hz,
                "duty_cycle": duty_cycle,
                "address": address,
                "command": command,
                "content_preview": cls._compact_preview(text),
                "target_device_type": target_device_type,
                "transmit_profile": transmit_profile,
                "risk_level": "low",
            }
        )

        return {
            "module": "infrared",
            "node_type": "flipper_ir_signal",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _parse_nfc_file(cls, file_path: Path, relative_path: Path):
        text = cls._read_text_limited(file_path)
        metadata = cls._parse_key_value_lines(text)

        technology = (
            metadata.get("device_type")
            or metadata.get("card_type")
            or metadata.get("type")
            or metadata.get("protocol")
            or "unknown"
        )
        uid = metadata.get("uid") or metadata.get("data") or ""
        sak = metadata.get("sak", "")
        atqa = metadata.get("atqa", "")
        protocol = metadata.get("protocol") or cls._infer_nfc_protocol(technology, text)
        memory_layout = cls._infer_nfc_memory_layout(text, technology)

        data = cls._base_file_data(file_path, relative_path, "nfc")
        data.update(
            {
                "title": f"NFC {file_path.stem}",
                "summary": cls._join_summary_parts([technology, uid[:18]]),
                "technology": technology,
                "frequency_khz": 13560,
                "uid": uid,
                "sak": sak,
                "atqa": atqa,
                "protocol": protocol,
                "content_preview": cls._compact_preview(text),
                "memory_layout": memory_layout,
                "risk_level": "medium" if uid else "low",
            }
        )

        return {
            "module": "nfc",
            "node_type": "flipper_nfc_dump",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _parse_rfid_file(cls, file_path: Path, relative_path: Path):
        text = cls._read_text_limited(file_path)
        metadata = cls._parse_key_value_lines(text)

        rfid_type = metadata.get("key_type") or metadata.get("type") or metadata.get("protocol") or "unknown"
        key_value = metadata.get("data") or metadata.get("key") or metadata.get("uid") or ""
        facility_code = metadata.get("facility_code", "")
        card_id = metadata.get("card_id", "")
        bit_length = cls._safe_int(metadata.get("bit") or metadata.get("bit_length") or metadata.get("bits") or "0")
        frequency_khz = cls._infer_rfid_frequency_khz(rfid_type, text)

        data = cls._base_file_data(file_path, relative_path, "rfid")
        data.update(
            {
                "title": f"RFID {file_path.stem}",
                "summary": cls._join_summary_parts([rfid_type, f"{frequency_khz} kHz", key_value[:18]]),
                "rfid_type": rfid_type,
                "frequency_khz": frequency_khz,
                "key_value": key_value,
                "facility_code": facility_code,
                "card_id": card_id,
                "bit_length": bit_length,
                "content_preview": cls._compact_preview(text),
                "risk_level": "medium" if key_value else "low",
            }
        )

        return {
            "module": "rfid",
            "node_type": "flipper_rfid_dump",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _parse_ibutton_file(cls, file_path: Path, relative_path: Path):
        text = cls._read_text_limited(file_path)
        metadata = cls._parse_key_value_lines(text)

        ibutton_type = metadata.get("key_type") or metadata.get("type") or "unknown"
        key_value = metadata.get("data") or metadata.get("key") or metadata.get("uid") or ""

        data = cls._base_file_data(file_path, relative_path, "ibutton")
        data.update(
            {
                "title": f"iButton {file_path.stem}",
                "summary": cls._join_summary_parts([ibutton_type, key_value[:18]]),
                "ibutton_type": ibutton_type,
                "key_value": key_value,
                "content_preview": cls._compact_preview(text),
                "risk_level": "medium" if key_value else "low",
            }
        )

        return {
            "module": "ibutton",
            "node_type": "flipper_ibutton_key",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _parse_wifi_artifact(cls, file_path: Path, relative_path: Path):
        extension = file_path.suffix.lower()
        text = ""
        if extension in {".txt", ".log", ".csv", ".json"}:
            text = cls._read_text_limited(file_path)

        indicators = cls._extract_attack_indicators(text)
        target_networks = cls._count_network_targets(text)
        deauth_events = cls._count_keyword(text, "deauth")
        handshake_events = cls._count_keyword(text, "handshake")
        artifact_kind = cls._infer_wifi_artifact_kind(file_path, text)

        attack_result = "unknown"
        lowered = text.lower()
        if "success" in lowered:
            attack_result = "success"
        elif "fail" in lowered or "error" in lowered:
            attack_result = "failed"
        elif indicators:
            attack_result = "partial"

        risk_level = "high" if indicators else "medium"

        data = cls._base_file_data(file_path, relative_path, "wifi")
        data.update(
            {
                "title": f"WiFi Artifact {file_path.stem}",
                "summary": f"{artifact_kind} ({len(indicators)} indicators)",
                "artifact_kind": artifact_kind,
                "attack_indicators": indicators,
                "target_networks": target_networks,
                "deauth_events": deauth_events,
                "handshake_events": handshake_events,
                "attack_result": attack_result,
                "content_preview": cls._compact_preview(text),
                "risk_level": risk_level,
            }
        )

        return {
            "module": "wifi",
            "node_type": "flipper_wifi_artifact",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _parse_log_artifact(cls, file_path: Path, relative_path: Path):
        text = cls._read_text_limited(file_path)
        lines = text.splitlines()

        indicators = cls._extract_attack_indicators(text)
        critical_events = sum(
            1 for line in lines if any(word in line.lower() for word in ("error", "critical", "failed", "denied"))
        )

        timestamps = re.findall(
            r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}|\d{2}:\d{2}:\d{2})",
            text,
        )
        last_timestamp = timestamps[-1] if timestamps else ""

        attack_result = "unknown"
        lowered = text.lower()
        if "success" in lowered:
            attack_result = "success"
        elif "fail" in lowered or "error" in lowered:
            attack_result = "failed"
        elif indicators:
            attack_result = "partial"

        risk_level = "low"
        if indicators or critical_events > 5:
            risk_level = "medium"

        data = cls._base_file_data(file_path, relative_path, "logs")
        data.update(
            {
                "title": f"Log {file_path.stem}",
                "summary": f"{len(lines)} events, {len(indicators)} indicators",
                "event_count": len(lines),
                "critical_events": critical_events,
                "attack_indicators": indicators,
                "attack_result": attack_result,
                "last_timestamp": last_timestamp,
                "content_preview": cls._compact_preview(text),
                "risk_level": risk_level,
            }
        )

        return {
            "module": "logs",
            "node_type": "flipper_log_artifact",
            "display_name": file_path.stem.replace("_", " ").title(),
            "data": data,
        }

    @classmethod
    def _looks_like_badusb_script(cls, file_path: Path) -> bool:
        preview = cls._read_text_limited(file_path, max_bytes=7000)
        if not preview.strip():
            return False

        score = 0
        for line in preview.splitlines()[:80]:
            token = line.strip().split(" ", 1)[0].lower() if line.strip() else ""
            if token in cls.DUCKY_KEYWORDS:
                score += 1
            if score >= 2:
                return True

        lowered = preview.lower()
        return "duckyscript" in lowered or "badusb" in lowered

    @classmethod
    def _looks_like_wifi_artifact(cls, file_path: Path, relative_path: Path) -> bool:
        name = f"{file_path.name} {relative_path}".lower()
        return any(hint in name for hint in cls.WIFI_HINTS)

    @classmethod
    def _looks_like_log_artifact(cls, file_path: Path, relative_path: Path) -> bool:
        name = f"{file_path.name} {relative_path}".lower()
        return any(hint in name for hint in cls.LOG_HINTS)

    @classmethod
    def _parse_key_value_lines(cls, text: str) -> dict:
        parsed = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue

            key, value = line.split(":", 1)
            clean_key = re.sub(r"[^a-z0-9_]+", "_", key.strip().lower()).strip("_")
            if not clean_key:
                continue
            parsed[clean_key] = value.strip()

        return parsed

    @classmethod
    def _infer_modulation_from_preset(cls, preset: str) -> str:
        lowered = preset.lower()
        if "ook" in lowered:
            return "ook"
        if "fsk" in lowered:
            return "fsk"
        if "ask" in lowered:
            return "ask"
        return "unknown"

    @classmethod
    def _infer_subghz_target_devices(cls, frequency_mhz: float, protocol: str) -> str:
        if 300.0 <= frequency_mhz <= 320.0:
            return "legacy car remotes, garage door openers"
        if 390.0 <= frequency_mhz <= 410.0:
            return "alarms, garage remotes, weather sensors"
        if 430.0 <= frequency_mhz <= 435.0:
            return "remote controls, IoT sensors, switches"
        if 860.0 <= frequency_mhz <= 870.0:
            return "EU ISM devices, alarms, smart metering"
        if 902.0 <= frequency_mhz <= 928.0:
            return "US ISM devices, LoRa/FSK telemetry"

        protocol_lower = protocol.lower()
        if protocol_lower and protocol_lower != "unknown":
            return f"devices using {protocol}"

        return "unknown"

    @classmethod
    def _infer_subghz_attack_surface(cls, protocol: str, target_devices: str) -> str:
        protocol_lower = protocol.lower()
        if "keeloq" in protocol_lower:
            return "rolling-code remote systems (capture/replay validation required)"
        if "raw" in protocol_lower:
            return "raw replay experiments against compatible receivers"
        if "princeton" in protocol_lower:
            return "fixed-code consumer remotes"
        if "unknown" in target_devices:
            return "manual analysis required"
        return target_devices

    @classmethod
    def _infer_badusb_intent(cls, text: str):
        lowered = text.lower()

        scores = {
            "reconnaissance": 0,
            "payload_download": 0,
            "credential_access": 0,
            "persistence": 0,
            "exfiltration": 0,
            "destructive": 0,
        }

        if any(token in lowered for token in ("whoami", "ipconfig", "ifconfig", "systeminfo", "hostname", "net user", "arp -a")):
            scores["reconnaissance"] += 2
        if any(token in lowered for token in ("invoke-webrequest", "downloadstring", "wget", "curl", "bitsadmin", "http://", "https://")):
            scores["payload_download"] += 2
        if any(token in lowered for token in ("mimikatz", "lsass", "sam", "credential", "hashdump")):
            scores["credential_access"] += 3
        if any(token in lowered for token in ("schtasks", "startup", "autorun", "reg add", "run key")):
            scores["persistence"] += 2
        if any(token in lowered for token in ("ftp ", "scp ", "exfil", "upload", "send-mail", "telegram")):
            scores["exfiltration"] += 2
        if any(token in lowered for token in ("rm -rf", "del /f", "format", "shutdown", "cipher /w")):
            scores["destructive"] += 3

        best_type = max(scores, key=scores.get)
        if scores[best_type] == 0:
            return "automation", "automation and command execution"

        objectives = {
            "reconnaissance": "collect host and network reconnaissance",
            "payload_download": "download and execute external payloads",
            "credential_access": "attempt credential extraction",
            "persistence": "establish persistence on target host",
            "exfiltration": "collect and exfiltrate data",
            "destructive": "perform destructive or disruptive actions",
        }
        return best_type, objectives.get(best_type, "automation")

    @classmethod
    def _infer_badusb_target_os(cls, text: str) -> str:
        lowered = text.lower()
        windows_hits = sum(token in lowered for token in ("powershell", "cmd.exe", "reg add", "start menu", "win+r"))
        linux_hits = sum(token in lowered for token in ("bash", "terminal", "ifconfig", "apt", "systemctl"))
        mac_hits = sum(token in lowered for token in ("osascript", "open -a", "osascript", "defaults write"))

        hit_map = {"windows": windows_hits, "linux": linux_hits, "macos": mac_hits}
        best_os = max(hit_map, key=hit_map.get)

        if hit_map[best_os] == 0:
            return "unknown"
        non_zero = [name for name, value in hit_map.items() if value > 0]
        if len(non_zero) > 1:
            return "mixed"
        return best_os

    @classmethod
    def _extract_binary_artifacts(cls, text: str) -> list:
        pattern = r"[A-Za-z0-9_./\\-]+\.(?:exe|dll|bat|cmd|ps1|vbs|js|jar|msi|sh|py)"
        found = re.findall(pattern, text, flags=re.IGNORECASE)
        normalized = sorted({item.strip('"\'') for item in found})
        return normalized[:12]

    @classmethod
    def _extract_urls(cls, text: str) -> list:
        found = re.findall(r"https?://[^\s\"'<>]+", text, flags=re.IGNORECASE)
        normalized = sorted({item.rstrip('.,;') for item in found})
        return normalized[:10]

    @classmethod
    def _infer_requires_admin(cls, text: str) -> bool:
        lowered = text.lower()
        admin_hints = (
            "run as administrator",
            "uac",
            "net session",
            "reg add hklm",
            "schtasks /create",
            "sc create",
        )
        return any(token in lowered for token in admin_hints)

    @classmethod
    def _infer_ir_target_device(cls, file_stem: str, command: str) -> str:
        joined = f"{file_stem} {command}".lower()
        if any(token in joined for token in ("tv", "television")):
            return "tv"
        if any(token in joined for token in ("ac", "aircon", "air_conditioner", "climate")):
            return "air_conditioner"
        if any(token in joined for token in ("projector", "beamer")):
            return "projector"
        if any(token in joined for token in ("audio", "receiver", "soundbar", "speaker")):
            return "audio_system"
        if any(token in joined for token in ("camera", "cctv")):
            return "camera"
        return "general_consumer_ir"

    @classmethod
    def _infer_ir_profile(cls, frequency_hz: int, duty_cycle: str) -> str:
        if 36000 <= frequency_hz <= 40000:
            return "standard_consumer_ir"
        if frequency_hz >= 50000:
            return "high_frequency_ir"
        if duty_cycle and duty_cycle.strip():
            return "custom_duty_cycle"
        return "unknown"

    @classmethod
    def _extract_attack_indicators(cls, text: str) -> list:
        lowered = text.lower()
        found = []
        for token, normalized in cls.ATTACK_KEYWORDS.items():
            if token in lowered and normalized not in found:
                found.append(normalized)
        return found[:8]

    @classmethod
    def _count_network_targets(cls, text: str) -> int:
        if not text:
            return 0

        ssid_matches = re.findall(r"\bssid\b", text, flags=re.IGNORECASE)
        bssid_matches = re.findall(r"\bbssid\b", text, flags=re.IGNORECASE)
        mac_matches = re.findall(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", text, flags=re.IGNORECASE)
        count = len(ssid_matches) + len(bssid_matches) + len(set(mac_matches))
        return min(count, 9999)

    @classmethod
    def _count_keyword(cls, text: str, keyword: str) -> int:
        if not text:
            return 0
        return len(re.findall(re.escape(keyword), text, flags=re.IGNORECASE))

    @classmethod
    def _infer_wifi_artifact_kind(cls, file_path: Path, text: str) -> str:
        extension = file_path.suffix.lower()
        name = file_path.name.lower()
        lowered = text.lower()

        if extension in {".pcap", ".pcapng", ".cap"}:
            return "capture"
        if "handshake" in name or "handshake" in lowered:
            return "handshake_dump"
        if "scan" in name or "ap list" in lowered:
            return "scan_results"
        if "script" in name:
            return "script"
        if "log" in name:
            return "attack_log"
        return "unknown"

    @classmethod
    def _compact_preview(cls, text: str, max_length: int = 180) -> str:
        if not text:
            return ""
        collapsed = re.sub(r"\s+", " ", text).strip()
        if len(collapsed) <= max_length:
            return collapsed
        return f"{collapsed[: max_length - 3].rstrip()}..."

    @classmethod
    def _join_summary_parts(cls, parts) -> str:
        clean_parts = [str(part).strip() for part in parts if part and str(part).strip()]
        return " | ".join(clean_parts)

    @classmethod
    def _infer_nfc_protocol(cls, technology: str, text: str) -> str:
        joined = f"{technology} {text}".lower()
        if any(token in joined for token in ("mifare ultralight", "ultralight")):
            return "MIFARE Ultralight"
        if any(token in joined for token in ("mifare classic 1k", "mf_classic_1k", "classic 1k")):
            return "MIFARE Classic 1K"
        if any(token in joined for token in ("mifare classic 4k", "mf_classic_4k", "classic 4k")):
            return "MIFARE Classic 4K"
        if "ntag213" in joined:
            return "NTAG213"
        if "ntag215" in joined:
            return "NTAG215"
        if "ntag216" in joined:
            return "NTAG216"
        if "iso14443-4" in joined or "iso 14443-4" in joined:
            return "ISO14443-4"
        if "iso14443-3" in joined or "iso 14443-3" in joined:
            return "ISO14443-3"
        if "felica" in joined:
            return "FeliCa"
        return technology or "unknown"

    @classmethod
    def _infer_nfc_memory_layout(cls, text: str, technology: str) -> str:
        lowered = f"{technology} {text}".lower()
        sectors = re.search(r"(\d+)\s+sectors?", lowered)
        pages = re.search(r"(\d+)\s+pages?", lowered)
        blocks = re.search(r"(\d+)\s+blocks?", lowered)
        if sectors:
            return f"{sectors.group(1)} sectors"
        if pages:
            return f"{pages.group(1)} pages"
        if blocks:
            return f"{blocks.group(1)} blocks"
        if "1k" in lowered:
            return "1 KB"
        if "4k" in lowered:
            return "4 KB"
        if "ultralight" in lowered:
            return "page-based"
        return ""

    @classmethod
    def _infer_rfid_frequency_khz(cls, rfid_type: str, text: str) -> int:
        joined = f"{rfid_type} {text}".lower()
        explicit_match = re.search(r"(\d{2,5}(?:\.\d+)?)\s*(khz|mhz|hz)", joined)
        if explicit_match:
            raw_value = float(explicit_match.group(1))
            unit = explicit_match.group(2)
            if unit == "mhz":
                return int(round(raw_value * 1000))
            if unit == "hz":
                return int(round(raw_value / 1000))
            return int(round(raw_value))
        if any(token in joined for token in ("em4100", "hid prox", "indala", "t5577", "125 khz", "125khz")):
            return 125
        if any(token in joined for token in ("13.56 mhz", "13.56mhz", "mifare", "iso14443")):
            return 13560
        return 125

    @classmethod
    def _read_text_limited(cls, file_path: Path, max_bytes: int = None) -> str:
        read_limit = max_bytes or cls.MAX_TEXT_READ_BYTES
        try:
            with open(file_path, "rb") as stream:
                payload = stream.read(read_limit)
        except OSError:
            return ""

        for encoding in ("utf-8", "latin-1"):
            try:
                return payload.decode(encoding, errors="ignore")
            except LookupError:
                continue
        return ""

    @classmethod
    def _safe_int(cls, raw_value) -> int:
        if raw_value is None:
            return 0
        text = str(raw_value).strip().replace("_", "")
        match = re.search(r"-?\d+", text)
        if not match:
            return 0
        try:
            return int(match.group(0))
        except ValueError:
            return 0

    @classmethod
    def _safe_file_size(cls, file_path: Path) -> int:
        try:
            return int(file_path.stat().st_size)
        except OSError:
            return 0
