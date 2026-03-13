import subprocess
import platform
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QLineEdit, QGroupBox, 
                             QMessageBox, QProgressBar, QSplitter, QFrame, QScrollArea)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QPalette, QColor
from tools.wsl_handler import WSLHandler
from tools.tools_output_parser import ToolsOutputParser
from tools.tools_downloader import ToolsDownloadManager

class CommandThread(QThread):
    output_received = pyqtSignal(str)
    command_finished = pyqtSignal(int)
    error_occurred = pyqtSignal(str)

    def __init__(self, command, working_dir=None, use_wsl=False):
        super().__init__()
        self.command = command
        self.working_dir = working_dir
        self.use_wsl = use_wsl

    def run(self):
        try:
            if self.use_wsl and WSLHandler.is_wsl_available():
                self.output_received.emit("Executing via WSL...\n")
                process = WSLHandler.execute_via_wsl(self.command, self.working_dir)
            else:
                if platform.system() == "Windows":
                    shell_cmd = ["cmd", "/c"] + self.command
                else:
                    shell_cmd = ["/bin/bash", "-c"] + [" ".join(self.command)]

                self.output_received.emit(f"Executing: {' '.join(self.command)}\n")
                self.output_received.emit("-" * 50 + "\n")

                process = subprocess.Popen(
                    shell_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    cwd=self.working_dir,
                    bufsize=1,
                    universal_newlines=True
                )

            while True:
                output = process.stdout.readline()
                if output:
                    self.output_received.emit(output)
                elif process.poll() is not None:
                    break

            remaining_output = process.communicate()[0]
            if remaining_output:
                self.output_received.emit(remaining_output)

            exit_code = process.poll()
            self.command_finished.emit(exit_code)

        except Exception as e:
            self.error_occurred.emit(f"Error executing command: {str(e)}")

