from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QComboBox, QPushButton,
    QGroupBox, QFormLayout, QScrollArea, QFileDialog, QMessageBox,
    QDialog, QTreeWidget, QTreeWidgetItem, QTabWidget, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from models.object_model import SandboxObject, ObjectType, CodeContent, LoginCredentials
from features.sandbox.core.sandbox_object_factory import SandboxObjectFactory

class CodeEditorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Language selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Python", "JavaScript", "Java", "Ruby", "PHP", "HTML", "CSS", "SQL", "YAML", "JSON"])
        lang_layout.addWidget(self.language_combo)
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Code editor
        self.code_editor = QTextEdit()
        self.code_editor.setPlaceholderText("Enter your source code here...")
        self.code_editor.setFontFamily("Courier New")
        self.code_editor.setFontPointSize(10)
        layout.addWidget(self.code_editor)
        
        # Dependencies
        deps_group = QGroupBox("Dependencies")
        deps_layout = QVBoxLayout(deps_group)
        self.dependencies_edit = QTextEdit()
        self.dependencies_edit.setPlaceholderText("Enter dependencies (one per line)...")
        self.dependencies_edit.setMaximumHeight(80)
        deps_layout.addWidget(self.dependencies_edit)
        layout.addWidget(deps_group)
        
        # Environment variables
        env_group = QGroupBox("Environment Variables")
        env_layout = QVBoxLayout(env_group)
        self.env_vars_edit = QTextEdit()
        self.env_vars_edit.setPlaceholderText("KEY=VALUE (one per line)...")
        self.env_vars_edit.setMaximumHeight(80)
        env_layout.addWidget(self.env_vars_edit)
        layout.addWidget(env_group)

class LoginCredentialsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.url_edit = QLineEdit()
        self.port_edit = QLineEdit()
        self.database_edit = QLineEdit()
        
        layout.addRow("Username:", self.username_edit)
        layout.addRow("Password:", self.password_edit)
        layout.addRow("URL:", self.url_edit)
        layout.addRow("Port:", self.port_edit)
        layout.addRow("Database:", self.database_edit)
  
        self.additional_fields_edit = QTextEdit()
        self.additional_fields_edit.setPlaceholderText("Additional fields as KEY=VALUE (one per line)")
        self.additional_fields_edit.setMaximumHeight(100)
        layout.addRow("Additional Fields:", self.additional_fields_edit)

