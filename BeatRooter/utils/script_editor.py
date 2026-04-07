from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QLabel, QFileDialog, QMessageBox,
                             QComboBox, QLineEdit, QGroupBox, QFormLayout)
from PyQt6.QtCore import pyqtSignal, Qt
import os

class ScriptEditor(QDialog):
    script_saved = pyqtSignal(dict)
    
    def __init__(self, script_data, parent=None):
        super().__init__(parent)
        self.script_data = script_data.copy()
        self.setup_ui()
        self.load_script_data()
        
    def setup_ui(self):
        self.setWindowTitle("Script Editor")
        self.setGeometry(200, 200, 800, 600)
        
        layout = QVBoxLayout(self)

        info_group = QGroupBox("Script Information")
        info_layout = QFormLayout(info_group)
        
        self.filename_edit = QLineEdit()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["bash", "python", "powershell", "javascript", "batch", "other"])
        
        info_layout.addRow("Filename:", self.filename_edit)
        info_layout.addRow("Language:", self.language_combo)
        
        layout.addWidget(info_group)

        content_group = QGroupBox("Script Content")
        content_layout = QVBoxLayout(content_group)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Enter script content here...")
        content_layout.addWidget(self.content_edit)
        
        layout.addWidget(content_group)
        
        button_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("Import from File")
        self.import_btn.clicked.connect(self.import_from_file)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_script)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.import_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_script_data(self):
        self.filename_edit.setText(self.script_data.get('filename', ''))
        self.language_combo.setCurrentText(self.script_data.get('language', 'bash'))
        self.content_edit.setPlainText(self.script_data.get('content', ''))
    
    def import_from_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, 
            "Import Script File", 
            "", 
            "All Files (*);;Shell Scripts (*.sh);;Python Files (*.py);;PowerShell (*.ps1);;Batch Files (*.bat);;JavaScript (*.js)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()

                ext = os.path.splitext(filename)[1].lower()
                lang_map = {
                    '.sh': 'bash',
                    '.py': 'python', 
                    '.ps1': 'powershell',
                    '.bat': 'batch',
                    '.js': 'javascript'
                }
                
                self.script_data['file_path'] = filename
                self.script_data['filename'] = os.path.basename(filename)
                self.script_data['language'] = lang_map.get(ext, 'other')
                self.script_data['content'] = content
                
                self.load_script_data()
                
            except Exception as e:
                QMessageBox.warning(self, "Import Error", f"Failed to import file: {e}")
    
    def save_script(self):
        self.script_data.update({
            'filename': self.filename_edit.text(),
            'language': self.language_combo.currentText(),
            'content': self.content_edit.toPlainText()
        })
        
        self.script_saved.emit(self.script_data)
        self.accept()