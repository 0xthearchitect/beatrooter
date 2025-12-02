from PyQt6.QtCore import QPointF

class NodeFactory:
    CATEGORY_TEMPLATES = {
        # RED TEAM - Web Application Testing
        'web_pentesting': {
            'web_application': {
                'name': 'Web Application',
                'color': '#ff6b6b',
                'default_data': {
                    'url': 'https://example.com',
                    'technology_stack': '',
                    'authentication_method': '',
                    'endpoints': '',
                    'vulnerabilities_found': 0,
                    'risk_level': 'medium',
                    'notes': ''
                }
            },
            'endpoint': {
                'name': 'Endpoint',
                'color': '#4ecdc4',
                'default_data': {
                    'path': '/api/v1/endpoint',
                    'method': 'GET',
                    'parameters': '',
                    'authentication_required': False,
                    'vulnerable': False,
                    'vulnerability_type': '',
                    'notes': ''
                }
            },
            'vulnerability_finding': {
                'name': 'Vulnerability Finding',
                'color': '#ffa500',
                'default_data': {
                    'type': 'SQL Injection',
                    'severity': 'high',
                    'cvss_score': 0.0,
                    'proof_of_concept': '',
                    'remediation': '',
                    'exploited': False,
                    'notes': ''
                }
            },
            'payload': {
                'name': 'Payload',
                'color': '#6c5ce7',
                'default_data': {
                    'type': 'SQLi',
                    'payload': "' OR '1'='1",
                    'technique': 'Union Based',
                    'successful': False,
                    'output': '',
                    'notes': ''
                }
            }
        },
        
        # RED TEAM - Network Assessment
        'network_pentesting': {
            'network_range': {
                'name': 'Network Range',
                'color': '#45b7d1',
                'default_data': {
                    'cidr': '192.168.1.0/24',
                    'hosts_alive': 0,
                    'open_ports': '',
                    'os_discovery': '',
                    'vulnerable_hosts': 0,
                    'notes': ''
                }
            },
            'port_service': {
                'name': 'Port/Service',
                'color': '#fdcb6e',
                'default_data': {
                    'port': 80,
                    'service': 'http',
                    'version': '',
                    'banner': '',
                    'vulnerabilities': '',
                    'exploitable': False,
                    'notes': ''
                }
            },
            'exploit': {
                'name': 'Exploit',
                'color': '#ff0000',
                'default_data': {
                    'cve': 'CVE-XXXX-XXXX',
                    'service': '',
                    'port': 0,
                    'success_rate': 0.0,
                    'payload': '',
                    'executed': False,
                    'notes': ''
                }
            },
            'lateral_movement': {
                'name': 'Lateral Movement',
                'color': '#00b894',
                'default_data': {
                    'technique': 'Pass the Hash',
                    'source_host': '',
                    'target_host': '',
                    'credentials_used': '',
                    'successful': False,
                    'persistence': False,
                    'notes': ''
                }
            }
        },
        
        # RED TEAM - Social Engineering
        'social_engineering': {
            'target_person': {
                'name': 'Target Person',
                'color': '#dda0dd',
                'default_data': {
                    'name': 'John Doe',
                    'position': '',
                    'department': '',
                    'email': '',
                    'phone': '',
                    'social_media': '',
                    'vulnerability_level': 'medium',
                    'notes': ''
                }
            },
            'phishing_email': {
                'name': 'Phishing Email',
                'color': '#ffeaa7',
                'default_data': {
                    'subject': 'Urgent: Password Reset Required',
                    'sender': 'security@company.com',
                    'targets': '',
                    'click_rate': 0.0,
                    'credentials_captured': 0,
                    'malicious_links': '',
                    'notes': ''
                }
            },
            'credential_harvest': {
                'name': 'Credential Harvest',
                'color': '#fd79a8',
                'default_data': {
                    'technique': 'Fake Login Page',
                    'target_service': '',
                    'credentials_captured': '',
                    'timestamp': '',
                    'user_agent': '',
                    'ip_address': '',
                    'notes': ''
                }
            },
            'physical_access': {
                'name': 'Physical Access',
                'color': '#e17055',
                'default_data': {
                    'location': 'Main Office',
                    'method': 'Tailgating',
                    'devices_accessed': '',
                    'data_captured': '',
                    'time_inside': '',
                    'security_breached': False,
                    'notes': ''
                }
            }
        },

        # BLUE TEAM - Incident Response
        'incident_response': {
            'security_incident': {
                'name': 'Security Incident',
                'color': '#dc2626',
                'default_data': {
                    'incident_id': 'INC-001',
                    'title': 'Unauthorized Access Attempt',
                    'severity': 'high',
                    'status': 'open',
                    'detection_time': '',
                    'affected_assets': '',
                    'incident_type': 'Brute Force',
                    'assigned_analyst': '',
                    'notes': ''
                }
            },
            'incident_timeline': {
                'name': 'Incident Timeline',
                'color': '#ea580c',
                'default_data': {
                    'event_time': '',
                    'event_type': 'Detection',
                    'description': '',
                    'source_ip': '',
                    'destination_ip': '',
                    'user_involved': '',
                    'evidence_collected': '',
                    'notes': ''
                }
            },
            'forensic_artifact': {
                'name': 'Forensic Artifact',
                'color': '#65a30d',
                'default_data': {
                    'artifact_type': 'Memory Dump',
                    'source_host': '',
                    'collection_time': '',
                    'hash_md5': '',
                    'hash_sha256': '',
                    'analysis_status': 'pending',
                    'findings': '',
                    'notes': ''
                }
            },
            'containment_action': {
                'name': 'Containment Action',
                'color': '#0891b2',
                'default_data': {
                    'action_type': 'Network Block',
                    'target': '192.168.1.100',
                    'initiated_by': '',
                    'initiation_time': '',
                    'effectiveness': 'unknown',
                    'business_impact': '',
                    'notes': ''
                }
            }
        },

        # BLUE TEAM - Threat Hunting
        'threat_hunting': {
            'hypothesis': {
                'name': 'Hunting Hypothesis',
                'color': '#7c3aed',
                'default_data': {
                    'hypothesis': 'APT group using PowerShell for lateral movement',
                    'confidence': 'medium',
                    'data_sources': 'Windows Event Logs, Network Traffic',
                    'ttp_reference': 'T1059.001',
                    'status': 'active',
                    'findings': '',
                    'notes': ''
                }
            },
            'ioc': {
                'name': 'Indicator of Compromise',
                'color': '#db2777',
                'default_data': {
                    'ioc_type': 'IP Address',
                    'value': '192.168.1.50',
                    'confidence': 'high',
                    'first_seen': '',
                    'last_seen': '',
                    'source': 'Threat Intel Feed',
                    'context': '',
                    'notes': ''
                }
            },
            'hunting_rule': {
                'name': 'Hunting Rule',
                'color': '#059669',
                'default_data': {
                    'rule_name': 'Suspicious PowerShell Execution',
                    'query': 'CommandLine contains "Invoke-"',
                    'data_source': 'Windows Security Logs',
                    'risk_score': 85,
                    'execution_frequency': 'daily',
                    'notes': ''
                }
            },
            'ttp': {
                'name': 'TTP',
                'color': '#dc2626',
                'default_data': {
                    'mitre_attack_id': 'T1059.001',
                    'technique_name': 'PowerShell',
                    'description': 'Command and Scripting Interpreter',
                    'detection_methods': '',
                    'prevention_controls': '',
                    'examples': '',
                    'notes': ''
                }
            }
        },

        # BLUE TEAM - Malware Analysis
        'malware_analysis': {
            'malware_sample': {
                'name': 'Malware Sample',
                'color': '#991b1b',
                'default_data': {
                    'sample_name': 'trojan.exe',
                    'hash_md5': '',
                    'hash_sha256': '',
                    'file_size': 0,
                    'file_type': 'PE32',
                    'submission_source': 'EDR Alert',
                    'analysis_status': 'queued',
                    'notes': ''
                }
            },
            'analysis_environment': {
                'name': 'Analysis Environment',
                'color': '#7c3aed',
                'default_data': {
                    'vm_name': 'Windows 10 Analysis',
                    'os_version': 'Windows 10 21H2',
                    'tools_installed': 'Wireshark, Process Monitor',
                    'network_setup': 'NAT with Internet',
                    'isolation_level': 'sandbox',
                    'notes': ''
                }
            },
            'behavior_analysis': {
                'name': 'Behavior Analysis',
                'color': '#0891b2',
                'default_data': {
                    'process_activity': '',
                    'network_connections': '',
                    'file_system_changes': '',
                    'registry_modifications': '',
                    'persistence_mechanism': '',
                    'anti_analysis_techniques': '',
                    'notes': ''
                }
            },
            'yara_rule': {
                'name': 'YARA Rule',
                'color': '#65a30d',
                'default_data': {
                    'rule_name': 'Trojan_Generic_1',
                    'author': 'Analyst Name',
                    'reference': '',
                    'strings': '',
                    'condition': '',
                    'false_positives': 0,
                    'notes': ''
                }
            }
        },

        # BLUE TEAM - SIEM Investigation
        'siem_investigation': {
            'security_alert': {
                'name': 'Security Alert',
                'color': '#dc2626',
                'default_data': {
                    'alert_id': 'ALERT-001',
                    'alert_name': 'Multiple Failed Logins',
                    'severity': 'high',
                    'siem_source': 'Splunk',
                    'trigger_time': '',
                    'source_ip': '',
                    'destination_ip': '',
                    'notes': ''
                }
            },
            'correlation_rule': {
                'name': 'Correlation Rule',
                'color': '#7c3aed',
                'default_data': {
                    'rule_name': 'Brute Force Detection',
                    'description': 'Detect multiple failed authentication attempts',
                    'search_query': '',
                    'threshold': 5,
                    'time_window': '5m',
                    'risk_score': 80,
                    'notes': ''
                }
            },
            'log_source': {
                'name': 'Log Source',
                'color': '#0891b2',
                'default_data': {
                    'source_type': 'Windows Security',
                    'host': 'DC01.company.com',
                    'log_level': 'Information',
                    'ingestion_status': 'active',
                    'retention_days': 90,
                    'parsing_errors': 0,
                    'notes': ''
                }
            },
            'investigation_note': {
                'name': 'Investigation Note',
                'color': '#65a30d',
                'default_data': {
                    'analyst': '',
                    'timestamp': '',
                    'findings': '',
                    'next_steps': '',
                    'confidence_level': 'medium',
                    'escalation_required': False,
                    'notes': ''
                }
            }
        },

        # SOC TEAM - Alert Triage
        'alert_triage': {
            'ticket': {
                'name': 'Incident Ticket',
                'color': '#dc2626',
                'default_data': {
                    'ticket_id': 'TKT-001',
                    'priority': 'medium',
                    'status': 'new',
                    'assigned_analyst': '',
                    'sla_deadline': '',
                    'customer_impact': 'low',
                    'category': 'Malware',
                    'notes': ''
                }
            },
            'triage_decision': {
                'name': 'Triage Decision',
                'color': '#ea580c',
                'default_data': {
                    'decision': 'Escalate to L2',
                    'rationale': 'Multiple IOCs confirmed',
                    'confidence': 'high',
                    'false_positive': False,
                    'time_spent': '15m',
                    'next_step': 'Deep investigation',
                    'notes': ''
                }
            },
            'escalation': {
                'name': 'Escalation',
                'color': '#0891b2',
                'default_data': {
                    'from_tier': 'L1',
                    'to_tier': 'L2',
                    'reason': 'Advanced analysis required',
                    'escalation_time': '',
                    'additional_context': '',
                    'urgency': 'high',
                    'notes': ''
                }
            },
            'sla_check': {
                'name': 'SLA Check',
                'color': '#65a30d',
                'default_data': {
                    'sla_type': 'Response Time',
                    'target_time': '30m',
                    'actual_time': '25m',
                    'status': 'met',
                    'violation_reason': '',
                    'notes': ''
                }
            }
        },

        # SOC TEAM - Correlation Analysis
        'correlation_analysis': {
            'correlated_event': {
                'name': 'Correlated Event',
                'color': '#7c3aed',
                'default_data': {
                    'event_group': 'Lateral Movement Attempt',
                    'confidence_score': 85,
                    'time_range': '10 minutes',
                    'involved_hosts': 3,
                    'attack_phase': 'Execution',
                    'mitre_techniques': 'T1021, T1059',
                    'notes': ''
                }
            },
            'attack_chain': {
                'name': 'Attack Chain',
                'color': '#db2777',
                'default_data': {
                    'initial_access': 'Phishing Email',
                    'execution': 'PowerShell Script',
                    'persistence': 'Scheduled Task',
                    'lateral_movement': 'RDP',
                    'impact': 'Data Exfiltration',
                    'confidence': 'high',
                    'notes': ''
                }
            },
            'context_enrichment': {
                'name': 'Context Enrichment',
                'color': '#059669',
                'default_data': {
                    'enrichment_source': 'Threat Intel',
                    'data_type': 'IP Reputation',
                    'confidence': 'high',
                    'relevance': 'direct',
                    'additional_iocs': '',
                    'notes': ''
                }
            },
            'pattern_analysis': {
                'name': 'Pattern Analysis',
                'color': '#dc2626',
                'default_data': {
                    'pattern_type': 'Temporal',
                    'frequency': 'Every 2 hours',
                    'duration': '3 days',
                    'affected_assets': 'Domain Controllers',
                    'hypothesis': 'Scheduled data exfiltration',
                    'notes': ''
                }
            }
        },

        # SOC TEAM - Compliance Monitoring
        'compliance_monitoring': {
            'compliance_requirement': {
                'name': 'Compliance Requirement',
                'color': '#0891b2',
                'default_data': {
                    'standard': 'PCI DSS',
                    'requirement_id': 'PCI DSS 3.2.1',
                    'description': 'Encrypt transmission of cardholder data',
                    'priority': 'high',
                    'status': 'compliant',
                    'last_audit': '',
                    'notes': ''
                }
            },
            'control_gap': {
                'name': 'Control Gap',
                'color': '#ea580c',
                'default_data': {
                    'gap_description': 'Missing encryption for backup data',
                    'risk_level': 'medium',
                    'affected_systems': 'Backup Servers',
                    'remediation_deadline': '',
                    'responsible_team': 'Infrastructure',
                    'status': 'open',
                    'notes': ''
                }
            },
            'audit_finding': {
                'name': 'Audit Finding',
                'color': '#dc2626',
                'default_data': {
                    'finding_id': 'AUDIT-001',
                    'severity': 'medium',
                    'auditor': 'External Auditor',
                    'audit_date': '',
                    'evidence': '',
                    'recommendation': '',
                    'notes': ''
                }
            },
            'remediation_plan': {
                'name': 'Remediation Plan',
                'color': '#65a30d',
                'default_data': {
                    'plan_name': 'Encryption Implementation',
                    'owner': 'Security Team',
                    'start_date': '',
                    'completion_date': '',
                    'progress': '0%',
                    'risks': 'Potential performance impact',
                    'notes': ''
                }
            }
        }
    }

    NODE_TYPES = {
        'ip': {
            'name': 'IP Address',
            'color': '#ff6b6b',
            'default_data': {
                'address': '192.168.1.1',
                'geo_location': '',
                'threat_level': 'unknown',
                'os': '',
                'services': '',
                'ports': '',
                'notes': ''
            }
        },
        'domain': {
            'name': 'Domain',
            'color': '#4ecdc4',
            'default_data': {
                'name': 'example.com',
                'register': '',
                'creation_date': '',
                'name_servers': '',
                'subnames': '',
                'notes': ''
            }
        },
        'user': {
            'name': 'User',
            'color': '#45b7d1',
            'default_data': {
                'username': 'john_doe',
                'email': '',
                'role': '',
                'department': '',
                'phone': '',
                'last_login': '',
                'notes': ''
            }
        },
        'credential': {
            'name': 'Credential',
            'color': '#fdcb6e',
            'default_data': {
                'username': '',
                'domain': '',
                'credential_type': 'password',
                'password': '',
                'password_hash': '',
                'source': '',
                'compromised': False,
                'privilege_level': '',
                'notes': ''
            }
        },
        'attack': {
            'name': 'Attack',
            'color': "#ff0000",
            'default_data': {
                'type': '',
                'technique': '',
                'timestamp': '',
                'severity': 'high',
                'source': '',
                'target': '',
                'successful': False,
                'notes': ''
            }
        },
        'vulnerability': {
            'name': 'Vulnerability',
            'color': '#ffa500',
            'default_data': {
                'cve': 'CVE-XXXX-XXXX',
                'name': '',
                'severity': 'medium',
                'description': '',
                'exploited': False,
                'affected_hosts': '',
                'impact': '',
                'notes': ''
            }
        },
        'host': {
            'name': 'Host',
            'color': '#96ceb4',
            'default_data': {
                'hostname': 'server-01',
                'ip_address': '',
                'os': '',
                'domain': '',
                'role': '',
                'services': '',
                'notes': ''
            }
        },
        'note': {
            'name': 'Note',
            'color': '#ffeaa7',
            'default_data': {
                'title': '',
                'content': 'Investigation note...',
                'category': '',
                'priority': 'medium',
                'notes': ''
            }
        },
        'screenshot': {
            'name': 'Screenshot',
            'color': '#dda0dd',
            'default_data': {
                'filename': '',
                'file_path': '',
                'image_data': '',
                'timestamp': '',
                'description': '',
                'tags': '',
                'file_size': '',
                'dimensions': '',
                'format': '',
                'metadata': {},
                'notes': ''
            }
        },
        'command': {
            'name': 'Command',
            'color': '#6c5ce7',
            'default_data': {
                'command': 'whoami',
                'output': '',
                'timestamp': '',
                'executed_on': '',
                'privilege_level': '',
                'exit_code': 0,
                'notes': ''
            }
        },
        'script': {
            'name': 'Script',
            'color': '#00b894',
            'default_data': {
                'filename': 'script.sh',
                'file_path': '',
                'language': 'bash',
                'content': '',
                'purpose': '',
                'execution_result': '',
                'parameters': '',
                'timestamp': '',
                'notes': ''
            }
        }
    }

    @classmethod
    def create_node_data(cls, node_type: str, custom_data: dict = None, category: str = None) -> dict:
        if category and category in cls.CATEGORY_TEMPLATES:
            if node_type in cls.CATEGORY_TEMPLATES[category]:
                default_data = cls.CATEGORY_TEMPLATES[category][node_type]['default_data'].copy()
                if custom_data:
                    default_data.update(custom_data)
                return default_data
        
        if node_type in cls.NODE_TYPES:
            default_data = cls.NODE_TYPES[node_type].get('default_data', {}).copy()
            if custom_data:
                default_data.update(custom_data)
            return default_data
        
        return {'notes': ''}

    @classmethod
    def get_node_color(cls, node_type: str, category: str = None) -> str:
        if category and category in cls.CATEGORY_TEMPLATES:
            if node_type in cls.CATEGORY_TEMPLATES[category]:
                return cls.CATEGORY_TEMPLATES[category][node_type]['color']
        
        return cls.NODE_TYPES.get(node_type, {}).get('color', '#ffffff')

    @classmethod
    def get_node_name(cls, node_type: str, category: str = None) -> str:
        if category and category in cls.CATEGORY_TEMPLATES:
            if node_type in cls.CATEGORY_TEMPLATES[category]:
                return cls.CATEGORY_TEMPLATES[category][node_type]['name']
        
        return cls.NODE_TYPES.get(node_type, {}).get('name', 'Unknown')

    @classmethod
    def get_available_node_types(cls, category: str = None) -> list:
        """Retorna os tipos de nodes disponíveis para uma categoria"""
        if category and category in cls.CATEGORY_TEMPLATES:
            return list(cls.CATEGORY_TEMPLATES[category].keys())
        
        return list(cls.NODE_TYPES.keys())