import sys
import os
from PyQt6.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
    QToolBar, QStatusBar, QFileDialog, QMessageBox,
    QSplitter, QApplication, QDockWidget, QDialog, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QThread
from PyQt6.QtGui import QAction, QIcon, QKeySequence

from core.sandbox.sandbox_manager import SandboxManager
from core.sandbox.sandbox_object_factory import SandboxObjectFactory
from ui.sandbox.sandbox_canvas_widget import SandboxCanvasWidget
from ui.sandbox.sandbox_toolbox import SandboxToolbox
from ui.sandbox.sandbox_detail_panel import SandboxDetailPanel
from ui.sandbox.web_workspace_widget import WebWorkspaceWidget
from ui.sandbox.os_workspace_widget import OSWorkspaceWidget
from ui.sandbox.network_workspace_widget import NetworkWorkspaceWidget
from core.storage_manager import StorageManager
from core.theme_manager import ThemeManager
from models.object_model import ObjectCategory, ObjectType
from features.tools.docker.docker_integration import DockerAutomationManager
from utils.path_utils import get_resource_path

class SandboxMainWindow(QMainWindow):
    _window_refs = []

    def __init__(self, project_type=None, category=None, template_data=None):
        super().__init__()
        SandboxMainWindow._window_refs.append(self)
        self.sandbox_manager = SandboxManager()
        self.storage_manager = StorageManager()
        self.current_theme = 'cyber_modern'
        self.object_widgets = {}
        self.project_type = project_type
        self.category = category
        self.template_data = template_data
        self.workspace_mode = self.get_workspace_mode(category)
        self.web_mode = self.workspace_mode == 'web'
        self.web_workspace = None
        self.os_workspace = None
        self.network_workspace = None
        self.toolbox = None
        self.canvas_widget = None
        self.detail_panel = None
        self.toolbar = None
        self.object_menu = None
        self._skip_close_confirmation = False

        self.setWindowIcon(QIcon(get_resource_path("icons/app_icon.png", 'assets')))
        self.setup_ui()
        self.apply_theme(self.current_theme)
        self.setup_connections()

        self.docker_manager = DockerAutomationManager(self)

        self.update_menu_visibility()
        
        self.statusBar().showMessage(f"Ready - {self.get_project_title()}")
        self.sandbox_manager.save_state("Initial state")

    def get_project_title(self):
        if self.project_type and self.category:
            category_name = self.category.replace('_', ' ').title()
            return f"Sandbox - {category_name}"
        return "BeatRooter Sandbox"

    @staticmethod
    def is_web_category(category):
        return category in {'web_technologies', 'web_architecture', 'web_apps', 'docker_projects'}

    @staticmethod
    def is_os_category(category):
        return category in {'operating_systems', 'operative_system', 'os_analysis'}

    @staticmethod
    def is_network_category(category):
        return category in {'network_devices', 'network_topology'}

    @classmethod
    def get_workspace_mode(cls, category):
        if cls.is_web_category(category):
            return 'web'
        if cls.is_os_category(category):
            return 'os'
        if cls.is_network_category(category):
            return 'network'
        return 'legacy'

    def refresh_workspace_mode(self):
        self.workspace_mode = self.get_workspace_mode(self.category)
        self.web_mode = self.workspace_mode == 'web'

    def is_canvas_mode(self):
        return self.workspace_mode == 'legacy'

    def get_active_workspace(self):
        if self.workspace_mode == 'web':
            return self.web_workspace
        if self.workspace_mode == 'os':
            return self.os_workspace
        if self.workspace_mode == 'network':
            return self.network_workspace
        return None

    def setup_ui(self):
        self.setWindowTitle("BeatRooter Sandbox")
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        if self.workspace_mode == 'web':
            self.web_workspace = WebWorkspaceWidget(self)
            main_layout.addWidget(self.web_workspace)
        elif self.workspace_mode == 'os':
            self.os_workspace = OSWorkspaceWidget(self)
            main_layout.addWidget(self.os_workspace)
        elif self.workspace_mode == 'network':
            self.network_workspace = NetworkWorkspaceWidget(self)
            main_layout.addWidget(self.network_workspace)
        else:
            splitter = QSplitter(Qt.Orientation.Horizontal)

            # Toolbox
            category_enum = self.map_category_to_enum(self.category)
            self.toolbox = SandboxToolbox(self.sandbox_manager, category_enum)
        
            if self.category:
                category_enum = self.map_category_to_enum(self.category)
                self.toolbox.update_category(category_enum)

            splitter.addWidget(self.toolbox)
            
            # Canvas
            self.canvas_widget = SandboxCanvasWidget(self.sandbox_manager)
            splitter.addWidget(self.canvas_widget)
            
            # Detail panel
            self.detail_panel = SandboxDetailPanel(self)
            splitter.addWidget(self.detail_panel)
            
            splitter.setSizes([280, 600, 350])
            main_layout.addWidget(splitter)

        self.create_menu_bar()
        self.create_toolbar()
        self.setStatusBar(QStatusBar())
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Sandbox', self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_sandbox)
        file_menu.addAction(new_action)
        
        open_action = QAction('Open Sandbox...', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_sandbox)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save Sandbox', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_sandbox)
        file_menu.addAction(save_action)
        
        save_as_action = QAction('Save Sandbox As...', self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_sandbox_as)
        file_menu.addAction(save_as_action)

        open_folder_label = 'Open Project Folder...' if self.workspace_mode == 'web' else 'Import Project Folder...'
        self.open_folder_action = QAction(open_folder_label, self)
        self.open_folder_action.triggered.connect(self.import_project_folder)
        file_menu.addAction(self.open_folder_action)
        
        file_menu.addSeparator()

        self.undo_action = QAction('Undo', self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo)
        self.undo_action.setEnabled(False)
        file_menu.addAction(self.undo_action)
        
        self.redo_action = QAction('Redo', self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.redo)
        self.redo_action.setEnabled(False)
        file_menu.addAction(self.redo_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu('Export')
        
        export_png_action = QAction('PNG Image', self)
        export_png_action.triggered.connect(self.export_png)
        export_menu.addAction(export_png_action)
        
        export_json_action = QAction('JSON Data', self)
        export_json_action.triggered.connect(self.export_json)
        export_menu.addAction(export_json_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        theme_menu = view_menu.addMenu('Theme')
        
        cyber_theme_action = QAction('Cyber Modern', self)
        cyber_theme_action.triggered.connect(lambda: self.apply_theme('cyber_modern'))
        theme_menu.addAction(cyber_theme_action)
        
        hacker_theme_action = QAction('Hacker Dark', self)
        hacker_theme_action.triggered.connect(lambda: self.apply_theme('hacker_dark'))
        theme_menu.addAction(hacker_theme_action)
        
        # Object menu
        self.object_menu = menubar.addMenu('Object')
        
        arrange_menu = self.object_menu.addMenu('Arrange')
        
        group_action = QAction('Group Selected', self)
        group_action.triggered.connect(self.group_selected_objects)
        arrange_menu.addAction(group_action)
        
        ungroup_action = QAction('Ungroup Selected', self)
        ungroup_action.triggered.connect(self.ungroup_selected_objects)
        arrange_menu.addAction(ungroup_action)
        
        self.object_menu.addSeparator()
        
        align_menu = self.object_menu.addMenu('Align')
        
        align_left_action = QAction('Align Left', self)
        align_left_action.triggered.connect(lambda: self.align_objects('left'))
        align_menu.addAction(align_left_action)
        
        align_center_action = QAction('Align Center', self)
        align_center_action.triggered.connect(lambda: self.align_objects('center'))
        align_menu.addAction(align_center_action)
        
        align_right_action = QAction('Align Right', self)
        align_right_action.triggered.connect(lambda: self.align_objects('right'))
        align_menu.addAction(align_right_action)
        self.object_menu.menuAction().setVisible(self.is_canvas_mode())

        self.analyse_menu = menubar.addMenu('Analyse My System')
        self.analyse_menu.setVisible(False)

        full_analysis_action = QAction('Full System Analysis', self)
        full_analysis_action.triggered.connect(self.perform_full_system_analysis)
        self.analyse_menu.addAction(full_analysis_action)
        
        network_analysis_action = QAction('Network Analysis Only', self)
        network_analysis_action.triggered.connect(self.perform_network_analysis)
        self.analyse_menu.addAction(network_analysis_action)
        
        security_analysis_action = QAction('Security Analysis Only', self)
        security_analysis_action.triggered.connect(self.perform_security_analysis)
        self.analyse_menu.addAction(security_analysis_action)
        
        processes_analysis_action = QAction('Processes & Services Analysis', self)
        processes_analysis_action.triggered.connect(self.perform_processes_analysis)
        self.analyse_menu.addAction(processes_analysis_action)
        
        # Docker menu
        self.docker_menu = menubar.addMenu('Docker')
        self.docker_menu.setVisible(False)
        
        up_docker_action = QAction('Up Project in Env', self)
        up_docker_action.triggered.connect(self.show_docker_automation)
        self.docker_menu.addAction(up_docker_action)

        print(f"DEBUG AFTER CREATION: analyse_menu = {self.analyse_menu}")
        print(f"DEBUG AFTER CREATION: docker_menu = {self.docker_menu}")
    
    def create_toolbar(self):
        self.toolbar = QToolBar("Sandbox Toolbar")
        self.addToolBar(self.toolbar)
        
        new_action = QAction('New', self)
        new_action.triggered.connect(self.new_sandbox)
        self.toolbar.addAction(new_action)
        
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_sandbox)
        self.toolbar.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save_sandbox)
        self.toolbar.addAction(save_action)
        
        if self.workspace_mode == 'web':
            open_folder_action = QAction('Open Folder', self)
            open_folder_action.triggered.connect(self.import_project_folder)
            self.toolbar.addAction(open_folder_action)
        
        self.toolbar.addSeparator()

        undo_toolbar_action = QAction('Undo', self)
        undo_toolbar_action.triggered.connect(self.undo)
        undo_toolbar_action.setEnabled(False)
        self.toolbar.addAction(undo_toolbar_action)
        
        redo_toolbar_action = QAction('Redo', self)
        redo_toolbar_action.triggered.connect(self.redo)
        redo_toolbar_action.setEnabled(False)
        self.toolbar.addAction(redo_toolbar_action)
        
        self.toolbar.addSeparator()
        
        zoom_in_action = QAction('Zoom In', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        self.toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        self.toolbar.addAction(zoom_out_action)
        
        reset_zoom_action = QAction('Reset Zoom', self)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        self.toolbar.addAction(reset_zoom_action)

    def add_attack_button(self):
        for action in self.toolbar.actions():
            if action.text() == 'Start Attack':
                return
        
        attack_action = QAction('Start Attack', self)
        attack_action.triggered.connect(self.launch_security_attack)
        
        self.toolbar.addAction(attack_action)

        self.docker_menu.addAction(attack_action)
        
        print("Botão 'Start Attack' adicionado com sucesso!")

    def launch_security_attack(self):
        from features.tools.agents.attack_dialog import AttackDialog

        if not self.is_docker_environment_running():
            QMessageBox.warning(self, "Aviso", 
                            "O ambiente Docker precisa estar em execução!\n\n"
                            "Use 'Up Project in Env' primeiro.")
            return
        
        attack_dialog = AttackDialog("http://localhost:5000", self)
        attack_dialog.exec()

    def is_docker_environment_running(self):
        try:
            import subprocess
            result = subprocess.run(["docker", "compose", "ps"], 
                                capture_output=True, text=True)
            return "Up" in result.stdout
        except:
            return False

    def show_docker_automation(self):
        sandbox_data = self._get_sandbox_data_for_docker()
        if not sandbox_data or not sandbox_data.get('objects'):
            QMessageBox.warning(self, "Aviso", 
                            "Nenhum sandbox carregado ou vazio.\n\n"
                            "Por favor, carregue um sandbox com uma aplicação web primeiro.")
            return
        
        print(f"Sandbox carregado com {len(sandbox_data.get('objects', []))} objetos")
        
        from features.tools.docker.docker_automation import DockerAutomationDialog
        dialog = DockerAutomationDialog(sandbox_data, self)
        dialog.exec()
    
    def on_docker_success(self, message):
        self.add_attack_button()
        
        self.statusBar().showMessage("Ambiente Docker pronto - Botão de ataque adicionado!")
        
        QMessageBox.information(self, "Docker Pronto", 
                            "Ambiente Docker iniciado com sucesso!\n\n"
                            "O botão 'Start Attack' foi adicionado à toolbar.\n"
                            "Você pode agora iniciar os testes de segurança.")

    def update_menu_visibility(self):
        print(f"DEBUG: Current category = {self.category}")
        self.refresh_workspace_mode()
        if self.object_menu:
            self.object_menu.menuAction().setVisible(self.is_canvas_mode())
        if hasattr(self, 'open_folder_action') and self.open_folder_action:
            self.open_folder_action.setVisible(self.workspace_mode in {'web', 'legacy'})
            self.open_folder_action.setText(
                'Open Project Folder...' if self.workspace_mode == 'web' else 'Import Project Folder...'
            )
        
        if self.workspace_mode == 'os':
            print("DEBUG: Operating System category - Showing Analyse, Hiding Docker")
            self.analyse_menu.menuAction().setVisible(True)
            self.docker_menu.menuAction().setVisible(False)
        elif self.workspace_mode == 'web':
            print("DEBUG: Web Technology category - Hiding Analyse, Showing Docker")
            self.analyse_menu.menuAction().setVisible(False)
            self.docker_menu.menuAction().setVisible(True)
        else:
            print("DEBUG: Other category - Hiding both menus")
            self.analyse_menu.menuAction().setVisible(False)
            self.docker_menu.menuAction().setVisible(False)

        self.menuBar().adjustSize()

    def force_menu_update(self):
        print("FORCE UPDATING MENUS")
        self.update_menu_visibility()

    def update_category(self, new_category):
        self.category = new_category
        self.update_menu_visibility()

    def _get_sandbox_data_for_docker(self):
        try:
            environment = self.sandbox_manager.environment
            sandbox_data = {
                'metadata': environment.metadata,
                'objects': [obj.to_dict() for obj in environment.objects.values()]
            }
            return sandbox_data
        except:
            return None

    def map_category_to_enum(self, category_str):
        mapping = {
            'operating_systems': ObjectCategory.OPERATING_SYSTEM,
            'network_devices': ObjectCategory.NETWORK,
            'web_technologies': ObjectCategory.WEB,
            'organization': ObjectCategory.ORGANIZATION,
            'network_topology': ObjectCategory.NETWORK,
            'web_architecture': ObjectCategory.WEB,
            'operative_system': ObjectCategory.OPERATING_SYSTEM
        }
        return mapping.get(category_str, None)

    def setup_connections(self):
        active_workspace = self.get_active_workspace()
        if active_workspace and hasattr(active_workspace, 'status_message'):
            active_workspace.status_message.connect(self.statusBar().showMessage)

        if self.workspace_mode == 'web' and self.web_workspace:
            self.web_workspace.folder_loaded.connect(
                lambda path: self.statusBar().showMessage(f"Opened project folder: {path}")
            )
            self.web_workspace.file_opened.connect(
                lambda path: self.statusBar().showMessage(f"Opened file: {os.path.basename(path)}")
            )
            return
        if self.workspace_mode in {'os', 'network'}:
            return

        self.toolbox.object_created.connect(self.create_object)
        self.canvas_widget.object_created.connect(self.create_object_visual)
        self.canvas_widget.connection_requested.connect(self.create_connection)
        self.canvas_widget.parent_child_requested.connect(self.set_parent_child)
        
        self.detail_panel.object_data_updated.connect(self.on_object_updated)
        self.detail_panel.object_deleted.connect(self.on_object_deleted)
        if hasattr(self.toolbox, 'import_project'):
            self.toolbox.import_project.connect(self.import_project_folder)

    def create_object(self, obj_type, obj_name=None):
        from PyQt6.QtCore import QPointF
        from models.object_model import ObjectType
        
        view_center = self.canvas_widget.mapToScene(
            self.canvas_widget.viewport().rect().center()
        )

        try:
            if isinstance(obj_type, str):
                obj_type = ObjectType(obj_type)
            
            obj = self.sandbox_manager.add_object(obj_type, view_center, obj_name)
            self.create_object_visual(obj)
            
            self.statusBar().showMessage(f"Created {obj_type.value} object")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create object: {e}")

    def create_object_visual(self, obj):
        from ui.sandbox.sandbox_object_widget import SandboxObjectWidget
        
        obj_widget = SandboxObjectWidget(obj)
        self.canvas_widget.add_object_widget(obj_widget)
        
        obj_widget.object_updated.connect(self.on_object_selected)
        obj_widget.connection_started.connect(self.start_connection)
        obj_widget.parent_child_started.connect(self.start_parent_child)
        obj_widget.object_deleted.connect(self.on_object_deleted)
        
        self.object_widgets[obj.id] = obj_widget
        
        self.statusBar().showMessage(f"Created {obj.object_type.value} object visual")

    def on_object_selected(self, obj):
        self.detail_panel.display_object(obj)
        self.statusBar().showMessage(f"Selected {obj.object_type.value} object: {obj.name}")

    def on_object_updated(self, obj):
        if obj.id in self.object_widgets:
            self.object_widgets[obj.id].update_display()
        
        self.sandbox_manager.save_state(f"Update {obj.object_type.value} object")
        self.update_undo_redo_buttons()
        
        self.statusBar().showMessage(f"Updated {obj.object_type.value} object")

    def _remove_object_connections_visual(self, obj_id: str):
        connections_to_remove = []
        
        for connection_id, connection_item in self.canvas_widget.connection_items.items():
            if obj_id in connection_id:
                connections_to_remove.append(connection_id)
        
        for connection_id in connections_to_remove:
            self.canvas_widget.remove_connection_item(connection_id)

    def clear_all_connections(self):
        for connection_id in list(self.connection_items.keys()):
            self.remove_connection_item(connection_id)

    def start_connection(self, source_widget):
        self.connection_source = source_widget
        self.statusBar().showMessage("Connection mode: Click target object or ESC to cancel")

    def start_parent_child(self, parent_widget):
        self.parent_child_source = parent_widget
        self.statusBar().showMessage("Parent-Child mode: Click child object or ESC to cancel")

    def create_connection(self, source_id, target_id):
        try:
            connection_id = self.sandbox_manager.add_connection(source_id, target_id)
            self.canvas_widget.draw_connection(source_id, target_id, connection_id)
            
            self.update_undo_redo_buttons()
            self.statusBar().showMessage(f"Connected {source_id} to {target_id}")
        except Exception as e:
            self.statusBar().showMessage(f"Connection failed: {e}")

    def set_parent_child(self, parent_id, child_id):
        try:
            self.sandbox_manager.set_parent(child_id, parent_id)
            
            if parent_id in self.object_widgets and child_id in self.object_widgets:
                parent_widget = self.object_widgets[parent_id]
                child_widget = self.object_widgets[child_id]
                self.canvas_widget.update_parent_child_visual(parent_widget, child_widget)
            
            self.update_undo_redo_buttons()
            self.statusBar().showMessage(f"Set {child_id} as child of {parent_id}")
        except Exception as e:
            self.statusBar().showMessage(f"Parent-child relationship failed: {e}")

    def undo(self):
        if not self.is_canvas_mode():
            self.statusBar().showMessage("Undo is not available in this workspace mode.")
            return
        if self.sandbox_manager.undo():
            self.refresh_canvas_from_environment()
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Undo: " + self.sandbox_manager.history[self.sandbox_manager.history_position]['description'])
    
    def redo(self):
        if not self.is_canvas_mode():
            self.statusBar().showMessage("Redo is not available in this workspace mode.")
            return
        if self.sandbox_manager.redo():
            self.refresh_canvas_from_environment()
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Redo: " + self.sandbox_manager.history[self.sandbox_manager.history_position]['description'])
    
    def update_undo_redo_buttons(self):
        if not self.is_canvas_mode():
            if hasattr(self, 'undo_action'):
                self.undo_action.setEnabled(False)
            if hasattr(self, 'redo_action'):
                self.redo_action.setEnabled(False)
            return

        self.undo_action.setEnabled(self.sandbox_manager.can_undo())
        self.redo_action.setEnabled(self.sandbox_manager.can_redo())
        
        for action in self.findChildren(QAction):
            if action.text() == 'Undo':
                action.setEnabled(self.sandbox_manager.can_undo())
            elif action.text() == 'Redo':
                action.setEnabled(self.sandbox_manager.can_redo())

    def refresh_canvas_from_environment(self):
        if not self.is_canvas_mode() or not self.canvas_widget:
            return
        self.canvas_widget.scene.clear()
        self.object_widgets.clear()
        self.canvas_widget.connection_items.clear()

        for obj in self.sandbox_manager.environment.objects.values():
            self.create_object_visual(obj)
        
        for connection in self.sandbox_manager.environment.connections.values():
            self.canvas_widget.draw_connection(
                connection.source_id, 
                connection.target_id, 
                connection.id
            )
        
        if (self.detail_panel.current_object and 
            self.detail_panel.current_object.id not in self.sandbox_manager.environment.objects):
            self.detail_panel.clear_panel()

    def on_object_deleted(self, obj):
        reply = QMessageBox.question(self, 'Delete Object', 
                                f'Are you sure you want to delete this {obj.object_type.value} object?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas_widget.remove_connections_for_object(obj.id)
            
            self.sandbox_manager.remove_object(obj.id)

            if obj.id in self.object_widgets:
                obj_widget = self.object_widgets[obj.id]
                self.canvas_widget.scene.removeItem(obj_widget)
                del self.object_widgets[obj.id]
            
            if self.detail_panel.current_object and self.detail_panel.current_object.id == obj.id:
                self.detail_panel.clear_panel()
            
            self.update_undo_redo_buttons()
            
            self.statusBar().showMessage(f"Deleted {obj.object_type.value} object")

    def import_project_folder(self):
        if self.workspace_mode == 'web' and self.web_workspace:
            folder_path = self.web_workspace.open_project_folder_dialog()
            if folder_path:
                self.statusBar().showMessage(f"Project folder loaded: {os.path.basename(folder_path)}")
            return
        if not self.is_canvas_mode():
            QMessageBox.information(
                self,
                "Not Available",
                "Folder import is only available for the Web workspace or legacy canvas mode.",
            )
            return

        folder_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Project Folder to Import",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder_path:
            try:
                from PyQt6.QtCore import QPointF
                view_center = self.canvas_widget.mapToScene(
                    self.canvas_widget.viewport().rect().center()
                )
                
                project_obj = self.sandbox_manager.add_object(
                    ObjectType.PROJECT, 
                    view_center, 
                    os.path.basename(folder_path)
                )
                
                self.process_project_structure(folder_path, project_obj.id, view_center)
                
                self.statusBar().showMessage(f"Project imported: {os.path.basename(folder_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import project: {e}")

    def process_project_structure(self, folder_path, parent_id, base_position, depth=0):
        try:
            x_offset = 120
            y_offset = 100
            current_y = base_position.y() + (depth * y_offset)

            items = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if not item.startswith('.'):
                    items.append((item, item_path, os.path.isdir(item_path)))
            
            if not items:
                return

            items.sort(key=lambda x: (not x[2], x[0].lower()))
            
            for i, (item, item_path, is_dir) in enumerate(items):
                x_pos = base_position.x() + (i * x_offset)
                position = QPointF(x_pos, current_y)
                
                if is_dir:
                    folder_obj = self.sandbox_manager.add_object(
                        ObjectType.WEB_FOLDER,
                        position,
                        f"{item}"
                    )
                    self.create_object_visual(folder_obj)
                    
                    parent_obj = self.sandbox_manager.environment.objects.get(parent_id)
                    if parent_obj and SandboxObjectFactory.can_have_children(parent_obj.object_type):
                        try:
                            self.sandbox_manager.set_parent(folder_obj.id, parent_id)
                            print(f"Created folder: {item} as child of {parent_obj.name}")
                        except Exception as e:
                            print(f"Warning: Could not set parent for folder {item}: {e}")
                    else:
                        print(f"Warning: Parent {parent_obj.name if parent_obj else 'Unknown'} cannot have children")
                    
                    self.process_project_structure(item_path, folder_obj.id, position, depth + 1)
                    
                else:
                    obj_type = self.determine_file_type(item)
                    
                    parent_obj = self.sandbox_manager.environment.objects.get(parent_id)
                    if parent_obj and obj_type in SandboxObjectFactory.get_allowed_children(parent_obj.object_type):

                        file_obj = self.sandbox_manager.add_object(
                            obj_type,
                            position,
                            f"{item}"
                        )
                        
                        self.create_object_visual(file_obj)
                        
                        if obj_type in [ObjectType.CODE_FILE, ObjectType.CONFIG_FILE]:
                            self.load_file_content(file_obj, item_path)
                        
                        try:
                            self.sandbox_manager.set_parent(file_obj.id, parent_id)
                            print(f"Created file: {item} as child of {parent_obj.name}")
                        except Exception as e:
                            print(f"Warning: Could not set parent for file {item}: {e}")
                    else:
                        print(f"Warning: Cannot add {item} as child of {parent_obj.name if parent_obj else 'Unknown'}")
                    
        except Exception as e:
            print(f"Error processing project structure: {e}")
            import traceback
            traceback.print_exc()
        
    def can_add_as_child(self, parent_obj, child_type):
        if not parent_obj:
            return False
        
        allowed_children = SandboxObjectFactory.get_allowed_children(parent_obj.object_type)
        return child_type in allowed_children

    def determine_file_type(self, filename):
        extension = os.path.splitext(filename)[1].lower()
        
        file_type_mapping = {
            '.js': ObjectType.CODE_FILE,
            '.py': ObjectType.CODE_FILE,
            '.java': ObjectType.CODE_FILE,
            '.rb': ObjectType.CODE_FILE,
            '.php': ObjectType.CODE_FILE,
            '.html': ObjectType.CODE_FILE,
            '.css': ObjectType.CODE_FILE,
            '.ts': ObjectType.CODE_FILE,
            '.jsx': ObjectType.CODE_FILE,
            '.tsx': ObjectType.CODE_FILE,
            
            '.json': ObjectType.CONFIG_FILE,
            '.xml': ObjectType.CONFIG_FILE,
            '.yaml': ObjectType.CONFIG_FILE,
            '.yml': ObjectType.CONFIG_FILE,
            '.config': ObjectType.CONFIG_FILE,
            '.conf': ObjectType.CONFIG_FILE,
            '.ini': ObjectType.CONFIG_FILE,
            '.env': ObjectType.CONFIG_FILE,
            '.properties': ObjectType.CONFIG_FILE,
            '.toml': ObjectType.CONFIG_FILE,
        }
        
        return file_type_mapping.get(extension, ObjectType.FILE)

    def load_file_content(self, file_obj, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            extension = os.path.splitext(file_path)[1].lower()
            language_map = {
                '.js': 'JavaScript',
                '.py': 'Python',
                '.java': 'Java',
                '.rb': 'Ruby',
                '.php': 'PHP',
                '.html': 'HTML',
                '.css': 'CSS',
                '.ts': 'TypeScript',
                '.jsx': 'JSX',
                '.tsx': 'TSX',
                
                '.json': 'JSON',
                '.xml': 'XML',
                '.yaml': 'YAML',
                '.yml': 'YAML',
                '.config': 'XML',
                '.conf': 'Text',
                '.ini': 'INI',
                '.env': 'Text',
                '.properties': 'Properties',
                '.toml': 'TOML'
            }
            
            language = language_map.get(extension, 'Text')
            
            file_obj.set_code_content(
                language=language,
                source_code=content,
                dependencies=[],
                environment_vars={}
            )
            
            print(f"Loaded content for {file_obj.name} ({language}): {len(content)} characters")
            
        except Exception as e:
            print(f"Error loading file content for {file_path}: {e}")
            import traceback
            traceback.print_exc()

    def new_sandbox(self):
        if self.has_unsaved_changes():
            reply = QMessageBox.question(self, 'New Sandbox', 
                                    'You have unsaved changes. Are you sure you want to start a new sandbox?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        from ui.sandbox.sandbox_category_dialog import SandboxCategoryDialog
        category_dialog = SandboxCategoryDialog(self)
        
        if category_dialog.exec() == QDialog.DialogCode.Accepted:
            selected_category = category_dialog.selected_category
            selected_mode = self.get_workspace_mode(selected_category)

            if selected_mode != self.workspace_mode:
                replacement_window = SandboxMainWindow(self.project_type, selected_category, self.template_data)
                replacement_window.show()
                self._skip_close_confirmation = True
                self.close()
                return
            
            self.category = selected_category
            self.update_menu_visibility()

            active_workspace = self.get_active_workspace()
            if active_workspace:
                if hasattr(active_workspace, 'reset_workspace'):
                    active_workspace.reset_workspace()
                self.storage_manager.current_file = None
                self.statusBar().showMessage(f"New {selected_category.replace('_', ' ')} workspace ready.")
                return

            self.sandbox_manager.clear_environment()
            self.canvas_widget.scene.clear()
            self.object_widgets.clear()
            self.detail_panel.clear_panel()

            if selected_category != 'all_categories':
                category_enum = self.map_category_to_enum(selected_category)
                self.toolbox.update_category(category_enum)
            else:
                self.toolbox.update_category(None)
            
            self.statusBar().showMessage(f"New {selected_category.replace('_', ' ')} sandbox created")

    def start_connection(self, source_widget):
        if not self.is_canvas_mode() or not self.canvas_widget:
            return
        self.canvas_widget.start_connection(source_widget)

    def start_parent_child(self, parent_widget):
        if not self.is_canvas_mode() or not self.canvas_widget:
            return
        self.canvas_widget.start_parent_child(parent_widget)

    def create_connection(self, source_id, target_id):
        try:
            print(f"DEBUG: Creating connection in manager: {source_id} -> {target_id}")
            connection_id = self.sandbox_manager.add_connection(source_id, target_id)
            
            if connection_id:
                print(f"DEBUG: Connection created with ID: {connection_id}")
                connection = self.sandbox_manager.environment.connections.get(connection_id)
                if connection:
                    self.canvas_widget.draw_connection(
                        connection.source_id, 
                        connection.target_id, 
                        connection.id
                    )
                else:
                    print(f"DEBUG ERROR: Connection not found in environment: {connection_id}")
                
                self.update_undo_redo_buttons()
                self.statusBar().showMessage(f"Connected {source_id} to {target_id}")
            else:
                print(f"DEBUG ERROR: Connection ID is None")
                self.statusBar().showMessage(f"Connection failed: {source_id} to {target_id}")
                
        except Exception as e:
            print(f"DEBUG: Connection failed with exception: {e}")
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"Connection failed: {e}")

    def set_parent_child(self, parent_id, child_id):
        try:
            self.sandbox_manager.set_parent(child_id, parent_id)
            
            if parent_id in self.object_widgets and child_id in self.object_widgets:
                parent_widget = self.object_widgets[parent_id]
                child_widget = self.object_widgets[child_id]
                self.canvas_widget.update_parent_child_visual(parent_widget, child_widget)
            
            self.update_undo_redo_buttons()
            self.statusBar().showMessage(f"Set {child_id} as child of {parent_id}")
        except Exception as e:
            self.statusBar().showMessage(f"Parent-child relationship failed: {e}")

    def has_unsaved_changes(self):
        active_workspace = self.get_active_workspace()
        if active_workspace and hasattr(active_workspace, 'has_unsaved_changes'):
            return active_workspace.has_unsaved_changes()
        return len(self.sandbox_manager.environment.objects) > 0

    def save_sandbox(self):
        if self.workspace_mode == 'web' and self.web_workspace:
            if not self.web_workspace.current_file_path:
                QMessageBox.information(
                    self,
                    "No File Opened",
                    "Open a file in the editor before saving.",
                )
                return
            self.web_workspace.save_current_file()
            self.statusBar().showMessage(f"Saved file: {os.path.basename(self.web_workspace.current_file_path)}")
            return

        if self.storage_manager.current_file:
            success = self.save_environment_to_file(self.storage_manager.current_file)
            if success:
                self.statusBar().showMessage("Sandbox saved")
            else:
                self.statusBar().showMessage("Save failed")
        else:
            self.save_sandbox_as()

    def save_sandbox_as(self):
        if self.workspace_mode == 'web':
            QMessageBox.information(
                self,
                "Save As Not Available",
                "Use the editor Save button to persist the current file.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Save Sandbox', '', 
            'BeatRooter Sandbox Files (*.brs);;JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            if not filename.endswith('.brs') and not filename.endswith('.json'):
                filename += '.brs'
            
            success = self.save_environment_to_file(filename)
            if success:
                self.storage_manager.current_file = filename
                self.statusBar().showMessage(f"Sandbox saved as: {filename}")
            else:
                self.statusBar().showMessage("Save failed")

    def save_environment_to_file(self, filename):
        try:
            import json
            from datetime import datetime
            
            if self.is_canvas_mode():
                self.sandbox_manager.environment.metadata['modified'] = datetime.now().isoformat()
                if not self.sandbox_manager.environment.metadata.get('created'):
                    self.sandbox_manager.environment.metadata['created'] = datetime.now().isoformat()
                
                if self.category:
                    self.sandbox_manager.environment.metadata['category'] = self.category
                
                data = self.sandbox_manager.environment.to_dict()

                print(f"DEBUG: Saving to {filename}")
                print(f"DEBUG - Objects to save: {len(data.get('objects', []))}")
                print(f"DEBUG - Connections to save: {len(data.get('connections', []))}")
            else:
                active_workspace = self.get_active_workspace()
                if not active_workspace or not hasattr(active_workspace, 'to_dict'):
                    raise ValueError("Current workspace does not support serialization")

                data = {
                    'metadata': {
                        'created': datetime.now().isoformat(),
                        'modified': datetime.now().isoformat(),
                        'category': self.category,
                        'workspace_mode': self.workspace_mode,
                    },
                    'workspace_state': active_workspace.to_dict(),
                }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"DEBUG: File saved successfully")
            return True
            
        except Exception as e:
            print(f"DEBUG: Save error: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save sandbox: {e}")
            return False
        
    def refresh_menu_visibility(self):
        self.update_menu_visibility()

    def open_sandbox(self):
        if self.workspace_mode == 'web':
            self.import_project_folder()
            return

        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open Sandbox', '', 
            'BeatRooter Sandbox Files (*.brs);;JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            try:
                self.load_environment_from_file(filename)
                self.statusBar().showMessage(f"Opened sandbox: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def load_environment_from_file(self, filename):
        try:
            import json

            print(f"DEBUG: Loading from {filename}")

            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.load_data_bundle(data, filename)
            print(f"DEBUG: Environment loaded successfully")

        except Exception as e:
            print(f"DEBUG: Load error: {e}")
            raise Exception(f"Failed to load environment: {e}")

    def load_data_bundle(self, data, filename=None):
        metadata = data.get('metadata', {}) if isinstance(data, dict) else {}
        loaded_category = metadata.get('category', self.category)
        loaded_mode = self.get_workspace_mode(loaded_category)

        if loaded_mode != self.workspace_mode:
            replacement_window = SandboxMainWindow(self.project_type, loaded_category, self.template_data)
            replacement_window.show()
            replacement_window.load_data_bundle(data, filename)
            self._skip_close_confirmation = True
            self.close()
            return

        self.category = loaded_category
        self.update_menu_visibility()
        self.storage_manager.current_file = filename

        if not self.is_canvas_mode():
            active_workspace = self.get_active_workspace()
            workspace_state = data.get('workspace_state', {})

            if workspace_state and active_workspace and hasattr(active_workspace, 'load_state'):
                active_workspace.load_state(workspace_state)
                return

            if data.get('objects'):
                from models.object_model import SandboxEnvironment

                environment = SandboxEnvironment.from_dict(data)
                if self.workspace_mode == 'os' and self.os_workspace:
                    self.os_workspace.load_analysis_results(list(environment.objects.values()))
                    return
                if self.workspace_mode == 'network' and self.network_workspace:
                    self.network_workspace.load_legacy_topology(
                        list(environment.objects.values()),
                        list(environment.connections.values()),
                    )
                    return
            return

        print(f"DEBUG: File loaded - Objects: {len(data.get('objects', []))}, Connections: {len(data.get('connections', []))}")

        from models.object_model import SandboxEnvironment
        environment = SandboxEnvironment.from_dict(data)

        self.sandbox_manager.environment = environment
        self.refresh_canvas_from_environment()

    def export_png(self):
        if not self.is_canvas_mode():
            QMessageBox.information(
                self,
                "Export Not Available",
                "PNG export is only available in legacy object/canvas mode.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export as PNG', '', 'PNG Images (*.png)'
        )
        
        if filename:
            success = self.storage_manager.export_png(
                None,
                filename,
                self.canvas_widget.scene
            )
            if success:
                self.statusBar().showMessage(f"Exported PNG: {filename}")
            else:
                self.statusBar().showMessage("PNG export failed")

    def export_json(self):
        if self.workspace_mode == 'web':
            QMessageBox.information(
                self,
                "Export Not Available",
                "JSON export is not available in the Web workspace.",
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export as JSON', '', 'JSON Files (*.json)'
        )
        
        if filename:
            success = self.save_environment_to_file(filename)
            if success:
                self.statusBar().showMessage(f"Exported JSON: {filename}")
            else:
                self.statusBar().showMessage("JSON export failed")

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        style_sheet = ThemeManager.get_theme(theme_name)
        self.setStyleSheet(style_sheet)
        self.statusBar().showMessage(f"Applied {theme_name} theme")

    def zoom_in(self):
        active_workspace = self.get_active_workspace()
        if active_workspace and hasattr(active_workspace, 'zoom_in'):
            active_workspace.zoom_in()
            return
        if self.canvas_widget:
            self.canvas_widget.scale(1.2, 1.2)
    
    def zoom_out(self):
        active_workspace = self.get_active_workspace()
        if active_workspace and hasattr(active_workspace, 'zoom_out'):
            active_workspace.zoom_out()
            return
        if self.canvas_widget:
            self.canvas_widget.scale(0.8, 0.8)
    
    def reset_zoom(self):
        active_workspace = self.get_active_workspace()
        if active_workspace and hasattr(active_workspace, 'reset_zoom'):
            active_workspace.reset_zoom()
            return
        if self.canvas_widget:
            self.canvas_widget.resetTransform()

    def group_selected_objects(self):
        if not self.is_canvas_mode() or not self.canvas_widget:
            return
        selected_objects = [item for item in self.canvas_widget.scene.selectedItems() 
                          if hasattr(item, 'object')]
        
        if len(selected_objects) < 2:
            QMessageBox.information(self, "Group Objects", "Please select at least 2 objects to group")
            return
        
        self.statusBar().showMessage(f"Grouped {len(selected_objects)} objects")

    def ungroup_selected_objects(self):
        if not self.is_canvas_mode() or not self.canvas_widget:
            return
        selected_objects = [item for item in self.canvas_widget.scene.selectedItems() 
                          if hasattr(item, 'object')]
        
        if not selected_objects:
            QMessageBox.information(self, "Ungroup Objects", "Please select a group to ungroup")
            return
        
        self.statusBar().showMessage("Ungrouped objects")

    def align_objects(self, alignment):
        if not self.is_canvas_mode() or not self.canvas_widget:
            return
        selected_objects = [item for item in self.canvas_widget.scene.selectedItems() 
                          if hasattr(item, 'object')]
        
        if len(selected_objects) < 2:
            QMessageBox.information(self, "Align Objects", "Please select at least 2 objects to align")
            return
        
        self.statusBar().showMessage(f"Aligned objects to {alignment}")

    def perform_full_system_analysis(self):
        reply = QMessageBox.question(
            self, 
            "System Analysis", 
            "This will analyze your system and create a detailed map of your operating system components.\n\n"
            "The analysis may take a few minutes and will collect information about:\n"
            "- System hardware and configuration\n"
            "- Network interfaces and open ports\n"
            "- Running services and processes\n"
            "- Installed software\n"
            "- User accounts and security policies\n\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.start_system_analysis("full")

    def start_system_analysis(self, analysis_type):
        from features.tools.parsers.system_analyzer import SystemAnalysisThread
        
        self.progress_dialog = QProgressDialog("Analyzing system...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("System Analysis")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()
        
        self.analysis_thread = SystemAnalysisThread(analysis_type)
        self.analysis_thread.progress_updated.connect(self.update_analysis_progress)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.start()
        
        self.progress_dialog.canceled.connect(self.analysis_thread.terminate)

    def perform_network_analysis(self):
        self.start_system_analysis("network")

    def perform_security_analysis(self):
        self.start_system_analysis("security")

    def perform_processes_analysis(self):
        self.start_system_analysis("processes")

    def update_analysis_progress(self, value, message):
        self.progress_dialog.setValue(value)
        self.progress_dialog.setLabelText(message)

    def on_analysis_complete(self, objects_to_create):
        self.progress_dialog.close()
        
        if not objects_to_create:
            QMessageBox.information(self, "Analysis Complete", 
                                "System analysis completed but no components were found.\n\n"
                                "This could be due to system permissions or the analysis type selected.")
            return
        
        print(f"DEBUG: Analysis found {len(objects_to_create)} objects")
        
        from features.tools.parsers.system_analyzer_filters import SystemAnalysisFilter
        filtered_objects = SystemAnalysisFilter.filter_essential_components(objects_to_create, max_objects=25)
        
        print(f"DEBUG: After filtering: {len(filtered_objects)} objects")

        if self.workspace_mode == 'os' and self.os_workspace:
            self.os_workspace.load_analysis_results(filtered_objects)
            QMessageBox.information(
                self,
                "Analysis Complete",
                "System analysis completed successfully.\n\n"
                f"Imported {len(filtered_objects)} essential components into the OS VM Lab.\n\n"
                "You can now refine services, snapshots, and filesystem artifacts inside the new workspace.",
            )
            return

        categorized_objects = self.categorize_objects_for_display(filtered_objects)
        
        total_created = 0
        for category, objects in categorized_objects.items():
            created_count = self.create_objects_in_category(category, objects)
            total_created += created_count

        category_breakdown = "\n".join([f"- {cat}: {len(objs)}" for cat, objs in categorized_objects.items() if objs])
        
        QMessageBox.information(
            self, 
            "Analysis Complete", 
            f"System analysis completed successfully!\n\n"
            f"Created {total_created} essential system components.\n\n"
            f"Breakdown by category:\n{category_breakdown}\n\n"
            f"The analysis focused on the most relevant components for your system."
        )

    def categorize_objects_for_display(self, objects):
        categories = {
            'core_system': [],
            'network': [],
            'security': [],
            'services': [],
            'users': [],
            'files': []
        }
        
        for obj in objects:
            obj_type = obj.object_type.value if hasattr(obj.object_type, 'value') else str(obj.object_type)
            
            if obj_type in ['OPERATING_SYSTEM', 'KERNEL']:
                categories['core_system'].append(obj)
            elif any(net_key in obj_type.lower() for net_key in ['network', 'interface', 'port']):
                categories['network'].append(obj)
            elif any(sec_key in obj_type.lower() for sec_key in ['security', 'firewall', 'antivirus']):
                categories['security'].append(obj)
            elif obj_type in ['SERVICE', 'PROCESS', 'SERVER']:
                categories['services'].append(obj)
            elif obj_type in ['USER_ACCOUNT']:
                categories['users'].append(obj)
            else:
                categories['files'].append(obj)
        
        return categories

    def create_objects_in_category(self, category, objects):
        if not objects:
            return 0
        
        category_positions = {
            'core_system': (-400, -200),
            'network': (0, -200),
            'security': (400, -200),
            'services': (-400, 100),
            'users': (0, 100),
            'files': (400, 100)
        }
        
        base_x, base_y = category_positions.get(category, (0, 0))
        grid_spacing = 120
        
        created_count = 0
        for i, obj_template in enumerate(objects):
            row = i // 4
            col = i % 4
            x = base_x + (col * grid_spacing)
            y = base_y + (row * grid_spacing)
            
            try:
                obj = self.sandbox_manager.add_object(
                    obj_template.object_type,
                    QPointF(x, y),
                    obj_template.name,
                    obj_template.properties if hasattr(obj_template, 'properties') else {}
                )

                self.create_object_visual(obj)
                created_count += 1
                
            except Exception as e:
                print(f"Warning: Failed to create object {obj_template.name}: {e}")
        
        return created_count

    def closeEvent(self, event):
        if self._skip_close_confirmation:
            if self in SandboxMainWindow._window_refs:
                SandboxMainWindow._window_refs.remove(self)
            event.accept()
            return

        if self.has_unsaved_changes():
            reply = QMessageBox.question(self, 'Unsaved Changes', 
                                      'You have unsaved changes. Are you sure you want to quit?',
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

        if self in SandboxMainWindow._window_refs:
            SandboxMainWindow._window_refs.remove(self)
        event.accept()
