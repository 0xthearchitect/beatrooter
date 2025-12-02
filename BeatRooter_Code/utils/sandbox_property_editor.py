from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QTextEdit, QComboBox, QPushButton, 
                             QLabel, QGroupBox, QScrollArea)
from PyQt6.QtCore import pyqtSignal

class SandboxPropertyEditor(QDialog):
    properties_updated = pyqtSignal(dict)
    
    def __init__(self, sandbox_object, parent=None):
        super().__init__(parent)
        self.sandbox_object = sandbox_object
        self.setWindowTitle(f"Edit {sandbox_object.name}")
        self.setMinimumSize(500, 600)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel(f"Editing: {self.sandbox_object.name}")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(header_label)
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        form_layout = QVBoxLayout(scroll_widget)
        
        # Basic properties group
        basic_group = QGroupBox("Basic Properties")
        basic_layout = QFormLayout(basic_group)
        
        self.name_edit = QLineEdit(self.sandbox_object.name)
        basic_layout.addRow("Name:", self.name_edit)
        
        type_label = QLabel(self.sandbox_object.obj_type.value.replace('_', ' ').title())
        basic_layout.addRow("Type:", type_label)
        
        form_layout.addWidget(basic_group)
        
        # Specific properties group
        props_group = QGroupBox("Object Properties")
        props_layout = QFormLayout(props_group)
        
        self.property_widgets = {}
        
        for prop_name, prop_value in self.sandbox_object.properties.items():
            if isinstance(prop_value, bool):
                widget = QComboBox()
                widget.addItems(["False", "True"])
                widget.setCurrentText(str(prop_value))
            elif isinstance(prop_value, int):
                widget = QLineEdit(str(prop_value))
            elif isinstance(prop_value, list):
                widget = QTextEdit()
                widget.setPlainText(', '.join(prop_value))
            else:
                widget = QLineEdit(str(prop_value))
            
            self.property_widgets[prop_name] = widget
            display_name = prop_name.replace('_', ' ').title()
            props_layout.addRow(display_name + ":", widget)
        
        form_layout.addWidget(props_group)
        
        # Children section
        if self.sandbox_object.children:
            children_group = QGroupBox("Child Objects")
            children_layout = QVBoxLayout(children_group)
            
            for child in self.sandbox_object.children:
                child_label = QLabel(f"• {child.name} ({child.obj_type.value})")
                children_layout.addWidget(child_label)
            
            form_layout.addWidget(children_group)
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        cancel_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(self.save_changes)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
    
    def save_changes(self):
        self.sandbox_object.name = self.name_edit.text()
        
        for prop_name, widget in self.property_widgets.items():
            if isinstance(widget, QLineEdit):
                value = widget.text()
                if value.isdigit():
                    value = int(value)
                self.sandbox_object.properties[prop_name] = value
            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText()
                self.sandbox_object.properties[prop_name] = value
            elif isinstance(widget, QComboBox):
                value = widget.currentText() == "True"
                self.sandbox_object.properties[prop_name] = value
        
        self.sandbox_object.update()
        self.properties_updated.emit(self.sandbox_object.properties)
        self.accept()