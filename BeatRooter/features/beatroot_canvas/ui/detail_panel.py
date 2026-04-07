from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QScrollArea,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QPixmap
from utils.image_utils import ImageUtils
from features.beatroot_canvas.core import NodeFactory
from features.tools.core.tool_node_service import ToolNodeService
import os
import base64
import json


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        # Prevent accidental value changes while scrolling in the side panel.
        event.ignore()


class DetailPanel(QWidget):
    node_data_updated = pyqtSignal(object)
    node_deleted = pyqtSignal(object)
    panel_visibility_changed = pyqtSignal(bool)
    TOOL_NODE_HIDDEN_FIELDS = {
        "is_tool_node",
        "target_source_node_id",
        "created_node_ids",
        "last_output",
        "last_output_preview",
        "last_output_size",
        "has_output",
    }
    SCREENSHOT_READONLY_FIELDS = {
        "filename",
        "file_size",
        "dimensions",
        "current_dimensions",
        "format",
        "metadata",
        "exif_data",
        "png_info",
        "image_data",
    }
    
    def __init__(self, main_window=None): 
        super().__init__()
        self.current_node = None
        self.main_window = main_window
        self.tools_widget = None
        self._suppress_history_events = False
        self._pending_history_description = None
        self._history_timer = QTimer(self)
        self._history_timer.setSingleShot(True)
        self._history_timer.setInterval(500)
        self._history_timer.timeout.connect(self.flush_pending_history)
        self.setup_ui()
    
    def setup_ui(self):
        self.setObjectName("DetailPanel")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        self.right_tabs = QTabWidget()
        self.right_tabs.setObjectName("RightTabs")
        self.right_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.right_tabs.setDocumentMode(True)

        nodes_tab = QWidget()
        nodes_tab_layout = QVBoxLayout(nodes_tab)
        nodes_tab_layout.setContentsMargins(0, 0, 0, 0)
        nodes_tab_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("DetailScrollArea")
        scroll_widget = QWidget()
        scroll_widget.setObjectName("DetailScrollWidget")
        self.content_layout = QVBoxLayout(scroll_widget)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(8)

        info_group = QGroupBox("Node Information")
        info_group.setObjectName("NodeInfoGroup")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(10, 15, 10, 15)
        info_layout.setSpacing(8)
        
        self.node_type_label = QLabel("None")
        self.node_id_label = QLabel("None")
        
        info_layout.addRow("Type:", self.node_type_label)
        info_layout.addRow("ID:", self.node_id_label)
        
        self.content_layout.addWidget(info_group)
        
        # Data editing group
        self.data_group = QGroupBox("Edit Data")
        self.data_group.setObjectName("NodeDataGroup")
        self.data_layout = QFormLayout(self.data_group)
        self.data_layout.setContentsMargins(10, 15, 10, 15)
        self.data_layout.setSpacing(8)
        self.data_group.setVisible(False)
        
        self.data_fields = {}
        
        self.content_layout.addWidget(self.data_group)
        
        # Notes group
        notes_group = QGroupBox("Notes")
        notes_group.setObjectName("NotesGroup")
        notes_layout = QVBoxLayout(notes_group)
        notes_layout.setContentsMargins(10, 15, 10, 15)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add investigation notes here...")
        self.notes_edit.setMaximumHeight(120)
        self.notes_edit.textChanged.connect(self.on_notes_changed)
        notes_layout.addWidget(self.notes_edit)
        
        self.content_layout.addWidget(notes_group)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_group.setObjectName("ActionsGroup")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setContentsMargins(10, 15, 10, 15)
        actions_layout.setSpacing(8)
        
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setObjectName("SaveNodeBtn")
        self.save_btn.clicked.connect(self.save_changes)
        self.delete_btn = QPushButton("Delete Node")
        self.delete_btn.setObjectName("DeleteNodeBtn")
        self.delete_btn.clicked.connect(self.delete_node)
        
        actions_layout.addWidget(self.save_btn)
        actions_layout.addWidget(self.delete_btn)
        
        self.content_layout.addWidget(actions_group)

        self.content_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        nodes_tab_layout.addWidget(scroll_area)
        self.right_tabs.addTab(nodes_tab, "Nodes")

        self.stackers_tab = QWidget()
        stackers_tab_layout = QVBoxLayout(self.stackers_tab)
        stackers_tab_layout.setContentsMargins(0, 0, 0, 0)
        stackers_tab_layout.setSpacing(0)

        self.stackers_mount = QWidget()
        self.stackers_mount_layout = QVBoxLayout(self.stackers_mount)
        self.stackers_mount_layout.setContentsMargins(0, 0, 0, 0)
        self.stackers_mount_layout.setSpacing(0)
        stackers_tab_layout.addWidget(self.stackers_mount)

        self.right_tabs.addTab(self.stackers_tab, "Stackers")

        self.tools_tab = QWidget()
        tools_tab_layout = QVBoxLayout(self.tools_tab)
        tools_tab_layout.setContentsMargins(0, 0, 0, 0)
        tools_tab_layout.setSpacing(0)

        self.tools_mount = QWidget()
        self.tools_mount_layout = QVBoxLayout(self.tools_mount)
        self.tools_mount_layout.setContentsMargins(0, 0, 0, 0)
        self.tools_mount_layout.setSpacing(0)
        tools_tab_layout.addWidget(self.tools_mount)

        self.right_tabs.addTab(self.tools_tab, "Tools")

        main_layout.addWidget(self.right_tabs)
        
        self.clear_panel()

    def attach_tools_widget(self, tools_widget):
        if not tools_widget:
            return
        self.tools_widget = tools_widget
        tools_widget.setParent(self.tools_mount)
        self.tools_mount_layout.addWidget(tools_widget)

    def show_tools_tab(self):
        self.right_tabs.setCurrentWidget(self.tools_tab)

    def show_nodes_tab(self):
        self.right_tabs.setCurrentIndex(0)

    def attach_stackers_widget(self, stackers_widget):
        if not stackers_widget:
            return
        stackers_widget.setParent(self.stackers_mount)
        self.stackers_mount_layout.addWidget(stackers_widget)

    def show_stackers_tab(self):
        self.right_tabs.setCurrentWidget(self.stackers_tab)

    def set_nodes_tab_visible(self, visible: bool):
        index = self.right_tabs.indexOf(self.right_tabs.widget(0))
        if index >= 0:
            self.right_tabs.setTabVisible(index, bool(visible))
            self._ensure_valid_current_tab()
            self._update_panel_visibility()

    def set_tools_tab_visible(self, visible: bool):
        index = self.right_tabs.indexOf(self.tools_tab)
        if index >= 0:
            self.right_tabs.setTabVisible(index, bool(visible))
            self._ensure_valid_current_tab()
            self._update_panel_visibility()

    def set_stackers_tab_visible(self, visible: bool):
        index = self.right_tabs.indexOf(self.stackers_tab)
        if index >= 0:
            self.right_tabs.setTabVisible(index, bool(visible))
            self._ensure_valid_current_tab()
            self._update_panel_visibility()

    def is_nodes_tab_visible(self) -> bool:
        index = self.right_tabs.indexOf(self.right_tabs.widget(0))
        return index >= 0 and self.right_tabs.isTabVisible(index)

    def is_tools_tab_visible(self) -> bool:
        index = self.right_tabs.indexOf(self.tools_tab)
        return index >= 0 and self.right_tabs.isTabVisible(index)

    def is_stackers_tab_visible(self) -> bool:
        index = self.right_tabs.indexOf(self.stackers_tab)
        return index >= 0 and self.right_tabs.isTabVisible(index)

    def _ensure_valid_current_tab(self):
        current_index = self.right_tabs.currentIndex()
        if current_index >= 0 and self.right_tabs.isTabVisible(current_index):
            return
        for index in range(self.right_tabs.count()):
            if self.right_tabs.isTabVisible(index):
                self.right_tabs.setCurrentIndex(index)
                return

    def has_visible_tabs(self) -> bool:
        for index in range(self.right_tabs.count()):
            if self.right_tabs.isTabVisible(index):
                return True
        return False

    def _update_panel_visibility(self):
        self.panel_visibility_changed.emit(self.has_visible_tabs())

    def queue_history_save(self, description):
        if self._suppress_history_events:
            return
        if not hasattr(self, 'main_window') or not self.main_window:
            return
        self._pending_history_description = description
        self._history_timer.start()

    def flush_pending_history(self):
        if not self._pending_history_description:
            return
        if not hasattr(self, 'main_window') or not self.main_window:
            self._pending_history_description = None
            return

        self.main_window.graph_manager.save_state(self._pending_history_description)
        self.main_window.update_undo_redo_buttons()
        self._pending_history_description = None

    def display_node(self, node):
        self.current_node = node
        self._suppress_history_events = True
        try:
            self.node_type_label.setText(node.type.upper())
            self.node_id_label.setText(node.id)

            self.clear_data_fields()
            
            for key, value in node.data.items():
                if key == 'notes':
                    self.notes_edit.setPlainText(str(value))
                else:
                    if ToolNodeService.is_tool_node(node) and key in self.TOOL_NODE_HIDDEN_FIELDS:
                        continue
                    self.create_data_field(key, value)
            
            if not node.data or len(node.data) <= 1:
                self.create_fields_from_template(node.type)

            if node.type == 'credential':
                self.on_credential_type_changed(node.data.get('credential_type', 'password'))

            if node.type == 'screenshot' and node.data.get('metadata'):
                metadata_btn = QPushButton("View Metadata Details")
                metadata_btn.clicked.connect(self.view_metadata_details)
                self.data_layout.addRow("Metadata:", metadata_btn)

            if ToolNodeService.is_tool_node(node) and node.data.get("has_output") and self.main_window:
                output_btn = QPushButton("View Raw Output")
                output_btn.clicked.connect(lambda: self.main_window.show_tool_node_output(node))
                self.data_layout.addRow("Output:", output_btn)
            
            self.data_group.setVisible(True)
            self.save_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        finally:
            self._suppress_history_events = False
    
    def create_fields_from_template(self, node_type):
        try:
            default_data = NodeFactory.create_node_data(node_type)
            
            for key, default_value in default_data.items():
                if key not in self.data_fields and key != 'notes':
                    self.create_data_field(key, default_value)
                    
        except Exception as e:
            print(f"Error creating fields from template: {e}")
    
    def create_data_field(self, key, value):
        label = QLabel(key.replace('_', ' ').title() + ":")

        if self.current_node and self.current_node.type == 'screenshot' and key in self.SCREENSHOT_READONLY_FIELDS:
            if key == 'image_data':
                if value:
                    field = QPushButton("View Image Data")
                    field.clicked.connect(lambda checked, val=value: self.view_image_data(val))
                else:
                    field = QLabel("No image data")
            elif key in {'metadata', 'exif_data', 'png_info'}:
                count = len(value) if isinstance(value, dict) else 0
                field = QLabel(f"Read-only ({count} entries)")
                field.setToolTip("Image metadata is read-only. Use 'View Metadata Details' for full inspection.")
            else:
                field = QLineEdit()
                field.setText(str(value))
                field.setReadOnly(True)
            field.setProperty('readOnlyInfo', True)
            self.data_fields[key] = field
            self.data_layout.addRow(label, field)
            return
        
        if key == 'content' and self.current_node and self.current_node.type == 'script':
            field = QPushButton("Open Script Editor")
            field.setProperty('fieldKey', key)
            field.clicked.connect(self.open_script_editor)
        
        elif key == 'credential_type' and self.current_node and self.current_node.type == 'credential':
            field = NoWheelComboBox()
            field.addItems(["password", "hash"])
            field.setCurrentText(str(value))
            field.currentTextChanged.connect(self.on_credential_type_changed)
        
        elif key == 'file_path' and self.current_node and self.current_node.type == 'screenshot':
            field = QPushButton("Import Image..." if not value else "Change Image...")
            field.setProperty('fieldKey', key)
            field.clicked.connect(self.import_screenshot_image)
            
            if value and os.path.exists(value):
                self.create_image_preview(value)
        
        elif key == 'image_data' and self.current_node and self.current_node.type == 'screenshot':
            if value:
                field = QPushButton("View Image Data")
                field.setProperty('fieldKey', key)
                field.clicked.connect(lambda checked, val=value: self.view_image_data(val))
            else:
                field = QLabel("No image data")
        elif NodeFactory.get_field_options(key):
            field = NoWheelComboBox()
            options = NodeFactory.get_field_options(key)
            field.addItems(options)
            str_value = str(value)
            if str_value and str_value not in options:
                field.addItem(str_value)
            field.setCurrentText(str_value if str_value else options[0])
        
        elif isinstance(value, bool):
            field = NoWheelComboBox()
            field.addItems(["False", "True"])
            field.setCurrentText(str(value))
        elif isinstance(value, int):
            field = QLineEdit()
            field.setText(str(value))
            field.setProperty('valueType', 'int')
        elif isinstance(value, float):
            field = QLineEdit()
            field.setText(str(value))
            field.setProperty('valueType', 'float')
        elif isinstance(value, list):
            field = QLineEdit()
            field.setText(", ".join(str(item) for item in value))
            field.setProperty('valueType', 'list')
        elif isinstance(value, dict):
            field = QTextEdit()
            field.setPlainText(json.dumps(value, ensure_ascii=False))
            field.setMaximumHeight(80)
            field.setProperty('valueType', 'dict')
        elif key in ['threat_level', 'severity', 'priority', 'privilege_level', 'language', 'risk_level', 'confidence', 'status', 'analysis_status']:
            field = NoWheelComboBox()
            if key == 'language':
                field.addItems(["bash", "python", "powershell", "javascript", "batch", "other"])
            elif key == 'privilege_level':
                field.addItems(["user", "admin", "root", "system", "unknown"])
            elif key in ['confidence', 'risk_level']:
                field.addItems(["low", "medium", "high", "critical", "unknown"])
            elif key in ['status', 'analysis_status']:
                field.addItems(["new", "in progress", "completed", "pending", "open", "closed"])
            else:
                field.addItems(["low", "medium", "high", "critical", "unknown"])
            field.setCurrentText(str(value))
        elif key in ['analysis_status', 'isolation_level', 'file_type', 'incident_type', 'action_type', 'technique', 'ioc_type']:
            field = NoWheelComboBox()
            if key == 'analysis_status':
                field.addItems(["queued", "in progress", "completed", "failed"])
            elif key == 'isolation_level':
                field.addItems(["sandbox", "isolated", "production"])
            elif key == 'file_type':
                field.addItems(["PE32", "PE64", "ELF", "Script", "Document", "Other"])
            elif key == 'incident_type':
                field.addItems(["Malware", "Unauthorized Access", "Data Breach", "DDoS", "Phishing", "Other"])
            elif key == 'action_type':
                field.addItems(["Network Block", "Process Termination", "User Account Disable", "Other"])
            elif key == 'technique':
                field.addItems(["SQL Injection", "XSS", "RCE", "Phishing", "Brute Force", "Other"])
            elif key == 'ioc_type':
                field.addItems(["IP Address", "Domain", "Hash", "URL", "Email", "Other"])
            else:
                field.addItems(["low", "medium", "high", "critical", "unknown"])
            field.setCurrentText(str(value))
        elif isinstance(value, str) and len(value) > 50:
            field = QTextEdit()
            field.setPlainText(str(value))
            field.setMaximumHeight(80)
        else:
            field = QLineEdit()
            field.setText(str(value))
        
        if key != 'content' or self.current_node.type != 'script':
            field.setProperty('fieldKey', key)
        
        if isinstance(field, (QLineEdit, QTextEdit)):
            field.textChanged.connect(self.on_field_changed)
        elif isinstance(field, QComboBox) and key != 'credential_type':
            field.currentTextChanged.connect(self.on_field_changed)
        
        self.data_fields[key] = field
        self.data_layout.addRow(label, field)

    def view_image_data(self, image_data):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Image Data (Base64)")
            dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(dialog)
            
            info_label = QLabel(f"Image data size: {len(image_data)} characters")
            
            text_edit = QTextEdit()
            text_edit.setPlainText(image_data)
            text_edit.setReadOnly(True)
            
            button_layout = QHBoxLayout()
            copy_btn = QPushButton("Copy to Clipboard")
            close_btn = QPushButton("Close")
            
            copy_btn.clicked.connect(lambda: self.copy_to_clipboard(image_data))
            close_btn.clicked.connect(dialog.accept)
            
            button_layout.addWidget(copy_btn)
            button_layout.addWidget(close_btn)
            
            layout.addWidget(info_label)
            layout.addWidget(text_edit)
            layout.addLayout(button_layout)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to display image data: {e}")

    def copy_to_clipboard(self, text):
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Success", "Image data copied to clipboard!")

    def import_screenshot_image(self):
        if not self.current_node or self.current_node.type != 'screenshot':
            return
        
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Import Screenshot Image")
        file_dialog.setNameFilters(ImageUtils.get_supported_formats())
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self.load_screenshot_image_with_data(file_path)

    def load_screenshot_image_with_data(self, file_path):
        try:
            print(f"Carregando imagem: {file_path}")

            metadata = ImageUtils.load_image_metadata(file_path)
            print(f"Metadados extraídos: {metadata}")

            image_data = ImageUtils.image_to_base64(file_path)
            
            all_metadata = metadata.get('all_metadata', {})
            exif_data = metadata.get('exif_data', {})
            png_info = metadata.get('png_info', {})
            
            print(f"EXIF Tags: {len(exif_data)}")
            print(f"PNG Info: {len(png_info)}")
            print(f"Todos metadados: {len(all_metadata)}")

            self.current_node.data.update({
                'file_path': file_path,
                'filename': os.path.basename(file_path),
                'file_size': metadata.get('file_size', ''),
                'dimensions': metadata.get('dimensions', ''),
                'format': metadata.get('format', ''),
                'metadata': all_metadata,
                'exif_data': exif_data,
                'png_info': png_info,
                'image_data': image_data
            })
            
            print(f"Dados atualizados do nó")
            
            self.display_node(self.current_node)
            
            self.create_image_preview(file_path)
            
            self.node_data_updated.emit(self.current_node)
            
            total_metadata = len(all_metadata)
            QMessageBox.information(self, "Success", 
                                f"Image loaded successfully!\n"
                                f"File: {os.path.basename(file_path)}\n"
                                f"Size: {metadata.get('file_size', 'N/A')}\n"
                                f"Dimensions: {metadata.get('dimensions', 'N/A')}\n"
                                f"Format: {metadata.get('format', 'N/A')}\n"
                                f"Total Metadata Fields: {total_metadata}")
            
        except Exception as e:
            print(f"ERRO ao carregar imagem: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load image: {e}")

    def view_metadata_details(self):
        if not self.current_node or self.current_node.type != 'screenshot':
            return
        
        all_metadata = self.current_node.data.get('all_metadata', {})
        metadata = self.current_node.data.get('metadata', {})
        exif_data = self.current_node.data.get('exif_data', {})
        png_info = self.current_node.data.get('png_info', {})
        
        combined_metadata = {}
        combined_metadata.update(all_metadata)
        combined_metadata.update(metadata)
        combined_metadata.update(exif_data)
        combined_metadata.update(png_info)
        
        print(f"Metadados combinados: {len(combined_metadata)} campos")
        
        if not combined_metadata:
            QMessageBox.information(self, "Metadata", "No metadata available")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Image Metadata - {len(combined_metadata)} fields")
        dialog.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setFontFamily("Courier New")
        text_edit.setFontPointSize(9)

        metadata_text = f"COMPLETE IMAGE METADATA ({len(combined_metadata)} fields)\n"
        metadata_text += "=" * 50 + "\n\n"
        
        categories = {
            'File Information': [],
            'EXIF Data': [],
            'PNG Information': [],
            'Image Properties': [],
            'Other Metadata': []
        }
        
        for key, value in sorted(combined_metadata.items()):
            key_str = str(key)
            value_str = str(value)
            
            if any(prefix in key_str for prefix in ['file_', 'File', 'filename']):
                categories['File Information'].append((key_str, value_str))
            elif any(prefix in key_str for prefix in ['exif', 'EXIF', 'GPS', 'DateTime']):
                categories['EXIF Data'].append((key_str, value_str))
            elif any(prefix in key_str for prefix in ['png', 'PNG', 'tEXt', 'zTXt']):
                categories['PNG Information'].append((key_str, value_str))
            elif any(prefix in key_str for prefix in ['width', 'height', 'size', 'mode', 'format', 'dimensions']):
                categories['Image Properties'].append((key_str, value_str))
            else:
                categories['Other Metadata'].append((key_str, value_str))
        
        for category, items in categories.items():
            if items:
                metadata_text += f"\n{category.upper()} ({len(items)} items):\n"
                metadata_text += "-" * 40 + "\n"
                for key, value in sorted(items):
                    metadata_text += f"{key:<30} : {value}\n"
        
        text_edit.setPlainText(metadata_text)
        text_edit.setReadOnly(True)

        button_layout = QHBoxLayout()
        copy_btn = QPushButton("Copy All")
        export_btn = QPushButton("Export JSON")
        close_btn = QPushButton("Close")
        
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(metadata_text))
        export_btn.clicked.connect(lambda: self.export_metadata_json(combined_metadata))
        close_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(copy_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(close_btn)
        
        layout.addWidget(text_edit)
        layout.addLayout(button_layout)
        
        dialog.exec()

    def export_metadata_json(self, metadata):
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Metadata as JSON", "", "JSON Files (*.json)"
            )
            if filename:
                if not filename.endswith('.json'):
                    filename += '.json'
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(self, "Success", f"Metadata exported to {filename}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export metadata: {e}")

    def load_screenshot_image(self, file_path):
        self.load_screenshot_image_with_data(file_path)

    def create_image_preview(self, file_path):
        try:
            if hasattr(self, 'image_preview_label'):
                self.data_layout.removeWidget(self.image_preview_label)
                self.image_preview_label.deleteLater()
            
            self.image_preview_label = QLabel()
            self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_preview_label.setStyleSheet("border: 1px solid #555; background: #2a2a2a;")
            self.image_preview_label.setMaximumHeight(200)
            self.image_preview_label.setScaledContents(True)
            
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(300, 150, Qt.AspectRatioMode.KeepAspectRatio, 
                                    Qt.TransformationMode.SmoothTransformation)
                self.image_preview_label.setPixmap(pixmap)
                
                self.data_layout.addRow("Preview:", self.image_preview_label)
                
        except Exception as e:
            print(f"Error creating image preview: {e}")

    def open_script_editor(self):
        if not self.current_node or self.current_node.type != 'script':
            return
            
        from utils.script_editor import ScriptEditor
        
        editor = ScriptEditor(self.current_node.data, self)
        editor.script_saved.connect(self.on_script_updated)
        editor.exec()

    def on_script_updated(self, updated_data):
        if self.current_node:
            self.current_node.data.update(updated_data)
            self.display_node(self.current_node)
            self.node_data_updated.emit(self.current_node)

    def on_credential_type_changed(self, new_type):
        if not self.current_node or self.current_node.type != 'credential':
            return
        
        self.current_node.data['credential_type'] = new_type
        
        password_field = self.data_fields.get('password')
        hash_field = self.data_fields.get('password_hash')
        
        if password_field and hash_field:
            if new_type == 'password':
                password_field.setVisible(True)
                self.data_layout.labelForField(password_field).setVisible(True)
                hash_field.setVisible(False)
                self.data_layout.labelForField(hash_field).setVisible(False)
            else:
                password_field.setVisible(False)
                self.data_layout.labelForField(password_field).setVisible(False)
                hash_field.setVisible(True)
                self.data_layout.labelForField(hash_field).setVisible(True)
        
    def clear_data_fields(self):
        for i in reversed(range(self.data_layout.count())):
            item = self.data_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.data_fields.clear()

        if hasattr(self, 'image_preview_label'):
            self.image_preview_label.deleteLater()
            delattr(self, 'image_preview_label')
    
    def clear_panel(self):
        self._history_timer.stop()
        self._pending_history_description = None
        self.current_node = None
        self.node_type_label.setText("None")
        self.node_id_label.setText("None")

        for i in reversed(range(self.data_layout.count())):
            item = self.data_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        self.data_fields.clear()
        self.notes_edit.clear()
        self.data_group.setVisible(False)
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
    
    def on_field_changed(self):
        if not self.current_node:
            return
            
        sender = self.sender()
        if not sender:
            return
        key = sender.property('fieldKey')
        if not key:
            return
        
        if isinstance(sender, QLineEdit):
            text_value = sender.text()
            value_type = sender.property('valueType')
            if value_type == 'int':
                try:
                    self.current_node.data[key] = int(text_value)
                except ValueError:
                    self.current_node.data[key] = 0
            elif value_type == 'float':
                try:
                    self.current_node.data[key] = float(text_value)
                except ValueError:
                    self.current_node.data[key] = 0.0
            elif value_type == 'list':
                self.current_node.data[key] = [item.strip() for item in text_value.split(',') if item.strip()]
            else:
                self.current_node.data[key] = text_value
        elif isinstance(sender, QTextEdit):
            text_value = sender.toPlainText()
            if sender.property('valueType') == 'dict':
                try:
                    parsed = json.loads(text_value) if text_value.strip() else {}
                    self.current_node.data[key] = parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    self.current_node.data[key] = {}
            else:
                self.current_node.data[key] = text_value
        elif isinstance(sender, QComboBox):
            value = sender.currentText()
            if value.lower() in ['true', 'false']:
                self.current_node.data[key] = value.lower() == 'true'
            else:
                self.current_node.data[key] = value

        self.queue_history_save(f"Update {self.current_node.type} node field: {key}")


    
    def on_notes_changed(self):
        if self.current_node:
            self.current_node.data['notes'] = self.notes_edit.toPlainText()
            self.queue_history_save(f"Update {self.current_node.type} node notes")
    
    def save_changes(self):
        if self.current_node:
            self.flush_pending_history()
            self.node_data_updated.emit(self.current_node)
    
    def delete_node(self):
        if self.current_node:
            self.node_deleted.emit(self.current_node)
            self.clear_panel()