class SandboxDetailPanel(QWidget):
    object_data_updated = pyqtSignal(object)
    object_deleted = pyqtSignal(object)
    
    def __init__(self, main_window=None):
        super().__init__()
        self.current_object = None
        self.main_window = main_window

        self.code_tab = CodeEditorTab()
        self.login_tab = LoginCredentialsTab()
        
        self.setup_ui()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(10)

        # Object Information
        info_group = QGroupBox("Object Information")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(10, 15, 10, 15)
        info_layout.setSpacing(8)
        
        self.object_type_label = QLabel("None")
        self.object_id_label = QLabel("None")
        self.object_name_edit = QLineEdit()
        self.object_name_edit.textChanged.connect(self.on_name_changed)
        
        info_layout.addRow("Type:", self.object_type_label)
        info_layout.addRow("ID:", self.object_id_label)
        info_layout.addRow("Name:", self.object_name_edit)
        
        layout.addWidget(info_group)

        self.tab_widget = QTabWidget()

        self.properties_tab = QWidget()
        self.properties_layout = QFormLayout(self.properties_tab)
        self.properties_layout.setContentsMargins(10, 15, 10, 15)
        self.properties_layout.setSpacing(8)
        
        self.property_fields = {}
        
        self.tab_widget.addTab(self.properties_tab, "Properties")
        self.tab_widget.addTab(self.code_tab, "Source Code")
        self.tab_widget.addTab(self.login_tab, "Login Credentials")
        
        layout.addWidget(self.tab_widget)
        
        self.code_tab.language_combo.currentTextChanged.connect(self.on_language_changed)
        
        # Hierarchy
        self.hierarchy_group = QGroupBox("Hierarchy")
        hierarchy_layout = QVBoxLayout(self.hierarchy_group)
        hierarchy_layout.setContentsMargins(10, 15, 10, 15)
        
        self.children_tree = QTreeWidget()
        self.children_tree.setHeaderLabel("Child Objects")
        self.children_tree.setMaximumHeight(150)
        
        hierarchy_layout.addWidget(self.children_tree)
        
        layout.addWidget(self.hierarchy_group)
        
        # Notes
        notes_group = QGroupBox("Notes")
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setContentsMargins(10, 15, 10, 15)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add technical notes here...")
        self.notes_edit.setMaximumHeight(120)
        self.notes_edit.textChanged.connect(self.on_notes_changed)
        notes_layout.addWidget(self.notes_edit)
        
        layout.addWidget(notes_group)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setContentsMargins(10, 15, 10, 15)
        actions_layout.setSpacing(8)
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self.save_changes)
        self.delete_btn = QPushButton("Delete Object")
        self.delete_btn.clicked.connect(self.delete_object)
        
        actions_layout.addWidget(self.save_btn)
        actions_layout.addWidget(self.delete_btn)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        main_layout.addWidget(scroll_area)
        
        self.clear_panel()
    
    def should_show_code_tab(self, obj_type):
        code_related_types = [
            ObjectType.CODE_FILE, ObjectType.WEB_APP, ObjectType.API_ENDPOINT,
            ObjectType.DJANGO, ObjectType.FLASK, ObjectType.NODEJS, ObjectType.SPRING,
            ObjectType.EXPRESS, ObjectType.NESTJS, ObjectType.RAILS,
            ObjectType.REACT, ObjectType.ANGULAR, ObjectType.VUE,
            ObjectType.WEB_FOLDER, ObjectType.CONFIG_FILE
        ]
        return obj_type in code_related_types
    
    def should_show_login_tab(self, obj_type):
        login_related_types = [
            ObjectType.SERVER, ObjectType.DATABASE, ObjectType.MYSQL, ObjectType.POSTGRESQL,
            ObjectType.MONGODB, ObjectType.REDIS, ObjectType.APACHE, ObjectType.NGINX,
            ObjectType.IIS, ObjectType.TOMCAT, ObjectType.ROUTER, ObjectType.FIREWALL,
            ObjectType.ACCESS_POINT, ObjectType.SWITCH, ObjectType.USER
        ]
        return obj_type in login_related_types
    
    def update_tab_visibility(self, obj_type):
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabVisible(i, False)

        self.tab_widget.setTabVisible(0, True)

        if self.should_show_code_tab(obj_type):
            self.tab_widget.setTabVisible(1, True)

        if self.should_show_login_tab(obj_type):
            self.tab_widget.setTabVisible(2, True)
    
    def on_language_changed(self):
        if (self.current_object and 
            self.current_object.object_type.value == 'code_file' and
            hasattr(self.main_window, 'object_widgets')):
            
            obj_widget = self.main_window.object_widgets.get(self.current_object.id)
            if obj_widget and hasattr(obj_widget, 'update_icon'):
                obj_widget.update_icon()
    
    def display_object(self, obj):
        self.current_object = obj
        self.object_type_label.setText(SandboxObjectFactory.get_object_name(obj.object_type))
        self.object_id_label.setText(obj.id)
        self.object_name_edit.setText(obj.name)

        self.update_tab_visibility(obj.object_type)

        self.clear_property_fields()
        self.create_property_fields(obj.properties)
        
        if obj.code_content and self.should_show_code_tab(obj.object_type):
            self.load_code_content(obj.code_content)
        else:
            self.clear_code_content()
        
        if obj.login_credentials and self.should_show_login_tab(obj.object_type):
            self.load_login_credentials(obj.login_credentials)
        else:
            self.clear_login_credentials()
        
        self.update_hierarchy_tree()
        
        self.notes_edit.setPlainText(obj.properties.get('notes', ''))
        
        self.tab_widget.setVisible(True)
        self.hierarchy_group.setVisible(True)
        self.setEnabled(True)
    
    def load_code_content(self, code_content):
        if code_content.language:
            index = self.code_tab.language_combo.findText(code_content.language)
            if index >= 0:
                self.code_tab.language_combo.setCurrentIndex(index)
        
        self.code_tab.code_editor.setPlainText(code_content.source_code)
        self.code_tab.dependencies_edit.setPlainText('\n'.join(code_content.dependencies))
        
        env_vars_text = '\n'.join([f"{k}={v}" for k, v in code_content.environment_vars.items()])
        self.code_tab.env_vars_edit.setPlainText(env_vars_text)
    
    def clear_code_content(self):
        self.code_tab.language_combo.setCurrentIndex(0)
        self.code_tab.code_editor.clear()
        self.code_tab.dependencies_edit.clear()
        self.code_tab.env_vars_edit.clear()
    
    def load_login_credentials(self, login_creds):
        self.login_tab.username_edit.setText(login_creds.username)
        self.login_tab.password_edit.setText(login_creds.password)
        self.login_tab.url_edit.setText(login_creds.url)
        self.login_tab.port_edit.setText(str(login_creds.port) if login_creds.port else "")
        self.login_tab.database_edit.setText(login_creds.database)
        
        additional_fields = '\n'.join([f"{k}={v}" for k, v in login_creds.additional_fields.items()])
        self.login_tab.additional_fields_edit.setPlainText(additional_fields)
    
    def clear_login_credentials(self):
        self.login_tab.username_edit.clear()
        self.login_tab.password_edit.clear()
        self.login_tab.url_edit.clear()
        self.login_tab.port_edit.clear()
        self.login_tab.database_edit.clear()
        self.login_tab.additional_fields_edit.clear()
    
    def create_property_fields(self, properties):
        for key, value in properties.items():
            if key == 'notes':
                continue
                
            label = QLabel(key.replace('_', ' ').title() + ":")
            
            if isinstance(value, bool):
                field = QComboBox()
                field.addItems(["False", "True"])
                field.setCurrentText(str(value))
            elif isinstance(value, (list, dict)):
                field = QTextEdit()
                field.setPlainText(str(value))
                field.setMaximumHeight(60)
            elif isinstance(value, str) and len(value) > 50:
                field = QTextEdit()
                field.setPlainText(str(value))
                field.setMaximumHeight(80)
            else:
                field = QLineEdit()
                field.setText(str(value))
            
            field.setProperty('propertyKey', key)
            
            if isinstance(field, (QLineEdit, QTextEdit)):
                field.textChanged.connect(self.on_property_changed)
            elif isinstance(field, QComboBox):
                field.currentTextChanged.connect(self.on_property_changed)
            
            self.property_fields[key] = field
            self.properties_layout.addRow(label, field)
    
    def clear_property_fields(self):
        for i in reversed(range(self.properties_layout.count())):
            item = self.properties_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.property_fields.clear()
    
    def update_hierarchy_tree(self):
        self.children_tree.clear()
        
        if not self.current_object or not self.current_object.children:
            return
        
        root_item = QTreeWidgetItem(self.children_tree, [f"Children ({len(self.current_object.children)})"])
        
        for child_id in self.current_object.children:
            child_obj = self.main_window.sandbox_manager.environment.get_object(child_id)
            if child_obj:
                child_item = QTreeWidgetItem(root_item, [
                    f"{SandboxObjectFactory.get_object_name(child_obj.object_type)}: {child_obj.name}"
                ])
        
        root_item.setExpanded(True)
    
    def on_name_changed(self):
        if self.current_object:
            self.current_object.name = self.object_name_edit.text()
            self.object_data_updated.emit(self.current_object)
    
    def on_property_changed(self):
        if not self.current_object:
            return
            
        sender = self.sender()
        key = sender.property('propertyKey')
        
        if isinstance(sender, QLineEdit):
            self.current_object.properties[key] = sender.text()
        elif isinstance(sender, QTextEdit):
            self.current_object.properties[key] = sender.toPlainText()
        elif isinstance(sender, QComboBox):
            value = sender.currentText()
            if value.lower() in ['true', 'false']:
                self.current_object.properties[key] = value.lower() == 'true'
            else:
                self.current_object.properties[key] = value
        
        self.object_data_updated.emit(self.current_object)
    
    def on_notes_changed(self):
        if self.current_object:
            self.current_object.properties['notes'] = self.notes_edit.toPlainText()
            self.object_data_updated.emit(self.current_object)
    
    def save_changes(self):
        if self.current_object:
            if self.should_show_code_tab(self.current_object.object_type):
                self.save_code_content()
            
            if self.should_show_login_tab(self.current_object.object_type):
                self.save_login_credentials()
            
            self.object_data_updated.emit(self.current_object)
    
    def save_code_content(self):
        if not self.current_object:
            return
        
        language = self.code_tab.language_combo.currentText()
        source_code = self.code_tab.code_editor.toPlainText()
        dependencies = self.code_tab.dependencies_edit.toPlainText().split('\n')
        dependencies = [dep.strip() for dep in dependencies if dep.strip()]
        
        env_vars = {}
        for line in self.code_tab.env_vars_edit.toPlainText().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
        
        self.current_object.set_code_content(language, source_code, dependencies, env_vars)
        
        self.on_language_changed()
    
    def save_login_credentials(self):
        if not self.current_object:
            return
        
        username = self.login_tab.username_edit.text()
        password = self.login_tab.password_edit.text()
        url = self.login_tab.url_edit.text()
        
        try:
            port = int(self.login_tab.port_edit.text()) if self.login_tab.port_edit.text() else 0
        except ValueError:
            port = 0
        
        database = self.login_tab.database_edit.text()
        
        additional_fields = {}
        for line in self.login_tab.additional_fields_edit.toPlainText().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                additional_fields[key.strip()] = value.strip()
        
        self.current_object.set_login_credentials(username, password, url, port, database, additional_fields)
    
    def delete_object(self):
        if self.current_object:
            self.object_deleted.emit(self.current_object)
            self.clear_panel()
    
    def clear_panel(self):
        self.current_object = None
        self.object_type_label.setText("None")
        self.object_id_label.setText("None")
        self.object_name_edit.clear()

        self.clear_property_fields()
        self.children_tree.clear()
        self.notes_edit.clear()

        self.clear_code_content()
        self.clear_login_credentials()
        
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabVisible(i, i == 0)
        
        self.tab_widget.setVisible(False)
        self.hierarchy_group.setVisible(False)
        self.setEnabled(False)