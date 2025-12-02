import platform
import socket
import psutil
import winreg
import subprocess
import os
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QProgressDialog, QMessageBox
from models.object_model import ObjectType
from core.sandbox.sandbox_object_factory import SandboxObjectFactory
from tools.system_analyzer_core import SystemAnalyzer

class SystemAnalysisThread(QThread):
    progress_updated = pyqtSignal(int, str)
    analysis_complete = pyqtSignal(list)
    
    def __init__(self, analysis_type, config=None):
        super().__init__()
        self.analysis_type = analysis_type
        self.config = config or {
            'max_objects': 60,
            'show_processes': True,
            'show_network': True,
            'show_security': True,
            'show_files': True,
            'group_similar': False
        }
    
    def run(self):
        try:
            self.progress_updated.emit(0, "Initializing system analysis...")
            
            analyzer = SystemAnalyzer()
            
            if self.analysis_type == "full":
                objects = analyzer.analyze_full_system()
            elif self.analysis_type == "network":
                objects = analyzer.analyze_network_only()
            elif self.analysis_type == "security":
                objects = analyzer.analyze_security_only()
            elif self.analysis_type == "processes":
                objects = analyzer.analyze_processes_only()
            else:
                objects = []
            
            self.progress_updated.emit(80, "Filtering and organizing results...")
            
            filtered_objects = self.apply_config_filters(objects)
            
            self.progress_updated.emit(100, "Analysis complete!")
            self.analysis_complete.emit(filtered_objects)
            
        except Exception as e:
            print(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()
            self.analysis_complete.emit([])
    
    def apply_config_filters(self, objects):
        if not objects:
            return []
        
        try:
            filtered = []
            for obj in objects:
                obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)
                
                if obj_type in ['PROCESS', 'SERVICE'] and not self.config.get('show_processes', True):
                    continue
                elif any(net_key in obj_type.lower() for net_key in ['network', 'interface', 'port']) and not self.config.get('show_network', True):
                    continue
                elif any(sec_key in obj_type.lower() for sec_key in ['security', 'firewall']) and not self.config.get('show_security', True):
                    continue
                elif obj_type in ['FILE', 'LOG'] and not self.config.get('show_files', False):
                    continue
                else:
                    filtered.append(obj)
            
            max_objects = self.config.get('max_objects', 25)
            if len(filtered) > max_objects:
                try:
                    from tools.system_analyzer_filters import SystemAnalysisFilter
                    filtered = SystemAnalysisFilter.filter_essential_components(filtered, max_objects)
                except Exception as e:
                    print(f"Error in filtering: {e}")
                    filtered = filtered[:max_objects]
            
            return filtered
            
        except Exception as e:
            print(f"Critical error in filtering: {e}")
            return objects[:self.config.get('max_objects', 60)]
    
    def perform_full_analysis(self):
        steps = [
            ("Collecting system information...", self.collect_system_info),
            ("Analyzing network interfaces...", self.collect_network_info),
            ("Scanning open ports...", self.collect_open_ports),
            ("Analyzing running services...", self.collect_services),
            ("Checking installed software...", self.collect_installed_software),
            ("Analyzing user accounts...", self.collect_user_accounts),
            ("Checking security policies...", self.collect_security_policies),
            ("Analyzing processes...", self.collect_running_processes)
        ]
        
        total_steps = len(steps)
        for i, (message, method) in enumerate(steps):
            self.progress_updated.emit(int((i / total_steps) * 100), message)
            method()
    
    def collect_system_info(self):
        try:
            system_info = {
                'hostname': socket.gethostname(),
                'platform': platform.system(),
                'platform_version': platform.version(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'total_ram': f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
                'available_ram': f"{psutil.virtual_memory().available / (1024**3):.2f} GB",
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            system_obj = self.create_object_template(ObjectType.SYSTEM_INFO, "System Information")
            system_obj.properties.update(system_info)
            self.objects_to_create.append(system_obj)
            
        except Exception as e:
            print(f"Error collecting system info: {e}")
    
    def collect_network_info(self):
        try:
            for interface_name, interface_addresses in psutil.net_if_addrs().items():
                network_obj = self.create_object_template(ObjectType.NETWORK_INTERFACE, f"Interface: {interface_name}")
                
                interface_stats = psutil.net_if_stats().get(interface_name, None)
                
                network_info = {
                    'interface_name': interface_name,
                    'status': 'up' if interface_stats and interface_stats.isup else 'down',
                    'speed': f"{interface_stats.speed} Mbps" if interface_stats else 'N/A'
                }
                
                for address in interface_addresses:
                    if address.family == socket.AF_INET:
                        network_info['ip_address'] = address.address
                        network_info['subnet_mask'] = address.netmask
                    elif address.family == psutil.AF_LINK:
                        network_info['mac_address'] = address.address
                
                network_obj.properties.update(network_info)
                self.objects_to_create.append(network_obj)
                
        except Exception as e:
            print(f"Error collecting network info: {e}")
    
    def collect_open_ports(self):
        try:
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=30)
            
            for line in result.stdout.split('\n'):
                if 'LISTENING' in line or 'ESTABLISHED' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        local_address = parts[1]
                        if ':' in local_address:
                            port = local_address.split(':')[-1]
                            if port.isdigit():
                                port_obj = self.create_object_template(ObjectType.OPEN_PORT, f"Port {port}")
                                port_obj.properties.update({
                                    'port_number': port,
                                    'protocol': 'TCP',
                                    'state': 'listening',
                                    'local_address': local_address,
                                    'security_risk': self.assess_port_risk(int(port))
                                })
                                self.objects_to_create.append(port_obj)
                                
        except Exception as e:
            print(f"Error collecting open ports: {e}")
    
    def collect_services(self):
        try:
            for service in psutil.win_service_iter() if platform.system() == "Windows" else []:
                service_obj = self.create_object_template(ObjectType.RUNNING_SERVICE, service.name())
                service_obj.properties.update({
                    'service_name': service.name(),
                    'display_name': service.display_name(),
                    'status': service.status(),
                    'startup_type': service.startup_type(),
                    'description': service.description() or 'No description'
                })
                self.objects_to_create.append(service_obj)
                
        except Exception as e:
            print(f"Error collecting services: {e}")
    
    def collect_installed_software(self):
        try:
            if platform.system() == "Windows":
                reg_paths = [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
                ]
                
                for reg_path in reg_paths:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                subkey = winreg.OpenKey(key, subkey_name)
                                
                                name = self.get_reg_value(subkey, "DisplayName")
                                if name:
                                    software_obj = self.create_object_template(
                                        ObjectType.INSTALLED_SOFTWARE, 
                                        name
                                    )
                                    software_obj.properties.update({
                                        'name': name,
                                        'version': self.get_reg_value(subkey, "DisplayVersion"),
                                        'publisher': self.get_reg_value(subkey, "Publisher"),
                                        'install_date': self.get_reg_value(subkey, "InstallDate"),
                                        'install_location': self.get_reg_value(subkey, "InstallLocation")
                                    })
                                    self.objects_to_create.append(software_obj)
                                    
                                winreg.CloseKey(subkey)
                            except:
                                continue
                        winreg.CloseKey(key)
                    except:
                        continue
                        
        except Exception as e:
            print(f"Error collecting installed software: {e}")
    
    def collect_user_accounts(self):
        try:
            for user in psutil.users():
                user_obj = self.create_object_template(ObjectType.USER_ACCOUNT, user.name)
                user_obj.properties.update({
                    'username': user.name,
                    'terminal': user.terminal or 'N/A',
                    'host': user.host or 'N/A',
                    'started': datetime.fromtimestamp(user.started).strftime("%Y-%m-%d %H:%M:%S")
                })
                self.objects_to_create.append(user_obj)
                
        except Exception as e:
            print(f"Error collecting user accounts: {e}")
    
    def collect_security_policies(self):
        try:
            security_checks = [
                ("Password Policy", "password", "Check password complexity requirements"),
                ("Firewall Status", "firewall", "Verify firewall is enabled"),
                ("UAC Settings", "uac", "Check User Account Control settings"),
                ("Windows Update", "update", "Verify automatic updates are enabled")
            ]
            
            for policy_name, policy_type, description in security_checks:
                policy_obj = self.create_object_template(ObjectType.SECURITY_POLICY, policy_name)
                policy_obj.properties.update({
                    'policy_name': policy_name,
                    'policy_type': policy_type,
                    'description': description,
                    'compliance_status': 'unknown',
                    'risk_level': 'medium'
                })
                self.objects_to_create.append(policy_obj)
                
        except Exception as e:
            print(f"Error collecting security policies: {e}")
    
    def collect_running_processes(self):
        try:
            for process in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    process_obj = self.create_object_template(ObjectType.PROCESS, process.info['name'])
                    process_obj.properties.update({
                        'name': process.info['name'],
                        'pid': str(process.info['pid']),
                        'cpu_usage': f"{process.info['cpu_percent']:.1f}%",
                        'memory_usage': f"{process.info['memory_percent']:.1f}%"
                    })
                    self.objects_to_create.append(process_obj)
                except:
                    continue
                    
        except Exception as e:
            print(f"Error collecting running processes: {e}")
    
    def get_reg_value(self, key, value_name):
        try:
            value, regtype = winreg.QueryValueEx(key, value_name)
            return value
        except:
            return None
    
    def assess_port_risk(self, port):
        high_risk_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995, 1433, 3306, 3389, 5432]
        if port in high_risk_ports:
            return "high"
        elif port < 1024:
            return "medium"
        else:
            return "low"
    
    def create_object_template(self, obj_type, name):
        from PyQt6.QtCore import QPointF
        return type('ObjectTemplate', (), {
            'object_type': obj_type,
            'name': name,
            'properties': {},
            'position': QPointF(0, 0)
        })()
    
    def perform_network_analysis(self):
        self.collect_system_info()
        self.collect_network_info()
        self.collect_open_ports()
    
    def perform_security_analysis(self):
        self.collect_system_info()
        self.collect_open_ports()
        self.collect_security_policies()
        self.collect_user_accounts()
    
    def perform_processes_analysis(self):
        self.collect_system_info()
        self.collect_running_processes()
        self.collect_services()

