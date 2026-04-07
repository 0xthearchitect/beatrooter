from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

from features.sandbox.core.network_state import (
    ACLRule,
    NetworkDevice,
    NetworkInterface,
    NetworkSegment,
    NetworkState,
    PublishedService,
)


@dataclass
class TraceRequest:
    source: str
    target: str
    proto: str
    port: str


@dataclass
class TraceStep:
    phase: str
    outcome: str
    detail: str


@dataclass
class TraceHop:
    source: str
    target: str
    via: str
    note: str = ""


@dataclass
class TraceResult:
    request: TraceRequest
    verdict: str
    reason: str
    steps: list[TraceStep] = field(default_factory=list)
    hops: list[str] = field(default_factory=list)
    hop_details: list[TraceHop] = field(default_factory=list)
    matched_rule: ACLRule | None = None
    matched_service: PublishedService | None = None


@dataclass
class _EndpointContext:
    label: str
    kind: str
    device: NetworkDevice | None = None
    interfaces: list[NetworkInterface] = field(default_factory=list)
    route_segments: set[str] = field(default_factory=set)
    segment_tokens: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)


def _normalize_token(value: str) -> str:
    return str(value or "").strip().lower()


class NetworkTraceEngine:
    def __init__(
        self,
        devices: Iterable[NetworkDevice] | None = None,
        segments: Iterable[NetworkSegment] | None = None,
        interfaces: Iterable[NetworkInterface] | None = None,
        rules: Iterable[ACLRule] | None = None,
        exposures: Iterable[PublishedService] | None = None,
        state: NetworkState | None = None,
    ):
        self.state = state or NetworkState(
            devices=list(devices or []),
            segments=list(segments or []),
            interfaces=list(interfaces or []),
            rules=list(rules or []),
            exposures=list(exposures or []),
        )
        self.devices = list(self.state.devices)
        self.segments = list(self.state.segments)
        self.interfaces = list(self.state.interfaces)
        self.rules = list(self.state.rules)
        self.exposures = list(self.state.exposures)

        self._devices_by_name = {_normalize_token(device.name): device for device in self.devices if device.name}
        self._segments_by_vlan = {}
        self._segments_by_name = {}
        for segment in self.segments:
            if segment.vlan:
                self._segments_by_vlan[_normalize_token(segment.vlan)] = segment
            if segment.name:
                self._segments_by_name[_normalize_token(segment.name)] = segment

    @classmethod
    def from_workspace_state(cls, state: dict) -> "NetworkTraceEngine":
        return cls.from_network_state(NetworkState.from_workspace_dict(state))

    @classmethod
    def from_network_state(cls, state: NetworkState) -> "NetworkTraceEngine":
        return cls(state=state)

    def trace(self, request: TraceRequest) -> TraceResult:
        request = TraceRequest(
            source=request.source.strip(),
            target=request.target.strip(),
            proto=request.proto.strip().upper(),
            port=request.port.strip(),
        )
        steps: list[TraceStep] = []

        source_ctx = self._resolve_endpoint(request.source)
        if not source_ctx:
            steps.append(TraceStep("source", "error", f"Unknown source endpoint '{request.source}'."))
            return TraceResult(request, "BLOCKED", "Unknown source endpoint.", steps=steps)
        steps.append(
            TraceStep(
                "source",
                "ok",
                f"Resolved source '{source_ctx.label}' as {source_ctx.kind} with tags: {', '.join(sorted(source_ctx.tags)) or '-'}",
            )
        )
        if source_ctx.kind == "device":
            active_source_interfaces = [
                iface for iface in source_ctx.interfaces if self._is_active_interface(iface)
            ]
            if not active_source_interfaces:
                steps.append(TraceStep("source-interface", "error", "Source has no active interfaces."))
                return TraceResult(request, "UNREACHABLE", "Source has no active interfaces.", steps=steps)
            steps.append(
                TraceStep(
                    "source-interface",
                    "ok",
                    f"Found {len(active_source_interfaces)} active source interface(s): {', '.join(iface.interface or iface.vlan for iface in active_source_interfaces)}",
                )
            )

        target_ctx = self._resolve_endpoint(request.target)
        if not target_ctx or target_ctx.kind != "device":
            steps.append(TraceStep("target", "error", f"Unknown target device '{request.target}'."))
            return TraceResult(request, "BLOCKED", "Unknown target device.", steps=steps)
        steps.append(
            TraceStep(
                "target",
                "ok",
                f"Resolved target '{target_ctx.label}' with segments: {', '.join(sorted(target_ctx.segment_tokens)) or '-'}",
            )
        )

        active_interfaces = [iface for iface in target_ctx.interfaces if self._is_active_interface(iface)]
        if not active_interfaces:
            steps.append(TraceStep("interface", "error", "Target has no active interfaces."))
            return TraceResult(request, "UNREACHABLE", "Target has no active interfaces.", steps=steps)
        steps.append(
            TraceStep(
                "interface",
                "ok",
                f"Found {len(active_interfaces)} active target interface(s): {', '.join(iface.interface or iface.vlan for iface in active_interfaces)}",
            )
        )

        hop_path, hop_details = self._find_hops(source_ctx, target_ctx)
        if not hop_path:
            steps.append(
                TraceStep(
                    "path",
                    "error",
                    f"No routed path could be inferred from {source_ctx.label} to {target_ctx.label}.",
                )
            )
            return TraceResult(
                request,
                "UNREACHABLE",
                "No routed path found to target.",
                steps=steps,
            )
        steps.append(
            TraceStep(
                "path",
                "ok",
                f"Inferred hop path: {' -> '.join(hop_path)}",
            )
        )

        matched_service = self._find_matching_service(target_ctx.label, request.proto, request.port)
        if not matched_service:
            steps.append(
                TraceStep(
                    "service",
                    "error",
                    f"No published service on {target_ctx.label} matches {request.proto}/{request.port}.",
                )
            )
            return TraceResult(
                request,
                "BLOCKED",
                "No published service matches this destination port.",
                steps=steps,
                hops=hop_path,
                hop_details=hop_details,
            )
        steps.append(
            TraceStep(
                "service",
                "ok",
                f"Matched service '{matched_service.service or 'service'}' on {matched_service.proto}/{matched_service.port} with visibility '{matched_service.visibility}'.",
            )
        )

        matched_rule = self._find_matching_rule(source_ctx, target_ctx, request.proto, request.port)
        if matched_rule:
            action = _normalize_token(matched_rule.action)
            steps.append(
                TraceStep(
                    "acl",
                    "ok" if action in {"allow", "permit"} else "error",
                    f"Matched ACL rule {matched_rule.source} -> {matched_rule.target} {matched_rule.proto}/{matched_rule.port} => {matched_rule.action}.",
                )
            )
            if action in {"deny", "block"}:
                return TraceResult(
                    request,
                    "BLOCKED",
                    "ACL policy explicitly denies the flow.",
                    steps=steps,
                    hops=hop_path,
                    hop_details=hop_details,
                    matched_rule=matched_rule,
                    matched_service=matched_service,
                )
        else:
            steps.append(
                TraceStep(
                    "acl",
                    "ok",
                    "No ACL rule matched. The engine falls back to service visibility and active interfaces.",
                )
            )

        visibility_allowed, visibility_reason = self._evaluate_visibility(source_ctx, target_ctx, matched_service)
        steps.append(
            TraceStep(
                "visibility",
                "ok" if visibility_allowed else "error",
                visibility_reason,
            )
        )
        if not visibility_allowed:
            return TraceResult(
                request,
                "FILTERED",
                visibility_reason,
                steps=steps,
                hops=hop_path,
                hop_details=hop_details,
                matched_rule=matched_rule,
                matched_service=matched_service,
            )

        steps.append(
            TraceStep(
                "result",
                "ok",
                f"Traffic from {request.source} to {request.target} on {request.proto}/{request.port} is allowed.",
            )
        )
        return TraceResult(
            request,
            "ALLOWED",
            "Exposure exists and policy permits the flow.",
            steps=steps,
            hops=hop_path,
            hop_details=hop_details,
            matched_rule=matched_rule,
            matched_service=matched_service,
        )

    def _resolve_endpoint(self, endpoint_name: str) -> _EndpointContext | None:
        normalized = _normalize_token(endpoint_name)
        if not normalized:
            return None
        if normalized in {"internet", "external", "wan"}:
            return _EndpointContext(
                label="Internet",
                kind="internet",
                tags={"internet", "external"},
            )

        device = self._devices_by_name.get(normalized)
        if not device:
            return None

        device_interfaces = [iface for iface in self.interfaces if _normalize_token(iface.device) == normalized]
        route_segments = self._build_route_segments(device_interfaces)
        segment_tokens = self._build_segment_tokens(device_interfaces)
        tags = {
            "internal",
            _normalize_token(device.name),
            _normalize_token(device.device_type),
            _normalize_token(device.role),
        }
        tags.update(segment_tokens)
        tags.update(route_segments)
        return _EndpointContext(
            label=device.name,
            kind="device",
            device=device,
            interfaces=device_interfaces,
            route_segments=route_segments,
            segment_tokens=segment_tokens,
            tags={tag for tag in tags if tag},
        )

    def _build_route_segments(self, interfaces: Iterable[NetworkInterface]) -> set[str]:
        route_segments: set[str] = set()
        for interface in interfaces:
            vlan_token = _normalize_token(interface.vlan)
            if not vlan_token:
                continue
            segment = self._segments_by_vlan.get(vlan_token) or self._segments_by_name.get(vlan_token)
            if segment and segment.name:
                route_segments.add(f"segment:{_normalize_token(segment.name)}")
            elif vlan_token:
                route_segments.add(f"vlan:{vlan_token}")
        return route_segments

    def _build_segment_tokens(self, interfaces: Iterable[NetworkInterface]) -> set[str]:
        tokens: set[str] = set()
        for interface in interfaces:
            vlan_token = _normalize_token(interface.vlan)
            if not vlan_token:
                continue
            tokens.add(vlan_token)
            tokens.add(f"vlan:{vlan_token}")
            segment = self._segments_by_vlan.get(vlan_token) or self._segments_by_name.get(vlan_token)
            if not segment:
                continue
            if segment.name:
                name_token = _normalize_token(segment.name)
                tokens.add(name_token)
                tokens.add(f"segment:{name_token}")
            if segment.vlan:
                tokens.add(f"vlan:{_normalize_token(segment.vlan)}")
        return tokens

    def _find_matching_service(self, target: str, proto: str, port: str) -> PublishedService | None:
        target_token = _normalize_token(target)
        for exposure in self.exposures:
            if _normalize_token(exposure.device) != target_token:
                continue
            if _normalize_token(exposure.proto) not in {"any", _normalize_token(proto)}:
                continue
            if not self._port_matches(exposure.port, port):
                continue
            return exposure
        return None

    def _find_matching_rule(
        self,
        source_ctx: _EndpointContext,
        target_ctx: _EndpointContext,
        proto: str,
        port: str,
    ) -> ACLRule | None:
        for rule in self.rules:
            if not self._selector_matches(rule.source, source_ctx):
                continue
            if not self._selector_matches(rule.target, target_ctx):
                continue
            if _normalize_token(rule.proto) not in {"any", _normalize_token(proto)}:
                continue
            if not self._port_matches(rule.port, port):
                continue
            return rule
        return None

    def _find_hops(
        self,
        source_ctx: _EndpointContext,
        target_ctx: _EndpointContext,
    ) -> tuple[list[str], list[TraceHop]]:
        if source_ctx.label == target_ctx.label:
            return [source_ctx.label], []

        graph = self._build_route_graph()
        start = "Internet" if source_ctx.kind == "internet" else source_ctx.label
        end = target_ctx.label

        if start not in graph or end not in graph:
            return [], []

        queue = deque([start])
        visited = {start}
        previous: dict[str, tuple[str | None, TraceHop | None]] = {start: (None, None)}

        while queue:
            current = queue.popleft()
            if current == end:
                break
            for hop in graph.get(current, []):
                if hop.target in visited:
                    continue
                visited.add(hop.target)
                previous[hop.target] = (current, hop)
                queue.append(hop.target)

        if end not in previous:
            return [], []

        nodes: list[str] = []
        hop_details: list[TraceHop] = []
        cursor = end
        while cursor is not None:
            nodes.append(cursor)
            prev_node, hop = previous[cursor]
            if hop is not None:
                hop_details.append(hop)
            cursor = prev_node

        nodes.reverse()
        hop_details.reverse()
        return nodes, hop_details

    def _build_route_graph(self) -> dict[str, list[TraceHop]]:
        graph: dict[str, list[TraceHop]] = {}
        active_interfaces_by_device: dict[str, list[NetworkInterface]] = {}
        for interface in self.interfaces:
            if not self._is_active_interface(interface):
                continue
            device_name = self._device_name_from_token(interface.device)
            if not device_name:
                continue
            active_interfaces_by_device.setdefault(device_name, []).append(interface)

        for device_name in active_interfaces_by_device:
            graph.setdefault(device_name, [])

        device_names = sorted(active_interfaces_by_device)
        for index, left_name in enumerate(device_names):
            left_segments = self._build_route_segments(active_interfaces_by_device[left_name])
            if not left_segments:
                continue
            for right_name in device_names[index + 1 :]:
                right_segments = self._build_route_segments(active_interfaces_by_device[right_name])
                shared_segments = sorted(left_segments & right_segments)
                if not shared_segments:
                    continue
                via_segment = self._format_route_segment(shared_segments[0])
                self._add_graph_edge(graph, left_name, right_name, via_segment, "shared segment")
                self._add_graph_edge(graph, right_name, left_name, via_segment, "shared segment")

        ingress_devices = self._find_ingress_devices(active_interfaces_by_device)
        if ingress_devices:
            graph.setdefault("Internet", [])
            for device_name in sorted(ingress_devices):
                via = self._describe_ingress_path(active_interfaces_by_device.get(device_name, []))
                self._add_graph_edge(graph, "Internet", device_name, via, "edge ingress")
                self._add_graph_edge(graph, device_name, "Internet", via, "edge egress")
        else:
            public_targets = {
                self._device_name_from_token(exposure.device)
                for exposure in self.exposures
                if _normalize_token(exposure.visibility) in {"published", "public", "internet", "external"}
            }
            public_targets.discard("")
            if public_targets:
                graph.setdefault("Internet", [])
                for device_name in sorted(public_targets):
                    self._add_graph_edge(graph, "Internet", device_name, "public exposure", "direct public reachability")
                    self._add_graph_edge(graph, device_name, "Internet", "public exposure", "direct public reachability")

        return graph

    def _find_ingress_devices(self, active_interfaces_by_device: dict[str, list[NetworkInterface]]) -> set[str]:
        ingress_devices: set[str] = set()
        ingress_tokens = {"wan", "internet", "external", "uplink", "outside", "public"}
        ingress_roles = {"firewall", "router", "gateway", "edge", "perimeter"}

        for device_name, interfaces in active_interfaces_by_device.items():
            device = self._devices_by_name.get(_normalize_token(device_name))
            device_tokens = {
                _normalize_token(device.name if device else device_name),
                _normalize_token(device.device_type if device else ""),
                _normalize_token(device.role if device else ""),
            }
            if device_tokens & ingress_roles:
                ingress_devices.add(device_name)
                continue

            for interface in interfaces:
                vlan_token = _normalize_token(interface.vlan)
                route_tokens = {
                    vlan_token,
                    f"vlan:{vlan_token}" if vlan_token else "",
                }
                segment = self._segments_by_vlan.get(vlan_token) or self._segments_by_name.get(vlan_token)
                if segment and segment.name:
                    route_tokens.add(_normalize_token(segment.name))
                    route_tokens.add(f"segment:{_normalize_token(segment.name)}")
                if route_tokens & ingress_tokens:
                    ingress_devices.add(device_name)
                    break
        return ingress_devices

    def _describe_ingress_path(self, interfaces: Iterable[NetworkInterface]) -> str:
        ingress_tokens = {"wan", "internet", "external", "uplink", "outside", "public"}
        for interface in interfaces:
            vlan_token = _normalize_token(interface.vlan)
            if vlan_token in ingress_tokens:
                return interface.interface or vlan_token.upper()
            segment = self._segments_by_vlan.get(vlan_token) or self._segments_by_name.get(vlan_token)
            if segment and _normalize_token(segment.name) in ingress_tokens:
                return interface.interface or segment.name
        return "edge link"

    def _add_graph_edge(self, graph: dict[str, list[TraceHop]], source: str, target: str, via: str, note: str) -> None:
        graph.setdefault(source, [])
        graph[source].append(TraceHop(source=source, target=target, via=via, note=note))

    def _device_name_from_token(self, token: str) -> str:
        normalized = _normalize_token(token)
        device = self._devices_by_name.get(normalized)
        return device.name if device else ""

    def _format_route_segment(self, route_segment: str) -> str:
        normalized = _normalize_token(route_segment)
        if normalized.startswith("segment:"):
            return normalized.split(":", 1)[1].upper()
        if normalized.startswith("vlan:"):
            return normalized.split(":", 1)[1].upper()
        return route_segment

    def _is_active_interface(self, interface: NetworkInterface) -> bool:
        return _normalize_token(interface.status) in {"up", "active", "enabled"}

    def _selector_matches(self, selector: str, endpoint_ctx: _EndpointContext) -> bool:
        normalized = _normalize_token(selector)
        if normalized in {"", "any", "*"}:
            return True
        if endpoint_ctx.kind == "internet":
            return normalized in endpoint_ctx.tags
        return normalized in endpoint_ctx.tags

    def _port_matches(self, rule_port: str, requested_port: str) -> bool:
        normalized_rule = _normalize_token(rule_port)
        normalized_port = _normalize_token(requested_port)
        if normalized_rule in {"", "any", "*"}:
            return True
        if normalized_rule == normalized_port:
            return True
        if "," in normalized_rule:
            return any(self._port_matches(candidate, normalized_port) for candidate in normalized_rule.split(","))
        if "-" in normalized_rule:
            start, _, end = normalized_rule.partition("-")
            if start.isdigit() and end.isdigit() and normalized_port.isdigit():
                return int(start) <= int(normalized_port) <= int(end)
        return False

    def _evaluate_visibility(
        self,
        source_ctx: _EndpointContext,
        target_ctx: _EndpointContext,
        exposure: PublishedService,
    ) -> tuple[bool, str]:
        visibility = _normalize_token(exposure.visibility)
        if visibility in {"published", "public", "internet", "external"}:
            return True, "Service visibility is public/published."
        if visibility in {"internal", "internal only", "private"}:
            if source_ctx.kind == "internet":
                return False, "Service exists but is marked internal-only."
            return True, "Service is internal-only and the source is internal."
        if visibility in {"management", "management only", "mgmt", "mgmt only"}:
            if any(token in source_ctx.tags for token in {"mgmt", "management", "segment:mgmt", "vlan:10"}):
                return True, "Source matches the management visibility requirement."
            return False, "Service is restricted to management sources."
        if visibility in {"same segment", "same-segment", "segment only"}:
            shared = source_ctx.segment_tokens & target_ctx.segment_tokens
            if source_ctx.kind != "internet" and shared:
                return True, f"Source and target share the segment(s): {', '.join(sorted(shared))}."
            return False, "Service is limited to the same segment and the source does not match."
        if visibility.startswith("segment:") or visibility.startswith("vlan:"):
            if visibility in source_ctx.tags:
                return True, f"Source matches restricted visibility '{exposure.visibility}'."
            return False, f"Service is restricted to '{exposure.visibility}'."
        if visibility in {"disabled", "off", "closed"}:
            return False, "Service is disabled."
        if source_ctx.kind == "internet":
            return False, f"Unknown visibility '{exposure.visibility}' defaults to non-public."
        return True, f"Unknown visibility '{exposure.visibility}' treated as internal-only; source is internal."


