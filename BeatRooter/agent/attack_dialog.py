import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTextEdit, QLabel, QProgressBar, QGroupBox,
                            QScrollArea, QWidget, QMessageBox, QStackedWidget)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon, QMovie, QPixmap
from agent.pentest_agent import SecurityAgent, SecurityVulnerability
import os
from agent.pdf_report_generator import PDFReportGenerator
from agent.markdown_report_generator import MarkdownReportGenerator
from agent.json_report_generator import JSONReportGenerator
from pathlib import Path
from utils.path_utils import get_resource_path
import re
import traceback
import logging
from datetime import datetime

def setup_animation_logger():
    try:
        logger = logging.getLogger('animation')
        logger.setLevel(logging.DEBUG)
        
        logger.handlers.clear()
        
        if not hasattr(sys, '_MEIPASS'):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        logger.info("=" * 60)
        logger.info("ANIMATION DEBUG LOG - BeatRooter")
        logger.info("=" * 60)
        logger.info(f"Início: {datetime.now()}")
        logger.info(f"PyInstaller: {hasattr(sys, '_MEIPASS')}")
        
        return logger
        
    except Exception as e:
        print(f"[ERROR] Não foi possível configurar logger: {e}")
        logger = logging.getLogger('animation_fallback')
        logger.addHandler(logging.NullHandler())
        return logger

animation_logger = setup_animation_logger()

