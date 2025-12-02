import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTextEdit, QLabel, QProgressBar, QMessageBox, 
                            QDialog, QFileDialog, QLineEdit)
from PyQt6.QtCore import QThread, pyqtSignal
from agent.attack_dialog import AttackDialog

class DockerEnvironmentGenerator:
    def __init__(self, sandbox_data: Dict[str, Any], project_path: Path):
        self.sandbox_data = sandbox_data
        self.base_path = project_path
        
    def validate_docker_installation(self) -> bool:
        try:
            result = subprocess.run(["docker", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                result = subprocess.run(["docker", "info"], 
                                      capture_output=True, text=True)
                return result.returncode == 0
            return False
        except FileNotFoundError:
            return False
    
    def validate_sandbox_data(self) -> tuple[bool, List[str]]:
        missing_info = []

        if 'objects' not in self.sandbox_data:
            missing_info.append("Estrutura de objetos não encontrada")
            return False, missing_info
        
        objects = self.sandbox_data['objects']
        
        backend_objects = [obj for obj in objects if obj.get('type') in ['flask', 'django', 'web_app', 'code_file']]
        if not backend_objects:
            missing_info.append("Nenhum backend (Flask/Django) encontrado no mapa mental")
        
        db_objects = [obj for obj in objects if obj.get('type') in ['postgresql', 'mysql', 'mongodb', 'database']]
        if not db_objects:
            missing_info.append("Nenhuma base de dados encontrada no mapa mental")
        
        return len(missing_info) == 0, missing_info
    
    def _get_backend_dependencies(self, backend_obj: Dict) -> List[str]:
        dependencies = []
        
        if backend_obj.get('code_content') and backend_obj['code_content'].get('dependencies'):
            deps = backend_obj['code_content']['dependencies']
            if isinstance(deps, list):
                dependencies.extend(deps)
            elif isinstance(deps, str):
                for dep in deps.split(','):
                    dep = dep.strip()
                    if dep:
                        if dep == 'psycopg2':
                            dep = 'psycopg2-binary'
                        elif dep == 'datatime':
                            dep = ''
                        dependencies.append(dep)
        
        python_stdlib = {'json', 'datetime', 'functools', 'os', 'sys', 'pathlib', 
                        'typing', 'collections', 're', 'math', 'random', 'time'}
        
        filtered_deps = []
        for dep in dependencies:
            if dep and dep not in python_stdlib:
                if ' ' not in dep and ',' not in dep:
                    filtered_deps.append(dep)
        
        return filtered_deps

    def _generate_requirements(self):
        dependencies = set()
        
        base_dependencies = {
            'flask',
            'psycopg2-binary', 
            'python-dotenv',
            'gunicorn',
            'werkzeug',
            'jinja2',
            'bcrypt'
        }
        dependencies.update(base_dependencies)
        
        for obj in self.sandbox_data['objects']:
            if obj.get('type') in ['flask', 'django', 'web_app', 'code_file']:
                deps = self._get_backend_dependencies(obj)
                for dep in deps:
                    if (dep and 
                        ' ' not in dep and 
                        ',' not in dep and
                        not dep.startswith('.')):
                        dependencies.add(dep)
        
        problematic_deps = {
            'models',
            'os, datatime',
            'flask, psycopg2, datatime, json, functools'
        }
        dependencies = dependencies - problematic_deps
        
        requirements_content = "\n".join(sorted(dependencies)) + "\n"
        
        with open(self.base_path / "requirements.txt", "w") as f:
            f.write(requirements_content)
        print("requirements.txt gerado")
        print(f"  Dependências: {', '.join(sorted(dependencies))}")
    
    def generate_project_structure(self):
        print(f"Gerando projeto em: {self.base_path}")

        if self.base_path.exists():
            import shutil
            shutil.rmtree(self.base_path)
        
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self._generate_dockerfile()
        self._generate_docker_compose()
        self._generate_requirements()
        self._generate_code_files()
        self._generate_database_init()
        
        print(f"Estrutura gerada com sucesso em: {self.base_path}")
        return str(self.base_path)
    
    def _generate_dockerfile(self):
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \\
    postgresql-client \\
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretório para logs
RUN mkdir -p /app/logs

# Expor porta
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "app.py"]
"""
        
        with open(self.base_path / "Dockerfile", "w") as f:
            f.write(dockerfile_content)
        print("Dockerfile gerado")
    
    def _generate_docker_compose(self):
        compose_content = """version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:admin123@db:5432/social_notes
      - SECRET_KEY=your-secret-key-change-in-production
    depends_on:
      - db
    volumes:
      - .:/app
    command: python app.py
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=social_notes
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=admin123
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@socialnotes.com
      - PGADMIN_DEFAULT_PASSWORD=admin123
    ports:
      - "5050:80"
    depends_on:
      - db
    restart: unless-stopped

volumes:
  postgres_data:
"""
        
        with open(self.base_path / "docker-compose.yml", "w") as f:
            f.write(compose_content)
        print("docker-compose.yml gerado")
    
    def _generate_code_files(self):
        templates_dir = self.base_path / "templates"
        static_dir = self.base_path / "static"
        css_dir = static_dir / "css"
        js_dir = static_dir / "js"
        
        templates_dir.mkdir(parents=True, exist_ok=True)
        css_dir.mkdir(parents=True, exist_ok=True)
        js_dir.mkdir(parents=True, exist_ok=True)
        
        for obj in self.sandbox_data['objects']:
            if obj.get('type') == 'code_file' and obj.get('code_content'):
                code_content = obj['code_content']
                filename = obj.get('name')
                
                if filename:
                    if filename.endswith('.html'):
                        file_path = templates_dir / filename
                    elif filename.endswith('.css'):
                        file_path = css_dir / filename
                    elif filename.endswith('.js'):
                        file_path = js_dir / filename
                    else:
                        file_path = self.base_path / filename

                    source_code = code_content.get('source_code', '')
                    if source_code:
                        with open(file_path, "w", encoding='utf-8') as f:
                            f.write(source_code)
                        print(f"Ficheiro gerado: {filename}")
    
    def _generate_database_init(self):
        init_sql = """-- Execução automática quando o container do PostgreSQL iniciar
-- Garante que o banco de dados social_notes existe
SELECT 'CREATE DATABASE social_notes'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'social_notes')\\gexec
"""
        
        with open(self.base_path / "init.sql", "w") as f:
            f.write(init_sql)
        print("init.sql gerado")
    
    def start_environment(self) -> bool:
        try:
            original_dir = os.getcwd()
            os.chdir(self.base_path)
            
            print("Construindo e iniciando containers Docker...")
            
            result = subprocess.run(["docker-compose", "--version"], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                print("docker-compose não encontrado, tentando com docker compose...")
                result = subprocess.run(["docker", "compose", "up", "-d", "--build"], 
                                      capture_output=True, text=True)
            else:
                result = subprocess.run(["docker-compose", "up", "-d", "--build"], 
                                      capture_output=True, text=True)
            
            os.chdir(original_dir)
            
            if result.returncode == 0:
                print("Ambiente Docker iniciado com sucesso")
                return True
            else:
                print(f"Erro ao iniciar ambiente: {result.stderr}")
                self._diagnose_docker_issue()
                return False
                
        except Exception as e:
            print(f"Erro: {e}")
            return False
    
    def _diagnose_docker_issue(self):
        try:
            print("Executando diagnóstico Docker...")
            
            result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
            if result.returncode != 0:
                print("Docker daemon não está em execução")
                return
            
            result = subprocess.run(["docker", "system", "df"], capture_output=True, text=True)
            print("Status do Docker:")
            print(result.stdout)
            
        except Exception as e:
            print(f"Erro no diagnóstico: {e}")

class DockerAutomationThread(QThread):
    progress_updated = pyqtSignal(str)
    finished_success = pyqtSignal(str)
    finished_error = pyqtSignal(str)
    
    def __init__(self, sandbox_data: Dict[str, Any], project_path: Path):
        super().__init__()
        self.sandbox_data = sandbox_data
        self.project_path = project_path
        self.generator = DockerEnvironmentGenerator(sandbox_data, project_path)
    
    def run(self):
        try:
            # Verificar Docker
            self.progress_updated.emit("Verificando instalação do Docker...")
            if not self.generator.validate_docker_installation():
                self.finished_error.emit(
                    "Docker Desktop não encontrado ou não está em execução.\n\n"
                    "Por favor:\n"
                    "1. Instale o Docker Desktop a partir de https://www.docker.com/products/docker-desktop/\n"
                    "2. Certifique-se de que o Docker Desktop está em execução\n"
                    "3. Tente novamente"
                )
                return
            
            # Validar dados
            self.progress_updated.emit("Validando informações do mapa mental...")
            is_valid, missing_info = self.generator.validate_sandbox_data()
            
            if not is_valid:
                error_msg = "Informações insuficientes no mapa mental:\n\n" + "\n".join(f"• {info}" for info in missing_info)
                self.finished_error.emit(error_msg)
                return
            
            self.progress_updated.emit("Gerando estrutura do projeto...")
            project_path = self.generator.generate_project_structure()
            
            self.progress_updated.emit("Iniciando ambiente Docker...")
            if self.generator.start_environment():
                success_msg = (
                    f"Ambiente Docker criado com sucesso!\n\n"
                    f"Localização: {project_path}\n"
                    f"O ambiente está agora em execução.\n\n"
                    f"Aceda a:\n"
                    f"   • Aplicação: http://localhost:5000\n"
                    f"   • pgAdmin: http://localhost:5050 (email: admin@socialnotes.com, password: admin123)\n"
                    f"   • Base de dados: localhost:5433\n\n"
                    f"Comandos úteis:\n"
                    f"   - Parar ambiente: docker-compose down\n"
                    f"   - Ver logs: docker-compose logs\n"
                    f"   - Reiniciar: docker-compose restart"
                )
                self.finished_success.emit(success_msg)
            else:
                self.finished_error.emit(
                    "Erro ao iniciar o ambiente Docker.\n\n"
                    "Possíveis causas:\n"
                    "• Docker Desktop não está em execução\n"
                    "• Portas 5000, 5050 ou 5433 já estão em uso\n"
                    "• Sem recursos suficientes (memória/CPU)\n\n"
                    "Verifique o Docker Desktop e tente novamente."
                )
                
        except Exception as e:
            self.finished_error.emit(f"Erro inesperado: {str(e)}")

class ProjectLocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Selecionar Localização do Projeto")
        self.setGeometry(400, 400, 600, 200)
        
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("Onde deseja criar o projeto Docker?")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Descrição
        description = QLabel("Selecione a pasta onde o ambiente Docker será criado:")
        layout.addWidget(description)
        
        # Seleção de pasta
        path_layout = QHBoxLayout()
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Selecione uma pasta...")
        self.path_edit.setText(str(Path.home() / "social-notes-docker"))
        path_layout.addWidget(self.path_edit)
        
        browse_btn = QPushButton("Procurar...")
        browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        # Botões
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("Criar Projeto")
        self.ok_btn.clicked.connect(self.accept_selection)
        button_layout.addWidget(self.ok_btn)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Selecionar Pasta do Projeto",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.path_edit.setText(folder)
    
    def accept_selection(self):
        path = self.path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma pasta.")
            return
        
        self.selected_path = Path(path)
        self.accept()

class DockerAutomationDialog(QDialog):
    def __init__(self, sandbox_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.sandbox_data = sandbox_data
        self.project_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Up Project in Env - Docker Automation")
        self.setGeometry(300, 300, 700, 500)
        
        layout = QVBoxLayout()
        
        # Título
        title = QLabel("Docker Automation - Up Project in Env")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px; color: #2563eb;")
        layout.addWidget(title)
        
        # Descrição
        description = QLabel(
            "Este assistente irá analisar o seu mapa mental da aplicação web e criar automaticamente "
            "um ambiente Docker completo com base na arquitetura definida."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px; color: #4b5563;")
        layout.addWidget(description)
        
        # Informações do projeto
        info_label = QLabel("Informações do Sandbox:")
        info_label.setStyleSheet("font-weight: bold; margin: 10px 0 5px 0;")
        layout.addWidget(info_label)
        
        # Estatísticas
        objects_count = len(self.sandbox_data.get('objects', []))
        code_files = len([obj for obj in self.sandbox_data.get('objects', []) if obj.get('type') == 'code_file'])
        databases = len([obj for obj in self.sandbox_data.get('objects', []) if obj.get('type') in ['postgresql', 'mysql', 'database']])
        
        stats_text = f"""
        • Total de objetos: {objects_count}
        • Ficheiros de código: {code_files}
        • Bases de dados: {databases}
        • Tecnologia: Flask + PostgreSQL
        """
        
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet("background-color: #4b5363; padding: 10px; border-radius: 5px;")
        layout.addWidget(stats_label)
        
        # Área de progresso
        self.progress_label = QLabel("Pronto para iniciar...")
        self.progress_label.setStyleSheet("font-weight: bold; margin: 10px;")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log
        log_label = QLabel("Log do Processo:")
        log_label.setStyleSheet("font-weight: bold; margin: 10px 0 5px 0;")
        layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("O log do processo aparecerá aqui...")
        self.log_output.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt;")
        layout.addWidget(self.log_output)
        
        # Botões
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Selecionar Localização e Iniciar")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """)
        self.start_button.clicked.connect(self.select_location_and_start)
        button_layout.addWidget(self.start_button)
        
        self.close_button = QPushButton("Fechar")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def add_attack_button(self):
        if hasattr(self, 'attack_button') and self.attack_button:
            return
        
        attack_widget = QWidget()
        attack_layout = QHBoxLayout(attack_widget)
        attack_layout.setContentsMargins(0, 0, 0, 0)
        
        self.attack_button = QPushButton("Call Nabia")
        self.attack_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
                font-size: 14px;
                margin: 8px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        self.attack_button.clicked.connect(self.launch_security_attack)
        attack_layout.addWidget(self.attack_button)
        
        main_layout = self.layout()
        main_layout.insertWidget(5, attack_widget)

    def launch_security_attack(self):
        attack_dialog = AttackDialog("http://localhost:5000", self)
        attack_dialog.exec()
    
    def select_location_and_start(self):
        location_dialog = ProjectLocationDialog(self)
        if location_dialog.exec():
            self.project_path = location_dialog.selected_path
            self.start_automation()
    
    def start_automation(self):
        if not self.project_path:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma localização primeiro.")
            return
            
        self.start_button.setEnabled(False)
        self.start_button.setText("Processando...")
        self.progress_bar.setVisible(True)
        self.log_output.clear()
        
        self.log_output.append(f"Localização selecionada: {self.project_path}")
        
        self.worker_thread = DockerAutomationThread(self.sandbox_data, self.project_path)
        self.worker_thread.progress_updated.connect(self.update_progress)
        self.worker_thread.finished_success.connect(self.automation_success)
        self.worker_thread.finished_error.connect(self.automation_error)
        self.worker_thread.start()
    
    def update_progress(self, message):
        self.progress_label.setText(message)
        self.log_output.append(f"{message}")
        cursor = self.log_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_output.setTextCursor(cursor)
    
    def automation_success(self, message):
        self.progress_label.setText("Processo concluído com sucesso!")
        self.log_output.append("\n" + "="*60)
        self.log_output.append("SUCESSO!")
        self.log_output.append("="*60)
        self.log_output.append(message)
        
        self.start_button.setEnabled(True)
        self.start_button.setText("Selecionar Localização e Iniciar")
        self.progress_bar.setVisible(False)

        self.add_attack_button()
        
        QMessageBox.information(self, "Sucesso", message)
    
    def automation_error(self, message):
        self.progress_label.setText("Erro no processo")
        self.log_output.append("\n" + "="*60)
        self.log_output.append("ERRO!")
        self.log_output.append("="*60)
        self.log_output.append(message)
        
        self.start_button.setEnabled(True)
        self.start_button.setText("Selecionar Localização e Iniciar")
        self.progress_bar.setVisible(False)
        
        QMessageBox.critical(self, "Erro", message)