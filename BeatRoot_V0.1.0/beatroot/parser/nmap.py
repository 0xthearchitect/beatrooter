from __future__ import annotations

import re
from typing import Any


PORT_RE = re.compile(
    r"(?P<port>\d+)/(?P<state>[^/]+)/(?P<proto>[^/]+)/(?P<owner>[^/]*)/(?P<service>[^/]*)/(?P<rpc>[^/]*)/(?P<version>.*)"
)


def parse_nmap_grepable_output(text: str) -> dict[str, Any]:
    hosts: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.startswith("Host:") or "Ports:" not in line:
            continue
        host_section, ports_section = line.split("Ports:", 1)
        address = host_section.replace("Host:", "", 1).strip().split()[0]
        ports: list[dict[str, Any]] = []
        for raw_port in ports_section.split(","):
            candidate = raw_port.strip()
            if not candidate:
                continue
            match = PORT_RE.match(candidate)
            if not match:
                continue
            service = match.group("service") or "unknown"
            version = match.group("version").strip()
            ports.append(
                {
                    "port": int(match.group("port")),
                    "state": match.group("state"),
                    "protocol": match.group("proto"),
                    "service": service,
                    "version": version or None,
                }
            )
        hosts.append({"address": address, "ports": ports})
    return {"hosts": hosts}