class SystemAnalysisFilter:
    
    @staticmethod
    def filter_essential_components(all_objects, max_objects=50):
        if len(all_objects) <= max_objects:
            return all_objects

        scored_objects = []
        for obj in all_objects:
            score = SystemAnalysisFilter.calculate_importance_score(obj)
            scored_objects.append((score, obj))
        
        scored_objects.sort(key=lambda x: x[0], reverse=True)
        return [obj for score, obj in scored_objects[:max_objects]]
    
    @staticmethod
    def calculate_importance_score(obj):
        score = 0

        type_weights = {
            'OPERATING_SYSTEM': 100,
            'KERNEL': 90,
            'SERVER': 85,
            'DATABASE': 80,
            'NETWORK_INTERFACE': 75,
            'FIREWALL': 70,
            'SECURITY_SERVICE': 65,
            'WEB_SERVER': 60,
            'CRITICAL_SERVICE': 55,
            'USER_ACCOUNT': 50,
            'PROCESS': 40,
            'FILE': 30,
            'LOG': 20,
            'REGISTRY_KEY': 10
        }
        
        obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)
        score += type_weights.get(obj_type, 0)

        props = obj.properties if hasattr(obj, 'properties') else {}

        if props.get('status') == 'running':
            score += 20
        
        if any(net_key in str(props).lower() for net_key in ['network', 'port', 'ip', 'interface']):
            score += 15

        if any(sec_key in str(props).lower() for sec_key in ['security', 'firewall', 'antivirus', 'encryption']):
            score += 25

        name = obj.name.lower() if hasattr(obj, 'name') else str(obj).lower()
        
        critical_keywords = [
            'kernel', 'system', 'root', 'admin', 'windows', 'linux', 
            'apache', 'nginx', 'mysql', 'postgresql', 'oracle',
            'ssh', 'http', 'https', 'dns', 'dhcp'
        ]
        
        for keyword in critical_keywords:
            if keyword in name:
                score += 10
        
        return score
    
    @staticmethod
    def group_similar_objects(objects):
        grouped = {}
        
        for obj in objects:
            obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)
            
            if obj_type in ['PROCESS', 'SERVICE']:
                status = obj.properties.get('status', 'unknown') if hasattr(obj, 'properties') else 'unknown'
                group_key = f"{obj_type}_{status}"
            elif obj_type in ['FILE', 'LOG']:
                name = obj.name.lower() if hasattr(obj, 'name') else str(obj).lower()
                if '.' in name:
                    ext = name.split('.')[-1]
                    group_key = f"{obj_type}_{ext}"
                else:
                    group_key = f"{obj_type}_other"
            else:
                group_key = obj_type
            
            if group_key not in grouped:
                grouped[group_key] = []
            grouped[group_key].append(obj)

        result = []
        for group_key, group_objects in grouped.items():
            if len(group_objects) <= 5:
                result.extend(group_objects)
            else:
                scored = [(SystemAnalysisFilter.calculate_importance_score(obj), obj) for obj in group_objects]
                scored.sort(key=lambda x: x[0], reverse=True)
                result.extend([obj for score, obj in scored[:3]])
                
                if len(group_objects) > 3:
                    group_obj = SystemAnalysisFilter.create_group_object(group_key, group_objects[3:])
                    result.append(group_obj)
        
        return result
    
    @staticmethod
    def create_group_object(group_name, grouped_objects):
        from models.object_model import SandboxObject, ObjectType
        from PyQt6.QtCore import QPointF
        
        group_obj = SandboxObject(
            object_type=ObjectType.CONTAINER,
            position=QPointF(0, 0),
            name=f"{group_name.replace('_', ' ').title()} Group ({len(grouped_objects)} items)"
        )
        
        sample_names = [obj.name for obj in grouped_objects[:5]]
        group_obj.properties = {
            'group_type': group_name,
            'item_count': len(grouped_objects),
            'sample_items': sample_names,
            'all_items': [obj.name for obj in grouped_objects],
            'is_group': True
        }
        
        return group_obj