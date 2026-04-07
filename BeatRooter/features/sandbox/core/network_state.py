from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NetworkLabProfile:
    lab_name: str = ""
    mgmt_subnet: str = ""
    edge_type: str = "Perimeter firewall"


@dataclass
class NetworkDevice:
    name: str
    device_type: str = ""
    mgmt_ip: str = ""
    role: str = ""


@dataclass
class NetworkSegment:
    vlan: str = ""
    name: str = ""
    cidr: str = ""
    gateway: str = ""


@dataclass
class NetworkInterface:
    device: str
    interface: str = ""
    ip_cidr: str = ""
    vlan: str = ""
    status: str = "up"


@dataclass
class ACLRule:
    source: str = "any"
    target: str = "any"
    proto: str = "any"
    port: str = "any"
    action: str = "allow"


@dataclass
class PublishedService:
    device: str
    service: str = ""
    proto: str = "TCP"
    port: str = ""
    visibility: str = "published"


@dataclass
class NetworkTraceDefaults:
    source: str = "Internet"
    target: str = ""
    protocol: str = "TCP"
    port: str = ""


@dataclass
class NetworkState:
    profile: NetworkLabProfile = field(default_factory=NetworkLabProfile)
    devices: list[NetworkDevice] = field(default_factory=list)
    segments: list[NetworkSegment] = field(default_factory=list)
    rules: list[ACLRule] = field(default_factory=list)
    interfaces: list[NetworkInterface] = field(default_factory=list)
    exposures: list[PublishedService] = field(default_factory=list)
    topology_notes: str = ""
    operations_notes: str = ""
    trace_output: str = ""
    trace_defaults: NetworkTraceDefaults = field(default_factory=NetworkTraceDefaults)

    @classmethod
    def from_workspace_dict(cls, state: dict | None) -> "NetworkState":
        state = state or {}
        profile = state.get("lab_profile", {}) or {}
        trace_defaults = state.get("trace_defaults", {}) or {}
        return cls(
            profile=NetworkLabProfile(
                lab_name=str(profile.get("lab_name", "")).strip(),
                mgmt_subnet=str(profile.get("mgmt_subnet", "")).strip(),
                edge_type=str(profile.get("edge_type", "Perimeter firewall")).strip() or "Perimeter firewall",
            ),
            devices=[
                NetworkDevice(
                    name=str(row.get("Device", "")).strip(),
                    device_type=str(row.get("Type", "")).strip(),
                    mgmt_ip=str(row.get("Mgmt IP", "")).strip(),
                    role=str(row.get("Role", "")).strip(),
                )
                for row in state.get("devices", [])
                if str(row.get("Device", "")).strip()
            ],
            segments=[
                NetworkSegment(
                    vlan=str(row.get("VLAN", "")).strip(),
                    name=str(row.get("Name", "")).strip(),
                    cidr=str(row.get("CIDR", "")).strip(),
                    gateway=str(row.get("Gateway", "")).strip(),
                )
                for row in state.get("segments", [])
                if any(str(row.get(field, "")).strip() for field in ("VLAN", "Name", "CIDR", "Gateway"))
            ],
            rules=[
                ACLRule(
                    source=str(row.get("Source", "any")).strip() or "any",
                    target=str(row.get("Target", "any")).strip() or "any",
                    proto=str(row.get("Proto", "any")).strip() or "any",
                    port=str(row.get("Port", "any")).strip() or "any",
                    action=str(row.get("Action", "allow")).strip() or "allow",
                )
                for row in state.get("rules", [])
                if any(str(row.get(field, "")).strip() for field in ("Source", "Target", "Proto", "Port", "Action"))
            ],
            interfaces=[
                NetworkInterface(
                    device=str(row.get("Device", "")).strip(),
                    interface=str(row.get("Interface", "")).strip(),
                    ip_cidr=str(row.get("IP/CIDR", "")).strip(),
                    vlan=str(row.get("VLAN", "")).strip(),
                    status=str(row.get("Status", "up")).strip() or "up",
                )
                for row in state.get("interfaces", [])
                if str(row.get("Device", "")).strip()
            ],
            exposures=[
                PublishedService(
                    device=str(row.get("Device", "")).strip(),
                    service=str(row.get("Service", "")).strip(),
                    proto=str(row.get("Proto", "TCP")).strip() or "TCP",
                    port=str(row.get("Port", "")).strip(),
                    visibility=str(row.get("Visibility", "published")).strip() or "published",
                )
                for row in state.get("exposures", [])
                if str(row.get("Device", "")).strip()
            ],
            topology_notes=str(state.get("topology_notes", "")),
            operations_notes=str(state.get("operations_notes", "")),
            trace_output=str(state.get("trace_output", "")),
            trace_defaults=NetworkTraceDefaults(
                source=str(trace_defaults.get("source", "Internet")).strip() or "Internet",
                target=str(trace_defaults.get("target", "")).strip(),
                protocol=str(trace_defaults.get("protocol", "TCP")).strip() or "TCP",
                port=str(trace_defaults.get("port", "")).strip(),
            ),
        )

    def to_workspace_dict(self) -> dict:
        return {
            "lab_profile": {
                "lab_name": self.profile.lab_name,
                "mgmt_subnet": self.profile.mgmt_subnet,
                "edge_type": self.profile.edge_type,
            },
            "devices": [
                {
                    "Device": device.name,
                    "Type": device.device_type,
                    "Mgmt IP": device.mgmt_ip,
                    "Role": device.role,
                }
                for device in self.devices
            ],
            "segments": [
                {
                    "VLAN": segment.vlan,
                    "Name": segment.name,
                    "CIDR": segment.cidr,
                    "Gateway": segment.gateway,
                }
                for segment in self.segments
            ],
            "rules": [
                {
                    "Source": rule.source,
                    "Target": rule.target,
                    "Proto": rule.proto,
                    "Port": rule.port,
                    "Action": rule.action,
                }
                for rule in self.rules
            ],
            "interfaces": [
                {
                    "Device": interface.device,
                    "Interface": interface.interface,
                    "IP/CIDR": interface.ip_cidr,
                    "VLAN": interface.vlan,
                    "Status": interface.status,
                }
                for interface in self.interfaces
            ],
            "exposures": [
                {
                    "Device": exposure.device,
                    "Service": exposure.service,
                    "Proto": exposure.proto,
                    "Port": exposure.port,
                    "Visibility": exposure.visibility,
                }
                for exposure in self.exposures
            ],
            "topology_notes": self.topology_notes,
            "operations_notes": self.operations_notes,
            "trace_output": self.trace_output,
            "trace_defaults": {
                "source": self.trace_defaults.source,
                "target": self.trace_defaults.target,
                "protocol": self.trace_defaults.protocol,
                "port": self.trace_defaults.port,
            },
        }