def format_trace_result(result: TraceResult) -> str:
    lines = [
        "Trace request",
        f"- From: {result.request.source}",
        f"- To: {result.request.target}",
        f"- Service: {result.request.proto}/{result.request.port}",
        "",
        "Outcome",
        f"- Result: {result.verdict}",
        f"- Why: {result.reason}",
        "",
    ]

    if result.hops:
        lines.append("Path")
        lines.append("- " + " -> ".join(result.hops))
        if result.hop_details:
            lines.append("- Hop details:")
            for hop in result.hop_details:
                detail = f"{hop.source} -> {hop.target} via {hop.via}"
                if hop.note:
                    detail += f" ({hop.note})"
                lines.append(f"  {detail}")
        lines.append("")

    if result.matched_service:
        lines.append(
            "Matched service"
        )
        lines.append(
            "- "
            f"{result.matched_service.device} {result.matched_service.service or '-'} "
            f"{result.matched_service.proto}/{result.matched_service.port} "
            f"[{result.matched_service.visibility}]"
        )
    if result.matched_rule:
        lines.append(
            "Matched ACL"
        )
        lines.append(
            "- "
            f"{result.matched_rule.source} -> {result.matched_rule.target} "
            f"{result.matched_rule.proto}/{result.matched_rule.port} => {result.matched_rule.action}"
        )

    lines.append("")
    lines.append("Engine details")
    for step in result.steps:
        lines.append(f"- {step.phase}: {step.outcome} - {step.detail}")
    return "\n".join(lines).strip()
