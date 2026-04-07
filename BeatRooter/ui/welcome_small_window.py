# welcome_small_menu.py - Compact Quick Start Side Panel
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor
import os

# Import shared gradient frames and visual primitives from welcome window
from ui.welcome_window import GradientFrame, ReverseGradientFrame
from ui.theme import get_app_font, build_filled_button_qss


class WelcomeSmallMenu(QWidget):
    """Compact vertical quick-start side panel matching the welcome window style."""

    open_previous_project = pyqtSignal()
    start_new_project = pyqtSignal()
    settings_requested = pyqtSignal()

    # Shared colour palette (mirrors welcome_window.py)
    COLORS = {
        'panel_top':          '#0A0710',
        'panel_mid':          '#17111F',
        'panel_bottom':       '#4A233C',
        'tile_pink':          '#923A5F',
        'tile_pink_end':      '#7A2E4F',
        'tile_blue':          '#1565C0',
        'tile_blue_end':      '#0D47A1',
        'button_pink':        '#B3386C',
        'button_blue':        '#1976D2',
        'text_white':         '#FFFFFF',
        'text_light_gray':    '#E0E0E0',
        'text_muted':         '#8a8a9a',
        'edge_glow':          '#B3386C',
        'separator':          '#3a3a3a',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_font = get_app_font()
        self.panel_width = 340
        self.setMinimumWidth(0)
        self.setMaximumWidth(self.panel_width)
        self.resize(self.panel_width, self.height())
        self.setAutoFillBackground(True)
        self.setup_ui()
        self.setup_animations()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Background frame ────────────────────────────────────────────────
        bg = QFrame()
        bg.setObjectName("background_frame")
        bg.setStyleSheet(f"""
            QFrame#background_frame {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 {self.COLORS['panel_top']},
                    stop: 0.62 {self.COLORS['panel_mid']},
                    stop: 1 {self.COLORS['panel_bottom']}
                );
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                border-top-right-radius: 16px;
                border-bottom-right-radius: 16px;
            }}
        """)

        self.edge_line = QFrame(bg)
        self.edge_line.setStyleSheet(f"background-color: {self.COLORS['edge_glow']}; border: none;")
        edge_glow = QGraphicsDropShadowEffect()
        edge_glow.setBlurRadius(16)
        edge_glow.setColor(QColor(self.COLORS['edge_glow']))
        edge_glow.setOffset(0, 0)
        self.edge_line.setGraphicsEffect(edge_glow)

        # Atmospheric gradient overlay (cosmetic, mouse-transparent)
        self.gradient_overlay = ReverseGradientFrame('#923A5F', bg)
        self.gradient_overlay.top_color = QColor(0, 0, 0, 255)
        self.gradient_overlay.set_bottom_color(QColor('#923A5F'))
        self.gradient_overlay.wave_animation.stop()
        self.gradient_overlay.color_animation.stop()
        self.gradient_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.gradient_overlay.lower()

        # ── Content layout ──────────────────────────────────────────────────
        content = QVBoxLayout(bg)
        content.setContentsMargins(22, 28, 22, 30)
        content.setSpacing(0)
        content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("background: transparent; border: none;")
        logo_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'designs', 'logos(app)', 'png', '6.png'
        )
        if os.path.exists(logo_path):
            px = QPixmap(logo_path)
            if not px.isNull():
                logo_label.setPixmap(px.scaledToHeight(
                    100, Qt.TransformationMode.SmoothTransformation
                ))
        else:
            logo_label.setText("BeatRooter")
            logo_label.setStyleSheet(f"""
                color: {self.COLORS['text_white']};
                font-family: {self.app_font};
                font-size: 20px; font-weight: 700;
                background: transparent; border: none;
            """)
        content.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        content.addSpacing(16)

        # Title
        title = QLabel("Welcome back to\nBeatRooter!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet(f"""
            color: {self.COLORS['text_white']};
            font-family: {self.app_font};
            font-size: 20px; font-weight: 700;
            background: transparent; border: none;
        """)
        content.addWidget(title)
        content.addSpacing(6)

        # Subtitle
        subtitle = QLabel("Your Tool for Forensics\nand Security Analysis.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"""
            color: {self.COLORS['text_light_gray']};
            font-family: {self.app_font};
            font-size: 13px; font-weight: 400; font-style: italic;
            background: transparent; border: none;
        """)
        content.addWidget(subtitle)
        content.addSpacing(18)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {self.COLORS['separator']}; border: none;")
        content.addWidget(sep)
        content.addSpacing(18)

        # Action tiles
        self.prev_tile, self.prev_btn = self._make_action_tile(
            title="Continue Project",
            description="Jump right into your previous project",
            button_text="Open Previous",
            tile_color=self.COLORS['tile_pink'],
            tile_end=self.COLORS['tile_pink_end'],
            btn_color=self.COLORS['button_pink'],
            callback=self.on_previous_project_clicked,
        )
        content.addWidget(self.prev_tile)
        content.addSpacing(12)

        new_tile, _ = self._make_action_tile(
            title="New Project",
            description="Start a fresh investigation",
            button_text="Start Project",
            tile_color=self.COLORS['tile_blue'],
            tile_end=self.COLORS['tile_blue_end'],
            btn_color=self.COLORS['button_blue'],
            callback=self.on_new_project_clicked,
        )
        content.addWidget(new_tile)
        content.addStretch()

        # Footer
        hint = QLabel("Deactivate this menu in settings.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"""
            color: {self.COLORS['text_muted']};
            font-family: {self.app_font};
            font-size: 10px; background: transparent; border: none;
        """)
        content.addWidget(hint)
        content.addSpacing(4)

        brand = QLabel("BeatRooter Notes")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.setStyleSheet(f"""
            color: #6a6a7a;
            font-family: {self.app_font};
            font-size: 9px; font-weight: 600; letter-spacing: 1px;
            background: transparent; border: none;
        """)
        content.addWidget(brand)
        content.addSpacing(4)

        main_layout.addWidget(bg)

    def _make_action_tile(self, title, description, button_text,
                          tile_color, tile_end, btn_color, callback):
        """Create a welcome-window-style action card with title, description and button."""
        tile = GradientFrame(tile_color, tile_end)
        tile.setMinimumHeight(128)
        tile.setMaximumHeight(156)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 110))
        shadow.setOffset(0, 5)
        tile.setGraphicsEffect(shadow)
        tile.setStyleSheet("border-radius: 16px;")

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        t_label = QLabel(title)
        t_label.setStyleSheet(f"""
            color: {self.COLORS['text_white']};
            font-family: {self.app_font};
            font-size: 16px; font-weight: 700;
            background: transparent;
        """)

        d_label = QLabel(description)
        d_label.setWordWrap(True)
        d_label.setMinimumHeight(34)
        d_label.setStyleSheet(f"""
            color: {self.COLORS['text_light_gray']};
            font-family: {self.app_font};
            font-size: 12px; font-weight: 400;
            background: transparent;
        """)

        btn = QPushButton(button_text)
        btn.setFixedHeight(32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(build_filled_button_qss(
            self.app_font,
            btn_color,
            self.COLORS['text_white'],
            radius=10,
            font_size=13,
            padding="4px 12px"
        ))
        btn.clicked.connect(callback)

        layout.addWidget(t_label)
        layout.addWidget(d_label)
        layout.addStretch()
        layout.addWidget(btn)

        return tile, btn

    def setup_animations(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(400)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'animation'):
            self.animation.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'gradient_overlay'):
            self.gradient_overlay.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, 'edge_line'):
            self.edge_line.setGeometry(self.width() - 3, 0, 3, self.height())
            self.edge_line.raise_()

    def on_previous_project_clicked(self):
        self.open_previous_project.emit()

    def on_new_project_clicked(self):
        self.start_new_project.emit()

    def set_previous_project_enabled(self, enabled):
        """Enable/disable the 'continue project' tile."""
        self.prev_btn.setEnabled(enabled)
        opacity = QGraphicsOpacityEffect()
        if enabled:
            opacity.setOpacity(1.0)
            # Restore drop shadow
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(18)
            shadow.setColor(QColor(0, 0, 0, 110))
            shadow.setOffset(0, 5)
            self.prev_tile.setGraphicsEffect(shadow)
        else:
            opacity.setOpacity(0.40)
            self.prev_tile.setGraphicsEffect(opacity)