class IntroAnimationWidget(QWidget):
    animation_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation_frames = []
        self.current_frame_index = 0
        self.current_text_index = 0
        self.current_text = ""
        self.full_text = ""
        self.animation_timer = QTimer()
        self.text_timer = QTimer()
        
        try:
            animation_logger.info("Inicializando IntroAnimationWidget")
            self.setup_ui()
            self.setWindowIcon(QIcon(get_resource_path("icons/app_icon.png")))
            animation_logger.info("IntroAnimationWidget inicializado com sucesso")
        except Exception as e:
            animation_logger.error(f"Erro ao inicializar IntroAnimationWidget: {e}")
            animation_logger.error(traceback.format_exc())
            raise
        
    def setup_ui(self):
        try:
            animation_logger.info("Configurando UI do IntroAnimationWidget")
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
            
            # Container para a animação/imagem
            self.animation_container = QLabel()
            self.animation_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.animation_container.setMinimumSize(400, 300)
            self.animation_container.setStyleSheet("""
                background-color: transparent;
                border: none;
                padding: 0px;
            """)
            layout.addWidget(self.animation_container)
            
            # Container para o texto recursivo
            self.text_container = QLabel()
            self.text_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.text_container.setWordWrap(True)
            self.text_container.setStyleSheet("""
                background-color: #2d2d2d;
                color: #ffffff;
                font-family: 'Courier New';
                font-size: 12px;
                padding: 10px;
                border: 1px solid #444;
                border-radius: 5px;
                min-height: 60px;
            """)
            self.text_container.setMinimumHeight(70)
            self.text_container.setMaximumHeight(100)
            layout.addWidget(self.text_container)
            
            self.setLayout(layout)
            animation_logger.info("UI configurada com sucesso")
            
        except Exception as e:
            animation_logger.error(f"Erro ao configurar UI: {e}")
            animation_logger.error(traceback.format_exc())
            raise
    
    def start_animation(self, frames_folder, text_sequence, frame_duration=150):
        try:
            animation_logger.info(f"Iniciando animação: {frames_folder}")
            animation_logger.info(f"Text sequence: {text_sequence}")
            
            self.animation_frames = self.load_frames_from_folder(frames_folder)
            self.text_sequence = text_sequence
            self.current_frame_index = 0
            self.current_text_index = 0
            
            animation_logger.info(f"Total de frames carregados: {len(self.animation_frames)}")
            
            if not self.animation_frames:
                animation_logger.warning("Nenhum frame carregado, usando frame padrão")
                self.show_default_frame()
                self.start_text_animation()
                return
            
            self.animation_timer.timeout.connect(self.next_frame)
            self.animation_timer.start(frame_duration)
            
            self.show_current_frame()
            
            QTimer.singleShot(500, lambda: self.start_text_animation())
            animation_logger.info("Animação iniciada com sucesso")
            
        except Exception as e:
            animation_logger.error(f"Erro ao iniciar animação: {e}")
            animation_logger.error(traceback.format_exc())
            self.show_default_frame()
            self.text_container.setText("Nábia - Agente de Segurança")
            QTimer.singleShot(2000, lambda: self.animation_complete.emit())
    
    def load_frames_from_folder(self, frames_folder):
        frames = []
        try:
            animation_logger.info(f"Tentando carregar frames de: {frames_folder}")
            
            if os.path.isabs(frames_folder):
                actual_folder = frames_folder
                animation_logger.info(f"Caminho absoluto: {actual_folder}")
            else:
                actual_folder = get_resource_path(frames_folder)
                animation_logger.info(f"Caminho resolvido: {actual_folder}")
            
            if os.path.exists(actual_folder):
                animation_logger.info(f"Pasta existe: {actual_folder}")
                
                all_files = os.listdir(actual_folder)
                animation_logger.info(f"Arquivos na pasta: {len(all_files)}")
                
                image_files = []
                for file in all_files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        image_files.append(file)
                
                animation_logger.info(f"Imagens encontradas: {len(image_files)}")
                
                image_files.sort()
                
                for file in image_files:
                    frame_path = os.path.join(actual_folder, file)
                    frames.append(frame_path)
                    animation_logger.debug(f"Frame adicionado: {file}")
                    
                animation_logger.info(f"Total de {len(frames)} frames carregados")
                
            else:
                animation_logger.warning(f"Pasta não encontrada: {actual_folder}")
                
                possible_paths = [
                    frames_folder,
                    os.path.join("assets", frames_folder),
                    os.path.join("animations", frames_folder.split('/')[-1] if '/' in frames_folder else frames_folder),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        animation_logger.info(f"Encontrado em caminho alternativo: {path}")
                        for file in sorted(os.listdir(path)):
                            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                frame_path = os.path.join(path, file)
                                frames.append(frame_path)
                        break
                    
        except Exception as e:
            animation_logger.error(f"Erro ao carregar frames: {e}")
            animation_logger.error(traceback.format_exc())
            
        return frames
    
    def show_default_frame(self):
        try:
            animation_logger.info("Mostrando frame padrão")
            pixmap = QPixmap(400, 300)
            pixmap.fill(QColor(45, 45, 45))
            
            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Nábia")
            painter.end()
            
            self.animation_container.setPixmap(pixmap)
            
        except Exception as e:
            animation_logger.error(f"Erro ao mostrar frame padrão: {e}")
            animation_logger.error(traceback.format_exc())
    
    def show_current_frame(self):
        try:
            if self.current_frame_index < len(self.animation_frames):
                frame_path = self.animation_frames[self.current_frame_index]
                animation_logger.debug(f"Mostrando frame {self.current_frame_index}: {frame_path}")
                
                pixmap = QPixmap(frame_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
                    self.animation_container.setPixmap(pixmap)
                else:
                    animation_logger.warning(f"Falha ao carregar imagem: {frame_path}")
                    self.show_default_frame()
            else:
                animation_logger.warning("Índice de frame fora do alcance")
                self.show_default_frame()
                
        except Exception as e:
            animation_logger.error(f"Erro ao mostrar frame atual: {e}")
            animation_logger.error(traceback.format_exc())
            self.show_default_frame()
    
    def next_frame(self):
        try:
            self.current_frame_index += 1
            if self.current_frame_index >= len(self.animation_frames):
                self.current_frame_index = 0
            
            self.show_current_frame()
            
        except Exception as e:
            animation_logger.error(f"Erro no next_frame: {e}")
            animation_logger.error(traceback.format_exc())
            self.animation_timer.stop()
    
    def start_text_animation(self):
        try:
            if self.current_text_index < len(self.text_sequence):
                self.full_text = self.text_sequence[self.current_text_index]
                self.current_text = ""
                animation_logger.info(f"Iniciando texto: {self.full_text}")
                self.text_timer.timeout.connect(self.next_character)
                self.text_timer.start(50)
            else:
                animation_logger.info("Nenhum texto disponível, completando animação")
                self.animation_complete.emit()
                
        except Exception as e:
            animation_logger.error(f"Erro ao iniciar texto animado: {e}")
            animation_logger.error(traceback.format_exc())
            self.animation_complete.emit()
    
    def next_character(self):
        try:
            if len(self.current_text) < len(self.full_text):
                self.current_text += self.full_text[len(self.current_text)]
                self.text_container.setText(self.current_text)
            else:
                self.text_timer.stop()
                animation_logger.info("Texto completo, aguardando próxima segmento")
                QTimer.singleShot(2000, self.next_text_segment)
                
        except Exception as e:
            animation_logger.error(f"Erro no next_character: {e}")
            animation_logger.error(traceback.format_exc())
            self.text_timer.stop()
            self.next_text_segment()
    
    def next_text_segment(self):
        try:
            self.current_text_index += 1
            
            if self.current_text_index < len(self.text_sequence):
                animation_logger.info(f"Próximo segmento de texto: {self.current_text_index}")
                self.start_text_animation()
            else:
                animation_logger.info("Todos os segmentos de texto completados")
                self.animation_complete.emit()
                
        except Exception as e:
            animation_logger.error(f"Erro no next_text_segment: {e}")
            animation_logger.error(traceback.format_exc())
            self.animation_complete.emit()
    
    def cleanup(self):
        try:
            animation_logger.info("Limpando animação")
            self.animation_timer.stop()
            self.text_timer.stop()
        except Exception as e:
            animation_logger.error(f"Erro ao limpar: {e}")

class CompletionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Análise Concluída")
        self.setFixedSize(500, 450)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        completion_image = QLabel()
        completion_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        completion_image.setMinimumSize(400, 300)
        completion_image.setStyleSheet("""
            background-color: transparent;
            border: none;
            padding: 0px;
        """)
        
        completion_path = get_resource_path("animations/nabia_complete")
        frames = []
        if os.path.exists(completion_path):
            for file in sorted(os.listdir(completion_path)):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    frame_path = os.path.join(completion_path, file)
                    frames.append(frame_path)
        
        if frames:
            pixmap = QPixmap(frames[0])
            pixmap = pixmap.scaled(400, 300, Qt.AspectRatioMode.KeepAspectRatio, 
                                 Qt.TransformationMode.SmoothTransformation)
            completion_image.setPixmap(pixmap)
        else:
            completion_image.setText("Completo!")
            completion_image.setStyleSheet("""
                background-color: transparent; 
                color: white; 
                font-size: 16px;
                font-weight: bold;
                border: none;
            """)
        
        layout.addWidget(completion_image, alignment=Qt.AlignmentFlag.AlignCenter)
        
        completion_text = QLabel("Acabei, toma ai o relatório com as vulnerabilidades encontradas, que eu não aguento mais ver tanta asneira num só código")
        completion_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        completion_text.setWordWrap(True)
        completion_text.setStyleSheet("""
            background-color: #2d2d2d;
            color: #ffffff;
            font-family: 'Courier New';
            font-size: 12px;
            padding: 10px;
            border: 1px solid #444;
            border-radius: 5px;
            min-height: 60px;
        """)
        completion_text.setMinimumHeight(70)
        completion_text.setMaximumHeight(100)
        layout.addWidget(completion_text)
        
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 5px;
                font-size: 14px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
        
        self.setLayout(layout)


class AttackDialog(QDialog):
    def __init__(self, target_url="http://localhost:5000", parent=None):
        super().__init__(parent)
        self.target_url = target_url
        self.security_agent = None
        self.animation_sequence = []
        self.current_animation_index = 0
        
        try:
            animation_logger.info("Inicializando AttackDialog")
            self.setup_ui()
            animation_logger.info("AttackDialog inicializado com sucesso")
            
            QTimer.singleShot(500, self.start_intro_animation)
            
        except Exception as e:
            animation_logger.error(f"Erro ao inicializar AttackDialog: {e}")
            animation_logger.error(traceback.format_exc())
            raise
    
    def setup_ui(self):
        self.setWindowTitle("Security Attack Agent")
        self.setGeometry(400, 200, 600, 500)
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget)
        
        # Tela de introdução
        self.setup_intro_screen()
        
        # Tela principal
        self.setup_main_screen()
        
        self.setLayout(self.main_layout)
        
        # Iniciar tela de introdução
        self.stacked_widget.setCurrentIndex(0)
    
    def setup_intro_screen(self):
        self.intro_widget = QWidget()
        intro_layout = QVBoxLayout(self.intro_widget)
        intro_layout.setContentsMargins(20, 20, 20, 20)
        intro_layout.setSpacing(15)
        
        # Título
        title = QLabel("Agente de Ataque - Nábia")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #dc2626; margin: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_layout.addWidget(title)
        
        # Widget de animação
        self.animation_widget = IntroAnimationWidget()
        intro_layout.addWidget(self.animation_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # pular introdução
        skip_button = QPushButton("Pular Introdução")
        skip_button.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #888;
            }
        """)
        skip_button.clicked.connect(self.skip_intro)
        intro_layout.addWidget(skip_button)
        
        self.stacked_widget.addWidget(self.intro_widget)
    
    def setup_main_screen(self):
        self.main_widget = QWidget()
        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("Agente de Ataque de Segurança")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #dc2626; margin: 5px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Status
        self.status_label = QLabel("Pronto para iniciar ataque...")
        self.status_label.setStyleSheet("font-weight: bold; padding: 8px; background-color: #4b5363; border-radius: 5px; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Vulnerabilities Area
        vuln_group = QGroupBox("Vulnerabilidades Detectadas")
        vuln_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        vuln_layout = QVBoxLayout(vuln_group)
        
        self.vulnerabilities_display = QTextEdit()
        self.vulnerabilities_display.setReadOnly(True)
        self.vulnerabilities_display.setMaximumHeight(350)
        self.vulnerabilities_display.setStyleSheet("font-family: 'Courier New'; font-size: 9pt;")
        vuln_layout.addWidget(self.vulnerabilities_display)
        
        layout.addWidget(vuln_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Atattack")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """)
        self.start_button.clicked.connect(self.start_real_attack)
        button_layout.addWidget(self.start_button)
        
        self.open_site_button = QPushButton("Open WebSite")
        self.open_site_button.setStyleSheet("padding: 10px; font-size: 12px;")
        self.open_site_button.clicked.connect(self.open_target_site)
        button_layout.addWidget(self.open_site_button)
        
        self.close_button = QPushButton("Close")
        self.close_button.setStyleSheet("padding: 10px; font-size: 12px;")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
        
        self.stacked_widget.addWidget(self.main_widget)
    
    def start_intro_animation(self):
        try:
            animation_logger.info("Iniciando animação de introdução")
            
            self.animation_sequence = [
                {
                    "frames_folder": "animations/nabia_intro",
                    "text": ["Olá sou a Nábia e sou o teu agente pessoal de ataque e ajuda"]
                },
                {
                    "frames_folder": "animations/nabia_ready",
                    "text": ["Vamos lá então rebentar com esse site"]
                }
            ]
            
            animation_logger.info(f"Sequência de animação configurada: {len(self.animation_sequence)} partes")
            
            self.animation_widget.animation_complete.connect(self.on_animation_complete)
            
            self.current_animation_index = 0
            self.start_current_animation()
            
        except Exception as e:
            animation_logger.error(f"Erro ao iniciar animação de introdução: {e}")
            animation_logger.error(traceback.format_exc())
            self.skip_intro()
    
    def start_current_animation(self):
        try:
            if self.current_animation_index < len(self.animation_sequence):
                anim_data = self.animation_sequence[self.current_animation_index]
                
                frames_folder = anim_data["frames_folder"]
                text_sequence = anim_data["text"]
                
                animation_logger.info(f"Iniciando animação {self.current_animation_index + 1}: {frames_folder}")
                animation_logger.info(f"Texto: {text_sequence}")
                
                actual_path = get_resource_path(frames_folder)
                animation_logger.info(f"Caminho resolvido: {actual_path}")
                
                if os.path.exists(actual_path):
                    animation_logger.info(f"Caminho existe: {actual_path}")
                    self.animation_widget.start_animation(actual_path, text_sequence)
                else:
                    animation_logger.warning(f"Caminho não existe: {actual_path}")
                    
                    alternative_paths = [
                        frames_folder,
                        os.path.join("assets", frames_folder),
                        frames_folder.replace("animations/", ""),
                    ]
                    
                    for alt_path in alternative_paths:
                        if os.path.exists(alt_path):
                            animation_logger.info(f"Usando caminho alternativo: {alt_path}")
                            self.animation_widget.start_animation(alt_path, text_sequence)
                            return

                    animation_logger.warning("Nenhum caminho de animação encontrado, usando fallback")
                    self.animation_widget.show_default_frame()
                    self.animation_widget.text_container.setText(text_sequence[0] if text_sequence else "")
                    QTimer.singleShot(3000, self.on_animation_complete)
            else:
                animation_logger.info("Todas as animações completas")
                self.on_intro_complete()
                
        except Exception as e:
            animation_logger.error(f"Erro em start_current_animation: {e}")
            animation_logger.error(traceback.format_exc())
            self.on_animation_complete()
    
    def on_animation_complete(self):
        print(f"Animação {self.current_animation_index + 1} completada")

        self.current_animation_index += 1
        
        if self.current_animation_index < len(self.animation_sequence):
            QTimer.singleShot(1000, self.start_current_animation)
        else:
            self.on_intro_complete()
    
    def on_intro_complete(self):
        print("Todas as animações de introdução completas")
        self.stacked_widget.setCurrentIndex(1)
    
    def skip_intro(self):
        self.animation_widget.cleanup()
        self.stacked_widget.setCurrentIndex(1)
    
    def start_real_attack(self):
        self.start_button.setEnabled(False)
        self.start_button.setText("Ataque em Andamento...")
        self.progress_bar.setVisible(True)
        self.vulnerabilities_display.clear()
        
        sandbox_objects = []
        try:
            if hasattr(self, 'sandbox_manager') and self.sandbox_manager:
                sandbox_objects = list(self.sandbox_manager.environment.objects.values())
                print(f"Encontrados {len(sandbox_objects)} objetos do sandbox")
            else:
                print("Sandbox manager não disponível, usando objetos vazios")
        except Exception as e:
            print(f"Erro ao obter objetos do sandbox: {e}")
        
        self.security_agent = SecurityAgent(self.target_url, sandbox_objects)
        self.security_agent.vulnerability_found.connect(self.on_vulnerability_found)
        self.security_agent.status_updated.connect(self.on_status_updated)
        self.security_agent.attack_completed.connect(self.on_attack_completed)
        self.security_agent.start()
    
    def show_completion_message(self):
        completion_dialog = CompletionDialog(self)
        completion_dialog.exec()
    
    def open_target_site(self):
        import webbrowser
        webbrowser.open(self.target_url)
        self.status_label.setText(f"Site aberto: {self.target_url}")

    def on_vulnerability_found(self, vulnerability: SecurityVulnerability):
        try:
            print(f"Vulnerabilidade recebida na UI: {vulnerability.type} - {vulnerability.severity}")
            
            if vulnerability.severity == "Crítica":
                color = "#dc2626"
                icon = "🔴"
            elif vulnerability.severity == "Alta":
                color = "#ea580c"
                icon = "🟠"  
            elif vulnerability.severity == "Média":
                color = "#f59e0b"
                icon = "🟡"
            else:
                color = "#16a34a"
                icon = "🟢"
            
            vuln_text = f"""
    {icon} <span style='color: {color}; font-weight: bold; font-size: 12px;'>{vulnerability.type} - {vulnerability.severity}</span>
    <b>Descrição:</b> {vulnerability.description}
    <b>Localização:</b> {vulnerability.location}
    """
            
            # payload
            if vulnerability.payload:
                vuln_text += f"<b>Payload usado:</b> <code style='background: #2d2d2d; padding: 2px 4px; border-radius: 3px;'>{vulnerability.payload}</code>\n"
            
            # status
            status_html = ""
            if vulnerability.exploited:
                status_html = '<span style="color: #dc2626; font-weight: bold;">EXPLORADA</span>'
            else:
                status_html = '<span style="color: #f59e0b;">DETECTADA</span>'
            
            vuln_text += f"<b>Status:</b> {status_html}\n"
            
            # CVSS score
            if hasattr(vulnerability, 'cvss_score') and vulnerability.cvss_score > 0:
                vuln_text += f"<b>CVSS Score:</b> {vulnerability.cvss_score}/10\n"
            
            # impacto de negócio
            if hasattr(vulnerability, 'business_impact') and vulnerability.business_impact:
                vuln_text += f"<b>Impacto:</b> {vulnerability.business_impact}\n"
            
            # recomendação
            vuln_text += f"<b>Recomendação:</b> {vulnerability.recommendation}\n"
            
            # separador
            vuln_text += f"{'='*60}\n"
            
            # display
            current_content = self.vulnerabilities_display.toHtml()
            self.vulnerabilities_display.setHtml(current_content + vuln_text)
            
            # Scroll
            cursor = self.vulnerabilities_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.vulnerabilities_display.setTextCursor(cursor)
            
            print(f"Vulnerabilidade processada na UI: {vulnerability.type}")
            
        except Exception as e:
            print(f"Erro ao processar vulnerabilidade na UI: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    
    def on_status_updated(self, message: str):
        self.status_label.setText(message)

    def get_downloads_folder(self) -> Path:
        if os.name == 'nt':  # Windows
            downloads = Path.home() / "Downloads"
        else:  # Linux/Mac
            downloads = Path.home() / "Downloads"
            
        downloads.mkdir(exist_ok=True)
        return downloads
    
    def generate_reports(self):
        try:
            downloads_folder = self.get_downloads_folder()
            
            if not hasattr(self, 'security_agent') or not self.security_agent.vulnerabilities:
                QMessageBox.warning(self, "Aviso", 
                                "Nenhuma vulnerabilidade encontrada para gerar relatórios.\n"
                                "Execute a análise primeiro.")
                return
            
            # JSON
            json_generator = JSONReportGenerator(
                self.security_agent.vulnerabilities, 
                self.target_url
            )
            json_path = downloads_folder / "security_report.json"
            json_success = json_generator.generate_json_report(str(json_path))
            
            # PDF
            pdf_generator = PDFReportGenerator(str(json_path))
            pdf_path = downloads_folder / "security_report.pdf"
            pdf_success = pdf_generator.generate_pdf_report(str(pdf_path))
            
            # Markdown
            md_generator = MarkdownReportGenerator(str(json_path))
            md_path = downloads_folder / "security_report.md"
            md_success = md_generator.generate_markdown_report(str(md_path))
        
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao gerar relatórios: {str(e)}")

    def on_attack_completed(self):
        self.show_completion_message()

        self.debug_check_vulnerabilities()
        
        self.generate_reports()
        
        self.start_button.setEnabled(True)
        self.start_button.setText("Reset Attack")
        self.progress_bar.setVisible(False)

    def debug_check_vulnerabilities(self):
        if hasattr(self, 'security_agent') and self.security_agent:
            print(f"Total de vulnerabilidades encontradas: {len(self.security_agent.vulnerabilities)}")
            for i, vuln in enumerate(self.security_agent.vulnerabilities):
                print(f"  {i+1}. {vuln.type} - {vuln.severity}")

    def closeEvent(self, event):
        if hasattr(self, 'animation_widget'):
            self.animation_widget.cleanup()
        
        if self.security_agent and self.security_agent.isRunning():
            self.security_agent.terminate()
            self.security_agent.wait()
        event.accept()
    
    def safe_execute(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                animation_logger.error(f"Erro em {func.__name__}: {e}")
                animation_logger.error(traceback.format_exc())
                return None
        return wrapper