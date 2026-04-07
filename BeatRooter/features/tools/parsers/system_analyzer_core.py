import platform
import socket
import psutil
import winreg
import subprocess
import os
from datetime import datetime
from models.object_model import ObjectType

class SystemAnalyzer:
    def __init__(self):
        self.objects_to_create = []
    
    def analyze_full_system(self):
        self.objects_to_create = []
        
        self.collect_system_info()
        self.collect_network_info()
        self.collect_open_ports()
        self.collect_services()
        self.collect_installed_software()
        self.collect_user_accounts()
        self.collect_security_policies()
        self.collect_running_processes()
        
        return self.objects_to_create
    
    def analyze_network_only(self):
        self.objects_to_create = []
        self.collect_system_info()
        self.collect_network_info()
        self.collect_open_ports()
        return self.objects_to_create
    
    def analyze_security_only(self):
        self.objects_to_create = []
        self.collect_system_info()
        self.collect_open_ports()
        self.collect_security_policies()
        self.collect_user_accounts()
        return self.objects_to_create
    
    def analyze_processes_only(self):
        self.objects_to_create = []
        self.collect_system_info()
        self.collect_running_processes()
        self.collect_services()
        return self.objects_to_create
    
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
            if platform.system() == "Windows":
                for service in psutil.win_service_iter():
                    try:
                        service_info = service.as_dict()
                        service_name = service_info.get('name', 'Unknown Service')
                        
                        if service_name in ['WaaSMedicSvc']:
                            continue
                            
                        service_obj = self.create_object_template(ObjectType.RUNNING_SERVICE, service_name)
                        
                        properties = {
                            'service_name': service_name,
                            'display_name': service_info.get('display_name', ''),
                            'status': service_info.get('status', 'unknown'),
                            'description': service_info.get('description', 'No description')
                        }
                        
                        try:
                            properties['startup_type'] = service_info.get('startup_type', 'unknown')
                        except:
                            properties['startup_type'] = 'unknown'
                        
                        try:
                            properties['username'] = service_info.get('username', '')
                        except:
                            properties['username'] = ''
                        
                        try:
                            properties['pid'] = str(service_info.get('pid', ''))
                        except:
                            properties['pid'] = ''
                        
                        service_obj.properties.update(properties)
                        self.objects_to_create.append(service_obj)
                        
                    except Exception as e:
                        print(f"Error processing service {service.name() if hasattr(service, 'name') else 'Unknown'}: {e}")
                        continue
            else:
                try:
                    result = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=running', '--no-legend'], 
                                        capture_output=True, text=True, timeout=10)
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 4:
                                service_name = parts[0]
                                service_obj = self.create_object_template(ObjectType.RUNNING_SERVICE, service_name)
                                service_obj.properties.update({
                                    'service_name': service_name,
                                    'status': 'running',
                                    'description': ' '.join(parts[4:]) if len(parts) > 4 else 'No description'
                                })
                                self.objects_to_create.append(service_obj)
                except Exception as e:
                    print(f"Error collecting Linux services: {e}")
                    
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