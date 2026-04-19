from __future__ import annotations

import ipaddress
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from features.wordlists.core.wordlist_service import WordlistService


class ToolNodeService:
    TOOL_NODE_TYPE = "tool_node"
    TOOL_MIME_TYPE = "application/x-beatrooter-tool"
    BASE_TOOL_WARNING_TEMPLATE = {
        "color": "#f59e0b",
        "category": "networking_assessment",
        "default_data": {
            "target": "",
            "warning": "",
            "context": "",
            "recommendation": "",
            "raw_excerpt": "",
            "notes": "",
        },
        "removed_fields": [
            "title",
            "summary",
            "owner",
            "asset_ref",
            "tags",
            "status",
            "severity",
            "confidence",
            "environment",
            "exposure",
            "data_classification",
        ],
        "hidden_fields": ["notes", "generated_by_tool_id"],
        "field_labels": {
            "target": "Alvo",
            "warning": "Aviso",
            "context": "Contexto",
            "recommendation": "Proximo passo",
            "raw_excerpt": "Saida bruta",
        },
        "preview_fields": ("target", "warning", "context", "recommendation"),
        "preview_prefixes": {
            "target": "Target",
            "warning": "Aviso",
            "context": "Contexto",
            "recommendation": "Proximo",
        },
    }
    BASE_TOOL_RESULT_TEMPLATE = {
        "color": "#84cc16",
        "category": "networking_assessment",
        "default_data": {
            "target": "",
            "service": "",
            "outcome": "",
            "credentials": "",
            "attempt_summary": "",
            "recommendation": "",
            "raw_excerpt": "",
            "notes": "",
        },
        "removed_fields": [
            "title",
            "summary",
            "owner",
            "asset_ref",
            "tags",
            "status",
            "severity",
            "confidence",
            "environment",
            "exposure",
            "data_classification",
        ],
        "hidden_fields": ["notes", "generated_by_tool_id"],
        "field_labels": {
            "target": "Alvo",
            "service": "Servico",
            "outcome": "Resultado",
            "credentials": "Credenciais",
            "attempt_summary": "Resumo da execucao",
            "recommendation": "Proximo passo",
            "raw_excerpt": "Saida bruta",
        },
        "preview_fields": ("target", "outcome", "credentials", "attempt_summary"),
        "preview_prefixes": {
            "target": "Target",
            "outcome": "Resultado",
            "credentials": "Creds",
            "attempt_summary": "Exec",
        },
    }
    BASE_TOOL_ERROR_TEMPLATE = {
        "color": "#ef4444",
        "category": "networking_assessment",
        "default_data": {
            "target": "",
            "error": "",
            "fix": "",
            "raw_excerpt": "",
            "notes": "",
        },
        "removed_fields": [
            "title",
            "summary",
            "owner",
            "asset_ref",
            "tags",
            "status",
            "severity",
            "confidence",
            "environment",
            "exposure",
            "data_classification",
        ],
        "hidden_fields": ["notes", "generated_by_tool_id"],
        "field_labels": {
            "target": "Alvo",
            "error": "Erro",
            "fix": "Como resolver",
            "raw_excerpt": "Saida bruta",
        },
        "preview_fields": ("target", "error", "fix", "raw_excerpt"),
        "preview_prefixes": {
            "target": "Target",
            "error": "Erro",
            "fix": "Fix",
            "raw_excerpt": "Raw",
        },
    }
    TOOL_ERROR_NODE_TEMPLATES = {
        "enum4linux": {
            "node_type": "enum4linux_error",
            "name": "Enum4linux Error",
            "symbol": "[SMB!]",
            "preview_prefixes": {
                "target": "SMB",
                "error": "Erro",
                "fix": "Fix",
                "raw_excerpt": "Raw",
            },
        },
        "hydra": {
            "node_type": "hydra_error",
            "name": "Hydra Error",
            "symbol": "[HYD!]",
            "preview_prefixes": {
                "target": "Hydra",
                "error": "Erro",
                "fix": "Fix",
                "raw_excerpt": "Raw",
            },
        },
        "rpcclient": {
            "node_type": "rpcclient_error",
            "name": "RPCClient Error",
            "symbol": "[RPC!]",
            "preview_prefixes": {
                "target": "SMB/RPC",
                "error": "Erro",
                "fix": "Fix",
                "raw_excerpt": "Raw",
            },
        },
    }
    TOOL_RESULT_NODE_TEMPLATES = {
        "hydra": {
            "node_type": "hydra_result",
            "name": "Hydra Result",
            "symbol": "[HYD]",
            "preview_prefixes": {
                "target": "Hydra",
                "outcome": "Resultado",
                "credentials": "Creds",
                "attempt_summary": "Exec",
            },
        },
    }
    RESULT_NODE_TYPE_TEMPLATES = {}
    TOOL_WARNING_NODE_TEMPLATES = {
        "hydra": {
            "node_type": "hydra_warning",
            "name": "Hydra Warning",
            "symbol": "[HYDW]",
            "preview_prefixes": {
                "target": "Hydra",
                "warning": "Aviso",
                "context": "Contexto",
                "recommendation": "Proximo",
            },
        },
    }

    TOOL_SIDEBAR_LAYOUT = (
        {
            "key": "target",
            "label": "Tools Target",
            "description": "Ferramentas orientadas a um alvo explícito.",
            "accent": "#22c55e",
            "subgroups": (
                {
                    "label": "Network / Infra",
                    "tools": ("nmap", "masscan", "enum4linux", "rpcclient", "netcat", "hydra"),
                },
                {
                    "label": "Web / DNS",
                    "tools": ("gobuster", "whatweb", "sqlmap", "dnsutils", "subfinder", "amass", "whois"),
                },
                {
                    "label": "File / Reverse / Forensics",
                    "tools": ("exiftool", "binwalk", "strings", "steghide", "john"),
                },
                {
                    "label": "Capture / Traffic",
                    "tools": ("tshark",),
                },
            ),
        },
        {
            "key": "interaction",
            "label": "Tools Interaction",
            "description": "Ferramentas orientadas a contexto, geração ou execução assistida.",
            "accent": "#8b5cf6",
            "subgroups": (
                {
                    "label": "Research / Search",
                    "tools": ("searchsploit",),
                },
                {
                    "label": "Generation / Wordlists",
                    "tools": ("cupp", "revshellgen"),
                },
                {
                    "label": "Execution / Context",
                    "tools": ("patator", "hashcat", "ghidra"),
                },
                {
                    "label": "Local / PrivEsc / Wi-Fi",
                    "tools": ("linpeas", "wifite"),
                },
            ),
        },
    )

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
            "wordlist_required": True,
            "wordlist_hint": "Connect a Wordlists node with a directories or generic list.",
            "wordlist_kinds": ("directories", "generic"),
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
            "target_hint": "Connect an Exploit/Vulnerability/Port-Service/Note node, or set Manual Target.",
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
            "wordlist_required": "conditional",
            "wordlist_hint": "Connect a Wordlists node com passwords/generic quando nao definires -p, -x, -e, -P ou -C.",
            "wordlist_kinds": ("passwords", "generic"),
            "result_node_type": "hydra_result",
        },
        "patator": {
            "name": "Patator",
            "description": "Modular brute force framework",
            "color": "#bef264",
            "short": "PAT",
            "target_hint": "Connect a Host/Domain/Web/Port-Service node with target details or set Manual Target.",
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
        "subfinder": {
            "name": "Subfinder",
            "description": "Passive subdomain enumeration",
            "color": "#a78bfa",
            "short": "SUB",
            "target_hint": "Connect a node with a valid domain or set Manual Target.",
            "target_placeholder": "Enter domain...",
            "target_type": "dns_domain",
            "result_node_type": "note",
        },
        "amass": {
            "name": "Amass",
            "description": "Asset discovery and subdomain enumeration",
            "color": "#c084fc",
            "short": "AMA",
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
            "target_hint": "Connect a Credential/IOC node with a hash, a hash file node, or set Manual Target.",
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
            "target_hint": "Ferramenta interativa: execute num terminal com TTY real. O runner embutido só mostra estado/erros.",
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
    def get_tool_sidebar_sections(cls, include_hidden: bool = False) -> list[dict]:
        sections = []
        for section in cls.TOOL_SIDEBAR_LAYOUT:
            groups = []
            tool_total = 0
            for subgroup in section.get("subgroups", ()):
                tools = []
                for tool_name in subgroup.get("tools", ()):
                    spec = cls.get_tool_spec(tool_name)
                    if not spec:
                        continue
                    if spec.get("hidden") and not include_hidden:
                        continue
                    tools.append(tool_name)
                if tools:
                    tool_total += len(tools)
                    groups.append({"label": subgroup["label"], "tools": tools})
            if groups:
                sections.append(
                    {
                        "key": section["key"],
                        "label": section["label"],
                        "description": section.get("description", ""),
                        "accent": section.get("accent", "#7aa2f7"),
                        "tool_count": tool_total,
                        "group_count": len(groups),
                        "groups": groups,
                    }
                )
        return sections

    @classmethod
    def get_tool_sidebar_group(cls, tool_name: str) -> str:
        tool_name = str(tool_name or "").strip().lower()
        for section in cls.TOOL_SIDEBAR_LAYOUT:
            for subgroup in section.get("subgroups", ()):
                if tool_name in subgroup.get("tools", ()):
                    return subgroup["label"]
        return "Other"

    @classmethod
    def get_tool_sidebar_section(cls, tool_name: str) -> str:
        tool_name = str(tool_name or "").strip().lower()
        for section in cls.TOOL_SIDEBAR_LAYOUT:
            for subgroup in section.get("subgroups", ()):
                if tool_name in subgroup.get("tools", ()):
                    return section["key"]
        return "interaction"

    @classmethod
    def list_tool_names(cls, include_hidden: bool = False) -> list[str]:
        if include_hidden:
            return list(cls.TOOL_SPECS.keys())
        return [name for name, spec in cls.TOOL_SPECS.items() if not spec.get("hidden")]

    @classmethod
    def get_tool_spec(cls, tool_name: str) -> dict:
        if str(tool_name or "").strip().lower() == "sublist3r":
            tool_name = "subfinder"
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
    def tool_supports_wordlist(cls, tool_name: str) -> bool:
        spec = cls.get_tool_spec(tool_name)
        return bool(spec.get("wordlist_required"))

    @classmethod
    def tool_requires_wordlist(cls, tool_name: str, options: str = "") -> bool:
        spec = cls.get_tool_spec(tool_name)
        requirement = spec.get("wordlist_required")
        if requirement is True:
            return True
        if requirement == "conditional":
            return cls._tool_conditionally_requires_wordlist(tool_name, options)
        return False

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
            "resolved_wordlist_node_id": "",
            "resolved_wordlist_label": "",
            "resolved_wordlist_name": "",
            "wordlist_compatible": not cls.tool_supports_wordlist(tool_name),
            "wordlist_reason": (
                "No wordlist required for this tool."
                if not cls.tool_supports_wordlist(tool_name)
                else cls.get_tool_spec(tool_name).get("wordlist_hint", "Connect a compatible Wordlists node.")
            ),
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
        wordlist_resolution = cls.resolve_wordlist(graph_manager, tool_node)
        tool_node.data["wordlist_compatible"] = wordlist_resolution["compatible"]
        tool_node.data["resolved_wordlist_node_id"] = wordlist_resolution["source_node_id"]
        tool_node.data["resolved_wordlist_label"] = wordlist_resolution["source_label"]
        tool_node.data["resolved_wordlist_name"] = wordlist_resolution["wordlist_name"]
        tool_node.data["wordlist_reason"] = wordlist_resolution["reason"]
        tool_node.data["compatible"] = bool(resolution["compatible"] and wordlist_resolution["compatible"])
        tool_node.data["resolved_target"] = resolution["target"]
        tool_node.data["target_source_node_id"] = resolution["source_node_id"]
        tool_node.data["target_source_label"] = resolution["source_label"]
        tool_node.data["compatibility_reason"] = cls._compose_tool_compatibility_reason(
            tool_node,
            resolution,
            wordlist_resolution,
        )
        return {
            **resolution,
            "compatible": tool_node.data["compatible"],
            "wordlist": wordlist_resolution,
            "reason": tool_node.data["compatibility_reason"],
        }

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
        if cls.get_tool_command_name(tool_name) == "hydra":
            hydra_resolution = cls._resolve_hydra_target(connected_nodes, tool_node.id)
            if hydra_resolution:
                return hydra_resolution

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
    def resolve_wordlist(cls, graph_manager, tool_node) -> dict:
        tool_name = str(tool_node.data.get("tool_name", "")).strip().lower()
        options = str(tool_node.data.get("options", "") or "").strip()
        requires_wordlist = cls.tool_requires_wordlist(tool_name, options)
        supports_wordlist = cls.tool_supports_wordlist(tool_name)
        wordlist_hint = cls.get_tool_spec(tool_name).get("wordlist_hint", "Connect a compatible Wordlists node.")

        if not tool_name or not supports_wordlist:
            return {
                "compatible": True,
                "source_node_id": "",
                "source_label": "",
                "wordlist_name": "",
                "reason": "No wordlist required for this tool.",
            }

        if not graph_manager:
            return {
                "compatible": not requires_wordlist,
                "source_node_id": "",
                "source_label": "",
                "wordlist_name": "",
                "reason": wordlist_hint if requires_wordlist else "Wordlist association is optional for this tool.",
            }

        connected_nodes = graph_manager.get_connected_nodes(tool_node.id)
        compatible_node = None
        incompatible_reason = ""

        for connected_node in connected_nodes:
            if cls.is_tool_node(connected_node) or getattr(connected_node, "type", "") != "wordlists":
                continue

            inspection = WordlistService.inspect_node_data(getattr(connected_node, "data", {}) or {})
            if not inspection["valid"]:
                incompatible_reason = inspection["reason"]
                continue

            wordlist_kind = inspection["kind"]
            if not cls._is_wordlist_kind_compatible(tool_name, wordlist_kind):
                incompatible_reason = (
                    f"Connected wordlist kind '{wordlist_kind}' is not compatible with "
                    f"{cls.get_tool_display_name(tool_name)}."
                )
                continue

            compatible_node = connected_node
            break

        if compatible_node is not None:
            return {
                "compatible": True,
                "source_node_id": compatible_node.id,
                "source_label": "Wordlists Node",
                "wordlist_name": str(compatible_node.data.get("name", "") or compatible_node.data.get("source_label", "") or "wordlist").strip(),
                "reason": f"Resolved from connected {compatible_node.type} node.",
            }

        if not requires_wordlist:
            return {
                "compatible": True,
                "source_node_id": "",
                "source_label": "",
                "wordlist_name": "",
                "reason": "Wordlist association is optional for this tool.",
            }

        return {
            "compatible": False,
            "source_node_id": "",
            "source_label": "",
            "wordlist_name": "",
            "reason": incompatible_reason or wordlist_hint,
        }

    @classmethod
    def resolve_hydra_login(cls, graph_manager, tool_node) -> dict:
        tool_name = str(tool_node.data.get("tool_name", "")).strip().lower()
        if cls.get_tool_command_name(tool_name) != "hydra":
            return {
                "compatible": True,
                "login": "",
                "source_node_id": "",
                "source_label": "",
                "reason": "Hydra login resolution is not required for this tool.",
            }

        options = str(tool_node.data.get("options", "") or "").strip()
        option_parts = cls._split_cli(options)
        if cls._cli_has_value(option_parts, "-l") or cls._cli_has_value(option_parts, "-L") or cls._cli_has_value(option_parts, "-C"):
            return {
                "compatible": True,
                "login": "",
                "source_node_id": "",
                "source_label": "Options",
                "reason": "Hydra login already defined in Options.",
            }

        if not graph_manager:
            return {
                "compatible": False,
                "login": "",
                "source_node_id": "",
                "source_label": "",
                "reason": "Connect a User or Credential node, or define -l/-L/-C in Options.",
            }

        connected_nodes = graph_manager.get_connected_nodes(tool_node.id)
        for connected_node in connected_nodes:
            if cls.is_tool_node(connected_node):
                continue
            candidate = cls._extract_hydra_login_candidate(connected_node)
            if not candidate:
                continue
            return {
                "compatible": True,
                "login": candidate["login"],
                "source_node_id": connected_node.id,
                "source_label": candidate["label"],
                "reason": f"Resolved Hydra login from connected {connected_node.type} node.",
            }

        return {
            "compatible": False,
            "login": "",
            "source_node_id": "",
            "source_label": "",
            "reason": "Hydra requires a login source. Connect a User/Credential node or define -l/-L/-C in Options.",
        }

    @classmethod
    def _resolve_hydra_target(cls, connected_nodes, tool_node_id: str) -> dict | None:
        host_candidate = None
        service_candidate = None
        host_source_node_id = ""
        service_source_node_id = ""
        host_source_label = ""
        service_source_label = ""

        for connected_node in connected_nodes:
            if cls.is_tool_node(connected_node):
                continue
            if str(connected_node.data.get("generated_by_tool_id", "") or "").strip() == tool_node_id:
                continue

            if service_candidate is None:
                service_match = cls._extract_hydra_service_target(connected_node)
                if service_match:
                    service_candidate = service_match["target"]
                    service_source_node_id = connected_node.id
                    service_source_label = service_match["label"]

            if host_candidate is None:
                host_match = cls._extract_network_target(connected_node, allow_domain=True)
                if host_match:
                    host_candidate = host_match["target"]
                    host_source_node_id = connected_node.id
                    host_source_label = host_match["label"]

        if host_candidate and service_candidate:
            source_node_id = service_source_node_id or host_source_node_id
            source_label = "Hydra Target + Service"
            if host_source_label or service_source_label:
                source_label = " + ".join(part for part in (host_source_label, service_source_label) if part)
            return {
                "compatible": True,
                "target": f"{service_candidate}://{host_candidate}",
                "source_node_id": source_node_id,
                "source_label": source_label,
                "reason": "Resolved from connected host and service nodes.",
            }

        if host_candidate:
            return {
                "compatible": True,
                "target": host_candidate,
                "source_node_id": host_source_node_id,
                "source_label": host_source_label,
                "reason": "Resolved host for Hydra, but service still must come from Options or a Port/Service node.",
            }

        return None

    @classmethod
    def extract_target_for_tool(cls, tool_name: str, node) -> dict | None:
        tool_name = cls.get_tool_command_name(tool_name)
        if tool_name in {"exiftool", "binwalk", "strings", "steghide", "ghidra", "john"}:
            return cls._extract_file_target(node)
        if tool_name == "tshark":
            return cls._extract_tshark_target(node)
        if tool_name == "searchsploit":
            return cls._extract_searchsploit_target(node)
        if tool_name == "hashcat":
            return cls._extract_hash_target(node)
        if tool_name == "patator":
            return cls._extract_patator_target(node)
        if tool_name in {"gobuster", "whatweb", "sqlmap"}:
            return cls._extract_url_target(node)
        if tool_name in {"nmap", "enum4linux", "rpcclient", "netcat", "hydra"}:
            return cls._extract_network_target(node, allow_domain=True)
        if tool_name == "masscan":
            return cls._extract_network_target(node, allow_domain=False)
        if tool_name in {"nslookup", "dnsutils"}:
            return cls._extract_dns_target(node, allow_ip=True)
        if tool_name in {"subfinder", "amass", "whois"}:
            return cls._extract_dns_target(node, allow_ip=False)
        if tool_name == "cupp":
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
            "search_query",
            "domain",
            "url",
            "path",
            "file_path",
            "ip_address",
            "host",
            "hostname",
            "service",
            "version",
            "cve",
            "password_hash",
            "hash_md5",
            "hash_sha256",
            "description",
            "content",
        )
        for field_name in generic_keys:
            value = str(data.get(field_name, "") or "").strip()
            if value:
                return {"target": value, "label": field_name.replace("_", " ").title()}
        return None

    @classmethod
    def _extract_searchsploit_target(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}

        cve_value = cls._clean_placeholder_value(data.get("cve", ""))
        if cve_value:
            return {"target": cve_value, "label": "CVE"}

        service_value = cls._clean_placeholder_value(data.get("service", ""))
        version_value = cls._clean_placeholder_value(data.get("version", ""))
        vulnerabilities_value = cls._clean_placeholder_value(data.get("vulnerabilities", ""))

        if service_value and version_value:
            return {"target": f"{service_value} {version_value}", "label": "Service + Version"}
        if service_value:
            return {"target": service_value, "label": "Service"}
        if vulnerabilities_value:
            return {"target": vulnerabilities_value, "label": "Vulnerabilities"}

        note_candidate = cls._extract_generic_target(node)
        if note_candidate:
            return note_candidate

        return None

    @classmethod
    def _extract_hash_target(cls, node) -> dict | None:
        file_candidate = cls._extract_file_target(node)
        if file_candidate:
            return file_candidate

        data = getattr(node, "data", {}) or {}
        hash_fields = (
            "password_hash",
            "hash",
            "hash_md5",
            "hash_sha1",
            "hash_sha256",
            "hash_sha512",
        )
        for field_name in hash_fields:
            value = cls._clean_placeholder_value(data.get(field_name, ""))
            if value:
                return {"target": value, "label": field_name.replace("_", " ").title()}

        return cls._extract_generic_target(node)

    @classmethod
    def _extract_patator_target(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}

        target_fields = ("target", "host", "hostname", "ip_address", "domain", "url", "address")
        for field_name in target_fields:
            value = cls._clean_placeholder_value(data.get(field_name, ""))
            if not value:
                continue
            if field_name == "url":
                host_value = cls._host_from_url(value)
                if host_value:
                    return {"target": host_value, "label": "URL Host"}
            return {"target": value, "label": field_name.replace("_", " ").title()}

        service_value = cls._clean_placeholder_value(data.get("service", ""))
        if service_value:
            return {"target": service_value, "label": "Service"}

        return cls._extract_generic_target(node)

    @classmethod
    def _extract_hydra_service_target(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}
        service_value = cls._clean_placeholder_value(data.get("service", ""))
        if service_value:
            return {"target": service_value.lower(), "label": "Service"}
        return None

    @classmethod
    def _extract_hydra_login_candidate(cls, node) -> dict | None:
        data = getattr(node, "data", {}) or {}
        login_fields = (
            ("username", "Username"),
            ("user", "User"),
            ("login", "Login"),
            ("email", "Email"),
        )
        for field_name, label in login_fields:
            value = cls._clean_placeholder_value(data.get(field_name, ""))
            if value:
                return {"login": value, "label": label}
        return None

    @classmethod
    def _tool_conditionally_requires_wordlist(cls, tool_name: str, options: str) -> bool:
        command_name = cls.get_tool_command_name(tool_name)
        option_parts = cls._split_cli(options)

        if command_name == "hydra":
            if cls._cli_has_value(option_parts, "-P") or cls._cli_has_value(option_parts, "-C"):
                return False
            if cls._cli_has_value(option_parts, "-p"):
                return False
            if cls._cli_has_value(option_parts, "-x") or cls._cli_has_value(option_parts, "-e"):
                return False
            return True

        return False

    @classmethod
    def _is_wordlist_kind_compatible(cls, tool_name: str, wordlist_kind: str) -> bool:
        allowed_kinds = cls.get_tool_spec(tool_name).get("wordlist_kinds", ())
        if not allowed_kinds:
            return True
        return str(wordlist_kind or "").strip().lower() in {kind.lower() for kind in allowed_kinds}

    @classmethod
    def _compose_tool_compatibility_reason(cls, tool_node, target_resolution: dict, wordlist_resolution: dict) -> str:
        tool_name = str(tool_node.data.get("tool_name", "") or "").strip().lower()
        options = str(tool_node.data.get("options", "") or "").strip()

        if not target_resolution["compatible"]:
            return target_resolution["reason"]
        if cls.tool_requires_wordlist(tool_name, options) and not wordlist_resolution["compatible"]:
            return wordlist_resolution["reason"]
        if target_resolution.get("target") and wordlist_resolution.get("source_node_id"):
            return (
                f"{target_resolution['reason']} "
                f"Wordlist resolved from {wordlist_resolution['wordlist_name'] or 'connected node'}."
            ).strip()
        return target_resolution["reason"] or wordlist_resolution["reason"]

    @staticmethod
    def _split_cli(value: str) -> list[str]:
        raw_value = str(value or "").strip()
        if not raw_value:
            return []
        return [token for token in re.split(r"\s+", raw_value) if token]

    @staticmethod
    def _cli_has_value(tokens: list[str], short_flag: str) -> bool:
        for index, token in enumerate(tokens):
            raw = str(token or "")
            if raw == short_flag and index + 1 < len(tokens):
                next_value = str(tokens[index + 1] or "").strip()
                if next_value and not next_value.startswith("-"):
                    return True
            if raw.startswith(short_flag) and raw != short_flag:
                return True
        return False

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
    def map_known_tool_error(cls, tool_name: str, output_text: str) -> str:
        tool_name = cls.get_tool_command_name(tool_name)
        normalized_output = (output_text or "").lower()

        if tool_name == "tshark":
            if "dumpcap in child process: permission denied" in normalized_output or "permission denied" in normalized_output:
                return (
                    "Sem permissões para captura ao vivo com TShark.\n"
                    "Use um ficheiro .pcap/.pcapng como target, ou conceda permissões ao dumpcap "
                    "(grupo wireshark/cap_net_raw,cap_net_admin)."
                )

        if tool_name == "whatweb":
            if "cannot load such file -- getoptlong" in normalized_output or "cannot load such file -- resolv-replace" in normalized_output:
                return (
                    "WhatWeb falhou porque a instalação local está incompleta para Ruby 3.4+ "
                    "(faltam gems extraídas da stdlib, como `getoptlong`/`resolv-replace`).\n"
                    "Reinstale o WhatWeb em Manage Tools para aplicar a correção automática, "
                    "ou execute em `~/opt/WhatWeb`: `bundle add getoptlong resolv-replace && bundle install`."
                )

        if tool_name == "enum4linux":
            error_kind = cls._detect_enum4linux_error_kind(normalized_output)
            if error_kind == "null_session_denied":
                return (
                    "Enum4linux falhou porque o alvo recusou null session SMB.\n"
                    "Confirme primeiro se 139/445 estão abertas e use credenciais válidas, "
                    "ou teste `smbclient -L //<host> -N` / `rpcclient -N -U \"\" <host>`."
                )
            if error_kind == "no_smb_reply":
                return (
                    "Enum4linux não conseguiu obter resposta SMB/NetBIOS útil do alvo.\n"
                    "Verifique se o host expõe SMB (139/445) e se não está filtrado antes de repetir a enumeração."
                )

        if tool_name == "rpcclient":
            if "nt_status_logon_failure" in normalized_output or "nt_status_access_denied" in normalized_output:
                return (
                    "RPCClient falhou por autenticação SMB rejeitada.\n"
                    "O alvo não aceitou as credenciais atuais; teste com credenciais válidas ou confirme se null session é permitida."
                )
            if "nt_status_connection_refused" in normalized_output or "connection refused" in normalized_output:
                return (
                    "RPCClient não conseguiu ligar ao serviço SMB/RPC do alvo.\n"
                    "Confirme se 139/445 estão abertas e se o serviço SMB está ativo."
                )
            if "nt_status_io_timeout" in normalized_output or "timed out" in normalized_output or "no route to host" in normalized_output:
                return (
                    "RPCClient excedeu o tempo de ligação ao alvo.\n"
                    "Verifique conectividade de rede e se SMB/RPC não está filtrado."
                )

        if tool_name == "hydra":
            error_kind = cls._detect_hydra_error_kind(normalized_output)
            if error_kind == "connection_refused":
                return (
                    "Hydra nao conseguiu ligar ao servico remoto porque a ligacao foi recusada.\n"
                    "Confirma se a porta do servico esta aberta no alvo e se o daemon correspondente esta ativo."
                )
            if error_kind == "no_route":
                return (
                    "Hydra nao conseguiu alcancar o alvo pela rede.\n"
                    "Verifica routing, VPN, firewall, segmentacao e se o host esta realmente acessivel a partir desta maquina."
                )
            if error_kind == "missing_login":
                return (
                    "Hydra precisa de uma fonte de login antes de iniciar o brute force.\n"
                    "Liga um node User/Credential ou define -l, -L ou -C nas Options."
                )
            if error_kind == "timeout":
                return (
                    "Hydra excedeu o tempo de ligacao ao alvo.\n"
                    "Confirma acessibilidade ao servico, latencia e firewall stateful. Em SSH, reduz paralelismo com `-t 4`."
                )
            if error_kind == "parallelism_limit":
                return (
                    "Hydra detetou um alvo SSH sensivel a excesso de paralelismo.\n"
                    "Reduz as tasks com `-t 4` ou menos para evitar resets, timeouts e limitacoes do servico."
                )

        if tool_name == "revshellgen":
            if "inappropriate ioctl for device" in normalized_output or "termios.error" in normalized_output:
                return (
                    "RevShellGen requer um terminal interativo (TTY real) e não funciona no runner embutido da app.\n"
                    "Execute `~/.local/bin/revshellgen` diretamente num terminal para usar o menu interativo."
                )

        return ""

    @classmethod
    def build_tool_error_result_payload(cls, tool_name: str, target: str, output_text: str) -> dict | None:
        tool_name = cls.get_tool_command_name(tool_name)
        normalized_output = (output_text or "").lower()
        excerpt = cls._build_output_excerpt(output_text, limit=10)
        mapped_error = cls.map_known_tool_error(tool_name, output_text)

        if tool_name == "enum4linux":
            error_kind = cls._detect_enum4linux_error_kind(normalized_output)
            if not error_kind:
                return None

            if error_kind == "null_session_denied":
                error = "Null session SMB recusada."
                fix = (
                    "Confirma 139/445 com Nmap; testa `smbclient -L //<host> -N`; "
                    "se falhar, repete com credenciais válidas ou tenta `rpcclient`."
                )
            else:
                error = "Sem resposta SMB/NetBIOS útil."
                fix = (
                    "Confirma se 139/445 estão abertas, verifica filtragem/firewall "
                    "e valida se o host realmente expõe SMB antes de repetir."
                )

            notes_parts = [mapped_error]
            if excerpt:
                notes_parts.append(f"Raw excerpt:\n{excerpt}")

            return cls._build_tool_error_payload(
                "enum4linux",
                {
                    "target": target or "",
                    "error": error,
                    "fix": fix,
                    "raw_excerpt": excerpt,
                    "notes": "\n\n".join(part for part in notes_parts if part),
                },
                summary_text="Created Enum4linux error node.",
            )

        if tool_name == "rpcclient":
            error_kind = cls._detect_rpcclient_error_kind(normalized_output)
            if not error_kind:
                return None

            if error_kind == "auth_rejected":
                error = "Autenticacao SMB rejeitada."
                fix = "Testa credenciais validas ou confirma se null session e permitida no alvo."
            elif error_kind == "connection_refused":
                error = "Ligacao SMB/RPC recusada."
                fix = "Confirma se 139/445 estao abertas e se o servico SMB esta ativo."
            else:
                error = "Ligacao SMB/RPC sem resposta."
                fix = "Verifica conectividade de rede e se SMB/RPC nao esta filtrado."

            notes_parts = [mapped_error]
            if excerpt:
                notes_parts.append(f"Raw excerpt:\n{excerpt}")

            return cls._build_tool_error_payload(
                "rpcclient",
                {
                    "target": target or "",
                    "error": error,
                    "fix": fix,
                    "raw_excerpt": excerpt,
                    "notes": "\n\n".join(part for part in notes_parts if part),
                },
                summary_text="Created RPCClient error node.",
            )

        if tool_name == "hydra":
            error_kind = cls._detect_hydra_error_kind(normalized_output)
            if not error_kind:
                return None
            if error_kind == "parallelism_limit" and cls._hydra_execution_completed(normalized_output):
                return None

            if error_kind == "connection_refused":
                error = "Ligacao ao servico recusada."
                fix = (
                    "Confirma se a porta do protocolo esta aberta no alvo, se o servico esta ativo "
                    "e se nao existe filtragem local/remota a bloquear a ligacao."
                )
            elif error_kind == "no_route":
                error = "Sem rota ate ao alvo."
                fix = (
                    "Verifica conectividade IP, routing, VPN, VLAN/firewall e confirma se o host "
                    "esta acessivel antes de repetir o brute force."
                )
            elif error_kind == "timeout":
                error = "Ligacao ao servico expirou."
                fix = (
                    "Valida que o servico responde na porta esperada, verifica filtragem/firewall "
                    "e baixa o paralelismo com `-t 4` se estiveres a usar SSH."
                )
            elif error_kind == "parallelism_limit":
                error = "Paralelismo excessivo para o servico remoto."
                fix = (
                    "Reduz o numero de tasks com `-t 4` ou menos e repete, sobretudo em SSH onde "
                    "muitos servidores limitam tentativas concorrentes."
                )
            else:
                error = "Hydra sem fonte de login."
                fix = "Liga um node User/Credential ou define -l, -L ou -C nas Options do tool node."

            notes_parts = [mapped_error]
            if excerpt:
                notes_parts.append(f"Raw excerpt:\n{excerpt}")

            return cls._build_tool_error_payload(
                "hydra",
                {
                    "target": target or "",
                    "error": error,
                    "fix": fix,
                    "raw_excerpt": excerpt,
                    "notes": "\n\n".join(part for part in notes_parts if part),
                },
                summary_text="Created Hydra error node.",
            )

        return None

    @classmethod
    def is_special_tool_result_node(cls, node_or_type) -> bool:
        node_type = getattr(node_or_type, "type", node_or_type)
        node_type = str(node_type or "").strip()
        return bool(cls.get_special_tool_result_template_by_node_type(node_type))

    @classmethod
    def get_special_node_hidden_fields(cls, node_type: str) -> set[str]:
        template = cls.get_special_tool_result_template_by_node_type(node_type)
        if not template:
            return set()
        return set(template.get("hidden_fields", cls.BASE_TOOL_WARNING_TEMPLATE["hidden_fields"]))

    @classmethod
    def get_special_node_field_label(cls, node_type: str, field_name: str) -> str:
        template = cls.get_special_tool_result_template_by_node_type(node_type)
        label_map = {}
        if template:
            label_map = template.get("field_labels", cls.BASE_TOOL_WARNING_TEMPLATE["field_labels"])
        return label_map.get(field_name, field_name.replace("_", " ").title())

    @classmethod
    def get_special_node_preview_lines(cls, node_or_type, node_data: dict) -> list[str]:
        node_type = getattr(node_or_type, "type", node_or_type)
        template = cls.get_special_tool_result_template_by_node_type(node_type)
        if not template:
            return []

        preview_fields = template.get("preview_fields", cls.BASE_TOOL_WARNING_TEMPLATE["preview_fields"])
        preview_prefixes = template.get("preview_prefixes", cls.BASE_TOOL_WARNING_TEMPLATE["preview_prefixes"])
        lines = []
        for field_name in preview_fields:
            value = str((node_data or {}).get(field_name, "") or "").strip()
            if not value:
                continue
            if field_name == "raw_excerpt":
                value = value.splitlines()[0].strip()
                if not value:
                    continue
            prefix = preview_prefixes.get(field_name, field_name.replace("_", " ").title())
            lines.append(f"{prefix}: {value}")
        return lines

    @classmethod
    def iter_tool_error_templates(cls) -> list[dict]:
        return [cls.get_tool_error_template(tool_name) for tool_name in cls.TOOL_ERROR_NODE_TEMPLATES]

    @classmethod
    def iter_tool_result_templates(cls) -> list[dict]:
        templates = [cls.get_tool_result_template(tool_name) for tool_name in cls.TOOL_RESULT_NODE_TEMPLATES]
        templates.extend(cls._build_tool_result_template_from_payload(payload) for payload in cls.RESULT_NODE_TYPE_TEMPLATES.values())
        return templates

    @classmethod
    def iter_tool_warning_templates(cls) -> list[dict]:
        return [cls.get_tool_warning_template(tool_name) for tool_name in cls.TOOL_WARNING_NODE_TEMPLATES]

    @classmethod
    def get_tool_error_template(cls, tool_name: str) -> dict:
        payload = cls.TOOL_ERROR_NODE_TEMPLATES.get(cls.get_tool_command_name(tool_name), {})
        if not payload:
            return {}
        template = {
            "default_data": dict(cls.BASE_TOOL_ERROR_TEMPLATE["default_data"]),
            "removed_fields": list(cls.BASE_TOOL_ERROR_TEMPLATE["removed_fields"]),
            "hidden_fields": list(cls.BASE_TOOL_ERROR_TEMPLATE["hidden_fields"]),
            "field_labels": dict(cls.BASE_TOOL_ERROR_TEMPLATE["field_labels"]),
            "preview_fields": tuple(cls.BASE_TOOL_ERROR_TEMPLATE["preview_fields"]),
            "preview_prefixes": dict(cls.BASE_TOOL_ERROR_TEMPLATE["preview_prefixes"]),
        }
        for key, value in cls.BASE_TOOL_ERROR_TEMPLATE.items():
            if key not in template:
                template[key] = value
        for key, value in payload.items():
            if key == "default_data":
                template["default_data"].update(value)
            elif key == "removed_fields":
                template["removed_fields"] = list(value)
            elif key == "hidden_fields":
                template["hidden_fields"] = list(value)
            elif key == "field_labels":
                template["field_labels"].update(value)
            elif key == "preview_fields":
                template["preview_fields"] = tuple(value)
            elif key == "preview_prefixes":
                template["preview_prefixes"].update(value)
            else:
                template[key] = value
        return template

    @classmethod
    def get_tool_result_template(cls, tool_name: str) -> dict:
        payload = cls.TOOL_RESULT_NODE_TEMPLATES.get(cls.get_tool_command_name(tool_name), {})
        if not payload:
            return {}
        return cls._build_tool_result_template_from_payload(payload)

    @classmethod
    def get_tool_warning_template(cls, tool_name: str) -> dict:
        payload = cls.TOOL_WARNING_NODE_TEMPLATES.get(cls.get_tool_command_name(tool_name), {})
        if not payload:
            return {}
        template = {
            "default_data": dict(cls.BASE_TOOL_WARNING_TEMPLATE["default_data"]),
            "removed_fields": list(cls.BASE_TOOL_WARNING_TEMPLATE["removed_fields"]),
            "hidden_fields": list(cls.BASE_TOOL_WARNING_TEMPLATE["hidden_fields"]),
            "field_labels": dict(cls.BASE_TOOL_WARNING_TEMPLATE["field_labels"]),
            "preview_fields": tuple(cls.BASE_TOOL_WARNING_TEMPLATE["preview_fields"]),
            "preview_prefixes": dict(cls.BASE_TOOL_WARNING_TEMPLATE["preview_prefixes"]),
        }
        for key, value in cls.BASE_TOOL_WARNING_TEMPLATE.items():
            if key not in template:
                template[key] = value
        for key, value in payload.items():
            if key == "default_data":
                template["default_data"].update(value)
            elif key == "removed_fields":
                template["removed_fields"] = list(value)
            elif key == "hidden_fields":
                template["hidden_fields"] = list(value)
            elif key == "field_labels":
                template["field_labels"].update(value)
            elif key == "preview_fields":
                template["preview_fields"] = tuple(value)
            elif key == "preview_prefixes":
                template["preview_prefixes"].update(value)
            else:
                template[key] = value
        return template

    @classmethod
    def get_tool_error_template_by_node_type(cls, node_type: str) -> dict:
        normalized_node_type = str(node_type or "").strip()
        for tool_name in cls.TOOL_ERROR_NODE_TEMPLATES:
            template = cls.get_tool_error_template(tool_name)
            if template.get("node_type") == normalized_node_type:
                return template
        return {}

    @classmethod
    def get_tool_result_template_by_node_type(cls, node_type: str) -> dict:
        normalized_node_type = str(node_type or "").strip()
        for tool_name in cls.TOOL_RESULT_NODE_TEMPLATES:
            template = cls.get_tool_result_template(tool_name)
            if template.get("node_type") == normalized_node_type:
                return template
        if normalized_node_type in cls.RESULT_NODE_TYPE_TEMPLATES:
            return cls._build_tool_result_template_from_payload(cls.RESULT_NODE_TYPE_TEMPLATES[normalized_node_type])
        return {}

    @classmethod
    def get_tool_warning_template_by_node_type(cls, node_type: str) -> dict:
        normalized_node_type = str(node_type or "").strip()
        for tool_name in cls.TOOL_WARNING_NODE_TEMPLATES:
            template = cls.get_tool_warning_template(tool_name)
            if template.get("node_type") == normalized_node_type:
                return template
        return {}

    @classmethod
    def get_special_tool_result_template_by_node_type(cls, node_type: str) -> dict:
        return (
            cls.get_tool_error_template_by_node_type(node_type)
            or cls.get_tool_warning_template_by_node_type(node_type)
            or cls.get_tool_result_template_by_node_type(node_type)
        )

    @classmethod
    def _build_tool_result_template_from_payload(cls, payload: dict) -> dict:
        template = {
            "default_data": dict(cls.BASE_TOOL_RESULT_TEMPLATE["default_data"]),
            "removed_fields": list(cls.BASE_TOOL_RESULT_TEMPLATE["removed_fields"]),
            "hidden_fields": list(cls.BASE_TOOL_RESULT_TEMPLATE["hidden_fields"]),
            "field_labels": dict(cls.BASE_TOOL_RESULT_TEMPLATE["field_labels"]),
            "preview_fields": tuple(cls.BASE_TOOL_RESULT_TEMPLATE["preview_fields"]),
            "preview_prefixes": dict(cls.BASE_TOOL_RESULT_TEMPLATE["preview_prefixes"]),
        }
        for key, value in cls.BASE_TOOL_RESULT_TEMPLATE.items():
            if key not in template:
                template[key] = value
        for key, value in (payload or {}).items():
            if key == "default_data":
                template["default_data"].update(value)
            elif key == "removed_fields":
                template["removed_fields"] = list(value)
            elif key == "hidden_fields":
                template["hidden_fields"] = list(value)
            elif key == "field_labels":
                template["field_labels"].update(value)
            elif key == "preview_fields":
                template["preview_fields"] = tuple(value)
            elif key == "preview_prefixes":
                template["preview_prefixes"].update(value)
            else:
                template[key] = value
        return template

    @classmethod
    def _build_tool_error_payload(cls, tool_name: str, data: dict, *, summary_text: str) -> dict:
        template = cls.get_tool_error_template(tool_name)
        return {
            "node_type": template["node_type"],
            "template": template,
            "data": data,
            "summary_text": summary_text,
        }

    @classmethod
    def build_tool_result_payload(cls, tool_name: str, target: str, output_text: str, exit_code: int) -> dict | None:
        tool_name = cls.get_tool_command_name(tool_name)
        if tool_name != "hydra":
            return None

        if cls._hydra_is_warning_case(output_text):
            return None

        template = cls.get_tool_result_template(tool_name)
        if not template:
            return None

        excerpt = cls._build_output_excerpt(output_text, limit=12)
        credentials = cls._extract_hydra_credentials(output_text)
        return {
            "node_type": template["node_type"],
            "template": template,
            "data": {
                "target": target or "",
                "service": cls._extract_service_from_target(target),
                "outcome": cls._summarize_hydra_result(output_text, exit_code, credentials),
                "credentials": credentials,
                "attempt_summary": cls._extract_hydra_attempt_summary(output_text),
                "recommendation": cls._recommend_hydra_next_step(output_text, credentials),
                "raw_excerpt": excerpt,
                "notes": "",
            },
            "summary_text": "Created Hydra result node.",
        }

    @classmethod
    def build_tool_result_payloads(cls, tool_name: str, target: str, output_text: str, exit_code: int) -> list[dict]:
        tool_name = cls.get_tool_command_name(tool_name)
        payload = cls.build_tool_result_payload(tool_name, target, output_text, exit_code)
        return [payload] if payload else []

    @classmethod
    def build_tool_warning_payload(cls, tool_name: str, target: str, output_text: str, exit_code: int) -> dict | None:
        tool_name = cls.get_tool_command_name(tool_name)
        if tool_name != "hydra" or not cls._hydra_is_warning_case(output_text):
            return None

        template = cls.get_tool_warning_template(tool_name)
        if not template:
            return None

        excerpt = cls._build_output_excerpt(output_text, limit=12)
        return {
            "node_type": template["node_type"],
            "template": template,
            "data": {
                "target": target or "",
                "warning": cls._summarize_hydra_warning(output_text, exit_code),
                "context": cls._extract_hydra_attempt_summary(output_text),
                "recommendation": cls._recommend_hydra_next_step(output_text, ""),
                "raw_excerpt": excerpt,
                "notes": "",
            },
            "summary_text": "Created Hydra warning node.",
        }

    @classmethod
    def normalize_tool_exit_code(cls, tool_name: str, output_text: str, exit_code: int) -> int:
        tool_name = cls.get_tool_command_name(tool_name)
        if tool_name == "hydra" and exit_code != 0:
            normalized_output = (output_text or "").lower()
            if cls._hydra_execution_completed(normalized_output):
                return 0
        return exit_code

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
    def _detect_enum4linux_error_kind(cls, normalized_output: str) -> str:
        if "server doesn't allow session using username '', password ''" in normalized_output:
            return "null_session_denied"
        if "[e] can't find workgroup/domain" in normalized_output or "no reply from" in normalized_output:
            return "no_smb_reply"
        return ""

    @classmethod
    def _detect_rpcclient_error_kind(cls, normalized_output: str) -> str:
        if "nt_status_logon_failure" in normalized_output or "nt_status_access_denied" in normalized_output:
            return "auth_rejected"
        if "nt_status_connection_refused" in normalized_output or "connection refused" in normalized_output:
            return "connection_refused"
        if "nt_status_io_timeout" in normalized_output or "timed out" in normalized_output or "no route to host" in normalized_output:
            return "timeout"
        return ""

    @classmethod
    def _detect_hydra_error_kind(cls, normalized_output: str) -> str:
        if "could not connect" in normalized_output and "connection refused" in normalized_output:
            return "connection_refused"
        if "could not connect" in normalized_output and "no route to host" in normalized_output:
            return "no_route"
        if "timed out" in normalized_output or "timeout" in normalized_output:
            return "timeout"
        if "recommended to reduce the tasks" in normalized_output or "limit the number of parallel tasks" in normalized_output:
            return "parallelism_limit"
        if "i need at least either the -l, -l or -c option to know the login" in normalized_output:
            return "missing_login"
        if "i need at least either the -l, -l or -c option" in normalized_output:
            return "missing_login"
        if "i need at least either the -l, -l/-l or -c option" in normalized_output:
            return "missing_login"
        if "i need at least either the -l" in normalized_output and "to know the login" in normalized_output:
            return "missing_login"
        return ""

    @classmethod
    def _extract_service_from_target(cls, target: str) -> str:
        parsed = urlparse(str(target or "").strip())
        if parsed.scheme:
            return parsed.scheme.lower()
        return ""

    @classmethod
    def _extract_hydra_credentials(cls, output_text: str) -> str:
        for line in (output_text or "").splitlines():
            match = re.search(
                r"host:\s*(?P<host>\S+)\s+login:\s*(?P<login>\S+)\s+password:\s*(?P<password>.+)$",
                line.strip(),
                re.IGNORECASE,
            )
            if match:
                login = match.group("login").strip()
                password = match.group("password").strip()
                return f"{login}:{password}"
        return ""

    @classmethod
    def _extract_hydra_attempt_summary(cls, output_text: str) -> str:
        for line in (output_text or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("[DATA] max ") or "login tries" in stripped.lower():
                return stripped.removeprefix("[DATA]").strip()
            if stripped.startswith("[STATUS]"):
                return stripped.removeprefix("[STATUS]").strip()
        return ""

    @classmethod
    def _summarize_hydra_result(cls, output_text: str, exit_code: int, credentials: str) -> str:
        normalized_output = (output_text or "").lower()
        if credentials:
            return "Credenciais validas encontradas."
        if "0 valid password found" in normalized_output:
            return "Execucao concluida sem credenciais validas."
        if "attack finished" in normalized_output:
            return "Execucao concluida."
        if "recommended to reduce the tasks" in normalized_output:
            return "Execucao concluida com aviso de paralelismo."
        if exit_code == 0:
            return "Execucao concluida sem parser estruturado."
        return "Execucao terminou com erro."

    @classmethod
    def _recommend_hydra_next_step(cls, output_text: str, credentials: str) -> str:
        normalized_output = (output_text or "").lower()
        if credentials:
            return "Valida as credenciais fora do brute force e cria um Credential node se o acesso for real."
        if "recommended to reduce the tasks" in normalized_output or "limit the number of parallel tasks" in normalized_output:
            return "Repete com `-t 4` ou menos para evitar resets e timeouts em SSH."
        if "0 valid password found" in normalized_output:
            return "Troca de wordlist, ajusta usernames ou confirma primeiro se o servico aceita autenticacao por password."
        return "Reve a wordlist, username e options antes da proxima execucao."

    @classmethod
    def _hydra_is_warning_case(cls, output_text: str) -> bool:
        normalized_output = (output_text or "").lower()
        return cls._hydra_execution_completed(normalized_output) and not cls._extract_hydra_credentials(output_text)

    @classmethod
    def _summarize_hydra_warning(cls, output_text: str, exit_code: int) -> str:
        normalized_output = (output_text or "").lower()
        if "0 valid password found" in normalized_output:
            if "recommended to reduce the tasks" in normalized_output:
                return "Execucao concluida sem credenciais validas e com aviso de paralelismo."
            return "Execucao concluida sem credenciais validas."
        if exit_code == 0:
            return "Execucao concluida sem findings relevantes."
        return "Execucao concluida com aviso."

    @classmethod
    def _hydra_execution_completed(cls, normalized_output: str) -> bool:
        return any(
            marker in normalized_output
            for marker in (
                "target completed, 0 valid password found",
                "0 valid password found",
                "hydra (https://github.com/vanhauser-thc/thc-hydra) finished at",
                "[status] attack finished",
            )
        )


    @classmethod
    def _build_output_excerpt(cls, output_text: str, limit: int = 8) -> str:
        lines = []
        for line in (output_text or "").splitlines():
            clean_line = str(line or "").strip()
            if not clean_line:
                continue
            if clean_line.startswith("Executing:"):
                continue
            if set(clean_line) == {"-"}:
                continue
            lines.append(clean_line)
            if len(lines) >= limit:
                break
        return "\n".join(lines)

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

    @staticmethod
    def _clean_placeholder_value(value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        placeholders = {
            "cve-xxxx-xxxx",
            "investigation note...",
            "example.com",
            "server-01",
        }
        if text.lower() in placeholders:
            return ""
        return text
