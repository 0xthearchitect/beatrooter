from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QComboBox, QGroupBox, QScrollArea, QFrame, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont
from core.node_factory import NodeFactory
from ui.custom_node_dialog import CustomNodeDialog
from ui.node_settings_dialog import NodeSettingsDialog

class ToolboxWidget(QWidget):
    node_created = pyqtSignal(str)
    custom_template_created = pyqtSignal(str)
    node_settings_changed = pyqtSignal()
    tools_requested = pyqtSignal()
    
    def __init__(self, graph_manager, current_category=None):
        super().__init__()
        self.graph_manager = graph_manager
        self.current_category = NodeFactory.normalize_category(current_category)
        self.expanded_categories = {}
        self.setup_ui()
    
    def setup_ui(self):
        self.setObjectName("ToolboxWidget")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Search and Filter section
        search_group = QGroupBox("Search / Filter")
        search_group.setObjectName("SearchGroup")
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(8, 12, 8, 10)
        search_layout.setSpacing(6)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search nodes...")
        self.search_input.setMinimumHeight(28)
        self.search_input.textChanged.connect(self.filter_nodes)
        search_layout.addWidget(self.search_input)
        
        # Filter by type
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.refresh_filter_categories()
        
        self.filter_combo.currentIndexChanged.connect(self.filter_nodes)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        search_layout.addLayout(filter_layout)
        
        layout.addWidget(search_group)
        
        # Node counter
        self.node_count_label = QLabel("0 of 0 nodes")
        self.node_count_label.setObjectName("NodeCountLabel")
        self.node_count_label.setStyleSheet("color: #7f8ea5; font-size: 10px; padding: 2px 4px;")
        layout.addWidget(self.node_count_label)

        self.custom_node_btn = QPushButton("+ Custom Node")
        self.custom_node_btn.setObjectName("CustomNodeBtn")
        self.custom_node_btn.setMinimumHeight(26)
        self.custom_node_btn.clicked.connect(self.create_custom_node_template)
        layout.addWidget(self.custom_node_btn)

        self.node_settings_btn = QPushButton("Node Settings")
        self.node_settings_btn.setObjectName("NodeSettingsBtn")
        self.node_settings_btn.setMinimumHeight(26)
        self.node_settings_btn.clicked.connect(self.configure_node_settings)
        layout.addWidget(self.node_settings_btn)
        
        # Main container with scroll
        scroll_area = QScrollArea()
        scroll_area.setObjectName("ToolboxScroll")
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(6)

        self.create_sections()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        layout.addWidget(scroll_area)

        self.update_node_count()
    
    def create_sections(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.current_category:
            category_display_name = self.format_category_name(self.current_category)
            category_group = QGroupBox(f"{category_display_name} Nodes")
            category_layout = QVBoxLayout(category_group)
            category_layout.setContentsMargins(8, 12, 8, 8)
            category_layout.setSpacing(4)
            
            category_nodes = NodeFactory.get_available_node_types(self.current_category)
            
            if category_nodes:
                for node_type in sorted(category_nodes):
                    node_name = NodeFactory.get_node_name(node_type, self.current_category)
                    btn = self.create_node_button(node_name, node_type)
                    category_layout.addWidget(btn)
            else:
                no_nodes_label = QLabel("No category-specific nodes available")
                no_nodes_label.setStyleSheet("color: #6c7086; font-style: italic; padding: 8px;")
                no_nodes_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                category_layout.addWidget(no_nodes_label)
            
            self.scroll_layout.addWidget(category_group)

        all_group = QGroupBox("All Available Nodes")
        all_layout = QVBoxLayout(all_group)
        all_layout.setContentsMargins(8, 12, 8, 8)
        all_layout.setSpacing(8)
        
        all_categories = {}
        for node_type, category in NodeFactory.get_node_type_categories().items():
            if category == self.current_category:
                continue
            all_categories.setdefault(category, []).append(node_type)
        
        categories_with_nodes = {cat: nodes for cat, nodes in all_categories.items() if nodes}
        
        if categories_with_nodes:
            for category_name in sorted(categories_with_nodes.keys()):
                node_types = sorted(categories_with_nodes[category_name])

                category_section = self.create_expandable_category_section(category_name, node_types)
                all_layout.addWidget(category_section)
        else:
            no_nodes_label = QLabel("No nodes available")
            no_nodes_label.setStyleSheet("color: #6c7086; font-style: italic; padding: 12px;")
            no_nodes_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            all_layout.addWidget(no_nodes_label)
        
        self.scroll_layout.addWidget(all_group)
        self.scroll_layout.addStretch()
    
    def create_expandable_category_section(self, category_name, node_types):
        section_frame = QFrame()
        section_frame.setFrameStyle(QFrame.Shape.NoFrame)
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(0)
        
        header_frame = QFrame()
        header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 2px;
                padding: 1px;
            }
            QFrame:hover {
                background-color: #142033;
                border: 1px solid #223247;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(8)

        arrow_label = QLabel("▶")
        arrow_label.setFixedSize(12, 12)
        arrow_label.setStyleSheet("color: #6b84a6; font-size: 9px;")
        
        category_label = QLabel(self.format_category_name(category_name))
        category_label.setStyleSheet("""
            QLabel {
                color: #9bb0ca;
                font-weight: 500;
                font-size: 10px;
            }
        """)

        count_label = QLabel(f"({len(node_types)})")
        count_label.setStyleSheet("color: #5f738f; font-size: 9px;")
        
        header_layout.addWidget(arrow_label)
        header_layout.addWidget(category_label)
        header_layout.addStretch()
        header_layout.addWidget(count_label)

        nodes_container = QFrame()
        nodes_layout = QVBoxLayout(nodes_container)
        nodes_layout.setContentsMargins(12, 2, 6, 4)
        nodes_layout.setSpacing(2)
        
        for node_type in node_types:
            node_name = NodeFactory.get_node_name(node_type, category_name)
            btn = self.create_node_button(node_name, node_type)
            nodes_layout.addWidget(btn)
        
        section_layout.addWidget(header_frame)
        section_layout.addWidget(nodes_container)
        
        section_frame.arrow_label = arrow_label
        section_frame.nodes_container = nodes_container
        section_frame.is_expanded = False
        
        header_frame.mousePressEvent = lambda e, sf=section_frame: self.toggle_category_expansion(sf)

        nodes_container.setVisible(False)
        
        return section_frame
    
    def toggle_category_expansion(self, section_frame):
        if section_frame.is_expanded:
            section_frame.nodes_container.setVisible(False)
            section_frame.arrow_label.setText("▶")
            section_frame.is_expanded = False
        else:
            section_frame.nodes_container.setVisible(True)
            section_frame.arrow_label.setText("▼")
            section_frame.is_expanded = True
    
    def create_node_button(self, node_name, node_type):
        prefix = self.get_node_prefix(node_type)
        btn = QPushButton(f"{prefix} {node_name}")
        btn.setProperty('nodeType', node_type)
        btn.setProperty('toolItem', True)
        btn.clicked.connect(self.on_node_button_click)
        btn.setMinimumHeight(23)
        btn.setToolTip(f"Add {node_name} node")

        color_hex = NodeFactory.get_node_color(node_type, self.current_category)
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #a9b8cf;
                border: 1px solid transparent;
                border-radius: 2px;
                padding: 3px 8px;
                font-weight: 500;
                font-size: 9px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: #142034;
                border: 1px solid #24354a;
                color: #eef4ff;
            }}
            QPushButton:pressed {{
                background-color: #1a2a42;
                color: #eef4ff;
            }}
        """)
        
        return btn

    def format_category_name(self, category_name):
        return NodeFactory.get_category_display_name(category_name)

    def create_custom_node_template(self):
        dialog = CustomNodeDialog(self)
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
            'attack': '>',
            'command': '>',
            'credential': '-',
            'domain': '-',
            'host': '-',
            'ip': '-',
            'note': '-',
            'screenshot': '-',
            'script': '-',
            'user': '-',
            'vulnerability': '-',
        }
        return symbols.get(node_type, '>')
    
    def filter_nodes(self):
        search_text = self.search_input.text().lower()
        filter_data = self.filter_combo.currentData()

        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget():
                group_box = item.widget()
                if isinstance(group_box, QGroupBox):
                    self.filter_group_box(group_box, search_text, filter_data)
        
        self.update_node_count()
    
    def filter_group_box(self, group_box, search_text, filter_data):
        layout = group_box.layout()
        if not layout:
            return
            
        visible_items = 0
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                
                if hasattr(widget, 'nodes_container'):
                    category_visible = False

                    nodes_layout = widget.nodes_container.layout()
                    if nodes_layout:
                        for j in range(nodes_layout.count()):
                            node_item = nodes_layout.itemAt(j)
                            if node_item and node_item.widget():
                                node_widget = node_item.widget()
                                if hasattr(node_widget, 'property') and node_widget.property('nodeType'):
                                    node_type = node_widget.property('nodeType')
                                    node_name = NodeFactory.get_node_name(node_type)
                                    
                                    matches_search = not search_text or search_text in node_name.lower()
                                    matches_filter = not filter_data or node_type in filter_data
                                    
                                    is_visible = matches_search and matches_filter
                                    node_widget.setVisible(is_visible)
                                    
                                    if is_visible:
                                        category_visible = True
                                        visible_items += 1

                    widget.setVisible(category_visible)
                    continue
                
                elif isinstance(widget, QPushButton) and widget.property('nodeType'):
                    node_type = widget.property('nodeType')
                    node_name = NodeFactory.get_node_name(node_type)
                    
                    matches_search = not search_text or search_text in node_name.lower()
                    matches_filter = not filter_data or node_type in filter_data
                    
                    is_visible = matches_search and matches_filter
                    widget.setVisible(is_visible)
                    
                    if is_visible:
                        visible_items += 1

        group_box.setVisible(visible_items > 0)
    
    def update_node_count(self):
        """Atualiza o contador de nodes disponíveis"""
        total_count = len(NodeFactory.get_all_node_types())
        visible_count = 0
        
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget() and item.widget().isVisible():
                group_box = item.widget()
                if isinstance(group_box, QGroupBox):
                    layout = group_box.layout()
                    if layout:
                        for j in range(layout.count()):
                            child_item = layout.itemAt(j)
                            if child_item and child_item.widget():
                                widget = child_item.widget()
                                
                                if hasattr(widget, 'nodes_container'):
                                    nodes_layout = widget.nodes_container.layout()
                                    if nodes_layout:
                                        for k in range(nodes_layout.count()):
                                            node_item = nodes_layout.itemAt(k)
                                            if node_item and node_item.widget() and node_item.widget().isVisible():
                                                visible_count += 1
                                
                                elif (isinstance(widget, QPushButton) and widget.property('nodeType') and widget.isVisible()):
                                    visible_count += 1
        
        self.node_count_label.setText(f"{visible_count} of {total_count} nodes")
    
    def on_node_button_click(self):
        sender = self.sender()
        node_type = sender.property('nodeType')
        self.node_created.emit(node_type)
    
    # No método update_category, adicione uma verificação para sandbox:
    def update_category(self, new_category):
        """Atualiza a toolbox para uma nova categoria"""
        # Se for sandbox, não atualiza a categoria
        if new_category == 'sandbox_mode':
            return
            
        self.current_category = NodeFactory.normalize_category(new_category)
        self.refresh_filter_categories()
        self.create_sections()
        self.filter_nodes()
