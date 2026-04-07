from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QScrollArea, QWidget, QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QFont
import os

from ui.welcome_window import GradientFrame, ReverseGradientFrame, PROJECT_TEMPLATES
from ui.theme import get_app_font, get_welcome_palette, lighten_color


class PillButton(QPushButton):
    """QPushButton with anti-aliased pill-shaped background drawn via paintEvent."""

    def __init__(self, text, bg_color: str, hover_color: str, pressed_color: str, text_color: str, app_font: str, parent=None):
        super().__init__(text, parent)
        self._bg = QColor(bg_color)
        self._hover = QColor(hover_color)
        self._pressed = QColor(pressed_color)
        self._text_color = QColor(text_color)
        self._hovered = False
        self._is_pressed = False
        self._draw_font = QFont(app_font)
        self._draw_font.setPixelSize(18)
        self._draw_font.setBold(True)
        self.setFont(self._draw_font)

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        self._is_pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._is_pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        if self._is_pressed:
            color = self._pressed
        elif self._hovered:
            color = self._hover
        else:
            color = self._bg
        painter.setBrush(color)
        r = self.height() / 2.0
        painter.drawRoundedRect(self.rect(), r, r)
        painter.setFont(self._draw_font)
        painter.setPen(self._text_color)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class ProjectSelectionDialog(QDialog):
    project_selected = pyqtSignal(str, str)  # project_type, category

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_project = None
        self.selected_category = None
        self.current_project_type = None

        self.colors = get_welcome_palette()
        self.app_font = get_app_font()
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.logo_path = os.path.join(self.base_path, 'assets', 'beatrooter_logo.svg')

        self.setWindowTitle("New Investigation - Select Project Type")
        self.setMinimumSize(1200, 860)
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        self.gradient_overlay = ReverseGradientFrame('#923A5F', self)
        self.gradient_overlay.setGeometry(self.rect())
        self.gradient_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Keep this menu's signature look: blue atmosphere blending into team color.
        self.gradient_overlay.top_color = QColor(21, 101, 192, 42)
        self.gradient_overlay.lower()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 20, 40, 24)
        self.layout.setSpacing(20)

        self.header_container = self._build_selection_header()
        self.layout.addWidget(self.header_container)

        self.screen_stack = QFrame()
        self.screen_stack_layout = QVBoxLayout(self.screen_stack)
        self.screen_stack_layout.setContentsMargins(0, 0, 0, 0)
        self.screen_stack_layout.setSpacing(0)
        self.screen_stack.setStyleSheet("background-color: transparent;")
        self.layout.addWidget(self.screen_stack, 1)

        self.project_page = self._build_project_page()
        self.category_page = self._build_category_page()
        self.screen_stack_layout.addWidget(self.project_page)
        self.screen_stack_layout.addWidget(self.category_page)
        self.category_page.hide()

        self._set_header(
            title_text="Select Project Type",
            subtitle_text="Choose the specialized workflow for your analysis",
            accent_color="rgba(255, 255, 255, 0.65)",
            show_back=False,
        )
        self._set_menu_gradient(None)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setFixedSize(120, 44)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(button_layout)

    def _build_selection_header(self):
        header_container = QWidget()
        header_container.setStyleSheet("background-color: transparent;")
        header_main_layout = QHBoxLayout(header_container)
        header_main_layout.setContentsMargins(0, 0, 0, 0)
        header_main_layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.logo_label.setStyleSheet("background-color: transparent;")
        if os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            self.logo_label.setPixmap(pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo_label.setText("BeatRooter")
            self.logo_label.setStyleSheet(f"""
                color: {self.colors['text_primary']};
                font-size: 28px;
                font-weight: 700;
                font-family: {self.app_font};
                background-color: transparent;
            """)

        self.header_title = QLabel()
        self.header_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.header_title.setStyleSheet(f"""
            color: {self.colors['text_primary']};
            font-size: 28px;
            font-weight: 500;
            font-family: {self.app_font};
            background-color: transparent;
        """)

        self.header_subtitle = QLabel()
        self.header_subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.header_subtitle.setStyleSheet(f"""
            color: {self.colors['text_primary']};
            font-size: 15px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
        """)

        title_block = QWidget()
        title_block.setStyleSheet("background-color: transparent;")
        title_block_layout = QHBoxLayout(title_block)
        title_block_layout.setContentsMargins(0, 0, 0, 0)
        title_block_layout.setSpacing(10)
        title_block_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.accent_line = QFrame()
        self.accent_line.setFixedWidth(4)
        self.accent_line.setStyleSheet("background-color: rgba(255, 255, 255, 0.65); border-radius: 2px;")

        title_text_container = QWidget()
        self.title_text_container = title_text_container
        title_text_container.setStyleSheet("background-color: transparent;")
        title_text_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        title_text_layout = QVBoxLayout(title_text_container)
        title_text_layout.setContentsMargins(0, 0, 0, 0)
        title_text_layout.setSpacing(2)
        title_text_layout.addWidget(self.header_title)
        title_text_layout.addWidget(self.header_subtitle)

        self.header_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.header_subtitle.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._sync_header_geometry()

        title_block_layout.addWidget(self.accent_line, 0, Qt.AlignmentFlag.AlignTop)
        title_block_layout.addWidget(title_text_container, 0, Qt.AlignmentFlag.AlignTop)

        left_layout.addWidget(self.logo_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        left_layout.addWidget(title_block, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.show_projects)
        self.back_btn.setVisible(False)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.back_btn, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        right_layout.addStretch()

        header_main_layout.addLayout(left_layout)
        header_main_layout.addStretch()
        header_main_layout.addLayout(right_layout)
        return header_container

    def _build_project_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: transparent;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        cards_container = QWidget()
        cards_container.setStyleSheet("background-color: transparent;")
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setContentsMargins(0, 15, 0, 15)
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cards_layout.addWidget(self.create_project_type_card("redteam", PROJECT_TEMPLATES["redteam"]))
        cards_layout.addWidget(self.create_project_type_card("clean", PROJECT_TEMPLATES["clean"]))
        cards_layout.addWidget(self.create_project_type_card("blueteam", PROJECT_TEMPLATES["blueteam"]))

        page_layout.addWidget(cards_container)
        page_layout.addStretch()
        return page

    def _build_category_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: transparent;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        list_scroll = QScrollArea()
        list_scroll.setWidgetResizable(True)
        list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        list_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        list_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background-color: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(16)
        self.list_layout.addStretch()

        list_scroll.setWidget(self.list_container)
        page_layout.addWidget(list_scroll)
        return page

    def _set_header(self, title_text, subtitle_text, accent_color, show_back):
        self.header_title.setText(title_text)
        self.header_subtitle.setText(subtitle_text)
        self.accent_line.setStyleSheet(f"background-color: {accent_color}; border-radius: 2px;")
        self._sync_header_geometry()
        self.back_btn.setVisible(show_back)

    def _sync_header_geometry(self):
        self.title_text_container.adjustSize()
        text_height = self.title_text_container.sizeHint().height()
        self.accent_line.setFixedHeight(max(40, text_height))

    def create_project_type_card(self, project_type, config):
        tile_color, tile_gradient = self._tile_colors(project_type)

        tile = GradientFrame(tile_color, tile_gradient)
        tile.setMinimumWidth(275)
        tile.setMaximumWidth(355)
        tile.setMinimumHeight(440)
        tile.setMaximumHeight(440)
        tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tile.setCursor(Qt.CursorShape.PointingHandCursor)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        tile.setGraphicsEffect(shadow)
        tile.setStyleSheet("border-radius: 16px;")

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(26, 28, 26, 28)
        layout.setSpacing(0)

        layout.addSpacing(6)

        title_label = QLabel(config['name'])
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_primary']};
            font-size: 24px;
            font-weight: 600;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(title_label)
        layout.addSpacing(14)

        desc_label = QLabel(config['description'])
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 16px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(desc_label)
        layout.addSpacing(16)

        spec_header = QLabel("Available Specializations:")
        spec_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spec_header.setStyleSheet(f"""
            color: {self.colors['text_primary']};
            font-size: 17px;
            font-weight: 500;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(spec_header)
        layout.addSpacing(8)

        specs = config.get('specializations', [])
        spec_text = "\n".join(f"• {item}" for item in specs)
        spec_label = QLabel(spec_text)
        spec_label.setWordWrap(True)
        spec_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        spec_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 16px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(spec_label)

        button_text_map = {
            "redteam": "Start Red Project",
            "clean": "Start Blank Project",
            "blueteam": "Start Blue/SOC Project",
        }
        button_color = lighten_color(tile_color, 30)
        button_hover = lighten_color(tile_color, 40)
        button = PillButton(
            button_text_map.get(project_type, f"Start {config['name']} Project"),
            bg_color=button_color,
            hover_color=button_hover,
            pressed_color=tile_color,
            text_color=self.colors['text_primary'],
            app_font=self.app_font,
        )
        button.setFixedHeight(46)
        button.setFixedWidth(252)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self.start_project_flow(project_type))

        layout.addStretch()
        layout.addSpacing(22)
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)

        return tile

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'gradient_overlay'):
            self.gradient_overlay.setGeometry(self.rect())

    def start_project_flow(self, project_type):
        self.selected_project = project_type
        if project_type == "clean":
            self.start_project(project_type, "blank")
            return
        self.show_categories_for_project(project_type)

    def _tile_colors(self, project_type):
        if project_type == "redteam":
            return self.colors['red_team_tile'], self.colors['red_team_gradient']
        if project_type == "blueteam":
            return self.colors['blue_team_tile'], self.colors['blue_team_gradient']
        return self.colors['tile_bg'], self.colors['tile_gradient_end']

    def show_categories_for_project(self, project_type):
        self.current_project_type = project_type
        self.project_page.hide()
        self.category_page.show()
        self._set_header(
            title_text=f"Choose {self.get_project_name(project_type)} Specialization",
            subtitle_text="Select the specific investigation workflow that matches your requirements",
            accent_color=self._team_color(project_type),
            show_back=True,
        )
        self._set_menu_gradient(project_type)
        self._populate_category_list(project_type)

    def show_projects(self):
        self.category_page.hide()
        self.project_page.show()
        self.current_project_type = None
        self._set_header(
            title_text="Select Project Type",
            subtitle_text="Choose the specialized workflow for your analysis",
            accent_color="rgba(255, 255, 255, 0.65)",
            show_back=False,
        )
        self._set_menu_gradient(None)

    def get_project_name(self, project_type):
        config = PROJECT_TEMPLATES.get(project_type)
        return config['name'] if config else "Unknown"

    def _team_color(self, project_type):
        if project_type == "redteam":
            return self.colors['accent_red']
        if project_type == "blueteam":
            return self.colors['accent_blue']
        return self.colors['accent_clean']

    def _set_menu_gradient(self, project_type):
        if not hasattr(self, 'gradient_overlay'):
            return
        if project_type == "redteam":
            target = self.colors['red_team_tile']
        elif project_type == "blueteam":
            target = self.colors['blue_team_tile']
        else:
            target = self.colors['tile_bg']
        self.gradient_overlay.set_gradient_color(target, animated=True)

    def get_categories_for_project(self, project_type):
        config = PROJECT_TEMPLATES.get(project_type)
        if not config:
            return {}
        return config.get('categories', {})

    def _category_icon_path(self, category_name):
        return os.path.join(self.base_path, "assets", "icons", "category", f"{category_name}.svg")

    def _populate_category_list(self, project_type):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        categories = self.get_categories_for_project(project_type)
        for category_id, config in categories.items():
            row = self.create_category_list_item(project_type, category_id, config)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)

    def _collapse_visible_category_rows(self, except_frame=None):
        if not hasattr(self, 'list_layout'):
            return

        for i in range(self.list_layout.count()):
            item = self.list_layout.itemAt(i)
            if not item:
                continue
            widget = item.widget()
            if not widget or widget is except_frame:
                continue
            try:
                if hasattr(widget, '_collapse'):
                    widget._collapse()
            except RuntimeError:
                continue

    def create_category_list_item(self, project_type, category_id, config):
        team_color, _ = self._tile_colors(project_type)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-left: 5px solid {team_color};
                border-radius: 12px;
            }}
        """)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        frame.setMinimumHeight(86)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 0, 16, 0)
        frame_layout.setSpacing(0)

        row = QWidget()
        row.setStyleSheet("background-color: transparent; border: none;")
        row.setMinimumHeight(86)
        row.setCursor(Qt.CursorShape.PointingHandCursor)

        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 10, 4, 10)
        row_layout.setSpacing(12)

        icon_path = self._category_icon_path(config['name'])
        if os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(40, 40)))
            icon_label.setFixedSize(48, 48)
            icon_label.setStyleSheet("background-color: transparent; border: none;")
            row_layout.addWidget(icon_label)

        name_label = QLabel(config['name'])
        name_label.setStyleSheet(f"""
            color: {self.colors['text_primary']};
            font-size: 19px;
            font-weight: 600;
            font-family: {self.app_font};
            background-color: transparent;
            border: none;
        """)
        row_layout.addWidget(name_label, 1)

        arrow_label = QLabel("▶")
        arrow_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 11px;
            background-color: transparent;
            border: none;
        """)
        row_layout.addWidget(arrow_label)
        frame_layout.addWidget(row)

        detail_panel = QWidget()
        detail_panel.setStyleSheet("background-color: transparent; border: none;")
        detail_panel.setVisible(False)
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(4, 4, 4, 16)
        detail_layout.setSpacing(14)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.15); border: none; max-height: 1px;")
        detail_layout.addWidget(sep)

        desc_label = QLabel(config['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_secondary']};
            font-size: 16px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
            border: none;
        """)
        detail_layout.addWidget(desc_label)

        btn_color = lighten_color(team_color, 25)
        start_btn = QPushButton("Start Investigation")
        start_btn.setObjectName("start_investigation_btn")
        start_btn.setMinimumHeight(62)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet(f"""
            QPushButton#start_investigation_btn {{
                background-color: {btn_color};
                color: {self.colors['text_primary']};
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                font-family: {self.app_font};
                padding: 10px 24px;
                text-align: center;
            }}
            QPushButton#start_investigation_btn:hover {{
                background-color: {lighten_color(team_color, 35)};
            }}
            QPushButton#start_investigation_btn:pressed {{
                background-color: {team_color};
            }}
        """)
        start_btn.clicked.connect(lambda: self.start_project(project_type, category_id))
        detail_layout.addWidget(start_btn)

        frame_layout.addWidget(detail_panel)

        def _toggle(event=None):
            expanded = detail_panel.isVisible()
            if expanded:
                _collapse()
                return

            self._collapse_visible_category_rows(except_frame=frame)
            detail_panel.setVisible(True)
            arrow_label.setText("▼")

        def _collapse():
            detail_panel.setVisible(False)
            arrow_label.setText("▶")

        row.mousePressEvent = _toggle
        frame._collapse = _collapse
        return frame

    def start_project(self, project_type, category_id):
        self.selected_project = project_type
        self.selected_category = category_id
        self.project_selected.emit(self.selected_project, self.selected_category)
        self.accept()

    def apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['page_bg']};
                color: {self.colors['text_primary']};
                font-family: {self.app_font};
            }}

            QPushButton#cancel_btn {{
                background-color: transparent;
                color: {self.colors['text_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
            }}

            QPushButton#cancel_btn:hover {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['text_muted']};
            }}

            QPushButton#back_btn {{
                background-color: transparent;
                color: {self.colors['text_primary']};
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 6px;
            }}

            QPushButton#back_btn:hover {{
                background-color: rgba(255, 255, 255, 0.12);
            }}

            QPushButton#project_type_cta {{
                min-width: 252px;
                max-width: 252px;
                min-height: 46px;
                max-height: 46px;
                border-radius: 999px;
                padding: 0px;
            }}

            QPushButton {{
                font-family: {self.app_font};
            }}
        """)
