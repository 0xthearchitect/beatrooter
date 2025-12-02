import re
import json
from PyQt6.QtCore import QPointF
from models.node import Node
from models.edge import Edge

class ToolsOutputParser:
    def __init__(self, graph_manager):
        self.graph_manager = graph_manager
        self.parsers = {
            'nmap': self.parse_nmap_output,
            'masscan': self.parse_masscan_output, 
            'whois': self.parse_whois_output,
            'nslookup': self.parse_nslookup_output,
            'sublist3r': self.parse_sublist3r_output,
            'exiftool': self.parse_exiftool_output,
            'gobuster': self.parse_gobuster_output
        }
    
    def parse_tool_output(self, tool_name, output, target=None):
        if tool_name in self.parsers:
            return self.parsers[tool_name](output, target)
        return []
    
    def parse_nmap_output(self, output, target=None):
        nodes_created = []
        
        host_pattern = r"Nmap scan report for (.+?)\n"
        ip_pattern = r"(\d+\.\d+\.\d+\.\d+)"
        port_pattern = r"(\d+)/(tcp|udp)\s+(\w+)\s+(.+)"
        os_pattern = r"OS:\s*(.+)"
        service_pattern = r"(\d+)/(tcp|udp)\s+(\w+)\s+([^\n]+)"
        
        hosts = re.findall(host_pattern, output)
        current_host = None
        
        for host in hosts:
            if re.match(ip_pattern, host):
                host_data = {
                    'hostname': '',
                    'ip_address': host,
                    'os': '',
                    'services': [],
                    'open_ports': 0,
                    'notes': f"Nmap scan: {target if target else 'unknown'}"
                }
            else:
                ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", host)
                ip = ip_match.group(1) if ip_match else ''
                host_data = {
                    'hostname': host,
                    'ip_address': ip,
                    'os': '',
                    'services': [],
                    'open_ports': 0,
                    'notes': f"Nmap scan: {target if target else 'unknown'}"
                }
            
            host_position = QPointF(len(nodes_created) * 200, 0)
            host_node = self.graph_manager.add_node('host', host_position, host_data)
            nodes_created.append(host_node)
            current_host = host_node
            
            os_match = re.search(os_pattern, output)
            if os_match:
                current_host.data['os'] = os_match.group(1)
        
        port_matches = re.findall(service_pattern, output)
        for port_match in port_matches:
            port, protocol, state, service_info = port_match
            if state.lower() == 'open':
                if current_host:
                    current_host.data['open_ports'] = current_host.data.get('open_ports', 0) + 1
                    
                    service_data = {
                        'port': int(port),
                        'service': service_info.split()[0] if service_info else 'unknown',
                        'protocol': protocol,
                        'version': service_info,
                        'banner': service_info,
                        'state': 'open',
                        'notes': f"Discovered via Nmap scan"
                    }
                    
                    service_position = QPointF(current_host.position.x() + 150, 
                                             current_host.position.y() + len(nodes_created) * 80)
                    service_node = self.graph_manager.add_node('port_service', service_position, service_data)
                    nodes_created.append(service_node)
                    
                    self.graph_manager.connect_nodes(current_host.id, service_node.id, f"runs_on_port_{port}")
        
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
            'registrar': '',
            'creation_date': '',
            'expiration_date': '',
            'name_servers': [],
            'status': '',
            'notes': 'WHOIS lookup'
        }
        
        registrar_pattern = r"Registrar:\s*(.+)"
        creation_pattern = r"(Creation Date|Created On):\s*(.+)"
        expiration_pattern = r"(Expiration Date|Expires On):\s*(.+)"
        nameserver_pattern = r"Name Server:\s*(.+)"
        status_pattern = r"Status:\s*(.+)"
        
        registrar_match = re.search(registrar_pattern, output, re.IGNORECASE)
        if registrar_match:
            domain_data['registrar'] = registrar_match.group(1).strip()
        
        creation_match = re.search(creation_pattern, output, re.IGNORECASE)
        if creation_match:
            domain_data['creation_date'] = creation_match.group(2).strip()
        
        expiration_match = re.search(expiration_pattern, output, re.IGNORECASE)
        if expiration_match:
            domain_data['expiration_date'] = expiration_match.group(2).strip()
        
        nameserver_matches = re.findall(nameserver_pattern, output, re.IGNORECASE)
        domain_data['name_servers'] = [ns.strip().lower() for ns in nameserver_matches]
        
        status_matches = re.findall(status_pattern, output, re.IGNORECASE)
        if status_matches:
            domain_data['status'] = ', '.join([s.strip() for s in status_matches])
        
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
        
        domain_data = {
            'name': target or 'unknown',
            'dns_records': [],
            'notes': 'DNS lookup results'
        }
        
        a_record_pattern = r"Address:\s*(\d+\.\d+\.\d+\.\d+)"
        mx_record_pattern = r"mail exchanger\s*=\s*(\d+)\s*([^\s]+)"
        ns_record_pattern = r"nameserver\s*=\s*([^\s]+)"
        cname_pattern = r"canonical name\s*=\s*([^\s]+)"
        
        a_matches = re.findall(a_record_pattern, output)
        for ip in a_matches:
            domain_data['dns_records'].append(f"A: {ip}")
            
            ip_data = {
                'address': ip,
                'hostname': target,
                'notes': f"A record for {target}"
            }
            
            ip_position = QPointF(len(nodes_created) * 180, 100)
            ip_node = self.graph_manager.add_node('ip', ip_position, ip_data)
            nodes_created.append(ip_node)
        
        if target:
            domain_position = QPointF(0, 0)
            domain_node = self.graph_manager.add_node('domain', domain_position, domain_data)
            nodes_created.append(domain_node)
            
            for node in nodes_created:
                if node.type == 'ip':
                    self.graph_manager.connect_nodes(domain_node.id, node.id, "resolves_to")
        
        return nodes_created
    
    def parse_sublist3r_output(self, output, target=None):
        nodes_created = []
        
        if not target:
            return nodes_created
        
        subdomain_pattern = r"([a-zA-Z0-9.-]+\." + re.escape(target) + r")"
        subdomains = re.findall(subdomain_pattern, output)
        
        main_domain_data = {
            'name': target,
            'subdomains_found': len(subdomains),
            'notes': 'Sublist3r enumeration'
        }
        
        main_domain_position = QPointF(0, 0)
        main_domain_node = self.graph_manager.add_node('domain', main_domain_position, main_domain_data)
        nodes_created.append(main_domain_node)
        
        for i, subdomain in enumerate(set(subdomains)):
            subdomain_data = {
                'name': subdomain,
                'parent_domain': target,
                'notes': f"Discovered via Sublist3r"
            }
            
            subdomain_position = QPointF(main_domain_position.x() + 200, 
                                       main_domain_position.y() + i * 120)
            subdomain_node = self.graph_manager.add_node('domain', subdomain_position, subdomain_data)
            nodes_created.append(subdomain_node)
            
            self.graph_manager.connect_nodes(main_domain_node.id, subdomain_node.id, "has_subdomain")
        
        return nodes_created
    
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
        
        found_pattern = r"(Status:\s*\d+).*?(Size:\s*[^\s]+).*?(http[s]?://[^\s]+)"
        directory_pattern = r"(\/\S+)\s+\(Status:\s*(\d+))"
        
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
        
        directory_matches = re.findall(directory_pattern, output)
        for path, status in directory_matches:
            endpoint_data = {
                'path': path,
                'method': 'GET',
                'status_code': int(status),
                'authentication_required': False,
                'vulnerable': int(status) in [200, 301, 302, 307],
                'notes': f"Discovered via Gobuster"
            }
            
            endpoint_position = QPointF(web_app_position.x() + 180, 
                                      web_app_position.y() + len(nodes_created) * 100)
            endpoint_node = self.graph_manager.add_node('endpoint', endpoint_position, endpoint_data)
            nodes_created.append(endpoint_node)
            
            self.graph_manager.connect_nodes(web_app_node.id, endpoint_node.id, "has_endpoint")
            
            web_app_node.data['endpoints_found'] = web_app_node.data.get('endpoints_found', 0) + 1
        
        return nodes_created