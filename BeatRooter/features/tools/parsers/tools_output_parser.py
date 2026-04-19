import re
import json
import ast
from PyQt6.QtCore import QPointF
from features.beatroot_canvas.models.node import Node
from features.beatroot_canvas.models.edge import Edge

class ToolsOutputParser:
    MAX_SUBFINDER_VISIBLE_NODES = 10
    MAX_SUBFINDER_NOTE_PREVIEW = 80
    MAX_GOBUSTER_VISIBLE_ENDPOINTS = 60
    MAX_GOBUSTER_NOTE_PREVIEW = 80
    GOBUSTER_WILDCARD_SIGNATURE_THRESHOLD = 12
    MAX_TSHARK_HOST_NODES = 30
    MAX_TSHARK_SERVICE_NODES = 80
    GOBUSTER_INTERESTING_STATUSES = {200, 201, 202, 204, 301, 302, 307, 308, 401}

    def __init__(self, graph_manager):
        self.graph_manager = graph_manager
        self.parsers = {
            'nmap': self.parse_nmap_output,
            'masscan': self.parse_masscan_output, 
            'whois': self.parse_whois_output,
            'nslookup': self.parse_nslookup_output,
            'dnsutils': self.parse_nslookup_output,
            'subfinder': self.parse_subfinder_output,
            'amass': self.parse_amass_output,
            'sublist3r': self.parse_subfinder_output,
            'exiftool': self.parse_exiftool_output,
            'gobuster': self.parse_gobuster_output,
            'whatweb': self.parse_whatweb_output,
            'netcat': self.parse_netcat_output,
            'tshark': self.parse_tshark_output,
        }
    
    def parse_tool_output(self, tool_name, output, target=None):
        if tool_name in self.parsers:
            return self.parsers[tool_name](output, target)
        return []
    
    def parse_nmap_output(self, output, target=None):
        nodes_created = []

        host_block_pattern = r"(Nmap scan report for .+?)(?=\nNmap scan report for |\nNmap done:|\Z)"
        ip_pattern = r"(\d+\.\d+\.\d+\.\d+)"
        os_pattern = r"OS:\s*(.+)"
        service_pattern = r"^(\d+)/(tcp|udp)\s+(\S+)\s+([^\n]+)$"

        host_blocks = re.findall(host_block_pattern, output, flags=re.DOTALL | re.MULTILINE)
        if not host_blocks:
            return nodes_created

        host_spacing_x = 280.0
        host_spacing_y = 230.0
        service_offset_x = 170.0
        service_spacing_y = 72.0
        max_columns = 3

        for host_index, host_block in enumerate(host_blocks):
            header_line = host_block.splitlines()[0].replace("Nmap scan report for ", "", 1).strip()
            ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", header_line)
            ip_address = ip_match.group(1) if ip_match else (header_line if re.fullmatch(ip_pattern, header_line) else "")
            hostname = header_line
            if ip_match:
                hostname = header_line.split("(", 1)[0].strip()
            elif ip_address:
                hostname = ""

            grid_col = host_index % max_columns
            grid_row = host_index // max_columns
            host_position = QPointF(grid_col * host_spacing_x, grid_row * host_spacing_y)

            host_data = {
                'hostname': hostname,
                'ip_address': ip_address,
                'os': '',
                'services': [],
                'open_ports': 0,
                'notes': f"Nmap scan: {target if target else 'unknown'}"
            }

            os_match = re.search(os_pattern, host_block)
            if os_match:
                host_data['os'] = os_match.group(1).strip()

            host_node = self.graph_manager.add_node('host', host_position, host_data)
            nodes_created.append(host_node)

            service_matches = re.findall(service_pattern, host_block, flags=re.MULTILINE)
            visible_service_index = 0
            for port, protocol, state, service_info in service_matches:
                if not str(state).lower().startswith('open'):
                    continue

                service_name = service_info.split()[0] if service_info else 'unknown'
                host_reference = ip_address or hostname or (target or 'unknown')
                service_data = {
                    'port': int(port),
                    'service': service_name,
                    'protocol': protocol,
                    'version': service_info.strip(),
                    'banner': service_info.strip(),
                    'state': state,
                    'host': host_reference,
                    'ip_address': ip_address,
                    'hostname': hostname,
                    'notes': f"Discovered via Nmap scan on {host_reference}"
                }

                service_position = QPointF(
                    host_position.x() + service_offset_x,
                    host_position.y() + (visible_service_index * service_spacing_y)
                )
                service_node = self.graph_manager.add_node('port_service', service_position, service_data)
                nodes_created.append(service_node)
                visible_service_index += 1

                host_node.data['open_ports'] = host_node.data.get('open_ports', 0) + 1
                host_node.data.setdefault('services', []).append(service_name)
                self.graph_manager.connect_nodes(host_node.id, service_node.id, f"runs_on_port_{port}")

        return nodes_created
    
    def parse_masscan_output(self, output, target=None):
        nodes_created = []
        
        open_port_pattern = r"open\s+(tcp|udp)\s+(\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)"
        banner_pattern = r"banner\s+(tcp|udp)\s+(\d+)\s+(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+(.+)"
        
        open_ports = {}
        
        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            open_match = re.match(open_port_pattern, line)
            if open_match:
                protocol, port, ip, timestamp = open_match.groups()
                
                if ip not in open_ports:
                    open_ports[ip] = {
                        'hostname': ip,
                        'ip_address': ip,
                        'open_ports': [],
                        'protocols': set(),
                        'notes': f"Masscan scan: {target if target else 'unknown'}"
                    }
                
                open_ports[ip]['open_ports'].append({
                    'port': int(port),
                    'protocol': protocol,
                    'state': 'open'
                })
                open_ports[ip]['protocols'].add(protocol)
                continue

            banner_match = re.match(banner_pattern, line)
            if banner_match:
                protocol, port, ip, timestamp, banner = banner_match.groups()
                
                if ip in open_ports:
                    for port_info in open_ports[ip]['open_ports']:
                        if port_info['port'] == int(port):
                            port_info['banner'] = banner
                            port_info['service'] = self.guess_service_from_banner(banner, int(port))

        for i, (ip, host_data) in enumerate(open_ports.items()):
            host_data['open_ports_count'] = len(host_data['open_ports'])
            host_data['protocols'] = list(host_data['protocols'])
            
            host_position = QPointF(i * 250, 0)
            host_node = self.graph_manager.add_node('host', host_position, host_data)
            nodes_created.append(host_node)

            for j, port_info in enumerate(host_data['open_ports']):
                service_data = {
                    'port': port_info['port'],
                    'service': port_info.get('service', 'unknown'),
                    'protocol': port_info['protocol'],
                    'banner': port_info.get('banner', ''),
                    'state': 'open',
                    'notes': f"Discovered via Masscan scan"
                }
                
                service_position = QPointF(
                    host_position.x() + 150,
                    host_position.y() + j * 80
                )
                service_node = self.graph_manager.add_node('port_service', service_position, service_data)
                nodes_created.append(service_node)
                
                self.graph_manager.connect_nodes(
                    host_node.id, 
                    service_node.id, 
                    f"runs_on_port_{port_info['port']}"
                )
        
        return nodes_created
    
    def guess_service_from_banner(self, banner, port):
        banner_lower = banner.lower()

        if 'http' in banner_lower or port in [80, 443, 8080, 8443]:
            return 'http'
        elif 'ssh' in banner_lower or port == 22:
            return 'ssh'
        elif 'ftp' in banner_lower or port == 21:
            return 'ftp'
        elif 'smtp' in banner_lower or port == 25:
            return 'smtp'
        elif 'dns' in banner_lower or port == 53:
            return 'dns'
        elif 'mysql' in banner_lower or port == 3306:
            return 'mysql'
        elif 'postgresql' in banner_lower or port == 5432:
            return 'postgresql'
        elif 'rdp' in banner_lower or port == 3389:
            return 'rdp'
        elif 'vnc' in banner_lower or port in [5900, 5901]:
            return 'vnc'
        else:
            common_ports = {
                20: 'ftp-data', 21: 'ftp', 22: 'ssh', 23: 'telnet',
                25: 'smtp', 53: 'dns', 67: 'dhcp', 68: 'dhcp',
                69: 'tftp', 80: 'http', 110: 'pop3', 111: 'rpcbind',
                119: 'nntp', 123: 'ntp', 135: 'msrpc', 137: 'netbios-ns',
                138: 'netbios-dgm', 139: 'netbios-ssn', 143: 'imap',
                161: 'snmp', 162: 'snmptrap', 389: 'ldap', 443: 'https',
                445: 'smb', 465: 'smtps', 514: 'syslog', 515: 'printer',
                587: 'smtp-submission', 631: 'ipp', 636: 'ldaps',
                993: 'imaps', 995: 'pop3s', 1080: 'socks', 1433: 'mssql',
                1521: 'oracle', 1723: 'pptp', 1883: 'mqtt', 1900: 'upnp',
                2049: 'nfs', 2082: 'cpanel', 2083: 'cpanel-ssl',
                2086: 'whm', 2087: 'whm-ssl', 2095: 'webmail',
                2096: 'webmail-ssl', 2181: 'zookeeper', 2375: 'docker',
                2376: 'docker-ssl', 3000: 'nodejs', 3306: 'mysql',
                3389: 'rdp', 3690: 'svn', 4369: 'epmd', 4789: 'docker-swarm',
                5000: 'upnp', 5432: 'postgresql', 5672: 'amqp',
                5900: 'vnc', 5901: 'vnc', 5984: 'couchdb', 6379: 'redis',
                6443: 'kubernetes', 6666: 'irc', 6667: 'irc',
                8000: 'http-alt', 8008: 'http-alt', 8080: 'http-proxy',
                8081: 'http-alt', 8443: 'https-alt', 8888: 'http-alt',
                9000: 'php-fpm', 9001: 'tor', 9042: 'cassandra',
                9092: 'kafka', 9100: 'jetdirect', 9200: 'elasticsearch',
                9300: 'elasticsearch', 9418: 'git', 9999: 'abyss',
                10000: 'webmin', 11211: 'memcached', 15672: 'rabbitmq',
                27017: 'mongodb', 27018: 'mongodb', 28017: 'mongodb',
                50000: 'db2', 50070: 'hadoop', 50075: 'hadoop',
                61616: 'activemq'
            }
            
            return common_ports.get(port, 'unknown')
        
    def parse_whois_output(self, output, target=None):
        nodes_created = []

        domain_data = {
            'name': target or 'unknown',
            'register': '',
            'creation_date': '',
            'expiration_date': '',
            'name_servers': [],
            'status': '',
            'notes': 'WHOIS lookup'
        }

        parsed_payload = self._parse_whois_structured_payload(output)

        if parsed_payload:
            domain_value = parsed_payload.get('domain_name') or parsed_payload.get('domain') or parsed_payload.get('name')
            if domain_value:
                domain_data['name'] = self._coerce_single_value(domain_value) or domain_data['name']

            registrar_value = parsed_payload.get('registrar') or parsed_payload.get('registrant_name') or parsed_payload.get('registrant')
            if registrar_value:
                domain_data['register'] = self._coerce_single_value(registrar_value)

            creation_value = parsed_payload.get('creation_date') or parsed_payload.get('created_on') or parsed_payload.get('created')
            if creation_value:
                domain_data['creation_date'] = self._coerce_single_value(creation_value)

            expiration_value = parsed_payload.get('expiration_date') or parsed_payload.get('expires_on') or parsed_payload.get('expiry_date')
            if expiration_value:
                domain_data['expiration_date'] = self._coerce_single_value(expiration_value)

            name_servers = parsed_payload.get('name_servers') or parsed_payload.get('nserver') or []
            domain_data['name_servers'] = self._coerce_name_servers(name_servers)

            status_value = parsed_payload.get('status') or parsed_payload.get('domain_status')
            if status_value:
                domain_data['status'] = self._coerce_single_value(status_value)

            extra_mappings = {
                'registrant_name': ('registrant_name', 'registrant'),
                'registrant_email': ('registrant_email',),
                'registrant_street': ('registrant_street', 'registrant_address'),
                'registrant_city': ('registrant_city',),
                'registrant_postal_code': ('registrant_postal_code',),
                'admin': ('admin', 'admin_name'),
                'admin_email': ('admin_email',),
                'admin_street': ('admin_street',),
                'admin_city': ('admin_city',),
                'admin_postal_code': ('admin_postal_code',),
                'updated_date': ('updated_date', 'updated_on'),
                'emails': ('emails',),
            }

            for output_key, payload_keys in extra_mappings.items():
                for payload_key in payload_keys:
                    value = parsed_payload.get(payload_key)
                    if value:
                        if output_key == 'emails':
                            domain_data[output_key] = self._coerce_name_servers(value)
                        else:
                            domain_data[output_key] = self._coerce_single_value(value)
                        break
        else:
            registrar_pattern = r"Registrar:\s*(.+)"
            creation_pattern = r"(Creation Date|Created On):\s*(.+)"
            expiration_pattern = r"(Expiration Date|Expires On):\s*(.+)"
            nameserver_pattern = r"Name Server:\s*(.+)"
            status_pattern = r"Status:\s*(.+)"

            registrar_match = re.search(registrar_pattern, output, re.IGNORECASE)
            if registrar_match:
                domain_data['register'] = registrar_match.group(1).strip()

            creation_match = re.search(creation_pattern, output, re.IGNORECASE)
            if creation_match:
                domain_data['creation_date'] = creation_match.group(2).strip()

            expiration_match = re.search(expiration_pattern, output, re.IGNORECASE)
            if expiration_match:
                domain_data['expiration_date'] = expiration_match.group(2).strip()

            nameserver_matches = re.findall(nameserver_pattern, output, re.IGNORECASE)
            domain_data['name_servers'] = [ns.strip().lower() for ns in nameserver_matches if ns.strip()]

            status_matches = re.findall(status_pattern, output, re.IGNORECASE)
            if status_matches:
                domain_data['status'] = ', '.join([s.strip() for s in status_matches if s.strip()])

        domain_data['notes'] = self._build_whois_notes(domain_data)
        
        domain_position = QPointF(0, len(nodes_created) * 150)
        domain_node = self.graph_manager.add_node('domain', domain_position, domain_data)
        nodes_created.append(domain_node)
        
        for i, nameserver in enumerate(domain_data['name_servers']):
            ns_data = {
                'name': nameserver,
                'type': 'nameserver',
                'notes': f"Nameserver for {domain_data['name']}"
            }
            
            ns_position = QPointF(domain_position.x() + 200, domain_position.y() + i * 100)
            ns_node = self.graph_manager.add_node('domain', ns_position, ns_data)
            nodes_created.append(ns_node)
            
            self.graph_manager.connect_nodes(domain_node.id, ns_node.id, "uses_nameserver")
        
        return nodes_created
    
    def parse_nslookup_output(self, output, target=None):
        nodes_created = []
        output_text = output or ""
        target_value = str(target or "").strip()

        # Parse common formats from nslookup / host / dig
        a_record_matches = set(re.findall(r"\bAddress:\s*(\d+\.\d+\.\d+\.\d+)", output_text))
        a_record_matches.update(re.findall(r"\bhas address\s+(\d+\.\d+\.\d+\.\d+)", output_text, re.IGNORECASE))
        a_record_matches.update(re.findall(r"^\S+\s+\d+\s+IN\s+A\s+(\d+\.\d+\.\d+\.\d+)\s*$", output_text, re.MULTILINE))
        # dig +short / simple answers can be just a line with an IP.
        for line in output_text.splitlines():
            candidate = line.strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", candidate):
                a_record_matches.add(candidate)

        ns_matches = set(re.findall(r"nameserver\s*=\s*([^\s]+)", output_text, re.IGNORECASE))
        ns_matches.update(re.findall(r"\bname server\s+([^\s]+)", output_text, re.IGNORECASE))
        ns_matches.update(re.findall(r"^\S+\s+\d+\s+IN\s+NS\s+([^\s]+)\s*$", output_text, re.MULTILINE))

        mx_matches = re.findall(r"mail exchanger\s*=\s*(\d+)\s*([^\s]+)", output_text, re.IGNORECASE)
        mx_matches += re.findall(r"^\S+\s+\d+\s+IN\s+MX\s+(\d+)\s+([^\s]+)\s*$", output_text, re.MULTILINE)

        cname_matches = set(re.findall(r"canonical name\s*=\s*([^\s]+)", output_text, re.IGNORECASE))
        cname_matches.update(re.findall(r"^\S+\s+\d+\s+IN\s+CNAME\s+([^\s]+)\s*$", output_text, re.MULTILINE))

        reverse_name_matches = set(re.findall(
            r"(?:\d+\.\d+\.\d+\.\d+\.in-addr\.arpa)\s+name\s*=\s*([^\s]+)",
            output_text,
            re.IGNORECASE,
        ))
        reverse_name_matches.update(re.findall(
            r"(?:\d+\.\d+\.\d+\.\d+\.in-addr\.arpa\.?\s+\d*\s*IN\s+PTR\s+)([^\s]+)",
            output_text,
            re.IGNORECASE,
        ))

        target_is_ip = bool(re.match(r"^\d+\.\d+\.\d+\.\d+$", target_value))

        # Reverse lookup target (IP) -> build DNS graph nodes (ip + domain when PTR exists).
        if target_is_ip:
            ip_data = {
                "address": target_value,
                "hostname": "",
                "notes": "Reverse DNS lookup (PTR)",
            }
            ip_node = self.graph_manager.add_node("ip", QPointF(0, 0), ip_data)
            nodes_created.append(ip_node)

            if reverse_name_matches:
                ptr_name = next(iter(sorted(reverse_name_matches))).rstrip(".")
                ip_node.data["hostname"] = ptr_name
                domain_node = self.graph_manager.add_node(
                    "domain",
                    QPointF(-200, 0),
                    {
                        "name": ptr_name,
                        "dns_records": [f"PTR: {target_value}"],
                        "notes": "Resolved from reverse DNS (PTR)",
                    },
                )
                nodes_created.append(domain_node)
                self.graph_manager.connect_nodes(domain_node.id, ip_node.id, "resolves_to")

            return nodes_created

        domain_name = target_value or ""
        if not domain_name and cname_matches:
            domain_name = next(iter(cname_matches))

        if not domain_name:
            return nodes_created

        dns_records = []
        for ip in sorted(a_record_matches):
            dns_records.append(f"A: {ip}")
        for cname in sorted(cname_matches):
            dns_records.append(f"CNAME: {cname}")
        for ns in sorted(ns_matches):
            dns_records.append(f"NS: {ns}")
        for pref, mx in mx_matches:
            dns_records.append(f"MX: {pref} {mx}")

        domain_data = {
            "name": domain_name,
            "dns_records": dns_records,
            "notes": "DNS lookup results",
        }
        domain_node = self.graph_manager.add_node("domain", QPointF(0, 0), domain_data)
        nodes_created.append(domain_node)

        for idx, ip in enumerate(sorted(a_record_matches)):
            ip_data = {
                "address": ip,
                "hostname": domain_name,
                "notes": f"A record for {domain_name}",
            }
            ip_node = self.graph_manager.add_node("ip", QPointF(180, idx * 90), ip_data)
            nodes_created.append(ip_node)
            self.graph_manager.connect_nodes(domain_node.id, ip_node.id, "resolves_to")

        for idx, ns in enumerate(sorted(ns_matches)):
            ns_data = {
                "name": ns.rstrip("."),
                "type": "nameserver",
                "notes": f"NS for {domain_name}",
            }
            ns_node = self.graph_manager.add_node("domain", QPointF(360, idx * 90), ns_data)
            nodes_created.append(ns_node)
            self.graph_manager.connect_nodes(domain_node.id, ns_node.id, "uses_nameserver")

        return nodes_created
    
    def parse_subfinder_output(self, output, target=None):
        return self._parse_subdomain_enumerator_output(output, target, tool_label="Subfinder")

    def parse_amass_output(self, output, target=None):
        return self._parse_subdomain_enumerator_output(output, target, tool_label="Amass")

    def _parse_subdomain_enumerator_output(self, output, target=None, tool_label="Subdomain Enumerator"):
        nodes_created = []
        
        if not target:
            return nodes_created

        subdomains = self._extract_subfinder_subdomains(output, target)
        main_domain_data = {
            'name': target,
            'subdomains_found': len(subdomains),
            'notes': f'{tool_label} enumeration'
        }
        
        main_domain_position = QPointF(0, 0)
        main_domain_node = self.graph_manager.add_node('domain', main_domain_position, main_domain_data)
        nodes_created.append(main_domain_node)

        visible_subdomains = subdomains[:self.MAX_SUBFINDER_VISIBLE_NODES]
        hidden_subdomains = subdomains[self.MAX_SUBFINDER_VISIBLE_NODES:]

        for i, subdomain in enumerate(visible_subdomains):
            subdomain_data = {
                'name': subdomain,
                'parent_domain': target,
                'notes': f"Discovered via {tool_label}"
            }
            
            subdomain_position = QPointF(main_domain_position.x() + 200, 
                                       main_domain_position.y() + i * 120)
            subdomain_node = self.graph_manager.add_node('domain', subdomain_position, subdomain_data)
            nodes_created.append(subdomain_node)
            
            self.graph_manager.connect_nodes(main_domain_node.id, subdomain_node.id, "has_subdomain")

        if hidden_subdomains:
            preview = "\n".join(hidden_subdomains[:self.MAX_SUBFINDER_NOTE_PREVIEW])
            remaining_count = len(hidden_subdomains)
            hidden_note_data = {
                'title': f'{tool_label} Overflow ({remaining_count})',
                'content': (
                    f"Target: {target}\n"
                    f"Visible subdomain nodes: {len(visible_subdomains)}\n"
                    f"Hidden subdomains: {remaining_count}\n\n"
                    f"Preview:\n{preview}"
                ),
                'category': 'subdomain_enumeration',
                'priority': 'medium',
                'notes': f'Additional {tool_label} results grouped to keep the canvas usable.'
            }
            note_position = QPointF(main_domain_position.x() + 230, main_domain_position.y() + len(visible_subdomains) * 120)
            overflow_node = self.graph_manager.add_node('note', note_position, hidden_note_data)
            nodes_created.append(overflow_node)
            self.graph_manager.connect_nodes(main_domain_node.id, overflow_node.id, "subdomain_overflow")
        
        return nodes_created

    def _parse_whois_structured_payload(self, output):
        if not output:
            return None

        text = output.strip()
        if not text:
            return None

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        json_candidate = self._extract_json_object(text)
        if json_candidate:
            try:
                parsed = json.loads(json_candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        if text.startswith("{") and text.endswith("}"):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        if json_candidate:
            try:
                parsed = ast.literal_eval(json_candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        return None

    def _extract_json_object(self, text):
        start = text.find("{")
        if start < 0:
            return ""

        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == "\"":
                    in_string = False
                continue

            if char == "\"":
                in_string = True
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1].strip()
        return ""

    def _build_whois_notes(self, domain_data):
        note_lines = ["WHOIS lookup"]
        for key in (
            "register",
            "creation_date",
            "expiration_date",
            "status",
            "registrant_name",
            "registrant_email",
            "admin",
            "admin_email",
        ):
            value = domain_data.get(key)
            if not value:
                continue
            label = key.replace("_", " ").title()
            note_lines.append(f"{label}: {value}")
        return "\n".join(note_lines)

    def _coerce_single_value(self, value):
        if isinstance(value, (list, tuple, set)):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return ", ".join(cleaned)
        return str(value).strip()

    def _coerce_name_servers(self, value):
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip().lower() for item in value if str(item).strip()]

        if not value:
            return []

        text = str(value)
        parts = [part.strip().lower() for part in re.split(r"[,\n;]+", text) if part.strip()]
        return parts

    def _extract_subfinder_subdomains(self, output, target):
        if not output or not target:
            return []

        normalized_target = str(target).strip().lower().rstrip(".")
        if not normalized_target:
            return []

        subdomains = []
        seen = set()
        domain_regex = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+" + re.escape(normalized_target) + r"$",
            re.IGNORECASE,
        )

        for raw_line in output.splitlines():
            candidate = raw_line.strip().lower().rstrip(".")
            if not candidate:
                continue
            if candidate.startswith(("[", "process ", "traceback", "file ", "indexerror", "error ")):
                continue
            if not domain_regex.match(candidate):
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            subdomains.append(candidate)

        subdomains.sort(key=self._subdomain_sort_key)
        return subdomains

    def parse_sublist3r_output(self, output, target=None):
        return self.parse_subfinder_output(output, target)

    def _subdomain_sort_key(self, subdomain):
        labels = subdomain.split(".")
        return (len(labels), len(subdomain), subdomain)
    
    def parse_exiftool_output(self, output, target=None):
        nodes_created = []
        
        if not target:
            return nodes_created
        
        metadata = {}
        lines = output.split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        screenshot_data = {
            'filename': target,
            'file_path': target,
            'metadata': metadata,
            'notes': 'ExifTool metadata extraction'
        }
        
        if 'File Size' in metadata:
            screenshot_data['file_size'] = metadata['File Size']
        if 'Image Size' in metadata:
            screenshot_data['dimensions'] = metadata['Image Size']
        if 'File Type' in metadata:
            screenshot_data['format'] = metadata['File Type']
        if 'Create Date' in metadata:
            screenshot_data['timestamp'] = metadata['Create Date']

        screenshot_position = QPointF(0, 0)
        screenshot_node = self.graph_manager.add_node('screenshot', screenshot_position, screenshot_data)
        nodes_created.append(screenshot_node)
        
        return nodes_created
    
    def parse_gobuster_output(self, output, target=None):
        nodes_created = []
        
        if not target:
            return nodes_created

        # Gobuster output lines look like:
        # index.html           (Status: 200) [Size: 358]
        directory_pattern = re.compile(
            r"^(\S+)\s+\(Status:\s*(\d+)\)\s+\[Size:\s*([^\]]+)\]$",
            re.MULTILINE,
        )
        
        web_app_data = {
            'url': target,
            'endpoints_found': 0,
            'technology_stack': '',
            'vulnerabilities_found': 0,
            'risk_level': 'unknown',
            'notes': 'Gobuster directory enumeration'
        }
        
        web_app_position = QPointF(0, 0)
        web_app_node = self.graph_manager.add_node('web_application', web_app_position, web_app_data)
        nodes_created.append(web_app_node)

        seen_paths = set()
        filtered_by_status = {}
        all_entries = []
        directory_matches = directory_pattern.findall(output or "")

        for path, status, size in directory_matches:
            normalized_path = str(path).strip()
            if not normalized_path:
                continue
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)

            status_code = int(status)
            entry = {
                "path": normalized_path,
                "status": status_code,
                "size": str(size).strip(),
            }
            all_entries.append(entry)

            if status_code not in self.GOBUSTER_INTERESTING_STATUSES:
                filtered_by_status[status_code] = filtered_by_status.get(status_code, 0) + 1

        interesting_entries = [
            entry for entry in all_entries
            if entry["status"] in self.GOBUSTER_INTERESTING_STATUSES
        ]

        # Gobuster can return wildcard-like noise (often auth/forbidden responses)
        # where many endpoints share the same status+size signature.
        signature_counts = {}
        for entry in interesting_entries:
            signature = (entry["status"], entry["size"])
            signature_counts[signature] = signature_counts.get(signature, 0) + 1

        noisy_signatures = {
            signature
            for signature, count in signature_counts.items()
            if count >= self.GOBUSTER_WILDCARD_SIGNATURE_THRESHOLD and signature[0] in {401, 403}
        }
        if noisy_signatures:
            cleaned_entries = []
            for entry in interesting_entries:
                signature = (entry["status"], entry["size"])
                if signature in noisy_signatures:
                    filtered_by_status[entry["status"]] = filtered_by_status.get(entry["status"], 0) + 1
                    continue
                cleaned_entries.append(entry)
            interesting_entries = cleaned_entries

        visible_entries = interesting_entries[:self.MAX_GOBUSTER_VISIBLE_ENDPOINTS]
        hidden_entries = interesting_entries[self.MAX_GOBUSTER_VISIBLE_ENDPOINTS:]

        for entry in visible_entries:
            path = entry["path"]
            status_code = entry["status"]
            size = entry["size"]

            endpoint_data = {
                'path': path,
                'method': 'GET',
                'status_code': status_code,
                'response_size': size,
                'authentication_required': False,
                'vulnerable': status_code in [200, 301, 302, 307],
                'notes': f"Discovered via Gobuster"
            }
            
            endpoint_position = QPointF(web_app_position.x() + 180, 
                                      web_app_position.y() + len(nodes_created) * 100)
            endpoint_node = self.graph_manager.add_node('endpoint', endpoint_position, endpoint_data)
            nodes_created.append(endpoint_node)
            
            self.graph_manager.connect_nodes(web_app_node.id, endpoint_node.id, "has_endpoint")
            
            web_app_node.data['endpoints_found'] = web_app_node.data.get('endpoints_found', 0) + 1

        noise_count = sum(filtered_by_status.values())
        overflow_count = len(hidden_entries)
        if noise_count > 0 or overflow_count > 0:
            noise_preview = ", ".join(
                f"{status}:{count}"
                for status, count in sorted(filtered_by_status.items())
            ) or "none"
            hidden_preview = "\n".join(entry["path"] for entry in hidden_entries[:self.MAX_GOBUSTER_NOTE_PREVIEW])
            overflow_note_data = {
                'title': 'Gobuster Overflow',
                'content': (
                    f"Target: {target}\n"
                    f"Visible endpoint nodes: {len(visible_entries)}\n"
                    f"Hidden interesting endpoints: {overflow_count}\n"
                    f"Filtered noisy statuses: {noise_count} ({noise_preview})\n\n"
                    f"Hidden preview:\n{hidden_preview}"
                ).strip(),
                'category': 'web_enumeration',
                'priority': 'medium',
                'notes': 'Gobuster results were condensed to keep canvas performance stable.'
            }
            note_position = QPointF(web_app_position.x() + 210, web_app_position.y() + max(120, len(visible_entries) * 90))
            overflow_node = self.graph_manager.add_node('note', note_position, overflow_note_data)
            nodes_created.append(overflow_node)
            self.graph_manager.connect_nodes(web_app_node.id, overflow_node.id, "gobuster_overflow")
        
        return nodes_created

    def parse_whatweb_output(self, output, target=None):
        nodes_created = []
        entries = self._parse_whatweb_entries(output)
        if not entries:
            return nodes_created

        primary_entry = self._select_primary_whatweb_entry(entries)
        if not primary_entry:
            return nodes_created
        redirect_entry = self._find_whatweb_redirect_entry(entries)

        web_app_position = QPointF(0, 0)
        web_app_data = {
            "url": primary_entry["url"],
            "title": primary_entry["title"],
            "http_status": primary_entry["status_text"],
            "web_server": primary_entry["web_server"],
            "redirect_location": redirect_entry["redirect_location"] if redirect_entry else "",
            "ip_address": primary_entry["ip_address"],
            "technology_stack": primary_entry["technologies"],
            "fingerprint": primary_entry["raw_line"],
            "authentication_method": "",
            "endpoints": "",
            "vulnerabilities_found": 0,
            "risk_level": "unknown",
            "notes": "WhatWeb technology fingerprinting",
        }
        web_app_node = self.graph_manager.add_node("web_application", web_app_position, web_app_data)
        nodes_created.append(web_app_node)

        if primary_entry["ip_address"]:
            ip_node = self.graph_manager.add_node(
                "ip",
                QPointF(220, 0),
                {
                    "address": primary_entry["ip_address"],
                    "geo_location": primary_entry["country"],
                    "threat_level": "unknown",
                    "os": "",
                    "services": primary_entry["web_server"],
                    "ports": "",
                    "notes": f"Observed via WhatWeb for {primary_entry['url']}",
                },
            )
            nodes_created.append(ip_node)
            self.graph_manager.connect_nodes(web_app_node.id, ip_node.id, "resolves_to_ip")

        if redirect_entry and redirect_entry["redirect_location"]:
            redirect_host = self._extract_host_from_url(redirect_entry["redirect_location"])
            redirect_name = redirect_host or redirect_entry["redirect_location"]
            redirect_node = self.graph_manager.add_node(
                "domain",
                QPointF(-220, 0),
                {
                    "name": redirect_name,
                    "register": "",
                    "creation_date": "",
                    "name_servers": "",
                    "subnames": "",
                    "notes": f"Redirect target discovered by WhatWeb: {redirect_entry['redirect_location']}",
                },
            )
            nodes_created.append(redirect_node)
            self.graph_manager.connect_nodes(web_app_node.id, redirect_node.id, "redirects_to")

        if primary_entry["details"]:
            note_node = self.graph_manager.add_node(
                "note",
                QPointF(220, 120),
                {
                    "title": "WhatWeb Details",
                    "content": (
                        f"Target: {primary_entry['url']}\n"
                        f"HTTP: {primary_entry['status_text']}\n"
                        f"Technologies: {primary_entry['technologies'] or 'n/a'}\n\n"
                        f"{primary_entry['details']}"
                    ).strip(),
                    "category": "web_enumeration",
                    "priority": "medium",
                    "notes": "Extended WhatWeb fingerprint details.",
                },
            )
            nodes_created.append(note_node)
            self.graph_manager.connect_nodes(web_app_node.id, note_node.id, "fingerprint_details")

        return nodes_created

    def _parse_whatweb_entries(self, output):
        entries = []
        for raw_line in (output or "").splitlines():
            line = raw_line.strip()
            if not line or not re.match(r"^https?://", line, re.IGNORECASE):
                continue

            match = re.match(r"^(https?://\S+)\s+\[(.*?)\](?:\s+(.*))?$", line)
            if not match:
                continue

            url, status_text, raw_fields = match.groups()
            field_values = {}
            bare_values = []
            for token in self._split_whatweb_fields(raw_fields or ""):
                field_match = re.match(r"^([A-Za-z0-9_.-]+)\[(.*)\]$", token)
                if field_match:
                    field_values[field_match.group(1).strip()] = field_match.group(2).strip()
                elif token:
                    bare_values.append(token.strip())

            technology_parts = []
            for key, value in field_values.items():
                if key in {"Country", "IP", "Title", "RedirectLocation", "HTTPServer"}:
                    continue
                technology_parts.append(f"{key}[{value}]" if value else key)
            technology_parts.extend(value for value in bare_values if value and value not in technology_parts)

            details = []
            for key in ("Country", "Email", "MetaGenerator", "PoweredBy", "X-Powered-By", "Strict-Transport-Security"):
                value = field_values.get(key, "")
                if value:
                    details.append(f"{key}: {value}")

            entries.append(
                {
                    "url": url,
                    "status_code": self._extract_whatweb_status_code(status_text),
                    "status_text": status_text,
                    "title": field_values.get("Title", ""),
                    "web_server": field_values.get("HTTPServer", "") or next((value for value in bare_values if value), ""),
                    "ip_address": field_values.get("IP", ""),
                    "redirect_location": field_values.get("RedirectLocation", ""),
                    "country": field_values.get("Country", ""),
                    "technologies": ", ".join(technology_parts),
                    "details": "\n".join(details),
                    "raw_line": line,
                }
            )
        return entries

    def _split_whatweb_fields(self, raw_fields):
        tokens = []
        current = []
        depth = 0
        for char in str(raw_fields or ""):
            if char == "[":
                depth += 1
            elif char == "]" and depth > 0:
                depth -= 1
            if char == "," and depth == 0:
                token = "".join(current).strip()
                if token:
                    tokens.append(token)
                current = []
                continue
            current.append(char)
        tail = "".join(current).strip()
        if tail:
            tokens.append(tail)
        return tokens

    def _select_primary_whatweb_entry(self, entries):
        if not entries:
            return None
        for entry in reversed(entries):
            if str(entry.get("status_code", "")).startswith("2"):
                return entry
        return entries[-1]

    def _find_whatweb_redirect_entry(self, entries):
        for entry in entries:
            if entry.get("redirect_location") and str(entry.get("status_code", "")).startswith("3"):
                return entry
        return None

    def _extract_host_from_url(self, value):
        match = re.match(r"^https?://([^/:?#]+)", str(value or "").strip(), re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _extract_whatweb_status_code(self, status_text):
        match = re.match(r"^(\d{3})", str(status_text or "").strip())
        return match.group(1) if match else str(status_text or "").strip()

    def parse_tshark_output(self, output, target=None):
        nodes_created = []
        if not output:
            return nodes_created

        endpoint_pattern = re.compile(
            r"(?P<src>(?:\d{1,3}\.){3}\d{1,3})(?:\.(?P<src_port>\d+))?\s+(?:->|→)\s+"
            r"(?P<dst>(?:\d{1,3}\.){3}\d{1,3})(?:\.(?P<dst_port>\d+))?"
        )
        ip_token_pattern = re.compile(r"((?:\d{1,3}\.){3}\d{1,3})(?:\.(\d+))?")
        ipv4_pattern = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")

        host_nodes = {}
        service_seen = set()
        service_index = 0

        def ensure_host_node(ip_addr):
            if ip_addr in host_nodes:
                return host_nodes[ip_addr]
            if len(host_nodes) >= self.MAX_TSHARK_HOST_NODES:
                return None

            host_position = QPointF((len(host_nodes) % 4) * 240, (len(host_nodes) // 4) * 160)
            host_data = {
                "hostname": ip_addr,
                "ip_address": ip_addr,
                "notes": f"Observed via TShark ({target or 'capture'})",
            }
            host_node = self.graph_manager.add_node("host", host_position, host_data)
            host_nodes[ip_addr] = host_node
            nodes_created.append(host_node)
            return host_node

        for raw_line in output.splitlines():
            line = (raw_line or "").strip()
            if not line:
                continue

            src_ip = ""
            dst_ip = ""
            dst_port = ""
            protocol_name = "unknown"

            csv_parts = [part.strip() for part in line.split(",")]
            if len(csv_parts) >= 2 and ipv4_pattern.match(csv_parts[0]) and ipv4_pattern.match(csv_parts[1]):
                src_ip = csv_parts[0]
                dst_ip = csv_parts[1]
                if len(csv_parts) > 2 and csv_parts[2].isdigit():
                    dst_port = csv_parts[2]
                elif len(csv_parts) > 3 and csv_parts[3].isdigit():
                    dst_port = csv_parts[3]
                if len(csv_parts) > 4 and csv_parts[4]:
                    protocol_name = str(csv_parts[4]).strip().lower()
            else:
                match = endpoint_pattern.search(line)
                if match:
                    src_ip = match.group("src")
                    dst_ip = match.group("dst")
                    dst_port = match.group("dst_port") or ""
                else:
                    token_matches = ip_token_pattern.findall(line)
                    if len(token_matches) >= 2:
                        src_ip = token_matches[0][0]
                        dst_ip = token_matches[1][0]
                        dst_port = token_matches[1][1] or ""

            if not src_ip or not dst_ip:
                continue

            src_node = ensure_host_node(src_ip)
            dst_node = ensure_host_node(dst_ip)
            if not src_node or not dst_node:
                continue

            if src_node.id != dst_node.id:
                try:
                    self.graph_manager.connect_nodes(src_node.id, dst_node.id, "network_flow")
                except Exception:
                    pass

            if not dst_port:
                continue
            if service_index >= self.MAX_TSHARK_SERVICE_NODES:
                continue
            if (dst_ip, dst_port) in service_seen:
                continue

            service_seen.add((dst_ip, dst_port))
            service_index += 1
            if protocol_name == "unknown":
                protocol_name = self._infer_tshark_protocol(line)
            service_data = {
                "port": int(dst_port),
                "protocol": protocol_name,
                "service": protocol_name if protocol_name != "unknown" else "unknown",
                "state": "observed",
                "notes": "Observed via TShark capture flow",
            }
            service_position = QPointF(dst_node.position.x() + 170, dst_node.position.y() + (service_index % 6) * 70)
            service_node = self.graph_manager.add_node("port_service", service_position, service_data)
            nodes_created.append(service_node)

            try:
                self.graph_manager.connect_nodes(dst_node.id, service_node.id, f"runs_on_port_{dst_port}")
            except Exception:
                pass

        return nodes_created

    def _infer_tshark_protocol(self, line):
        if not line:
            return "unknown"
        for proto in ("TCP", "UDP", "ICMP", "DNS", "TLS", "HTTP", "HTTPS", "ARP"):
            if re.search(rf"\b{proto}\b", line, re.IGNORECASE):
                return proto.lower()
        return "unknown"

    def parse_netcat_output(self, output, target=None):
        nodes_created = []
        target_host = str(target or "").strip()
        if not target_host:
            return nodes_created

        host_node = self.graph_manager.add_node(
            "host",
            QPointF(0, 0),
            {
                "hostname": target_host,
                "ip_address": target_host if re.match(r"^\d+\.\d+\.\d+\.\d+$", target_host) else "",
                "notes": "Netcat connectivity scan target",
            },
        )
        nodes_created.append(host_node)

        output_text = output or ""
        open_ports = set()

        # OpenBSD nc output patterns (examples):
        # "Connection to 192.168.1.1 80 port [tcp/http] succeeded!"
        # "192.168.1.1 [192.168.1.1] 443 (https) open"
        for port_match in re.findall(r"\b(\d{1,5})\s+\([^)]+\)\s+open\b", output_text, re.IGNORECASE):
            try:
                open_ports.add(int(port_match))
            except ValueError:
                continue

        for line in output_text.splitlines():
            if "succeeded" not in line.lower():
                continue
            inline_port = re.search(r"\s(\d{1,5})\s+port\b", line, re.IGNORECASE)
            if inline_port:
                try:
                    open_ports.add(int(inline_port.group(1)))
                except ValueError:
                    pass

        for idx, port in enumerate(sorted(open_ports)):
            service_node = self.graph_manager.add_node(
                "port_service",
                QPointF(190, idx * 90),
                {
                    "port": int(port),
                    "service": "unknown",
                    "protocol": "tcp",
                    "state": "open",
                    "notes": "Discovered via Netcat (-zv scan)",
                },
            )
            nodes_created.append(service_node)
            self.graph_manager.connect_nodes(host_node.id, service_node.id, f"runs_on_port_{port}")

        return nodes_created
