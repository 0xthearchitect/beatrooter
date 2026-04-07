from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QLabel, QFrame, QScrollArea, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from models.object_model import ObjectCategory

class SandboxCategoryDialog(QDialog):
    category_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_category = None
        self.category_cards = []
        
        self.colors = {
            'dark_bg': '#0f0f23',
            'darker_bg': '#151622',
            'darkest_bg': '#0b1020',
            'card_bg': '#171726',
            'card_hover': '#23242f',
            'accent_blue': '#2563eb',
            'accent_purple': '#7c3aed',
            'accent_green': '#10b981',
            'accent_orange': '#f59e0b',
            'text_primary': '#e6eef8',
            'text_secondary': '#9aa8bf',
            'text_muted': '#6e7a8a',
            'border': '#2b3444'
        }
        
        self.setWindowTitle("New Sandbox - Select Category")
        self.setMinimumSize(900, 650)
        self.setMaximumSize(1200, 800)
        self.resize(950, 700)
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 30)
        self.layout.setSpacing(25)
        
        # Header
        self.header_label = QLabel("Create New Sandbox")
        self.header_label.setObjectName("main_header")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        
        self.subheader_label = QLabel("Choose the kind of sandbox lab you want to open")
        self.subheader_label.setObjectName("sub_header")
        self.subheader_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subheader_label.setFont(QFont("Arial", 12))
        
        self.layout.addWidget(self.header_label)
        self.layout.addWidget(self.subheader_label)
        self.layout.addSpacing(30)
        
        # Scroll area for categories to prevent overflow
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.categories_container = QWidget()
        categories_layout = QGridLayout(self.categories_container)
        categories_layout.setSpacing(25)
        categories_layout.setContentsMargins(20, 10, 20, 10)
        categories_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        categories = [
            {
                'id': 'operating_systems',
                'name': 'Operating Systems',
                'description': 'VM-style snapshots, services, users, artifacts and local attack surface',
                'color': self.colors['accent_blue'],
                'icon': 'OS',
                'object_count': 'VM Lab'
            },
            {
                'id': 'network_devices', 
                'name': 'Network Devices',
                'description': 'Cisco-style topology, VLANs, ACLs, interfaces and packet tracing',
                'color': self.colors['accent_green'],
                'icon': 'NET',
                'object_count': 'Network Lab'
            },
            {
                'id': 'web_technologies',
                'name': 'Web Technologies',
                'description': 'Explorer, editor, containers and attack simulation for local web projects',
                'color': self.colors['accent_purple'],
                'icon': 'WEB',
                'object_count': 'Workspace'
            }
        ]
        
        row, col = 0, 0
        max_cols = 2
        
        for category in categories:
            card = self.create_category_card(
                category['name'],
                category['description'],
                category['color'],
                category['icon'],
                category['object_count']
            )
            card.setProperty("category_id", category['id'])
            
            categories_layout.addWidget(card, row, col)
            self.category_cards.append(card)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        scroll.setWidget(self.categories_container)
        self.layout.addWidget(scroll, 1)
        self.layout.addSpacing(10)
        
        # Botões
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setFixedSize(120, 44)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.create_btn = QPushButton("Create Sandbox")
        self.create_btn.setObjectName("create_btn")
        self.create_btn.setFixedSize(180, 44)
        self.create_btn.clicked.connect(self.accept_selection)
        self.create_btn.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.create_btn)
        
        self.layout.addLayout(button_layout)
    
    def create_category_card(self, title, description, color, icon, object_count):
        card = QFrame()
        card.setMinimumSize(380, 220)
        card.setMaximumSize(450, 250)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("selected", "false")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Título com ícone
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(50, 50)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color}20;
                color: {color};
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                border: 1px solid {color}40;
            }}
        """)
        
        # Título e contagem de objetos
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        
        count_label = QLabel(object_count)
        count_label.setFont(QFont("Arial", 10))
        count_label.setStyleSheet(f"color: {self.colors['text_muted']};")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(count_label)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont("Arial", 11))
        desc_label.setStyleSheet(f"color: {self.colors['text_secondary']}; line-height: 1.5;")
        desc_label.setMinimumHeight(45)
        desc_label.setMaximumHeight(60)
        
        layout.addWidget(desc_label)
        layout.addStretch()
        
        objects_preview = self.get_objects_preview(title)
        if objects_preview:
            preview_label = QLabel(objects_preview)
            preview_label.setWordWrap(True)
            preview_label.setFont(QFont("Arial", 9))
            preview_label.setStyleSheet(f"color: {self.colors['text_muted']}; font-style: italic;")
            layout.addWidget(preview_label)
        
        card.mousePressEvent = lambda e, c=card: self.on_category_selected(c)
        
        return card
    
    def get_objects_preview(self, category_name):
        previews = {
            'Operating Systems': 'Includes: snapshots, honeypot services, filesystem artifacts, users and policy notes',
            'Network Devices': 'Includes: devices, VLANs, ACLs, interfaces, published services and packet tracing',
            'Web Technologies': 'Includes: explorer, code editor, container controls, preview and attack simulator',
            'All Categories': 'All available objects from every category'
        }
        return previews.get(category_name, '')
    
    def on_category_selected(self, card):
        for category_card in self.category_cards:
            category_card.setProperty("selected", "false")
            category_card.style().unpolish(category_card)
            category_card.style().polish(category_card)
            category_card.update()
        
        card.setProperty("selected", "true")
        card.style().unpolish(card)
        card.style().polish(card)
        card.update()
        
        self.selected_category = card.property("category_id")
        self.create_btn.setEnabled(True)
    
    def accept_selection(self):
        if self.selected_category:
            self.category_selected.emit(self.selected_category)
            self.accept()
    
    def apply_styles(self):
        self.setStyleSheet(f"""
            /* ========== GLOBAL ========== */
            QDialog {{
                background-color: {self.colors['dark_bg']};
                color: {self.colors['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            }}
            
            /* ========== HEADERS ========== */
            QLabel#main_header {{
                color: {self.colors['text_primary']};
                font-size: 26px;
                font-weight: 700;
            }}
            
            QLabel#sub_header {{
                color: {self.colors['text_secondary']};
                font-size: 14px;
            }}
            
            /* ========== CATEGORY CARDS ========== */
            QFrame {{
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 12px;
            }}
            
            QFrame:hover {{
                background-color: {self.colors['card_hover']};
                border: 1px solid {self.colors['text_muted']};
            }}
            
            QFrame[selected="true"] {{
                background-color: {self.colors['card_hover']};
                border: 2px solid {self.colors['accent_blue']};
            }}
            
            /* ========== BUTTONS ========== */
            QPushButton#create_btn {{
                background-color: {self.colors['accent_blue']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            
            QPushButton#create_btn:hover {{
                background-color: #3b82f6;
            }}
            
            QPushButton#create_btn:pressed {{
                background-color: #1e40af;
            }}
            
            QPushButton#create_btn:disabled {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['text_muted']};
                border: 1px solid {self.colors['border']};
            }}
            
            QPushButton#cancel_btn {{
                background-color: transparent;
                color: {self.colors['text_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            
            QPushButton#cancel_btn:hover {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['text_muted']};
            }}
        """)
