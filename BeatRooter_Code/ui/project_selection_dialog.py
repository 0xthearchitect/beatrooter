from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QLabel, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ProjectSelectionDialog(QDialog):
    project_selected = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_project = None
        self.selected_category = None
        self.project_cards = []
        self.category_cards = []
        
        self.colors = {
            'dark_bg': '#0f0f23',
            'darker_bg': '#151622',
            'darkest_bg': '#0b1020',
            'card_bg': '#171726',
            'card_hover': '#23242f',
            'accent_blue': '#2563eb',
            'accent_purple': '#7c3aed',
            'accent_red': '#dc2626',
            'text_primary': '#e6eef8',
            'text_secondary': '#9aa8bf',
            'text_muted': '#6e7a8a',
            'border': '#2b3444'
        }
        
        self.setWindowTitle("New Investigation - Select Project Type")
        self.setMinimumSize(900, 700)
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 30)
        self.layout.setSpacing(25)
        
        # Header
        self.header_label = QLabel("Start New Investigation")
        self.header_label.setObjectName("main_header")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        
        self.subheader_label = QLabel("Choose the type of investigation you want to create")
        self.subheader_label.setObjectName("sub_header")
        self.subheader_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subheader_label.setFont(QFont("Arial", 12))
        
        self.layout.addWidget(self.header_label)
        self.layout.addWidget(self.subheader_label)
        self.layout.addSpacing(30)
        
        # Project type selection container
        self.projects_container = QWidget()
        self.projects_layout = QHBoxLayout(self.projects_container)
        self.projects_layout.setSpacing(25)
        self.projects_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Blue Team Card
        blue_card = self.create_project_card(
            "Blue Team", 
            "Defensive security operations and incident response",
            self.colors['accent_blue'],
            "BT"
        )
        blue_card.setProperty("project_type", "blueteam")
        blue_card.setObjectName("blueteam_card")
        self.projects_layout.addWidget(blue_card)
        self.project_cards.append(blue_card)
        
        # SOC Team Card  
        soc_card = self.create_project_card(
            "SOC Operations",
            "Security Operations Center monitoring and analysis",
            self.colors['accent_purple'],
            "SOC"
        )
        soc_card.setProperty("project_type", "soc_team")
        soc_card.setObjectName("soc_team_card")
        self.projects_layout.addWidget(soc_card)
        self.project_cards.append(soc_card)
        
        # Red Team Card
        red_card = self.create_project_card(
            "Red Team",
            "Offensive security testing and penetration testing", 
            self.colors['accent_red'],
            "RT"
        )
        red_card.setProperty("project_type", "redteam")
        red_card.setObjectName("redteam_card")
        self.projects_layout.addWidget(red_card)
        self.project_cards.append(red_card)
        
        self.layout.addWidget(self.projects_container)
        self.layout.addStretch()
        
        # Categories area
        self.categories_container = QWidget()
        self.categories_container.setVisible(False)
        categories_layout = QVBoxLayout(self.categories_container)
        categories_layout.setContentsMargins(0, 0, 0, 0)
        categories_layout.setSpacing(20)
        
        categories_header_layout = QHBoxLayout()
        categories_header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # Back button
        self.back_btn = QPushButton("← Back to Project Types")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.show_projects)
        categories_header_layout.addWidget(self.back_btn)
        categories_header_layout.addStretch()
        
        categories_layout.addLayout(categories_header_layout)
        
        categories_title = QLabel("Select Specialization")
        categories_title.setObjectName("categories_header")
        categories_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        categories_title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        categories_layout.addWidget(categories_title)
        
        # Categories grid
        self.categories_grid = QGridLayout()
        self.categories_grid.setSpacing(15)
        self.categories_grid.setContentsMargins(0, 0, 0, 0)
        
        categories_layout.addLayout(self.categories_grid)
        categories_layout.addStretch()
        
        self.layout.addWidget(self.categories_container)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setFixedSize(120, 44)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.create_btn = QPushButton("Create Investigation")
        self.create_btn.setObjectName("create_btn")
        self.create_btn.setFixedSize(180, 44)
        self.create_btn.clicked.connect(self.accept_selection)
        self.create_btn.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.create_btn)
        
        self.layout.addLayout(button_layout)
    
    def create_project_card(self, title, description, color, icon):
        card = QFrame()
        card.setFixedSize(260, 320)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("selected", "false")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(80, 80)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {self.colors['text_primary']};
                font-size: 28px;
                font-weight: bold;
                border-radius: 12px;
                border: 1px solid {self.colors['border']};
            }}
        """)
        
        # Title
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        
        # Description
        desc_label = QLabel(description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont("Arial", 11))
        desc_label.setStyleSheet(f"color: {self.colors['text_secondary']}; line-height: 1.4;")
        
        layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        
        card.mousePressEvent = lambda e, c=card: self.on_project_selected(c)

        tools_info = QLabel("Includes: ExifTool, Nmap, Gobuster, Whois, etc.")
        tools_info.setStyleSheet(f"color: {self.colors['text_muted']}; font-size: 10px; margin-top: 5px;")
        layout.addWidget(tools_info)
        
        return card
    
    def create_category_card(self, title, description, color, icon):
        card = QFrame()
        card.setFixedSize(380, 120)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setProperty("selected", "false")
        card.setObjectName("category_card")
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(50, 50)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(37, 99, 235, 0.15);
                color: {self.colors['accent_blue']};
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                border: 1px solid {self.colors['accent_blue']};
            }}
        """)
        
        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {self.colors['text_primary']};")
        
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont("Arial", 11))
        desc_label.setStyleSheet(f"color: {self.colors['text_secondary']}; line-height: 1.3;")
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        text_layout.addStretch()
        
        layout.addWidget(icon_label)
        layout.addLayout(text_layout)
        layout.addStretch()
        
        return card
    
    def on_project_selected(self, card):
        self.selected_project = card.property("project_type")
        self.show_categories_for_project(self.selected_project)
    
    def show_categories_for_project(self, project_type):
        self.projects_container.setVisible(False)
        self.categories_container.setVisible(True)
        
        self.header_label.setText(f"Start New Investigation - {self.get_project_name(project_type)}")
        self.subheader_label.setText("Choose your specialization area")
        
        self.category_cards.clear()
        while self.categories_grid.count():
            child = self.categories_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        categories = self.get_categories_for_project(project_type)
        
        if not categories:
            return
        
        row, col = 0, 0
        max_cols = 2
        
        for cat_id, cat_config in categories.items():
            card = self.create_category_card(
                cat_config['name'],
                cat_config['description'],
                cat_config['color'],
                cat_config['icon']
            )
            card.setProperty("category_id", cat_id)
            card.mousePressEvent = lambda e, c=card: self.on_category_selected(c)
            
            self.categories_grid.addWidget(card, row, col)
            self.category_cards.append(card)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def show_projects(self):
        self.projects_container.setVisible(True)
        self.categories_container.setVisible(False)

        self.header_label.setText("Start New Investigation")
        self.subheader_label.setText("Choose the type of investigation you want to create")
        
        self.selected_project = None
        self.selected_category = None
        self.create_btn.setEnabled(False)
    
    def get_project_name(self, project_type):
        names = {
            "blueteam": "Blue Team",
            "soc_team": "SOC Operations", 
            "redteam": "Red Team"
        }
        return names.get(project_type, "Unknown")
    
    def get_categories_for_project(self, project_type):
        categories = {
            "blueteam": {
                "incident_response": {
                    "name": "Incident Response",
                    "description": "Investigate security incidents and breaches",
                    "color": "#2563eb",
                    "icon": "IR"
                },
                "threat_hunting": {
                    "name": "Threat Hunting", 
                    "description": "Proactive search for threats and IOCs",
                    "color": "#1d4ed8",
                    "icon": "TH"
                },
                "malware_analysis": {
                    "name": "Malware Analysis",
                    "description": "Analyze malicious software in isolated environments",
                    "color": "#4338ca", 
                    "icon": "MA"
                },
                "siem_investigation": {
                    "name": "SIEM Investigation",
                    "description": "Analyze security events and logs",
                    "color": "#3730a3",
                    "icon": "SI"
                }
            },
            "soc_team": {
                "alert_triage": {
                    "name": "Alert Triage",
                    "description": "Prioritize and investigate security alerts",
                    "color": "#7c3aed",
                    "icon": "AT"
                },
                "correlation_analysis": {
                    "name": "Correlation Analysis",
                    "description": "Connect related security events",
                    "color": "#6d28d9",
                    "icon": "CA"
                },
                "compliance_monitoring": {
                    "name": "Compliance Monitoring", 
                    "description": "Monitor regulatory compliance requirements",
                    "color": "#5b21b6",
                    "icon": "CM"
                }
            },
            "redteam": {
                "web_pentesting": {
                    "name": "Web Application Testing",
                    "description": "Web application security assessment",
                    "color": "#dc2626",
                    "icon": "WP"
                },
                "network_pentesting": {
                    "name": "Network Assessment",
                    "description": "Network infrastructure security evaluation", 
                    "color": "#b91c1c",
                    "icon": "NA"
                },
                "social_engineering": {
                    "name": "Social Engineering",
                    "description": "Human factor security controls assessment",
                    "color": "#991b1b",
                    "icon": "SE"
                }
            }
        }
        
        return categories.get(project_type, {})
    
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
        if self.selected_project and self.selected_category:
            self.project_selected.emit(self.selected_project, self.selected_category)
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
            
            QLabel#categories_header {{
                color: {self.colors['text_primary']};
                font-size: 18px;
                font-weight: 700;
                padding: 10px;
            }}
            
            /* ========== PROJECT CARDS ========== */
            QFrame#blueteam_card {{
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 16px;
            }}
            
            QFrame#blueteam_card:hover {{
                background-color: {self.colors['card_hover']};
                border: 1px solid {self.colors['accent_blue']};
            }}
            
            QFrame#soc_team_card {{
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 16px;
            }}
            
            QFrame#soc_team_card:hover {{
                background-color: {self.colors['card_hover']};
                border: 1px solid {self.colors['accent_purple']};
            }}
            
            QFrame#redteam_card {{
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 16px;
            }}
            
            QFrame#redteam_card:hover {{
                background-color: {self.colors['card_hover']};
                border: 1px solid {self.colors['accent_red']};
            }}
            
            /* ========== CATEGORY CARDS ========== */
            QFrame#category_card {{
                background-color: {self.colors['card_bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 12px;
            }}
            
            QFrame#category_card:hover {{
                background-color: {self.colors['card_hover']};
                border: 1px solid {self.colors['text_muted']};
            }}
            
            QFrame#category_card[selected="true"] {{
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
            
            QPushButton#back_btn {{
                background-color: transparent;
                color: {self.colors['accent_blue']};
                border: none;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 6px;
            }}
            
            QPushButton#back_btn:hover {{
                background-color: rgba(37, 99, 235, 0.1);
            }}
        """)