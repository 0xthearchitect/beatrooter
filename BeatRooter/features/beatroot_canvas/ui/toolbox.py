from PyQt6.QtCore import QSize, pyqtSignal, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from features.beatroot_canvas.core import NodeFactory
from features.beatroot_canvas.ui.custom_node_dialog import CustomNodeDialog
from features.beatroot_canvas.ui.node_settings_dialog import NodeSettingsDialog


class ToolboxWidget(QWidget):
    node_created = pyqtSignal(str)
    custom_template_created = pyqtSignal(str)
    node_settings_changed = pyqtSignal()
    tools_requested = pyqtSignal()

    COLLAPSED_WIDTH = 72
    RAIL_WIDTH = 72
    RAIL_HEIGHT = 248
    DRAWER_WIDTH = 248
    COLLAPSED_HEIGHT = 248
    EXPANDED_MIN_HEIGHT = 420
    EXPANDED_MAX_HEIGHT = 620

    def __init__(self, graph_manager, current_category=None):
        super().__init__()
        self.graph_manager = graph_manager
        self.current_category = NodeFactory.normalize_category(current_category)
        self.expanded_categories = {}
        self.expandable_sections = []
        self.drawer_open = False
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("FloatingToolboxRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        self.rail_frame = QFrame()
        self.rail_frame.setObjectName("FloatingToolboxRail")
        self.rail_frame.setFixedWidth(self.RAIL_WIDTH)
        self.rail_frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        rail_layout = QVBoxLayout(self.rail_frame)
        rail_layout.setContentsMargins(8, 10, 8, 10)
        rail_layout.setSpacing(10)

        self.toggle_btn = self._create_rail_button("+", "Open quick node menu", self.toggle_drawer, primary=True)
        self.search_btn = self._create_rail_button("⌕", "Open search", self.open_drawer_and_focus_search)
        self.sections_btn = self._create_rail_button("⇅", "Expand/collapse categories", self.open_drawer_and_toggle_sections)
        self.sections_btn.setProperty("railCompactGlyph", True)
        self.settings_btn = self._create_rail_button("⚙", "Node settings", self.configure_node_settings)
        self.settings_btn.setProperty("railLargeGlyph", True)

        rail_layout.addWidget(self.toggle_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addWidget(self.search_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addWidget(self.sections_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_layout.addStretch()

        self.drawer_frame = QFrame()
        self.drawer_frame.setObjectName("FloatingToolboxDrawer")
        drawer_layout = QVBoxLayout(self.drawer_frame)
        drawer_layout.setContentsMargins(16, 16, 16, 16)
        drawer_layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(10)

        title_block = QVBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(2)

        eyebrow = QLabel("QUICK ACTIONS")
        eyebrow.setObjectName("ToolboxEyebrow")
        title_block.addWidget(eyebrow)

        self.title_label = QLabel("Nodes")
        self.title_label.setObjectName("ToolboxTitle")
        title_block.addWidget(self.title_label)

        header_row.addLayout(title_block, 1)

        header_actions = QVBoxLayout()
        header_actions.setContentsMargins(0, 0, 0, 0)
        header_actions.setSpacing(8)

        self.node_count_label = QLabel("0 / 0")
        self.node_count_label.setObjectName("NodeCountBadge")
        self.node_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_actions.addWidget(self.node_count_label, 0, Qt.AlignmentFlag.AlignRight)

        self.close_btn = QToolButton()
        self.close_btn.setObjectName("DrawerCloseButton")
        self.close_btn.setText("×")
        self.close_btn.setToolTip("Collapse quick menu")
        self.close_btn.clicked.connect(self.close_drawer)
        header_actions.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignRight)
        header_actions.addStretch()

        header_row.addLayout(header_actions)
        drawer_layout.addLayout(header_row)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("ToolboxSearchInput")
        self.search_input.setPlaceholderText("Search nodes...")
        self.search_input.setMinimumHeight(34)
        self.search_input.textChanged.connect(self.filter_nodes)
        drawer_layout.addWidget(self.search_input)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)

        self.filter_combo = QComboBox()
        self.filter_combo.setObjectName("ToolboxFilterCombo")
        self.refresh_filter_categories()
        self.filter_combo.currentIndexChanged.connect(self.filter_nodes)
        filter_row.addWidget(self.filter_combo, 1)

        self.expand_all_btn = QPushButton("Expand")
        self.expand_all_btn.setObjectName("ToolboxGhostButton")
        self.expand_all_btn.clicked.connect(self.toggle_all_sections)
        filter_row.addWidget(self.expand_all_btn)
        drawer_layout.addLayout(filter_row)

        self.custom_node_btn = QPushButton("Create custom node")
        self.custom_node_btn.setObjectName("CustomNodeBtn")
        self.custom_node_btn.setMinimumHeight(34)
        self.custom_node_btn.clicked.connect(self.create_custom_node_template)
        drawer_layout.addWidget(self.custom_node_btn)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ToolboxScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_host = QWidget()
        scroll_host.setObjectName("ToolboxScrollHost")
        self.scroll_layout = QVBoxLayout(scroll_host)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)
        self.scroll_area.setWidget(scroll_host)
        drawer_layout.addWidget(self.scroll_area, 1)

        root_layout.addWidget(self.rail_frame, 0, Qt.AlignmentFlag.AlignTop)
        root_layout.addWidget(self.drawer_frame)

        self.apply_styles()
        self._apply_shadow(self.rail_frame, blur_radius=22, y_offset=8, alpha=90)
        self._apply_shadow(self.drawer_frame, blur_radius=28, y_offset=10, alpha=110)

        self.refresh_header()
        self.create_sections()
        self.filter_nodes()
        self._apply_drawer_state()

    def apply_styles(self):
        self.setStyleSheet(
            """
            QWidget#FloatingToolboxRoot {
                background: transparent;
            }
            QFrame#FloatingToolboxRail {
                background: rgba(9, 16, 27, 236);
                border: 1px solid rgba(76, 101, 145, 150);
                border-radius: 26px;
            }
            QToolButton[railButton="true"] {
                min-width: 42px;
                max-width: 42px;
                min-height: 42px;
                max-height: 42px;
                background: rgba(15, 25, 40, 242);
                color: #dbe7ff;
                border: 1px solid rgba(81, 108, 154, 145);
                border-radius: 15px;
                font-size: 17px;
                font-weight: 700;
                font-family: 'DejaVu Sans', 'Segoe UI Symbol';
            }
            QToolButton[railLargeGlyph="true"] {
                font-size: 22px;
            }
            QToolButton[railCompactGlyph="true"] {
                font-size: 13px;
                padding: 0px;
                qproperty-toolButtonStyle: ToolButtonTextOnly;
            }
            QToolButton#RailPrimaryButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #3478ff,
                    stop: 1 #1e47cf
                );
                border: 1px solid rgba(118, 157, 255, 235);
            }
            QToolButton[railButton="true"]:hover {
                background: rgba(24, 39, 61, 250);
                border: 1px solid rgba(113, 146, 201, 220);
                color: #ffffff;
            }
            QToolButton#RailPrimaryButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #4e8cff,
                    stop: 1 #2758ea
                );
            }
            QToolButton[railButton="true"]:pressed {
                background: rgba(33, 53, 82, 255);
            }
            QFrame#FloatingToolboxDrawer {
                background: rgba(8, 13, 22, 240);
                border: 1px solid rgba(83, 109, 153, 158);
                border-radius: 24px;
            }
            QLabel#ToolboxEyebrow {
                color: #7d9ad1;
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QLabel#ToolboxTitle {
                color: #f5f8ff;
                font-size: 17px;
                font-weight: 700;
            }
            QLabel#NodeCountBadge {
                background: rgba(23, 39, 67, 235);
                color: #eff5ff;
                border: 1px solid rgba(94, 127, 182, 194);
                border-radius: 11px;
                padding: 5px 8px;
                font-size: 10px;
                font-weight: 700;
                min-width: 62px;
            }
            QToolButton#DrawerCloseButton {
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                border: 1px solid rgba(82, 106, 144, 158);
                border-radius: 12px;
                background: rgba(16, 26, 43, 240);
                color: #cfe0ff;
                font-size: 14px;
                font-weight: 700;
            }
            QToolButton#DrawerCloseButton:hover {
                background: rgba(29, 46, 72, 255);
                color: #ffffff;
            }
            QLineEdit#ToolboxSearchInput,
            QComboBox#ToolboxFilterCombo {
                background: rgba(14, 22, 36, 247);
                color: #f2f6ff;
                border: 1px solid rgba(71, 92, 128, 145);
                border-radius: 12px;
                padding: 7px 10px;
                selection-background-color: #436fcb;
            }
            QLineEdit#ToolboxSearchInput:focus,
            QComboBox#ToolboxFilterCombo:focus {
                border: 1px solid rgba(108, 146, 224, 242);
            }
            QComboBox#ToolboxFilterCombo::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox#ToolboxFilterCombo::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #90abd9;
                margin-right: 7px;
            }
            QComboBox#ToolboxFilterCombo QAbstractItemView {
                background: #0d1524;
                color: #ebf2ff;
                border: 1px solid rgba(81, 104, 145, 219);
                selection-background-color: #27426e;
            }
            QPushButton#ToolboxGhostButton,
            QPushButton#CustomNodeBtn {
                min-height: 34px;
                border-radius: 12px;
                font-size: 10px;
                font-weight: 700;
                padding: 7px 10px;
            }
            QPushButton#ToolboxGhostButton {
                background: rgba(15, 23, 36, 242);
                color: #d7e5fb;
                border: 1px solid rgba(73, 96, 132, 153);
            }
            QPushButton#ToolboxGhostButton:hover {
                background: rgba(26, 39, 59, 255);
                border: 1px solid rgba(113, 146, 201, 214);
                color: #ffffff;
            }
            QPushButton#CustomNodeBtn {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2458cf,
                    stop: 1 #1b3da4
                );
                color: #f6fbff;
                border: 1px solid rgba(102, 137, 213, 189);
            }
            QPushButton#CustomNodeBtn:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #2f69ef,
                    stop: 1 #224cc8
                );
            }
            QScrollArea#ToolboxScrollArea,
            QWidget#ToolboxScrollHost {
                background: transparent;
                border: none;
            }
            QGroupBox[toolSectionGroup="true"] {
                background: rgba(12, 19, 31, 210);
                border: 1px solid rgba(58, 77, 107, 130);
                border-radius: 18px;
                margin-top: 14px;
                padding-top: 12px;
            }
            QGroupBox[featuredSection="true"] {
                border: 1px solid rgba(92, 122, 180, 194);
            }
            QGroupBox[toolSectionGroup="true"]::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
                color: #eaf1ff;
                background: #0d1524;
                font-size: 10px;
                font-weight: 700;
            }
            QFrame[sectionHeader="true"] {
                background: rgba(17, 27, 42, 224);
                border: 1px solid rgba(60, 79, 108, 125);
                border-radius: 12px;
            }
            QFrame[sectionHeader="true"]:hover {
                background: rgba(27, 42, 64, 245);
                border: 1px solid rgba(103, 133, 188, 194);
            }
            QLabel[categoryArrow="true"] {
                color: #73a4ff;
                font-size: 10px;
                font-weight: 700;
            }
            QLabel[categoryTitle="true"] {
                color: #d8e4fb;
                font-size: 10px;
                font-weight: 600;
            }
            QLabel[categoryCount="true"] {
                color: #7e96bb;
                font-size: 9px;
            }
            QPushButton[toolItem="true"] {
                background: rgba(13, 20, 31, 240);
                color: #dce8ff;
                border: 1px solid rgba(48, 67, 95, 145);
                border-left: 3px solid #4f84ff;
                border-radius: 11px;
                padding: 7px 10px;
                font-size: 10px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton[toolItem="true"]:hover {
                background: rgba(24, 37, 57, 252);
                border: 1px solid rgba(101, 132, 186, 224);
                color: #ffffff;
            }
            QLabel#EmptyStateLabel {
                color: #8094b5;
                font-style: italic;
                padding: 10px 6px;
            }
            QScrollBar:vertical {
                background: rgba(10, 16, 26, 230);
                width: 9px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(58, 83, 120, 240);
                border-radius: 4px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(86, 121, 176, 255);
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }
            """
        )

    def _apply_shadow(self, widget, blur_radius, y_offset, alpha):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur_radius)
        shadow.setOffset(0, y_offset)
        shadow.setColor(QColor(0, 0, 0, alpha))
        widget.setGraphicsEffect(shadow)

    def _create_rail_button(self, label, tooltip, handler, primary=False):
        button = QToolButton()
        button.setText(label)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("railButton", True)
        button.setObjectName("RailPrimaryButton" if primary else "RailButton")
        button.clicked.connect(handler)
        return button

    def preferred_size(self, viewport_size):
        viewport_width = max(0, int(viewport_size.width()))
        viewport_height = max(0, int(viewport_size.height()))
        if self.drawer_open:
            max_total_width = min(self.RAIL_WIDTH + self.DRAWER_WIDTH + 12, max(260, viewport_width - 48))
            panel_height = min(self.EXPANDED_MAX_HEIGHT, max(self.EXPANDED_MIN_HEIGHT, viewport_height - 44))
            return QSize(max_total_width, panel_height)
        collapsed_height = min(self.COLLAPSED_HEIGHT, max(190, viewport_height - 32))
        return QSize(self.COLLAPSED_WIDTH, collapsed_height)

    def sync_overlay_size(self, viewport_size):
        size = self.preferred_size(viewport_size)
        self.setFixedSize(size)
        if self.drawer_open:
            drawer_width = max(212, size.width() - self.RAIL_WIDTH - 12)
            self.drawer_frame.setFixedWidth(drawer_width)
            self.drawer_frame.setFixedHeight(size.height())
        else:
            self.drawer_frame.setFixedWidth(self.DRAWER_WIDTH)

        rail_height = min(size.height(), self.RAIL_HEIGHT)
        self.rail_frame.setFixedHeight(rail_height)

    def toggle_drawer(self):
        self.drawer_open = not self.drawer_open
        self._apply_drawer_state()

    def close_drawer(self):
        self.drawer_open = False
        self._apply_drawer_state()

    def open_drawer(self):
        if not self.drawer_open:
            self.drawer_open = True
            self._apply_drawer_state()

    def open_drawer_and_focus_search(self):
        self.open_drawer()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def open_drawer_and_toggle_sections(self):
        self.open_drawer()
        self.toggle_all_sections()

    def _apply_drawer_state(self):
        self.drawer_frame.setVisible(self.drawer_open)
        self.toggle_btn.setText("−" if self.drawer_open else "+")
        self.toggle_btn.setToolTip("Collapse quick node menu" if self.drawer_open else "Open quick node menu")
        parent = self.parentWidget()
        if parent is not None:
            self.sync_overlay_size(parent.size())
        else:
            self.adjustSize()
        self.raise_()

    def refresh_header(self):
        pass

    def create_empty_label(self, text):
        label = QLabel(text)
        label.setObjectName("EmptyStateLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def create_sections(self):
        self.expandable_sections = []

        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.current_category:
            category_display_name = self.format_category_name(self.current_category)
            category_group = QGroupBox(f"{category_display_name} Nodes")
            category_group.setProperty("toolSectionGroup", True)
            category_group.setProperty("featuredSection", True)
            category_layout = QVBoxLayout(category_group)
            category_layout.setContentsMargins(10, 12, 10, 10)
            category_layout.setSpacing(6)

            category_nodes = NodeFactory.get_available_node_types(self.current_category)
            if category_nodes:
                for node_type in sorted(category_nodes):
                    node_name = NodeFactory.get_node_name(node_type, self.current_category)
                    category_layout.addWidget(self.create_node_button(node_name, node_type))
            else:
                category_layout.addWidget(self.create_empty_label("No category-specific nodes available"))

            self.scroll_layout.addWidget(category_group)

        standard_categories = {}
        user_categories = {}
        for node_type, category in NodeFactory.get_node_type_categories().items():
            normalized_category = NodeFactory.normalize_category(category)
            if normalized_category == self.current_category:
                continue

            is_custom_node = NodeFactory.is_custom_node_type(node_type)
            is_user_category = is_custom_node and (
                normalized_category == NodeFactory.CUSTOM_CATEGORY
                or normalized_category not in NodeFactory.CATEGORY_CATALOG
            )

            target = user_categories if is_user_category else standard_categories
            target.setdefault(normalized_category, []).append(node_type)

        if user_categories:
            user_group = QGroupBox("User Categories")
            user_group.setProperty("toolSectionGroup", True)
            user_layout = QVBoxLayout(user_group)
            user_layout.setContentsMargins(10, 12, 10, 10)
            user_layout.setSpacing(8)

            for category_name in sorted(user_categories.keys(), key=lambda item: self.format_category_name(item).lower()):
                node_types = sorted(
                    user_categories[category_name],
                    key=lambda node_type: NodeFactory.get_node_name(node_type).lower(),
                )
                user_layout.addWidget(self.create_expandable_category_section(category_name, node_types))

            self.scroll_layout.addWidget(user_group)

        library_group = QGroupBox("Node Library")
        library_group.setProperty("toolSectionGroup", True)
        library_layout = QVBoxLayout(library_group)
        library_layout.setContentsMargins(10, 12, 10, 10)
        library_layout.setSpacing(8)

        categories_with_nodes = {cat: nodes for cat, nodes in standard_categories.items() if nodes}
        if categories_with_nodes:
            for category_name in sorted(categories_with_nodes.keys(), key=lambda item: self.format_category_name(item).lower()):
                node_types = sorted(
                    categories_with_nodes[category_name],
                    key=lambda node_type: NodeFactory.get_node_name(node_type).lower(),
                )
                library_layout.addWidget(self.create_expandable_category_section(category_name, node_types))
        else:
            library_layout.addWidget(self.create_empty_label("No nodes available"))

        self.scroll_layout.addWidget(library_group)
        self.scroll_layout.addStretch()
        self.update_expand_all_label()

    def create_expandable_category_section(self, category_name, node_types):
        section_frame = QFrame()
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(6)

        header_frame = QFrame()
        header_frame.setProperty("sectionHeader", True)
        header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        arrow_label = QLabel("▶")
        arrow_label.setProperty("categoryArrow", True)
        arrow_label.setFixedWidth(12)

        category_label = QLabel(self.format_category_name(category_name))
        category_label.setProperty("categoryTitle", True)

        count_label = QLabel(str(len(node_types)))
        count_label.setProperty("categoryCount", True)

        header_layout.addWidget(arrow_label)
        header_layout.addWidget(category_label)
        header_layout.addStretch()
        header_layout.addWidget(count_label)

        nodes_container = QFrame()
        nodes_layout = QVBoxLayout(nodes_container)
        nodes_layout.setContentsMargins(8, 0, 0, 0)
        nodes_layout.setSpacing(4)

        for node_type in node_types:
            node_name = NodeFactory.get_node_name(node_type, category_name)
            nodes_layout.addWidget(self.create_node_button(node_name, node_type))

        section_frame.arrow_label = arrow_label
        section_frame.nodes_container = nodes_container
        section_frame.is_expanded = self.expanded_categories.get(category_name, False)
        section_frame.category_name = category_name

        nodes_container.setVisible(section_frame.is_expanded)
        arrow_label.setText("▼" if section_frame.is_expanded else "▶")
        header_frame.mousePressEvent = lambda _event, sf=section_frame: self.toggle_category_expansion(sf)

        section_layout.addWidget(header_frame)
        section_layout.addWidget(nodes_container)
        self.expandable_sections.append(section_frame)
        return section_frame

    def toggle_category_expansion(self, section_frame, expanded=None):
        target_state = (not section_frame.is_expanded) if expanded is None else bool(expanded)
        section_frame.is_expanded = target_state
        self.expanded_categories[section_frame.category_name] = target_state
        search_active = bool(self.search_input.text().strip())
        section_frame.nodes_container.setVisible(target_state or search_active)
        section_frame.arrow_label.setText("▼" if section_frame.nodes_container.isVisible() else "▶")
        self.update_expand_all_label()

    def toggle_all_sections(self):
        visible_sections = [section for section in self.expandable_sections if section.isVisible()]
        if not visible_sections:
            return

        should_expand = any(not section.is_expanded for section in visible_sections)
        for section in visible_sections:
            self.toggle_category_expansion(section, expanded=should_expand)

    def update_expand_all_label(self):
        visible_sections = [section for section in self.expandable_sections if section.isVisible()]
        should_expand = any(not section.is_expanded for section in visible_sections)
        self.expand_all_btn.setText("Expand" if should_expand else "Collapse")

    def create_node_button(self, node_name, node_type):
        btn = QPushButton(f"{self.get_node_prefix(node_type)} {node_name}")
        btn.setProperty("nodeType", node_type)
        btn.setProperty("toolItem", True)
        btn.setMinimumHeight(32)
        btn.setToolTip(f"Add {node_name} node")
        btn.clicked.connect(self.on_node_button_click)

        color_hex = NodeFactory.get_node_color(node_type, self.current_category)
        btn.setStyleSheet(
            f"""
            QPushButton[toolItem="true"] {{
                border-left: 3px solid {color_hex};
            }}
            """
        )
        return btn

    def format_category_name(self, category_name):
        return NodeFactory.get_category_display_name(category_name)

    def reset_filters(self):
        self.search_input.clear()
        self.filter_combo.setCurrentIndex(0)
        self.filter_nodes()

    def create_custom_node_template(self):
        self.open_drawer()
        dialog = CustomNodeDialog(self, default_category=self.current_category)
        if not dialog.exec():
            return

        payload = dialog.get_template_payload()
        if not payload:
            return

        try:
            node_type = NodeFactory.register_custom_node_template(
                name=payload["name"],
                node_type=payload["node_type"],
                color=payload["color"],
                symbol=payload["symbol"],
                category=payload["category"],
                category_label=payload["category_label"],
                default_data=payload["default_data"],
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Custom Node", str(exc))
            return

        self.create_sections()
        self.filter_nodes()
        self.refresh_filter_categories()
        self.custom_template_created.emit(node_type)
        self.node_created.emit(node_type)

    def configure_node_settings(self):
        dialog = NodeSettingsDialog(self)
        accepted = bool(dialog.exec())
        if not accepted and not dialog.did_apply_changes():
            return

        self.create_sections()
        self.filter_nodes()
        self.refresh_filter_categories()
        self.node_settings_changed.emit()

    def refresh_filter_categories(self):
        current_text = self.filter_combo.currentText() if hasattr(self, "filter_combo") else "All Nodes"
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem("All Nodes", [])

        categories = {}
        for node_type, category in NodeFactory.get_node_type_categories().items():
            categories.setdefault(category, []).append(node_type)

        for category in sorted(categories.keys()):
            self.filter_combo.addItem(self.format_category_name(category), categories[category])

        selected_index = self.filter_combo.findText(current_text)
        self.filter_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.filter_combo.blockSignals(False)

    def get_node_prefix(self, node_type):
        symbols = {
            "attack": ">",
            "command": ">",
            "credential": ">",
            "domain": ">",
            "host": ">",
            "ip": ">",
            "note": ">",
            "screenshot": ">",
            "script": ">",
            "user": ">",
            "vulnerability": ">",
        }
        return symbols.get(node_type, ">")

    def filter_nodes(self):
        search_text = self.search_input.text().strip().lower()
        filter_data = self.filter_combo.currentData()

        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), QGroupBox):
                self.filter_group_box(item.widget(), search_text, filter_data)

        self.update_node_count()
        self.update_expand_all_label()

    def filter_group_box(self, group_box, search_text, filter_data):
        layout = group_box.layout()
        if not layout:
            return

        visible_items = 0
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item or not item.widget():
                continue

            widget = item.widget()
            if hasattr(widget, "nodes_container"):
                category_visible = False
                nodes_layout = widget.nodes_container.layout()
                if nodes_layout:
                    for j in range(nodes_layout.count()):
                        node_item = nodes_layout.itemAt(j)
                        if not node_item or not node_item.widget():
                            continue

                        node_widget = node_item.widget()
                        node_type = node_widget.property("nodeType")
                        if not node_type:
                            continue

                        node_name = NodeFactory.get_node_name(node_type)
                        matches_search = not search_text or search_text in node_name.lower()
                        matches_filter = not filter_data or node_type in filter_data
                        is_visible = matches_search and matches_filter
                        node_widget.setVisible(is_visible)

                        if is_visible:
                            visible_items += 1
                            category_visible = True

                widget.setVisible(category_visible)
                widget.nodes_container.setVisible(category_visible and (widget.is_expanded or bool(search_text)))
                widget.arrow_label.setText("▼" if widget.nodes_container.isVisible() else "▶")
                continue

            if isinstance(widget, QPushButton) and widget.property("nodeType"):
                node_type = widget.property("nodeType")
                node_name = NodeFactory.get_node_name(node_type)
                matches_search = not search_text or search_text in node_name.lower()
                matches_filter = not filter_data or node_type in filter_data
                is_visible = matches_search and matches_filter
                widget.setVisible(is_visible)
                if is_visible:
                    visible_items += 1

        group_box.setVisible(visible_items > 0)

    def update_node_count(self):
        total_count = len(NodeFactory.get_all_node_types())
        visible_count = 0
        search_text = self.search_input.text().strip().lower()
        filter_data = self.filter_combo.currentData()

        for node_type in NodeFactory.get_all_node_types():
            node_name = NodeFactory.get_node_name(node_type).lower()
            matches_search = not search_text or search_text in node_name
            matches_filter = not filter_data or node_type in filter_data
            if matches_search and matches_filter:
                visible_count += 1

        self.node_count_label.setText(f"{visible_count} / {total_count}")

    def on_node_button_click(self):
        sender = self.sender()
        node_type = sender.property("nodeType")
        self.node_created.emit(node_type)

    def update_category(self, new_category):
        if new_category == "sandbox_mode":
            return

        self.current_category = NodeFactory.normalize_category(new_category)
        self.refresh_header()
        self.refresh_filter_categories()
        self.create_sections()
        self.filter_nodes()
