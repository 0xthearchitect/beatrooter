import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QToolBar, QStatusBar, QFileDialog, QMessageBox,
                             QSplitter, QApplication, QGraphicsLineItem)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QLineF, QSettings
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPen, QColor

from core.graph_manager import GraphManager
from core.storage_manager import StorageManager
from core.theme_manager import ThemeManager
from core.node_factory import NodeFactory

from ui.canvas_widget import CanvasWidget
from ui.toolbox import ToolboxWidget
from ui.detail_panel import DetailPanel
from ui.node_widget import NodeWidget
from ui.dynamic_edge import DynamicEdge
from utils.image_utils import ImageUtils
#from ai.ai_assistant import AIAssistant
from utils.path_utils import get_resource_path

class DigitalDetectiveBoard(QMainWindow):
    def __init__(self, project_type=None, category=None, template_data=None):
        super().__init__()
        self.graph_manager = GraphManager()
        self.storage_manager = StorageManager()
        self.current_theme = 'cyber_modern'
        self.node_widgets = {}
        self.edge_items = {}
        self.connection_source = None

        from tools.tools_integration import ToolsIntegration
        self.tools_integration = ToolsIntegration(self)

        self.project_type = project_type
        self.category = category
        self.template_data = template_data

        #self.ai_assistant = None
        
        self.setWindowIcon(QIcon(get_resource_path("icons/app_icon.png", 'assets')))
        self.setup_ui()
        self.apply_theme(self.current_theme)
        self.setup_connections()

        
        if category:
            self.toolbox.update_category(category)
        
        self.statusBar().showMessage(f"Ready - {self.get_project_title()}")

        self.graph_manager.save_state("Initial state")

    def get_project_title(self):
        if self.project_type and self.category:
            category_name = self.category.replace('_', ' ').title()
            project_name = self.project_type.replace('_', ' ').title()
            return f"{project_name} - {category_name}"
        return "BeatRooter"

    def setup_ui(self):
        self.setWindowTitle("BeatRooter")
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)

        from tools.tools_integration import ToolsIntegration
        self.tools_integration = ToolsIntegration(self)
        self.tools_integration.setup_tools_integration()
        
        # Toolbox
        self.toolbox = ToolboxWidget(self.graph_manager, self.category)
        splitter.addWidget(self.toolbox)
        
        # Canvas
        self.canvas_widget = CanvasWidget(self.graph_manager)
        splitter.addWidget(self.canvas_widget)
        
        # Detail panel
        self.detail_panel = DetailPanel(self)
        splitter.addWidget(self.detail_panel)
        
        splitter.setSizes([250, 600, 350])
        main_layout.addWidget(splitter)

        self.create_menu_bar()
        self.create_toolbar()
        self.setStatusBar(QStatusBar())

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self.check_and_request_tools)
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Investigation', self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_investigation)
        file_menu.addAction(new_action)
        
        open_action = QAction('Open...', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_investigation)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_investigation)
        file_menu.addAction(save_action)
        
        save_as_action = QAction('Save As...', self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_investigation_as)
        file_menu.addAction(save_as_action)
        
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
        
        export_svg_action = QAction('SVG Vector', self)
        export_svg_action.triggered.connect(self.export_svg)
        export_menu.addAction(export_svg_action)
        
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
        
        detective_theme_action = QAction('Detective Classic', self)
        detective_theme_action.triggered.connect(lambda: self.apply_theme('detective_classic'))
        theme_menu.addAction(detective_theme_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        beat_helper_action = QAction('BeatHelper - Manual Finder', self)
        beat_helper_action.triggered.connect(self.open_beat_helper)
        tools_menu.addAction(beat_helper_action)
        
        tools_menu.addSeparator()

        # Show/Hide Tools Panel
        toggle_tools_action = QAction('Show/Hide Tools Panel', self)
        toggle_tools_action.triggered.connect(self.toggle_tools_panel)
        tools_menu.addAction(toggle_tools_action)

        tools_menu.addSeparator()

        # Quick tools actions
        exif_action = QAction('ExifTool', self)
        exif_action.triggered.connect(lambda: self.tools_integration.quick_launch_tool('exiftool'))
        tools_menu.addAction(exif_action)

        nmap_action = QAction('Nmap', self)
        nmap_action.triggered.connect(lambda: self.tools_integration.quick_launch_tool('nmap'))
        tools_menu.addAction(nmap_action)

        whois_action = QAction('Whois', self)
        whois_action.triggered.connect(lambda: self.tools_integration.quick_launch_tool('whois'))
        tools_menu.addAction(whois_action)

        tools_menu.addSeparator()

        # Manage tools submenu
        manage_menu = tools_menu.addMenu('Manage Tools')
        install_action = QAction('Install Missing Tools...', self)
        install_action.triggered.connect(self.tools_integration.install_missing_tools)
        manage_menu.addAction(install_action)

        check_action = QAction('Check Tool Availability', self)
        check_action.triggered.connect(self.tools_integration.check_tool_availability)
        manage_menu.addAction(check_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        new_action = QAction('New', self)
        new_action.triggered.connect(self.new_investigation)
        toolbar.addAction(new_action)
        
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_investigation)
        toolbar.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save_investigation)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()

        undo_toolbar_action = QAction('Undo', self)
        undo_toolbar_action.triggered.connect(self.undo)
        undo_toolbar_action.setEnabled(False)
        toolbar.addAction(undo_toolbar_action)
        
        redo_toolbar_action = QAction('Redo', self)
        redo_toolbar_action.triggered.connect(self.redo)
        redo_toolbar_action.setEnabled(False)
        toolbar.addAction(redo_toolbar_action)
        
        toolbar.addSeparator()
        
        zoom_in_action = QAction('+ Zoom In', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction('- Zoom Out', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        reset_zoom_action = QAction('Reset Zoom', self)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        toolbar.addAction(reset_zoom_action)

    def apply_project_template(self, template_config):
        if 'metadata' in template_config:
            self.graph_manager.graph_data.metadata.update(template_config['metadata'])
        
        project_title = template_config['metadata'].get('title', 'Untitled Investigation')
        self.setWindowTitle(f"BeatRooter - {project_title}")
        
        self.statusBar().showMessage(f"Started {project_title} investigation")
    
    def setup_connections(self):
        self.toolbox.node_created.connect(self.create_node)
        self.toolbox.tools_requested.connect(self.toggle_external_tools)
        
        self.canvas_widget.node_created.connect(self.create_node_visual)
        self.canvas_widget.connection_requested.connect(self.create_connection)
        
        self.detail_panel.node_data_updated.connect(self.on_node_updated)
        self.detail_panel.node_deleted.connect(self.on_node_deleted)

    def check_and_request_tools(self):
        """Verifica e solicita instalação de ferramentas em falta após carregar"""
        from tools.tools_downloader import ToolsDownloadManager
        
        # Criar instância do download manager
        download_manager = ToolsDownloadManager(self)
        
        # Verificar ferramentas em falta
        missing_tools = download_manager.check_missing_tools()
        
        # Se houver ferramentas em falta, perguntar se quer instalar
        if missing_tools:
            warning_text = (
                "Algumas ferramentas de segurança não foram encontradas:\n\n"
                f"{', '.join(missing_tools)}\n\n"
                "Deseja instalá-las automaticamente agora?"
            )
            
            reply = QMessageBox.question(
                self,
                "Ferramentas em Falta",
                warning_text,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Solicitar instalação
                if download_manager.request_installation():
                    QMessageBox.information(
                        self,
                        "Instalação Concluída",
                        "Ferramentas instaladas com sucesso! Agora você pode usá-las."
                    )
                    # Atualizar a UI do tools manager
                    if hasattr(self, 'tools_integration') and self.tools_integration.tools_manager:
                        self.tools_integration.tools_manager.check_available_tools()

    def open_beat_helper(self):
        """Open BeatHelper manual finder dialog"""
        from ui.beat_helper_dialog import BeatHelperDialog
        
        dialog = BeatHelperDialog(self)
        dialog.exec()
        
        self.statusBar().showMessage("BeatHelper closed")

    def toggle_external_tools(self):
        self.tools_integration.toggle_tools_panel()
    
    def draw_connection(self, edge):
        if edge.source_id in self.node_widgets and edge.target_id in self.node_widgets:
            source_widget = self.node_widgets[edge.source_id]
            target_widget = self.node_widgets[edge.target_id]
            
            print(f"Creating connection from {edge.source_id} to {edge.target_id}")
            
            edge_item = DynamicEdge(source_widget, target_widget, edge)
            self.canvas_widget.scene.addItem(edge_item)
            self.edge_items[edge.id] = edge_item
    
    def on_edge_updated(self, edge):
        print(f"Updating edge: {edge.id} with label: {edge.label}")
        self.graph_manager.update_edge(edge.id, label=edge.label)
        self.statusBar().showMessage(f"Updated edge: {edge.label}")

    def on_edge_deleted(self, edge):
        print(f"Deleting edge: {edge.id}")
        
        reply = QMessageBox.question(self, 'Delete Edge', 
                                'Are you sure you want to delete this connection?',
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.graph_manager.remove_edge(edge.id)
            
            if edge.id in self.edge_items:
                edge_item = self.edge_items[edge.id]
                self.canvas_widget.scene.removeItem(edge_item)
                del self.edge_items[edge.id]
                print(f"Edge {edge.id} removed from scene")
            
            if edge.source_id in self.node_widgets:
                source_node = self.graph_manager.get_node(edge.source_id)
                if edge.id in source_node.connections:
                    source_node.connections.remove(edge.id)
            
            if edge.target_id in self.node_widgets:
                target_node = self.graph_manager.get_node(edge.target_id)
                if edge.id in target_node.connections:
                    target_node.connections.remove(edge.id)
            
            self.statusBar().showMessage("Edge deleted successfully")
            print(f"Edge {edge.id} completely deleted")
        else:
            self.statusBar().showMessage("Edge deletion cancelled")

    def undo(self):
        if self.graph_manager.undo():
            self.refresh_canvas_from_graph()
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Undo: " + self.graph_manager.history[self.graph_manager.history_position]['description'])
    
    def redo(self):
        if self.graph_manager.redo():
            self.refresh_canvas_from_graph()
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Redo: " + self.graph_manager.history[self.graph_manager.history_position]['description'])
    
    def update_undo_redo_buttons(self):
        self.undo_action.setEnabled(self.graph_manager.can_undo())
        self.redo_action.setEnabled(self.graph_manager.can_redo())
        
        for action in self.findChildren(QAction):
            if action.text() == 'Undo':
                action.setEnabled(self.graph_manager.can_undo())
            elif action.text() == 'Redo':
                action.setEnabled(self.graph_manager.can_redo())
    
    def refresh_canvas_from_graph(self):
        self.canvas_widget.scene.clear()
        self.node_widgets.clear()
        self.edge_items.clear()
        
        for node in self.graph_manager.graph_data.nodes.values():
            node_widget = NodeWidget(node, self.category)
            self.canvas_widget.add_node_widget(node_widget)
            
            node_widget.node_updated.connect(self.on_node_selected)
            node_widget.connection_started.connect(self.start_connection)
            node_widget.node_deleted.connect(self.on_node_deleted)
            
            self.node_widgets[node.id] = node_widget
        
        for edge in self.graph_manager.graph_data.edges.values():
            self.draw_connection(edge)
        
        if (self.detail_panel.current_node and 
            self.detail_panel.current_node.id not in self.graph_manager.graph_data.nodes):
            self.detail_panel.clear_panel()

    def create_node_visual(self, node):
        from core.node_factory import NodeFactory
        node_category = NodeFactory.find_node_category(node.type)
        
        if not node_category:
            node_category = self.category
            
        node_widget = NodeWidget(node, node_category)
        self.canvas_widget.add_node_widget(node_widget)
        
        node_widget.node_updated.connect(self.on_node_selected)
        node_widget.connection_started.connect(self.start_connection)
        node_widget.node_deleted.connect(self.on_node_deleted)
        
        self.node_widgets[node.id] = node_widget
        
        self.statusBar().showMessage(f"Created {node.type} node at position")

    def create_node(self, node_type):
        from PyQt6.QtCore import QPointF
        
        view_center = self.canvas_widget.mapToScene(
            self.canvas_widget.viewport().rect().center()
        )

        node_data = NodeFactory.create_node_data(node_type, category=self.category)
        node = self.graph_manager.add_node(node_type, view_center, node_data)
        
        node_widget = NodeWidget(node, self.category)
        self.canvas_widget.add_node_widget(node_widget)
        
        node_widget.node_updated.connect(self.on_node_selected)
        node_widget.connection_started.connect(self.start_connection)
        node_widget.node_deleted.connect(self.on_node_deleted)

        self.node_widgets[node.id] = node_widget
        
        self.statusBar().showMessage(f"Created {node_type} node")

        if node_type == 'screenshot':
            node_data.update({
                'filename': '',
                'file_path': '',
                'file_size': '',
                'dimensions': '',
                'format': '',
                'metadata': {}
            })
    
    def on_node_selected(self, node):
        self.detail_panel.display_node(node)
        self.statusBar().showMessage(f"Selected {node.type} node: {node.id}")
    
    def on_node_updated(self, node):
        if node.id in self.node_widgets:
            self.node_widgets[node.id].update_display()
            if hasattr(self, 'edge_items'):
                for edge_item in self.edge_items.values():
                    if (edge_item.source_node.node.id == node.id or 
                        edge_item.target_node.node.id == node.id):
                        edge_item.update_path()

        self.graph_manager.save_state(f"Update {node.type} node")
        self.update_undo_redo_buttons()
        
        self.statusBar().showMessage(f"Updated {node.type} node")

    def on_node_deleted(self, node):
        print(f"Deleting node from detail panel: {node.id}")
        
        reply = QMessageBox.question(self, 'Delete Node', 
                                   f'Are you sure you want to delete this {node.type} node?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.graph_manager.remove_node(node.id)

            if node.id in self.node_widgets:
                node_widget = self.node_widgets[node.id]
                self.canvas_widget.scene.removeItem(node_widget)
                del self.node_widgets[node.id]
            
            edges_to_remove = []
            for edge_id, edge_item in self.edge_items.items():
                edge = self.graph_manager.get_edge(edge_id)
                if edge is None or edge.source_id == node.id or edge.target_id == node.id:
                    self.canvas_widget.scene.removeItem(edge_item)
                    edges_to_remove.append(edge_id)
            
            for edge_id in edges_to_remove:
                if edge_id in self.edge_items:
                    del self.edge_items[edge_id]
            
            if self.detail_panel.current_node and self.detail_panel.current_node.id == node.id:
                self.detail_panel.clear_panel()
            
            self.update_undo_redo_buttons()
            
            self.statusBar().showMessage(f"Deleted {node.type} node and its connections")

    
    def start_connection(self, source_widget):
        print(f"Starting connection from node: {source_widget.node.id}")
        self.connection_source = source_widget
        
        self.canvas_widget.viewport().installEventFilter(self)
        self.statusBar().showMessage("Connection mode: Click target node or ESC to cancel")
    
    def create_connection(self, source_id, target_id):
        try:
            print(f"Attempting to connect {source_id} to {target_id}")
            
            edge = self.graph_manager.connect_nodes(source_id, target_id, "")
            
            self.draw_connection(edge)
            
            self.update_undo_redo_buttons()
            
            self.statusBar().showMessage(f"Connected {source_id} to {target_id}")
        except ValueError as e:
            self.statusBar().showMessage(f"Connection failed: {e}")
            print(f"Connection error: {e}")
    
    def search_nodes(self, search_text):
        if not search_text:
            for node_widget in self.node_widgets.values():
                node_widget.setVisible(True)
            return
            
        for node_id, node_widget in self.node_widgets.items():
            node = node_widget.node
            matches = any(
                search_text.lower() in str(value).lower() 
                for value in node.data.values()
            ) or search_text.lower() in node.type.lower() or search_text.lower() in node.id.lower()
            
            node_widget.setVisible(matches)
    
    def filter_nodes(self, node_types):
        if not node_types:
            for node_widget in self.node_widgets.values():
                node_widget.setVisible(True)
        else:
            for node_id, node_widget in self.node_widgets.items():
                node_widget.setVisible(node_widget.node.type in node_types)
    
    def new_investigation(self):
        from ui.project_selection_dialog import ProjectSelectionDialog
        
        if self.has_unsaved_changes():
            reply = QMessageBox.question(self, 'New Investigation', 
                                    'You have unsaved changes. Are you sure you want to start a new investigation?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        dialog = ProjectSelectionDialog(self)
        
        def on_project_selected(project_type, category):
            self.graph_manager.clear_graph()
            self.canvas_widget.scene.clear()
            self.node_widgets.clear()
            self.edge_items.clear()
            self.detail_panel.clear_panel()

            self.project_type = project_type
            self.category = category
            
            self.toolbox.update_category(category)
            
            self.setWindowTitle(f"BeatRooter - {self.get_project_title()}")
            
            self.statusBar().showMessage(f"New {project_type} investigation started: {category}")
        
        dialog.project_selected.connect(on_project_selected)
        dialog.exec()

    def has_unsaved_changes(self):
        return len(self.graph_manager.graph_data.nodes) > 0

    def get_project_title(self):
        if hasattr(self, 'project_type') and hasattr(self, 'category') and self.project_type and self.category:
            project_names = {
                'blueteam': 'Blue Team',
                'soc_team': 'SOC Operations', 
                'redteam': 'Red Team'
            }
            
            category_names = {
                'incident_response': 'Incident Response',
                'threat_hunting': 'Threat Hunting',
                'malware_analysis': 'Malware Analysis', 
                'siem_investigation': 'SIEM Investigation',
                'alert_triage': 'Alert Triage',
                'correlation_analysis': 'Correlation Analysis',
                'compliance_monitoring': 'Compliance Monitoring',
                'web_pentesting': 'Web Application Testing',
                'network_pentesting': 'Network Assessment',
                'social_engineering': 'Social Engineering'
            }
            
            project_name = project_names.get(self.project_type, self.project_type.title())
            category_name = category_names.get(self.category, self.category.replace('_', ' ').title())
            
            return f"{project_name} - {category_name}"
        return "BeatRooter - New Investigation"

    def load_graph_data(self, graph_data):
        self.graph_manager.clear_graph()
        self.canvas_widget.scene.clear()
        self.node_widgets.clear()
        self.edge_items.clear()
        
        for node in graph_data.nodes.values():
            self.graph_manager.graph_data.nodes[node.id] = node
            node_widget = NodeWidget(node)
            self.canvas_widget.add_node_widget(node_widget)
            node_widget.node_updated.connect(self.on_node_selected)
            node_widget.connection_started.connect(self.start_connection)
            self.node_widgets[node.id] = node_widget
        
        for edge in graph_data.edges.values():
            self.graph_manager.graph_data.edges[edge.id] = edge
            self.draw_connection(edge)
    
    def open_investigation(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open Investigation', '', 
            'BeatRooter Tree Files (*.brt);;JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            try:
                graph_data = self.storage_manager.load_graph(filename)
                self.load_graph_data(graph_data)
                self.statusBar().showMessage(f"Opened investigation: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
                print(f"Error loading file: {e}")

    
    def save_investigation(self):
        if self.storage_manager.current_file:
            success = self.storage_manager.save_graph(
                self.graph_manager.graph_data, 
                self.storage_manager.current_file
            )
            if success:
                # Save as last project for quick access
                settings = QSettings('BeatRooter', 'BeatRooter')
                settings.setValue('last_project', self.storage_manager.current_file)
                self.statusBar().showMessage(f"Investigation saved")
            else:
                self.statusBar().showMessage("Save failed")
        else:
            self.save_investigation_as()
    
    def save_investigation_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Save Investigation', '', 
            'BeatRooter Tree Files (*.brt);;JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            if not filename.endswith('.brt') and not filename.endswith('.json'):
                filename += '.brt'
            
            success = self.storage_manager.save_graph(
                self.graph_manager.graph_data, filename
            )
            if success:
                # Save as last project for quick access
                settings = QSettings('BeatRooter', 'BeatRooter')
                settings.setValue('last_project', filename)
                self.statusBar().showMessage(f"Investigation saved as: {filename}")
            else:
                self.statusBar().showMessage("Save failed")
    
    def export_png(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export as PNG', '', 'PNG Images (*.png)'
        )
        
        if filename:
            if not filename.lower().endswith('.png'):
                filename += '.png'
                
            if len(self.canvas_widget.scene.items()) == 0:
                QMessageBox.warning(self, "Empty Canvas", "There are no items to export on the canvas.")
                return
                
            print(f"Starting PNG export with {len(self.canvas_widget.scene.items())} items")
            success = self.storage_manager.export_png(
                self.graph_manager.graph_data, 
                filename,
                self.canvas_widget.scene
            )
            if success:
                self.statusBar().showMessage(f"Exported PNG: {filename}")
                QMessageBox.information(self, "Export Successful", f"PNG exported successfully to:\n{filename}")
            else:
                self.statusBar().showMessage("PNG export failed")
                QMessageBox.warning(self, "Export Failed", "Failed to export PNG. Check console for details.")

    def export_svg(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export as SVG', '', 'SVG Files (*.svg)'
        )
        
        if filename:
            if not filename.lower().endswith('.svg'):
                filename += '.svg'
                
            success = self.storage_manager.export_svg(
                self.graph_manager.graph_data, 
                filename,
                self.canvas_widget.scene
            )
            if success:
                self.statusBar().showMessage(f"Exported SVG: {filename}")
            else:
                self.statusBar().showMessage("SVG export failed")

    def export_json(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Export as JSON', '', 'JSON Files (*.json)'
        )
        
        if filename:
            if not filename.lower().endswith('.json'):
                filename += '.json'
                
            success = self.storage_manager.export_json(
                self.graph_manager.graph_data, filename
            )
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
        self.canvas_widget.scale(1.2, 1.2)
    
    def zoom_out(self):
        self.canvas_widget.scale(0.8, 0.8)
    
    def reset_zoom(self):
        self.canvas_widget.resetTransform()
    
    def clear_canvas(self):
        reply = QMessageBox.question(self, 'Clear Canvas', 
                                   'Are you sure you want to clear the entire canvas?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.graph_manager.clear_graph()
            self.canvas_widget.scene.clear()
            self.node_widgets.clear()
            self.detail_panel.clear_panel()
            self.statusBar().showMessage("Canvas cleared")
    
    def show_about(self):
        about_text = """
        <h2>BeatRooter</h2>
        <p><b>Version 1.0</b></p>
        <p>Cyber Investigation and Threat Mapping Tool</p>
        <p>Built with PyQt6 for digital forensics and security analysis.</p>
        <p>Features:</p>
        <ul>
        <li>Interactive investigation boards</li>
        <li>Multiple node types for cyber investigations</li>
        <li>Relationship mapping and visualization</li>
        <li>Hacker and classic detective themes</li>
        <li>Export to multiple formats</li>
        </ul>
        <p>© 2024 BeatRooter</p>
        """
        
        QMessageBox.about(self, "About BeatRooter", about_text)
    
    def closeEvent(self, event):
        event.accept()

    def toggle_tools_panel(self):
        """Toggle the visibility of the tools panel"""
        if hasattr(self, 'tools_integration') and self.tools_integration.tools_dock:
            if self.tools_integration.tools_dock.isVisible():
                self.tools_integration.tools_dock.hide()
            else:
                self.tools_integration.tools_dock.show()

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.undo()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Y:
                self.redo()
                event.accept()
                return
        
        super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        if (obj == self.canvas_widget.viewport() and 
            event.type() == event.Type.MouseButtonPress and
            self.connection_source):
            
            print("Mouse click detected in connection mode")
            
            items = self.canvas_widget.items(event.pos())
            print(f"Found {len(items)} items at click position")
            
            for item in items:
                if isinstance(item, NodeWidget) and item != self.connection_source:
                    print(f"Target node found: {item.node.id}")
                    self.create_connection(self.connection_source.node.id, item.node.id)
                    
                    self.connection_source = None
                    self.canvas_widget.viewport().removeEventFilter(self)
                    self.statusBar().showMessage("Connection completed")
                    return True
            
            print("No valid target found, canceling connection")
            self.connection_source = None
            self.canvas_widget.viewport().removeEventFilter(self)
            self.statusBar().showMessage("Connection cancelled")
            return True
            
        elif (event.type() == event.Type.KeyPress and 
            event.key() == Qt.Key.Key_Escape and
            self.connection_source):
            
            print("ESC pressed, canceling connection")
            self.connection_source = None
            self.canvas_widget.viewport().removeEventFilter(self)
            self.statusBar().showMessage("Connection cancelled")
            return True
            
        return super().eventFilter(obj, event)