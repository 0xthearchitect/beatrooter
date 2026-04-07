import sys
import os
import re
import json
import shlex
import copy
import platform
import shutil
import stat
import subprocess
import getpass
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QToolBar, QStatusBar, QFileDialog, QMessageBox,
                             QSplitter, QApplication, QGraphicsLineItem, QGraphicsRectItem,
                             QDialog, QDialogButtonBox, QPlainTextEdit, QTabBar)
from PyQt6.QtCore import Qt, QPointF, QLineF, QSettings, QRectF, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QPen, QColor
from PyQt6 import sip

from features.beatroot_canvas.core import GraphManager, StorageManager, ThemeManager, NodeFactory
from features.beatroot_canvas.core.flipper_workspace_importer import FlipperWorkspaceImporter
from features.beatroot_canvas.core.flipper_device_manager import FlipperDeviceManager
from features.beatroot_canvas.core.flipper_serial_storage import FlipperSerialStorageMirror, FlipperSerialBusyError, FlipperSerialError

from features.beatroot_canvas.ui.canvas_widget import CanvasWidget
from features.beatroot_canvas.ui.flipper_explorer_dialog import FlipperExplorerDialog
from features.beatroot_canvas.ui.toolbox import ToolboxWidget
from features.beatroot_canvas.ui.detail_panel import DetailPanel
from features.beatroot_canvas.ui.node_widget import NodeWidget
from features.beatroot_canvas.ui.dynamic_edge import DynamicEdge
from features.beatroot_canvas.ui.tool_node_dialogs import ToolNodeConfigDialog, ToolNodeOutputDialog
from features.beatroot_canvas.ui.stacker_item import StackerItem
from features.beatroot_canvas.ui.stackers_panel import StackersPanel, StackerDetailsDialog
from utils.image_utils import ImageUtils
#from ai.ai_assistant import AIAssistant
from utils.path_utils import get_resource_path
from features.tools.core.tool_node_service import ToolNodeService


