from __future__ import annotations

import ipaddress
import os
import re
from pathlib import Path
from urllib.parse import urlparse


class ToolNodeService:
    TOOL_NODE_TYPE = "tool_node"
    TOOL_MIME_TYPE = "application/x-beatrooter-tool"

    TOOL_SPECS = {
        "exiftool": {
            "name": "ExifTool",
            "description": "Extract metadata from files",
            "color": "#4ecdc4",
            "short": "EXF",
            "target_hint": "Connect a node with a valid file path or set Manual Target.",
            "target_placeholder": "Enter file path...",
            "target_type": "file",
            "result_node_type": "note",
        },
        "binwalk": {
            "name": "Binwalk",
            "description": "Firmware and embedded file analysis",
            "color": "#22d3ee",
            "short": "BIN",
            "target_hint": "Connect a node with a valid file path or set Manual Target.",
            "target_placeholder": "Enter firmware/binary path...",
            "target_type": "file",
            "result_node_type": "note",
        },
        "strings": {
            "name": "Strings",
            "description": "Extract printable strings from binaries",
            "color": "#38bdf8",
            "short": "STR",
            "target_hint": "Connect a node with a valid file path or set Manual Target.",
            "target_placeholder": "Enter file path...",
            "target_type": "file",
            "result_node_type": "note",
        },
        "steghide": {
            "name": "Steghide",
            "description": "Steganography embed/extract utility",
            "color": "#06b6d4",
            "short": "STG",
            "target_hint": "Connect a node with a valid file path or set Manual Target.",
            "target_placeholder": "Enter image/audio file path...",
            "target_type": "file",
            "result_node_type": "note",
        },
        "ghidra": {
            "name": "Ghidra",
            "description": "Reverse engineering suite",
            "color": "#3b82f6",
            "short": "GHD",
            "target_hint": "Connect a node with a valid file path or set Manual Target.",
            "target_placeholder": "Enter binary path (optional)...",
            "target_type": "file",
            "requires_target": False,
            "result_node_type": "note",
        },
        "gobuster": {
            "name": "Gobuster",
            "description": "Directory/file busting",
            "color": "#5eead4",
            "short": "GOB",
            "target_hint": "Connect a node with a URL/domain or set Manual Target.",
            "target_placeholder": "Enter target URL...",
            "target_type": "url",
            "result_node_type": "note",
        },
        "whatweb": {
            "name": "WhatWeb",
            "description": "Web technology fingerprinting",
            "color": "#14b8a6",
            "short": "WWB",
            "target_hint": "Connect a node with a URL/domain or set Manual Target.",
            "target_placeholder": "Enter target URL/domain...",
            "target_type": "url",
            "result_node_type": "note",
        },
        "sqlmap": {
            "name": "SQLmap",
            "description": "Automated SQL injection testing",
            "color": "#2dd4bf",
            "short": "SQL",
            "target_hint": "Connect a node with a URL/domain or set Manual Target.",
            "target_placeholder": "Enter injectable URL...",
            "target_type": "url",
            "result_node_type": "note",
        },
        "searchsploit": {
            "name": "Searchsploit",
            "description": "Offline exploit-db search",
            "color": "#99f6e4",
            "short": "SXP",
            "target_hint": "Set a search term in Manual Target, or connect a node with relevant text.",
            "target_placeholder": "Enter search query...",
            "target_type": "generic",
            "result_node_type": "note",
        },
        "nmap": {
            "name": "Nmap",
            "description": "Network discovery",
            "color": "#34d399",
            "short": "NMP",
            "target_hint": "Connect a node with an IP, host, URL or CIDR or set Manual Target.",
            "target_placeholder": "Enter IP/hostname/CIDR...",
            "target_type": "network",
            "result_node_type": "note",
        },
        "masscan": {
            "name": "Masscan",
            "description": "Fast port scanner",
            "color": "#f59e0b",
            "short": "MSC",
            "target_hint": "Connect a node with an IP or CIDR or set Manual Target.",
            "target_placeholder": "Enter IP/CIDR...",
            "target_type": "network_strict",
            "result_node_type": "note",
        },
        "enum4linux": {
            "name": "Enum4linux",
            "description": "SMB/NetBIOS enumeration",
            "color": "#22c55e",
            "short": "E4L",
            "target_hint": "Connect a node with an IP/host or set Manual Target.",
            "target_placeholder": "Enter target IP/hostname...",
            "target_type": "network",
            "result_node_type": "note",
        },
        "rpcclient": {
            "name": "RPCClient",
            "description": "RPC enumeration for SMB targets",
            "color": "#16a34a",
            "short": "RPC",
            "target_hint": "Connect a node with an IP/host or set Manual Target.",
            "target_placeholder": "Enter target IP/hostname...",
            "target_type": "network",
            "result_node_type": "note",
        },
        "netcat": {
            "name": "Netcat",
            "description": "TCP/UDP connectivity and shells",
            "color": "#4ade80",
            "short": "NCT",
            "target_hint": "Connect a node with an IP/host or set Manual Target.",
            "target_placeholder": "Enter target host...",
            "target_type": "network",
            "result_node_type": "note",
        },
        "hydra": {
            "name": "Hydra",
            "description": "Parallel login brute force",
            "color": "#84cc16",
            "short": "HYD",
            "target_hint": "Connect a node with an IP/host or set Manual Target.",
            "target_placeholder": "Enter target host/service...",
            "target_type": "network",
            "result_node_type": "note",
        },
        "patator": {
            "name": "Patator",
            "description": "Modular brute force framework",
            "color": "#bef264",
            "short": "PAT",
            "target_hint": "Connect a node with target details or set Manual Target.",
            "target_placeholder": "Enter target (optional with module options)...",
            "target_type": "generic",
            "result_node_type": "note",
        },
        "nslookup": {
            "name": "NSLookup/Dig",
            "description": "DNS queries",
            "color": "#60a5fa",
            "short": "DNS",
            "target_hint": "Connect a node with a domain/IP or set Manual Target.",
            "target_placeholder": "Enter domain/IP...",
            "target_type": "dns",
            "command_name": "nslookup",
            "hidden": True,
            "result_node_type": "note",
        },
        "dnsutils": {
            "name": "DNS Utils (nslookup/dig)",
            "description": "DNS queries and diagnostics",
            "color": "#93c5fd",
            "short": "DNS",
            "target_hint": "Connect a node with a domain/IP or set Manual Target.",
            "target_placeholder": "Enter domain/IP...",
            "target_type": "dns",
            "command_name": "nslookup",
            "result_node_type": "note",
        },
        "sublist3r": {
            "name": "Sublist3r",
            "description": "Subdomain enumeration",
            "color": "#a78bfa",
            "short": "SUB",
            "target_hint": "Connect a node with a valid domain or set Manual Target.",
            "target_placeholder": "Enter domain...",
            "target_type": "dns_domain",
            "result_node_type": "note",
        },
        "whois": {
            "name": "Whois",
            "description": "Domain information",
            "color": "#f472b6",
            "short": "WHO",
            "target_hint": "Connect a node with a valid domain or set Manual Target.",
            "target_placeholder": "Enter domain...",
            "target_type": "dns_domain",
            "result_node_type": "note",
        },
        "hashcat": {
            "name": "Hashcat",
            "description": "High-performance hash cracking",
            "color": "#fb7185",
            "short": "HSH",
            "target_hint": "Connect a node with a hash/hashfile path or set Manual Target.",
            "target_placeholder": "Enter hash or hashfile path...",
            "target_type": "generic",
            "result_node_type": "note",
        },
        "john": {
            "name": "John the Ripper",
            "description": "Password/hash cracking",
            "color": "#f43f5e",
            "short": "JHN",
            "target_hint": "Connect a node with a hash/hashfile path or set Manual Target.",
            "target_placeholder": "Enter hashfile path...",
            "target_type": "file",
            "result_node_type": "note",
        },
        "cupp": {
            "name": "CUPP",
            "description": "Custom wordlist generator",
            "color": "#eab308",
            "short": "CUP",
            "target_hint": "Set Manual Target with context (or run with options like -i).",
            "target_placeholder": "Enter context/target (optional)...",
            "target_type": "generic",
            "requires_target": False,
            "result_node_type": "note",
        },
        "linpeas": {
            "name": "LinPEAS",
            "description": "Linux privilege escalation checks",
            "color": "#a3e635",
            "short": "LPE",
            "target_hint": "No target required. Use options when needed.",
            "target_placeholder": "Target not required",
            "target_type": "none",
            "requires_target": False,
            "result_node_type": "note",
        },
        "revshellgen": {
            "name": "RevShellGen",
            "description": "Reverse shell generator",
            "color": "#facc15",
            "short": "RSG",
            "target_hint": "No target required. Use options to define IP/port/payload.",
            "target_placeholder": "Target optional (use options)...",
            "target_type": "none",
            "requires_target": False,
            "result_node_type": "note",
        },
        "tshark": {
            "name": "TShark",
            "description": "Packet capture and analysis",
            "color": "#60a5fa",
            "short": "TSH",
            "target_hint": "Define um target: interface (ex: eth0/wlan0) ou ficheiro .pcap/.pcapng.",
            "target_placeholder": "Enter interface (eth0) ou path .pcap...",
            "target_type": "generic",
            "requires_target": True,
            "result_node_type": "note",
        },
        "wifite": {
            "name": "Wifite",
            "description": "Automated Wi-Fi auditing",
            "color": "#818cf8",
            "short": "WIF",
            "target_hint": "No target required. Use options for channel/BSSID control.",
            "target_placeholder": "Target optional (use options)...",
            "target_type": "none",
            "requires_target": False,
            "result_node_type": "note",
        },
    }

    NETWORK_KEYS = (
        "ip_address",
        "ip",
        "address",
        "target_ip",
        "source_ip",
        "destination_ip",
        "host",
        "hostname",
        "target",
        "cidr",
        "network",
        "name",
        "domain",
        "url",
    )
    URL_KEYS = ("url", "target_url", "base_url", "website", "endpoint_url", "target")
    DOMAIN_KEYS = ("domain", "fqdn", "hostname", "host", "common_name", "name", "url", "target", "address")
    FILE_KEYS = ("file_path", "path", "local_path", "relative_path", "workspace_path", "target")

    @classmethod
    def list_tool_names(cls, include_hidden: bool = False) -> list[str]:
        if include_hidden:
            return list(cls.TOOL_SPECS.keys())
        return [name for name, spec in cls.TOOL_SPECS.items() if not spec.get("hidden")]

    @classmethod
    def get_tool_spec(cls, tool_name: str) -> dict:
        return cls.TOOL_SPECS.get(tool_name, {})

    @classmethod
    def get_tool_target_placeholder(cls, tool_name: str) -> str:
        return cls.get_tool_spec(tool_name).get("target_placeholder", "Enter target...")

    @classmethod
    def get_tool_command_name(cls, tool_name: str) -> str:
        spec = cls.get_tool_spec(tool_name)
        return str(spec.get("command_name", tool_name)).strip().lower()

    @classmethod
    def tool_requires_target(cls, tool_name: str) -> bool:
        return bool(cls.get_tool_spec(tool_name).get("requires_target", True))

    @classmethod
    def is_tool_node(cls, node_or_type) -> bool:
        if hasattr(node_or_type, "type"):
            return getattr(node_or_type, "type", None) == cls.TOOL_NODE_TYPE
        return node_or_type == cls.TOOL_NODE_TYPE

    @classmethod
    def create_tool_node_data(cls, tool_name: str) -> dict:
        spec = cls.get_tool_spec(tool_name)
        requires_target = cls.tool_requires_target(tool_name)
        default_reason = (
            spec.get("target_hint", "Connect a compatible node.")
            if requires_target
            else "No target required for this tool."
        )
        return {
            "is_tool_node": True,
            "tool_name": tool_name,
            "display_name": spec.get("name", tool_name.title()),
            "description": spec.get("description", ""),
            "manual_target": "",
            "resolved_target": "",
            "target_source_node_id": "",
            "target_source_label": "",
            "compatible": not requires_target,
            "compatibility_reason": default_reason,
            "options": "",
            "custom_command": "",
            "last_status": "idle",
            "last_exit_code": "",
            "last_run_at": "",
            "last_command": "",
            "last_output": "",
            "last_output_preview": "",
            "last_output_size": 0,
            "last_error": "",
            "has_output": False,
            "output_summary": "Awaiting execution",
            "created_node_ids": [],
            "notes": "",
        }

    @classmethod
    def get_tool_display_name(cls, tool_name: str) -> str:
        return cls.get_tool_spec(tool_name).get("name", tool_name.title())

    @classmethod
    def get_tool_color(cls, tool_name: str) -> str:
        return cls.get_tool_spec(tool_name).get("color", "#7aa2f7")

    @classmethod
    def get_tool_short_label(cls, tool_name: str) -> str:
        short = cls.get_tool_spec(tool_name).get("short")
        if short:
            return short
        return tool_name[:3].upper()

    @classmethod
    def refresh_tool_node_state(cls, graph_manager, tool_node) -> dict:
        resolution = cls.resolve_target(graph_manager, tool_node)
        tool_node.data["compatible"] = resolution["compatible"]
        tool_node.data["resolved_target"] = resolution["target"]
        tool_node.data["target_source_node_id"] = resolution["source_node_id"]
        tool_node.data["target_source_label"] = resolution["source_label"]
        tool_node.data["compatibility_reason"] = resolution["reason"]
        return resolution

    @classmethod
    def resolve_target(cls, graph_manager, tool_node) -> dict:
        tool_name = str(tool_node.data.get("tool_name", "")).strip().lower()
        requires_target = cls.tool_requires_target(tool_name)
        manual_target = str(tool_node.data.get("manual_target", "") or "").strip()
        if manual_target:
            return {
                "compatible": True,
                "target": manual_target,
                "source_node_id": "",
                "source_label": "Manual Target",
                "reason": "Running with Manual Target override.",
            }

        if not graph_manager or not tool_name:
            return {
                "compatible": not requires_target,
                "target": "",
                "source_node_id": "",
                "source_label": "",
                "reason": (
                    cls.get_tool_spec(tool_name).get("target_hint", "Connect a compatible node.")
                    if requires_target
                    else "No target required for this tool."
                ),
            }

        connected_nodes = graph_manager.get_connected_nodes(tool_node.id)
        for connected_node in connected_nodes:
            if cls.is_tool_node(connected_node):
                continue
            if str(connected_node.data.get("generated_by_tool_id", "") or "").strip() == tool_node.id:
                continue
            candidate = cls.extract_target_for_tool(tool_name, connected_node)
            if not candidate:
                continue
            return {
                "compatible": True,
                "target": candidate["target"],
                "source_node_id": connected_node.id,
                "source_label": candidate["label"],
                "reason": f"Resolved from {connected_node.type}.",
            }

        if not requires_target:
            return {
                "compatible": True,
                "target": "",
                "source_node_id": "",
                "source_label": "",
                "reason": "No target required for this tool.",
            }

        return {
            "compatible": False,
            "target": "",
            "source_node_id": "",
            "source_label": "",
            "reason": cls.get_tool_spec(tool_name).get("target_hint", "Connect a compatible node."),
        }

    @classmethod
    def extract_target_for_tool(cls, tool_name: str, node) -> dict | None:
        tool_name = str(tool_name or "").lower()
        if tool_name in {"exiftool", "binwalk", "strings", "steghide", "ghidra", "john"}:
            return cls._extract_file_target(node)
        if tool_name == "tshark":
            return cls._extract_tshark_target(node)
        if tool_name in {"gobuster", "whatweb", "sqlmap"}:
            return cls._extract_url_target(node)
        if tool_name in {"nmap", "enum4linux", "rpcclient", "netcat", "hydra"}:
            return cls._extract_network_target(node, allow_domain=True)
        if tool_name == "masscan":
            return cls._extract_network_target(node, allow_domain=False)
        if tool_name in {"nslookup", "dnsutils"}:
            return cls._extract_dns_target(node, allow_ip=True)
        if tool_name in {"sublist3r", "whois"}:
            return cls._extract_dns_target(node, allow_ip=False)
        if tool_name in {"searchsploit", "hashcat", "cupp", "patator"}:
            return cls._extract_generic_target(node)
        return None

    @classmethod
    def _extract_tshark_target(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}

        # Prefer explicit capture interface fields when present.
        interface_fields = ("interface", "capture_interface", "network_interface", "adapter")
        for field_name in interface_fields:
            value = str(data.get(field_name, "") or "").strip()
            if value:
                return {"target": value, "label": field_name.replace("_", " ").title()}

        # Accept capture files if provided by connected nodes.
        file_fields = ("pcap_path", "capture_file", "file_path", "path")
        for field_name in file_fields:
            value = str(data.get(field_name, "") or "").strip()
            if not value:
                continue
            lower_value = value.lower()
            if lower_value.endswith((".pcap", ".pcapng", ".cap")):
                return {"target": value, "label": field_name.replace("_", " ").title()}

        # Fallback to generic target fields (manual labels, etc.).
        return cls._extract_generic_target(node)

    @classmethod
    def _extract_generic_target(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}
        generic_keys = (
            "target",
            "name",
            "title",
            "query",
            "keyword",
            "domain",
            "url",
            "path",
            "file_path",
            "ip_address",
            "host",
        )
        for field_name in generic_keys:
            value = str(data.get(field_name, "") or "").strip()
            if value:
                return {"target": value, "label": field_name.replace("_", " ").title()}
        return None

    @classmethod
    def summarize_created_nodes(cls, created_nodes: list) -> str:
        if not created_nodes:
            return "No structured nodes were generated from the output."

        counts = {}
        for node in created_nodes:
            counts[node.type] = counts.get(node.type, 0) + 1

        ordered = ", ".join(f"{node_type}: {count}" for node_type, count in sorted(counts.items()))
        return f"Generated {len(created_nodes)} node(s) ({ordered})."

    @classmethod
    def build_fallback_result_data(cls, tool_name: str, target: str, output_text: str, exit_code: int) -> dict:
        clean_lines = [line.strip() for line in output_text.splitlines() if line.strip()]
        preview = clean_lines[:8]
        return {
            "title": f"{cls.get_tool_display_name(tool_name)} Result",
            "summary": f"Target: {target or 'unknown'}",
            "status": "completed" if exit_code == 0 else "error",
            "severity": "info",
            "notes": "\n".join(preview) if preview else "No output captured.",
        }

    @classmethod
    def _extract_file_target(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}

        direct_fields = ("file_path", "path", "local_path")
        for field_name in direct_fields:
            file_path = str(data.get(field_name, "") or "").strip()
            if file_path and os.path.exists(file_path):
                return {"target": file_path, "label": field_name.replace("_", " ").title()}

        relative_path = str(data.get("relative_path", "") or "").strip()
        workspace_path = str(data.get("workspace_path", "") or "").strip()
        if relative_path and workspace_path:
            combined = str(Path(workspace_path) / relative_path)
            if os.path.exists(combined):
                return {"target": combined, "label": "Workspace File"}

        for field_name in cls.FILE_KEYS:
            file_path = str(data.get(field_name, "") or "").strip()
            if file_path and os.path.exists(file_path):
                return {"target": file_path, "label": field_name.replace("_", " ").title()}

        return None

    @classmethod
    def _extract_url_target(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}
        for field_name in cls.URL_KEYS:
            raw_value = str(data.get(field_name, "") or "").strip()
            url_value = cls._normalize_url(raw_value)
            if url_value:
                return {"target": url_value, "label": field_name.replace("_", " ").title()}

        domain_candidate = cls._extract_dns_target(node, allow_ip=False)
        if domain_candidate:
            return {
                "target": cls._normalize_url(domain_candidate["target"]),
                "label": domain_candidate["label"],
            }

        network_candidate = cls._extract_network_target(node, allow_domain=True)
        if network_candidate:
            return {
                "target": cls._normalize_url(network_candidate["target"]),
                "label": network_candidate["label"],
            }

        return None

    @classmethod
    def _extract_network_target(cls, node, allow_domain: bool) -> dict | None:
        data = getattr(node, "data", {}) or {}
        for field_name in cls.NETWORK_KEYS:
            value = str(data.get(field_name, "") or "").strip()
            if not value:
                continue

            if field_name == "url":
                parsed_host = cls._host_from_url(value)
                if parsed_host:
                    value = parsed_host

            if cls._is_ip_or_cidr(value):
                return {"target": value, "label": field_name.replace("_", " ").title()}

            if allow_domain and cls._is_valid_host(value):
                return {"target": value, "label": field_name.replace("_", " ").title()}

        return None

    @classmethod
    def _extract_dns_target(cls, node, allow_ip: bool) -> dict | None:
        data = getattr(node, "data", {}) or {}
        for field_name in cls.DOMAIN_KEYS:
            value = str(data.get(field_name, "") or "").strip()
            if not value:
                continue

            if field_name == "url":
                host_value = cls._host_from_url(value)
                if not host_value:
                    continue
                value = host_value

            if cls._is_domain(value):
                return {"target": value, "label": field_name.replace("_", " ").title()}

            if allow_ip and cls._is_ip_or_cidr(value):
                return {"target": value, "label": field_name.replace("_", " ").title()}

        return None

    @classmethod
    def _normalize_url(cls, value: str) -> str:
        value = str(value or "").strip()
        if not value:
            return ""

        if value.startswith(("http://", "https://")):
            parsed = urlparse(value)
            return value if parsed.netloc else ""

        if cls._is_valid_host(value) or cls._is_ip_or_cidr(value):
            return f"http://{value}"
        return ""

    @classmethod
    def _host_from_url(cls, value: str) -> str:
        try:
            parsed = urlparse(value)
        except Exception:
            return ""

        return (parsed.hostname or "").strip()

    @classmethod
    def _is_ip_or_cidr(cls, value: str) -> bool:
        try:
            ipaddress.ip_network(value, strict=False)
            return True
        except ValueError:
            return False

    @classmethod
    def _is_valid_host(cls, value: str) -> bool:
        value = str(value or "").strip()
        if not value:
            return False
        if value.startswith(("http://", "https://")):
            value = cls._host_from_url(value)
        if not value:
            return False
        if cls._is_ip_or_cidr(value):
            return True
        if value.lower() == "localhost":
            return True
        if " " in value or "/" in value:
            return False
        return bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]", value))

    @classmethod
    def _is_domain(cls, value: str) -> bool:
        value = str(value or "").strip().rstrip(".")
        if not value or "." not in value:
            return False
        if cls._is_ip_or_cidr(value):
            return False
        return bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,63}", value))