class ToolsManager(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.current_command_thread = None
        self.output_parser = ToolsOutputParser(main_window.graph_manager)
        self.download_manager = ToolsDownloadManager(main_window)
        self.available_tools = {}
        
        self.setup_ui()
        self.check_and_request_tools()

    def setup_ui(self):
        self.setObjectName("ToolsManagerPanel")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 10, 0, 0)
        main_layout.setSpacing(10)

        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.NoFrame)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 2px;
                padding: 0px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("External Tools")
        title.setFont(QFont("Consolas", 9, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #9fb0c8;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Execute security tools directly from the application")
        subtitle.setFont(QFont("Consolas", 7))
        subtitle.setStyleSheet("color: #6f809a;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header_frame)

        tools_group = QGroupBox("Available Tools")
        tools_group.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        tools_group.setStyleSheet("""
            QGroupBox {
                color: #7f90aa;
                border: 1px solid #1f2d40;
                border-radius: 2px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: #0f1928;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
            }
        """)
        
        tools_layout = QVBoxLayout(tools_group)
        tools_layout.setSpacing(4)
        tools_layout.setContentsMargins(6, 12, 6, 6)

        self.exiftool_btn = self.create_tool_button("ExifTool", "Extract metadata from files")
        self.gobuster_btn = self.create_tool_button("Gobuster", "Directory/file busting")
        self.nmap_btn = self.create_tool_button("Nmap", "Network discovery")
        self.masscan_btn = self.create_tool_button("Masscan", "Fast port scanner")
        self.nslookup_btn = self.create_tool_button("NSLookup/Dig", "DNS queries")
        self.sublist3r_btn = self.create_tool_button("Sublist3r", "Subdomain enumeration")
        self.whois_btn = self.create_tool_button("Whois", "Domain information")

        tools_layout.addWidget(self.exiftool_btn)
        tools_layout.addWidget(self.gobuster_btn)
        tools_layout.addWidget(self.nmap_btn)
        tools_layout.addWidget(self.masscan_btn)
        tools_layout.addWidget(self.nslookup_btn)
        tools_layout.addWidget(self.sublist3r_btn)
        tools_layout.addWidget(self.whois_btn)

        main_layout.addWidget(tools_group)

        command_group = QGroupBox("Command Configuration")
        command_group.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        command_group.setStyleSheet("""
            QGroupBox {
                color: #7f90aa;
                border: 1px solid #1f2d40;
                border-radius: 2px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: #0f1928;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
            }
        """)
        
        command_layout = QVBoxLayout(command_group)
        command_layout.setSpacing(6)
        command_layout.setContentsMargins(6, 12, 6, 6)

        target_layout = QHBoxLayout()
        target_label = QLabel("Target:")
        target_label.setFont(QFont("Consolas", 8))
        target_label.setStyleSheet("color: #91a1b8; min-width: 60px;")
        target_layout.addWidget(target_label)
        
        self.target_input = QLineEdit()
        self.target_input.setFont(QFont("Consolas", 8))
        self.target_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a2435;
                border: 1px solid #2d3d55;
                border-radius: 2px;
                padding: 4px 6px;
                color: #d2ddec;
                selection-background-color: #355a82;
            }
            QLineEdit:focus {
                border: 1px solid #4e79ab;
            }
        """)
        self.target_input.setPlaceholderText("Enter target...")
        target_layout.addWidget(self.target_input)
        command_layout.addLayout(target_layout)

        options_layout = QHBoxLayout()
        options_label = QLabel("Options:")
        options_label.setFont(QFont("Consolas", 8))
        options_label.setStyleSheet("color: #91a1b8; min-width: 60px;")
        options_layout.addWidget(options_label)
        
        self.options_input = QLineEdit()
        self.options_input.setFont(QFont("Consolas", 8))
        self.options_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a2435;
                border: 1px solid #2d3d55;
                border-radius: 2px;
                padding: 4px 6px;
                color: #d2ddec;
                selection-background-color: #355a82;
            }
            QLineEdit:focus {
                border: 1px solid #4e79ab;
            }
        """)
        self.options_input.setPlaceholderText("e.g., -p 80,443")
        options_layout.addWidget(self.options_input)
        command_layout.addLayout(options_layout)

        custom_layout = QHBoxLayout()
        custom_label = QLabel("Custom:")
        custom_label.setFont(QFont("Consolas", 8))
        custom_label.setStyleSheet("color: #91a1b8; min-width: 60px;")
        custom_layout.addWidget(custom_label)
        
        self.custom_input = QLineEdit()
        self.custom_input.setFont(QFont("Consolas", 8))
        self.custom_input.setStyleSheet("""
            QLineEdit {
                background-color: #1a2435;
                border: 1px solid #2d3d55;
                border-radius: 2px;
                padding: 4px 6px;
                color: #d2ddec;
                selection-background-color: #355a82;
            }
            QLineEdit:focus {
                border: 1px solid #4e79ab;
            }
        """)
        self.custom_input.setPlaceholderText("Custom command...")
        custom_layout.addWidget(self.custom_input)
        command_layout.addLayout(custom_layout)

        main_layout.addWidget(command_group)

        controls_frame = QFrame()
        controls_frame.setFrameStyle(QFrame.Shape.NoFrame)
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        self.execute_btn = QPushButton("Execute")
        self.execute_btn.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #1d3528;
                color: #75d39e;
                border: 1px solid #2f6c4f;
                border-radius: 2px;
                padding: 6px 12px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #24432f;
            }
            QPushButton:pressed {
                background-color: #1b3226;
            }
            QPushButton:disabled {
                background-color: #182437;
                color: #60748d;
                border: 1px solid #2a3a51;
            }
        """)
        self.execute_btn.clicked.connect(self.execute_current_command)
        self.execute_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFont(QFont("Consolas", 8))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b242e;
                color: #f0aab8;
                border: 1px solid #6b3748;
                border-radius: 2px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #522d3a;
            }
            QPushButton:pressed {
                background-color: #3f2530;
            }
            QPushButton:disabled {
                background-color: #182437;
                color: #60748d;
                border: 1px solid #2a3a51;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_current_command)
        self.stop_btn.setEnabled(False)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFont(QFont("Consolas", 8))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #202d42;
                color: #c8d1e0;
                border: 1px solid #33465f;
                border-radius: 2px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #27374f;
            }
            QPushButton:pressed {
                background-color: #2a3e5c;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_output)

        controls_layout.addWidget(self.execute_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addStretch()

        main_layout.addWidget(controls_frame)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #2d3d55;
                border-radius: 2px;
                text-align: center;
                background-color: #1a2435;
                color: #c8d1e0;
                height: 4px;
            }
            QProgressBar::chunk {
                background-color: #4e79ab;
                border-radius: 2px;
            }
        """)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFont(QFont("Consolas", 7))
        main_layout.addWidget(self.progress_bar)

        output_group = QGroupBox("Command Output")
        output_group.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        output_group.setStyleSheet("""
            QGroupBox {
                color: #7f90aa;
                border: 1px solid #273347;
                border-radius: 2px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: #111b2b;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
            }
        """)
        
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(6, 12, 6, 6)
        
        self.output_text = QTextEdit()
        self.output_text.setFont(QFont("Consolas", 8))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #121b2a;
                border: 1px solid #2d3d55;
                border-radius: 2px;
                color: #cbd7e8;
                padding: 6px;
                selection-background-color: #355a82;
            }
        """)
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(90)
        self.output_text.setMaximumHeight(170)
        output_layout.addWidget(self.output_text)

        main_layout.addWidget(output_group)

        self.connect_tool_buttons()

    def create_tool_button(self, name, description):
        btn = QPushButton()
        btn.setProperty('tool_name', name.lower())
        btn.setMinimumHeight(38)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #c2d0e3;
                border: 1px solid transparent;
                border-left: 1px solid #2a3b50;
                border-radius: 0px;
                text-align: left;
                padding: 3px 8px;
            }}
            QPushButton:hover {{
                background-color: #132033;
                border: 1px solid transparent;
                border-left: 1px solid #4c6f99;
            }}
            QPushButton:pressed {{
                background-color: #17253a;
            }}
        """)
        
        layout = QVBoxLayout(btn)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)
        
        name_label = QLabel(name)
        name_label.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        name_label.setStyleSheet("color: #c2d0e3;")
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Consolas", 7))
        desc_label.setStyleSheet("color: #7387a4;")
        
        layout.addWidget(name_label)
        layout.addWidget(desc_label)
        
        return btn

    def connect_tool_buttons(self):
        self.exiftool_btn.clicked.connect(lambda: self.select_tool('exiftool'))
        self.gobuster_btn.clicked.connect(lambda: self.select_tool('gobuster'))
        self.nmap_btn.clicked.connect(lambda: self.select_tool('nmap'))
        self.masscan_btn.clicked.connect(lambda: self.select_tool('masscan'))
        self.nslookup_btn.clicked.connect(lambda: self.select_tool('nslookup'))
        self.sublist3r_btn.clicked.connect(lambda: self.select_tool('sublist3r'))
        self.whois_btn.clicked.connect(lambda: self.select_tool('whois'))

    def update_tool_availability(self, tool_name, is_available):
        button_mapping = {
            'exiftool': self.exiftool_btn,
            'gobuster': self.gobuster_btn,
            'nmap': self.nmap_btn,
            'masscan': self.masscan_btn, 
            'nslookup': self.nslookup_btn,
            'sublist3r': self.sublist3r_btn,
            'whois': self.whois_btn
        }
        
        button = button_mapping.get(tool_name)
        if button:
            if is_available:
                button.setEnabled(True)
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: #c2d0e3;
                        border: 1px solid transparent;
                        border-left: 1px solid #2a3b50;
                        border-radius: 0px;
                        text-align: left;
                        padding: 3px 8px;
                    }}
                    QPushButton:hover {{
                        background-color: #132033;
                        border: 1px solid transparent;
                        border-left: 1px solid #4c6f99;
                    }}
                    QPushButton:pressed {{
                        background-color: #17253a;
                    }}
                """)
                button.setToolTip("")
            else:
                button.setEnabled(False)
                button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #5d6f86;
                        border: 1px solid transparent;
                        border-left: 1px solid #243247;
                        border-radius: 0px;
                        text-align: left;
                        padding: 3px 8px;
                    }
                """)
                button.setToolTip(f"{tool_name.capitalize()} não encontrado. Clique em 'Manage Tools' para instalar.")

    def check_and_request_tools(self):
        self.check_available_tools()

    def check_available_tools(self):
        tools_to_check = ['exiftool', 'gobuster', 'nmap', 'masscan', 'nslookup', 'sublist3r', 'whois']
        
        for tool_name in tools_to_check:
            is_available = self.download_manager.is_tool_available(tool_name)
            self.available_tools[tool_name] = is_available
            self.update_tool_availability(tool_name, is_available)

    def check_tool_availability(self, tool_name):
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['where', tool_name], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', tool_name], capture_output=True, text=True)
            
            return result.returncode == 0
        except Exception:
            return False

    def get_command_for_tool(self, tool_name, target, options):
        try:
            if platform.system() == "Windows" and tool_name in ['masscan', 'nmap', 'gobuster', 'exiftool']:
                # Verifica se está disponível no WSL
                if self.download_manager.check_tool_in_wsl(tool_name):
                    tool_path = f'wsl {tool_name}'
                else:
                    raise Exception(f"Ferramenta {tool_name} não disponível nem no WSL.")
            else:
                tool_path = self.download_manager.get_tool_path(tool_name)
            
            if not tool_path:
                raise Exception(f"Ferramenta {tool_name} não disponível. Instale via 'Manage Tools'.")
            
            if tool_name == 'sublist3r' and '-m' in tool_path:
                base_parts = tool_path.split()
            else:
                base_parts = [tool_path]
            
            base_commands = {
                'exiftool': base_parts + [target] + (options.split() if options else []),
                'gobuster': self.get_gobuster_command(target, options, tool_path),
                'nmap': base_parts + (options.split() if options else ['-sV', '-sC']) + [target],
                'masscan': self.get_masscan_command(target, options, tool_path),
                'nslookup': base_parts + [target] + (options.split() if options else []),
                'sublist3r': base_parts + ['-d', target] + (options.split() if options else []),
                'whois': base_parts + [target] + (options.split() if options else [])
            }
            
            return base_commands.get(tool_name, [])
            
        except Exception as e:
            QMessageBox.warning(self, "Erro de Ferramenta", f"Erro ao preparar {tool_name}: {str(e)}")
            # Certifique-se que tool_name está correto aqui
            return []

    def get_masscan_command(self, target, options, tool_path):
        # Se estiver usando WSL, adicione sudo
        if tool_path.startswith('wsl '):
            # Remove 'wsl ' do início e adiciona sudo
            base_cmd = ['wsl', 'sudo', tool_path[4:]]  # tool_path[4:] remove 'wsl '
        else:
            base_cmd = [tool_path]
        
        default_options = [
            '--rate', '1000000',
            '--open-only',
            '-oL', '-'
        ]
        
        if '/' in target:
            base_cmd += ['-p0-65535', target]
        else:
            base_cmd += ['-p0-65535', target]
        
        if options:
            user_options = options.split()
            return base_cmd + user_options
        
        return base_cmd + default_options

    def select_tool(self, tool_name):
        self.current_tool = tool_name
        self.target_input.clear()
        self.options_input.clear()
        self.custom_input.clear()
        
        placeholders = {
            'exiftool': "Enter file path...",
            'gobuster': "Enter target URL...", 
            'nmap': "Enter IP/hostname...",
            'masscan': "Enter IP/CIDR...", 
            'nslookup': "Enter domain...",
            'sublist3r': "Enter domain...",
            'whois': "Enter domain..."
        }
        
        self.target_input.setPlaceholderText(placeholders.get(tool_name, "Enter target..."))
        self.execute_btn.setEnabled(True)
        
        self.output_text.append(f"> Selected tool: {tool_name}")

    def setup_gobuster_wordlist(self):
        try:
            if platform.system() != "Windows":
                return "/usr/share/dirb/wordlists/common.txt"
                
            wsl_home_path = "/home/wordlist"
            wsl_wordlist_path = f"{wsl_home_path}/wordlist.txt"
            
            check_dir_cmd = ['wsl', 'test', '-d', wsl_home_path, '&&', 'echo', 'EXISTS']
            result = subprocess.run(check_dir_cmd, capture_output=True, text=True, timeout=10)
            
            if 'EXISTS' not in result.stdout:
                create_dir_cmd = ['wsl', 'mkdir', '-p', wsl_home_path]
                subprocess.run(create_dir_cmd, capture_output=True, timeout=10)
                print(f"Created directory: {wsl_home_path}")
            
            check_file_cmd = ['wsl', 'test', '-f', wsl_wordlist_path, '&&', 'echo', 'EXISTS']
            result = subprocess.run(check_file_cmd, capture_output=True, text=True, timeout=10)
            
            if 'EXISTS' not in result.stdout:
                default_wordlist = """admin
    api
    backup
    config
    database
    doc
    docs
    documentation
    files
    images
    img
    js
    css
    static
    uploads
    download
    downloads
    login
    logout
    register
    signin
    signout
    signup
    user
    users
    profile
    account
    panel
    adminpanel
    wp-admin
    wp-content
    wp-includes
    phpmyadmin
    server-status
    .htaccess
    .htpasswd
    robots.txt
    sitemap.xml
    web.config
    index.php
    index.html
    test
    dev
    development
    staging
    production
    backoffice
    dashboard
    cpanel
    webmail
    ftp
    ssh
    telnet
    """
                
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_wordlist = os.path.join(temp_dir, "temp_wordlist.txt")
                
                with open(temp_wordlist, 'w', encoding='utf-8') as f:
                    f.write(default_wordlist)

                drive_letter = temp_dir[0].lower()
                wsl_temp_path = temp_dir[2:].replace('\\', '/')
                wsl_full_path = f"/mnt/{drive_letter}{wsl_temp_path}/temp_wordlist.txt"

                copy_cmd = ['wsl', 'cp', wsl_full_path, wsl_wordlist_path]
                result = subprocess.run(copy_cmd, capture_output=True, text=True, timeout=10)
                
                os.remove(temp_wordlist)
                
                if result.returncode == 0:
                    print(f"Created default wordlist: {wsl_wordlist_path}")
                else:
                    print(f"Failed to copy wordlist: {result.stderr}")
                    return "/usr/share/dirb/wordlists/common.txt"
            
            return wsl_wordlist_path
            
        except Exception as e:
            print(f"Error setting up Gobuster wordlist: {e}")
            return "/usr/share/dirb/wordlists/common.txt"

    def get_gobuster_command(self, target, options, tool_path):
        base_cmd = [tool_path, 'dir', '-u', target]
        
        fast_settings = [
            '--timeout', '5s',
            '-t', '15',
            '-r',
            '--no-error',
            '-k',
        ]
        
        if options:
            user_options = options.split()
            if '-k' not in user_options and '--no-tls-validation' not in user_options:
                user_options.append('-k')
            return base_cmd + user_options
        
        wordlist_path = self.setup_gobuster_wordlist()
        
        return base_cmd + fast_settings + [
            '-w', wordlist_path,
            '-x', 'php,html',
        ]

    def execute_current_command(self):
        if not hasattr(self, 'current_tool'):
            QMessageBox.warning(self, "No Tool Selected", "Please select a tool first.")
            return

        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "No Target", "Please enter a target.")
            return

        reply = QMessageBox.question(
            self, 
            "Execute Command", 
            f"This will execute a system command. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return

        custom_cmd = self.custom_input.text().strip()
        if custom_cmd:
            command_parts = custom_cmd.split()
        else:
            options = self.options_input.text().strip()
            command_parts = self.get_command_for_tool(self.current_tool, target, options)

        if not command_parts:
            QMessageBox.warning(self, "Invalid Command", "Could not generate command.")
            return

        self.execute_command(command_parts)
        
    def execute_command(self, command_parts):
        if self.current_command_thread and self.current_command_thread.isRunning():
            QMessageBox.warning(self, "Command Running", "Please wait for the current command to finish.")
            return

        if not command_parts:
            QMessageBox.warning(self, "Invalid Command", "Command is empty.")
            return
        
        use_wsl = False
        tool_name = getattr(self, 'current_tool', None)
        
        if (platform.system() == "Windows" and 
            tool_name in ['sublist3r', 'whois', 'nmap', 'gobuster'] and
            self.should_use_wsl(tool_name)):
            
            use_wsl = True
            command_parts = self.convert_to_wsl_command(command_parts, tool_name)

        self.output_text.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.execute_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.current_command_thread = CommandThread(command_parts, use_wsl=use_wsl)
        self.current_command_thread.output_received.connect(self.on_output_received)
        self.current_command_thread.command_finished.connect(self.on_command_finished)
        self.current_command_thread.error_occurred.connect(self.on_command_error)
        self.current_command_thread.start()

    def should_use_wsl(self, tool_name):
        if self.download_manager.is_tool_available(tool_name):
            return False
        
        try:
            result = subprocess.run(['wsl', '--status'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def convert_to_wsl_command(self, command_parts, tool_name):
        if tool_name in ['sublist3r']:
            return ['wsl', 'python3', '-m', 'sublist3r'] + command_parts[1:]
        
        return ['wsl'] + command_parts

    def fix_wsl_dns_for_gobuster(self, command_parts):
        try:
            url_index = command_parts.index('-u') + 1 if '-u' in command_parts else -1
            if url_index > 0 and url_index < len(command_parts):
                url = command_parts[url_index]

                import socket
                try:
                    ip_address = socket.gethostbyname(url.replace('https://', '').replace('http://', '').split('/')[0])
                    self.output_text.append(f"Resolved {url} to {ip_address} using Windows DNS")

                    command_parts[url_index] = url.replace(
                        url.replace('https://', '').replace('http://', '').split('/')[0], 
                        ip_address
                    )

                    if '--add-header' not in command_parts and '-H' not in command_parts:
                        original_host = url.replace('https://', '').replace('http://', '').split('/')[0]
                        command_parts.extend(['-H', f'Host: {original_host}'])
                        
                except socket.gaierror:
                    self.output_text.append(f"Warning: Could not resolve {url} using Windows DNS")
                    
        except Exception as e:
            self.output_text.append(f"DNS fix error: {str(e)}")
        
        return command_parts

    def stop_current_command(self):
        if self.current_command_thread and self.current_command_thread.isRunning():
            self.current_command_thread.terminate()
            self.current_command_thread.wait()
            self.output_text.append("\n*** Command execution stopped by user ***\n")
            self.on_command_finished(-1)

    def on_output_received(self, output):
        self.output_text.insertPlainText(output)
        self.output_text.ensureCursorVisible()

    def on_command_finished(self, exit_code):
        self.progress_bar.setVisible(False)
        self.execute_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if exit_code == 0 and hasattr(self, 'current_tool'):
            output_text = self.output_text.toPlainText()
            target = self.target_input.text().strip()
            
            try:
                created_nodes = self.output_parser.parse_tool_output(
                    self.current_tool, output_text, target
                )
                
                if created_nodes:
                    self.output_text.append(f"\n*** Created {len(created_nodes)} nodes automatically ***")
                    
                    if self.main_window:
                        for node in created_nodes:
                            self.main_window.create_node_visual(node)
                else:
                    self.output_text.append("\n*** No nodes created from output ***")
                    
            except Exception as e:
                self.output_text.append(f"\n*** Error parsing output: {str(e)} ***")
        
        elif exit_code == 0:
            self.output_text.append("\n*** Command completed successfully ***")
        else:
            self.output_text.append(f"\n*** Command finished with exit code: {exit_code} ***")

    def on_command_error(self, error_message):
        self.output_text.append(f"\n*** ERROR: {error_message} ***")
        self.on_command_finished(-1)

    def clear_output(self):
        self.output_text.clear()

    def check_tool_availability(self, tool_name):
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['where', tool_name], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', tool_name], capture_output=True, text=True)
            
            return result.returncode == 0
        except Exception:
            return False