class DigitalDetectiveBoard(QMainWindow):
    STACKER_Z_BASE = -200.0

    def __init__(self, project_type=None, category=None, template_data=None):
        super().__init__()
        self.graph_manager = GraphManager()
        self.storage_manager = StorageManager()
        self.current_theme = 'cyber_modern'
        self.node_widgets = {}
        self.edge_items = {}
        self.stacker_items = {}
        self.connection_source = None
        self.tool_run_threads = {}
        self.tool_output_cache = {}
        self.pending_stacker_preview_item = None
        self._active_stacker_drag_contexts = {}
        self._applying_stacker_cascade = False
        self._syncing_stacker_selection = False
        self.flipper_explorer_dialog = None
        self.flipper_rpc_mirror_root = None
        self.stackers_panel = None
        self.documents = []
        self.active_document_index = -1
        self._document_sequence = 0
        self._suspend_document_dirty_tracking = False
        self._missing_tools_prompt_shown = False
        self._suppress_missing_tools_prompt = False
        NodeFactory.reset_custom_node_templates()
        NodeFactory.reset_node_template_settings()

        from features.tools.integrations.tools_integration import ToolsIntegration
        self.tools_integration = ToolsIntegration(self)

        self.project_type = project_type
        self.category = category
        self.template_data = template_data
        self._load_accessibility_preferences()

        #self.ai_assistant = None
        
        self.setWindowIcon(QIcon(get_resource_path("icons/app_icon.png", 'assets')))
        self.setup_ui()
        self.apply_theme(self.current_theme)
        self.setup_connections()
        self._install_save_state_hook()

        
        if category:
            self.toolbox.update_category(category)
        
        self.statusBar().showMessage(f"Ready - {self.get_project_title()}")

        self.graph_manager.save_state("Initial state")
        if self.documents and self.active_document_index >= 0:
            self.documents[self.active_document_index]["dirty"] = False
            self._update_document_tab_label(self.active_document_index)

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
        central_widget.setObjectName("MainRoot")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("MainSplitter")
        self.main_splitter = splitter
        self._detail_panel_last_width = 300

        self.toolbox = ToolboxWidget(self.graph_manager, self.category)
        self.toolbox.setObjectName("ToolboxColumn")
        
        # Canvas column (tabs + canvas)
        canvas_column = QWidget()
        canvas_column.setObjectName("CanvasColumn")
        canvas_column_layout = QVBoxLayout(canvas_column)
        canvas_column_layout.setContentsMargins(0, 0, 0, 0)
        canvas_column_layout.setSpacing(0)

        self.document_tabs = QTabBar()
        self.document_tabs.setDrawBase(False)
        self.document_tabs.setExpanding(False)
        self.document_tabs.setMovable(False)
        self.document_tabs.setTabsClosable(True)
        self.document_tabs.setObjectName("DocumentTabs")
        self.document_tabs.currentChanged.connect(self._on_document_tab_changed)
        self.document_tabs.tabCloseRequested.connect(self._close_document_tab)
        canvas_column_layout.addWidget(self.document_tabs)

        self.canvas_widget = CanvasWidget(self.graph_manager)
        self.canvas_widget.setObjectName("CanvasView")
        canvas_column_layout.addWidget(self.canvas_widget)
        splitter.addWidget(canvas_column)
        self.canvas_widget.viewport_resized.connect(self._sync_floating_toolbox_geometry)
        self.toolbox.setParent(self.canvas_widget.viewport())
        self.toolbox.show()
        self.toolbox.raise_()
        
        # Detail panel
        self.detail_panel = DetailPanel(self)
        self.detail_panel.setObjectName("DetailColumn")
        self.detail_panel.setMinimumWidth(380)
        self.detail_panel.setMaximumWidth(540)
        splitter.addWidget(self.detail_panel)

        self.tools_integration.setup_tools_integration(use_dock=False)
        self.detail_panel.attach_tools_widget(self.tools_integration.tools_manager)

        self.stackers_panel = StackersPanel(self)
        self.stackers_panel.create_requested.connect(self.toggle_stacker_creation_mode)
        self.stackers_panel.edit_selected_requested.connect(self.edit_selected_stacker)
        self.stackers_panel.delete_selected_requested.connect(self.delete_selected_stacker)
        self.stackers_panel.stacker_selected.connect(self._on_stacker_selected_from_panel)
        self.stackers_panel.layer_action_requested.connect(self._on_stacker_layer_action_requested)
        self.detail_panel.attach_stackers_widget(self.stackers_panel)
        self.canvas_widget.scene.selectionChanged.connect(self._on_scene_selection_changed)
        
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1140, 320])
        main_layout.addWidget(splitter)

        self.create_menu_bar()
        self.create_toolbar()
        self.setStatusBar(QStatusBar())
        self._ensure_stacker_metadata()
        self._refresh_stackers_panel()
        self._create_initial_document_tab()
        self.detail_panel.panel_visibility_changed.connect(self._apply_detail_panel_visibility)
        self._apply_detail_panel_visibility(self.detail_panel.has_visible_tabs())
        self._schedule_missing_tools_prompt_if_needed()
        QTimer.singleShot(0, self._sync_floating_toolbox_geometry)

    def _sync_floating_toolbox_geometry(self):
        if not hasattr(self, "toolbox") or not hasattr(self, "canvas_widget"):
            return

        viewport = self.canvas_widget.viewport()
        if viewport is None:
            return

        if self.toolbox.parent() is not viewport:
            self.toolbox.setParent(viewport)
            self.toolbox.show()

        viewport_size = viewport.size()
        if viewport_size.width() <= 0 or viewport_size.height() <= 0:
            return

        self.toolbox.sync_overlay_size(viewport_size)
        x = 18
        y = 18
        self.toolbox.move(x, y)
        self.toolbox.raise_()
    
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
        self.fullscreen_action = QAction('Full Screen', self)
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setShortcut('F11')
        self.fullscreen_action.toggled.connect(self.toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)

        # Accessibility menu
        accessibility_menu = menubar.addMenu('Accessibility')
        self.suppress_missing_tools_prompt_action = QAction('Silence missing tools popup', self)
        self.suppress_missing_tools_prompt_action.setCheckable(True)
        self.suppress_missing_tools_prompt_action.setChecked(self._suppress_missing_tools_prompt)
        self.suppress_missing_tools_prompt_action.setToolTip(
            'Disables the automatic missing tools prompt when opening BeatRooter and new projects.'
        )
        self.suppress_missing_tools_prompt_action.toggled.connect(self._set_suppress_missing_tools_prompt)
        accessibility_menu.addAction(self.suppress_missing_tools_prompt_action)

        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        node_settings_action = QAction('Node Settings...', self)
        node_settings_action.triggered.connect(self.open_node_settings_dialog)
        settings_menu.addAction(node_settings_action)
        settings_menu.addSeparator()

        dockers_menu = settings_menu.addMenu('Panels')

        self.docker_nodes_action = QAction('Nodes', self)
        self.docker_nodes_action.setCheckable(True)
        self.docker_nodes_action.setChecked(True)
        self.docker_nodes_action.toggled.connect(
            lambda checked: self.detail_panel.set_nodes_tab_visible(checked)
        )
        dockers_menu.addAction(self.docker_nodes_action)

        self.docker_tools_action = QAction('Tools', self)
        self.docker_tools_action.setCheckable(True)
        self.docker_tools_action.setChecked(True)
        self.docker_tools_action.toggled.connect(
            lambda checked: self.detail_panel.set_tools_tab_visible(checked)
        )
        dockers_menu.addAction(self.docker_tools_action)

        self.docker_stackers_action = QAction('Stackers', self)
        self.docker_stackers_action.setCheckable(True)
        self.docker_stackers_action.setChecked(True)
        self.docker_stackers_action.toggled.connect(
            lambda checked: self.detail_panel.set_stackers_tab_visible(checked)
        )
        dockers_menu.addAction(self.docker_stackers_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        beat_helper_action = QAction('BeatHelper - Manual Finder', self)
        beat_helper_action.triggered.connect(self.open_beat_helper)
        tools_menu.addAction(beat_helper_action)

        import_flipper_action = QAction('Open Flipper Explorer...', self)
        import_flipper_action.triggered.connect(self.import_flipper_workspace)
        tools_menu.addAction(import_flipper_action)
        
        tools_menu.addSeparator()

        # Manage tools submenu
        manage_menu = tools_menu.addMenu('Manage Tools')
        install_action = QAction('Install Missing Tools...', self)
        install_action.triggered.connect(self.tools_integration.install_missing_tools)
        manage_menu.addAction(install_action)

        check_action = QAction('Check Tool Availability', self)
        check_action.triggered.connect(self.tools_integration.check_tool_availability)
        manage_menu.addAction(check_action)

        permissions_action = QAction('Run Permissions Diagnostics...', self)
        permissions_action.triggered.connect(self.run_permissions_diagnostics)
        manage_menu.addAction(permissions_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        self.main_toolbar = QToolBar("Main Toolbar")
        self.main_toolbar.setObjectName("MainToolbar")
        self.main_toolbar.setMovable(False)
        self.addToolBar(self.main_toolbar)
        
        new_action = QAction('New', self)
        new_action.triggered.connect(self.new_investigation)
        self.main_toolbar.addAction(new_action)
        
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_investigation)
        self.main_toolbar.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save_investigation)
        self.main_toolbar.addAction(save_action)
        
        self.main_toolbar.addSeparator()

        undo_toolbar_action = QAction('Undo', self)
        undo_toolbar_action.triggered.connect(self.undo)
        undo_toolbar_action.setEnabled(False)
        self.main_toolbar.addAction(undo_toolbar_action)
        
        redo_toolbar_action = QAction('Redo', self)
        redo_toolbar_action.triggered.connect(self.redo)
        redo_toolbar_action.setEnabled(False)
        self.main_toolbar.addAction(redo_toolbar_action)
        
        self.main_toolbar.addSeparator()
        
        zoom_in_action = QAction('Zoom +', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        self.main_toolbar.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom -', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        self.main_toolbar.addAction(zoom_out_action)
        
        reset_zoom_action = QAction('Reset', self)
        reset_zoom_action.triggered.connect(self.reset_zoom)
        self.main_toolbar.addAction(reset_zoom_action)

    def _install_save_state_hook(self):
        original_save_state = self.graph_manager.save_state

        def hooked_save_state(description=""):
            original_save_state(description)
            if not self._suspend_document_dirty_tracking:
                self._mark_active_document_dirty()

        self.graph_manager.save_state = hooked_save_state

    def _create_initial_document_tab(self):
        self._append_document_tab(
            graph_data=copy.deepcopy(self.graph_manager.graph_data),
            project_type=self.project_type,
            category=self.category,
            file_path=None,
            dirty=False,
            activate=True,
        )

    def _append_document_tab(
        self,
        graph_data=None,
        project_type=None,
        category=None,
        file_path=None,
        dirty=False,
        activate=True,
    ):
        payload = graph_data if graph_data is not None else self.graph_manager.graph_data
        snapshot = copy.deepcopy(payload)
        try:
            node_counter = max(
                [int(str(node_id).split("_")[-1]) for node_id in snapshot.nodes.keys() if str(node_id).startswith("node_")]
                + [-1]
            ) + 1
        except ValueError:
            node_counter = len(snapshot.nodes)
        try:
            edge_counter = max(
                [int(str(edge_id).split("_")[-1]) for edge_id in snapshot.edges.keys() if str(edge_id).startswith("edge_")]
                + [-1]
            ) + 1
        except ValueError:
            edge_counter = len(snapshot.edges)

        document = {
            "id": f"doc_{self._document_sequence}",
            "graph_data": snapshot,
            "project_type": project_type,
            "category": category,
            "file_path": file_path,
            "dirty": bool(dirty),
            "node_counter": node_counter,
            "edge_counter": edge_counter,
        }
        self._document_sequence += 1
        self.documents.append(document)
        tab_index = len(self.documents) - 1

        self.document_tabs.blockSignals(True)
        self.document_tabs.addTab("")
        self._update_document_tab_label(tab_index)
        self.document_tabs.blockSignals(False)

        if activate:
            self._activate_document_tab(tab_index)
            self._schedule_missing_tools_prompt_if_needed()
        return tab_index

    def _estimate_document_size_bytes(self, document: dict) -> int:
        file_path = str(document.get("file_path") or "").strip()
        if file_path and os.path.exists(file_path) and not bool(document.get("dirty")):
            try:
                return max(0, int(os.path.getsize(file_path)))
            except OSError:
                pass
        graph_data = document.get("graph_data")
        if (
            self.active_document_index >= 0
            and self.active_document_index < len(self.documents)
            and self.documents[self.active_document_index] is document
        ):
            graph_data = self.graph_manager.graph_data
        if not graph_data:
            return 0
        try:
            serialized = json.dumps(graph_data.to_dict(), ensure_ascii=False)
            return len(serialized.encode("utf-8"))
        except Exception:
            return 0

    def _format_size_label(self, size_bytes: int) -> str:
        size_bytes = max(0, int(size_bytes))
        if size_bytes < (1024 * 1024):
            if size_bytes == 0:
                return "0 KB"
            kb = size_bytes / 1024.0
            return f"{max(1, int(round(kb)))} KB"

        mb = float(size_bytes) / (1024.0 * 1024.0)
        return f"{mb:.1f} MB"

    def _build_document_tab_text(self, document: dict) -> str:
        file_path = str(document.get("file_path") or "").strip()
        dirty = bool(document.get("dirty"))
        base_name = os.path.basename(file_path) if file_path else "Untitled Investigation"
        state_label = "Not Saved" if dirty or not file_path else "Saved"
        size_label = self._format_size_label(self._estimate_document_size_bytes(document))
        return f"[{state_label}] {base_name} ({size_label})"

    def _update_document_tab_label(self, index: int):
        if index < 0 or index >= len(self.documents):
            return
        self.document_tabs.setTabText(index, self._build_document_tab_text(self.documents[index]))
        if index == self.active_document_index:
            self._update_window_title_for_active_document()

    def _update_window_title_for_active_document(self):
        if self.active_document_index < 0 or self.active_document_index >= len(self.documents):
            self.setWindowTitle("BeatRooter")
            return
        document = self.documents[self.active_document_index]
        file_path = str(document.get("file_path") or "").strip()
        base_name = os.path.basename(file_path) if file_path else "Untitled Investigation"
        self.setWindowTitle(f"BeatRooter - {base_name}")

    def _snapshot_active_document(self):
        if self.active_document_index < 0 or self.active_document_index >= len(self.documents):
            return
        document = self.documents[self.active_document_index]
        document["graph_data"] = copy.deepcopy(self.graph_manager.graph_data)
        document["project_type"] = self.project_type
        document["category"] = self.category
        document["file_path"] = self.storage_manager.current_file
        document["node_counter"] = int(self.graph_manager.node_counter)
        document["edge_counter"] = int(self.graph_manager.edge_counter)
        self._update_document_tab_label(self.active_document_index)

    def _load_document_into_canvas(self, index: int):
        if index < 0 or index >= len(self.documents):
            return
        document = self.documents[index]
        self._suspend_document_dirty_tracking = True
        try:
            self.project_type = document.get("project_type")
            self.category = document.get("category")
            self.storage_manager.current_file = document.get("file_path")
            self.load_graph_data(copy.deepcopy(document["graph_data"]))
            self.graph_manager.node_counter = int(document.get("node_counter", self.graph_manager.node_counter))
            self.graph_manager.edge_counter = int(document.get("edge_counter", self.graph_manager.edge_counter))
            if self.category:
                self.toolbox.update_category(self.category)
        finally:
            self._suspend_document_dirty_tracking = False

    def _activate_document_tab(self, index: int):
        if index < 0 or index >= len(self.documents):
            return
        if self.active_document_index == index:
            self.document_tabs.setCurrentIndex(index)
            self._update_document_tab_label(index)
            return

        self._snapshot_active_document()
        self.active_document_index = index
        self.document_tabs.blockSignals(True)
        self.document_tabs.setCurrentIndex(index)
        self.document_tabs.blockSignals(False)
        self._load_document_into_canvas(index)
        self._update_document_tab_label(index)
        self._schedule_missing_tools_prompt_if_needed()

    def _on_document_tab_changed(self, index: int):
        self._activate_document_tab(index)

    def _mark_active_document_dirty(self):
        if self.active_document_index < 0 or self.active_document_index >= len(self.documents):
            return
        document = self.documents[self.active_document_index]
        if not document.get("dirty"):
            document["dirty"] = True
            self._update_document_tab_label(self.active_document_index)
        else:
            self._update_document_tab_label(self.active_document_index)

    def _save_document_snapshot(self, index: int, force_save_as: bool = False) -> bool:
        if index < 0 or index >= len(self.documents):
            return False

        document = self.documents[index]
        target_file = str(document.get("file_path") or "").strip()
        if force_save_as or not target_file:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Investigation",
                target_file or "",
                "BeatRooter Tree Files (*.brt);;JSON Files (*.json);;All Files (*)",
            )
            if not filename:
                return False
            if not filename.endswith(".brt") and not filename.endswith(".json"):
                filename += ".brt"
            target_file = filename

        previous_current = self.storage_manager.current_file
        success = self.storage_manager.save_graph(document["graph_data"], target_file)
        if not success:
            self.storage_manager.current_file = previous_current
            self.statusBar().showMessage("Save failed")
            return False

        document["file_path"] = target_file
        document["dirty"] = False
        if index == self.active_document_index:
            self.storage_manager.current_file = target_file
        else:
            self.storage_manager.current_file = previous_current

        settings = QSettings("BeatRooter", "BeatRooter")
        settings.setValue("last_project", target_file)
        self._update_document_tab_label(index)
        return True

    def _confirm_close_document(self, index: int) -> bool:
        if index < 0 or index >= len(self.documents):
            return False
        document = self.documents[index]
        if not document.get("dirty"):
            return True
        file_path = str(document.get("file_path") or "").strip()
        base_name = os.path.basename(file_path) if file_path else "Untitled Investigation"
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Question)
        message.setWindowTitle("Close Document")
        message.setText(f"'{base_name}' has unsaved changes.")
        message.setInformativeText("Do you want to save changes before closing?")
        save_btn = message.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard_btn = message.addButton("Don't Save", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = message.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        message.setDefaultButton(save_btn)
        message.exec()

        clicked = message.clickedButton()
        if clicked == save_btn:
            return self._save_document_snapshot(index)
        if clicked == discard_btn:
            return True
        if clicked == cancel_btn:
            return False
        return False

    def _close_document_tab(self, index: int):
        if index < 0 or index >= len(self.documents):
            return
        self._snapshot_active_document()
        if not self._confirm_close_document(index):
            self.document_tabs.blockSignals(True)
            if self.active_document_index >= 0:
                self.document_tabs.setCurrentIndex(self.active_document_index)
            self.document_tabs.blockSignals(False)
            return

        closing_active = index == self.active_document_index
        self.documents.pop(index)
        self.document_tabs.blockSignals(True)
        self.document_tabs.removeTab(index)
        self.document_tabs.blockSignals(False)

        if not self.documents:
            self.active_document_index = -1
            self._suspend_document_dirty_tracking = True
            try:
                self._stop_all_tool_threads()
                NodeFactory.reset_custom_node_templates()
                NodeFactory.reset_node_template_settings()
                self.graph_manager.clear_graph()
                self.canvas_widget.scene.clear()
                self.node_widgets.clear()
                self.edge_items.clear()
                self.stacker_items.clear()
                self.detail_panel.clear_panel()
                self._reset_stackers_metadata()
                self.storage_manager.current_file = None
            finally:
                self._suspend_document_dirty_tracking = False
            self._append_document_tab(
                graph_data=copy.deepcopy(self.graph_manager.graph_data),
                project_type=self.project_type,
                category=self.category,
                file_path=None,
                dirty=False,
                activate=True,
            )
            return

        if closing_active:
            target = max(0, min(index, len(self.documents) - 1))
            self.active_document_index = -1
            self._activate_document_tab(target)
            return

        if self.active_document_index > index:
            self.active_document_index -= 1
        self._update_document_tab_label(self.active_document_index)

    def _ensure_stacker_metadata(self):
        metadata = self.graph_manager.graph_data.metadata
        if not isinstance(metadata.get("stackers"), list):
            metadata["stackers"] = []
        if not isinstance(metadata.get("stacker_counter"), int):
            metadata["stacker_counter"] = 0

    def _reset_stackers_metadata(self):
        self.graph_manager.graph_data.metadata["stackers"] = []
        self.graph_manager.graph_data.metadata["stacker_counter"] = 0
        self._refresh_stackers_panel()

    def _next_stacker_id(self) -> str:
        self._ensure_stacker_metadata()
        counter = self.graph_manager.graph_data.metadata.get("stacker_counter", 0)
        stacker_id = f"stacker_{counter}"
        self.graph_manager.graph_data.metadata["stacker_counter"] = counter + 1
        return stacker_id

    def _find_stacker_payload(self, stacker_id: str):
        self._ensure_stacker_metadata()
        for payload in self.graph_manager.graph_data.metadata.get("stackers", []):
            if str(payload.get("id", "")) == stacker_id:
                return payload
        return None

    def _stacker_z_for_layer(self, layer: int) -> float:
        return self.STACKER_Z_BASE + float(layer)

    def _safe_canvas_scene(self):
        canvas_widget = getattr(self, "canvas_widget", None)
        if canvas_widget is None:
            return None

        scene = getattr(canvas_widget, "scene", None)
        if scene is None:
            return None

        try:
            if sip.isdeleted(scene):
                return None
        except Exception:
            return None

        return scene

    def _normalize_stacker_layers(self):
        self._ensure_stacker_metadata()
        stackers = self.graph_manager.graph_data.metadata.get("stackers", [])
        ordered = []
        for original_index, payload in enumerate(stackers):
            if not isinstance(payload, dict):
                continue
            try:
                layer_value = int(payload.get("layer", original_index))
            except (TypeError, ValueError):
                layer_value = original_index
            ordered.append((layer_value, original_index, payload))

        ordered.sort(key=lambda entry: (entry[0], entry[1]))
        for new_layer, (_, _, payload) in enumerate(ordered):
            payload["layer"] = new_layer

    def _next_stacker_layer(self) -> int:
        self._normalize_stacker_layers()
        stackers = [
            payload
            for payload in self.graph_manager.graph_data.metadata.get("stackers", [])
            if isinstance(payload, dict)
        ]
        return len(stackers)

    def _apply_stacker_layers_to_items(self):
        for stacker_id, stacker_item in self.stacker_items.items():
            payload = self._find_stacker_payload(stacker_id)
            if not payload:
                continue
            try:
                layer = int(payload.get("layer", 0))
            except (TypeError, ValueError):
                layer = 0
            stacker_item.setZValue(self._stacker_z_for_layer(layer))

    def _selected_stacker_id_from_scene(self) -> str:
        scene = self._safe_canvas_scene()
        if scene is None:
            return ""

        try:
            for item in scene.selectedItems():
                if isinstance(item, StackerItem):
                    return item.stacker_id
        except RuntimeError:
            return ""
        return ""

    def _refresh_stackers_panel(self, selected_id: str = ""):
        if not self.stackers_panel:
            return

        self._ensure_stacker_metadata()
        entries = []
        for payload in self.graph_manager.graph_data.metadata.get("stackers", []):
            if not isinstance(payload, dict):
                continue
            stacker_id = str(payload.get("id", "")).strip()
            if not stacker_id:
                continue
            try:
                layer = int(payload.get("layer", 0))
            except (TypeError, ValueError):
                layer = 0
            entries.append(
                {
                    "id": stacker_id,
                    "name": str(payload.get("name", "Stacker")).strip() or "Stacker",
                    "layer": layer,
                }
            )

        entries.sort(key=lambda item: item["layer"], reverse=True)
        current_selected = str(selected_id or self._selected_stacker_id_from_scene() or "")
        self.stackers_panel.set_stackers(entries, selected_id=current_selected)

    def _on_scene_selection_changed(self):
        if self._syncing_stacker_selection or not self.stackers_panel:
            return
        scene = self._safe_canvas_scene()
        if scene is None:
            return
        selected_id = self._selected_stacker_id_from_scene()
        self.stackers_panel.set_selected_stacker(selected_id)

    def _on_stacker_selected_from_panel(self, stacker_id: str):
        if self._syncing_stacker_selection:
            return

        scene = self._safe_canvas_scene()
        if scene is None:
            return

        stacker_item = self.stacker_items.get(str(stacker_id or ""))
        if not stacker_item:
            return

        self._syncing_stacker_selection = True
        try:
            try:
                for item in scene.selectedItems():
                    if isinstance(item, StackerItem) and item is not stacker_item:
                        item.setSelected(False)
            except RuntimeError:
                return
            stacker_item.setSelected(True)
        finally:
            self._syncing_stacker_selection = False

    def _on_stacker_layer_action_requested(self, stacker_id: str, action: str):
        stacker_id = str(stacker_id or "").strip()
        action = str(action or "").strip()
        if not stacker_id or not action:
            return

        self._ensure_stacker_metadata()
        self._normalize_stacker_layers()
        ordered_payloads = sorted(
            [
                payload
                for payload in self.graph_manager.graph_data.metadata.get("stackers", [])
                if isinstance(payload, dict) and payload.get("id")
            ],
            key=lambda payload: int(payload.get("layer", 0)),
        )
        ordered_ids = [str(payload.get("id", "")) for payload in ordered_payloads]
        if stacker_id not in ordered_ids or len(ordered_ids) < 2:
            return

        current_index = ordered_ids.index(stacker_id)
        target_index = current_index
        if action == "to_front":
            target_index = len(ordered_ids) - 1
        elif action == "to_back":
            target_index = 0
        elif action == "forward":
            target_index = min(len(ordered_ids) - 1, current_index + 1)
        elif action == "backward":
            target_index = max(0, current_index - 1)

        if target_index == current_index:
            return

        moved_id = ordered_ids.pop(current_index)
        ordered_ids.insert(target_index, moved_id)

        for layer, ordered_id in enumerate(ordered_ids):
            payload = self._find_stacker_payload(ordered_id)
            if payload:
                payload["layer"] = layer

        self._apply_stacker_layers_to_items()
        self._refresh_stackers_panel(selected_id=stacker_id)
        self.graph_manager.save_state("Reorder stacker layer")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage("Stacker layer updated")

    def _add_stacker_item(self, payload: dict):
        stacker_item = StackerItem(payload)
        stacker_item.dragged_delta.connect(self._on_stacker_dragged_delta)
        stacker_item.moved.connect(self._on_stacker_moved)
        stacker_item.resized.connect(self._on_stacker_resized)
        stacker_item.edit_requested.connect(self._edit_stacker_by_id)
        stacker_item.delete_requested.connect(self._delete_stacker_by_id)
        stacker_item.node_creation_requested.connect(self.canvas_widget.create_node_at_position)
        stacker_item.stacker_creation_requested.connect(self.toggle_stacker_creation_mode)
        stacker_item.delete_selected_requested.connect(self.delete_selected_scene_items)
        try:
            layer = int(payload.get("layer", 0))
        except (TypeError, ValueError):
            layer = 0
        stacker_item.setZValue(self._stacker_z_for_layer(layer))
        self.canvas_widget.scene.addItem(stacker_item)
        self.stacker_items[stacker_item.stacker_id] = stacker_item

    def load_stackers_from_metadata(self):
        self._ensure_stacker_metadata()
        self.stacker_items.clear()
        self._normalize_stacker_layers()
        payloads = sorted(
            [
                payload
                for payload in self.graph_manager.graph_data.metadata.get("stackers", [])
                if isinstance(payload, dict)
            ],
            key=lambda payload: int(payload.get("layer", 0)),
        )
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            if not payload.get("id"):
                payload["id"] = self._next_stacker_id()
            self._add_stacker_item(payload)
        self._refresh_stackers_panel()

    def create_stacker_from_panel(self, payload: dict):
        self._ensure_stacker_metadata()
        layer = self._next_stacker_layer()

        width = float(payload.get("width", 360))
        height = float(payload.get("height", 220))
        x = payload.get("x")
        y = payload.get("y")

        if x is None or y is None:
            view_center = self.canvas_widget.mapToScene(self.canvas_widget.viewport().rect().center())
            x = float(view_center.x() - width / 2.0)
            y = float(view_center.y() - height / 2.0)

        stacker_payload = {
            "id": self._next_stacker_id(),
            "name": str(payload.get("name", "New Stacker")).strip() or "New Stacker",
            "type": str(payload.get("type", "")).strip(),
            "color": str(payload.get("color", "#7FB3D5")).strip() or "#7FB3D5",
            "width": width,
            "height": height,
            "x": float(x),
            "y": float(y),
            "layer": layer,
        }

        self.graph_manager.graph_data.metadata["stackers"].append(stacker_payload)
        self._add_stacker_item(stacker_payload)
        created_item = self.stacker_items.get(stacker_payload["id"])
        if created_item:
            created_item.setSelected(True)
        self._refresh_stackers_panel(selected_id=stacker_payload["id"])
        self.graph_manager.save_state("Add stacker")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage(f"Created stacker: {stacker_payload['name']}")

    def toggle_stacker_creation_mode(self):
        if self.canvas_widget.stacker_selection_mode:
            self.canvas_widget.cancel_stacker_selection()
            return

        self._clear_pending_stacker_preview()
        self.canvas_widget.start_stacker_selection()
        self.stackers_panel.set_selection_mode(True)
        self.statusBar().showMessage("Drag on the canvas to create a new stacker")

    def on_stacker_area_selected(self, rect: QRectF):
        self.stackers_panel.set_selection_mode(False)
        self._show_pending_stacker_preview(rect)

        dialog = StackerDetailsDialog(self, default_color="#5DADE2")
        if not dialog.exec():
            self._clear_pending_stacker_preview()
            self.statusBar().showMessage("Stacker creation cancelled")
            return

        payload = dialog.get_payload()
        payload.update(
            {
                "type": "",
                "width": float(rect.width()),
                "height": float(rect.height()),
                "x": float(rect.x()),
                "y": float(rect.y()),
            }
        )
        self.create_stacker_from_panel(payload)
        self._clear_pending_stacker_preview()

    def on_stacker_selection_cancelled(self):
        self.stackers_panel.set_selection_mode(False)
        self._clear_pending_stacker_preview()
        self.statusBar().showMessage("Stacker creation cancelled")

    def _show_pending_stacker_preview(self, rect: QRectF):
        self._clear_pending_stacker_preview()
        preview = QGraphicsRectItem(rect)
        preview.setBrush(QColor(135, 188, 202, 90))
        preview_pen = QPen(QColor(135, 188, 202, 220), 1.2, Qt.PenStyle.DashLine)
        preview_pen.setDashPattern([6, 4])
        preview.setPen(preview_pen)
        preview.setZValue(-11.5)
        self.canvas_widget.scene.addItem(preview)
        self.pending_stacker_preview_item = preview

    def _clear_pending_stacker_preview(self):
        if self.pending_stacker_preview_item is None:
            return
        try:
            self.canvas_widget.scene.removeItem(self.pending_stacker_preview_item)
        except Exception:
            pass
        self.pending_stacker_preview_item = None

    def _on_stacker_moved(self, stacker_id: str, position: QPointF):
        payload = self._find_stacker_payload(stacker_id)
        if not payload:
            return
        if self._applying_stacker_cascade:
            return

        old_x = float(payload.get("x", 0.0))
        old_y = float(payload.get("y", 0.0))
        if abs(old_x - position.x()) < 0.01 and abs(old_y - position.y()) < 0.01:
            return

        payload["x"] = float(position.x())
        payload["y"] = float(position.y())
        context = self._active_stacker_drag_contexts.pop(stacker_id, None)
        if context is None:
            self.graph_manager.save_state("Move stacker")
        self.update_undo_redo_buttons()

    def _on_stacker_dragged_delta(self, stacker_id: str, delta: QPointF):
        if self._applying_stacker_cascade:
            return
        if abs(delta.x()) < 0.01 and abs(delta.y()) < 0.01:
            return

        context = self._active_stacker_drag_contexts.get(stacker_id)
        if context is None:
            source_payload = self._find_stacker_payload(stacker_id)
            if not source_payload:
                return
            source_rect = QRectF(
                float(source_payload.get("x", 0.0)),
                float(source_payload.get("y", 0.0)),
                float(source_payload.get("width", 0.0)),
                float(source_payload.get("height", 0.0)),
            )
            tracked_items = []
            for item in self.canvas_widget.scene.items():
                if isinstance(item, StackerItem):
                    if item.stacker_id == stacker_id:
                        continue
                    child_payload = self._find_stacker_payload(item.stacker_id)
                    if not child_payload:
                        continue
                    child_rect = QRectF(
                        float(child_payload.get("x", 0.0)),
                        float(child_payload.get("y", 0.0)),
                        float(child_payload.get("width", 0.0)),
                        float(child_payload.get("height", 0.0)),
                    )
                    if source_rect.contains(child_rect):
                        tracked_items.append(item)
                elif isinstance(item, NodeWidget):
                    node_rect = item.sceneBoundingRect().adjusted(1.0, 1.0, -1.0, -1.0)
                    if source_rect.contains(node_rect):
                        tracked_items.append(item)

            self.graph_manager.save_state("Move stacker")
            context = {"items": tracked_items}
            self._active_stacker_drag_contexts[stacker_id] = context

        if not context.get("items"):
            return

        self._applying_stacker_cascade = True
        try:
            for item in list(context["items"]):
                if not item.scene():
                    continue
                item.setPos(item.pos() + delta)
                if isinstance(item, StackerItem):
                    child_payload = self._find_stacker_payload(item.stacker_id)
                    if child_payload:
                        child_payload["x"] = float(item.scenePos().x())
                        child_payload["y"] = float(item.scenePos().y())
        finally:
            self._applying_stacker_cascade = False

    def _on_stacker_resized(self, stacker_id: str, width: float, height: float):
        payload = self._find_stacker_payload(stacker_id)
        if not payload:
            return

        old_width = float(payload.get("width", 0.0))
        old_height = float(payload.get("height", 0.0))
        if abs(old_width - width) < 0.01 and abs(old_height - height) < 0.01:
            return

        payload["width"] = float(width)
        payload["height"] = float(height)
        self.graph_manager.save_state("Resize stacker")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage(f"Resized stacker to {int(width)}x{int(height)}")

    def delete_selected_stacker(self):
        scene = self._safe_canvas_scene()
        if scene is None:
            return

        try:
            selected_stackers = [item for item in scene.selectedItems() if isinstance(item, StackerItem)]
        except RuntimeError:
            return
        if not selected_stackers:
            self.statusBar().showMessage("Select a stacker to delete")
            return
        self._delete_stacker_by_id(selected_stackers[0].stacker_id)

    def edit_selected_stacker(self):
        stacker_id = self._selected_stacker_id_from_scene()
        if not stacker_id:
            self.statusBar().showMessage("Select a stacker to edit")
            return
        self._edit_stacker_by_id(stacker_id)

    def _edit_stacker_by_id(self, stacker_id: str):
        payload = self._find_stacker_payload(stacker_id)
        stacker_item = self.stacker_items.get(stacker_id)
        if not payload or not stacker_item:
            return

        current_name = str(payload.get("name", "Stacker")).strip() or "Stacker"
        current_color = str(payload.get("color", "#5DADE2")).strip() or "#5DADE2"

        dialog = StackerDetailsDialog(
            self,
            default_name=current_name,
            default_color=current_color,
        )
        dialog.setWindowTitle("Edit Stacker")
        if not dialog.exec():
            return

        data = dialog.get_payload()
        new_name = str(data.get("name", current_name)).strip() or current_name
        new_color = str(data.get("color", current_color)).strip() or current_color

        if new_name == current_name and new_color.upper() == current_color.upper():
            return

        payload["name"] = new_name
        payload["color"] = new_color
        stacker_item.name = new_name
        stacker_item.color_hex = new_color
        stacker_item.update()
        self._refresh_stackers_panel(selected_id=stacker_id)
        self.graph_manager.save_state("Edit stacker")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage(f"Updated stacker: {new_name}")

    def _delete_stacker_by_id(
        self,
        stacker_id: str,
        save_state: bool = True,
        refresh_panel: bool = True,
        show_status: bool = True,
    ) -> bool:
        payload = self._find_stacker_payload(stacker_id)
        stacker_item = self.stacker_items.get(stacker_id)
        if not payload or not stacker_item:
            return False

        self.graph_manager.graph_data.metadata["stackers"] = [
            item
            for item in self.graph_manager.graph_data.metadata.get("stackers", [])
            if str(item.get("id", "")) != stacker_id
        ]

        self.canvas_widget.scene.removeItem(stacker_item)
        del self.stacker_items[stacker_id]
        self._normalize_stacker_layers()
        self._apply_stacker_layers_to_items()
        if refresh_panel:
            self._refresh_stackers_panel()
        if save_state:
            self.graph_manager.save_state("Delete stacker")
            self.update_undo_redo_buttons()
        if show_status:
            self.statusBar().showMessage("Stacker deleted")
        return True

    def apply_project_template(self, template_config):
        if 'metadata' in template_config:
            self.graph_manager.graph_data.metadata.update(template_config['metadata'])
        
        project_title = template_config['metadata'].get('title', 'Untitled Investigation')
        self.setWindowTitle(f"BeatRooter - {project_title}")
        
        self.statusBar().showMessage(f"Started {project_title} investigation")
    
    def setup_connections(self):
        self.toolbox.node_created.connect(self.create_node)
        self.toolbox.custom_template_created.connect(self.on_custom_template_created)
        self.toolbox.node_settings_changed.connect(self.on_node_settings_changed)
        
        self.canvas_widget.node_created.connect(self.create_node_visual)
        self.canvas_widget.connection_requested.connect(self.create_connection)
        self.canvas_widget.custom_template_created.connect(self.on_custom_template_created)
        self.canvas_widget.flipper_files_dropped.connect(self.on_flipper_files_dropped)
        self.canvas_widget.tool_dropped.connect(self.create_tool_node_from_canvas)
        self.canvas_widget.stacker_creation_requested.connect(self.toggle_stacker_creation_mode)
        self.canvas_widget.delete_selected_requested.connect(self.delete_selected_scene_items)
        self.canvas_widget.stacker_selection_completed.connect(self.on_stacker_area_selected)
        self.canvas_widget.stacker_selection_cancelled.connect(self.on_stacker_selection_cancelled)
        
        self.detail_panel.node_data_updated.connect(self.on_node_updated)
        self.detail_panel.node_deleted.connect(self.on_node_deleted)

    def _apply_detail_panel_visibility(self, visible: bool):
        if not hasattr(self, "main_splitter") or not self.main_splitter:
            return

        sizes = self.main_splitter.sizes()
        if len(sizes) < 3:
            return

        if visible:
            self.detail_panel.show()
            detail_width = max(300, int(self._detail_panel_last_width or 320))
            available = max(340, sum(sizes))
            left = sizes[0]
            center = max(300, available - left - detail_width)
            self.main_splitter.setSizes([left, center, detail_width])
            return

        current_width = sizes[2]
        if current_width > 0:
            self._detail_panel_last_width = current_width

        self.detail_panel.hide()
        self.main_splitter.setSizes([sizes[0], sizes[1] + sizes[2], 0])

    def open_node_settings_dialog(self):
        if hasattr(self, 'toolbox') and self.toolbox:
            self.toolbox.configure_node_settings()

    def check_and_request_tools(self):
        """Verifica e solicita instalação de ferramentas em falta após carregar"""
        from features.tools.core.tools_downloader import ToolsDownloadManager
        
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

    def _load_accessibility_preferences(self) -> None:
        settings = QSettings('BeatRooter', 'BeatRooter')
        self._suppress_missing_tools_prompt = bool(
            settings.value('accessibility/suppress_missing_tools_prompt', False, type=bool)
        )

    def _set_suppress_missing_tools_prompt(self, suppress: bool) -> None:
        self._suppress_missing_tools_prompt = bool(suppress)
        settings = QSettings('BeatRooter', 'BeatRooter')
        settings.setValue('accessibility/suppress_missing_tools_prompt', self._suppress_missing_tools_prompt)
        if self._suppress_missing_tools_prompt:
            self.statusBar().showMessage('Missing tools prompt silenced')
        else:
            self.statusBar().showMessage('Missing tools prompt enabled')

    def _has_real_project_context(self) -> bool:
        if self.active_document_index < 0 or self.active_document_index >= len(self.documents):
            return False
        document = self.documents[self.active_document_index]
        if str(document.get("file_path") or "").strip():
            return True
        project_type = str(document.get("project_type") or "").strip()
        category = str(document.get("category") or "").strip()
        return bool(project_type and category)

    def _schedule_missing_tools_prompt_if_needed(self) -> None:
        if self._suppress_missing_tools_prompt:
            return
        if self._missing_tools_prompt_shown:
            return
        if not self._has_real_project_context():
            return
        self._missing_tools_prompt_shown = True
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(250, self.check_and_request_tools)

    def open_beat_helper(self):
        """Open BeatHelper manual finder dialog"""
        from ui.beat_helper_dialog import BeatHelperDialog
        
        dialog = BeatHelperDialog(self)
        dialog.exec()
        
        self.statusBar().showMessage("BeatHelper closed")

    def _run_diagnostic_command(self, command, timeout=8):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            output = (result.stdout or result.stderr or "").strip()
            return result.returncode, output
        except Exception as exc:
            return -1, str(exc)

    def _show_text_report_dialog(self, title, text):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(900, 620)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        text_view = QPlainTextEdit()
        text_view.setReadOnly(True)
        text_view.setPlainText(text)
        layout.addWidget(text_view)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def run_permissions_diagnostics(self):
        system_name = platform.system()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "BeatRooter Permissions Diagnostics",
            "================================",
            f"Date: {now}",
            f"System: {system_name}",
            f"User: {getpass.getuser()}",
            "",
        ]

        # Basic identity and groups
        uid = getattr(os, "getuid", lambda: -1)()
        gid = getattr(os, "getgid", lambda: -1)()
        lines.append(f"UID/GID: {uid}/{gid}")
        try:
            group_ids = getattr(os, "getgroups", lambda: [])()
            lines.append(f"Supplementary groups (ids): {group_ids}")
        except Exception as exc:
            lines.append(f"Supplementary groups: error ({exc})")

        if system_name == "Linux":
            try:
                import grp  # Linux/Unix only
                group_names = []
                for group_id in getattr(os, "getgroups", lambda: [])():
                    try:
                        group_names.append(grp.getgrgid(group_id).gr_name)
                    except KeyError:
                        continue
                if group_names:
                    lines.append(f"Supplementary groups (names): {', '.join(sorted(set(group_names)))}")
            except Exception:
                pass

        lines.append("")

        # Tool binary checks
        lines.append("Core binaries:")
        binaries = ["tshark", "dumpcap", "nmap", "masscan", "sqlmap", "gobuster", "exiftool"]
        for binary in binaries:
            path = shutil.which(binary)
            if not path:
                lines.append(f"- {binary}: NOT FOUND in PATH")
                continue
            executable = os.access(path, os.X_OK)
            lines.append(f"- {binary}: {path} (executable={executable})")

        lines.append("")

        # Linux-specific capture permission checks (most common blocker)
        recommendations = []
        if system_name == "Linux":
            dumpcap_path = shutil.which("dumpcap")
            tshark_path = shutil.which("tshark")

            lines.append("Linux capture permission checks:")
            if not dumpcap_path:
                lines.append("- dumpcap: not found")
                recommendations.append("Install wireshark-cli (or equivalent package providing dumpcap).")
            else:
                try:
                    st = os.stat(dumpcap_path)
                    mode = stat.S_IMODE(st.st_mode)
                    lines.append(f"- dumpcap owner uid/gid: {st.st_uid}/{st.st_gid}")
                    lines.append(f"- dumpcap mode: {oct(mode)}")
                except Exception as exc:
                    lines.append(f"- dumpcap stat failed: {exc}")

                cap_bin = shutil.which("getcap")
                if cap_bin:
                    rc, cap_out = self._run_diagnostic_command([cap_bin, dumpcap_path], timeout=5)
                    lines.append(f"- getcap dumpcap: {cap_out if cap_out else '(no capabilities shown)'}")
                    if "cap_net_admin" not in cap_out or "cap_net_raw" not in cap_out:
                        recommendations.append(
                            "Grant dumpcap capabilities: sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap"
                        )
                else:
                    lines.append("- getcap: not found")
                    recommendations.append("Install libcap utilities (getcap/setcap) for capability checks.")

                rc, iface_out = self._run_diagnostic_command(["dumpcap", "-D"], timeout=8)
                lines.append(f"- dumpcap -D return code: {rc}")
                if iface_out:
                    lines.append(f"- dumpcap -D output (first lines): {iface_out.splitlines()[0]}")
                if rc != 0:
                    recommendations.append(
                        "dumpcap cannot list interfaces for current user. Add user to wireshark group and relogin."
                    )

            if tshark_path:
                rc, tshark_out = self._run_diagnostic_command(["tshark", "-D"], timeout=8)
                lines.append(f"- tshark -D return code: {rc}")
                if tshark_out:
                    lines.append(f"- tshark -D output (first lines): {tshark_out.splitlines()[0]}")
                if rc != 0:
                    recommendations.append("tshark failed to list interfaces. Check dumpcap permissions.")

            lines.append("")
            lines.append("Quick fix commands (Linux):")
            lines.append("sudo groupadd -f wireshark")
            lines.append("sudo usermod -aG wireshark \"$USER\"")
            lines.append("sudo chgrp wireshark /usr/bin/dumpcap")
            lines.append("sudo chmod 750 /usr/bin/dumpcap")
            lines.append("sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap")
            lines.append("Then logout/login.")
        else:
            lines.append("Non-Linux OS detected: Linux-specific dumpcap capability checks were skipped.")

        if recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for item in recommendations:
                lines.append(f"- {item}")

        report = "\n".join(lines)
        self._show_text_report_dialog("Permissions Diagnostics", report)
        self.statusBar().showMessage("Permissions diagnostics completed")

    def _register_flipper_templates(self):
        for template in FlipperWorkspaceImporter.get_default_templates():
            try:
                node_type = template.get('node_type', '')
                category_key = template.get('category', NodeFactory.CUSTOM_CATEGORY)
                category_label = template.get('category_label', '')
                if node_type.startswith('flipper_'):
                    category_key = 'flipper'
                    category_label = ''

                NodeFactory.register_custom_node_template(
                    name=template.get('name', ''),
                    node_type=node_type,
                    color=template.get('color', ''),
                    symbol=template.get('symbol', ''),
                    category=category_key,
                    category_label=category_label,
                    default_data=template.get('default_data', {}),
                    overwrite=True,
                )
            except ValueError as exc:
                print(f"Failed to register Flipper template: {exc}")

    def _add_imported_node(self, node_type: str, position: QPointF, custom_data: dict):
        node_data = NodeFactory.create_node_data(node_type, custom_data=custom_data, category=self.category)
        node = self.graph_manager.add_node(node_type, position, node_data)
        self.create_node_visual(node)
        return node

    def import_flipper_workspace(self):
        root_paths = FlipperDeviceManager.find_connected_flipper_roots()
        serial_ports = FlipperDeviceManager.find_connected_flipper_ports()
        selected_serial_port = serial_ports[0] if serial_ports else ""
        rpc_without_filesystem = bool(serial_ports) and not root_paths
        settings = QSettings('BeatRooter', 'BeatRooter')

        # Reuse last known good Flipper root to avoid prompting every time.
        if not root_paths:
            last_root_path = settings.value('flipper_last_root_path', '', type=str) or ''
            if last_root_path and os.path.isdir(last_root_path):
                root_paths = [last_root_path]
                rpc_without_filesystem = bool(serial_ports) and not FlipperDeviceManager.find_connected_flipper_roots()

        if not root_paths and serial_ports:
            busy_ports = []
            mirror_errors = []

            for serial_port in serial_ports:
                selected_serial_port = serial_port
                self.statusBar().showMessage(f'Flipper RPC detected ({serial_port}). Syncing remote storage...')
                try:
                    with FlipperSerialStorageMirror(serial_port) as mirror:
                        rpc_root = mirror.create_local_mirror()
                    self.flipper_rpc_mirror_root = rpc_root
                    root_paths = [rpc_root]
                    settings.setValue('flipper_last_root_path', rpc_root)
                    rpc_without_filesystem = False
                    break
                except FlipperSerialBusyError as exc:
                    busy_ports.append(serial_port)
                    mirror_errors.append(f"{serial_port}: {exc}")
                except FlipperSerialError as exc:
                    mirror_errors.append(f"{serial_port}: {exc}")
                    print(f"Flipper serial mirror error on {serial_port}: {exc}")
                except Exception as exc:
                    mirror_errors.append(f"{serial_port}: {exc}")
                    print(f"Unexpected Flipper RPC mirror error on {serial_port}: {exc}")

            if not root_paths and busy_ports:
                QMessageBox.warning(
                    self,
                    'Flipper Device Busy',
                    "A porta serial do Flipper está ocupada (normalmente pelo qFlipper).\n"
                    f"Porta(s): {', '.join(busy_ports[:4])}\n"
                    "Fecha o qFlipper e tenta novamente para browsing automático sem pasta manual.",
                )
            elif not root_paths and mirror_errors:
                preview = "\n".join(mirror_errors[:3])
                QMessageBox.warning(
                    self,
                    'Flipper RPC Error',
                    "O Flipper foi detetado por serial, mas o mirror RPC falhou.\n"
                    f"{preview}\n\n"
                    "Se estiveres no Windows, isto normalmente indica porta errada, bloqueada ou resposta RPC inesperada.",
                )

        if not root_paths:
            if serial_ports:
                port_preview = ", ".join(serial_ports[:3])
                reply = QMessageBox.question(
                    self,
                    'Flipper Device',
                    "Flipper detetado por porta serial/RPC, mas sem filesystem montado.\n"
                    f"Porta(s): {port_preview}\n\n"
                    "Para arrastar ficheiros, seleciona manualmente a pasta do SD card/mount.\n"
                    "Queres escolher essa pasta agora?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
            else:
                reply = QMessageBox.question(
                    self,
                    'Flipper Device',
                    'No connected Flipper filesystem was auto-detected.\n'
                    'Do you want to select a Flipper folder manually?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )

            if reply != QMessageBox.StandardButton.Yes:
                return

            manual_root = QFileDialog.getExistingDirectory(self, 'Select Flipper Root Folder')
            if not manual_root:
                return
            root_paths = [manual_root]
            settings.setValue('flipper_last_root_path', manual_root)
        else:
            # Persist the first detected/resolved root for future RPC-only sessions.
            settings.setValue('flipper_last_root_path', root_paths[0])

        if self.flipper_explorer_dialog and self.flipper_explorer_dialog.isVisible():
            self.flipper_explorer_dialog.raise_()
            self.flipper_explorer_dialog.activateWindow()
            return

        dialog = FlipperExplorerDialog(root_paths, self)
        dialog.setModal(False)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.files_import_requested.connect(self.import_selected_flipper_files)
        dialog.destroyed.connect(self._on_flipper_explorer_closed)
        dialog.show()

        self.flipper_explorer_dialog = dialog
        if rpc_without_filesystem:
            self.statusBar().showMessage(f'Flipper RPC detected ({selected_serial_port}). Using selected storage path.')
        else:
            self.statusBar().showMessage('Flipper explorer ready. Drag files to the canvas.')

    def _on_flipper_explorer_closed(self):
        self.flipper_explorer_dialog = None

    def on_flipper_files_dropped(self, file_paths: list, drop_scene_pos: QPointF, root_path: str):
        self.import_selected_flipper_files(file_paths, root_path, drop_scene_pos)

    def import_selected_flipper_files(self, file_paths: list, root_path: str = "", drop_scene_pos: QPointF = None):
        if not file_paths:
            return

        if root_path and os.path.isdir(root_path):
            QSettings('BeatRooter', 'BeatRooter').setValue('flipper_last_root_path', root_path)
        imported = []

        valid_paths = []
        seen = set()
        for file_path in file_paths:
            if not file_path or file_path in seen:
                continue
            seen.add(file_path)
            if os.path.isfile(file_path):
                valid_paths.append(file_path)

        if not valid_paths:
            return

        anchor = drop_scene_pos
        if anchor is None:
            anchor = self.canvas_widget.mapToScene(self.canvas_widget.viewport().rect().center())

        parsed_artifacts = []
        for file_path in valid_paths:
            artifact = FlipperWorkspaceImporter.parse_file(file_path, workspace_root=root_path)
            if not artifact:
                continue
            parsed_artifacts.append((file_path, artifact))

        if not parsed_artifacts:
            QMessageBox.information(self, 'Flipper Import', 'No selected files could be parsed.')
            return

        self._register_flipper_templates()

        for index, (file_path, artifact) in enumerate(parsed_artifacts):
            file_data = dict(artifact.get('data', {}))
            file_data.setdefault('title', artifact.get('display_name', os.path.basename(file_path)))
            if root_path:
                file_data.setdefault('workspace_path', root_path)
            file_data['scan_timestamp'] = datetime.now().isoformat(timespec='seconds')

            row = index // 2
            col = index % 2
            x_offset = -130 if col == 0 else 130
            y_offset = row * 155
            position = QPointF(anchor.x() + x_offset, anchor.y() + y_offset)

            node_type = artifact.get('node_type', 'flipper_file')
            self._add_imported_node(node_type, position, file_data)
            imported.append(artifact)

        self.sync_custom_node_templates_metadata()
        self.toolbox.refresh_filter_categories()
        self.toolbox.create_sections()
        self.toolbox.filter_nodes()
        self.update_undo_redo_buttons()

        module_counts = {}
        for artifact in imported:
            module_name = artifact.get('module', 'general')
            module_counts[module_name] = module_counts.get(module_name, 0) + 1

        module_summary = ', '.join(
            f"{FlipperWorkspaceImporter.get_module_label(module)}: {module_counts.get(module, 0)}"
            for module in FlipperWorkspaceImporter.sorted_modules(module_counts.keys())
        )

        self.statusBar().showMessage(
            f"Imported {len(imported)} Flipper file(s): {module_summary or 'general'}"
        )

    def toggle_external_tools(self):
        if hasattr(self, 'detail_panel'):
            self.detail_panel.show_tools_tab()
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

    def _bind_node_widget_signals(self, node_widget):
        node_widget.node_updated.connect(self.on_node_selected)
        node_widget.connection_started.connect(self.start_connection)
        node_widget.node_deleted.connect(self.on_node_deleted)
        node_widget.delete_selected_requested.connect(self.delete_selected_scene_items)
        node_widget.tool_run_requested.connect(self.on_tool_node_run_requested)
        node_widget.tool_edit_requested.connect(self.on_tool_node_edit_requested)
        node_widget.tool_output_requested.connect(self.show_tool_node_output)
        node_widget.output_details_requested.connect(self.show_node_output_details)

    def show_node_output_details(self, node):
        if ToolNodeService.is_tool_node(node):
            self.show_tool_node_output(node)
            return

        lines = []
        for key, value in (node.data or {}).items():
            if key in {"notes"}:
                continue
            if isinstance(value, dict):
                rendered = json.dumps(value, ensure_ascii=False, indent=2)
            elif isinstance(value, list):
                rendered = ", ".join(str(item) for item in value)
            else:
                rendered = str(value)
            if rendered.strip():
                lines.append(f"{key.replace('_', ' ').title()}: {rendered}")

        output_text = "\n".join(lines).strip()
        if not output_text:
            output_text = "No detailed output available."

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{NodeFactory.get_node_name(node.type, self.category)} Output Details")
        dialog.resize(760, 520)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        output_view = QPlainTextEdit()
        output_view.setReadOnly(True)
        output_view.setPlainText(output_text)
        layout.addWidget(output_view)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    def _sanitize_tool_output(self, text):
        if not text:
            return ""

        ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        cleaned = ansi_escape.sub("", str(text))
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        return cleaned

    def _append_tool_output_cache(self, node_id, text):
        cleaned_text = self._sanitize_tool_output(text)
        if not cleaned_text:
            return

        current = self.tool_output_cache.get(node_id, "")
        merged = current + cleaned_text
        max_chars = 500000
        if len(merged) > max_chars:
            merged = merged[-max_chars:]
        self.tool_output_cache[node_id] = merged

    def _build_tool_output_preview(self, text):
        cleaned_text = self._sanitize_tool_output(text)
        if not cleaned_text.strip():
            return ""

        lines = []
        for raw_line in cleaned_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("Executing:"):
                continue
            if set(line) == {"-"}:
                continue
            lines.append(line)

        if not lines:
            return ""

        preview = "\n".join(lines[:10])
        if len(preview) > 1400:
            preview = preview[:1400].rstrip() + "..."
        return preview

    def _stop_all_tool_threads(self):
        for thread in list(self.tool_run_threads.values()):
            if thread and thread.isRunning():
                thread.terminate()
                thread.wait(1000)
            if thread:
                thread.deleteLater()
        self.tool_run_threads.clear()
        self.tool_output_cache.clear()

    def refresh_tool_nodes(self, update_widgets=True):
        refreshed_ids = []
        for node in self.graph_manager.graph_data.nodes.values():
            if not ToolNodeService.is_tool_node(node):
                continue
            ToolNodeService.refresh_tool_node_state(self.graph_manager, node)
            refreshed_ids.append(node.id)

        if not update_widgets:
            return refreshed_ids

        for node_id in refreshed_ids:
            if node_id in self.node_widgets:
                self.node_widgets[node_id].update_display()

        return refreshed_ids

    def create_tool_node_from_canvas(self, tool_name, scene_pos):
        tool_name = str(tool_name or "").strip().lower()
        if tool_name not in ToolNodeService.list_tool_names():
            QMessageBox.warning(self, "Tool Node", f"Unknown tool: {tool_name}")
            return

        node_data = ToolNodeService.create_tool_node_data(tool_name)
        node = self.graph_manager.add_node(ToolNodeService.TOOL_NODE_TYPE, scene_pos, node_data)
        ToolNodeService.refresh_tool_node_state(self.graph_manager, node)
        self.create_node_visual(node)
        self.update_undo_redo_buttons()
        self.statusBar().showMessage(f"Created {ToolNodeService.get_tool_display_name(tool_name)} tool node")

    def refresh_canvas_from_graph(self):
        self.canvas_widget.scene.clear()
        self.node_widgets.clear()
        self.edge_items.clear()
        self.stacker_items.clear()
        self.load_stackers_from_metadata()
        
        for node in self.graph_manager.graph_data.nodes.values():
            node_widget = NodeWidget(node, self.category, self.project_type)
            self.canvas_widget.add_node_widget(node_widget)
            self._bind_node_widget_signals(node_widget)
            self.node_widgets[node.id] = node_widget
        
        for edge in self.graph_manager.graph_data.edges.values():
            self.draw_connection(edge)

        self.refresh_tool_nodes()
        
        if (self.detail_panel.current_node and 
            self.detail_panel.current_node.id not in self.graph_manager.graph_data.nodes):
            self.detail_panel.clear_panel()

    def create_node_visual(self, node):
        from features.beatroot_canvas.core import NodeFactory
        node_category = NodeFactory.find_node_category(node.type)
        
        if not node_category:
            node_category = self.category
            
        node_widget = NodeWidget(node, node_category, self.project_type)
        self.canvas_widget.add_node_widget(node_widget)
        self._bind_node_widget_signals(node_widget)
        self.node_widgets[node.id] = node_widget

        if ToolNodeService.is_tool_node(node):
            ToolNodeService.refresh_tool_node_state(self.graph_manager, node)
            node_widget.update_display()
        
        self.statusBar().showMessage(f"Created {node.type} node at position")

    def create_node(self, node_type):
        from PyQt6.QtCore import QPointF
        
        view_center = self.canvas_widget.mapToScene(
            self.canvas_widget.viewport().rect().center()
        )

        node_data = NodeFactory.create_node_data(node_type, category=self.category)
        node = self.graph_manager.add_node(node_type, view_center, node_data)
        
        node_widget = NodeWidget(node, self.category, self.project_type)
        self.canvas_widget.add_node_widget(node_widget)
        self._bind_node_widget_signals(node_widget)
        self.node_widgets[node.id] = node_widget
        
        self.statusBar().showMessage(f"Created {node_type} node")
        self.sync_custom_node_templates_metadata()

        if node_type == 'screenshot':
            node_data.update({
                'filename': '',
                'file_path': '',
                'file_size': '',
                'dimensions': '',
                'format': '',
                'metadata': {}
            })

    def _refresh_selected_node_panel(self, node):
        if self.detail_panel.current_node and self.detail_panel.current_node.id == node.id:
            self.detail_panel.display_node(node)

    def on_tool_node_edit_requested(self, node):
        ToolNodeService.refresh_tool_node_state(self.graph_manager, node)
        dialog = ToolNodeConfigDialog(node, self)
        if not dialog.exec():
            return

        payload = dialog.get_payload()
        changed = False
        for key, value in payload.items():
            if node.data.get(key) == value:
                continue
            node.data[key] = value
            changed = True

        ToolNodeService.refresh_tool_node_state(self.graph_manager, node)

        if node.id in self.node_widgets:
            self.node_widgets[node.id].update_display()
        self._refresh_selected_node_panel(node)

        if changed:
            self.graph_manager.save_state(f"Configure {ToolNodeService.get_tool_display_name(node.data.get('tool_name', 'tool'))}")
            self.update_undo_redo_buttons()

        self.statusBar().showMessage(f"Updated {ToolNodeService.get_tool_display_name(node.data.get('tool_name', 'tool'))} tool node")

    def show_tool_node_output(self, node):
        output_text = self.tool_output_cache.get(node.id, "")
        if not output_text:
            output_text = str(
                node.data.get("last_output_preview", "")
                or node.data.get("last_output", "")
                or node.data.get("last_error", "")
                or ""
            )
        dialog = ToolNodeOutputDialog(node, output_text=output_text, parent=self)
        dialog.exec()

    def on_tool_node_run_requested(self, node):
        tool_name = str(node.data.get("tool_name", "") or "").strip().lower()
        if not tool_name:
            QMessageBox.warning(self, "Tool Node", "This tool node is missing its tool name.")
            return

        thread = self.tool_run_threads.get(node.id)
        if thread and thread.isRunning():
            self.statusBar().showMessage(f"{ToolNodeService.get_tool_display_name(tool_name)} is already running")
            return

        resolution = ToolNodeService.refresh_tool_node_state(self.graph_manager, node)
        target = str(resolution.get("target", "") or "").strip()
        if ToolNodeService.tool_requires_target(tool_name) and not target:
            if node.id in self.node_widgets:
                self.node_widgets[node.id].update_display()
            QMessageBox.warning(self, "Tool Node", resolution.get("reason", "Connect a compatible node or define Manual Target."))
            return

        tool_manager = self.tools_integration.tools_manager
        if not tool_manager:
            QMessageBox.warning(self, "Tool Node", "Tools manager is not available.")
            return

        custom_command = str(node.data.get("custom_command", "") or "").strip()
        if custom_command:
            command_parts = shlex.split(custom_command, posix=not sys.platform.startswith("win"))
        else:
            options = str(node.data.get("options", "") or "").strip()
            command_parts = tool_manager.get_command_for_tool(tool_name, target, options)

        if not command_parts:
            QMessageBox.warning(self, "Tool Node", "Could not build a command for this tool node.")
            return

        use_wsl = False
        if (
            sys.platform.startswith("win")
            and tool_name
            and tool_manager.should_use_wsl(tool_name)
        ):
            use_wsl = True
            command_parts = tool_manager.convert_to_wsl_command(command_parts, tool_name)

        from features.tools.core.tools_manager import CommandThread

        node.data["last_status"] = "running"
        node.data["last_exit_code"] = ""
        node.data["last_output"] = ""
        node.data["last_output_preview"] = ""
        node.data["last_output_size"] = 0
        node.data["last_error"] = ""
        node.data["has_output"] = False
        node.data["created_node_ids"] = []
        node.data["output_summary"] = f"Running against {target}" if target else "Running command"
        node.data["last_run_at"] = datetime.now().isoformat(timespec='seconds')
        node.data["last_command"] = " ".join(command_parts)
        self.tool_output_cache[node.id] = ""

        if node.id in self.node_widgets:
            self.node_widgets[node.id].update_display()
        self._refresh_selected_node_panel(node)

        command_thread = CommandThread(command_parts, use_wsl=use_wsl)
        command_thread.output_received.connect(lambda output, node_id=node.id: self._on_tool_node_output_received(node_id, output))
        command_thread.command_finished.connect(lambda exit_code, node_id=node.id: self._on_tool_node_command_finished(node_id, exit_code))
        command_thread.error_occurred.connect(lambda error, node_id=node.id: self._on_tool_node_command_error(node_id, error))
        self.tool_run_threads[node.id] = command_thread
        command_thread.start()

        self.statusBar().showMessage(f"Running {ToolNodeService.get_tool_display_name(tool_name)} against {target}")

    def _on_tool_node_output_received(self, node_id, output):
        node = self.graph_manager.get_node(node_id)
        if not node:
            return

        self._append_tool_output_cache(node_id, output)
        node.data["has_output"] = bool(self.tool_output_cache.get(node_id, "").strip())

    def _on_tool_node_command_error(self, node_id, error_message):
        node = self.graph_manager.get_node(node_id)
        if node:
            clean_error = self._sanitize_tool_output(error_message).strip()
            node.data["last_error"] = clean_error
            self._append_tool_output_cache(node_id, clean_error + "\n")
            node.data["has_output"] = True
        self._finalize_tool_node_run(node_id, -1)

    def _on_tool_node_command_finished(self, node_id, exit_code):
        self._finalize_tool_node_run(node_id, exit_code)

    def _finalize_tool_node_run(self, node_id, exit_code):
        command_thread = self.tool_run_threads.pop(node_id, None)
        if command_thread:
            command_thread.deleteLater()

        node = self.graph_manager.get_node(node_id)
        if not node:
            return

        tool_name = str(node.data.get("tool_name", "") or "").strip().lower()
        target = str(node.data.get("resolved_target", "") or node.data.get("manual_target", "")).strip()
        output_text = self.tool_output_cache.get(node_id, "")

        if exit_code != 0 and tool_name == "tshark":
            normalized_output = (output_text or "").lower()
            if "dumpcap in child process: permission denied" in normalized_output or "permission denied" in normalized_output:
                node.data["last_error"] = (
                    "Sem permissões para captura ao vivo com TShark.\n"
                    "Use um ficheiro .pcap/.pcapng como target, ou conceda permissões ao dumpcap "
                    "(grupo wireshark/cap_net_raw,cap_net_admin)."
                )

        created_nodes = []
        if exit_code == 0 and tool_name:
            try:
                created_nodes = self.tools_integration.tools_manager.output_parser.parse_tool_output(
                    tool_name,
                    output_text,
                    target,
                )
            except Exception as exc:
                node.data["last_error"] = self._sanitize_tool_output(str(exc))
                exit_code = -1

        preview_text = self._build_tool_output_preview(output_text or node.data.get("last_error", ""))
        node.data["last_exit_code"] = str(exit_code)
        node.data["last_output"] = ""
        node.data["last_output_preview"] = preview_text
        node.data["last_output_size"] = len(output_text)
        node.data["has_output"] = bool((output_text or node.data.get("last_error", "")).strip())

        if exit_code == 0:
            if created_nodes:
                self._position_tool_result_nodes(node, created_nodes)
                for created_node in created_nodes:
                    created_node.data["generated_by_tool_id"] = node.id
                    self.create_node_visual(created_node)
                    self._connect_tool_node_to_result(node, created_node)
            else:
                if tool_name == "tshark":
                    node.data["output_summary"] = "TShark completed with no structured entities extracted."
                else:
                    fallback_node = self._create_tool_fallback_result_node(node, output_text, exit_code)
                    if fallback_node:
                        created_nodes = [fallback_node]

            node.data["last_status"] = "success"
            node.data["created_node_ids"] = [created_node.id for created_node in created_nodes]
            if created_nodes:
                node.data["output_summary"] = ToolNodeService.summarize_created_nodes(created_nodes)
            elif not node.data.get("output_summary"):
                node.data["output_summary"] = "No result nodes created."
            self.statusBar().showMessage(
                f"{ToolNodeService.get_tool_display_name(tool_name)} completed: {node.data['output_summary']}"
            )
        else:
            node.data["last_status"] = "error"
            if not node.data.get("last_error"):
                node.data["last_error"] = f"Command finished with exit code {exit_code}"
            node.data["output_summary"] = str(node.data.get("last_error", "") or "")
            self.statusBar().showMessage(
                f"{ToolNodeService.get_tool_display_name(tool_name)} failed: {node.data['output_summary']}"
            )

        self.refresh_tool_nodes()
        if node.id in self.node_widgets:
            self.node_widgets[node.id].update_display()
        self._refresh_selected_node_panel(node)
        self.graph_manager.save_state(f"Run {ToolNodeService.get_tool_display_name(tool_name)} tool")
        self.update_undo_redo_buttons()

    def _position_tool_result_nodes(self, tool_node, created_nodes):
        if not created_nodes:
            return

        x_values = [created_node.position.x() for created_node in created_nodes]
        y_values = [created_node.position.y() for created_node in created_nodes]
        min_x = min(x_values)
        min_y = min(y_values)
        max_y = max(y_values)

        target_x = tool_node.position.x() + 210
        target_center_y = tool_node.position.y()
        current_center_y = (min_y + max_y) / 2
        delta_x = target_x - min_x
        delta_y = target_center_y - current_center_y

        for created_node in created_nodes:
            created_node.position = QPointF(
                created_node.position.x() + delta_x,
                created_node.position.y() + delta_y,
            )

    def _create_tool_fallback_result_node(self, tool_node, output_text, exit_code):
        tool_name = str(tool_node.data.get("tool_name", "") or "").strip().lower()
        result_type = ToolNodeService.get_tool_spec(tool_name).get("result_node_type", "note")
        custom_data = ToolNodeService.build_fallback_result_data(
            tool_name,
            str(tool_node.data.get("resolved_target", "") or tool_node.data.get("manual_target", "")),
            output_text,
            exit_code,
        )

        node_data = NodeFactory.create_node_data(result_type, custom_data=custom_data, category=self.category)
        fallback_position = QPointF(tool_node.position.x() + 210, tool_node.position.y())
        result_node = self.graph_manager.add_node(result_type, fallback_position, node_data)
        result_node.data["generated_by_tool_id"] = tool_node.id
        self.create_node_visual(result_node)
        self._connect_tool_node_to_result(tool_node, result_node)
        return result_node

    def _connect_tool_node_to_result(self, tool_node, result_node):
        try:
            edge = self.graph_manager.connect_nodes(tool_node.id, result_node.id, "")
        except ValueError:
            return
        self.draw_connection(edge)

    def on_node_selected(self, node):
        self.detail_panel.display_node(node)
        self.statusBar().showMessage(f"Selected {node.type} node: {node.id}")

    def on_custom_template_created(self, node_type):
        self.sync_custom_node_templates_metadata()
        self.toolbox.refresh_filter_categories()
        self.toolbox.create_sections()
        self.toolbox.filter_nodes()
        self.statusBar().showMessage(f"Registered custom node template: {NodeFactory.get_node_name(node_type)}")

    def on_node_settings_changed(self):
        self.sync_custom_node_templates_metadata()
        self.toolbox.refresh_filter_categories()
        self.toolbox.create_sections()
        self.toolbox.filter_nodes()
        self.statusBar().showMessage("Node settings updated")
    
    def on_node_updated(self, node):
        if node.id in self.node_widgets:
            self.node_widgets[node.id].update_display()
            if hasattr(self, 'edge_items'):
                for edge_item in self.edge_items.values():
                    if (edge_item.source_node.node.id == node.id or 
                        edge_item.target_node.node.id == node.id):
                        edge_item.update_path()

        self.refresh_tool_nodes()

        self.graph_manager.save_state(f"Update {node.type} node")
        self.update_undo_redo_buttons()
        
        self.statusBar().showMessage(f"Updated {node.type} node")

    def _delete_node_by_id(
        self,
        node_id: str,
        save_state: bool = True,
        refresh_ui: bool = True,
        show_status: bool = True,
    ) -> bool:
        node = self.graph_manager.get_node(node_id)
        if not node:
            return False

        running_thread = self.tool_run_threads.pop(node.id, None)
        self.tool_output_cache.pop(node.id, None)
        if running_thread and running_thread.isRunning():
            running_thread.terminate()
            running_thread.wait(1500)
            running_thread.deleteLater()

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

        if refresh_ui:
            self.refresh_tool_nodes()
            self.sync_custom_node_templates_metadata()

        if save_state:
            self.graph_manager.save_state("Delete node")
            self.update_undo_redo_buttons()

        if show_status:
            self.statusBar().showMessage(f"Deleted {node.type} node and its connections")

        return True

    def _collect_selected_scene_ids(self):
        node_ids = []
        stacker_ids = []
        scene = self._safe_canvas_scene()
        if scene is None:
            return node_ids, stacker_ids

        try:
            for item in scene.selectedItems():
                if isinstance(item, NodeWidget):
                    node_id = str(item.node.id)
                    if node_id not in node_ids:
                        node_ids.append(node_id)
                elif isinstance(item, StackerItem):
                    stacker_id = str(item.stacker_id)
                    if stacker_id not in stacker_ids:
                        stacker_ids.append(stacker_id)
        except RuntimeError:
            return [], []
        return node_ids, stacker_ids

    def delete_selected_scene_items(self):
        node_ids, stacker_ids = self._collect_selected_scene_ids()
        total = len(node_ids) + len(stacker_ids)
        if total == 0:
            self.statusBar().showMessage("No selected items to delete")
            return

        if total == 1:
            if node_ids:
                node = self.graph_manager.get_node(node_ids[0])
                if node:
                    self.on_node_deleted(node)
                return
            self._delete_stacker_by_id(stacker_ids[0])
            return

        details = []
        if node_ids:
            details.append(f"{len(node_ids)} node(s)")
        if stacker_ids:
            details.append(f"{len(stacker_ids)} stacker(s)")
        label = " and ".join(details)

        reply = QMessageBox.question(
            self,
            "Delete Selected",
            f"Are you sure you want to delete {total} selected items ({label})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted_nodes = 0
        for node_id in node_ids:
            if self._delete_node_by_id(node_id, save_state=False, refresh_ui=False, show_status=False):
                deleted_nodes += 1

        deleted_stackers = 0
        for stacker_id in stacker_ids:
            if self._delete_stacker_by_id(
                stacker_id,
                save_state=False,
                refresh_panel=False,
                show_status=False,
            ):
                deleted_stackers += 1

        if deleted_stackers:
            self._refresh_stackers_panel()
        if deleted_nodes or deleted_stackers:
            self.refresh_tool_nodes()
            self.sync_custom_node_templates_metadata()
            self.graph_manager.save_state("Delete selected items")
            self.update_undo_redo_buttons()
            self.statusBar().showMessage(
                f"Deleted {deleted_nodes} node(s) and {deleted_stackers} stacker(s)"
            )

    def on_node_deleted(self, node):
        print(f"Deleting node from detail panel: {node.id}")
        
        reply = QMessageBox.question(self, 'Delete Node', 
                                   f'Are you sure you want to delete this {node.type} node?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_node_by_id(node.id)

    
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
            self.refresh_tool_nodes()
            
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

        dialog = ProjectSelectionDialog(self)
        
        def on_project_selected(project_type, category):
            graph_data = self.graph_manager.graph_data.__class__()
            tab_index = self._append_document_tab(
                graph_data=graph_data,
                project_type=project_type,
                category=category,
                file_path=None,
                dirty=False,
                activate=True,
            )
            self.statusBar().showMessage(f"New investigation tab created: {project_type} / {category}")
            self._update_document_tab_label(tab_index)
        
        dialog.project_selected.connect(on_project_selected)
        dialog.exec()

    def has_unsaved_changes(self):
        if self.active_document_index >= 0 and self.active_document_index < len(self.documents):
            return bool(self.documents[self.active_document_index].get("dirty"))
        return False

    def get_project_title(self):
        if hasattr(self, 'project_type') and hasattr(self, 'category') and self.project_type and self.category:
            project_names = {
                'blueteam': 'Blue Team',
                'soc_team': 'SOC Operations', 
                'redteam': 'Red Team'
            }
            project_name = project_names.get(self.project_type, self.project_type.title())
            category_name = NodeFactory.get_category_display_name(self.category)
            
            return f"{project_name} - {category_name}"
        return "BeatRooter - New Investigation"

    def load_graph_data(self, graph_data):
        self._stop_all_tool_threads()
        NodeFactory.load_custom_node_templates(graph_data.metadata.get('custom_node_templates', {}))
        NodeFactory.load_node_template_settings(graph_data.metadata.get('node_template_settings', {}))
        self.graph_manager.clear_graph()
        self.graph_manager.graph_data.metadata = dict(graph_data.metadata)
        self._ensure_stacker_metadata()
        self.canvas_widget.scene.clear()
        self.node_widgets.clear()
        self.edge_items.clear()
        self.stacker_items.clear()

        self.load_stackers_from_metadata()
        
        for node in graph_data.nodes.values():
            self.graph_manager.graph_data.nodes[node.id] = node
            node_widget = NodeWidget(node, self.category, self.project_type)
            self.canvas_widget.add_node_widget(node_widget)
            self._bind_node_widget_signals(node_widget)
            self.node_widgets[node.id] = node_widget
        
        for edge in graph_data.edges.values():
            self.graph_manager.graph_data.edges[edge.id] = edge
            self.draw_connection(edge)

        node_indices = [
            int(str(node_id).split("_")[-1])
            for node_id in self.graph_manager.graph_data.nodes.keys()
            if str(node_id).startswith("node_") and str(node_id).split("_")[-1].isdigit()
        ]
        edge_indices = [
            int(str(edge_id).split("_")[-1])
            for edge_id in self.graph_manager.graph_data.edges.keys()
            if str(edge_id).startswith("edge_") and str(edge_id).split("_")[-1].isdigit()
        ]
        self.graph_manager.node_counter = (max(node_indices) + 1) if node_indices else 0
        self.graph_manager.edge_counter = (max(edge_indices) + 1) if edge_indices else 0

        self.refresh_tool_nodes()
        self.toolbox.refresh_filter_categories()
        self.toolbox.create_sections()
        self.toolbox.filter_nodes()
    
    def open_investigation(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open Investigation', '', 
            'BeatRooter Tree Files (*.brt);;JSON Files (*.json);;All Files (*)'
        )
        
        if filename:
            try:
                previous_current_file = self.storage_manager.current_file
                graph_data = self.storage_manager.load_graph(filename)
                # Keep the current tab metadata stable while activating the new tab.
                # The target file will be applied to the opened tab in _load_document_into_canvas().
                self.storage_manager.current_file = previous_current_file
                tab_index = self._append_document_tab(
                    graph_data=graph_data,
                    project_type=self.project_type,
                    category=self.category,
                    file_path=filename,
                    dirty=False,
                    activate=True,
                )
                self.sync_custom_node_templates_metadata()
                self._update_document_tab_label(tab_index)
                self.statusBar().showMessage(f"Opened investigation: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {e}")
                print(f"Error loading file: {e}")

    
    def save_investigation(self):
        self.sync_custom_node_templates_metadata()
        if self.active_document_index < 0 or self.active_document_index >= len(self.documents):
            return False
        self._snapshot_active_document()
        success = self._save_document_snapshot(self.active_document_index)
        if success:
            self.statusBar().showMessage("Investigation saved")
        return success
    
    def save_investigation_as(self):
        self.sync_custom_node_templates_metadata()
        if self.active_document_index < 0 or self.active_document_index >= len(self.documents):
            return False
        self._snapshot_active_document()
        success = self._save_document_snapshot(self.active_document_index, force_save_as=True)
        if success:
            active_doc = self.documents[self.active_document_index]
            self.statusBar().showMessage(f"Investigation saved as: {active_doc.get('file_path')}")
        return success
    
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
        self.sync_custom_node_templates_metadata()
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

    def toggle_fullscreen(self, enabled: bool):
        if enabled:
            self.showFullScreen()
        else:
            self.showNormal()

    def zoom_in(self):
        self.canvas_widget.zoom_in()
    
    def zoom_out(self):
        self.canvas_widget.zoom_out()
    
    def reset_zoom(self):
        self.canvas_widget.reset_zoom()
    
    def clear_canvas(self):
        reply = QMessageBox.question(self, 'Clear Canvas', 
                                   'Are you sure you want to clear the entire canvas?',
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self._stop_all_tool_threads()
            self.graph_manager.clear_graph()
            self.canvas_widget.scene.clear()
            self.node_widgets.clear()
            self.stacker_items.clear()
            self.detail_panel.clear_panel()
            self._reset_stackers_metadata()
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
        try:
            if getattr(self, "canvas_widget", None) is not None:
                scene = getattr(self.canvas_widget, "scene", None)
                if scene is not None and not sip.isdeleted(scene):
                    try:
                        scene.selectionChanged.disconnect(self._on_scene_selection_changed)
                    except (TypeError, RuntimeError):
                        pass
        except Exception:
            pass

        self._snapshot_active_document()
        dirty_docs = [doc for doc in self.documents if doc.get("dirty")]
        if dirty_docs:
            message = QMessageBox(self)
            message.setIcon(QMessageBox.Icon.Question)
            message.setWindowTitle("Exit BeatRooter")
            message.setText(f"You have {len(dirty_docs)} unsaved tab(s).")
            message.setInformativeText("Do you want to save changes before exiting?")
            save_all_btn = message.addButton("Save All", QMessageBox.ButtonRole.AcceptRole)
            discard_btn = message.addButton("Don't Save", QMessageBox.ButtonRole.DestructiveRole)
            cancel_btn = message.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            message.setDefaultButton(save_all_btn)
            message.exec()

            clicked = message.clickedButton()
            if clicked == cancel_btn:
                event.ignore()
                return
            if clicked == save_all_btn:
                dirty_indexes = [idx for idx, doc in enumerate(self.documents) if doc.get("dirty")]
                for index in dirty_indexes:
                    if not self._save_document_snapshot(index):
                        event.ignore()
                        return
            elif clicked != discard_btn:
                event.ignore()
                return
        self._stop_all_tool_threads()
        event.accept()

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "fullscreen_action"):
            is_fullscreen = self.isFullScreen()
            if self.fullscreen_action.isChecked() != is_fullscreen:
                self.fullscreen_action.blockSignals(True)
                self.fullscreen_action.setChecked(is_fullscreen)
                self.fullscreen_action.blockSignals(False)

    def sync_custom_node_templates_metadata(self):
        self.graph_manager.graph_data.metadata['custom_node_templates'] = NodeFactory.export_custom_node_templates()
        self.graph_manager.graph_data.metadata['node_template_settings'] = NodeFactory.export_node_template_settings()
        self._ensure_stacker_metadata()

    def toggle_tools_panel(self):
        """Toggle the visibility of the tools panel"""
        if getattr(self.tools_integration, 'embedded_mode', False):
            if hasattr(self, 'detail_panel'):
                self.detail_panel.show_tools_tab()
            return
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

        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected_scene_items()
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
