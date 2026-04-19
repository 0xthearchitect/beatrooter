import os
import json
import requests
import zipfile
import tarfile
import platform
import sys
import subprocess
from pathlib import Path
import shutil
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QProgressBar, QPushButton, QTextEdit, QCheckBox,
                             QMessageBox, QApplication, QGroupBox, QScrollArea,
                             QFrame, QWidget, QComboBox, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from features.tools.core.tool_node_service import ToolNodeService

class InstallationThread(QThread):
    progress_updated = pyqtSignal(int, str)
    installation_finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)

    def __init__(self, tools_to_install, install_methods):
        super().__init__()
        self.tools_to_install = [self._normalize_tool_name(tool_name) for tool_name in tools_to_install]
        self.install_methods = install_methods
        self.repo_root = Path(__file__).resolve().parents[2]
        self.installer_dir = self.repo_root / "toolInstallerScripts"
        self.installer_scripts_dir = self.installer_dir / "individualInstallers"
        self.installer_config = self._load_installer_config()
        self.installed_tools = []
        self.failed_tools = []
        self.manual_tools = {}
        self._current_tool = None
        self._current_outcome = None

    def _normalize_tool_name(self, tool_name):
        aliases = {
            "nslookup": "dnsutils",
            "searchexploit": "searchsploit",
            "sublist3r": "subfinder",
        }
        return aliases.get(str(tool_name or "").strip().lower(), str(tool_name or "").strip().lower())

    def _load_installer_config(self):
        config_path = self.installer_dir / "tools.json"
        if not config_path.exists():
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return {}

    def _get_installer_entry(self, tool_name):
        normalized = self._normalize_tool_name(tool_name)
        if normalized in self.installer_config:
            return self.installer_config[normalized]
        if normalized == "searchsploit" and "searchexploit" in self.installer_config:
            return self.installer_config["searchexploit"]
        if normalized == "dnsutils" and "nslookup" in self.installer_config:
            return self.installer_config["nslookup"]
        if normalized == "subfinder" and "sublist3r" in self.installer_config:
            return self.installer_config["sublist3r"]
        return None

    def _resolve_install_method(self, tool_name):
        normalized = self._normalize_tool_name(tool_name)
        candidate_keys = [normalized]
        if normalized == "dnsutils":
            candidate_keys.append("nslookup")
        if normalized == "searchsploit":
            candidate_keys.append("searchexploit")

        for key in candidate_keys:
            if key in self.install_methods:
                return self.install_methods[key]
        return "native"

    def run(self):
        try:
            total_tools = len(self.tools_to_install)

            for i, tool_name in enumerate(self.tools_to_install, 1):
                progress = int((i - 1) / total_tools * 100)
                self.progress_updated.emit(progress, f"Instalando {tool_name}...")
                
                install_method = self._resolve_install_method(tool_name)
                outcome = self.install_tool(tool_name, install_method)
                if outcome == "installed":
                    self.installed_tools.append(tool_name)
                    self.log_message.emit(f"{tool_name} instalado com sucesso")
                elif outcome == "manual":
                    self.log_message.emit(f"{tool_name} requer instalação manual")
                else:
                    self.failed_tools.append(tool_name)
                    self.log_message.emit(f"Falha ao instalar {tool_name}")

            self.installation_finished.emit(
                bool(self.installed_tools) and not self.failed_tools and not self.manual_tools,
                self._build_completion_message(total_tools)
            )

        except Exception as e:
            self.log_message.emit(f"Erro durante a instalação: {str(e)}")
            self.installation_finished.emit(False, f"Erro: {str(e)}")

    def install_tool(self, tool_name, method):
        self._current_tool = self._normalize_tool_name(tool_name)
        self._current_outcome = None
        try:
            tool_name = self._current_tool
            if method == 'native':
                result = self.install_native(tool_name)
            elif method == 'aur':
                result = self.install_via_aur(tool_name)
            elif method == 'local':
                result = self.install_local_user_tool(tool_name)
            elif method == 'wsl':
                result = self.install_via_wsl(tool_name)
            elif method == 'python':
                result = self.install_via_pip(tool_name)
            else:
                result = False

            if result:
                return "installed"
            return self._current_outcome or "failed"
                
        except Exception as e:
            self.log_message.emit(f"Erro ao instalar {tool_name}: {str(e)}")
            return "failed"

    def _mark_manual_required(self, note=None):
        self._current_outcome = "manual"
        if self._current_tool:
            self.manual_tools[self._current_tool] = note or self.manual_tools.get(self._current_tool)

    def _build_completion_message(self, total_tools):
        installed_count = len(self.installed_tools)
        manual_count = len(self.manual_tools)
        failed_count = len(self.failed_tools)

        lines = [f"Instalação concluída: {installed_count}/{total_tools} instaladas automaticamente."]
        if manual_count:
            lines.append(f"{manual_count} requerem ação manual.")
            for tool_name, note in self.manual_tools.items():
                lines.append(f"- {tool_name}: {note or 'instalação manual necessária'}")
        if failed_count:
            lines.append(f"{failed_count} falharam sem alternativa automática clara: {', '.join(self.failed_tools)}")
        return "\n".join(lines)

    def install_native(self, tool_name):
        system = platform.system().lower()

        if system == "windows":
            return self.install_windows_native(tool_name)
        if system == "linux":
            return self.install_linux_native(tool_name)
        if system == "darwin":
            return self.install_macos_native(tool_name)

        self.log_message.emit(f"Sistema {system} não suportado para instalação nativa")
        return False

    def install_windows_native(self, tool_name):
        if tool_name == 'whois':
            return self.install_via_pip(tool_name)

        if self._try_windows_package_manager_install(tool_name):
            return True

        manual_tools = {
            'nmap': "Baixe do site: https://nmap.org/download.html",
            'exiftool': "Baixe do site: https://exiftool.org/",
            'amass': "Projeto oficial: https://github.com/owasp-amass/amass",
            'gobuster': "Baixe do GitHub: https://github.com/OJ/gobuster/releases",
            'masscan': "Baixe do GitHub: https://github.com/robertdavidgraham/masscan/releases",
            'dnsutils': "Instale BIND Tools para Windows, ou use PowerShell Resolve-DnsName.",
            'binwalk': "Baixe do projeto oficial: https://github.com/ReFirmLabs/binwalk",
            'cupp': "Baixe do projeto oficial: https://github.com/Mebus/cupp",
            'enum4linux': "Use WSL ou projeto oficial: https://github.com/CiscoCXSecurity/enum4linux",
            'ghidra': "Baixe do site oficial: https://github.com/NationalSecurityAgency/ghidra/releases",
            'hashcat': "Baixe do site oficial: https://hashcat.net/hashcat/",
            'hydra': "Projeto oficial: https://github.com/vanhauser-thc/thc-hydra",
            'john': "Projeto oficial: https://www.openwall.com/john/",
            'linpeas': "Projeto oficial: https://github.com/peass-ng/PEASS-ng",
            'netcat': "Use Ncat oficial do Nmap: https://nmap.org/ncat/",
            'patator': "Projeto oficial: https://github.com/lanjelot/patator",
            'revshellgen': "Projeto oficial: https://github.com/t0thkr1s/revshellgen",
            'rpcclient': "Recomendado via WSL (Samba tools).",
            'searchsploit': "Projeto oficial: https://github.com/offensive-security/exploitdb",
            'sqlmap': "Projeto oficial: https://github.com/sqlmapproject/sqlmap",
            'steghide': "Projeto oficial: http://steghide.sourceforge.net/",
            'strings': "Instale GNU binutils (ex: MSYS2/MinGW ou WSL).",
            'tshark': "Baixe do site oficial Wireshark: https://www.wireshark.org/download.html",
            'whatweb': "Projeto oficial: https://github.com/urbanadventurer/WhatWeb",
            'wifite': "Recomendado via WSL/Linux: https://github.com/derv82/wifite2",
        }

        if tool_name in manual_tools:
            self.log_message.emit(f"{tool_name} requer download manual:")
            self.log_message.emit(f"{manual_tools[tool_name]}")
            self._mark_manual_required(manual_tools[tool_name])
            return False

        self.log_message.emit(f"{tool_name} não suportado para instalação nativa no Windows")
        return False

    def install_linux_native(self, tool_name):
        package_manager = self._detect_linux_package_manager()
        if not package_manager:
            self.log_message.emit("Nenhum gestor de pacotes Linux suportado foi encontrado (apt/dnf/pacman/zypper/apk).")
            if tool_name in {'whois'}:
                return self.install_via_pip(tool_name)
            return False

        self.log_message.emit(f"Distribuição detetada via gestor: {package_manager}")

        if self._can_manage_linux_packages(package_manager) and self.install_via_toolinstaller_script(tool_name):
            return True

        package_name = self._get_linux_package_name(tool_name, package_manager)
        if not package_name:
            self.log_message.emit(f"{tool_name} não tem mapeamento oficial para {package_manager}.")
            self._log_linux_install_hint(tool_name, package_manager)
            if tool_name in {'whois'}:
                return self.install_via_pip(tool_name)
            return False

        if not self._can_manage_linux_packages(package_manager):
            self._log_linux_privilege_issue(tool_name, package_manager, package_name)
            return False

        update_cmd = self._get_linux_update_command(package_manager)
        install_cmd = self._get_linux_install_command(package_manager, package_name)

        if not self._run_linux_privileged_command(update_cmd, package_manager, timeout=180):
            return False
        if not self._run_linux_privileged_command(install_cmd, package_manager, timeout=240):
            return False

        entry = self._get_installer_entry(tool_name)
        if (entry and self.verify_installation_from_entry(entry)) or self.verify_system_installation(tool_name):
            self.log_message.emit(f"{tool_name} instalado com sucesso")
            return True

        self.log_message.emit(f"{tool_name} instalado, mas não foi encontrado no PATH atual.")
        return False

    def install_via_toolinstaller_script(self, tool_name):
        entry = self._get_installer_entry(tool_name)
        if not entry:
            return False

        script_name = str(entry.get("script", "") or "").strip()
        if not script_name:
            return False

        script_path = self.installer_scripts_dir / script_name
        if not script_path.exists():
            return False

        install_option = str(entry.get("install_option", "1"))
        self.log_message.emit(f"Instalação via script oficial: {script_name} (opção {install_option})")

        try:
            result = subprocess.run(
                ["bash", str(script_path)],
                input=f"{install_option}\n1\n",
                capture_output=True,
                text=True,
                timeout=900,
            )
        except subprocess.TimeoutExpired:
            self.log_message.emit(f"Timeout ao executar {script_name}")
            return False
        except Exception as exc:
            self.log_message.emit(f"Erro ao executar {script_name}: {exc}")
            return False

        if result.stdout and result.stdout.strip():
            self.log_message.emit(result.stdout.strip())
        if result.stderr and result.stderr.strip():
            self.log_message.emit(result.stderr.strip())

        if result.returncode != 0:
            self.log_message.emit(f"Script {script_name} terminou com código {result.returncode}.")
            return False

        if self.verify_installation_from_entry(entry):
            return True

        return self.verify_system_installation(tool_name)

    def verify_installation_from_entry(self, entry):
        check_cmd = entry.get("check_command")
        special_path = str(entry.get("special_path", "") or "").strip()

        if special_path and Path(special_path).exists():
            return True

        if isinstance(check_cmd, list):
            return any(shutil.which(str(cmd)) for cmd in check_cmd)

        if isinstance(check_cmd, str) and check_cmd.strip():
            return shutil.which(check_cmd.strip()) is not None

        return False

    def install_macos_native(self, tool_name):
        if not self._command_exists('brew'):
            self.log_message.emit("Homebrew não está instalado. Instale em https://brew.sh")
            if tool_name in {'whois'}:
                return self.install_via_pip(tool_name)
            return False

        brew_packages = {
            'nmap': 'nmap',
            'exiftool': 'exiftool',
            'amass': 'amass',
            'gobuster': 'gobuster',
            'masscan': 'masscan',
            'subfinder': 'subfinder',
            'whois': 'whois',
            'dnsutils': 'bind',
            'binwalk': 'binwalk',
            'hashcat': 'hashcat',
            'hydra': 'hydra',
            'john': 'john-jumbo',
            'netcat': 'netcat',
            'searchsploit': 'exploitdb',
            'sqlmap': 'sqlmap',
            'tshark': 'wireshark',
            'whatweb': 'whatweb',
        }
        package_name = brew_packages.get(tool_name)
        if not package_name:
            self.log_message.emit(f"{tool_name} não suportado para instalação nativa no macOS")
            return False

        if not self._run_command(['brew', 'install', package_name], timeout=300):
            return False

        return self.verify_system_installation(tool_name)

    def verify_system_installation(self, tool_name):
        aliases = {
            'amass': ['amass'],
            'dnsutils': ['nslookup', 'dig', 'host'],
            'exiftool': ['exiftool', 'exif'],
            'subfinder': ['subfinder'],
            'whois': ['whois'],
            'netcat': ['nc', 'netcat', 'ncat'],
            'tshark': ['tshark'],
            'searchsploit': ['searchsploit'],
            'linpeas': ['linpeas'],
            'revshellgen': ['revshellgen'],
            'rpcclient': ['rpcclient'],
            'strings': ['strings'],
        }
        for candidate in aliases.get(tool_name, [tool_name]):
            if shutil.which(candidate):
                return True
        return False

    def install_via_wsl(self, tool_name):
        if platform.system() != "Windows":
            self.log_message.emit("WSL apenas disponível no Windows")
            return False

        if not self._is_wsl_available():
            self.log_message.emit("WSL não está disponível ou não responde.")
            return False

        if tool_name == 'subfinder':
            return self._install_wsl_native_tool('subfinder')
        if tool_name == 'whois':
            if self._install_wsl_native_tool('whois'):
                return True
            return self._install_wsl_pip_package('python-whois')

        return self._install_wsl_native_tool(tool_name)

    def verify_wsl_installation(self, tool_name):
        try:
            if tool_name == 'dnsutils':
                cmd = ['wsl', 'bash', '-lc', 'command -v nslookup || command -v dig']
            elif tool_name == 'netcat':
                cmd = ['wsl', 'bash', '-lc', 'command -v nc || command -v netcat || command -v ncat']
            else:
                cmd = ['wsl', 'bash', '-lc', f'command -v {tool_name}']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0

        except Exception:
            return False

    def install_via_pip(self, tool_name):
        pip_packages = {
            'whois': 'python-whois'
        }
        
        if tool_name not in pip_packages:
            self.log_message.emit(f"{tool_name} não disponível via pip")
            return False
        
        package_name = pip_packages[tool_name]

        pip_commands = [
            [sys.executable, '-m', 'pip', 'install', package_name],
            [sys.executable, '-m', 'pip', 'install', '--user', package_name],
        ]
        if self._command_exists('pip3'):
            pip_commands.append(['pip3', 'install', '--user', package_name])
        if self._command_exists('pip'):
            pip_commands.append(['pip', 'install', '--user', package_name])

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
                self.log_message.emit(f"Falha com {' '.join(pip_cmd)}: {(result.stderr or result.stdout).strip()}")

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

    def install_via_aur(self, tool_name):
        if platform.system().lower() != "linux":
            self.log_message.emit("A instalação via AUR só está disponível no Linux.")
            return False

        if not self._command_exists('yay'):
            self.log_message.emit("O helper AUR `yay` não está disponível.")
            self._mark_manual_required("Instale `yay` ou use clone/manual para esta ferramenta.")
            return False

        aur_packages = {
            'amass': 'amass',
            'steghide': 'steghide',
            'enum4linux': 'enum4linux-git',
            'patator': 'patator',
            'subfinder': 'subfinder',
            'whatweb': 'whatweb',
        }
        package_name = aur_packages.get(tool_name)
        if not package_name:
            self.log_message.emit(f"{tool_name} não está configurado para instalação via AUR.")
            return False

        cmd = ['yay', '-S', '--noconfirm', package_name]
        if self._run_command(cmd, timeout=1200) and self.verify_system_installation(tool_name):
            return True

        self._mark_manual_required(f"A instalação via AUR (`yay -S {package_name}`) falhou; verifique o log.")
        return False

    def install_local_user_tool(self, tool_name):
        if platform.system().lower() != "linux":
            self.log_message.emit("A instalação local de utilizador está disponível apenas no Linux.")
            return False

        installers = {
            'cupp': self._install_local_cupp,
            'linpeas': self._install_local_linpeas,
            'patator': self._install_local_patator,
            'revshellgen': self._install_local_revshellgen,
            'whatweb': self._install_local_whatweb,
        }
        installer = installers.get(tool_name)
        if installer is None:
            self.log_message.emit(f"{tool_name} não tem instalador local configurado.")
            return False

        home = Path.home()
        local_bin = home / '.local' / 'bin'
        local_opt = home / 'opt'
        local_bin.mkdir(parents=True, exist_ok=True)
        local_opt.mkdir(parents=True, exist_ok=True)

        if installer(local_bin, local_opt):
            return self.verify_system_installation(tool_name)
        return False

    def _run_local_install_command(self, cmd, cwd=None, timeout=600):
        location = str(cwd) if cwd else None
        self.log_message.emit(f"Comando local: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=location,
            )
        except subprocess.TimeoutExpired:
            self.log_message.emit("Timeout ao executar comando local")
            return False
        except Exception as exc:
            self.log_message.emit(f"Erro ao executar comando local: {exc}")
            return False

        if result.stdout and result.stdout.strip():
            self.log_message.emit(result.stdout.strip())
        if result.stderr and result.stderr.strip():
            self.log_message.emit(result.stderr.strip())
        return result.returncode == 0

    def _write_user_wrapper(self, destination, script_body):
        try:
            destination.write_text(script_body, encoding='utf-8')
            destination.chmod(0o755)
            return True
        except Exception as exc:
            self.log_message.emit(f"Erro ao criar wrapper {destination}: {exc}")
            return False

    def _mark_local_path_hint(self):
        local_bin = Path.home() / '.local' / 'bin'
        path_parts = os.environ.get('PATH', '').split(os.pathsep)
        if str(local_bin) not in path_parts:
            self.log_message.emit(f"Sugestão: adicione {local_bin} ao PATH se ainda não estiver disponível nesta sessão.")

    def _ensure_whatweb_ruby_compatibility(self, target_dir):
        gemfile_path = Path(target_dir) / 'Gemfile'
        if not gemfile_path.exists():
            self.log_message.emit("Gemfile do WhatWeb não encontrado após o clone.")
            return False

        try:
            gemfile_text = gemfile_path.read_text(encoding='utf-8')
            missing_gems = [
                gem_name for gem_name in ('getoptlong', 'resolv-replace')
                if not re.search(rf"^\s*gem\s+['\"]{re.escape(gem_name)}['\"]", gemfile_text, flags=re.MULTILINE)
            ]
            if not missing_gems:
                return True

            compatibility_note = "\n# Ruby 3.4+ moved these libraries out of the default gems.\n"
            compatibility_note += "".join(f"gem '{gem_name}'\n" for gem_name in missing_gems)
            gemfile_path.write_text(gemfile_text.rstrip() + compatibility_note, encoding='utf-8')
            self.log_message.emit(
                "Compatibilidade WhatWeb/Ruby 3.4: adicionadas gems "
                + ", ".join(f"`{gem_name}`" for gem_name in missing_gems)
                + " ao Gemfile local."
            )
            return True
        except Exception as exc:
            self.log_message.emit(f"Erro ao ajustar Gemfile do WhatWeb: {exc}")
            return False

    @staticmethod
    def _build_whatweb_wrapper_script():
        return (
            '#!/bin/sh\n'
            'set -e\n'
            'cd "$HOME/opt/WhatWeb"\n'
            'exec bundle exec ruby "$HOME/opt/WhatWeb/whatweb" "$@"\n'
        )

    def _install_local_cupp(self, local_bin, local_opt):
        target_dir = local_opt / 'cupp'
        if target_dir.exists():
            shutil.rmtree(target_dir)
        if not self._run_local_install_command(['git', 'clone', 'https://github.com/Mebus/cupp.git', str(target_dir)], timeout=900):
            self._mark_manual_required("Clone manual: git clone https://github.com/Mebus/cupp.git ~/opt/cupp")
            return False

        wrapper = local_bin / 'cupp'
        if not self._write_user_wrapper(wrapper, '#!/bin/sh\nexec python3 "$HOME/opt/cupp/cupp.py" "$@"\n'):
            return False
        self._mark_local_path_hint()
        return True

    def _install_local_linpeas(self, local_bin, local_opt):
        target_file = local_opt / 'linpeas.sh'
        if not self._run_local_install_command(
            ['curl', '-L', 'https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh', '-o', str(target_file)],
            timeout=900,
        ):
            self._mark_manual_required("Download manual: curl -L .../linpeas.sh -o ~/opt/linpeas.sh")
            return False

        try:
            target_file.chmod(0o755)
            wrapper = local_bin / 'linpeas'
            if wrapper.exists() or wrapper.is_symlink():
                wrapper.unlink()
            wrapper.symlink_to(target_file)
        except Exception as exc:
            self.log_message.emit(f"Erro ao preparar linpeas local: {exc}")
            return False

        self._mark_local_path_hint()
        return True

    def _install_local_patator(self, local_bin, local_opt):
        if not self._command_exists('git'):
            self.log_message.emit("Patator local requer `git` instalado no sistema.")
            self._mark_manual_required("Instale `git`, depois use a instalação local do Patator.")
            return False
        if not self._command_exists('python3'):
            self.log_message.emit("Patator local requer `python3` instalado no sistema.")
            self._mark_manual_required("Instale `python3`, depois use a instalação local do Patator.")
            return False

        target_dir = local_opt / 'patator'
        venv_dir = local_opt / 'patator-venv'
        if target_dir.exists():
            shutil.rmtree(target_dir)
        if venv_dir.exists():
            shutil.rmtree(venv_dir)

        if not self._run_local_install_command(['git', 'clone', 'https://github.com/lanjelot/patator.git', str(target_dir)], timeout=900):
            self._mark_manual_required("Clone manual: git clone https://github.com/lanjelot/patator.git ~/opt/patator")
            return False

        if not self._run_local_install_command(['python3', '-m', 'venv', str(venv_dir)], timeout=900):
            self._mark_manual_required("Crie um venv manualmente: python3 -m venv ~/opt/patator-venv")
            return False

        pip_path = venv_dir / 'bin' / 'pip'
        python_path = venv_dir / 'bin' / 'python'
        if not pip_path.exists() or not python_path.exists():
            self.log_message.emit("Não foi possível preparar o ambiente virtual do Patator.")
            return False

        self._run_local_install_command([str(pip_path), 'install', '--upgrade', 'pip', 'setuptools', 'wheel'], timeout=1200)
        if not self._run_local_install_command([str(pip_path), 'install', '-r', 'requirements.txt'], cwd=target_dir, timeout=1200):
            self.log_message.emit(
                "Falha ao instalar todas as dependências do Patator. "
                "Vou tentar instalar apenas o conjunto base, sem drivers opcionais de bases de dados."
            )
            base_requirements = [
                'paramiko==3.5.1',
                'pycurl==7.45.4',
                'ajpy==0.0.5',
                'impacket==0.12.0',
                'pycryptodomex==3.21.0',
                'dnspython==2.7.0',
                'IPy==1.1',
                'pysnmp==7.1.16',
                'telnetlib-313-and-up==3.13.1',
            ]
            if not self._run_local_install_command([str(pip_path), 'install'] + base_requirements, timeout=1200):
                self._mark_manual_required(
                    "No diretório ~/opt/patator use o venv e instale dependências base; "
                    "dependências opcionais como `cx_Oracle` podem ser ignoradas."
                )
                return False
            self.log_message.emit(
                "Patator instalado com dependências base. "
                "Módulos como `oracle_login`, `mysql_login` e `pgsql_login` podem exigir pacotes extra."
            )

        wrapper = local_bin / 'patator'
        script_body = '#!/bin/sh\nexec "$HOME/opt/patator-venv/bin/python" "$HOME/opt/patator/src/patator/patator.py" "$@"\n'
        if not self._write_user_wrapper(wrapper, script_body):
            return False

        self._mark_local_path_hint()
        return True

    def _install_local_revshellgen(self, local_bin, local_opt):
        if not self._command_exists('python3'):
            self.log_message.emit("RevShellGen local requer `python3` instalado no sistema.")
            self._mark_manual_required("Instale `python3`, depois use a instalação local do RevShellGen.")
            return False

        target_dir = local_opt / 'revshellgen'
        venv_dir = local_opt / 'revshellgen-venv'
        if target_dir.exists():
            shutil.rmtree(target_dir)
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        if not self._run_local_install_command(['git', 'clone', 'https://github.com/t0thkr1s/revshellgen.git', str(target_dir)], timeout=900):
            self._mark_manual_required("Clone manual: git clone https://github.com/t0thkr1s/revshellgen.git ~/opt/revshellgen")
            return False

        if not self._run_local_install_command(['python3', '-m', 'venv', str(venv_dir)], timeout=900):
            self._mark_manual_required("Crie um venv manualmente: python3 -m venv ~/opt/revshellgen-venv")
            return False

        pip_path = venv_dir / 'bin' / 'pip'
        python_path = venv_dir / 'bin' / 'python'
        if not pip_path.exists() or not python_path.exists():
            self.log_message.emit("Não foi possível preparar o ambiente virtual do RevShellGen.")
            return False

        self._run_local_install_command([str(pip_path), 'install', '--upgrade', 'pip', 'setuptools', 'wheel'], timeout=1200)
        if not self._run_local_install_command([str(pip_path), 'install', '-r', 'requirements-minimal.txt'], cwd=target_dir, timeout=1200):
            self._mark_manual_required(
                "No diretório ~/opt/revshellgen use o venv e execute: pip install -r requirements-minimal.txt"
            )
            return False

        wrapper = local_bin / 'revshellgen'
        if not self._write_user_wrapper(
            wrapper,
            '#!/bin/sh\nexec "$HOME/opt/revshellgen-venv/bin/python" "$HOME/opt/revshellgen/revshellgen.py" "$@"\n',
        ):
            return False
        self._mark_local_path_hint()
        return True

    def _install_local_whatweb(self, local_bin, local_opt):
        if not self._command_exists('ruby') or not self._command_exists('bundle'):
            self.log_message.emit("WhatWeb local requer `ruby` e `bundle` instalados no sistema.")
            self._mark_manual_required("Instale `ruby` e `ruby-bundler`, depois use a instalação local do WhatWeb.")
            return False

        target_dir = local_opt / 'WhatWeb'
        if target_dir.exists():
            shutil.rmtree(target_dir)
        if not self._run_local_install_command(['git', 'clone', 'https://github.com/urbanadventurer/WhatWeb.git', str(target_dir)], timeout=900):
            self._mark_manual_required("Clone manual: git clone https://github.com/urbanadventurer/WhatWeb.git ~/opt/WhatWeb")
            return False

        if not self._ensure_whatweb_ruby_compatibility(target_dir):
            self._mark_manual_required(
                "No diretório do WhatWeb adicione `gem 'getoptlong'` e `gem 'resolv-replace'` ao Gemfile "
                "e execute `bundle install`."
            )
            return False

        if not self._run_local_install_command(['bundle', 'config', 'set', 'path', 'vendor/bundle'], cwd=target_dir, timeout=1200):
            self._mark_manual_required("No diretório do WhatWeb execute: bundle config set path vendor/bundle")
            return False

        if not self._run_local_install_command(['bundle', 'install'], cwd=target_dir, timeout=1200):
            self._mark_manual_required("No diretório do WhatWeb execute: bundle config set path vendor/bundle && bundle install")
            return False

        wrapper = local_bin / 'whatweb'
        if not self._write_user_wrapper(wrapper, self._build_whatweb_wrapper_script()):
            return False
        self._mark_local_path_hint()
        return True

    def verify_pip_installation(self, tool_name):
        verification_commands = {
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
        except Exception:
            return False

    def install_pip_workaround(self, tool_name, package_name):
        self.log_message.emit(f"Fallback Windows para {tool_name}: tentativa com py -m pip")
        try:
            result = subprocess.run(['py', '-m', 'pip', 'install', '--user', package_name], capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and self.verify_pip_installation(tool_name):
                return True
            self.log_message.emit(f"Fallback py -m pip falhou: {(result.stderr or result.stdout).strip()}")
        except Exception as exc:
            self.log_message.emit(f"Fallback py -m pip erro: {exc}")
        return False

    def _command_exists(self, command_name):
        from shutil import which
        return which(command_name) is not None

    def _run_command(self, cmd, timeout=180):
        self.log_message.emit(f"Comando: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.log_message.emit("Timeout ao executar comando")
            return False
        except Exception as exc:
            self.log_message.emit(f"Erro ao executar comando: {exc}")
            return False

        if result.stdout and result.stdout.strip():
            self.log_message.emit(result.stdout.strip())
        if result.stderr and result.stderr.strip():
            self.log_message.emit(result.stderr.strip())

        return result.returncode == 0

    def _detect_linux_package_manager(self):
        for manager in ['apt-get', 'apt', 'dnf', 'yum', 'pacman', 'zypper', 'apk']:
            if self._command_exists(manager):
                return manager
        return None

    def _get_linux_package_name(self, tool_name, manager):
        packages = {
            'nmap': {'apt-get': 'nmap', 'apt': 'nmap', 'dnf': 'nmap', 'yum': 'nmap', 'pacman': 'nmap', 'zypper': 'nmap', 'apk': 'nmap'},
            'exiftool': {
                'apt-get': 'libimage-exiftool-perl',
                'apt': 'libimage-exiftool-perl',
                'dnf': 'perl-Image-ExifTool',
                'yum': 'perl-Image-ExifTool',
                'pacman': 'perl-image-exiftool',
                'zypper': 'exiftool',
                'apk': 'perl-image-exiftool',
            },
            'gobuster': {'apt-get': 'gobuster', 'apt': 'gobuster', 'dnf': 'gobuster', 'yum': 'gobuster', 'pacman': 'gobuster', 'zypper': 'gobuster', 'apk': 'gobuster'},
            'masscan': {'apt-get': 'masscan', 'apt': 'masscan', 'dnf': 'masscan', 'yum': 'masscan', 'pacman': 'masscan', 'zypper': 'masscan', 'apk': 'masscan'},
            'amass': {'apt-get': 'amass', 'apt': 'amass', 'dnf': 'amass', 'yum': 'amass', 'zypper': 'amass', 'apk': 'amass'},
            'subfinder': {'apt-get': 'subfinder', 'apt': 'subfinder', 'dnf': 'subfinder', 'yum': 'subfinder', 'zypper': 'subfinder', 'apk': 'subfinder'},
            'whois': {'apt-get': 'whois', 'apt': 'whois', 'dnf': 'whois', 'yum': 'whois', 'pacman': 'whois', 'zypper': 'whois', 'apk': 'whois'},
            'dnsutils': {'apt-get': 'dnsutils', 'apt': 'dnsutils', 'dnf': 'bind-utils', 'yum': 'bind-utils', 'pacman': 'bind', 'zypper': 'bind-utils', 'apk': 'bind-tools'},
            'binwalk': {'apt-get': 'binwalk', 'apt': 'binwalk', 'dnf': 'binwalk', 'yum': 'binwalk', 'pacman': 'binwalk', 'zypper': 'binwalk', 'apk': 'binwalk'},
            'enum4linux': {'apt-get': 'enum4linux', 'apt': 'enum4linux', 'dnf': 'enum4linux', 'yum': 'enum4linux', 'zypper': 'enum4linux', 'apk': 'enum4linux'},
            'ghidra': {'apt-get': 'ghidra', 'apt': 'ghidra', 'dnf': 'ghidra', 'yum': 'ghidra', 'pacman': 'ghidra', 'zypper': 'ghidra', 'apk': 'ghidra'},
            'hashcat': {'apt-get': 'hashcat', 'apt': 'hashcat', 'dnf': 'hashcat', 'yum': 'hashcat', 'pacman': 'hashcat', 'zypper': 'hashcat', 'apk': 'hashcat'},
            'hydra': {'apt-get': 'hydra', 'apt': 'hydra', 'dnf': 'hydra', 'yum': 'hydra', 'pacman': 'hydra', 'zypper': 'hydra', 'apk': 'hydra'},
            'john': {'apt-get': 'john', 'apt': 'john', 'dnf': 'john', 'yum': 'john', 'pacman': 'john', 'zypper': 'john', 'apk': 'john'},
            'netcat': {'apt-get': 'netcat-openbsd', 'apt': 'netcat-openbsd', 'dnf': 'nmap-ncat', 'yum': 'nmap-ncat', 'pacman': 'openbsd-netcat', 'zypper': 'netcat-openbsd', 'apk': 'netcat-openbsd'},
            'patator': {'apt-get': 'patator', 'apt': 'patator', 'dnf': 'patator', 'yum': 'patator', 'zypper': 'patator', 'apk': 'patator'},
            'rpcclient': {'apt-get': 'samba-common-bin', 'apt': 'samba-common-bin', 'dnf': 'samba-common-tools', 'yum': 'samba-common-tools', 'pacman': 'smbclient', 'zypper': 'samba-client', 'apk': 'samba-client'},
            'searchsploit': {'apt-get': 'exploitdb', 'apt': 'exploitdb', 'dnf': 'exploitdb', 'yum': 'exploitdb', 'pacman': 'exploitdb', 'zypper': 'exploitdb', 'apk': 'exploitdb'},
            'sqlmap': {'apt-get': 'sqlmap', 'apt': 'sqlmap', 'dnf': 'sqlmap', 'yum': 'sqlmap', 'pacman': 'sqlmap', 'zypper': 'sqlmap', 'apk': 'sqlmap'},
            'steghide': {'apt-get': 'steghide', 'apt': 'steghide', 'dnf': 'steghide', 'yum': 'steghide', 'zypper': 'steghide', 'apk': 'steghide'},
            'strings': {'apt-get': 'binutils', 'apt': 'binutils', 'dnf': 'binutils', 'yum': 'binutils', 'pacman': 'binutils', 'zypper': 'binutils', 'apk': 'binutils'},
            'tshark': {'apt-get': 'tshark', 'apt': 'tshark', 'dnf': 'wireshark-cli', 'yum': 'wireshark-cli', 'pacman': 'wireshark-cli', 'zypper': 'wireshark', 'apk': 'tshark'},
            'whatweb': {'apt-get': 'whatweb', 'apt': 'whatweb', 'dnf': 'whatweb', 'yum': 'whatweb', 'zypper': 'whatweb', 'apk': 'whatweb'},
            'wifite': {'apt-get': 'wifite', 'apt': 'wifite', 'dnf': 'wifite', 'yum': 'wifite', 'pacman': 'wifite', 'zypper': 'wifite', 'apk': 'wifite'},
        }
        return packages.get(tool_name, {}).get(manager)

    def _can_manage_linux_packages(self, manager):
        if manager not in {'apt-get', 'apt', 'dnf', 'yum', 'pacman', 'zypper', 'apk'}:
            return True
        is_root = hasattr(os, 'geteuid') and os.geteuid() == 0
        return is_root or self._can_use_sudo_non_interactive()

    def _get_linux_install_hint(self, tool_name, manager, package_name=None):
        if manager != 'pacman':
            if package_name:
                return f"Instale manualmente com privilégios: sudo {manager} ... {package_name}"
            return None

        pacman_hints = {
            'amass': "No Arch, use AUR (`amass`) ou instale manualmente a partir do projeto OWASP Amass.",
            'cupp': "No Arch, use instalação manual do projeto ou AUR equivalente (`cupp-v3`).",
            'enum4linux': "No Arch, use AUR (`enum4linux-git`) ou clone manual do projeto.",
            'linpeas': "No Arch, use instalação manual a partir do projeto PEASS-ng.",
            'patator': "No Arch, use AUR (`patator`) ou clone manual do projeto.",
            'revshellgen': "No Arch, use clone manual do projeto oficial.",
            'steghide': "No Arch, `steghide` não costuma estar no repositório oficial; prefira AUR ou instalação manual.",
            'subfinder': "No Arch, use AUR (`subfinder`) ou instale manualmente a partir do projeto ProjectDiscovery.",
            'whatweb': "No Arch, use AUR (`whatweb`) ou instalação manual com Ruby/bundle.",
        }
        if tool_name in pacman_hints:
            return pacman_hints[tool_name]
        if package_name:
            return f"Instale manualmente com privilégios: sudo pacman -S --needed {package_name}"
        return None

    def _log_linux_install_hint(self, tool_name, manager, package_name=None):
        hint = self._get_linux_install_hint(tool_name, manager, package_name)
        if hint:
            self.log_message.emit(f"Sugestão: {hint}")
            self._mark_manual_required(hint)

    def _log_linux_privilege_issue(self, tool_name, manager, package_name):
        self.log_message.emit(
            "Este método requer privilégios administrativos. "
            "sudo não está disponível sem password (ou foi bloqueado)."
        )
        self._log_linux_install_hint(tool_name, manager, package_name)
        self.log_message.emit("Sugestão: execute o BeatRooter como root/admin ou instale manualmente no sistema.")

    def _get_linux_update_command(self, manager):
        updates = {
            'apt-get': ['apt-get', 'update'],
            'apt': ['apt', 'update'],
            'dnf': ['dnf', 'makecache'],
            'yum': ['yum', 'makecache'],
            'pacman': ['pacman', '-Sy', '--noconfirm'],
            'zypper': ['zypper', '--non-interactive', 'refresh'],
            'apk': ['apk', 'update'],
        }
        return updates.get(manager, [])

    def _get_linux_install_command(self, manager, package_name):
        commands = {
            'apt-get': ['apt-get', 'install', '-y', package_name],
            'apt': ['apt', 'install', '-y', package_name],
            'dnf': ['dnf', 'install', '-y', package_name],
            'yum': ['yum', 'install', '-y', package_name],
            'pacman': ['pacman', '-S', '--noconfirm', package_name],
            'zypper': ['zypper', '--non-interactive', 'install', package_name],
            'apk': ['apk', 'add', package_name],
        }
        return commands.get(manager, [])

    def _can_use_sudo_non_interactive(self):
        if not self._command_exists('sudo'):
            return False
        try:
            result = subprocess.run(['sudo', '-n', 'true'], capture_output=True, text=True, timeout=8)
            return result.returncode == 0
        except Exception:
            return False

    def _run_linux_privileged_command(self, cmd, manager, timeout=180):
        if not cmd:
            return False

        needs_root = manager in {'apt-get', 'apt', 'dnf', 'yum', 'pacman', 'zypper', 'apk'}
        if needs_root:
            is_root = hasattr(os, 'geteuid') and os.geteuid() == 0
            if is_root:
                return self._run_command(cmd, timeout=timeout)
            if self._can_use_sudo_non_interactive():
                return self._run_command(['sudo', '-n'] + cmd, timeout=timeout)
            self.log_message.emit(
                "Este método requer privilégios administrativos. "
                "sudo não está disponível sem password (ou foi bloqueado)."
            )
            self.log_message.emit("Sugestão: execute o BeatRooter como root/admin ou instale manualmente no sistema.")
            return False

        return self._run_command(cmd, timeout=timeout)

    def _try_windows_package_manager_install(self, tool_name):
        winget_ids = {
            'nmap': 'Insecure.Nmap',
            'exiftool': 'OliverBetz.ExifTool',
            'gobuster': None,
            'masscan': None,
            'ghidra': 'NSA.Ghidra',
            'tshark': 'WiresharkFoundation.Wireshark',
        }
        choco_pkgs = {
            'nmap': 'nmap',
            'exiftool': 'exiftool',
            'gobuster': 'gobuster',
            'masscan': 'masscan',
            'binwalk': 'binwalk',
            'hashcat': 'hashcat',
            'john': 'john',
            'sqlmap': 'sqlmap',
            'tshark': 'wireshark',
        }
        scoop_pkgs = {
            'nmap': 'nmap',
            'exiftool': 'exiftool',
            'gobuster': 'gobuster',
            'masscan': 'masscan',
            'hashcat': 'hashcat',
            'sqlmap': 'sqlmap',
        }

        attempted = False
        if self._command_exists('winget') and winget_ids.get(tool_name):
            attempted = True
            if self._run_command([
                'winget', 'install', '--id', winget_ids[tool_name], '-e',
                '--accept-package-agreements', '--accept-source-agreements'
            ], timeout=360) and self.verify_system_installation(tool_name):
                return True

        if self._command_exists('choco') and choco_pkgs.get(tool_name):
            attempted = True
            if self._run_command(['choco', 'install', choco_pkgs[tool_name], '-y'], timeout=360) and self.verify_system_installation(tool_name):
                return True

        if self._command_exists('scoop') and scoop_pkgs.get(tool_name):
            attempted = True
            if self._run_command(['scoop', 'install', scoop_pkgs[tool_name]], timeout=360) and self.verify_system_installation(tool_name):
                return True

        if attempted:
            self.log_message.emit("Nenhum gestor de pacotes do Windows conseguiu concluir a instalação.")
        return False

    def _is_wsl_available(self):
        try:
            result = subprocess.run(['wsl', '--status'], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def _run_wsl_shell(self, script, timeout=180):
        try:
            result = subprocess.run(['wsl', 'bash', '-lc', script], capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.log_message.emit("Timeout ao executar comando no WSL")
            return None
        except Exception as exc:
            self.log_message.emit(f"Erro ao executar comando no WSL: {exc}")
            return None

        if result.stdout and result.stdout.strip():
            self.log_message.emit(result.stdout.strip())
        if result.stderr and result.stderr.strip():
            self.log_message.emit(result.stderr.strip())
        return result

    def _detect_wsl_package_manager(self):
        managers = ['apt-get', 'apt', 'dnf', 'yum', 'pacman', 'zypper', 'apk']
        for manager in managers:
            result = self._run_wsl_shell(f"command -v {manager} >/dev/null 2>&1 && echo OK || true", timeout=20)
            if result and 'OK' in (result.stdout or ''):
                return manager
        return None

    def _wsl_prefix_for_privileged_commands(self, manager):
        if manager not in {'apt-get', 'apt', 'dnf', 'yum', 'pacman', 'zypper', 'apk'}:
            return ""
        root_check = self._run_wsl_shell("id -u", timeout=15)
        if root_check and root_check.stdout.strip() == '0':
            return ""
        sudo_check = self._run_wsl_shell("command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1 && echo OK || true", timeout=20)
        if sudo_check and 'OK' in (sudo_check.stdout or ''):
            return "sudo -n "
        return None

    def _install_wsl_native_tool(self, tool_name):
        manager = self._detect_wsl_package_manager()
        if not manager:
            self.log_message.emit("WSL sem gestor de pacotes suportado.")
            return False

        package_name = self._get_linux_package_name(tool_name, manager)
        if not package_name:
            self.log_message.emit(f"{tool_name} não tem pacote mapeado para {manager} no WSL.")
            return False

        prefix = self._wsl_prefix_for_privileged_commands(manager)
        if prefix is None:
            self.log_message.emit("WSL sem permissões para instalar (sudo bloqueado e utilizador não-root).")
            return False

        update_cmd = " ".join(self._get_linux_update_command(manager))
        install_cmd = " ".join(self._get_linux_install_command(manager, package_name))

        self.log_message.emit(f"WSL ({manager}) -> {tool_name}")
        update_result = self._run_wsl_shell(f"{prefix}{update_cmd}", timeout=240)
        if not update_result or update_result.returncode != 0:
            return False

        install_result = self._run_wsl_shell(f"{prefix}{install_cmd}", timeout=300)
        if not install_result or install_result.returncode != 0:
            return False

        return self.verify_wsl_installation(tool_name)

    def _install_wsl_pip_package(self, package_name):
        install_attempts = [
            f"python3 -m pip install --user {package_name}",
            f"pip3 install --user {package_name}",
        ]
        for script in install_attempts:
            result = self._run_wsl_shell(script, timeout=300)
            if result and result.returncode == 0:
                return True
        return False


class InstallationDialog(QDialog):
    def __init__(self, missing_tools, parent=None):
        super().__init__(parent)
        self.missing_tools = missing_tools
        self.selected_tools = missing_tools.copy()
        self.install_methods = {}
        self.setup_ui()

    def _command_exists(self, command_name):
        from shutil import which
        return which(command_name) is not None

    def setup_ui(self):
        self.setWindowTitle("Instalação de Ferramentas Externas")
        self.setMinimumSize(860, 680)
        self.resize(920, 720)

        self.setStyleSheet("""
            QDialog {
                background-color: #0f1728;
            }
            QGroupBox {
                border: 1px solid #233451;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                color: #9eb0ca;
                font-weight: 600;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 4px;
            }
            QLabel {
                color: #b9c8dd;
            }
            QPushButton {
                background-color: #1a2a44;
                color: #d4def0;
                border: 1px solid #2a4468;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #203456;
            }
            QPushButton:disabled {
                background-color: #17243a;
                color: #6f819c;
                border: 1px solid #243752;
            }
            QTextEdit, QComboBox {
                background-color: #111f34;
                color: #d8e2f3;
                border: 1px solid #2a3f5e;
                border-radius: 6px;
            }
            QCheckBox {
                color: #d8e2f3;
                font-weight: 600;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Título
        title = QLabel("Ferramentas Externas Necessárias")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #dce8ff;")
        layout.addWidget(title)

        # Descrição
        desc = QLabel(
            "As seguintes ferramentas de segurança não foram encontradas.\n"
            "Selecione quais deseja instalar e escolha o método de instalação:"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8fa3bf;")
        layout.addWidget(desc)

        # Grupo de ferramentas
        tools_group = QGroupBox("Ferramentas Disponíveis para Instalação")
        tools_layout = QVBoxLayout(tools_group)
        tools_layout.setContentsMargins(10, 14, 10, 10)
        tools_layout.setSpacing(8)

        controls_row = QHBoxLayout()
        self.selection_summary = QLabel("")
        self.selection_summary.setStyleSheet("color: #8fa3bf; font-size: 12px;")

        self.select_all_btn = QPushButton("Selecionar Tudo")
        self.select_all_btn.clicked.connect(self.select_all_tools)
        self.clear_all_btn = QPushButton("Limpar Seleção")
        self.clear_all_btn.clicked.connect(self.clear_all_tools)
        self.select_all_btn.setMinimumHeight(30)
        self.clear_all_btn.setMinimumHeight(30)

        controls_row.addWidget(self.selection_summary)
        controls_row.addStretch()
        controls_row.addWidget(self.select_all_btn)
        controls_row.addWidget(self.clear_all_btn)
        tools_layout.addLayout(controls_row)

        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tools_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        tools_scroll_content = QWidget()
        self.tools_scroll_layout = QVBoxLayout(tools_scroll_content)
        self.tools_scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.tools_scroll_layout.setSpacing(6)
        
        self.tool_widgets = {}
        for tool in sorted(self.missing_tools, key=lambda item: ToolNodeService.get_tool_display_name(item).lower()):
            tool_widget = self.create_tool_widget(tool)
            self.tool_widgets[tool] = tool_widget
            self.tools_scroll_layout.addWidget(tool_widget["widget"])

        self.tools_scroll_layout.addStretch()
        tools_scroll.setWidget(tools_scroll_content)
        tools_layout.addWidget(tools_scroll)
        
        layout.addWidget(tools_group)

        # Área de log
        layout.addWidget(QLabel("Log de Instalação:"))
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(160)
        self.log_text.setPlaceholderText("O progresso da instalação aparece aqui...")
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Botões
        button_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("Instalar Selecionados")
        self.install_btn.clicked.connect(self.start_installation)
        self.install_btn.setMinimumHeight(36)
        
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.cancel_installation)
        self.cancel_btn.setMinimumHeight(36)
        
        self.close_btn = QPushButton("Fechar")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setVisible(False)
        self.close_btn.setMinimumHeight(36)

        button_layout.addWidget(self.install_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        self.update_selection_summary()

    def create_tool_widget(self, tool_name):
        row = QFrame()
        row.setStyleSheet("""
            QFrame {
                background-color: #101d31;
                border: 1px solid #223654;
                border-radius: 6px;
            }
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        checkbox = QCheckBox(ToolNodeService.get_tool_display_name(tool_name))
        checkbox.setChecked(True)
        checkbox.toggled.connect(lambda checked, t=tool_name: self.toggle_tool(t, checked))
        checkbox.setMinimumWidth(260)
        layout.addWidget(checkbox)

        method_label = QLabel("Método:")
        method_label.setStyleSheet("color: #8fa3bf;")
        layout.addWidget(method_label)

        method_combo = QComboBox()
        method_combo.setMinimumWidth(230)
        method_combo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        methods = self.get_available_methods(tool_name)
        for method in methods:
            method_combo.addItem(method['name'], method['value'])
        
        default_method = self.get_default_method(tool_name)
        method_combo.setCurrentText(default_method['name'])
        self.install_methods[tool_name] = default_method['value']
        
        method_combo.currentTextChanged.connect(
            lambda text, t=tool_name: self.update_install_method(t, text)
        )

        layout.addWidget(method_combo)
        layout.addStretch()

        return {
            "widget": row,
            "checkbox": checkbox,
            "method_combo": method_combo,
        }

    def get_available_methods(self, tool_name):
        system = platform.system().lower()
        methods = []
        
        base_methods = [{'name': 'Instalação Nativa', 'value': 'native'}]

        if system == "linux" and self._command_exists('yay'):
            base_methods.append({'name': 'Via AUR (yay)', 'value': 'aur'})

        base_methods.append({'name': 'Instalação Local', 'value': 'local'})
        base_methods.append({'name': 'Via PIP (Python)', 'value': 'python'})
        
        if system == "windows" and self.is_wsl_available():
            base_methods.append({'name': 'Via WSL (Linux)', 'value': 'wsl'})
        
        for method in base_methods:
            if self.is_method_supported(tool_name, method['value']):
                methods.append(method)
        
        return methods

    def get_default_method(self, tool_name):
        system = platform.system().lower()
        
        if system == "linux":
            if tool_name in ['amass', 'steghide', 'enum4linux', 'subfinder'] and self._command_exists('yay'):
                return {'name': 'Via AUR (yay)', 'value': 'aur'}
            if tool_name in ['cupp', 'linpeas', 'patator', 'revshellgen', 'whatweb']:
                return {'name': 'Instalação Local', 'value': 'local'}
            return {'name': 'Instalação Nativa', 'value': 'native'}
        elif system == "windows":
            if tool_name in ['whois']:
                return {'name': 'Via PIP (Python)', 'value': 'python'}
            if self.is_wsl_available():
                return {'name': 'Via WSL (Linux)', 'value': 'wsl'}
            else:
                return {'name': 'Instalação Nativa', 'value': 'native'}
        else:
            return {'name': 'Instalação Nativa', 'value': 'native'}

    def is_method_supported(self, tool_name, method):
        if method == 'aur':
            return tool_name in ['amass', 'steghide', 'enum4linux', 'patator', 'subfinder', 'whatweb']
        if method == 'local':
            return tool_name in ['cupp', 'linpeas', 'patator', 'revshellgen', 'whatweb']
        if method == 'python':
            return tool_name in ['whois']
        return True

    def is_wsl_available(self):
        try:
            result = subprocess.run(['wsl', '--status'], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def toggle_tool(self, tool, enabled):
        if enabled:
            if tool not in self.selected_tools:
                self.selected_tools.append(tool)
        else:
            if tool in self.selected_tools:
                self.selected_tools.remove(tool)
        self.update_selection_summary()

    def select_all_tools(self):
        for tool in self.missing_tools:
            row = self.tool_widgets.get(tool)
            if not row:
                continue
            row["checkbox"].setChecked(True)

    def clear_all_tools(self):
        for tool in self.missing_tools:
            row = self.tool_widgets.get(tool)
            if not row:
                continue
            row["checkbox"].setChecked(False)

    def update_selection_summary(self):
        total = len(self.missing_tools)
        selected = len(self.selected_tools)
        self.selection_summary.setText(f"Selecionadas: {selected} de {total}")

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
            QMessageBox.warning(self, "Instalação Concluída com Ações Pendentes", 
                              f"{message}\n\n"
                              "Pode concluir manualmente as ferramentas pendentes.")

        self.install_btn.setEnabled(True)
        self.cancel_btn.setText("Cancelar")
        self.cancel_btn.setVisible(True)

    def update_progress(self, progress, message):
        self.progress_bar.setValue(progress)
        self.setWindowTitle(f"Instalação - {message}")

    def add_log(self, message):
        self.log_text.append(message)

class ToolsDownloadManager:
    TOOL_KEY_ALIASES = {
        'nslookup': 'dnsutils',
        'searchexploit': 'searchsploit',
        'sublist3r': 'subfinder',
    }

    TOOL_ALIASES = {
        'dnsutils': ['nslookup', 'dig', 'host'],
        'nslookup': ['nslookup', 'dig', 'host'],
        'subfinder': ['subfinder'],
        'amass': ['amass'],
        'whois': ['whois'],
        'nmap': ['nmap'],
        'exiftool': ['exiftool', 'exif'],
        'gobuster': ['gobuster'],
        'masscan': ['masscan'],
        'binwalk': ['binwalk'],
        'cupp': ['cupp'],
        'enum4linux': ['enum4linux'],
        'ghidra': ['ghidra'],
        'hashcat': ['hashcat'],
        'hydra': ['hydra'],
        'john': ['john'],
        'linpeas': ['linpeas'],
        'netcat': ['nc', 'netcat', 'ncat'],
        'patator': ['patator'],
        'revshellgen': ['revshellgen'],
        'rpcclient': ['rpcclient'],
        'searchsploit': ['searchsploit'],
        'sqlmap': ['sqlmap'],
        'steghide': ['steghide'],
        'strings': ['strings'],
        'tshark': ['tshark'],
        'whatweb': ['whatweb'],
        'wifite': ['wifite'],
    }

    def __init__(self, main_window):
        self.main_window = main_window
        self.tools_dir = Path(__file__).parent.parent / "downloaded_tools"
        self.tools_dir.mkdir(parents=True, exist_ok=True)
        self.repo_root = Path(__file__).resolve().parents[2]

    def normalize_tool_name(self, tool_name):
        key = str(tool_name or "").strip().lower()
        return self.TOOL_KEY_ALIASES.get(key, key)

    def tool_aliases(self, tool_name):
        normalized = self.normalize_tool_name(tool_name)
        aliases = self.TOOL_ALIASES.get(normalized)
        if aliases:
            return aliases
        return [normalized]

    def check_missing_tools(self):
        required_tools = ToolNodeService.list_tool_names(include_hidden=False)
        missing_tools = []

        for tool in required_tools:
            if not self.is_tool_available(tool):
                missing_tools.append(tool)

        return missing_tools

    def is_tool_available(self, tool_name):
        tool_name = self.normalize_tool_name(tool_name)

        for alias in self.tool_aliases(tool_name):
            if shutil.which(alias):
                return True
        
        if tool_name == 'whois':
            try:
                import whois
                return True
            except ImportError:
                pass
        
        # Se estiver no Windows, verifica no WSL também
        if platform.system() == "Windows":
            if self.check_tool_in_wsl(tool_name):
                return True
        
        return False

    def check_tool_in_wsl(self, tool_name):
        try:
            tool_name = self.normalize_tool_name(tool_name)
            alias_checks = " || ".join([f"command -v {alias}" for alias in self.tool_aliases(tool_name)])
            cmd = ['wsl', 'bash', '-lc', alias_checks]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
        except Exception:
            return False

    def check_downloaded_tools(self, tool_name):
        tool_name = self.normalize_tool_name(tool_name)
        tool_paths = {
            'nmap': self.tools_dir / 'nmap' / 'nmap.exe',
            'exiftool': self.tools_dir / 'exiftool' / 'exiftool.exe',
            'gobuster': self.tools_dir / 'gobuster' / 'gobuster.exe'
        }

        if tool_name in tool_paths:
            return tool_paths[tool_name].exists()
        return False

    def get_tool_path(self, tool_name):
        tool_name = self.normalize_tool_name(tool_name)

        if tool_name == 'dnsutils':
            for candidate in ['nslookup', 'dig', 'host']:
                candidate_path = shutil.which(candidate)
                if candidate_path:
                    return candidate_path

        if tool_name == 'whois':
            if self.check_python_module('whois'):
                return self.create_python_whois_wrapper()
            return shutil.which('whois')

        for alias in self.tool_aliases(tool_name):
            path = shutil.which(alias)
            if path:
                return path

        if platform.system() == "Windows" and self.check_tool_in_wsl(tool_name):
            preferred_alias = self.tool_aliases(tool_name)[0]
            return f'wsl {preferred_alias}'

        downloaded_paths = {
            'nmap': self.tools_dir / 'nmap' / 'nmap.exe',
            'exiftool': self.tools_dir / 'exiftool' / 'exiftool.exe',
            'gobuster': self.tools_dir / 'gobuster' / 'gobuster.exe',
            'masscan': self.tools_dir / 'masscan' / 'masscan.exe'
        }

        downloaded_path = downloaded_paths.get(tool_name)
        if downloaded_path and downloaded_path.exists():
            return str(downloaded_path)

        return None

    def check_python_module(self, module_name):
        try:
            if module_name == 'whois':
                import whois
                return True
        except ImportError:
            return False
        return False

    def create_python_whois_wrapper(self):
        wrapper_path = self.tools_dir / "whois_wrapper.py"
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        
        wrapper_code = (
            "#!/usr/bin/env python3\n"
            "import whois\n"
            "import sys\n\n"
            "if len(sys.argv) > 1:\n"
            "    domain = sys.argv[1]\n"
            "    try:\n"
            "        w = whois.whois(domain)\n"
            "        print(w)\n"
            "    except Exception as e:\n"
            "        print(f\"Error: {e}\")\n"
            "else:\n"
            "    print(\"Usage: whois_wrapper.py <domain>\")\n"
        )
        
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
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper_code = (
            "#!/usr/bin/env python3\n"
            "import whois\n"
            "import sys\n\n"
            "if len(sys.argv) > 1:\n"
            "    domain = sys.argv[1]\n"
            "    try:\n"
            "        w = whois.whois(domain)\n"
            "        print(w)\n"
            "    except Exception as e:\n"
            "        print(f\"Error: {e}\")\n"
            "else:\n"
            "    print(\"Usage: whois_wrapper.py <domain>\")\n"
        )
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
