import copy
import re

class NodeFactory:
    CATEGORY_TEMPLATES = {
        # RED TEAM - Web Application Testing
        'web_application_testing': {
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
        'networking_assessment': {
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
        'compliance_analysis': {
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
        },

        # RED TEAM - Reverse Engineering
        'reverse_engineering': {
            'binary_sample': {
                'name': 'Binary Sample',
                'color': '#b91c1c',
                'default_data': {
                    'file_name': 'sample.bin',
                    'sha256': '',
                    'architecture': 'x64',
                    'compiler_hint': '',
                    'packer_detected': False,
                    'source': '',
                    'notes': ''
                }
            },
            'function_profile': {
                'name': 'Function Profile',
                'color': '#be123c',
                'default_data': {
                    'function_name': 'sub_401000',
                    'address': '0x401000',
                    'calling_convention': 'cdecl',
                    'purpose': '',
                    'risk_level': 'medium',
                    'notes': ''
                }
            },
            'dynamic_trace': {
                'name': 'Dynamic Trace',
                'color': '#c2410c',
                'default_data': {
                    'debugger': 'x64dbg',
                    'breakpoints': '',
                    'api_calls': '',
                    'anti_debug': False,
                    'analysis_status': 'in_progress',
                    'notes': ''
                }
            },
            'patch_recommendation': {
                'name': 'Patch Recommendation',
                'color': '#0f766e',
                'default_data': {
                    'objective': 'Disable malware C2 callback',
                    'patch_type': 'binary_patch',
                    'target_offset': '',
                    'validation_status': 'draft',
                    'owner': '',
                    'notes': ''
                }
            }
        },

        # RED TEAM - Mobile Hacking
        'mobile_hacking': {
            'mobile_application': {
                'name': 'Mobile Application',
                'color': '#0369a1',
                'default_data': {
                    'app_name': 'Example Mobile App',
                    'package_id': 'com.example.app',
                    'platform': 'android',
                    'version': '1.0.0',
                    'build_type': 'release',
                    'obfuscation_level': 'unknown',
                    'notes': ''
                }
            },
            'mobile_endpoint': {
                'name': 'Mobile Endpoint',
                'color': '#0284c7',
                'default_data': {
                    'endpoint_url': 'https://api.example.com/v1',
                    'auth_type': 'bearer_token',
                    'certificate_pinning': False,
                    'method': 'GET',
                    'vulnerable': False,
                    'notes': ''
                }
            },
            'runtime_hook': {
                'name': 'Runtime Hook',
                'color': '#0ea5e9',
                'default_data': {
                    'framework': 'frida',
                    'target_method': '',
                    'hook_script': '',
                    'result': '',
                    'bypass_successful': False,
                    'notes': ''
                }
            },
            'mobile_finding': {
                'name': 'Mobile Finding',
                'color': '#7c3aed',
                'default_data': {
                    'finding_type': 'insecure_storage',
                    'owasp_mastg': 'MSTG-STORAGE-2',
                    'severity': 'medium',
                    'evidence_type': 'artifact',
                    'remediation': '',
                    'notes': ''
                }
            }
        },

        # RED TEAM - Infrastructure
        'infra': {
            'infra_asset': {
                'name': 'Infrastructure Asset',
                'color': '#1d4ed8',
                'default_data': {
                    'asset_name': 'prod-app-vm-01',
                    'asset_type': 'server',
                    'provider': 'on_prem',
                    'region': '',
                    'environment': 'prod',
                    'owner': '',
                    'notes': ''
                }
            },
            'configuration_item': {
                'name': 'Configuration Item',
                'color': '#2563eb',
                'default_data': {
                    'config_type': 'security_group',
                    'baseline': '',
                    'current_value': '',
                    'control_state': 'unknown',
                    'compliant': False,
                    'notes': ''
                }
            },
            'secret_exposure': {
                'name': 'Secret Exposure',
                'color': '#dc2626',
                'default_data': {
                    'secret_type': 'api_key',
                    'location': '',
                    'rotation_status': 'unknown',
                    'publicly_exposed': False,
                    'severity': 'high',
                    'notes': ''
                }
            },
            'hardening_task': {
                'name': 'Hardening Task',
                'color': '#0f766e',
                'default_data': {
                    'benchmark': 'CIS',
                    'task': '',
                    'priority': 'medium',
                    'status': 'draft',
                    'owner': '',
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

    CATEGORY_ALIASES = {
        "web_pentesting": "web_application_testing",
        "web_application_testing": "web_application_testing",
        "network_pentesting": "networking_assessment",
        "network_assessment": "networking_assessment",
        "networking_accessment": "networking_assessment",
        "networking_assessment": "networking_assessment",
        "compliance_monitoring": "compliance_analysis",
        "compliance_analysis": "compliance_analysis",
        "correlatiom_analysis": "correlation_analysis",
        "correlation_analysis": "correlation_analysis",
    }

    CATEGORY_CATALOG = {
        "incident_response": {
            "name": "Incident Response",
            "description": "Investigate security incidents and breaches.",
            "color": "#2563eb",
            "icon": "IR",
            "project_types": ["blueteam"],
        },
        "threat_hunting": {
            "name": "Threat Hunting",
            "description": "Proactively hunt adversary activity and uncover IOCs.",
            "color": "#1d4ed8",
            "icon": "TH",
            "project_types": ["blueteam", "soc_team"],
        },
        "compliance_analysis": {
            "name": "Compliance Analysis",
            "description": "Assess controls, gaps, and remediation for regulatory frameworks.",
            "color": "#0f766e",
            "icon": "CA",
            "project_types": ["blueteam", "soc_team"],
        },
        "siem_investigation": {
            "name": "SIEM Investigation",
            "description": "Analyze alerts, rules, and log telemetry in SIEM workflows.",
            "color": "#3730a3",
            "icon": "SI",
            "project_types": ["blueteam", "soc_team"],
        },
        "malware_analysis": {
            "name": "Malware Analysis",
            "description": "Perform static/dynamic analysis and build detections.",
            "color": "#4338ca",
            "icon": "MA",
            "project_types": ["blueteam"],
        },
        "correlation_analysis": {
            "name": "Correlation Analysis",
            "description": "Correlate multi-source events into attack narratives.",
            "color": "#6d28d9",
            "icon": "CR",
            "project_types": ["blueteam", "soc_team"],
        },
        "alert_triage": {
            "name": "Alert Triage",
            "description": "Prioritize alerts, reduce noise, and escalate accurately.",
            "color": "#7c3aed",
            "icon": "AT",
            "project_types": ["blueteam", "soc_team"],
        },
        "web_application_testing": {
            "name": "Web Application Testing",
            "description": "Assess web applications for exploitable vulnerabilities.",
            "color": "#dc2626",
            "icon": "WA",
            "project_types": ["redteam"],
        },
        "networking_assessment": {
            "name": "Networking Assessment",
            "description": "Evaluate network attack surface, exposure, and controls.",
            "color": "#b91c1c",
            "icon": "NA",
            "project_types": ["redteam"],
        },
        "social_engineering": {
            "name": "Social Engineering",
            "description": "Test human factors and organizational resilience.",
            "color": "#991b1b",
            "icon": "SE",
            "project_types": ["redteam"],
        },
        "reverse_engineering": {
            "name": "Reverse Engineering",
            "description": "Reverse binaries and document behavior and mitigations.",
            "color": "#be123c",
            "icon": "RE",
            "project_types": ["redteam"],
        },
        "mobile_hacking": {
            "name": "Mobile Hacking",
            "description": "Assess iOS/Android applications and runtime protections.",
            "color": "#0284c7",
            "icon": "MH",
            "project_types": ["redteam"],
        },
        "infra": {
            "name": "Infra",
            "description": "Review infrastructure assets, misconfigurations, and hardening.",
            "color": "#1d4ed8",
            "icon": "IF",
            "project_types": ["redteam"],
        },
    }

    CUSTOM_CATEGORY = "custom_nodes"
    DEFAULT_CUSTOM_COLOR = "#7cb1ff"

    # Base taxonomy derived from the report provided by the user.
    BASE_TAXONOMY = {
        "status": ["draft", "triage", "validated", "remediating", "accepted_risk", "closed"],
        "severity": ["info", "low", "medium", "high", "critical"],
        "confidence": ["low", "medium", "high"],
        "environment": ["lab", "dev", "test", "staging", "prod"],
        "exposure": ["internal", "external", "partner", "public"],
        "data_classification": ["public", "internal", "confidential", "restricted"],
        "control_state": ["absent", "partial", "effective", "unknown"],
        "evidence_type": ["note", "screenshot", "log", "config", "interview", "ticket", "artifact", "policy"],
    }

    CORE_NODE_FIELDS = {
        "title": "",
        "summary": "",
        "owner": "",
        "asset_ref": "",
        "tags": "",
        "status": "draft",
        "severity": "info",
        "confidence": "medium",
        "environment": "test",
        "exposure": "internal",
        "data_classification": "internal",
    }
    CORE_FIELD_SETTINGS = {field_name: True for field_name in CORE_NODE_FIELDS}
    PREDEFINED_NODE_TEMPLATE_OVERRIDES = {}

    FIELD_OPTION_SETS = {
        "status": BASE_TAXONOMY["status"],
        "severity": BASE_TAXONOMY["severity"],
        "risk_level": BASE_TAXONOMY["severity"],
        "confidence": BASE_TAXONOMY["confidence"],
        "confidence_level": BASE_TAXONOMY["confidence"],
        "priority": ["low", "medium", "high", "critical", "urgent"],
        "environment": BASE_TAXONOMY["environment"],
        "exposure": BASE_TAXONOMY["exposure"],
        "data_classification": BASE_TAXONOMY["data_classification"],
        "state": BASE_TAXONOMY["control_state"],
        "control_state": BASE_TAXONOMY["control_state"],
        "evidence_type": BASE_TAXONOMY["evidence_type"],
        "analysis_status": ["queued", "pending", "in_progress", "completed", "failed"],
        "incident_type": ["malware", "unauthorized_access", "data_breach", "ddos", "phishing", "other"],
        "action_type": ["network_block", "process_termination", "account_disable", "isolate_host", "other"],
        "technique": ["sqli", "xss", "rce", "phishing", "brute_force", "lateral_movement", "other"],
        "ioc_type": ["ip_address", "domain", "hash", "url", "email", "mutex", "other"],
        "privilege_level": ["user", "admin", "root", "system", "unknown"],
        "language": ["bash", "python", "powershell", "javascript", "batch", "other"],
        "credential_type": ["password", "hash", "token", "certificate", "api_key"],
        "platform": ["android", "ios", "cross_platform", "backend"],
        "asset_type": ["server", "container", "workstation", "database", "network_device", "cloud_service", "saas"],
        "provider": ["on_prem", "aws", "azure", "gcp", "hybrid", "other"],
        "rotation_status": ["unknown", "stale", "rotated", "revoked"],
        "validation_status": ["draft", "validated", "rejected", "implemented"],
        "patch_type": ["binary_patch", "signature_update", "rule_update", "configuration_change"],
        "module": ["workspace", "subghz", "badusb", "infrared", "wifi", "logs", "general"],
        "script_type": [
            "automation",
            "reconnaissance",
            "payload_download",
            "credential_access",
            "persistence",
            "exfiltration",
            "destructive",
            "unknown",
        ],
        "target_os": ["windows", "linux", "macos", "android", "ios", "mixed", "unknown"],
        "target_device_type": [
            "tv",
            "air_conditioner",
            "projector",
            "audio_system",
            "camera",
            "garage_door",
            "alarm_system",
            "iot_sensor",
            "general_consumer_ir",
            "unknown",
        ],
        "artifact_kind": ["capture", "scan_results", "attack_log", "handshake_dump", "script", "unknown"],
        "attack_result": ["success", "failed", "partial", "unknown"],
        "protocol_family": ["subghz", "infrared", "wifi", "rf", "unknown"],
    }

    DEFAULT_NODE_SYMBOLS = {
        "user": "[USER]",
        "ip": "[IP]",
        "domain": "[DOMAIN]",
        "credential": "[PASS]",
        "attack": "[ATTACK]",
        "vulnerability": "[VULN]",
        "host": "[HOST]",
        "note": "[NOTE]",
        "screenshot": "[IMG]",
        "command": "[CMD]",
        "script": "[SCRIPT]",
        "web_application": "[WEB]",
        "endpoint": "[ENDPT]",
        "vulnerability_finding": "[FIND]",
        "payload": "[PAYLD]",
        "network_range": "[NET]",
        "port_service": "[PORT]",
        "exploit": "[EXPL]",
        "lateral_movement": "[MOVE]",
        "target_person": "[TARGET]",
        "phishing_email": "[EMAIL]",
        "credential_harvest": "[HARV]",
        "physical_access": "[PHYS]",
        "security_incident": "[INCIDENT]",
        "incident_timeline": "[TIMELINE]",
        "forensic_artifact": "[ARTIFACT]",
        "containment_action": "[CONTAIN]",
        "hypothesis": "[HYPOTH]",
        "ioc": "[IOC]",
        "hunting_rule": "[RULE]",
        "ttp": "[TTP]",
        "malware_sample": "[MALWARE]",
        "analysis_environment": "[ENV]",
        "behavior_analysis": "[BEHAV]",
        "yara_rule": "[YARA]",
        "security_alert": "[ALERT]",
        "correlation_rule": "[CORR]",
        "log_source": "[LOG]",
        "investigation_note": "[INVEST]",
        "ticket": "[TICKET]",
        "triage_decision": "[TRIAGE]",
        "escalation": "[ESCAL]",
        "sla_check": "[SLA]",
        "correlated_event": "[CORREL]",
        "attack_chain": "[CHAIN]",
        "context_enrichment": "[ENRICH]",
        "pattern_analysis": "[PATTERN]",
        "compliance_requirement": "[REQ]",
        "control_gap": "[GAP]",
        "audit_finding": "[AUDIT]",
        "remediation_plan": "[PLAN]",
        "binary_sample": "[BIN]",
        "function_profile": "[FUNC]",
        "dynamic_trace": "[TRACE]",
        "patch_recommendation": "[PATCH]",
        "mobile_application": "[MOBAPP]",
        "mobile_endpoint": "[MOBAPI]",
        "runtime_hook": "[HOOK]",
        "mobile_finding": "[MOBF]",
        "infra_asset": "[INFRA]",
        "configuration_item": "[CFG]",
        "secret_exposure": "[SECRET]",
        "hardening_task": "[HARDEN]",
    }

    CUSTOM_NODE_TEMPLATES = {}

    @classmethod
    def _sanitize_node_type(cls, value: str) -> str:
        slug = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
        slug = re.sub(r"_+", "_", slug).strip("_")
        return slug

    @classmethod
    def normalize_category(cls, category: str = None):
        if not category:
            return category
        normalized = cls._sanitize_node_type(category)
        return cls.CATEGORY_ALIASES.get(normalized, normalized)

    @classmethod
    def get_category_display_name(cls, category: str) -> str:
        normalized = cls.normalize_category(category)
        if normalized == cls.CUSTOM_CATEGORY:
            return "Custom Nodes"
        if normalized in cls.CATEGORY_CATALOG:
            return cls.CATEGORY_CATALOG[normalized].get("name", normalized.replace("_", " ").title())
        return (normalized or "general").replace("_", " ").title()

    @classmethod
    def get_project_categories(cls, project_type: str = None) -> dict:
        selected_project = cls._sanitize_node_type(project_type) if project_type else None
        categories = {}
        for category, metadata in cls.CATEGORY_CATALOG.items():
            if category not in cls.CATEGORY_TEMPLATES:
                continue
            allowed = metadata.get("project_types", [])
            if selected_project and allowed and selected_project not in allowed:
                continue
            categories[category] = copy.deepcopy(metadata)
        return categories

    @classmethod
    def _normalize_color(cls, color: str) -> str:
        value = (color or "").strip()
        if not value:
            return cls.DEFAULT_CUSTOM_COLOR
        if not value.startswith("#"):
            value = f"#{value}"
        if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            return value.lower()
        return cls.DEFAULT_CUSTOM_COLOR

    @classmethod
    def _default_symbol_for_name(cls, name: str) -> str:
        letters = "".join(ch for ch in (name or "").upper() if ch.isalnum())
        if not letters:
            return "[NODE]"
        return f"[{letters[:5]}]"

    @classmethod
    def _is_reserved_node_type(cls, node_type: str) -> bool:
        if node_type in cls.NODE_TYPES:
            return True
        for templates in cls.CATEGORY_TEMPLATES.values():
            if node_type in templates:
                return True
        return False

    @classmethod
    def _is_predefined_node_type(cls, node_type: str) -> bool:
        if node_type in cls.NODE_TYPES:
            return True
        for templates in cls.CATEGORY_TEMPLATES.values():
            if node_type in templates:
                return True
        return False

    @classmethod
    def _resolve_template(cls, node_type: str, category: str = None):
        normalized_category = cls.normalize_category(category)
        if (
            normalized_category
            and normalized_category in cls.CATEGORY_TEMPLATES
            and node_type in cls.CATEGORY_TEMPLATES[normalized_category]
        ):
            return cls.CATEGORY_TEMPLATES[normalized_category][node_type]
        if node_type in cls.CUSTOM_NODE_TEMPLATES:
            return cls.CUSTOM_NODE_TEMPLATES[node_type]
        if node_type in cls.NODE_TYPES:
            return cls.NODE_TYPES[node_type]
        for templates in cls.CATEGORY_TEMPLATES.values():
            if node_type in templates:
                return templates[node_type]
        return None

    @classmethod
    def get_core_field_schema(cls) -> dict:
        return copy.deepcopy(cls.CORE_NODE_FIELDS)

    @classmethod
    def get_core_field_settings(cls) -> dict:
        settings = {field_name: True for field_name in cls.CORE_NODE_FIELDS}
        settings.update({field_name: bool(enabled) for field_name, enabled in cls.CORE_FIELD_SETTINGS.items()})
        return settings

    @classmethod
    def set_core_field_settings(cls, settings: dict):
        baseline = {field_name: True for field_name in cls.CORE_NODE_FIELDS}
        if isinstance(settings, dict):
            for field_name in baseline:
                if field_name in settings:
                    baseline[field_name] = bool(settings[field_name])
        cls.CORE_FIELD_SETTINGS = baseline

    @classmethod
    def reset_core_field_settings(cls):
        cls.CORE_FIELD_SETTINGS = {field_name: True for field_name in cls.CORE_NODE_FIELDS}

    @classmethod
    def list_predefined_node_types(cls) -> list:
        node_types = set(cls.NODE_TYPES.keys())
        for templates in cls.CATEGORY_TEMPLATES.values():
            node_types.update(templates.keys())
        return sorted(node_types, key=lambda node_type: cls.get_node_name(node_type).lower())

    @classmethod
    def get_predefined_node_template_override(cls, node_type: str) -> dict:
        override = cls.PREDEFINED_NODE_TEMPLATE_OVERRIDES.get(node_type, {})
        added_fields = override.get("added_fields", {})
        removed_fields = override.get("removed_fields", [])
        return {
            "added_fields": copy.deepcopy(added_fields) if isinstance(added_fields, dict) else {},
            "removed_fields": list(removed_fields) if isinstance(removed_fields, list) else [],
        }

    @classmethod
    def set_predefined_node_template_override(cls, node_type: str, added_fields: dict = None, removed_fields: list = None):
        if not cls._is_predefined_node_type(node_type):
            raise ValueError(f"'{node_type}' is not a predefined node type")

        clean_added_fields = {}
        if isinstance(added_fields, dict):
            for raw_key, raw_value in added_fields.items():
                clean_key = cls._sanitize_node_type(raw_key)
                if not clean_key or clean_key == "notes":
                    continue
                clean_added_fields[clean_key] = copy.deepcopy(raw_value)

        clean_removed_fields = []
        if isinstance(removed_fields, list):
            for raw_key in removed_fields:
                clean_key = cls._sanitize_node_type(raw_key)
                if not clean_key or clean_key == "notes":
                    continue
                if clean_key not in clean_removed_fields:
                    clean_removed_fields.append(clean_key)

        if not clean_added_fields and not clean_removed_fields:
            cls.PREDEFINED_NODE_TEMPLATE_OVERRIDES.pop(node_type, None)
            return

        cls.PREDEFINED_NODE_TEMPLATE_OVERRIDES[node_type] = {
            "added_fields": clean_added_fields,
            "removed_fields": clean_removed_fields,
        }

    @classmethod
    def clear_predefined_node_template_override(cls, node_type: str):
        cls.PREDEFINED_NODE_TEMPLATE_OVERRIDES.pop(node_type, None)

    @classmethod
    def export_node_template_settings(cls) -> dict:
        return {
            "core_field_settings": cls.get_core_field_settings(),
            "predefined_node_overrides": copy.deepcopy(cls.PREDEFINED_NODE_TEMPLATE_OVERRIDES),
        }

    @classmethod
    def reset_node_template_settings(cls):
        cls.reset_core_field_settings()
        cls.PREDEFINED_NODE_TEMPLATE_OVERRIDES = {}

    @classmethod
    def load_node_template_settings(cls, settings_payload: dict):
        cls.reset_node_template_settings()
        if not isinstance(settings_payload, dict):
            return

        cls.set_core_field_settings(settings_payload.get("core_field_settings", {}))
        overrides = settings_payload.get("predefined_node_overrides", {})
        if not isinstance(overrides, dict):
            return

        for node_type, payload in overrides.items():
            if not isinstance(payload, dict):
                continue
            try:
                cls.set_predefined_node_template_override(
                    node_type=node_type,
                    added_fields=payload.get("added_fields", {}),
                    removed_fields=payload.get("removed_fields", []),
                )
            except ValueError:
                continue

    @classmethod
    def get_field_options(cls, field_key: str) -> list:
        normalized = cls._sanitize_node_type(field_key or "")
        return list(cls.FIELD_OPTION_SETS.get(normalized, []))

    @classmethod
    def register_custom_node_template(
        cls,
        name: str,
        node_type: str = None,
        color: str = None,
        default_data: dict = None,
        symbol: str = None,
        overwrite: bool = False,
    ) -> str:
        display_name = (name or "").strip()
        if not display_name:
            raise ValueError("Node name cannot be empty")

        slug = cls._sanitize_node_type(node_type or display_name)
        if not slug:
            raise ValueError("Node type could not be generated")

        if cls._is_reserved_node_type(slug):
            raise ValueError(f"'{slug}' is a reserved node type")
        if slug in cls.CUSTOM_NODE_TEMPLATES and not overwrite:
            raise ValueError(f"Custom node type '{slug}' already exists")

        payload = copy.deepcopy(default_data or {})
        payload.setdefault("notes", "")

        template = {
            "name": display_name,
            "color": cls._normalize_color(color),
            "symbol": (symbol or "").strip() or cls._default_symbol_for_name(display_name),
            "category": cls.CUSTOM_CATEGORY,
            "custom": True,
            "default_data": payload,
        }
        cls.CUSTOM_NODE_TEMPLATES[slug] = template
        return slug

    @classmethod
    def remove_custom_node_template(cls, node_type: str):
        cls.CUSTOM_NODE_TEMPLATES.pop(node_type, None)

    @classmethod
    def list_custom_node_types(cls) -> list:
        return sorted(cls.CUSTOM_NODE_TEMPLATES.keys(), key=lambda item: cls.get_node_name(item).lower())

    @classmethod
    def export_custom_node_templates(cls) -> dict:
        return copy.deepcopy(cls.CUSTOM_NODE_TEMPLATES)

    @classmethod
    def reset_custom_node_templates(cls):
        cls.CUSTOM_NODE_TEMPLATES = {}

    @classmethod
    def load_custom_node_templates(cls, templates: dict):
        cls.reset_custom_node_templates()
        if not isinstance(templates, dict):
            return

        for node_type, template in templates.items():
            if not isinstance(template, dict):
                continue
            name = template.get("name", node_type.replace("_", " ").title())
            color = template.get("color", cls.DEFAULT_CUSTOM_COLOR)
            symbol = template.get("symbol", "")
            default_data = template.get("default_data", {})
            try:
                cls.register_custom_node_template(
                    name=name,
                    node_type=node_type,
                    color=color,
                    default_data=default_data,
                    symbol=symbol,
                    overwrite=True,
                )
            except ValueError:
                continue

    @classmethod
    def create_node_data(cls, node_type: str, custom_data: dict = None, category: str = None) -> dict:
        template = cls._resolve_template(node_type, category)
        core_settings = cls.get_core_field_settings()
        default_data = {
            field_name: copy.deepcopy(default_value)
            for field_name, default_value in cls.CORE_NODE_FIELDS.items()
            if core_settings.get(field_name, True)
        }
        if template:
            default_data.update(copy.deepcopy(template.get("default_data", {})))

        override = cls.PREDEFINED_NODE_TEMPLATE_OVERRIDES.get(node_type, {})
        removed_fields = override.get("removed_fields", [])
        for field_key in removed_fields if isinstance(removed_fields, list) else []:
            default_data.pop(field_key, None)

        added_fields = override.get("added_fields", {})
        if isinstance(added_fields, dict):
            default_data.update(copy.deepcopy(added_fields))

        default_data.setdefault("notes", "")
        if custom_data:
            default_data.update(custom_data)
        return default_data

    @classmethod
    def get_node_color(cls, node_type: str, category: str = None) -> str:
        template = cls._resolve_template(node_type, category)
        if template:
            return template.get("color", "#ffffff")
        return "#ffffff"

    @classmethod
    def get_node_name(cls, node_type: str, category: str = None) -> str:
        template = cls._resolve_template(node_type, category)
        if template:
            return template.get("name", "Unknown")
        return "Unknown"

    @classmethod
    def get_node_symbol(cls, node_type: str, category: str = None) -> str:
        template = cls._resolve_template(node_type, category)
        if template and template.get("symbol"):
            return template["symbol"]
        return cls.DEFAULT_NODE_SYMBOLS.get(node_type, "[NODE]")

    @classmethod
    def get_available_node_types(cls, category: str = None) -> list:
        normalized_category = cls.normalize_category(category)
        if normalized_category == cls.CUSTOM_CATEGORY:
            return cls.list_custom_node_types()
        if normalized_category and normalized_category in cls.CATEGORY_TEMPLATES:
            return sorted(cls.CATEGORY_TEMPLATES[normalized_category].keys())
        if normalized_category:
            typed = []
            for node_type, config in cls.NODE_TYPES.items():
                config_category = cls.normalize_category(config.get("category", "General"))
                if config_category == normalized_category:
                    typed.append(node_type)
            return sorted(typed)

        all_types = set(cls.NODE_TYPES.keys())
        all_types.update(cls.list_custom_node_types())
        return sorted(all_types)

    @classmethod
    def get_all_node_types(cls) -> list:
        all_types = set(cls.get_available_node_types())
        for templates in cls.CATEGORY_TEMPLATES.values():
            all_types.update(templates.keys())
        return sorted(all_types)

    @classmethod
    def get_node_type_categories(cls) -> dict:
        categories = {}

        for node_type, config in cls.NODE_TYPES.items():
            categories[node_type] = cls.normalize_category(config.get("category", "General"))

        for category_name, templates in cls.CATEGORY_TEMPLATES.items():
            for node_type in templates:
                categories.setdefault(node_type, cls.normalize_category(category_name))

        for node_type in cls.CUSTOM_NODE_TEMPLATES:
            categories[node_type] = cls.CUSTOM_CATEGORY

        return categories

    @classmethod
    def find_node_category(cls, node_type: str):
        if node_type in cls.CUSTOM_NODE_TEMPLATES:
            return cls.CUSTOM_CATEGORY

        for category_name, templates in cls.CATEGORY_TEMPLATES.items():
            if node_type in templates:
                return cls.normalize_category(category_name)

        if node_type in cls.NODE_TYPES:
            return cls.normalize_category(cls.NODE_TYPES[node_type].get("category", "General"))

        return None
