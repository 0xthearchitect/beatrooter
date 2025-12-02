from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QComboBox, QGroupBox, QScrollArea, QFrame, QInputDialog,
    QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QColor, QFont, QPixmap, QIcon, QPainter
from models.object_model import ObjectType, ObjectCategory
from core.sandbox.sandbox_object_factory import SandboxObjectFactory
import os
from utils.path_utils import get_resource_path

class ExpandableSection(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setup_ui(title)
        self.objects_list = []
        self.is_expanded = False
        
    def setup_ui(self, title):
        self.setFrameStyle(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header_frame = QFrame()
        self.header_frame.setObjectName("sectionHeader")
        self.header_frame.setMinimumHeight(35)
        self.header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        self.arrow_label = QLabel("▶")
        self.arrow_label.setFixedSize(12, 12)
        self.arrow_label.setObjectName("sectionArrow")
        
        # Título
        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        self.title_label.setFont(font)
        
        # Contador
        self.count_label = QLabel("0")
        self.count_label.setObjectName("sectionCount")
        
        header_layout.addWidget(self.arrow_label)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        
        # Área de conteúdo
        self.content_frame = QFrame()
        self.content_frame.setObjectName("sectionContent")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(12, 8, 12, 8)
        self.content_layout.setSpacing(4)
        
        self.content_frame.setVisible(False)
        
        layout.addWidget(self.header_frame)
        layout.addWidget(self.content_frame)
        
        self.header_frame.mousePressEvent = lambda e: self.toggle_section()
        
        self.apply_section_styles()
    
    def apply_section_styles(self):
        self.setStyleSheet("""
            ExpandableSection {
                background-color: transparent;
            }
            ExpandableSection QFrame#sectionHeader {
                background-color: #1e1e2e;
                border: none;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            ExpandableSection QFrame#sectionHeader:hover {
                background-color: #2a2a3a;
            }
            ExpandableSection QLabel#sectionArrow {
                color: #89b4fa;
                font-size: 10px;
                background-color: transparent;
            }
            ExpandableSection QLabel#sectionTitle {
                color: #89b4fa;
                background-color: transparent;
                font-weight: bold;
            }
            ExpandableSection QLabel#sectionCount {
                color: #6c7086;
                background-color: transparent;
                font-size: 10px;
                font-weight: bold;
            }
            ExpandableSection QFrame#sectionContent {
                background-color: transparent;
                border: none;
            }
        """)
    
    def toggle_section(self):
        self.is_expanded = not self.is_expanded
        self.content_frame.setVisible(self.is_expanded)
        self.arrow_label.setText("▼" if self.is_expanded else "▶")
    
    def add_object_item(self, obj_type, obj_name):
        item_btn = QPushButton(obj_name)
        item_btn.setObjectName("objectItem")
        item_btn.setProperty("objectType", obj_type.value)
        item_btn.setMinimumHeight(32)
        item_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        icon = self.get_icon_for_object(obj_type)
        if not icon.isNull():
            item_btn.setIcon(icon)
            item_btn.setIconSize(QSize(16, 16))
        
        item_btn.setToolTip(f"Create {obj_name} object")
        
        self.content_layout.addWidget(item_btn)
        self.objects_list.append(item_btn)
        
        self.count_label.setText(str(len(self.objects_list)))
        
        return item_btn
    
    def get_icon_for_object(self, obj_type):
        base_path = "assets/icons"
        
        icon_mapping = {
            # Operating Systems
            'windows_10': 'operating_systems/windows_10.png',
            'windows_11': 'operating_systems/windows_11.png',
            'ubuntu': 'operating_systems/ubuntu.png',
            'arch': 'operating_systems/arch.png',
            'folder': 'operating_systems/folder.png',
            'file': 'operating_systems/file.png',
            
            # Network Devices
            'computer': 'network/computer.png',
            'server': 'network/server.png',
            'router': 'network/router.png',
            'switch': 'network/switch.png',

            'apache': 'web/apache.png',
            'nginx': 'web/nginx.png',
            'iis': 'web/iis.png',
            'tomcat': 'web/tomcat.png',
            
            'mysql': 'web/mysql.png',
            'postgresql': 'web/postgresql.png',
            'mongodb': 'web/mongodb.png',
            'redis': 'web/redis.png',

            'django': 'web/django.png',
            'flask': 'web/flask.png',
            'nodejs': 'web/nodejs.png',
            'spring': 'web/spring.png',
            'express': 'web/express.png',
            'nestjs': 'web/nestjs.png',
            'rails': 'web/rails.png',
            
            'react': 'web/react.png',
            'angular': 'web/angular.png',
            'vue': 'web/vue.png',
            
            'web_folder': 'web/folder.png',
            'web_app': 'web/web_app.png',
            'code_file': 'web/code_file.png',
            'config_file': 'web/config_file.png',
            'api_endpoint': 'web/api_endpoint.png',

            'oauth': 'web/oauth.png',
            'jwt': 'web/jwt.png',
            'saml': 'web/saml.png',
            
            # Organization
            'project': 'organization/project.png',
            'team': 'organization/team.png',
            'user': 'organization/user.png',
            'group': 'organization/group.png',
        }
        
        icon_file = icon_mapping.get(obj_type.value, 'default.png')
    
        icon_path = get_resource_path(f"icons/{icon_file}")
        
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            pixmap = pixmap.scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            return QIcon(pixmap)
        else:
            print(f"[WARNING] Icon not found: {icon_path}")
            return QIcon()
    
    def clear_section(self):
        for item in self.objects_list:
            item.deleteLater()
        self.objects_list.clear()
        self.count_label.setText("0")

class SandboxToolbox(QWidget):
    object_created = pyqtSignal(object, str)
    
    def __init__(self, sandbox_manager, current_category=None):
        super().__init__()
        self.sandbox_manager = sandbox_manager
        self.current_category = current_category
        self.sections = {}
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        search_group = QGroupBox("Search Objects")
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(8, 12, 8, 12)
        search_layout.setSpacing(6)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search objects...")
        self.search_input.setMinimumHeight(30)
        self.search_input.textChanged.connect(self.filter_objects)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_group)
        
        self.object_count_label = QLabel("Total objects: 0")
        self.object_count_label.setStyleSheet("""
            QLabel {
                color: #a6adc8; 
                font-size: 11px; 
                padding: 4px;
                background-color: #1e1e2e;
                border-radius: 4px;
            }
        """)
        self.object_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.object_count_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.sections_container = QWidget()
        self.sections_layout = QVBoxLayout(self.sections_container)
        self.sections_layout.setContentsMargins(2, 2, 2, 2)
        self.sections_layout.setSpacing(8)
        
        scroll_area.setWidget(self.sections_container)
        layout.addWidget(scroll_area)

        quick_create_btn = QPushButton("Quick Create Object")
        quick_create_btn.setMinimumHeight(40)
        quick_create_btn.clicked.connect(self.quick_create_object)
        quick_create_btn.setStyleSheet("""
            QPushButton {
                background-color: #585b70;
                color: #cdd6f4;
                border: 1px solid #6c7086;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #6c7086;
                border: 1px solid #89b4fa;
            }
            QPushButton:pressed {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)
        layout.addWidget(quick_create_btn)

        self.update_sections()
        
        self.apply_toolbox_styles()
    
    def apply_toolbox_styles(self):
        self.setStyleSheet("""
            SandboxToolbox {
                background-color: #1e1e2e;
            }
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #313244;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit {
                background-color: #2d2d3a;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:hover {
                border: 1px solid #585b70;
            }
            QLineEdit:focus {
                border: 1px solid #89b4fa;
            }
            QPushButton#objectItem {
                background-color: #585b70;
                color: #cdd6f4;
                border: 1px solid #6c7086;
                border-radius: 6px;
                text-align: left;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton#objectItem:hover {
                background-color: #6c7086;
                border: 1px solid #89b4fa;
                color: #ffffff;
            }
            QPushButton#objectItem:pressed {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)
    
    def create_sections_structure(self, category):
        sections_structure = {
            ObjectCategory.OPERATING_SYSTEM: {
                "Main Systems": [ObjectType.WINDOWS, ObjectType.LINUX, ObjectType.MACOS],
                "Windows Distributions": [ObjectType.WINDOWS_10, ObjectType.WINDOWS_11],
                "Linux Distributions": [ObjectType.UBUNTU, ObjectType.DEBIAN, ObjectType.ARCH, ObjectType.CENTOS, ObjectType.KALI],
                "Services & Processes": [ObjectType.SERVICE, ObjectType.PROCESS, ObjectType.SCHEDULED_TASK],
                "Paths & Files": [ObjectType.FOLDER, ObjectType.FILE, ObjectType.REGISTRY_KEY, ObjectType.CONFIG_FILE]
            },
            ObjectCategory.NETWORK: {
                "Devices": [ObjectType.COMPUTER, ObjectType.SERVER, ObjectType.ROUTER, ObjectType.SWITCH, 
                           ObjectType.FIREWALL, ObjectType.ACCESS_POINT, ObjectType.MODEM, ObjectType.CONTAINER]
            },
            ObjectCategory.WEB: {
            "Web Servers": [ObjectType.APACHE, ObjectType.NGINX, ObjectType.IIS, ObjectType.TOMCAT],
            "Databases": [ObjectType.MYSQL, ObjectType.POSTGRESQL, ObjectType.MONGODB, ObjectType.REDIS],
            "Backend Frameworks": [ObjectType.DJANGO, ObjectType.FLASK, ObjectType.NODEJS, ObjectType.SPRING, 
                                  ObjectType.EXPRESS, ObjectType.NESTJS, ObjectType.RAILS],
            "Frontend Frameworks": [ObjectType.REACT, ObjectType.ANGULAR, ObjectType.VUE],
            "Application Components": [
                ObjectType.WEB_APP, ObjectType.WEB_FOLDER,
                ObjectType.API_ENDPOINT, ObjectType.CODE_FILE, ObjectType.CONFIG_FILE
            ],
            "Authentication": [ObjectType.OAUTH, ObjectType.JWT, ObjectType.SAML]
            },
            ObjectCategory.ORGANIZATION: {
                "Structure": [ObjectType.PROJECT, ObjectType.TEAM, ObjectType.USER, ObjectType.GROUP]
            }
        }
        
        if category is None:
            return {
                "Operating Systems": [obj for section in sections_structure[ObjectCategory.OPERATING_SYSTEM].values() for obj in section],
                "Network Devices": sections_structure[ObjectCategory.NETWORK]["Devices"],
                "Web Technologies": [obj for section in sections_structure[ObjectCategory.WEB].values() for obj in section],
                "Organization": sections_structure[ObjectCategory.ORGANIZATION]["Structure"]
            }
        
        return sections_structure.get(category, {})
    
    def update_sections(self):
        for section in self.sections.values():
            section.deleteLater()
        self.sections.clear()

        sections_structure = self.create_sections_structure(self.current_category)
        
        total_objects = 0

        for section_name, object_types in sections_structure.items():
            section = ExpandableSection(section_name)
            
            for obj_type in object_types:
                obj_name = SandboxObjectFactory.get_object_name(obj_type)
                item_btn = section.add_object_item(obj_type, obj_name)
                item_btn.clicked.connect(lambda checked=False, ot=obj_type: self.on_object_clicked(ot))
                total_objects += 1
            
            self.sections[section_name] = section
            self.sections_layout.addWidget(section)
        
        self.sections_layout.addStretch()
        
        self.object_count_label.setText(f"Total objects: {total_objects}")
    
    def on_object_clicked(self, obj_type):
        self.object_created.emit(obj_type, None)
    
    def filter_objects(self):
        search_text = self.search_input.text().lower().strip()
        
        if not search_text:
            total_visible = 0
            for section_name, section in self.sections.items():
                section_visible = False
                for item in section.objects_list:
                    item.setVisible(True)
                    section_visible = True
                    total_visible += 1
                section.setVisible(section_visible)
            
            self.object_count_label.setText(f"Total objects: {total_visible}")
        else:
            visible_count = 0
            for section_name, section in self.sections.items():
                section_has_visible = False
                for item in section.objects_list:
                    obj_name = item.text().lower()
                    if search_text in obj_name:
                        item.setVisible(True)
                        section_has_visible = True
                        visible_count += 1
                    else:
                        item.setVisible(False)
                
                section.setVisible(section_has_visible)
                if section_has_visible and not section.is_expanded:
                    section.toggle_section()
            
            self.object_count_label.setText(f"Filtered: {visible_count} objects")
    
    def update_category(self, new_category):
        self.current_category = new_category
        self.update_sections()
    
    def quick_create_object(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Quick Create Object")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Object Type:"))
        
        type_combo = QComboBox()
        if self.current_category:
            available_types = []
            sections_structure = self.create_sections_structure(self.current_category)
            for section_objects in sections_structure.values():
                available_types.extend(section_objects)
        else:
            available_types = SandboxObjectFactory.get_available_object_types()
            
        for obj_type in available_types:
            type_combo.addItem(SandboxObjectFactory.get_object_name(obj_type), obj_type.value)
        type_layout.addWidget(type_combo)
        
        layout.addLayout(type_layout)
        
        # Object name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Object Name:"))
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter object name...")
        name_layout.addWidget(name_input)
        
        layout.addLayout(name_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        create_btn = QPushButton("Create")
        cancel_btn = QPushButton("Cancel")
        
        create_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(create_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            obj_type = ObjectType(type_combo.currentData())
            obj_name = name_input.text().strip()
            
            if not obj_name:
                obj_name = SandboxObjectFactory.get_object_name(obj_type)
            
            self.object_created.emit(obj_type, obj_name)