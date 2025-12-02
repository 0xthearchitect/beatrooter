from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QComboBox, QGroupBox, QScrollArea, QFrame)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont
from core.node_factory import NodeFactory

class ToolboxWidget(QWidget):
    node_created = pyqtSignal(str)
    tools_requested = pyqtSignal()
    
    def __init__(self, graph_manager, current_category=None):
        super().__init__()
        self.graph_manager = graph_manager
        self.current_category = current_category
        self.expanded_categories = {}
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Search and Filter section
        search_group = QGroupBox("Search & Filter")
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(8, 12, 8, 12)
        search_layout.setSpacing(6)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search nodes...")
        self.search_input.setMinimumHeight(30)
        self.search_input.textChanged.connect(self.filter_nodes)
        search_layout.addWidget(self.search_input)
        
        # Filter by type
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Nodes", [])
        
        # Group nodes by category for filtering
        categories = {}
        for node_type, config in NodeFactory.NODE_TYPES.items():
            category = config.get('category', 'General')
            if category not in categories:
                categories[category] = []
            categories[category].append(node_type)
        
        # Add category filters
        for category in sorted(categories.keys()):
            self.filter_combo.addItem(f"{category}", categories[category])
        
        self.filter_combo.currentIndexChanged.connect(self.filter_nodes)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        search_layout.addLayout(filter_layout)
        
        layout.addWidget(search_group)
        
        # Node counter
        self.node_count_label = QLabel("Nodes available: 0")
        self.node_count_label.setStyleSheet("color: #a6adc8; font-size: 11px; padding: 4px;")
        layout.addWidget(self.node_count_label)
        
        # Main container with scroll
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(12)

        self.create_sections()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        layout.addWidget(scroll_area)

        tools_btn = QPushButton("External Tools")
        tools_btn.setMinimumHeight(40)
        tools_btn.setToolTip("Open external tools panel")
        tools_btn.clicked.connect(self.tools_requested.emit)
        layout.addWidget(tools_btn)

        self.update_node_count()
    
    def create_sections(self):
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.current_category:
            category_display_name = self.current_category.replace('_', ' ').title()
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
        
        all_categories['General'] = []
        for node_type, config in NodeFactory.NODE_TYPES.items():
            if config.get('category', 'General') == 'General':
                all_categories['General'].append(node_type)
        
        for category in NodeFactory.CATEGORY_TEMPLATES:
            if category != self.current_category:
                if category not in all_categories:
                    all_categories[category] = []
                all_categories[category].extend(list(NodeFactory.CATEGORY_TEMPLATES[category].keys()))
        
        for node_type, config in NodeFactory.NODE_TYPES.items():
            category = config.get('category', 'General')
            if category != 'General' and category not in all_categories:
                all_categories[category] = []
            if category != 'General':
                all_categories[category].append(node_type)
        
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
                background-color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }
            QFrame:hover {
                background-color: #2a2a3a;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(8)

        arrow_label = QLabel("▶")
        arrow_label.setFixedSize(12, 12)
        arrow_label.setStyleSheet("color: #89b4fa; font-size: 10px;")
        
        category_label = QLabel(category_name.replace('_', ' ').title())
        category_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-weight: bold;
                font-size: 12px;
            }
        """)

        count_label = QLabel(f"({len(node_types)})")
        count_label.setStyleSheet("color: #6c7086; font-size: 10px;")
        
        header_layout.addWidget(arrow_label)
        header_layout.addWidget(category_label)
        header_layout.addStretch()
        header_layout.addWidget(count_label)

        nodes_container = QFrame()
        nodes_layout = QVBoxLayout(nodes_container)
        nodes_layout.setContentsMargins(8, 4, 8, 4)
        nodes_layout.setSpacing(4)
        
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
        btn = QPushButton(node_name)
        btn.setProperty('nodeType', node_type)
        btn.clicked.connect(self.on_node_button_click)
        btn.setMinimumHeight(32)
        btn.setToolTip(f"Add {node_name} node")

        color_hex = NodeFactory.get_node_color(node_type, self.current_category)
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #585b70;
                color: #cdd6f4;
                border: 1px solid #6c7086;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 11px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: #6c7086;
                border: 1px solid {color_hex};
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: {color_hex};
                color: #1e1e2e;
            }}
        """)
        
        return btn
    
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
        total_count = 0
        visible_count = 0
        
        for node_type in NodeFactory.NODE_TYPES:
            total_count += 1
        for category in NodeFactory.CATEGORY_TEMPLATES:
            total_count += len(NodeFactory.CATEGORY_TEMPLATES[category])
        
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
        
        self.node_count_label.setText(f"Showing: {visible_count} of {total_count} nodes")
    
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
            
        self.current_category = new_category
        self.create_sections()
        self.filter_nodes()