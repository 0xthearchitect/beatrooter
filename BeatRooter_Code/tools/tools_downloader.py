import os
import requests
import zipfile
import tarfile
import platform
import sys
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QTextEdit, QCheckBox,
                             QMessageBox, QApplication, QGroupBox)
from PyQt6.QtCore import QThread, pyqtSignal

class InstallationThread(QThread):
    progress_updated = pyqtSignal(int, str)
    installation_finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)

    def __init__(self, tools_to_install, install_methods):
        super().__init__()
        self.tools_to_install = tools_to_install
        self.install_methods = install_methods

    def run(self):
        try:
            success_count = 0
            total_tools = len(self.tools_to_install)

            for i, tool_name in enumerate(self.tools_to_install, 1):
                progress = int((i - 1) / total_tools * 100)
                self.progress_updated.emit(progress, f"Instalando {tool_name}...")
                
                install_method = self.install_methods.get(tool_name, 'native')
                
                if self.install_tool(tool_name, install_method):
                    success_count += 1
                    self.log_message.emit(f"{tool_name} instalado com sucesso")
                else:
                    self.log_message.emit(f"Falha ao instalar {tool_name}")

            self.installation_finished.emit(
                success_count > 0,
                f"Instalação concluída: {success_count}/{total_tools} ferramentas"
            )

        except Exception as e:
            self.log_message.emit(f"Erro durante a instalação: {str(e)}")
            self.installation_finished.emit(False, f"Erro: {str(e)}")

    def install_tool(self, tool_name, method):
        try:
            if method == 'native':
                return self.install_native(tool_name)
            elif method == 'wsl':
                return self.install_via_wsl(tool_name)
            elif method == 'python':
                return self.install_via_pip(tool_name)
            else:
                return False
                
        except Exception as e:
            self.log_message.emit(f"Erro ao instalar {tool_name}: {str(e)}")
            return False

    def install_native(self, tool_name):
        system = platform.system().lower()
        
        if system == "windows":
            return self.install_windows_native(tool_name)
        elif system == "linux":
            return self.install_linux_native(tool_name)
        else:
            self.log_message.emit(f"Sistema {system} não suportado para instalação nativa")
            return False

    def install_windows_native(self, tool_name):
        pip_packages = {
            'sublist3r': 'sublist3r',
            'whois': 'python-whois'
        }
        
        if tool_name in pip_packages:
            return self.install_via_pip(tool_name)
        
        manual_tools = {
            'nmap': "Baixe do site: https://nmap.org/download.html",
            'exiftool': "Baixe do site: https://exiftool.org/",
            'gobuster': "Baixe do GitHub: https://github.com/OJ/gobuster/releases",
            'masscan': "Baixe do GitHub: https://github.com/robertdavidgraham/masscan/releases"
        }
        
        if tool_name in manual_tools:
            self.log_message.emit(f"{tool_name} requer download manual:")
            self.log_message.emit(f"{manual_tools[tool_name]}")
            return False
        
        self.log_message.emit(f"{tool_name} não suportado para instalação nativa no Windows")
        return False

    def install_linux_native(self, tool_name):
        if tool_name in ['sublist3r', 'whois']:
            return self.install_via_pip(tool_name)

        system_commands = {
            'nmap': [
                ['sudo', 'apt-get', 'update'],
                ['sudo', 'apt-get', 'install', '-y', 'nmap']
            ],
            'exiftool': [
                ['sudo', 'apt-get', 'update'], 
                ['sudo', 'apt-get', 'install', '-y', 'libimage-exiftool-perl']
            ],
            'gobuster': [
                ['sudo', 'apt-get', 'update'],
                ['sudo', 'apt-get', 'install', '-y', 'gobuster']
            ],
            'masscan': [
                ['sudo', 'apt-get', 'update'],
                ['sudo', 'apt-get', 'install', '-y', 'masscan']
            ]
        }
        
        if tool_name not in system_commands:
            self.log_message.emit(f"{tool_name} não suportado no Linux")
            return False
        
        commands = system_commands[tool_name]
        
        for i, cmd in enumerate(commands, 1):
            self.log_message.emit(f"Passo {i}/{len(commands)}: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    self.log_message.emit(f"Falha no passo {i}: {result.stderr}")
                    
                    if tool_name == 'gobuster' and i == len(commands):
                        return self.install_gobuster_alternative_linux()
                    return False
                else:
                    self.log_message.emit(f"Passo {i} concluído")
                    
            except subprocess.TimeoutExpired:
                self.log_message.emit(f"Timeout no passo {i}")
                return False
            except Exception as e:
                self.log_message.emit(f"Erro no passo {i}: {str(e)}")
                return False
        
        if self.verify_system_installation(tool_name):
            self.log_message.emit(f"{tool_name} instalado com sucesso")
            return True
        else:
            self.log_message.emit(f"{tool_name} instalado mas não encontrado no PATH")
            return False

    def verify_system_installation(self, tool_name):
        import shutil
        return shutil.which(tool_name) is not None

    def install_gobuster_alternative_linux(self):
        self.log_message.emit("Tentando método alternativo para Gobuster...")
        
        alternative_commands = [
            ['sudo', 'snap', 'install', 'gobuster'],
            ['sudo', 'apt-get', 'install', '-y', 'golang-go'],
            ['go', 'install', 'github.com/OJ/gobuster/v3@latest']
        ]
        
        for cmd in alternative_commands:
            self.log_message.emit(f"Tentando: {' '.join(cmd)}")
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    self.log_message.emit("Gobuster instalado via método alternativo")
                    return True
            except:
                continue
        
        self.log_message.emit("Todos os métodos alternativos falharam")
        return False

    def install_via_wsl(self, tool_name):
        if platform.system() != "Windows":
            self.log_message.emit("WSL apenas disponível no Windows")
            return False
            
        wsl_commands = {
            'sublist3r': {
                'cmd': 'sudo apt-get update && sudo apt-get install -y python3-pip && pip3 install sublist3r',
                'timeout': 180
            },
            'whois': {
                'cmd': 'sudo apt-get update && sudo apt-get install -y whois',
                'timeout': 120
            },
            'nmap': {
                'cmd': 'sudo apt-get update && sudo apt-get install -y nmap',
                'timeout': 120
            },
            'exiftool': {
                'cmd': 'sudo apt-get update && sudo apt-get install -y libimage-exiftool-perl',
                'timeout': 120
            },
            'gobuster': {
                'cmd': 'sudo apt-get update && sudo apt-get install -y gobuster',
                'timeout': 120
            },
            'masscan': {
                'cmd': 'sudo apt-get update && sudo apt-get install -y masscan',
                'timeout': 120
            }
        }
        
        if tool_name not in wsl_commands:
            self.log_message.emit(f"{tool_name} não suportado via WSL")
            return False
            
        cmd_config = wsl_commands[tool_name]
        cmd = ['wsl', 'bash', '-c', cmd_config['cmd']]
        timeout = cmd_config['timeout']
        
        self.log_message.emit(f"Instalando no WSL: {tool_name} (timeout: {timeout}s)")
        self.log_message.emit(f"Comando: {cmd_config['cmd']}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                shell=True
            )
            
            if result.returncode == 0:
                self.log_message.emit(f"{tool_name} instalado com sucesso no WSL")

                if self.verify_wsl_installation(tool_name):
                    return True
                else:
                    self.log_message.emit(f"{tool_name} instalado mas não encontrado no PATH do WSL")
                    return False
            else:
                self.log_message.emit(f"Falha no WSL (código {result.returncode}): {result.stderr}")
                
                if tool_name == 'gobuster':
                    return self.install_gobuster_alternative()
                return False
                
        except subprocess.TimeoutExpired:
            self.log_message.emit(f"Timeout na instalação do {tool_name} via WSL")

            if tool_name == 'gobuster':
                return self.install_gobuster_alternative()
            return False
            
        except Exception as e:
            self.log_message.emit(f"Erro WSL: {str(e)}")
            return False

    def install_gobuster_alternative(self):
        self.log_message.emit("Tentando instalação alternativa do Gobuster...")
        
        try:
            cmd_go = ['wsl', 'bash', '-c', 'sudo apt-get update && sudo apt-get install -y golang-go && go install github.com/OJ/gobuster/v3@latest']
            result_go = subprocess.run(cmd_go, capture_output=True, text=True, timeout=180)
            
            if result_go.returncode == 0:
                self.log_message.emit("Gobuster instalado via Go")
                return True
            
            self.log_message.emit("Tentando download direto do binary...")
            cmd_download = ['wsl', 'bash', '-c', '''
                wget https://github.com/OJ/gobuster/releases/download/v3.6.0/gobuster-linux-amd64.tar.gz &&
                tar -xzf gobuster-linux-amd64.tar.gz &&
                sudo mv gobuster /usr/local/bin/ &&
                rm gobuster-linux-amd64.tar.gz
            ''']
            
            result_download = subprocess.run(cmd_download, capture_output=True, text=True, timeout=120)
            
            if result_download.returncode == 0:
                self.log_message.emit("Gobuster instalado via download direto")
                return True
            else:
                self.log_message.emit(f"Falha na instalação alternativa: {result_download.stderr}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"Erro na instalação alternativa: {str(e)}")
            return False

    def verify_wsl_installation(self, tool_name):
        try:
            if tool_name == 'sublist3r':
                cmd = ['wsl', 'python3', '-m', 'sublist3r', '--help']
            else:
                cmd = ['wsl', 'which', tool_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
            
        except:
            return False

    def install_via_pip(self, tool_name):
        pip_packages = {
            'sublist3r': 'sublist3r',
            'whois': 'python-whois'
        }
        
        if tool_name not in pip_packages:
            self.log_message.emit(f"{tool_name} não disponível via pip")
            return False
        
        package_name = pip_packages[tool_name]

        pip_commands = [
            [sys.executable, '-m', 'pip', 'install', '--trusted-host', 'pypi.org', '--trusted-host', 'files.pythonhosted.org', package_name],
            [sys.executable, '-m', 'pip', 'install', '--trusted-host', 'pypi.org', package_name],
            [sys.executable, '-m', 'pip', 'install', package_name],
            ['pip', 'install', '--trusted-host', 'pypi.org', package_name],
            ['pip3', 'install', '--trusted-host', 'pypi.org', package_name]
        ]
        
        for pip_cmd in pip_commands:
            self.log_message.emit(f"Tentando: {' '.join(pip_cmd)}")
            
            try:
                result = subprocess.run(pip_cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    self.log_message.emit(f"{tool_name} instalado com sucesso via pip")

                    if self.verify_pip_installation(tool_name):
                        return True
                    else:
                        self.log_message.emit(f"{tool_name} instalado mas import falha")
                        return False
                else:
                    self.log_message.emit(f"Falha com {' '.join(pip_cmd)}: {result.stderr}")
                    continue
                    
            except subprocess.TimeoutExpired:
                self.log_message.emit(f"Timeout com {' '.join(pip_cmd)}")
                continue
            except Exception as e:
                self.log_message.emit(f"Erro com {' '.join(pip_cmd)}: {str(e)}")
                continue
        
        if platform.system() == "Windows":
            return self.install_pip_workaround(tool_name, package_name)
        
        self.log_message.emit(f"Todos os métodos pip falharam para {tool_name}")
        return False

    def verify_pip_installation(self, tool_name):
        verification_commands = {
            'sublist3r': [sys.executable, '-c', 'import sublist3r; print("OK")'],
            'whois': [sys.executable, '-c', 'import whois; print("OK")']
        }
        
        if tool_name not in verification_commands:
            return True
        
        try:
            result = subprocess.run(
                verification_commands[tool_name], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return result.returncode == 0 and "OK" in result.stdout
        except:
            return False


class InstallationDialog(QDialog):
    def __init__(self, missing_tools, parent=None):
        super().__init__(parent)
        self.missing_tools = missing_tools
        self.selected_tools = missing_tools.copy()
        self.install_methods = {}
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Instalação de Ferramentas Externas")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout(self)

        # Título
        title = QLabel("Ferramentas Externas Necessárias")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Descrição
        desc = QLabel(
            "As seguintes ferramentas de segurança não foram encontradas.\n"
            "Selecione quais deseja instalar e escolha o método de instalação:"
        )
        desc.setStyleSheet("margin: 10px; color: #666;")
        layout.addWidget(desc)

        # Grupo de ferramentas
        tools_group = QGroupBox("Ferramentas Disponíveis para Instalação")
        tools_layout = QVBoxLayout(tools_group)
        
        self.tool_widgets = {}
        for tool in self.missing_tools:
            tool_widget = self.create_tool_widget(tool)
            self.tool_widgets[tool] = tool_widget
            tools_layout.addWidget(tool_widget)
        
        layout.addWidget(tools_group)

        # Área de log
        layout.addWidget(QLabel("Log de Instalação:"))
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Botões
        button_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("Instalar Selecionados")
        self.install_btn.clicked.connect(self.start_installation)
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.cancel_installation)
        
        self.close_btn = QPushButton("Fechar")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)

        button_layout.addWidget(self.install_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)

    def create_tool_widget(self, tool_name):
        from PyQt6.QtWidgets import QWidget, QHBoxLayout, QComboBox
        
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        checkbox = QCheckBox(tool_name.capitalize())
        checkbox.setChecked(True)
        checkbox.toggled.connect(lambda checked, t=tool_name: self.toggle_tool(t, checked))
        layout.addWidget(checkbox)
        
        method_combo = QComboBox()
        methods = self.get_available_methods(tool_name)
        for method in methods:
            method_combo.addItem(method['name'], method['value'])
        
        default_method = self.get_default_method(tool_name)
        method_combo.setCurrentText(default_method['name'])
        self.install_methods[tool_name] = default_method['value']
        
        method_combo.currentTextChanged.connect(
            lambda text, t=tool_name: self.update_install_method(t, text)
        )
        
        layout.addWidget(QLabel("Método:"))
        layout.addWidget(method_combo)
        layout.addStretch()
        
        return widget

    def get_available_methods(self, tool_name):
        system = platform.system().lower()
        methods = []
        
        base_methods = [
            {'name': 'Instalação Nativa', 'value': 'native'},
            {'name': 'Via PIP (Python)', 'value': 'python'}
        ]
        
        if system == "windows" and self.is_wsl_available():
            base_methods.append({'name': 'Via WSL (Linux)', 'value': 'wsl'})
        
        for method in base_methods:
            if self.is_method_supported(tool_name, method['value']):
                methods.append(method)
        
        return methods

    def get_default_method(self, tool_name):
        system = platform.system().lower()
        
        if system == "linux":
            return {'name': 'Instalação Nativa', 'value': 'native'}
        elif system == "windows":
            if tool_name in ['sublist3r', 'whois']:
                return {'name': 'Via PIP (Python)', 'value': 'python'}
            else:
                return {'name': 'Instalação Nativa', 'value': 'native'}
        else:
            return {'name': 'Instalação Nativa', 'value': 'native'}

    def is_method_supported(self, tool_name, method):
        if method == 'python':
            return tool_name in ['sublist3r', 'whois']
        return True

    def is_wsl_available(self):
        try:
            result = subprocess.run(['wsl', '--status'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def toggle_tool(self, tool, enabled):
        if enabled:
            self.selected_tools.append(tool)
        else:
            if tool in self.selected_tools:
                self.selected_tools.remove(tool)

    def update_install_method(self, tool, method_name):
        methods = self.get_available_methods(tool)
        for method in methods:
            if method['name'] == method_name:
                self.install_methods[tool] = method['value']
                break

    def start_installation(self):
        if not self.selected_tools:
            QMessageBox.warning(self, "Nenhuma Ferramenta Selecionada", 
                              "Selecione pelo menos uma ferramenta para instalar.")
            return

        self.install_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelar Instalação")
        self.progress_bar.setVisible(True)

        self.install_thread = InstallationThread(self.selected_tools, self.install_methods)
        self.install_thread.progress_updated.connect(self.update_progress)
        self.install_thread.installation_finished.connect(self.installation_complete)
        self.install_thread.log_message.connect(self.add_log)
        self.install_thread.start()

    def cancel_installation(self):
        if self.install_thread and self.install_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Cancelar Instalação",
                "Tem a certeza que deseja cancelar a instalação?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.install_thread.terminate()
                self.install_thread.wait(5000)
                self.installation_complete(False, "Instalação cancelada pelo utilizador")

    def installation_complete(self, success, message):
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.terminate()
            self.install_thread.wait(3000)

        self.progress_bar.setVisible(False)
        self.install_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.close_btn.setVisible(True)

        if success:
            QMessageBox.information(self, "Instalação Concluída", 
                                  "Ferramentas instaladas com sucesso!\n"
                                  "As ferramentas estão agora disponíveis para uso.")
        else:
            QMessageBox.warning(self, "Instalação Interrompida", 
                              f"{message}\n\n"
                              "Pode tentar novamente ou instalar manualmente.")

        self.install_btn.setEnabled(True)
        self.cancel_btn.setText("Cancelar")
        self.cancel_btn.setVisible(True)

    def update_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.setWindowTitle(f"Instalação - {message}")

    def add_log(self, message):
        self.log_text.append(message)

class ToolsDownloadManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tools_dir = Path(__file__).parent.parent / "downloaded_tools"

    def check_missing_tools(self):
        required_tools = ['nmap', 'exiftool', 'gobuster', 'sublist3r', 'whois', 'nslookup', 'masscan']
        missing_tools = []

        for tool in required_tools:
            if not self.is_tool_available(tool):
                missing_tools.append(tool)

        return missing_tools

    def is_tool_available(self, tool_name):
        import shutil

        tool_aliases = {
            'nslookup': ['nslookup', 'dig'],
            'sublist3r': ['sublist3r'],
            'whois': ['whois'],
            'nmap': ['nmap'],
            'exiftool': ['exiftool', 'exif'],
            'gobuster': ['gobuster'],
            'masscan': ['masscan']
        }

        # Primeiro, verifica no sistema local (Windows)
        if tool_name in tool_aliases:
            for alias in tool_aliases[tool_name]:
                if shutil.which(alias):
                    return True
        
        # Verifica módulos Python
        if tool_name == 'sublist3r':
            try:
                import sublist3r
                return True
            except ImportError:
                pass
        
        if tool_name == 'whois':
            try:
                import whois
                return True
            except ImportError:
                pass
        
        # Se estiver no Windows, verifica no WSL também
        if platform.system() == "Windows":
            if tool_name in ['masscan', 'nmap', 'gobuster', 'exiftool']:  # Adicione outras ferramentas se necessário
                if self.check_tool_in_wsl(tool_name):
                    return True
            elif self.check_tool_in_wsl(tool_name):
                return True
        
        return False

    def check_tool_in_wsl(self, tool_name):
        try:
            if tool_name == 'sublist3r':
                cmd = ['wsl', 'python3', '-c', '"import sublist3r; print(\"available\")"']
            elif tool_name == 'whois':
                cmd = ['wsl', 'which', 'whois']
            else:
                cmd = ['wsl', 'which', tool_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except:
            return False

    def check_downloaded_tools(self, tool_name):
        tool_paths = {
            'nmap': self.tools_dir / 'nmap' / 'nmap.exe',
            'exiftool': self.tools_dir / 'exiftool' / 'exiftool.exe',
            'gobuster': self.tools_dir / 'gobuster' / 'gobuster.exe'
        }

        if tool_name in tool_paths:
            return tool_paths[tool_name].exists()
        return False

    def get_tool_path(self, tool_name):
        system = platform.system().lower()

        if tool_name == 'nslookup':
            import shutil
            return shutil.which('nslookup') or shutil.which('dig')
        
        if tool_name == 'sublist3r':
            if self.check_python_module('sublist3r'):
                return f'{sys.executable} -m sublist3r'
            else:
                import shutil
                path = shutil.which('sublist3r')
                return path if path else None
        
        if tool_name == 'whois':
            if self.check_python_module('whois'):
                return self.create_python_whois_wrapper()
            else:
                import shutil
                return shutil.which('whois')

        # Verifica se a ferramenta está disponível localmente
        import shutil
        path = shutil.which(tool_name)
        if path:
            return path

        # Verifica se está disponível via WSL (no Windows)
        if platform.system() == "Windows" and tool_name in ['masscan', 'nmap', 'gobuster', 'exiftool']:
            if self.check_tool_in_wsl(tool_name):
                # Retorna comando WSL para executar a ferramenta
                return f'wsl {tool_name}'

        downloaded_paths = {
            'nmap': self.tools_dir / 'nmap' / 'nmap.exe',
            'exiftool': self.tools_dir / 'exiftool' / 'exiftool.exe', 
            'gobuster': self.tools_dir / 'gobuster' / 'gobuster.exe',
            'masscan': self.tools_dir / 'masscan' / 'masscan.exe'
        }

        if tool_name in downloaded_paths and downloaded_paths[tool_name].exists():
            return str(downloaded_paths[tool_name])

        return None

        downloaded_paths = {
            'nmap': self.tools_dir / 'nmap' / 'nmap.exe',
            'exiftool': self.tools_dir / 'exiftool' / 'exiftool.exe', 
            'gobuster': self.tools_dir / 'gobuster' / 'gobuster.exe',
            'masscan': self.tools_dir / 'masscan' / 'masscan.exe'  # ADICIONE ESTA LINHA
        }

        if tool_name in downloaded_paths and downloaded_paths[tool_name].exists():
            return str(downloaded_paths[tool_name])

        return None

    def check_python_module(self, module_name):
        try:
            if module_name == 'sublist3r':
                import sublist3r
                return True
            elif module_name == 'whois':
                import whois
                return True
        except ImportError:
            return False
        return False

    def create_python_whois_wrapper(self):
        wrapper_path = self.tools_dir / "whois_wrapper.py"
        
        wrapper_code = '''#!/usr/bin/env python3
    import whois
    import sys

    if len(sys.argv) > 1:
        domain = sys.argv[1]
        try:
            w = whois.whois(domain)
            print(w)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: whois_wrapper.py <domain>")
    '''
        
        try:
            wrapper_path.write_text(wrapper_code, encoding='utf-8')
            
            if platform.system() != "Windows":
                import stat
                wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IEXEC)
            
            return f'{sys.executable} "{wrapper_path}"'
        except Exception as e:
            print(f"Erro ao criar wrapper whois: {e}")
            return None

    def create_whois_wrapper(self):
        wrapper_path = self.tools_dir / "whois_wrapper.py"
        wrapper_code = '''
import whois
import sys

if len(sys.argv) > 1:
    domain = sys.argv[1]
    try:
        w = whois.whois(domain)
        print(w)
    except Exception as e:
        print(f"Error: {e}")
'''
        wrapper_path.write_text(wrapper_code)
        return f'{sys.executable} "{wrapper_path}"'

    def request_installation(self):
        missing_tools = self.check_missing_tools()

        if not missing_tools:
            QMessageBox.information(
                self.main_window,
                "Ferramentas Disponíveis",
                "Todas as ferramentas estão disponíveis!"
            )
            return True

        dialog = InstallationDialog(missing_tools, self.main_window)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return self.verify_installation()
        
        return False

    def verify_installation(self):
        still_missing = self.check_missing_tools()
        
        if not still_missing:
            return True

        QMessageBox.information(
            self.main_window,
            "Instalação Concluída",
            f"Instalação finalizada. Ferramentas disponíveis.\n"
            f"Ainda em falta: {', '.join(still_missing) if still_missing else 'Nenhuma'}"
        )
        return len(still_missing) == 0