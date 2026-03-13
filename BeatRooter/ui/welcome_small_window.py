# welcome_small_menu.py - Compact Quick Start Menu
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QPen, QFont
import os


class CircularButton(QPushButton):
    """Custom square button with glow effect and softened corners"""
    
    def __init__(self, text, glow_color, parent=None):
        super().__init__(parent)
        self.display_text = text
        self.glow_color = QColor(glow_color)
        self.setFixedSize(240, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Add glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(30)
        glow.setColor(self.glow_color)
        glow.setOffset(0, 0)
        self.setGraphicsEffect(glow)
        
        # Extract RGB from glow_color and create lighter background
        r, g, b = self.glow_color.red(), self.glow_color.green(), self.glow_color.blue()
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba({r}, {g}, {b}, 0.2);
                border-left: 3px solid {glow_color};
                border-right: 3px solid {glow_color};
                border-top: none;
                border-bottom: none;
                border-radius: 12px;
                color: white;
                font-size: 12px;
                font-weight: 600;
                padding: 15px 10px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: rgba({r}, {g}, {b}, 0.35);
                border-left: 4px solid {glow_color};
                border-right: 4px solid {glow_color};
            }}
            QPushButton:pressed {{
                background-color: rgba({r}, {g}, {b}, 0.5);
            }}
        """)
        
        self.setText(text)


class WelcomeSmallMenu(QWidget):
    """Compact vertical quick start menu"""
    
    # Signals
    open_previous_project = pyqtSignal()
    start_new_project = pyqtSignal()
    settings_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setAutoFillBackground(True)
        self.setup_ui()
        self.apply_styles()
        self.setup_animations()
    
    def setup_ui(self):
        """Create the UI layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create background frame
        background_frame = QFrame()
        background_frame.setObjectName("background_frame")
        background_frame.setStyleSheet("""
            QFrame#background_frame {
                background-color: #2e2e2e;
                border-right: 2px solid #4a4a4a;
            }
        """)
        
        # Layout for content inside background frame
        content_layout = QVBoxLayout(background_frame)
        content_layout.setContentsMargins(20, 30, 20, 30)
        content_layout.setSpacing(25)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Logo section
        logo_frame = QFrame()
        logo_frame.setObjectName("logo_frame")
        logo_frame.setFixedSize(180, 180)
        
        logo_layout = QVBoxLayout(logo_frame)
        logo_layout.setContentsMargins(15, 15, 15, 15)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Logo image
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Load logo if exists
        logo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'BeatRooter_logo.png')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    140, 140,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback text logo
            logo_label.setText("BEAT\nROOTER")
            logo_label.setStyleSheet("""
                QLabel {
                    color: #ff6b9d;
                    font-size: 20px;
                    font-weight: 900;
                    background: transparent;
                    border: none;
                }
            """)
        
        logo_layout.addWidget(logo_label)
        content_layout.addWidget(logo_frame, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # Welcome text
        welcome_label = QLabel("Welcome back to BeatRooter!")
        welcome_label.setObjectName("welcome_text")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setWordWrap(True)
        content_layout.addWidget(welcome_label)
        
        content_layout.addSpacing(20)
        
        # Previous project button (red)
        self.previous_project_btn = CircularButton(
            "Jump right into your previous project",
            "#dc2626"
        )
        self.previous_project_btn.clicked.connect(self.on_previous_project_clicked)
        content_layout.addWidget(self.previous_project_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        content_layout.addSpacing(15)
        
        # New project button (blue)
        self.new_project_btn = CircularButton(
            "Start a new project",
            "#4a9eff"
        )
        self.new_project_btn.clicked.connect(self.on_new_project_clicked)
        content_layout.addWidget(self.new_project_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        content_layout.addStretch()
        
        # Footer section
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(8)
        
        settings_hint = QLabel("You can deactivate this quick menu in the settings.")
        settings_hint.setObjectName("footer_text")
        settings_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        settings_hint.setWordWrap(True)
        
        footer_label = QLabel("BeatRooter Notes")
        footer_label.setObjectName("footer_label")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        footer_layout.addWidget(settings_hint)
        footer_layout.addWidget(footer_label)
        
        content_layout.addLayout(footer_layout)
        
        # Add background frame to main layout
        main_layout.addWidget(background_frame)
    
    def apply_styles(self):
        """Apply dark theme styles"""
        self.setStyleSheet("""
            WelcomeSmallMenu {
                background-color: transparent;
            }
            
            QFrame#logo_frame {
                background-color: transparent;
                border: 2px solid #ff6b9d;
                border-radius: 20px;
            }
            
            QLabel#welcome_text {
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }
            
            QLabel#footer_text {
                color: #8a8a9a;
                font-size: 10px;
                background: transparent;
                border: none;
            }
            
            QLabel#footer_label {
                color: #6a6a7a;
                font-size: 9px;
                font-weight: 600;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }
        """)
    
    def setup_animations(self):
        """Setup entrance animations"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(400)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def showEvent(self, event):
        """Trigger animation when shown"""
        super().showEvent(event)
        if hasattr(self, 'animation'):
            self.animation.start()
    
    def on_previous_project_clicked(self):
        """Handle previous project button click"""
        self.open_previous_project.emit()
    
    def on_new_project_clicked(self):
        """Handle new project button click"""
        self.start_new_project.emit()
    
    def set_previous_project_enabled(self, enabled):
        """Enable/disable previous project button"""
        self.previous_project_btn.setEnabled(enabled)
        if not enabled:
            self.previous_project_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 3px solid #555555;
                    border-radius: 100px;
                    color: #666666;
                    font-size: 13px;
                    font-weight: 600;
                    padding: 30px;
                    text-align: center;
                }
            """)
