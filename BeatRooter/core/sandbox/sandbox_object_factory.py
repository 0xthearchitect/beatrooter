from models.object_model import ObjectType, ObjectCategory, SandboxObject
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor

class SandboxObjectFactory:
    
    OBJECT_TEMPLATES = {
        # === OPERATING SYSTEMS ===
        
        ObjectType.WINDOWS: {
            'name': 'Windows',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#0078d4',
            'icon': '',
            'default_properties': {
                'family': 'Windows',
                'vendor': 'Microsoft',
                'architecture': 'x64',
                'default_shell': 'PowerShell',
                'security_features': 'Windows Defender, BitLocker',
                'notes': ''
            },
            'allowed_children': [
                ObjectType.WINDOWS_10, ObjectType.WINDOWS_11,
                ObjectType.SERVICE, ObjectType.PROCESS,
                ObjectType.FOLDER, ObjectType.FILE, ObjectType.REGISTRY_KEY
            ]
        },
        
        ObjectType.LINUX: {
            'name': 'Linux',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#ff9900',
            'icon': '',
            'default_properties': {
                'family': 'Linux',
                'vendor': 'Various',
                'kernel_version': '',
                'package_manager': '',
                'default_shell': 'bash',
                'security_features': 'SELinux, AppArmor',
                'notes': ''
            },
            'allowed_children': [
                ObjectType.UBUNTU, ObjectType.DEBIAN, ObjectType.ARCH, 
                ObjectType.CENTOS, ObjectType.KALI,
                ObjectType.SERVICE, ObjectType.PROCESS,
                ObjectType.FOLDER, ObjectType.FILE, ObjectType.CONFIG_FILE
            ]
        },
        
        ObjectType.MACOS: {
            'name': 'macOS',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#999999',
            'icon': '',
            'default_properties': {
                'family': 'macOS',
                'vendor': 'Apple',
                'architecture': 'x64/ARM',
                'default_shell': 'zsh',
                'security_features': 'Gatekeeper, SIP, FileVault',
                'notes': ''
            },
            'allowed_children': [
                ObjectType.SERVICE, ObjectType.PROCESS,
                ObjectType.FOLDER, ObjectType.FILE
            ]
        },
        
        ObjectType.WINDOWS_10: {
            'name': 'Windows 10',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#0078d4',
            'icon': '',
            'default_properties': {
                'version': '10.0',
                'edition': 'Professional',
                'build_number': '',
                'end_of_support': '2025-10-14',
                'notes': ''
            },
            'allowed_children': [ObjectType.COMPUTER, ObjectType.SERVER]
        },
        
        ObjectType.WINDOWS_11: {
            'name': 'Windows 11',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#0078d4',
            'icon': '',
            'default_properties': {
                'version': '11.0',
                'edition': 'Professional',
                'build_number': '',
                'end_of_support': '2031-10-10',
                'notes': ''
            },
            'allowed_children': [ObjectType.COMPUTER, ObjectType.SERVER]
        },

        ObjectType.UBUNTU: {
            'name': 'Ubuntu',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#e95420',
            'icon': '',
            'default_properties': {
                'version': '22.04 LTS',
                'package_manager': 'apt',
                'desktop_environment': 'GNOME',
                'release_cycle': '2 years',
                'notes': ''
            },
            'allowed_children': [ObjectType.COMPUTER, ObjectType.SERVER, ObjectType.CONTAINER]
        },
        
        ObjectType.DEBIAN: {
            'name': 'Debian',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#d70751',
            'icon': '',
            'default_properties': {
                'version': '12',
                'package_manager': 'apt',
                'stability': 'Stable',
                'release_cycle': '2-3 years',
                'notes': ''
            },
            'allowed_children': [ObjectType.COMPUTER, ObjectType.SERVER]
        },
        
        ObjectType.ARCH: {
            'name': 'Arch Linux',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#1793d1',
            'icon': '',
            'default_properties': {
                'version': 'Rolling',
                'package_manager': 'pacman',
                'philosophy': 'KISS',
                'update_policy': 'Rolling Release',
                'notes': ''
            },
            'allowed_children': [ObjectType.COMPUTER]
        },
        
        ObjectType.CENTOS: {
            'name': 'CentOS',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#932279',
            'icon': '',
            'default_properties': {
                'version': 'Stream',
                'package_manager': 'yum/dnf',
                'enterprise_fork': 'RHEL',
                'notes': ''
            },
            'allowed_children': [ObjectType.SERVER]
        },
        
        ObjectType.KALI: {
            'name': 'Kali Linux',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#557c94',
            'icon': '',
            'default_properties': {
                'version': '2023.3',
                'purpose': 'Penetration Testing',
                'tools_included': 'Metasploit, Nmap, Wireshark',
                'notes': ''
            },
            'allowed_children': [ObjectType.COMPUTER]
        },
        
        ObjectType.SERVICE: {
            'name': 'Service',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#10b981',
            'icon': '',
            'default_properties': {
                'name': '',
                'type': 'systemd/service',
                'status': 'running',
                'startup_type': 'automatic',
                'executable_path': '',
                'dependencies': '',
                'logs': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.PROCESS: {
            'name': 'Process',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#10b981',
            'icon': '',
            'default_properties': {
                'name': '',
                'pid': '',
                'cpu_usage': '',
                'memory_usage': '',
                'user': '',
                'command_line': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.SCHEDULED_TASK: {
            'name': 'Scheduled Task',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#10b981',
            'icon': '',
            'default_properties': {
                'name': '',
                'schedule': '',
                'last_run': '',
                'next_run': '',
                'status': '',
                'action': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.FOLDER: {
            'name': 'Folder',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#6b7280',
            'icon': '',
            'default_properties': {
                'path': '',
                'permissions': '755',
                'owner': '',
                'group': '',
                'size': '',
                'created_date': '',
                'modified_date': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.FOLDER, ObjectType.FILE]
        },
        
        ObjectType.FILE: {
            'name': 'File',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#9ca3af',
            'icon': '',
            'default_properties': {
                'filename': '',
                'extension': '',
                'size': '',
                'permissions': '644',
                'owner': '',
                'modified_date': '',
                'checksum': '',
                'content_type': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.REGISTRY_KEY: {
            'name': 'Registry Key',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#8b5cf6',
            'icon': '',
            'default_properties': {
                'path': '',
                'values': '',
                'permissions': '',
                'last_modified': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.CONFIG_FILE: {
            'name': 'Config File',
            'category': ObjectCategory.OPERATING_SYSTEM,
            'color': '#8b5cf6',
            'icon': '',
            'default_properties': {
                'filename': '',
                'format': 'JSON/YAML/INI',
                'sections': '',
                'parameters': '',
                'sensitive_data': '',
                'notes': ''
            },
            'allowed_children': []
        },
    ObjectType.NETWORK_INTERFACE: {
        'name': 'Network Interface',
        'category': ObjectCategory.OPERATING_SYSTEM,
        'color': '#3b82f6',
        'icon': 'network_interface.png',
        'default_properties': {
            'interface_name': '',
            'ip_address': '',
            'mac_address': '',
            'subnet_mask': '',
            'gateway': '',
            'dns_servers': '',
            'status': 'up/down',
            'speed': '',
            'connection_type': '',
            'notes': ''
        },
        'allowed_children': []
    },
    
    ObjectType.OPEN_PORT: {
        'name': 'Open Port',
        'category': ObjectCategory.OPERATING_SYSTEM,
        'color': '#ef4444',
        'icon': 'open_port.png',
        'default_properties': {
            'port_number': '',
            'protocol': 'TCP/UDP',
            'service_name': '',
            'process_name': '',
            'process_id': '',
            'state': 'listening',
            'local_address': '',
            'foreign_address': '',
            'security_risk': 'low/medium/high',
            'notes': ''
        },
        'allowed_children': []
    },
    
    ObjectType.RUNNING_SERVICE: {
        'name': 'Running Service',
        'category': ObjectCategory.OPERATING_SYSTEM,
        'color': '#10b981',
        'icon': 'running_service.png',
        'default_properties': {
            'service_name': '',
            'display_name': '',
            'status': 'running/stopped',
            'startup_type': 'automatic/manual/disabled',
            'binary_path': '',
            'description': '',
            'log_on_as': '',
            'dependencies': '',
            'cpu_usage': '',
            'memory_usage': '',
            'security_implications': '',
            'notes': ''
        },
        'allowed_children': []
    },
    
    ObjectType.INSTALLED_SOFTWARE: {
        'name': 'Installed Software',
        'category': ObjectCategory.OPERATING_SYSTEM,
        'color': '#8b5cf6',
        'icon': 'installed_software.png',
        'default_properties': {
            'name': '',
            'version': '',
            'publisher': '',
            'install_date': '',
            'install_location': '',
            'size': '',
            'architecture': 'x64/x86',
            'update_available': False,
            'vulnerabilities': '',
            'security_rating': '',
            'notes': ''
        },
        'allowed_children': []
    },
    
    ObjectType.USER_ACCOUNT: {
        'name': 'User Account',
        'category': ObjectCategory.OPERATING_SYSTEM,
        'color': '#f59e0b',
        'icon': 'user_account.png',
        'default_properties': {
            'username': '',
            'full_name': '',
            'account_type': 'admin/user/guest',
            'status': 'enabled/disabled',
            'last_login': '',
            'password_age': '',
            'groups': '',
            'privileges': '',
            'home_directory': '',
            'login_script': '',
            'notes': ''
        },
        'allowed_children': []
    },
    
    ObjectType.SECURITY_POLICY: {
        'name': 'Security Policy',
        'category': ObjectCategory.OPERATING_SYSTEM,
        'color': '#dc2626',
        'icon': 'security_policy.png',
        'default_properties': {
            'policy_name': '',
            'policy_type': 'password/audit/firewall',
            'current_setting': '',
            'recommended_setting': '',
            'compliance_status': 'compliant/non-compliant',
            'risk_level': 'low/medium/high',
            'description': '',
            'impact': '',
            'notes': ''
        },
        'allowed_children': []
    },
    
    ObjectType.SYSTEM_INFO: {
        'name': 'System Information',
        'category': ObjectCategory.OPERATING_SYSTEM,
        'color': '#6b7280',
        'icon': 'system_info.png',
        'default_properties': {
            'hostname': '',
            'domain': '',
            'manufacturer': '',
            'model': '',
            'total_physical_memory': '',
            'available_physical_memory': '',
            'total_virtual_memory': '',
            'available_virtual_memory': '',
            'page_file_size': '',
            'page_file_free': '',
            'os_architecture': '',
            'boot_device': '',
            'system_directory': '',
            'last_boot_time': '',
            'timezone': '',
            'notes': ''
        },
        'allowed_children': []
    },
        
        # === NETWORK DEVICES ===
        
        ObjectType.COMPUTER: {
            'name': 'Computer',
            'category': ObjectCategory.NETWORK,
            'color': '#3b82f6',
            'icon': '',
            'default_properties': {
                'hostname': 'workstation-01',
                'ip_address': '192.168.1.100',
                'mac_address': '',
                'cpu': '',
                'ram': '8GB',
                'storage': '256GB SSD',
                'network_interface': 'eth0',
                'users': '',
                'installed_software': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.FOLDER, ObjectType.FILE, ObjectType.SERVICE]
        },
        
        ObjectType.SERVER: {
            'name': 'Server',
            'category': ObjectCategory.NETWORK,
            'color': '#059669',
            'icon': '',
            'default_properties': {
                'hostname': 'server-01',
                'ip_address': '192.168.1.10',
                'role': 'web server',
                'services': '',
                'cpu': '4 cores',
                'ram': '16GB',
                'storage': '1TB HDD',
                'backup_schedule': '',
                'monitoring': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.SERVICE, ObjectType.APACHE, ObjectType.NGINX, ObjectType.MYSQL, ObjectType.MONGODB]
        },
        
        ObjectType.ROUTER: {
            'name': 'Router',
            'category': ObjectCategory.NETWORK,
            'color': '#f59e0b',
            'icon': '',
            'default_properties': {
                'model': '',
                'firmware': '',
                'interfaces': 'eth0, eth1, wlan0',
                'routing_protocol': '',
                'firewall_rules': '',
                'dhcp_enabled': True,
                'wireless_ssid': '',
                'admin_interface': '192.168.1.1',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.SWITCH: {
            'name': 'Switch',
            'category': ObjectCategory.NETWORK,
            'color': '#d97706',
            'icon': '',
            'default_properties': {
                'model': '',
                'ports': 24,
                'vlan_support': True,
                'management_ip': '',
                'stackable': False,
                'poe_support': False,
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.FIREWALL: {
            'name': 'Firewall',
            'category': ObjectCategory.NETWORK,
            'color': '#dc2626',
            'icon': '',
            'default_properties': {
                'model': '',
                'throughput': '1Gbps',
                'security_zones': 'LAN, WAN, DMZ',
                'vpn_support': True,
                'intrusion_prevention': False,
                'application_control': False,
                'log_retention': '30 days',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.ACCESS_POINT: {
            'name': 'Access Point',
            'category': ObjectCategory.NETWORK,
            'color': '#7c3aed',
            'icon': '',
            'default_properties': {
                'model': '',
                'ssid': '',
                'security': 'WPA2/WPA3',
                'frequency': '2.4GHz/5GHz',
                'clients': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.MODEM: {
            'name': 'Modem',
            'category': ObjectCategory.NETWORK,
            'color': '#7c3aed',
            'icon': '',
            'default_properties': {
                'model': '',
                'type': 'Cable/DSL',
                'upstream_speed': '',
                'downstream_speed': '',
                'connection_status': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.CONTAINER: {
            'name': 'Container',
            'category': ObjectCategory.NETWORK,
            'color': '#84cc16',
            'icon': '',
            'default_properties': {
                'image': 'ubuntu:20.04',
                'runtime': 'docker',
                'ports': '',
                'volumes': '',
                'environment_variables': '',
                'resource_limits': '',
                'orchestration': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.SERVICE, ObjectType.FOLDER]
        },
        ObjectType.DATABASE: {
        'name': 'Database',
        'category': ObjectCategory.NETWORK,
        'color': '#336791',
        'icon': 'database.png',
        'default_properties': {
            'type': 'Relational/NoSQL',
            'host': 'localhost',
            'port': '',
            'version': '',
            'backup_strategy': '',
            'notes': ''
        },
        'allowed_children': []
    },
        
        # === WEB TECHNOLOGIES ===
        
        ObjectType.APACHE: {
            'name': 'Apache HTTP Server',
            'category': ObjectCategory.WEB,
            'color': '#d22128',
            'icon': 'apache.png',
            'default_properties': {
                'version': '2.4',
                'port': '80, 443',
                'ssl_enabled': False,
                'virtual_hosts': '',
                'modules': 'mod_ssl, mod_rewrite',
                'config_file': '/etc/apache2/apache2.conf',
                'log_path': '/var/log/apache2/',
                'document_root': '/var/www/html',
                'performance': '',
                'security_settings': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.NGINX: {
            'name': 'Nginx',
            'category': ObjectCategory.WEB,
            'color': '#009639',
            'icon': 'nginx.png',
            'default_properties': {
                'version': '1.18',
                'port': '80, 443',
                'ssl_enabled': False,
                'upstream_servers': '',
                'load_balancing': 'round-robin',
                'reverse_proxy': '',
                'config_file': '/etc/nginx/nginx.conf',
                'cache_settings': '',
                'performance_tuning': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.IIS: {
            'name': 'IIS Server',
            'category': ObjectCategory.WEB,
            'color': '#0078d4',
            'icon': 'iis.png',
            'default_properties': {
                'version': '10.0',
                'port': '80, 443',
                'applications': '',
                'app_pools': '',
                'authentication': 'Windows',
                'modules': '',
                'binding_config': '',
                'ssl_certificate': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.TOMCAT: {
            'name': 'Apache Tomcat',
            'category': ObjectCategory.WEB,
            'color': '#f8dc3d',
            'icon': 'tomcat.png',
            'default_properties': {
                'version': '9.0',
                'port': '8080',
                'java_version': '11',
                'webapps_dir': '',
                'connectors': '',
                'session_management': '',
                'jvm_settings': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.MYSQL: {
            'name': 'MySQL Database',
            'category': ObjectCategory.WEB,
            'color': '#00758f',
            'icon': 'mysql.png',
            'default_properties': {
                'version': '8.0',
                'type': 'Relational',
                'host': 'localhost',
                'port': 3306,
                'storage_engine': 'InnoDB',
                'character_set': 'utf8mb4',
                'users': '',
                'databases': '',
                'backup_strategy': '',
                'replication': '',
                'performance_tuning': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.POSTGRESQL: {
            'name': 'PostgreSQL',
            'category': ObjectCategory.WEB,
            'color': '#336791',
            'icon': 'postgresql.png',
            'default_properties': {
                'version': '15',
                'type': 'Relational',
                'host': 'localhost',
                'port': 5432,
                'encoding': 'UTF8',
                'extensions': '',
                'replication': '',
                'performance': '',
                'backup_config': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.MONGODB: {
            'name': 'MongoDB',
            'category': ObjectCategory.WEB,
            'color': '#47a248',
            'icon': 'mongodb.png',
            'default_properties': {
                'version': '6.0',
                'type': 'Document',
                'host': 'localhost',
                'port': 27017,
                'storage_engine': 'WiredTiger',
                'collections': '',
                'indexes': '',
                'sharding': False,
                'replica_set': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.REDIS: {
            'name': 'Redis',
            'category': ObjectCategory.WEB,
            'color': '#dc382d',
            'icon': 'redis.png',
            'default_properties': {
                'version': '7.0',
                'type': 'In-memory',
                'host': 'localhost',
                'port': 6379,
                'persistence': 'RDB/AOF',
                'databases': 16,
                'use_cases': 'Cache, Session Storage',
                'cluster_mode': False,
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.DJANGO: {
            'name': 'Django Framework',
            'category': ObjectCategory.WEB,
            'color': '#092e20',
            'icon': 'django.png',
            'default_properties': {
                'version': '4.2',
                'language': 'Python',
                'purpose': 'Web Development',
                'orm': 'Django ORM',
                'admin_interface': True,
                'authentication': 'Session-based',
                'installed_apps': '',
                'middleware': '',
                'url_routes': '',
                'settings_config': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.API_ENDPOINT, ObjectType.WEB_FOLDER]
        },
        
        ObjectType.FLASK: {
            'name': 'Flask Framework',
            'category': ObjectCategory.WEB,
            'color': '#000000',
            'icon': 'flask.png',
            'default_properties': {
                'version': '2.3',
                'language': 'Python',
                'purpose': 'Micro Web Framework',
                'extensions': '',
                'blueprints': '',
                'routes': '',
                'wsgi_server': '',
                'config_objects': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.API_ENDPOINT, ObjectType.WEB_FOLDER]
        },
        
        ObjectType.NODEJS: {
            'name': 'Node.js Runtime',
            'category': ObjectCategory.WEB,
            'color': '#68a063',
            'icon': 'nodejs.png',
            'default_properties': {
                'version': '18.x',
                'runtime': 'JavaScript',
                'package_manager': 'npm',
                'frameworks': 'Express, NestJS',
                'dependencies': '',
                'scripts': '',
                'environment_variables': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.EXPRESS, ObjectType.NESTJS, ObjectType.WEB_FOLDER]
        },
        
        ObjectType.SPRING: {
            'name': 'Spring Boot',
            'category': ObjectCategory.WEB,
            'color': '#6db33f',
            'icon': 'spring.png',
            'default_properties': {
                'version': '3.1',
                'language': 'Java',
                'purpose': 'Enterprise Applications',
                'dependencies': '',
                'embedded_server': 'Tomcat',
                'beans_config': '',
                'profiles': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.API_ENDPOINT, ObjectType.WEB_FOLDER]
        },
        
        ObjectType.EXPRESS: {
            'name': 'Express.js',
            'category': ObjectCategory.WEB,
            'color': '#000000',
            'icon': 'express.png',
            'default_properties': {
                'version': '4.18',
                'framework': 'Node.js',
                'middleware': '',
                'routing': '',
                'templates': '',
                'routes': '',
                'error_handling': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.API_ENDPOINT, ObjectType.WEB_FOLDER]
        },
        
        ObjectType.NESTJS: {
            'name': 'NestJS',
            'category': ObjectCategory.WEB,
            'color': '#ea2845',
            'icon': 'nestjs.png',
            'default_properties': {
                'version': '9.0',
                'architecture': 'Modular',
                'components': 'Controllers, Providers, Modules',
                'decorators': '',
                'dependency_injection': True,
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.RAILS: {
            'name': 'Ruby on Rails',
            'category': ObjectCategory.WEB,
            'color': '#cc0000',
            'icon': 'rails.png',
            'default_properties': {
                'version': '7.0',
                'language': 'Ruby',
                'mvc_framework': True,
                'database': 'SQLite/PostgreSQL',
                'gems': '',
                'migrations': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },

        ObjectType.REACT: {
            'name': 'React',
            'category': ObjectCategory.WEB,
            'color': '#61dafb',
            'icon': 'react.png',
            'default_properties': {
                'version': '18.x',
                'language': 'JavaScript',
                'build_tool': 'Webpack/Vite',
                'state_management': 'Redux/Context',
                'components': '',
                'hooks': '',
                'routing': 'React Router',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.ANGULAR: {
            'name': 'Angular',
            'category': ObjectCategory.WEB,
            'color': '#dd0031',
            'icon': 'angular.png',
            'default_properties': {
                'version': '16',
                'language': 'TypeScript',
                'architecture': 'Component-based',
                'cli': 'Angular CLI',
                'modules': '',
                'services': '',
                'routing': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.VUE: {
            'name': 'Vue.js',
            'category': ObjectCategory.WEB,
            'color': '#4fc08d',
            'icon': 'vue.png',
            'default_properties': {
                'version': '3.x',
                'language': 'JavaScript',
                'composition_api': True,
                'build_tool': 'Vite',
                'components': '',
                'stores': '',
                'router': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },

        ObjectType.WEB_FOLDER: {
            'name': 'Web Folder',
            'category': ObjectCategory.WEB,
            'color': '#6b7280',
            'icon': 'folder.png',
            'default_properties': {
                'path': '',
                'file_count': 0,
                'folder_count': 0,
                'total_size': '',
                'notes': ''
            },
            'allowed_children': [
                ObjectType.WEB_FOLDER, ObjectType.CODE_FILE, ObjectType.CONFIG_FILE,
                ObjectType.WEB_APP, ObjectType.API_ENDPOINT, ObjectType.FILE
            ]
        },
        ObjectType.WEB_APP: {
            'name': 'Web Application',
            'category': ObjectCategory.WEB,
            'color': '#8b5cf6',
            'icon': 'web_app.png',
            'default_properties': {
                'name': '',
                'programming_language': '',
                'framework': '',
                'entry_point': '',
                'dependencies': '',
                'build_commands': '',
                'deployment_target': '',
                'environment_vars': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.CODE_FILE, ObjectType.CONFIG_FILE, ObjectType.WEB_FOLDER]
        },
        
        ObjectType.CODE_FILE: {
            'name': 'Source Code File',
            'category': ObjectCategory.WEB,
            'color': '#f59e0b',
            'icon': 'code_file.png',
            'default_properties': {
                'filename': '',
                'extension': '.py/.js/.java/.rb',
                'language': '',
                'purpose': '',
                'functions': '',
                'classes': '',
                'imports': '',
                'code_content': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.CONFIG_FILE: {
            'name': 'Configuration File',
            'category': ObjectCategory.WEB,
            'color': '#6b7280',
            'icon': 'config_file.png',
            'default_properties': {
                'filename': '',
                'format': 'JSON/YAML/INI/XML',
                'sections': '',
                'parameters': '',
                'environment_specific': '',
                'sensitive_data': '',
                'validation_rules': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.API_ENDPOINT: {
            'name': 'API Endpoint',
            'category': ObjectCategory.WEB,
            'color': '#10b981',
            'icon': 'api_endpoint.png',
            'default_properties': {
                'path': '/api/v1/',
                'method': 'GET/POST/PUT/DELETE',
                'authentication': 'None/JWT/OAuth',
                'parameters': '',
                'response_format': 'JSON/XML',
                'rate_limiting': '',
                'documentation': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.WEB_FOLDER]
        },
        
        ObjectType.OAUTH: {
            'name': 'OAuth 2.0',
            'category': ObjectCategory.WEB,
            'color': '#eb5424',
            'icon': 'oauth.png',
            'default_properties': {
                'version': '2.0',
                'grant_types': 'Authorization Code',
                'providers': 'Google, GitHub, Microsoft',
                'scopes': 'read, write',
                'client_id': '',
                'client_secret': '',
                'redirect_uris': '',
                'token_endpoint': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.JWT: {
            'name': 'JWT Authentication',
            'category': ObjectCategory.WEB,
            'color': '#000000',
            'icon': 'jwt.png',
            'default_properties': {
                'algorithm': 'HS256/RS256',
                'secret_key': '',
                'expiration': '1h',
                'claims': '',
                'issuer': '',
                'audience': '',
                'security': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.SAML: {
            'name': 'SAML Identity Provider',
            'category': ObjectCategory.WEB,
            'color': '#034ea2',
            'icon': 'saml.png',
            'default_properties': {
                'version': '2.0',
                'identity_provider': '',
                'service_provider': '',
                'assertions': '',
                'certificates': '',
                'metadata_url': '',
                'notes': ''
            },
            'allowed_children': []
        },

        # === ORGANIZATION ===
        
        ObjectType.PROJECT: {
            'name': 'Project',
            'category': ObjectCategory.ORGANIZATION,
            'color': '#8b5cf6',
            'icon': '',
            'default_properties': {
                'name': '',
                'description': '',
                'status': 'Active',
                'start_date': '',
                'end_date': '',
                'team_members': '',
                'notes': ''
            },
            'allowed_children': [
        ObjectType.TEAM, ObjectType.USER, 
        ObjectType.WEB_FOLDER, ObjectType.FOLDER,
        ObjectType.WEB_APP, ObjectType.CODE_FILE, ObjectType.CONFIG_FILE
    ]
        },
        
        ObjectType.TEAM: {
            'name': 'Team',
            'category': ObjectCategory.ORGANIZATION,
            'color': '#06b6d4',
            'icon': '',
            'default_properties': {
                'name': '',
                'lead': '',
                'members': '',
                'responsibilities': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.USER]
        },
        
        ObjectType.USER: {
            'name': 'User',
            'category': ObjectCategory.ORGANIZATION,
            'color': '#f97316',
            'icon': '',
            'default_properties': {
                'username': '',
                'role': '',
                'permissions': '',
                'email': '',
                'department': '',
                'notes': ''
            },
            'allowed_children': []
        },
        
        ObjectType.GROUP: {
            'name': 'Group',
            'category': ObjectCategory.ORGANIZATION,
            'color': '#f59e0b',
            'icon': '',
            'default_properties': {
                'name': '',
                'members': '',
                'permissions': '',
                'purpose': '',
                'notes': ''
            },
            'allowed_children': [ObjectType.USER]
        }
    }
    
    @classmethod
    def create_object(cls, obj_type: ObjectType, position: QPointF, name: str = None, 
                     custom_properties: dict = None) -> SandboxObject:
        template = cls.OBJECT_TEMPLATES.get(obj_type, {})
        
        if not name:
            name = template.get('name', 'Unnamed Object')
        
        category = template.get('category', ObjectCategory.NETWORK)
        properties = template.get('default_properties', {}).copy()
        if custom_properties:
            properties.update(custom_properties)
        
        return SandboxObject(
            obj_id=cls.generate_id(),
            obj_type=obj_type,
            category=category,
            position=position,
            name=name,
            properties=properties
        )
    
    @classmethod
    def generate_id(cls) -> str:
        import time
        return f"obj_{int(time.time() * 1000)}"
    
    @classmethod
    def get_object_color(cls, obj_type: ObjectType) -> str:
        return cls.OBJECT_TEMPLATES.get(obj_type, {}).get('color', '#6b7280')
    
    @classmethod
    def get_object_name(cls, obj_type: ObjectType) -> str:
        return cls.OBJECT_TEMPLATES.get(obj_type, {}).get('name', 'Unknown Object')
    
    @classmethod
    def get_object_icon(cls, obj_type: ObjectType) -> str:
        return cls.OBJECT_TEMPLATES.get(obj_type, {}).get('icon', '📦')
    
    @classmethod
    def get_object_category(cls, obj_type: ObjectType) -> ObjectCategory:
        return cls.OBJECT_TEMPLATES.get(obj_type, {}).get('category', ObjectCategory.NETWORK)
    
    @classmethod
    def get_allowed_children(cls, obj_type: ObjectType) -> list:
        return cls.OBJECT_TEMPLATES.get(obj_type, {}).get('allowed_children', [])
    
    @classmethod
    def can_have_children(cls, obj_type: ObjectType) -> bool:
        allowed = cls.get_allowed_children(obj_type)
        return len(allowed) > 0
    
    @classmethod
    def get_objects_by_category(cls, category: ObjectCategory) -> list:
        return [obj_type for obj_type, config in cls.OBJECT_TEMPLATES.items() 
                if config.get('category') == category]
    
    @classmethod
    def get_available_object_types(cls, category: ObjectCategory = None) -> list:
        if category:
            return cls.get_objects_by_category(category)
        else:
            return list(cls.OBJECT_TEMPLATES.keys())
    
    @classmethod
    def get_category_sections(cls, category: ObjectCategory) -> dict:
        sections = {
            ObjectCategory.OPERATING_SYSTEM: {
                "Main Systems": [ObjectType.WINDOWS, ObjectType.LINUX, ObjectType.MACOS],
                "Windows Distributions": [ObjectType.WINDOWS_10, ObjectType.WINDOWS_11],
                "Linux Distributions": [ObjectType.UBUNTU, ObjectType.DEBIAN, ObjectType.ARCH, ObjectType.CENTOS, ObjectType.KALI],
                "Services & Processes": [ObjectType.SERVICE, ObjectType.PROCESS, ObjectType.SCHEDULED_TASK],
                "Paths & Files": [ObjectType.FOLDER, ObjectType.FILE, ObjectType.REGISTRY_KEY, ObjectType.CONFIG_FILE],
                 "System Analysis": [
        ObjectType.SYSTEM_INFO, ObjectType.NETWORK_INTERFACE, 
        ObjectType.OPEN_PORT, ObjectType.RUNNING_SERVICE,
        ObjectType.INSTALLED_SOFTWARE, ObjectType.USER_ACCOUNT,
        ObjectType.SECURITY_POLICY
    ],
            },
            ObjectCategory.NETWORK: {
                "Devices": [ObjectType.COMPUTER, ObjectType.SERVER, ObjectType.ROUTER, ObjectType.SWITCH, 
                           ObjectType.FIREWALL, ObjectType.ACCESS_POINT, ObjectType.MODEM, ObjectType.CONTAINER]
            },
            ObjectCategory.WEB: {
                "Web Servers": [ObjectType.APACHE, ObjectType.NGINX, ObjectType.IIS, ObjectType.TOMCAT],
                "Databases": [ObjectType.MYSQL, ObjectType.POSTGRESQL, ObjectType.MONGODB, ObjectType.REDIS],
                "Backend Frameworks": [ObjectType.DJANGO, ObjectType.FLASK, ObjectType.NODEJS, ObjectType.SPRING, ObjectType.EXPRESS, ObjectType.NESTJS, ObjectType.RAILS],
                "Frontend Frameworks": [ObjectType.REACT, ObjectType.ANGULAR, ObjectType.VUE],
                "Application Components": [ObjectType.WEB_APP, ObjectType.API_ENDPOINT, ObjectType.CODE_FILE, ObjectType.CONFIG_FILE],
                "Authentication": [ObjectType.OAUTH, ObjectType.JWT, ObjectType.SAML]
            },
            ObjectCategory.ORGANIZATION: {
                "Structure": [ObjectType.PROJECT, ObjectType.TEAM, ObjectType.USER, ObjectType.GROUP]
            }
        }
        return sections.get(category, {})