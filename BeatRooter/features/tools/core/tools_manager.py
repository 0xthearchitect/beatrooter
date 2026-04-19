import subprocess
import platform
import os
import shlex
import shutil
import ipaddress
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QLineEdit, QGroupBox, 
                             QMessageBox, QProgressBar, QSplitter, QFrame, QScrollArea, QApplication)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QPoint, QMimeData
from PyQt6.QtGui import QFont, QPalette, QColor, QDrag
from features.tools.docker.wsl_handler import WSLHandler
from features.tools.parsers.tools_output_parser import ToolsOutputParser
from features.tools.core.tools_downloader import ToolsDownloadManager
from features.tools.core.tool_node_service import ToolNodeService

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
                display_command = self._format_command_for_display(self.command)
                self.output_received.emit(f"Executing: {display_command}\n")
                self.output_received.emit("-" * 50 + "\n")

                process = subprocess.Popen(
                    self.command,
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

    @staticmethod
    def _format_command_for_display(command):
        try:
            return shlex.join([str(part) for part in command])
        except Exception:
            return " ".join(str(part) for part in command)


class ToolPaletteButton(QPushButton):
    AVAILABLE_BUTTON_STYLE = """
        QPushButton {
            background-color: #252525;
            color: #f0f0f0;
            border: 1px solid #353535;
            border-left: 3px solid {accent};
            border-radius: 8px;
            text-align: left;
            padding: 7px 10px 7px 16px;
        }
        QPushButton:hover {
            background-color: #2d2d2d;
            border: 1px solid #4a4a4a;
            border-left: 3px solid {accent};
        }
        QPushButton:pressed {
            background-color: #222222;
        }
        QPushButton[selected="true"] {
            background-color: #21303a;
            border: 1px solid #4e6f8d;
            border-left: 3px solid {accent};
        }
    """
    UNAVAILABLE_BUTTON_STYLE = """
        QPushButton {
            background-color: #231d20;
            color: #d8b6c4;
            border: 1px solid #46353d;
            border-left: 3px solid #925e77;
            border-radius: 8px;
            text-align: left;
            padding: 7px 10px 7px 16px;
        }
        QPushButton:disabled {
            background-color: #231d20;
            color: #d8b6c4;
            border: 1px solid #46353d;
            border-left: 3px solid #925e77;
        }
    """

    def __init__(self, tool_key, name, description, accent_color="#7aa2f7", parent=None):
        super().__init__(parent)
        self.tool_key = tool_key
        self.accent_color = accent_color or "#7aa2f7"
        self._drag_start_pos = QPoint()
        self.setProperty('tool_name', tool_key)
        self.setProperty('selected', False)
        self.setMinimumHeight(48)
        self.setStyleSheet(self._build_style(True))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 2, 2, 2)
        layout.setSpacing(2)

        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Consolas", 9, QFont.Weight.DemiBold))
        self.name_label.setStyleSheet("color: #d3d3d3;")

        self.desc_label = QLabel(description)
        self.desc_label.setFont(QFont("Consolas", 7))
        self.desc_label.setStyleSheet("color: #969696;")

        layout.addWidget(self.name_label)
        layout.addWidget(self.desc_label)

    def _build_style(self, is_available):
        accent = self.accent_color
        if is_available:
            return self.AVAILABLE_BUTTON_STYLE.replace("{accent}", accent)
        return self.UNAVAILABLE_BUTTON_STYLE

    def set_availability(self, is_available):
        self.setEnabled(is_available)
        if is_available:
            self.setStyleSheet(self._build_style(True))
            self.name_label.setStyleSheet("color: #d3d3d3;")
            self.desc_label.setStyleSheet("color: #969696;")
            return

        self.setStyleSheet(self._build_style(False))
        self.name_label.setStyleSheet("color: #c7a4b2;")
        self.desc_label.setStyleSheet("color: #a48390;")

    def set_selected(self, is_selected):
        self.setProperty('selected', bool(is_selected))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return

        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(ToolNodeService.TOOL_MIME_TYPE, self.tool_key.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

        super().mouseMoveEvent(event)

class ToolsManager(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.current_command_thread = None
        self.current_tool = None
        self.output_parser = ToolsOutputParser(main_window.graph_manager)
        self.download_manager = ToolsDownloadManager(main_window)
        self.available_tools = {}
        self.tool_buttons = {}
        self.section_boxes = []
        self.subgroup_boxes = []
        self.no_results_label = None
        self.tools_search_input = None
        
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
        title.setStyleSheet("color: #d3d3d3;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Execute security tools directly from the application")
        subtitle.setFont(QFont("Consolas", 7))
        subtitle.setStyleSheet("color: #969696;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header_frame)

        tools_group = QGroupBox("Available Tools")
        tools_group.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        tools_group.setStyleSheet("""
            QGroupBox {
                color: #9f9f9f;
                border: 1px solid #343434;
                border-radius: 2px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: #242424;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 6px 0 6px;
            }
        """)
        
        tools_layout = QVBoxLayout(tools_group)
        tools_layout.setSpacing(8)
        tools_layout.setContentsMargins(6, 12, 6, 6)

        self.tools_search_input = QLineEdit()
        self.tools_search_input.setFont(QFont("Consolas", 8))
        self.tools_search_input.setPlaceholderText("Search tools, groups, or categories...")
        self.tools_search_input.setClearButtonEnabled(True)
        self.tools_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 6px 10px;
                color: #f0f0f0;
                selection-background-color: #4b4b4b;
            }
            QLineEdit:focus {
                border: 1px solid #6880a8;
                background-color: #303030;
            }
        """)
        self.tools_search_input.textChanged.connect(self.filter_tools)
        tools_layout.addWidget(self.tools_search_input)

        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setFrameShape(QFrame.Shape.NoFrame)
        tools_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tools_scroll.setStyleSheet("""
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #4e4e4e;
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #686868;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
                height: 0px;
            }
        """)

        tools_scroll_content = QWidget()
        tools_buttons_layout = QVBoxLayout(tools_scroll_content)
        tools_buttons_layout.setSpacing(8)
        tools_buttons_layout.setContentsMargins(0, 0, 0, 0)

        self.tool_buttons = {}
        self.section_boxes = []
        self.subgroup_boxes = []
        for section in ToolNodeService.get_tool_sidebar_sections():
            section_box = self.create_tool_section_box(section)
            if section_box:
                tools_buttons_layout.addWidget(section_box)

        tools_buttons_layout.addStretch()
        tools_scroll.setWidget(tools_scroll_content)
        tools_layout.addWidget(tools_scroll)

        self.no_results_label = QLabel("No tools match the current filter.")
        self.no_results_label.setFont(QFont("Consolas", 8))
        self.no_results_label.setStyleSheet("color: #9f9f9f; padding: 4px 2px;")
        self.no_results_label.setVisible(False)
        tools_layout.addWidget(self.no_results_label)

        main_layout.addWidget(tools_group)

        command_group = QGroupBox("Command Configuration")
        command_group.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        command_group.setStyleSheet("""
            QGroupBox {
                color: #9f9f9f;
                border: 1px solid #343434;
                border-radius: 2px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: #242424;
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
        target_label.setStyleSheet("color: #d3d3d3; min-width: 60px;")
        target_layout.addWidget(target_label)
        
        self.target_input = QLineEdit()
        self.target_input.setFont(QFont("Consolas", 8))
        self.target_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 4px 6px;
                color: #f0f0f0;
                selection-background-color: #4b4b4b;
            }
            QLineEdit:focus {
                border: 1px solid #6a6a6a;
                background-color: #303030;
            }
        """)
        self.target_input.setPlaceholderText("Enter target...")
        target_layout.addWidget(self.target_input)
        command_layout.addLayout(target_layout)

        options_layout = QHBoxLayout()
        options_label = QLabel("Options:")
        options_label.setFont(QFont("Consolas", 8))
        options_label.setStyleSheet("color: #d3d3d3; min-width: 60px;")
        options_layout.addWidget(options_label)
        
        self.options_input = QLineEdit()
        self.options_input.setFont(QFont("Consolas", 8))
        self.options_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 4px 6px;
                color: #f0f0f0;
                selection-background-color: #4b4b4b;
            }
            QLineEdit:focus {
                border: 1px solid #6a6a6a;
                background-color: #303030;
            }
        """)
        self.options_input.setPlaceholderText("e.g., -p 80,443")
        options_layout.addWidget(self.options_input)
        command_layout.addLayout(options_layout)

        custom_layout = QHBoxLayout()
        custom_label = QLabel("Custom:")
        custom_label.setFont(QFont("Consolas", 8))
        custom_label.setStyleSheet("color: #d3d3d3; min-width: 60px;")
        custom_layout.addWidget(custom_label)
        
        self.custom_input = QLineEdit()
        self.custom_input.setFont(QFont("Consolas", 8))
        self.custom_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 4px 6px;
                color: #f0f0f0;
                selection-background-color: #4b4b4b;
            }
            QLineEdit:focus {
                border: 1px solid #6a6a6a;
                background-color: #303030;
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
                background-color: #2b2b2b;
                color: #dddddd;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 6px 12px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #313131;
                border: 1px solid #4a4a4a;
                color: #f5f5f5;
            }
            QPushButton:pressed {
                background-color: #262626;
            }
            QPushButton:disabled {
                background-color: #242424;
                color: #777777;
                border: 1px solid #333333;
            }
        """)
        self.execute_btn.clicked.connect(self.execute_current_command)
        self.execute_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFont(QFont("Consolas", 8))
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: #dddddd;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #313131;
                border: 1px solid #4a4a4a;
                color: #f5f5f5;
            }
            QPushButton:pressed {
                background-color: #262626;
            }
            QPushButton:disabled {
                background-color: #242424;
                color: #777777;
                border: 1px solid #333333;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_current_command)
        self.stop_btn.setEnabled(False)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFont(QFont("Consolas", 8))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b2b;
                color: #dddddd;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #313131;
                border: 1px solid #4a4a4a;
                color: #f5f5f5;
            }
            QPushButton:pressed {
                background-color: #262626;
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
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                text-align: center;
                background-color: #2b2b2b;
                color: #d3d3d3;
                height: 4px;
            }
            QProgressBar::chunk {
                background-color: #4e4e4e;
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
                color: #9f9f9f;
                border: 1px solid #343434;
                border-radius: 2px;
                margin-top: 10px;
                padding-top: 8px;
                background-color: #242424;
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
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                color: #f0f0f0;
                padding: 6px;
                selection-background-color: #4b4b4b;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #4e4e4e;
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #686868;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                border: none;
                height: 0px;
            }
        """)
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(90)
        self.output_text.setMaximumHeight(170)
        output_layout.addWidget(self.output_text)

        main_layout.addWidget(output_group)

        self.connect_tool_buttons()

    def create_tool_section_box(self, section):
        if not section or not section.get("groups"):
            return None

        accent = section.get("accent", "#7aa2f7")
        section_key = section.get("key", "")
        section_box = QFrame()
        section_box.setObjectName("ToolSectionCard")
        section_box.setStyleSheet(f"""
            QFrame#ToolSectionCard {{
                background-color: #1f1f1f;
                border: 1px solid #333333;
                border-radius: 14px;
            }}
        """)

        section_layout = QVBoxLayout(section_box)
        section_layout.setSpacing(8)
        section_layout.setContentsMargins(10, 10, 10, 10)
        section_box.section_key = section_key
        section_box.section_label = section.get("label", "")
        section_box.subgroup_boxes = []

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        accent_bar = QFrame()
        accent_bar.setFixedWidth(4)
        accent_bar.setStyleSheet(f"background-color: {accent}; border-radius: 2px;")
        header_layout.addWidget(accent_bar)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.setContentsMargins(0, 0, 0, 0)

        title = QLabel(section.get("label", "Tools"))
        title.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #f3f3f3;")

        subtitle = QLabel(section.get("description", ""))
        subtitle.setFont(QFont("Consolas", 7))
        subtitle.setStyleSheet("color: #9c9c9c;")
        subtitle.setWordWrap(True)

        title_stack.addWidget(title)
        if subtitle.text().strip():
            title_stack.addWidget(subtitle)

        title_container = QWidget()
        title_container.setLayout(title_stack)
        header_layout.addWidget(title_container, 1)

        counts_container = QWidget()
        counts_layout = QHBoxLayout(counts_container)
        counts_layout.setContentsMargins(0, 0, 0, 0)
        counts_layout.setSpacing(6)
        counts_layout.addWidget(self.create_count_badge(f"{section.get('group_count', 0)} groups"))
        counts_layout.addWidget(self.create_count_badge(f"{section.get('tool_count', 0)} tools"))
        header_layout.addWidget(counts_container, 0, Qt.AlignmentFlag.AlignTop)

        section_layout.addWidget(header)

        for subgroup in section.get("groups", []):
            subgroup_box = self.create_tool_subgroup_box(subgroup, section)
            if subgroup_box:
                section_box.subgroup_boxes.append(subgroup_box)
                section_layout.addWidget(subgroup_box)

        self.section_boxes.append(section_box)

        return section_box

    def create_tool_subgroup_box(self, subgroup, section):
        tools = list(subgroup.get("tools", []))
        if not tools:
            return None

        subgroup_box = QFrame()
        subgroup_box.setObjectName("ToolSubgroupCard")
        subgroup_box.setStyleSheet("""
            QFrame#ToolSubgroupCard {
                background-color: #202020;
                border: 1px solid #2f2f2f;
                border-radius: 12px;
            }
        """)

        subgroup_layout = QVBoxLayout(subgroup_box)
        subgroup_layout.setSpacing(6)
        subgroup_layout.setContentsMargins(8, 8, 8, 8)
        subgroup_box.section_key = section.get("key", "")
        subgroup_box.section_label = section.get("label", "")
        subgroup_box.subgroup_label = subgroup.get("label", "")
        subgroup_box.tool_keys = tools

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        label = QLabel(subgroup.get("label", "Group"))
        label.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        label.setStyleSheet("color: #e4e4e4;")

        header_layout.addWidget(label)
        header_layout.addStretch()
        header_layout.addWidget(self.create_count_badge(f"{len(tools)} tools"))

        subgroup_layout.addLayout(header_layout)

        for tool_key in tools:
            spec = ToolNodeService.get_tool_spec(tool_key)
            button = self.create_tool_button(
                tool_key,
                spec.get("name", tool_key.title()),
                spec.get("description", ""),
                spec.get("color", "#7aa2f7"),
            )
            self.tool_buttons[tool_key] = button
            subgroup_layout.addWidget(button)

        self.subgroup_boxes.append(subgroup_box)

        return subgroup_box

    def create_count_badge(self, text):
        badge = QLabel(text)
        badge.setFont(QFont("Consolas", 7, QFont.Weight.DemiBold))
        badge.setStyleSheet("""
            QLabel {
                color: #d8d8d8;
                background-color: #2a2a2a;
                border: 1px solid #393939;
                border-radius: 10px;
                padding: 3px 8px;
            }
        """)
        return badge

    def create_tool_button(self, tool_key, name, description, accent_color="#7aa2f7"):
        button = ToolPaletteButton(tool_key, name, description, accent_color, self)
        button.clicked.connect(lambda _, key=tool_key: self.select_tool(key))
        return button

    def connect_tool_buttons(self):
        # Buttons are connected when created in create_tool_button.
        return

    def filter_tools(self, query_text):
        query = str(query_text or "").strip().lower()

        visible_tool_count = 0
        for tool_key, button in self.tool_buttons.items():
            spec = ToolNodeService.get_tool_spec(tool_key)
            searchable = " ".join(
                [
                    tool_key,
                    str(spec.get("name", "")),
                    str(spec.get("description", "")),
                    ToolNodeService.get_tool_sidebar_group(tool_key),
                    ToolNodeService.get_tool_sidebar_section(tool_key),
                ]
            ).lower()
            is_visible = not query or query in searchable
            button.setVisible(is_visible)
            if is_visible:
                visible_tool_count += 1

        for subgroup_box in self.subgroup_boxes:
            any_tool_visible = False
            for tool_key in getattr(subgroup_box, "tool_keys", []):
                button = self.tool_buttons.get(tool_key)
                if button and not button.isHidden():
                    any_tool_visible = True
                    break
            subgroup_box.setVisible(any_tool_visible)

        for section_box in self.section_boxes:
            any_subgroup_visible = any(
                not subgroup.isHidden() for subgroup in getattr(section_box, "subgroup_boxes", [])
            )
            section_box.setVisible(any_subgroup_visible)

        if self.no_results_label is not None:
            self.no_results_label.setVisible(visible_tool_count == 0)

    def update_tool_availability(self, tool_name, is_available):
        button = self.tool_buttons.get(tool_name)
        if button:
            if is_available:
                button.set_availability(True)
                button.setToolTip("")
            else:
                button.set_availability(False)
                button.setToolTip(f"{ToolNodeService.get_tool_display_name(tool_name)} não encontrado. Clique em 'Manage Tools' para instalar.")

    def check_and_request_tools(self):
        self.check_available_tools()

    def check_available_tools(self):
        tools_to_check = ToolNodeService.list_tool_names()
        
        for tool_name in tools_to_check:
            is_available = self.download_manager.is_tool_available(tool_name)
            self.available_tools[tool_name] = is_available
            self.update_tool_availability(tool_name, is_available)

        if self.tools_search_input is not None:
            self.filter_tools(self.tools_search_input.text())

    def check_tool_availability(self, tool_name):
        try:
            if platform.system() == "Windows":
                result = subprocess.run(['where', tool_name], capture_output=True, text=True)
            else:
                result = subprocess.run(['which', tool_name], capture_output=True, text=True)
            
            return result.returncode == 0
        except Exception:
            return False

    def _split_cli(self, value):
        if not value:
            return []
        try:
            return shlex.split(value, posix=platform.system() != "Windows")
        except ValueError:
            return str(value).split()

    def _split_tool_path(self, tool_path):
        if not tool_path:
            return []
        if tool_path.startswith("wsl "):
            return tool_path.split()
        return self._split_cli(tool_path)

    def get_command_for_tool(self, tool_name, target, options, wordlist_path=None, login_value=None):
        try:
            tool_name = ToolNodeService.get_tool_command_name(tool_name)
            target = str(target or "").strip()
            option_parts = self._split_cli(options)
            command_name = ToolNodeService.get_tool_command_name(tool_name)
            tool_path = self.download_manager.get_tool_path(tool_name) or self.download_manager.get_tool_path(command_name)

            if not tool_path:
                raise Exception(f"Ferramenta {tool_name} não disponível. Instale via 'Manage Tools'.")

            base_parts = self._split_tool_path(tool_path)
            if not base_parts:
                raise Exception(f"Comando inválido para {tool_name}.")

            append_target = [target] if target else []

            if tool_name == "gobuster":
                return self.get_gobuster_command(target, options, base_parts, wordlist_path=wordlist_path)
            if tool_name == "masscan":
                return self.get_masscan_command(target, options, base_parts)
            if tool_name in {"nslookup", "dnsutils"}:
                return self.get_dnsutils_command(target, option_parts, base_parts)
            if tool_name == "subfinder":
                return base_parts + ["-d", target] + option_parts
            if tool_name == "amass":
                return base_parts + (option_parts if option_parts else ["enum", "-passive"]) + ["-d", target]
            if tool_name == "nmap":
                return base_parts + (option_parts if option_parts else ["-sV", "-sC"]) + append_target
            if tool_name == "sqlmap":
                defaults = ["--batch", "--random-agent"]
                return base_parts + ["-u", target] + (option_parts if option_parts else defaults)
            if tool_name == "enum4linux":
                return base_parts + (option_parts if option_parts else ["-a"]) + append_target
            if tool_name == "rpcclient":
                return base_parts + (option_parts if option_parts else ["-N", "-c", "help"]) + append_target
            if tool_name == "searchsploit":
                return base_parts + append_target + option_parts
            if tool_name == "netcat":
                return self.get_netcat_command(target, option_parts, base_parts)
            if tool_name == "hydra":
                return self.get_hydra_command(
                    target,
                    option_parts,
                    base_parts,
                    wordlist_path=wordlist_path,
                    login_value=login_value,
                )
            if tool_name == "steghide":
                return self.get_steghide_command(target, option_parts, base_parts)
            if tool_name in {"patator", "hashcat", "john"}:
                return base_parts + (option_parts if option_parts else ["--help"]) + append_target
            if tool_name in {"linpeas", "wifite"}:
                return base_parts + (option_parts if option_parts else [])
            if tool_name == "revshellgen":
                return base_parts + option_parts + append_target
            if tool_name == "tshark":
                return self.get_tshark_command(target, option_parts, base_parts)

            if tool_name in {"exiftool", "binwalk", "strings", "ghidra", "whatweb", "whois", "cupp"}:
                return base_parts + option_parts + append_target

            return base_parts + option_parts + append_target

        except Exception as e:
            QMessageBox.warning(self, "Erro de Ferramenta", f"Erro ao preparar {tool_name}: {str(e)}")
            return []

    def get_masscan_command(self, target, options, base_parts):
        base_cmd = list(base_parts)
        if base_cmd[:1] == ['wsl'] and len(base_cmd) > 1 and base_cmd[1] != 'sudo':
            base_cmd = ['wsl', 'sudo'] + base_cmd[1:]

        default_options = [
            '--rate', '1000000',
            '--open-only',
            '-oL', '-'
        ]

        base_cmd += ['-p0-65535', target]

        if options:
            user_options = self._split_cli(options)
            return base_cmd + user_options

        return base_cmd + default_options

    def get_tshark_command(self, target, option_parts, base_parts):
        base_cmd = list(base_parts)
        options = list(option_parts or [])

        has_interface = any(opt in options for opt in ["-i", "--interface"])
        has_read_file = any(opt in options for opt in ["-r", "--read-file"])
        has_stop_condition = any(opt in options for opt in ["-c", "-a", "--autostop"])
        has_output_format = "-T" in options
        has_name_resolution_flag = "-n" in options
        parse_friendly_fields = [
            "-T", "fields",
            "-E", "header=n",
            "-E", "separator=,",
            "-e", "ip.src",
            "-e", "ip.dst",
            "-e", "tcp.dstport",
            "-e", "udp.dstport",
            "-e", "_ws.col.Protocol",
        ]

        if not has_name_resolution_flag:
            options = ["-n"] + options

        if has_interface or has_read_file:
            if not has_output_format:
                options += parse_friendly_fields
            return base_cmd + options

        if target and os.path.exists(target):
            if not has_output_format:
                options += parse_friendly_fields
            return base_cmd + ["-r", target] + options

        if target:
            capture_cmd = base_cmd + ["-i", target]
            if not has_stop_condition:
                capture_cmd += ["-c", "50"]
            if not has_output_format:
                capture_cmd += parse_friendly_fields
            return capture_cmd + options

        return base_cmd + options

    def get_netcat_command(self, target, option_parts, base_parts):
        base_cmd = list(base_parts)
        options = list(option_parts or [])
        target_value = str(target or "").strip()

        # Respect explicit options from the user.
        if options:
            return base_cmd + ([target_value] if target_value else []) + options

        # Useful default: quick TCP scan on common ports when a target exists.
        if target_value:
            return base_cmd + ["-zv", "-w", "2", target_value, "20-1024"]

        # No target and no options -> show usage/help.
        return base_cmd + ["-h"]

    def get_hydra_command(self, target, option_parts, base_parts, wordlist_path=None, login_value=None):
        base_cmd = list(base_parts)
        options = list(option_parts or [])
        target_value = str(target or "").strip()
        target_is_uri = target_value and "://" in target_value
        resolved_login = str(login_value or "").strip()

        def _flag_with_value_present(tokens, short_flag):
            # Accept inline form (e.g. -ladmin, -Pwordlist.txt) or separated form (-l admin).
            for idx, token in enumerate(tokens):
                tok = str(token)
                if tok.startswith(short_flag) and tok != short_flag:
                    return True
                if tok == short_flag:
                    if idx + 1 < len(tokens):
                        nxt = str(tokens[idx + 1]).strip()
                        if nxt and not nxt.startswith("-"):
                            return True
            return False

        if not options and target_is_uri:
            if resolved_login:
                base_cmd += ["-l", resolved_login]
            if wordlist_path:
                return base_cmd + ["-P", wordlist_path, target_value]
            return base_cmd + [target_value]

        if not options:
            raise Exception(
                "Hydra requer Options com serviço/módulo (ex.: ssh, ftp ou URI service://host)."
            )

        has_combo_file = _flag_with_value_present(options, "-C")
        has_login_source = _flag_with_value_present(options, "-l") or _flag_with_value_present(options, "-L")
        has_password_source = _flag_with_value_present(options, "-p") or _flag_with_value_present(options, "-P")
        has_generator = _flag_with_value_present(options, "-x") or _flag_with_value_present(options, "-e")

        if resolved_login and not has_combo_file and not has_login_source:
            options = ["-l", resolved_login] + options
            has_login_source = True

        if wordlist_path and not has_combo_file and not has_password_source and not has_generator:
            options = options + ["-P", wordlist_path]
            has_password_source = True

        if target_is_uri:
            return base_cmd + options + [target_value]

        # If user already provided URI syntax, do not append target again.
        if any("://" in token for token in options):
            return base_cmd + options

        hydra_services = {
            "adam6500", "asterisk", "afp", "cisco", "cisco-enable", "cobaltstrike",
            "cvs", "firebird", "ftp", "ftps", "http-get", "http-post",
            "https-get", "https-post", "http-get-form", "http-post-form",
            "https-get-form", "https-post-form", "http-proxy", "http-proxy-urlenum",
            "imap", "imaps", "irc", "ldap2", "ldap2s", "ldap3", "ldap3s",
            "memcached", "mongodb", "mssql", "mysql", "nntp", "oracle-listener",
            "oracle-sid", "pcanywhere", "pcnfs", "pop3", "pop3s", "postgres",
            "radmin2", "rdp", "redis", "rexec", "rlogin", "rpcap", "rsh",
            "rtsp", "sip", "smb", "smtp", "smtps", "smtp-enum", "snmp",
            "socks5", "ssh", "sshkey", "svn", "teamspeak", "telnet", "telnets",
            "vmauthd", "vnc", "xmpp",
        }
        service_indexes = [
            idx for idx, token in enumerate(options)
            if str(token).lower() in hydra_services
        ]
        has_service = bool(service_indexes)
        has_target_in_options = target_value and any(token == target_value for token in options)

        if not has_service:
            raise Exception(
                "Hydra requer o serviço em Options (ex.: ssh, ftp, smb) "
                "ou URI completa service://host."
            )

        if not has_combo_file and not has_login_source:
            raise Exception("Hydra requer pelo menos utilizador (-l/-L) ou combo file (-C).")
        if not has_combo_file and not (has_password_source or has_generator):
            raise Exception("Hydra requer password source (-p/-P) ou geração (-x/-e), ou use -C.")

        if not target_value or has_target_in_options:
            ordered = list(options)
        else:
            # Hydra syntax expects: hydra [options] target service
            # If service token is present in options, place target just before the first service token.
            insert_at = service_indexes[0]
            ordered = options[:insert_at] + [target_value] + options[insert_at:]

        # SSH defaults can be noisy in parallel mode; set conservative tasks if user did not define one.
        has_tasks_option = any(
            token == "-t" or str(token).startswith("-t")
            for token in ordered
        )
        if "ssh" in [str(token).lower() for token in ordered] and not has_tasks_option:
            ordered = ["-t", "4"] + ordered

        return base_cmd + ordered

    def get_dnsutils_command(self, target, option_parts, base_parts):
        # Respect explicit user options exactly as provided.
        if option_parts:
            return list(base_parts) + ([target] if target else []) + list(option_parts)

        target_value = str(target or "").strip()
        if not target_value:
            return list(base_parts)

        dig_bin = shutil.which("dig")
        host_bin = shutil.which("host")

        target_is_ip = False
        try:
            ipaddress.ip_address(target_value)
            target_is_ip = True
        except ValueError:
            target_is_ip = False

        # Default strategy:
        # - IP target: reverse lookup with dig (or host fallback).
        # - Domain target: richer enumeration with host -a (or nslookup -type=any fallback).
        if target_is_ip:
            if dig_bin:
                return [dig_bin, "+nocmd", "+noall", "+answer", "-x", target_value]
            if host_bin:
                return [host_bin, target_value]
            return list(base_parts) + [target_value]

        if host_bin:
            return [host_bin, "-a", target_value]

        base_cmd = list(base_parts)
        cmd_name = os.path.basename(base_cmd[0]) if base_cmd else ""
        if cmd_name in {"nslookup", "nslookup.exe"}:
            return base_cmd + ["-type=any", target_value]
        return base_cmd + [target_value]

    def get_steghide_command(self, target, option_parts, base_parts):
        base_cmd = list(base_parts)
        options = list(option_parts or [])
        target_value = str(target or "").strip()
        steghide_commands = {"embed", "extract", "info", "encinfo"}
        has_passphrase = any(
            token in {"-p", "--passphrase"} or str(token).startswith("--passphrase=")
            for token in options
        )

        if not options:
            if target_value:
                return base_cmd + ["info", "-p", "", target_value]
            return base_cmd + ["--help"]

        first_token = str(options[0]).lower()
        if first_token in steghide_commands:
            if first_token == "info":
                info_args = list(options)
                if not has_passphrase:
                    info_args += ["-p", ""]
                if target_value and target_value not in info_args[1:]:
                    info_args.append(target_value)
                return base_cmd + info_args
            return base_cmd + options

        info_args = ["info"] + options
        if not has_passphrase:
            info_args += ["-p", ""]
        if target_value:
            info_args.append(target_value)
        return base_cmd + info_args

    def select_tool(self, tool_name):
        self.current_tool = tool_name
        self.target_input.clear()
        self.options_input.clear()
        self.custom_input.clear()

        for key, button in self.tool_buttons.items():
            button.set_selected(key == tool_name)

        self.target_input.setPlaceholderText(ToolNodeService.get_tool_target_placeholder(tool_name))
        self.execute_btn.setEnabled(True)

        self.output_text.append(f"> Selected tool: {ToolNodeService.get_tool_display_name(tool_name)}")

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

    def get_gobuster_command(self, target, options, base_parts, wordlist_path=None):
        base_cmd = list(base_parts) + ['dir', '-u', target, '-q']
        default_blacklist_codes = '404,429,500,502,503,504'
        
        fast_settings = [
            '--timeout', '8s',
            '-t', '4',
            '--delay', '200ms',
            '-r',
            '--no-error',
            '-b', default_blacklist_codes,
            '-k',
        ]
        
        if options:
            user_options = self._split_cli(options)
            has_wordlist = any(opt in user_options for opt in ['-w', '--wordlist'])
            has_status_list = any(
                opt in user_options
                for opt in [
                    '-s',
                    '--status-codes',
                ]
            )
            has_status_blacklist = any(
                opt in user_options
                for opt in [
                    '-b',
                    '--status-codes-blacklist',
                ]
            )
            has_wildcard_controls = any(
                opt in user_options
                for opt in [
                    '--wildcard',
                    '--exclude-length',
                ]
            )

            if has_status_list and not has_status_blacklist and not has_wildcard_controls:
                # Gobuster defaults status-codes-blacklist to 404. If user sets -s,
                # disable blacklist explicitly to avoid "both set" runtime error.
                user_options.extend(['-b', ''])
            elif not has_status_list and not has_status_blacklist and not has_wildcard_controls:
                user_options.extend(['-b', default_blacklist_codes])

            if '-k' not in user_options and '--no-tls-validation' not in user_options:
                user_options.append('-k')
            if wordlist_path and not has_wordlist:
                user_options.extend(['-w', wordlist_path])
            return base_cmd + user_options

        if wordlist_path:
            return base_cmd + fast_settings + ['-w', wordlist_path]

        wordlist_path = self.setup_gobuster_wordlist()
        return base_cmd + fast_settings + ['-w', wordlist_path]

    def execute_current_command(self):
        if not getattr(self, 'current_tool', None):
            QMessageBox.warning(self, "No Tool Selected", "Please select a tool first.")
            return

        target = self.target_input.text().strip()
        if ToolNodeService.tool_requires_target(self.current_tool) and not target:
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
            command_parts = self._split_cli(custom_cmd)
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

        if str(tool_name or "").strip().lower() == "revshellgen":
            self.output_text.clear()
            self.output_text.append(
                "RevShellGen requer um terminal interativo (TTY real) e não funciona no runner embutido da app.\n"
                "Execute `~/.local/bin/revshellgen` diretamente num terminal para usar o menu interativo."
            )
            self.progress_bar.setVisible(False)
            self.execute_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            return
        
        if (platform.system() == "Windows" and
            tool_name and
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
        if command_parts and command_parts[0] == 'wsl':
            return command_parts
        if tool_name in ['subfinder', 'amass']:
            return ['wsl', tool_name] + command_parts[1:]
        
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

    def _friendly_runtime_error(self, tool_name, output_text):
        tool_name = str(tool_name or "").strip().lower()
        normalized_output = str(output_text or "").lower()

        if tool_name == "revshellgen":
            if "inappropriate ioctl for device" in normalized_output or "termios.error" in normalized_output:
                return (
                    "RevShellGen requer um terminal interativo (TTY real) e não funciona no runner embutido da app.\n"
                    "Execute `~/.local/bin/revshellgen` diretamente num terminal para usar o menu interativo."
                )

        return ""

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
            friendly_error = self._friendly_runtime_error(
                getattr(self, 'current_tool', ''),
                self.output_text.toPlainText(),
            )
            if friendly_error:
                self.output_text.append(f"\n*** {friendly_error} ***")
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
