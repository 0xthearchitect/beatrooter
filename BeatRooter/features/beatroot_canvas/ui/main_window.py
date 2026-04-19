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
import tempfile
from datetime import datetime
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QToolBar, QStatusBar, QFileDialog, QMessageBox,
                             QSplitter, QApplication, QGraphicsLineItem, QGraphicsRectItem,
                             QDialog, QDialogButtonBox, QPlainTextEdit, QTabBar,
                             QLabel, QComboBox, QToolButton)
from PyQt6.QtCore import Qt, QPointF, QLineF, QSettings, QRectF, QTimer
from PyQt6.QtGui import QAction, QActionGroup, QIcon, QKeySequence, QPen, QColor
from PyQt6 import sip

from features.beatnote.core.beatnote_service import BeatNoteService
from features.beatroot_canvas.core import GraphManager, StorageManager, ThemeManager, NodeFactory
from features.beatroot_canvas.core.flipper_workspace_importer import FlipperWorkspaceImporter
from features.beatroot_canvas.core.flipper_device_manager import FlipperDeviceManager
from features.beatroot_canvas.core.flipper_serial_storage import FlipperSerialStorageMirror, FlipperSerialBusyError, FlipperSerialError
from features.ndc.core.integration import ensure_default_ndc_scheduler, get_default_ndc_runtime
from features.ndc.core.graph_capture import build_snapshot_payload, compute_graph_fingerprint, diff_graph_state
from features.ndc.core.tool_capture import build_artifact_refs, build_tool_payload, compact_tool_summary

from features.beatroot_canvas.ui.canvas_widget import CanvasWidget
from features.beatroot_canvas.ui.flipper_explorer_dialog import FlipperExplorerDialog
from features.beatroot_canvas.ui.toolbox import ToolboxWidget
from features.beatroot_canvas.ui.detail_panel import DetailPanel
from features.beatroot_canvas.ui.node_widget import NodeWidget
from features.beatroot_canvas.ui.dynamic_edge import DynamicEdge
from features.beatroot_canvas.ui.redo_action import RedoActionHandler
from features.beatroot_canvas.ui.tool_node_dialogs import ToolNodeConfigDialog, ToolNodeOutputDialog
from features.beatroot_canvas.ui.stacker_item import StackerItem
from features.beatroot_canvas.ui.stackers_panel import StackersPanel, StackerDetailsDialog
from features.beatroot_canvas.ui.undo_action import UndoActionHandler
from utils.image_utils import ImageUtils
#from ai.ai_assistant import AIAssistant
from utils.path_utils import get_resource_path
from features.tools.core.tool_node_service import ToolNodeService
from features.wordlists.core.wordlist_service import WordlistService, WordlistValidationError


class DigitalDetectiveBoard(QMainWindow):
    STACKER_Z_BASE = -200.0
    STACKER_EDGE_Z = -240.0
    STACKER_MIN_WIDTH = 124.0
    STACKER_MIN_HEIGHT = 108.0
    STACKER_COLLAPSED_WIDTH = 118.0
    STACKER_COLLAPSED_HEIGHT = 54.0
    STACKER_SIDE_PADDING = 24.0
    STACKER_TOP_PADDING = 42.0
    STACKER_BOTTOM_PADDING = 22.0
    STACKER_LINK_HOLD_MS = 700

    def __init__(self, project_type=None, category=None, template_data=None):
        super().__init__()
        self.graph_manager = GraphManager()
        self.storage_manager = StorageManager()
        self.ndc_runtime = get_default_ndc_runtime()
        self.ndc_scheduler = ensure_default_ndc_scheduler()
        self.ndc_snapshot_timer = QTimer(self)
        self.ndc_snapshot_timer.setInterval(60000)
        self.ndc_snapshot_timer.timeout.connect(self._emit_scheduled_snapshot_checkpoint)
        self._last_ndc_snapshot_id = None
        self.current_theme = 'cyber_modern'
        self.node_widgets = {}
        self.edge_items = {}
        self.stacker_items = {}
        self.connection_source = None
        self.tool_run_threads = {}
        self.tool_output_cache = {}
        self.pending_stacker_preview_item = None
        self._active_stacker_drag_contexts = {}
        self._active_node_move_snapshot = None
        self._active_stacker_move_snapshot = None
        self._applying_stacker_cascade = False
        self._drag_link_state = None
        self._drag_link_hold_timer = QTimer(self)
        self._drag_link_hold_timer.setSingleShot(True)
        self._drag_link_hold_timer.setInterval(self.STACKER_LINK_HOLD_MS)
        self._drag_link_hold_timer.timeout.connect(self._arm_pending_drag_link_action)
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
        self.edge_style_combo = None
        self.edge_style_actions = {}
        self._node_clipboard = []
        self._node_clipboard_paste_count = 0
        self.undo_handler = UndoActionHandler(self)
        self.redo_handler = RedoActionHandler(self)
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
        self.ndc_snapshot_timer.start()

        
        if category:
            self.toolbox.update_category(category)
        
        self.statusBar().showMessage(f"Ready - {self.get_project_title()}")
        self.graph_manager.reset_history("Initial state")
        self.update_undo_redo_buttons()
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
        self._detail_panel_last_width = 460

        self.beatnote_service = BeatNoteService(
            ndc_runtime=self.ndc_runtime,
            ndc_context_provider=self._current_ndc_note_context,
        )
        self.toolbox = ToolboxWidget(
            self.graph_manager,
            self.category,
            beatnote_service=self.beatnote_service,
            beatnote_open_handler=self.open_beatnote_workspace,
            beatnote_use_handler=self.apply_beatnote_to_selected_node,
        )
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
        self._apply_canvas_accessibility_preferences()
        canvas_column_layout.addWidget(self.canvas_widget)
        splitter.addWidget(canvas_column)
        self.canvas_widget.viewport_resized.connect(self._sync_floating_toolbox_geometry)
        self.toolbox.setParent(self.canvas_widget.viewport())
        self.toolbox.show()
        self.toolbox.raise_()
        
        # Detail panel
        self.detail_panel = DetailPanel(self, beatnote_service=self.beatnote_service)
        self.detail_panel.setObjectName("DetailColumn")
        self.detail_panel.setMinimumWidth(450)
        self.detail_panel.setMaximumWidth(620)
        splitter.addWidget(self.detail_panel)

        self.tools_integration.setup_tools_integration(use_dock=False)
        self.detail_panel.attach_tools_widget(self.tools_integration.tools_manager)

        self.stackers_panel = StackersPanel(self)
        self.stackers_panel.create_requested.connect(self.toggle_stacker_creation_mode)
        self.stackers_panel.edit_selected_requested.connect(self.edit_selected_stacker)
        self.stackers_panel.delete_selected_requested.connect(self.delete_selected_stacker)
        self.stackers_panel.stacker_selected.connect(self._on_stacker_selected_from_panel)
        self.detail_panel.attach_stackers_widget(self.stackers_panel)
        self.canvas_widget.scene.selectionChanged.connect(self._on_scene_selection_changed)
        
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([980, 460])
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

    def _apply_canvas_accessibility_preferences(self) -> None:
        if hasattr(self, "canvas_widget"):
            self.canvas_widget.set_background_style(self._canvas_background_style)
        if hasattr(self, "edge_items"):
            for edge_item in self.edge_items.values():
                if edge_item is not None and not sip.isdeleted(edge_item):
                    edge_item.set_render_style(self._edge_render_style)
        self._sync_edge_style_controls()

    def _sync_edge_style_controls(self) -> None:
        normalized_style = DynamicEdge.normalize_render_style(self._edge_render_style)
        if self.edge_style_combo is not None:
            combo_index = self.edge_style_combo.findData(normalized_style)
            if combo_index >= 0 and combo_index != self.edge_style_combo.currentIndex():
                self.edge_style_combo.blockSignals(True)
                self.edge_style_combo.setCurrentIndex(combo_index)
                self.edge_style_combo.blockSignals(False)

        for style_key, action in self.edge_style_actions.items():
            action.blockSignals(True)
            action.setChecked(style_key == normalized_style)
            action.blockSignals(False)
    
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

        self.undo_action = self.undo_handler.create_action(self, include_shortcut=True)
        file_menu.addAction(self.undo_action)
        
        self.redo_action = self.redo_handler.create_action(self, include_shortcut=True)
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

        canvas_background_menu = accessibility_menu.addMenu('Canvas Background')
        self.canvas_background_action_group = QActionGroup(self)
        self.canvas_background_action_group.setExclusive(True)

        self.canvas_background_grid_action = QAction('Grid', self)
        self.canvas_background_grid_action.setCheckable(True)
        self.canvas_background_grid_action.setChecked(self._canvas_background_style == 'grid')
        self.canvas_background_grid_action.triggered.connect(
            lambda checked: checked and self._set_canvas_background_style('grid')
        )
        self.canvas_background_action_group.addAction(self.canvas_background_grid_action)
        canvas_background_menu.addAction(self.canvas_background_grid_action)

        self.canvas_background_dots_action = QAction('Dots', self)
        self.canvas_background_dots_action.setCheckable(True)
        self.canvas_background_dots_action.setChecked(self._canvas_background_style == 'dots')
        self.canvas_background_dots_action.setToolTip(
            'Uses a subtle dotted canvas background similar to node-based workflow tools.'
        )
        self.canvas_background_dots_action.triggered.connect(
            lambda checked: checked and self._set_canvas_background_style('dots')
        )
        self.canvas_background_action_group.addAction(self.canvas_background_dots_action)
        canvas_background_menu.addAction(self.canvas_background_dots_action)

        edge_style_menu = accessibility_menu.addMenu('Edge Style')
        self.edge_style_action_group = QActionGroup(self)
        self.edge_style_action_group.setExclusive(True)
        self.edge_style_actions = {}
        for style_key, style_label in DynamicEdge.render_style_options().items():
            style_action = QAction(style_label, self)
            style_action.setCheckable(True)
            style_action.setChecked(self._edge_render_style == style_key)
            style_action.triggered.connect(
                lambda checked, key=style_key: checked and self._set_edge_render_style(key)
            )
            self.edge_style_action_group.addAction(style_action)
            edge_style_menu.addAction(style_action)
            self.edge_style_actions[style_key] = style_action

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

        self.undo_toolbar_action = self.undo_handler.create_action(self)
        self.main_toolbar.addAction(self.undo_toolbar_action)
        
        self.redo_toolbar_action = self.redo_handler.create_action(self)
        self.main_toolbar.addAction(self.redo_toolbar_action)
        
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

    def _on_edge_style_combo_changed(self, index: int) -> None:
        if self.edge_style_combo is None or index < 0:
            return
        style_key = str(self.edge_style_combo.itemData(index) or "").strip()
        if style_key:
            self._set_edge_render_style(style_key)

    def _install_save_state_hook(self):
        original_save_state = self.graph_manager.save_state

        def hooked_save_state(description=""):
            previous_graph = None
            if 0 <= self.graph_manager.history_position < len(self.graph_manager.history):
                previous_state = self.graph_manager.history[self.graph_manager.history_position]
                previous_graph = copy.deepcopy(previous_state.get("graph_data"))
            original_save_state(description)
            self._emit_ndc_graph_diff_events(previous_graph, self.graph_manager.graph_data)
            if not self._suspend_document_dirty_tracking:
                self._mark_active_document_dirty()
            self.update_undo_redo_buttons()

        self.graph_manager.save_state = hooked_save_state

    def _create_initial_document_tab(self):
        initial_graph = copy.deepcopy(self.graph_manager.graph_data)
        self._ensure_ndc_project_id(initial_graph.metadata)
        self._append_document_tab(
            graph_data=initial_graph,
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
        if hasattr(payload, "metadata") and isinstance(payload.metadata, dict):
            self._ensure_ndc_project_id(payload.metadata)
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
            "history": [],
            "history_position": -1,
        }
        self._document_sequence += 1
        self.documents.append(document)
        tab_index = len(self.documents) - 1

        self.document_tabs.blockSignals(True)
        self.document_tabs.addTab("")
        self._update_document_tab_label(tab_index)
        self._refresh_document_tab_close_buttons()
        self.document_tabs.blockSignals(False)

        if activate:
            self._activate_document_tab(tab_index)
            self._schedule_missing_tools_prompt_if_needed()
        return tab_index

    def _ensure_ndc_project_id(self, metadata: dict | None) -> str:
        return self.ndc_runtime.ensure_project_id(metadata, prefix="project")

    def _current_ndc_note_context(self) -> dict[str, str]:
        metadata = self.graph_manager.graph_data.metadata
        project_id = self._ensure_ndc_project_id(metadata)
        return {
            "project_id": project_id,
            "note_scope": "project",
            "source_ref": "beatroot_canvas.beatnote_panel",
            "format": "html",
        }

    def _build_ndc_project_payload(
        self,
        *,
        graph_data=None,
        file_path: str | None = None,
        reason: str | None = None,
        extra_payload: dict | None = None,
    ) -> dict:
        target_graph = graph_data or self.graph_manager.graph_data
        metadata = getattr(target_graph, "metadata", {})
        self._ensure_ndc_project_id(metadata)
        project_title = str(metadata.get("title") or self.get_project_title() or "Untitled Investigation")
        payload = {"project_title": project_title}
        if file_path:
            payload["file_path"] = str(file_path)
        if reason:
            payload["reason"] = reason
        if extra_payload:
            payload.update(extra_payload)
        return payload

    def _emit_ndc_project_event(
        self,
        action: str,
        *,
        graph_data=None,
        file_path: str | None = None,
        reason: str | None = None,
        extra_payload: dict | None = None,
    ) -> None:
        target_graph = graph_data or self.graph_manager.graph_data
        metadata = getattr(target_graph, "metadata", {})
        project_id = self._ensure_ndc_project_id(metadata)
        payload = self._build_ndc_project_payload(
            graph_data=target_graph,
            file_path=file_path,
            reason=reason,
            extra_payload=extra_payload,
        )
        try:
            self.ndc_runtime.enqueue_event(
                family="project",
                action=action,
                project_id=project_id,
                payload=payload,
            )
        except Exception:
            return

    def _emit_ndc_graph_diff_events(self, previous_graph, current_graph) -> None:
        metadata = getattr(current_graph, "metadata", {})
        project_id = self._ensure_ndc_project_id(metadata)
        for change in diff_graph_state(previous_graph, current_graph):
            try:
                self.ndc_runtime.enqueue_event(
                    family=change.family,
                    action=change.action,
                    project_id=project_id,
                    payload=change.payload,
                )
            except Exception:
                continue

    def _emit_ndc_snapshot_event(
        self,
        action: str,
        *,
        graph_data=None,
        trigger: str,
        summary: str,
    ) -> None:
        target_graph = graph_data or self.graph_manager.graph_data
        metadata = getattr(target_graph, "metadata", {})
        project_id = self._ensure_ndc_project_id(metadata)
        snapshot_payload = build_snapshot_payload(
            target_graph,
            trigger=trigger,
            summary=summary,
        )
        snapshot_id = snapshot_payload["snapshot_id"]
        try:
            self.ndc_runtime.enqueue_event(
                family="snapshot",
                action=action,
                project_id=project_id,
                payload=snapshot_payload,
            )
            self._last_ndc_snapshot_id = snapshot_id
        except Exception:
            return

    def _current_ndc_related_node_id(self) -> str | None:
        node = self._selected_node_for_beatnote()
        if node is None:
            return None
        node_id = str(getattr(node, "id", "") or "").strip()
        return node_id or None

    def _emit_ndc_tool_event(
        self,
        action: str,
        *,
        tool_name: str,
        surface: str,
        result_summary: str | None = None,
        result_status: str | None = None,
        result_count: int | None = None,
        related_node_id: str | None = None,
        target_ref: str | None = None,
        command_ref: str | None = None,
        artifact_refs: tuple[str, ...] | list[str] = (),
        context_scope: str | None = None,
    ) -> None:
        metadata = self.graph_manager.graph_data.metadata
        project_id = self._ensure_ndc_project_id(metadata)
        node_id = str(related_node_id or self._current_ndc_related_node_id() or "").strip() or None
        payload = build_tool_payload(
            event_action=action,
            tool_name=tool_name,
            surface=surface,
            result_summary=result_summary,
            result_status=result_status,
            result_count=result_count,
            related_node_id=node_id,
            target_ref=target_ref,
            command_ref=command_ref,
            artifact_refs=artifact_refs,
            context_scope=context_scope or ("node" if node_id else "project"),
        )
        try:
            self.ndc_runtime.enqueue_event(
                family="tool",
                action=action,
                project_id=project_id,
                payload=payload,
            )
        except Exception:
            return

    def _emit_scheduled_snapshot_checkpoint(self) -> None:
        graph_data = self.graph_manager.graph_data
        if len(graph_data.nodes) == 0 and len(graph_data.edges) == 0:
            return
        snapshot_id = compute_graph_fingerprint(graph_data)
        if snapshot_id == self._last_ndc_snapshot_id:
            return
        self._emit_ndc_snapshot_event(
            "checkpoint_scheduled",
            graph_data=graph_data,
            trigger="scheduled_interval",
            summary="Scheduled graph checkpoint for reconstruction fidelity.",
        )

    def emit_ndc_project_opened(self, file_path: str | None = None, *, reason: str = "open") -> None:
        self._emit_ndc_project_event(
            "opened",
            graph_data=self.graph_manager.graph_data,
            file_path=file_path or self.storage_manager.current_file,
            reason=reason,
        )

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
            estimate_filename = file_path or os.path.join(
                tempfile.gettempdir(),
                f"beatrooter_document_{document.get('id', 'untitled')}.brt",
            )
            return self.storage_manager.estimate_graph_size_bytes(graph_data, estimate_filename)
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

    def _refresh_document_tab_close_buttons(self):
        for index in range(self.document_tabs.count()):
            container = QWidget(self.document_tabs)
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 8, 0)
            row.setSpacing(0)

            close_btn = QToolButton(container)
            close_btn.setText("✕")
            close_btn.setAutoRaise(True)
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            close_btn.setToolTip("Close document")
            close_btn.setObjectName("DocumentTabCloseButton")
            close_btn.setFixedSize(18, 18)
            close_btn.clicked.connect(lambda _checked=False, i=index: self._close_document_tab(i))

            row.addStretch(1)
            row.addWidget(close_btn)

            self.document_tabs.setTabButton(index, QTabBar.ButtonPosition.RightSide, container)

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
        if getattr(self, "detail_panel", None) is not None:
            self.detail_panel.flush_pending_history()
        document = self.documents[self.active_document_index]
        document["graph_data"] = copy.deepcopy(self.graph_manager.graph_data)
        document["project_type"] = self.project_type
        document["category"] = self.category
        document["file_path"] = self.storage_manager.current_file
        document["node_counter"] = int(self.graph_manager.node_counter)
        document["edge_counter"] = int(self.graph_manager.edge_counter)
        document["history"] = copy.deepcopy(self.graph_manager.history)
        document["history_position"] = int(self.graph_manager.history_position)
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
            self.load_graph_data(
                copy.deepcopy(document["graph_data"]),
                node_counter=int(document.get("node_counter", 0)),
                edge_counter=int(document.get("edge_counter", 0)),
                history=copy.deepcopy(document.get("history") or []),
                history_position=document.get("history_position"),
            )
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
        self._emit_ndc_project_event(
            "saved",
            graph_data=document["graph_data"],
            file_path=target_file,
            reason="save_as" if force_save_as else "save",
        )
        self._emit_ndc_snapshot_event(
            "checkpoint_saved",
            graph_data=document["graph_data"],
            trigger="save",
            summary="Checkpoint captured on investigation save.",
        )
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

        closing_document = self.documents[index]
        self._emit_ndc_snapshot_event(
            "checkpoint_closed",
            graph_data=closing_document.get("graph_data"),
            trigger="tab_close",
            summary="Checkpoint captured before document tab close.",
        )

        closing_active = index == self.active_document_index
        self.documents.pop(index)
        self.document_tabs.blockSignals(True)
        self.document_tabs.removeTab(index)
        self._refresh_document_tab_close_buttons()
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
        normalized_stackers = []
        for payload in metadata.get("stackers", []):
            if not isinstance(payload, dict):
                continue
            self._normalize_stacker_payload(payload)
            normalized_stackers.append(payload)
        metadata["stackers"] = normalized_stackers

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

    def _normalize_stacker_payload(self, payload: dict):
        if not isinstance(payload, dict):
            return

        payload["color"] = "#292929"
        payload["name"] = str(payload.get("name", "Stacker")).strip() or "Stacker"
        payload["type"] = str(payload.get("type", "")).strip()
        payload["parent_stacker_id"] = str(payload.get("parent_stacker_id", "")).strip()
        payload["collapsed"] = bool(payload.get("collapsed", False))

        try:
            payload["width"] = max(self.STACKER_MIN_WIDTH, float(payload.get("width", self.STACKER_MIN_WIDTH)))
        except (TypeError, ValueError):
            payload["width"] = self.STACKER_MIN_WIDTH

        try:
            payload["height"] = max(self.STACKER_MIN_HEIGHT, float(payload.get("height", self.STACKER_MIN_HEIGHT)))
        except (TypeError, ValueError):
            payload["height"] = self.STACKER_MIN_HEIGHT

        for key in ("x", "y"):
            try:
                payload[key] = float(payload.get(key, 0.0))
            except (TypeError, ValueError):
                payload[key] = 0.0

    def _get_node_parent_stacker_id(self, node) -> str:
        if node is None:
            return ""
        parent_id = str((node.data or {}).get("parent_stacker_id", "") or "").strip()
        return parent_id

    def _set_node_parent_stacker_id(self, node, stacker_id: str):
        if node is None:
            return
        stacker_id = str(stacker_id or "").strip()
        if stacker_id:
            node.data["parent_stacker_id"] = stacker_id
        else:
            node.data.pop("parent_stacker_id", None)

    def _get_stacker_parent_id(self, stacker_id: str) -> str:
        payload = self._find_stacker_payload(stacker_id)
        if not payload:
            return ""
        return str(payload.get("parent_stacker_id", "") or "").strip()

    def _set_stacker_parent_id(self, stacker_id: str, parent_id: str):
        payload = self._find_stacker_payload(stacker_id)
        if not payload:
            return
        payload["parent_stacker_id"] = str(parent_id or "").strip()

    def _is_stacker_collapsed(self, stacker_id: str) -> bool:
        payload = self._find_stacker_payload(stacker_id)
        if not payload:
            return False
        return bool(payload.get("collapsed", False))

    def _set_stacker_collapsed(self, stacker_id: str, collapsed: bool):
        payload = self._find_stacker_payload(stacker_id)
        if not payload:
            return
        payload["collapsed"] = bool(collapsed)

    def _all_stacker_ids(self):
        self._ensure_stacker_metadata()
        ids = []
        for payload in self.graph_manager.graph_data.metadata.get("stackers", []):
            stacker_id = str(payload.get("id", "") or "").strip()
            if stacker_id:
                ids.append(stacker_id)
        return ids

    def _direct_child_node_ids(self, stacker_id: str):
        stacker_id = str(stacker_id or "").strip()
        if not stacker_id:
            return []
        node_ids = []
        for node in self.graph_manager.graph_data.nodes.values():
            if self._get_node_parent_stacker_id(node) == stacker_id:
                node_ids.append(node.id)
        return node_ids

    def _direct_child_stacker_ids(self, stacker_id: str):
        stacker_id = str(stacker_id or "").strip()
        if not stacker_id:
            return []
        child_ids = []
        for payload in self.graph_manager.graph_data.metadata.get("stackers", []):
            if str(payload.get("parent_stacker_id", "") or "").strip() == stacker_id:
                child_id = str(payload.get("id", "") or "").strip()
                if child_id:
                    child_ids.append(child_id)
        return child_ids

    def _is_stacker_descendant(self, candidate_id: str, ancestor_id: str) -> bool:
        candidate_id = str(candidate_id or "").strip()
        ancestor_id = str(ancestor_id or "").strip()
        if not candidate_id or not ancestor_id or candidate_id == ancestor_id:
            return False

        visited = set()
        current = self._get_stacker_parent_id(candidate_id)
        while current and current not in visited:
            if current == ancestor_id:
                return True
            visited.add(current)
            current = self._get_stacker_parent_id(current)
        return False

    def _repair_stacker_links(self):
        self._ensure_stacker_metadata()
        valid_ids = set(self._all_stacker_ids())

        for payload in self.graph_manager.graph_data.metadata.get("stackers", []):
            stacker_id = str(payload.get("id", "") or "").strip()
            parent_id = str(payload.get("parent_stacker_id", "") or "").strip()
            if not parent_id or parent_id not in valid_ids or parent_id == stacker_id:
                payload["parent_stacker_id"] = ""

        for payload in self.graph_manager.graph_data.metadata.get("stackers", []):
            stacker_id = str(payload.get("id", "") or "").strip()
            seen = {stacker_id}
            current = str(payload.get("parent_stacker_id", "") or "").strip()
            while current:
                if current in seen:
                    payload["parent_stacker_id"] = ""
                    break
                seen.add(current)
                current = self._get_stacker_parent_id(current)

        for node in self.graph_manager.graph_data.nodes.values():
            parent_id = self._get_node_parent_stacker_id(node)
            if parent_id and parent_id not in valid_ids:
                self._set_node_parent_stacker_id(node, "")

    def _stacker_depth(self, stacker_id: str, memo=None) -> int:
        memo = memo if memo is not None else {}
        if stacker_id in memo:
            return memo[stacker_id]

        child_ids = self._direct_child_stacker_ids(stacker_id)
        if not child_ids:
            memo[stacker_id] = 0
            return 0

        depth = 1 + max(self._stacker_depth(child_id, memo) for child_id in child_ids)
        memo[stacker_id] = depth
        return depth

    def _stacker_ids_child_first(self):
        memo = {}
        return sorted(self._all_stacker_ids(), key=lambda stacker_id: self._stacker_depth(stacker_id, memo))

    def _stacker_rect_from_payload(self, payload: dict) -> QRectF:
        return QRectF(
            float(payload.get("x", 0.0)),
            float(payload.get("y", 0.0)),
            max(self.STACKER_MIN_WIDTH, float(payload.get("width", self.STACKER_MIN_WIDTH))),
            max(self.STACKER_MIN_HEIGHT, float(payload.get("height", self.STACKER_MIN_HEIGHT))),
        )

    def _scene_rect_for_node_id(self, node_id: str) -> QRectF:
        node_widget = self.node_widgets.get(str(node_id or ""))
        if node_widget and node_widget.scene():
            return node_widget.sceneBoundingRect()

        node = self.graph_manager.get_node(str(node_id or ""))
        if node is None:
            return QRectF()
        return QRectF(node.position.x() - 31.0, node.position.y() - 31.0, 62.0, 62.0)

    def _scene_rect_for_stacker_id(self, stacker_id: str) -> QRectF:
        stacker_item = self.stacker_items.get(str(stacker_id or ""))
        if stacker_item and stacker_item.scene():
            return QRectF(
                float(stacker_item.scenePos().x()),
                float(stacker_item.scenePos().y()),
                float(stacker_item.width),
                float(stacker_item.height),
            )

        payload = self._find_stacker_payload(str(stacker_id or ""))
        if not payload:
            return QRectF()
        return self._stacker_rect_from_payload(payload)

    def _stacker_content_counts(self, stacker_id: str):
        node_ids, stacker_ids = self._collect_stacker_descendants(stacker_id)
        return len(node_ids), len(stacker_ids)

    def _stacker_hidden_by_collapsed_ancestor(self, stacker_id: str) -> bool:
        visited = set()
        current = self._get_stacker_parent_id(stacker_id)
        while current and current not in visited:
            if self._is_stacker_collapsed(current):
                return True
            visited.add(current)
            current = self._get_stacker_parent_id(current)
        return False

    def _node_hidden_by_collapsed_ancestor(self, node) -> bool:
        if node is None:
            return False
        visited = set()
        current = self._get_node_parent_stacker_id(node)
        while current and current not in visited:
            if self._is_stacker_collapsed(current):
                return True
            visited.add(current)
            current = self._get_stacker_parent_id(current)
        return False

    def _sync_edge_visibility(self):
        for edge_id, edge_item in self.edge_items.items():
            edge = self.graph_manager.get_edge(edge_id)
            if edge is None:
                continue
            source_widget = self._resolve_connection_widget(edge.source_id)
            target_widget = self._resolve_connection_widget(edge.target_id)
            if source_widget and target_widget:
                edge_item.update_path()
            visible = bool(
                source_widget
                and target_widget
                and source_widget.isVisible()
                and target_widget.isVisible()
            )
            if hasattr(edge_item, "set_content_visible"):
                edge_item.set_content_visible(visible)
            else:
                edge_item.setVisible(visible)

    def _edge_is_stacker_related(self, edge) -> bool:
        if edge is None:
            return False
        source_id = str(getattr(edge, "source_id", "") or "").strip()
        target_id = str(getattr(edge, "target_id", "") or "").strip()
        return source_id in self.stacker_items or target_id in self.stacker_items

    def _edge_z_value(self, edge) -> float:
        if self._edge_is_stacker_related(edge):
            return float(self.STACKER_EDGE_Z)
        return -1.0

    def _refresh_all_edge_z_values(self):
        for edge_id, edge_item in self.edge_items.items():
            edge = self.graph_manager.get_edge(edge_id)
            edge_item.setZValue(self._edge_z_value(edge))

    def _refresh_all_edge_paths(self):
        for edge_item in self.edge_items.values():
            if edge_item is None:
                continue
            try:
                edge_item.update_path()
            except RuntimeError:
                continue

    def _resolve_connection_widget(self, item_id: str):
        item_id = str(item_id or "").strip()
        if item_id in self.node_widgets:
            return self.node_widgets[item_id]
        if item_id in self.stacker_items:
            return self.stacker_items[item_id]
        return None

    def _sync_stacker_content_visibility(self):
        scene = self._safe_canvas_scene()
        for stacker_id, stacker_item in self.stacker_items.items():
            visible = not self._stacker_hidden_by_collapsed_ancestor(stacker_id)
            stacker_item.setVisible(visible)
            if not visible and scene is not None and stacker_item.isSelected():
                stacker_item.setSelected(False)

        for node_id, node_widget in self.node_widgets.items():
            node = self.graph_manager.get_node(node_id)
            visible = not self._node_hidden_by_collapsed_ancestor(node)
            node_widget.setVisible(visible)
            if not visible and scene is not None and node_widget.isSelected():
                node_widget.setSelected(False)

        self._sync_edge_visibility()

    def _find_free_stacker_position(self, width: float, height: float) -> QPointF:
        view_center = self.canvas_widget.mapToScene(self.canvas_widget.viewport().rect().center())
        candidate_origins = []
        spacing = 42.0

        for radius in range(0, 8):
            if radius == 0:
                candidate_origins.append(
                    QPointF(view_center.x() - (width / 2.0), view_center.y() - (height / 2.0))
                )
                continue

            offsets = [
                (-radius, -radius), (0, -radius), (radius, -radius),
                (-radius, 0),                     (radius, 0),
                (-radius, radius),  (0, radius),  (radius, radius),
            ]
            for offset_x, offset_y in offsets:
                candidate_origins.append(
                    QPointF(
                        view_center.x() - (width / 2.0) + (offset_x * (width + spacing)),
                        view_center.y() - (height / 2.0) + (offset_y * (height + spacing)),
                    )
                )

        occupied_rects = []
        for node_widget in self.node_widgets.values():
            if node_widget.scene():
                occupied_rects.append(node_widget.sceneBoundingRect().adjusted(-18.0, -18.0, 18.0, 18.0))
        for stacker_item in self.stacker_items.values():
            if stacker_item.scene():
                occupied_rects.append(
                    QRectF(
                        stacker_item.scenePos().x(),
                        stacker_item.scenePos().y(),
                        stacker_item.width,
                        stacker_item.height,
                    ).adjusted(-22.0, -22.0, 22.0, 22.0)
                )

        for origin in candidate_origins:
            proposed_rect = QRectF(origin.x(), origin.y(), width, height)
            if not any(proposed_rect.intersects(existing_rect) for existing_rect in occupied_rects):
                return origin

        return QPointF(view_center.x() - (width / 2.0), view_center.y() - (height / 2.0))

    def _stacker_layout_rect(self, stacker_id: str) -> QRectF:
        payload = self._find_stacker_payload(stacker_id)
        if not payload:
            return QRectF()

        if self._is_stacker_collapsed(stacker_id):
            current_rect = self._scene_rect_for_stacker_id(stacker_id)
            if not current_rect.isValid():
                current_rect = self._stacker_rect_from_payload(payload)
            return QRectF(
                current_rect.x(),
                current_rect.y(),
                self.STACKER_COLLAPSED_WIDTH,
                self.STACKER_COLLAPSED_HEIGHT,
            )

        child_rects = []
        for node_id in self._direct_child_node_ids(stacker_id):
            rect = self._scene_rect_for_node_id(node_id)
            if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                child_rects.append(rect)

        for child_stacker_id in self._direct_child_stacker_ids(stacker_id):
            rect = self._scene_rect_for_stacker_id(child_stacker_id)
            if rect.isValid() and rect.width() > 0 and rect.height() > 0:
                child_rects.append(rect)

        if not child_rects:
            current_rect = self._scene_rect_for_stacker_id(stacker_id)
            center = current_rect.center()
            return QRectF(
                center.x() - (self.STACKER_MIN_WIDTH / 2.0),
                center.y() - (self.STACKER_MIN_HEIGHT / 2.0),
                self.STACKER_MIN_WIDTH,
                self.STACKER_MIN_HEIGHT,
            )

        union_rect = QRectF(child_rects[0])
        for rect in child_rects[1:]:
            union_rect = union_rect.united(rect)

        layout_rect = union_rect.adjusted(
            -self.STACKER_SIDE_PADDING,
            -self.STACKER_TOP_PADDING,
            self.STACKER_SIDE_PADDING,
            self.STACKER_BOTTOM_PADDING,
        )

        if layout_rect.width() < self.STACKER_MIN_WIDTH:
            extra = (self.STACKER_MIN_WIDTH - layout_rect.width()) / 2.0
            layout_rect.adjust(-extra, 0.0, extra, 0.0)
        if layout_rect.height() < self.STACKER_MIN_HEIGHT:
            extra = (self.STACKER_MIN_HEIGHT - layout_rect.height()) / 2.0
            layout_rect.adjust(0.0, -extra, 0.0, extra)

        return layout_rect

    def _apply_stacker_layout_rect(self, stacker_id: str, rect: QRectF):
        payload = self._find_stacker_payload(stacker_id)
        stacker_item = self.stacker_items.get(stacker_id)
        if not payload or not stacker_item:
            return

        rect = QRectF(rect)
        payload["x"] = float(rect.x())
        payload["y"] = float(rect.y())
        payload["width"] = float(rect.width())
        payload["height"] = float(rect.height())
        stacker_item.set_geometry(rect)
        stacker_item.set_collapsed(self._is_stacker_collapsed(stacker_id))
        node_count, child_stacker_count = self._stacker_content_counts(stacker_id)
        stacker_item.set_child_counts(node_count, child_stacker_count)

    def _refresh_single_stacker_layout(self, stacker_id: str):
        stacker_id = str(stacker_id or "").strip()
        if not stacker_id:
            return

        rect = self._stacker_layout_rect(stacker_id)
        if rect.isValid():
            self._apply_stacker_layout_rect(stacker_id, rect)
        self._apply_stacker_layers_to_items()
        self._refresh_all_edge_paths()
        self._sync_stacker_content_visibility()

    def _refresh_all_stacker_layouts(self):
        self._repair_stacker_links()
        for stacker_id in self._stacker_ids_child_first():
            rect = self._stacker_layout_rect(stacker_id)
            if rect.isValid():
                self._apply_stacker_layout_rect(stacker_id, rect)
        self._apply_stacker_layers_to_items()
        self._refresh_all_edge_paths()
        self._sync_stacker_content_visibility()

    def _refresh_stacker_parent_chain(self, parent_stacker_id: str):
        parent_stacker_id = str(parent_stacker_id or "").strip()
        visited = set()
        current = parent_stacker_id
        while current and current not in visited:
            visited.add(current)
            rect = self._stacker_layout_rect(current)
            if rect.isValid():
                self._apply_stacker_layout_rect(current, rect)
            current = self._get_stacker_parent_id(current)
        self._apply_stacker_layers_to_items()
        self._refresh_all_edge_paths()
        self._sync_stacker_content_visibility()

    def _collect_stacker_descendants(self, stacker_id: str):
        node_ids = []
        stacker_ids = []
        queue = [str(stacker_id or "").strip()]

        while queue:
            current_id = queue.pop(0)
            for child_node_id in self._direct_child_node_ids(current_id):
                if child_node_id not in node_ids:
                    node_ids.append(child_node_id)
            for child_stacker_id in self._direct_child_stacker_ids(current_id):
                if child_stacker_id not in stacker_ids:
                    stacker_ids.append(child_stacker_id)
                    queue.append(child_stacker_id)

        return node_ids, stacker_ids

    def _capture_stacker_move_snapshot(self, stacker_id: str):
        stacker_id = str(stacker_id or "").strip()
        if not stacker_id:
            return None

        snapshot = {"stackers": {}, "nodes": {}}
        tracked_stacker_ids = [stacker_id]
        descendant_node_ids, descendant_stacker_ids = self._collect_stacker_descendants(stacker_id)
        tracked_stacker_ids.extend(descendant_stacker_ids)

        for tracked_stacker_id in tracked_stacker_ids:
            payload = self._find_stacker_payload(tracked_stacker_id)
            if payload is None:
                continue
            snapshot["stackers"][tracked_stacker_id] = QPointF(
                float(payload.get("x", 0.0)),
                float(payload.get("y", 0.0)),
            )

        for node_id in descendant_node_ids:
            node = self.graph_manager.get_node(node_id)
            if node is None:
                continue
            snapshot["nodes"][node_id] = QPointF(node.position)

        return snapshot

    def _restore_stacker_move_snapshot(self, snapshot):
        if not snapshot:
            return

        self._applying_stacker_cascade = True
        try:
            for stacker_id, position in (snapshot.get("stackers") or {}).items():
                payload = self._find_stacker_payload(stacker_id)
                stacker_item = self.stacker_items.get(stacker_id)
                if payload is None or stacker_item is None:
                    continue
                payload["x"] = float(position.x())
                payload["y"] = float(position.y())
                stacker_item.setPos(QPointF(position))

            for node_id, position in (snapshot.get("nodes") or {}).items():
                node = self.graph_manager.get_node(node_id)
                node_widget = self.node_widgets.get(node_id)
                if node is None or node_widget is None:
                    continue
                node.position = QPointF(position)
                node_widget.setPos(QPointF(position))
        finally:
            self._applying_stacker_cascade = False

    def _begin_drag_link_session(self, kind: str, item_id: str):
        self._clear_drag_link_state()
        self._drag_link_state = {
            "kind": str(kind or "").strip(),
            "item_id": str(item_id or "").strip(),
            "candidate": None,
            "armed_action": "",
            "armed_target_id": "",
            "hint_target_id": "",
            "break_reference_rect": QRectF(),
        }
        current_parent = self._dragged_item_parent_id(kind, item_id)
        if current_parent:
            self._drag_link_state["break_reference_rect"] = self._scene_rect_for_stacker_id(current_parent)
        self._update_drag_link_candidate()

    def _clear_drag_link_hint(self):
        state = self._drag_link_state or {}
        target_id = str(state.get("hint_target_id", "") or "").strip()
        if target_id and target_id in self.stacker_items:
            self.stacker_items[target_id].clear_link_hint()
        if self._drag_link_state is not None:
            self._drag_link_state["hint_target_id"] = ""

    def _show_drag_link_hint(self, stacker_id: str, text: str):
        self._clear_drag_link_hint()
        stacker_id = str(stacker_id or "").strip()
        if not stacker_id:
            return
        stacker_item = self.stacker_items.get(stacker_id)
        if not stacker_item:
            return
        stacker_item.set_link_hint(text)
        if self._drag_link_state is not None:
            self._drag_link_state["hint_target_id"] = stacker_id

    def _clear_drag_link_state(self):
        self._drag_link_hold_timer.stop()
        self._clear_drag_link_hint()
        for stacker_item in self.stacker_items.values():
            stacker_item.clear_link_hint()
        self._drag_link_state = None

    def _dragged_item_scene_rect(self, kind: str, item_id: str) -> QRectF:
        if kind == "node":
            return self._scene_rect_for_node_id(item_id)
        if kind == "stacker":
            return self._scene_rect_for_stacker_id(item_id)
        return QRectF()

    def _dragged_item_parent_id(self, kind: str, item_id: str) -> str:
        if kind == "node":
            return self._get_node_parent_stacker_id(self.graph_manager.get_node(item_id))
        if kind == "stacker":
            return self._get_stacker_parent_id(item_id)
        return ""

    def _find_candidate_stacker_for_drag(self, kind: str, item_id: str, rect: QRectF) -> str:
        if not rect.isValid():
            return ""

        exclude_ids = {str(item_id or "").strip()}
        current_parent = self._dragged_item_parent_id(kind, item_id)
        if current_parent:
            exclude_ids.add(current_parent)

        if kind == "stacker":
            descendants = set(self._collect_stacker_descendants(item_id)[1])
            exclude_ids.update(descendants)

        candidates = []
        for candidate_id, candidate_item in self.stacker_items.items():
            if candidate_id in exclude_ids or not candidate_item.scene():
                continue
            candidate_rect = QRectF(
                candidate_item.scenePos().x(),
                candidate_item.scenePos().y(),
                candidate_item.width,
                candidate_item.height,
            )
            if not candidate_rect.isValid():
                continue

            if kind == "stacker":
                if not self._stacker_can_accept_drag_link(candidate_rect, rect):
                    continue
            else:
                if not candidate_rect.adjusted(8.0, 8.0, -8.0, -8.0).contains(rect.center()):
                    continue

            candidates.append((candidate_rect.width() * candidate_rect.height(), candidate_id))

        if candidates:
            candidates.sort(key=lambda entry: entry[0])
            return candidates[0][1]
        return ""

    def _resolve_drag_link_candidate(self):
        state = self._drag_link_state or {}
        kind = str(state.get("kind", "") or "").strip()
        item_id = str(state.get("item_id", "") or "").strip()
        if not kind or not item_id:
            return None

        rect = self._dragged_item_scene_rect(kind, item_id)
        if not rect.isValid():
            return None

        current_parent = self._dragged_item_parent_id(kind, item_id)
        target_stacker_id = self._find_candidate_stacker_for_drag(kind, item_id, rect)

        if target_stacker_id:
            if self._item_has_edge_to_stacker(kind, item_id, target_stacker_id):
                return {"action": "blocked", "stacker_id": target_stacker_id, "hint": "BLOCKED BY EDGE"}
            return {"action": "create", "stacker_id": target_stacker_id}

        if current_parent:
            parent_rect = QRectF(state.get("break_reference_rect", QRectF()))
            if not parent_rect.isValid() or parent_rect.width() <= 0 or parent_rect.height() <= 0:
                parent_rect = self._scene_rect_for_stacker_id(current_parent)
            break_ratio = 0.72 if kind == "stacker" else 0.55
            if parent_rect.isValid() and self._stacker_breaks_drag_link(parent_rect, rect, break_ratio):
                return {"action": "break", "stacker_id": current_parent}

        return None

    def _update_drag_link_candidate(self):
        state = self._drag_link_state
        if not state:
            return

        candidate = self._resolve_drag_link_candidate()
        armed_action = str(state.get("armed_action", "") or "").strip()
        armed_target_id = str(state.get("armed_target_id", "") or "").strip()

        if armed_action and armed_target_id:
            candidate_matches_armed = bool(
                candidate
                and str(candidate.get("action", "") or "").strip() == armed_action
                and str(candidate.get("stacker_id", "") or "").strip() == armed_target_id
            )

            if candidate_matches_armed:
                state["candidate"] = candidate
                return

            if not candidate:
                return

        if candidate == state.get("candidate"):
            return

        self._drag_link_hold_timer.stop()
        self._clear_drag_link_hint()
        state["candidate"] = candidate
        state["armed_action"] = ""
        state["armed_target_id"] = ""

        if candidate:
            self._drag_link_hold_timer.start()

    def _arm_pending_drag_link_action(self):
        state = self._drag_link_state
        if not state:
            return

        candidate = state.get("candidate")
        if not candidate:
            return

        action = str(candidate.get("action", "") or "").strip()
        target_id = str(candidate.get("stacker_id", "") or "").strip()
        if not action or not target_id:
            return

        state["armed_action"] = action
        state["armed_target_id"] = target_id
        hint_text = str(candidate.get("hint", "") or "").strip().upper()
        if not hint_text:
            hint_text = "LINK" if action == "create" else "UNLINK"
        self._show_drag_link_hint(target_id, hint_text)

    def _apply_drag_link_action_if_needed(self):
        state = self._drag_link_state or {}
        armed_action = str(state.get("armed_action", "") or "").strip()
        target_id = str(state.get("armed_target_id", "") or "").strip()
        kind = str(state.get("kind", "") or "").strip()
        item_id = str(state.get("item_id", "") or "").strip()
        if not armed_action or not target_id or not kind or not item_id:
            self._clear_drag_link_state()
            return

        current_candidate = self._resolve_drag_link_candidate()
        if (
            not current_candidate
            or str(current_candidate.get("action", "") or "").strip() != armed_action
            or str(current_candidate.get("stacker_id", "") or "").strip() != target_id
        ):
            self._clear_drag_link_state()
            return

        if armed_action == "create":
            self._link_item_to_stacker(kind, item_id, target_id)
        elif armed_action == "break":
            self._unlink_item_from_stacker(kind, item_id, target_id)

        self._clear_drag_link_state()

    def _stacker_still_contains_drag_item(self, parent_rect: QRectF, item_rect: QRectF) -> bool:
        if not parent_rect.isValid() or not item_rect.isValid():
            return False

        inset_x = min(14.0, max(6.0, item_rect.width() * 0.18))
        inset_y = min(14.0, max(6.0, item_rect.height() * 0.18))
        probe_rect = item_rect.adjusted(inset_x, inset_y, -inset_x, -inset_y)
        if probe_rect.width() <= 0 or probe_rect.height() <= 0:
            probe_rect = item_rect

        inner_parent = parent_rect.adjusted(8.0, 8.0, -8.0, -8.0)
        if inner_parent.width() <= 0 or inner_parent.height() <= 0:
            inner_parent = parent_rect

        return inner_parent.contains(probe_rect)

    def _stacker_can_accept_drag_link(self, parent_rect: QRectF, item_rect: QRectF) -> bool:
        if not parent_rect.isValid() or not item_rect.isValid():
            return False

        inner_parent = parent_rect.adjusted(8.0, 8.0, -8.0, -8.0)
        if inner_parent.width() <= 0 or inner_parent.height() <= 0:
            inner_parent = parent_rect

        if inner_parent.contains(item_rect.center()):
            return True

        overlap_rect = inner_parent.intersected(item_rect)
        item_area = max(1.0, item_rect.width() * item_rect.height())
        overlap_area = max(0.0, overlap_rect.width()) * max(0.0, overlap_rect.height())
        overlap_ratio = overlap_area / item_area
        return overlap_ratio >= 0.22

    def _stacker_breaks_drag_link(self, parent_rect: QRectF, item_rect: QRectF, break_ratio: float = 0.55) -> bool:
        if not parent_rect.isValid() or not item_rect.isValid():
            return False

        inner_parent = parent_rect.adjusted(10.0, 10.0, -10.0, -10.0)
        if inner_parent.width() <= 0 or inner_parent.height() <= 0:
            inner_parent = parent_rect

        overlap_rect = inner_parent.intersected(item_rect)
        item_area = max(1.0, item_rect.width() * item_rect.height())
        overlap_area = max(0.0, overlap_rect.width()) * max(0.0, overlap_rect.height())
        overlap_ratio = overlap_area / item_area

        return overlap_ratio < float(break_ratio)

    def _link_item_to_stacker(self, kind: str, item_id: str, target_stacker_id: str):
        target_stacker_id = str(target_stacker_id or "").strip()
        if not target_stacker_id:
            return

        if kind == "node":
            node = self.graph_manager.get_node(item_id)
            if node is None:
                return
            previous_parent = self._get_node_parent_stacker_id(node)
            if previous_parent == target_stacker_id:
                return
            if self._item_has_edge_to_stacker("node", item_id, target_stacker_id):
                self.statusBar().showMessage("Cannot link node into a stacker it is already connected to by edge")
                return
            self._set_node_parent_stacker_id(node, target_stacker_id)
            self._refresh_stacker_parent_chain(previous_parent)
            self._refresh_stacker_parent_chain(target_stacker_id)
            self.graph_manager.save_state("Link node to stacker")
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Node linked to stacker")
            return

        if kind == "stacker":
            if item_id == target_stacker_id or self._is_stacker_descendant(target_stacker_id, item_id):
                return
            previous_parent = self._get_stacker_parent_id(item_id)
            if previous_parent == target_stacker_id:
                return
            if self._item_has_edge_to_stacker("stacker", item_id, target_stacker_id):
                self.statusBar().showMessage("Cannot link stacker into a stacker it is already connected to by edge")
                return
            self._set_stacker_parent_id(item_id, target_stacker_id)
            self._refresh_stacker_parent_chain(previous_parent)
            self._refresh_stacker_parent_chain(target_stacker_id)
            self.graph_manager.save_state("Link stacker to stacker")
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Stacker linked")

    def _item_has_edge_to_stacker(self, kind: str, item_id: str, target_stacker_id: str) -> bool:
        target_stacker_id = str(target_stacker_id or "").strip()
        item_id = str(item_id or "").strip()
        if not target_stacker_id or not item_id:
            return False

        related_ids = {item_id}
        if kind == "stacker":
            node_ids, stacker_ids = self._collect_stacker_descendants(item_id)
            related_ids.update(str(node_id) for node_id in node_ids)
            related_ids.update(str(stacker_id) for stacker_id in stacker_ids)

        for edge in self.graph_manager.graph_data.edges.values():
            source_id = str(getattr(edge, "source_id", "") or "").strip()
            target_id = str(getattr(edge, "target_id", "") or "").strip()
            if source_id == target_stacker_id and target_id in related_ids:
                return True
            if target_id == target_stacker_id and source_id in related_ids:
                return True

        return False

    def _unlink_item_from_stacker(self, kind: str, item_id: str, source_stacker_id: str):
        source_stacker_id = str(source_stacker_id or "").strip()
        if kind == "node":
            node = self.graph_manager.get_node(item_id)
            if node is None or self._get_node_parent_stacker_id(node) != source_stacker_id:
                return
            self._set_node_parent_stacker_id(node, "")
            self._refresh_stacker_parent_chain(source_stacker_id)
            self.graph_manager.save_state("Unlink node from stacker")
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Node unlinked from stacker")
            return

        if kind == "stacker":
            if self._get_stacker_parent_id(item_id) != source_stacker_id:
                return
            self._set_stacker_parent_id(item_id, "")
            self._refresh_stacker_parent_chain(source_stacker_id)
            self.graph_manager.save_state("Unlink stacker from stacker")
            self.update_undo_redo_buttons()
            self.statusBar().showMessage("Stacker unlinked")

    def _stacker_depth_to_root(self, stacker_id: str, memo=None) -> int:
        stacker_id = str(stacker_id or "").strip()
        if not stacker_id:
            return 0

        if memo is None:
            memo = {}
        if stacker_id in memo:
            return memo[stacker_id]

        visited = {stacker_id}
        depth = 0
        current = self._get_stacker_parent_id(stacker_id)
        while current and current not in visited:
            depth += 1
            visited.add(current)
            current = self._get_stacker_parent_id(current)

        memo[stacker_id] = depth
        return depth

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

    def _apply_stacker_layers_to_items(self):
        self._ensure_stacker_metadata()
        metadata_order = {}
        for index, payload in enumerate(self.graph_manager.graph_data.metadata.get("stackers", [])):
            if not isinstance(payload, dict):
                continue
            stacker_id = str(payload.get("id", "") or "").strip()
            if stacker_id and stacker_id not in metadata_order:
                metadata_order[stacker_id] = index

        memo = {}
        ordered_ids = sorted(
            list(self.stacker_items.keys()),
            key=lambda sid: (
                self._stacker_depth_to_root(sid, memo),
                metadata_order.get(sid, 10_000),
            ),
        )

        for z_offset, stacker_id in enumerate(ordered_ids):
            stacker_item = self.stacker_items.get(stacker_id)
            if stacker_item is None:
                continue
            stacker_item.setZValue(self.STACKER_Z_BASE + float(z_offset))

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
            parent_id = str(payload.get("parent_stacker_id", "") or "").strip()
            parent_payload = self._find_stacker_payload(parent_id) if parent_id else None
            parent_name = ""
            if isinstance(parent_payload, dict):
                parent_name = str(parent_payload.get("name", "")).strip()
            entries.append(
                {
                    "id": stacker_id,
                    "name": str(payload.get("name", "Stacker")).strip() or "Stacker",
                    "parent_name": parent_name,
                }
            )

        entries.sort(key=lambda item: item["name"].lower())
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

    def _toggle_stacker_collapsed(self, stacker_id: str):
        stacker_id = str(stacker_id or "").strip()
        if not stacker_id:
            return

        collapsed = not self._is_stacker_collapsed(stacker_id)
        self._set_stacker_collapsed(stacker_id, collapsed)
        self._refresh_single_stacker_layout(stacker_id)

        parent_id = self._get_stacker_parent_id(stacker_id)
        if parent_id:
            self._refresh_stacker_parent_chain(parent_id)

        self.graph_manager.save_state("Collapse stacker" if collapsed else "Expand stacker")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage("Stacker collapsed" if collapsed else "Stacker expanded")

    def _add_stacker_item(self, payload: dict):
        stacker_item = StackerItem(payload)
        stacker_item.dragged_delta.connect(self._on_stacker_dragged_delta)
        stacker_item.drag_started.connect(self._on_stacker_drag_started)
        stacker_item.drag_finished.connect(self._on_stacker_drag_finished)
        stacker_item.position_changed.connect(self._on_stacker_item_position_changed)
        stacker_item.moved.connect(self._on_stacker_moved)
        stacker_item.toggle_requested.connect(self._toggle_stacker_collapsed)
        stacker_item.connection_requested.connect(self.start_connection)
        stacker_item.edit_requested.connect(self._edit_stacker_by_id)
        stacker_item.delete_requested.connect(self._delete_stacker_by_id)
        stacker_item.node_creation_requested.connect(self.canvas_widget.create_node_at_position)
        stacker_item.stacker_creation_requested.connect(self.toggle_stacker_creation_mode)
        stacker_item.delete_selected_requested.connect(self.delete_selected_scene_items)
        stacker_item.setZValue(self.STACKER_Z_BASE)
        self.canvas_widget.scene.addItem(stacker_item)
        self.stacker_items[stacker_item.stacker_id] = stacker_item

    def load_stackers_from_metadata(self):
        self._ensure_stacker_metadata()
        self.stacker_items.clear()
        self._repair_stacker_links()
        payloads = [
            payload
            for payload in self.graph_manager.graph_data.metadata.get("stackers", [])
            if isinstance(payload, dict)
        ]
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            if not payload.get("id"):
                payload["id"] = self._next_stacker_id()
            self._add_stacker_item(payload)
        self._apply_stacker_layers_to_items()
        self._refresh_all_edge_z_values()
        self._refresh_stackers_panel()

    def create_stacker_from_panel(self, payload: dict):
        self._clear_drag_link_state()
        self._active_stacker_drag_contexts.clear()
        self._ensure_stacker_metadata()

        width = float(payload.get("width", self.STACKER_MIN_WIDTH))
        height = float(payload.get("height", self.STACKER_MIN_HEIGHT))
        x = payload.get("x")
        y = payload.get("y")

        if x is None or y is None:
            free_origin = self._find_free_stacker_position(width, height)
            x = float(free_origin.x())
            y = float(free_origin.y())

        stacker_payload = {
            "id": self._next_stacker_id(),
            "name": str(payload.get("name", "New Stacker")).strip() or "New Stacker",
            "type": str(payload.get("type", "")).strip(),
            "color": "#292929",
            "collapsed": False,
            "width": width,
            "height": height,
            "x": float(x),
            "y": float(y),
            "parent_stacker_id": "",
        }

        self._normalize_stacker_payload(stacker_payload)
        self.graph_manager.graph_data.metadata["stackers"].append(stacker_payload)
        self._add_stacker_item(stacker_payload)
        self._refresh_single_stacker_layout(stacker_payload["id"])
        created_item = self.stacker_items.get(stacker_payload["id"])
        scene = self._safe_canvas_scene()
        if scene is not None:
            try:
                scene.clearSelection()
            except RuntimeError:
                scene = None
        if created_item:
            created_item.setSelected(True)
        self._refresh_stackers_panel(selected_id=stacker_payload["id"])
        self._clear_drag_link_state()
        self.graph_manager.save_state("Add stacker")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage(f"Created stacker: {stacker_payload['name']}")

    def toggle_stacker_creation_mode(self):
        self._clear_drag_link_state()
        dialog = StackerDetailsDialog(self, default_color="#292929")
        if not dialog.exec():
            self.statusBar().showMessage("Stacker creation cancelled")
            return
        self.create_stacker_from_panel(dialog.get_payload())

    def on_stacker_area_selected(self, rect: QRectF):
        self.toggle_stacker_creation_mode()

    def on_stacker_selection_cancelled(self):
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

    def _on_stacker_drag_started(self, stacker_id: str):
        self._active_stacker_drag_contexts.pop(str(stacker_id or "").strip(), None)
        self._active_stacker_move_snapshot = self._capture_stacker_move_snapshot(stacker_id)
        self._begin_drag_link_session("stacker", stacker_id)

    def _on_stacker_drag_finished(self, stacker_id: str):
        snapshot = self._active_stacker_move_snapshot or {}
        self._active_stacker_move_snapshot = None
        state = self._drag_link_state or {}
        if (
            str(state.get("kind", "") or "").strip() == "stacker"
            and str(state.get("item_id", "") or "").strip() == str(stacker_id or "").strip()
        ):
            self._apply_drag_link_action_if_needed()
        else:
            self._clear_drag_link_state()

        current_parent = self._get_stacker_parent_id(stacker_id)
        if current_parent:
            parent_rect = self._scene_rect_for_stacker_id(current_parent)
            item_rect = self._scene_rect_for_stacker_id(stacker_id)
            if (
                parent_rect.isValid()
                and item_rect.isValid()
                and not self._stacker_still_contains_drag_item(parent_rect, item_rect)
            ):
                self._restore_stacker_move_snapshot(snapshot)
                self._refresh_stacker_parent_chain(current_parent)
                self.statusBar().showMessage("Hold to UNLINK before moving stacker outside")

    def _on_stacker_item_position_changed(self, stacker_id: str, position: QPointF):
        if self._applying_stacker_cascade:
            return

        for edge_item in self.edge_items.values():
            source_id = getattr(getattr(edge_item.source_node, "node", None), "id", None) or getattr(edge_item.source_node, "stacker_id", "")
            target_id = getattr(getattr(edge_item.target_node, "node", None), "id", None) or getattr(edge_item.target_node, "stacker_id", "")
            if source_id == stacker_id or target_id == stacker_id:
                edge_item.update_path()

        parent_id = self._get_stacker_parent_id(stacker_id)
        if parent_id:
            self._refresh_stacker_parent_chain(parent_id)

        state = self._drag_link_state or {}
        if (
            str(state.get("kind", "") or "").strip() == "stacker"
            and str(state.get("item_id", "") or "").strip() == str(stacker_id or "").strip()
        ):
            self._update_drag_link_candidate()

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
        self._active_stacker_drag_contexts.pop(stacker_id, None)
        self.graph_manager.save_state("Move stacker")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage(f"Moved stacker: {payload.get('name', stacker_id)}")

    def _on_stacker_dragged_delta(self, stacker_id: str, delta: QPointF):
        if self._applying_stacker_cascade:
            return
        if abs(delta.x()) < 0.01 and abs(delta.y()) < 0.01:
            return

        context = self._active_stacker_drag_contexts.get(stacker_id)
        if context is None:
            tracked_items = []
            descendant_node_ids, descendant_stacker_ids = self._collect_stacker_descendants(stacker_id)
            for node_id in descendant_node_ids:
                item = self.node_widgets.get(node_id)
                if item is not None:
                    tracked_items.append(item)
            for child_stacker_id in descendant_stacker_ids:
                item = self.stacker_items.get(child_stacker_id)
                if item is not None:
                    tracked_items.append(item)

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

        dialog = StackerDetailsDialog(
            self,
            default_name=current_name,
            default_color="#292929",
        )
        dialog.setWindowTitle("Edit Stacker")
        if not dialog.exec():
            return

        data = dialog.get_payload()
        new_name = str(data.get("name", current_name)).strip() or current_name

        if new_name == current_name:
            return

        payload["name"] = new_name
        stacker_item.name = new_name
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

        parent_id = str(payload.get("parent_stacker_id", "") or "").strip()
        for node in self.graph_manager.graph_data.nodes.values():
            if self._get_node_parent_stacker_id(node) == stacker_id:
                self._set_node_parent_stacker_id(node, parent_id)
        for child_payload in self.graph_manager.graph_data.metadata.get("stackers", []):
            if str(child_payload.get("parent_stacker_id", "") or "").strip() == stacker_id:
                child_payload["parent_stacker_id"] = parent_id

        self.graph_manager.graph_data.metadata["stackers"] = [
            item
            for item in self.graph_manager.graph_data.metadata.get("stackers", [])
            if str(item.get("id", "")) != stacker_id
        ]

        edges_to_remove = []
        for edge_id, edge_item in self.edge_items.items():
            edge = self.graph_manager.get_edge(edge_id)
            if edge is None or edge.source_id == stacker_id or edge.target_id == stacker_id:
                edge_item.dispose()
                self.canvas_widget.scene.removeItem(edge_item)
                edges_to_remove.append(edge_id)
        for edge_id in edges_to_remove:
            self.graph_manager.remove_edge(edge_id, save_state=False)
            if edge_id in self.edge_items:
                del self.edge_items[edge_id]

        self.canvas_widget.scene.removeItem(stacker_item)
        del self.stacker_items[stacker_id]
        self._apply_stacker_layers_to_items()
        self._refresh_stacker_parent_chain(parent_id)
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

    def _selected_node_widgets(self):
        scene = getattr(self.canvas_widget, "scene", None)
        if scene is None:
            return []
        return [item for item in scene.selectedItems() if isinstance(item, NodeWidget)]

    def _selected_node_for_beatnote(self):
        selected_widgets = self._selected_node_widgets()
        if selected_widgets:
            return selected_widgets[0].node

        current_node = getattr(self.detail_panel, "current_node", None)
        if current_node is None:
            return None
        return self.graph_manager.get_node(current_node.id) or current_node

    def open_beatnote_workspace(self):
        from features.beatnote.ui.beatnote_main_window import BeatNoteMainWindow

        window = BeatNoteMainWindow.launch(parent=self, service=self.beatnote_service)
        if window is not None and getattr(window, "beatnote_panel", None) is not None:
            window.beatnote_panel.reload_notes()

    def apply_beatnote_to_selected_node(self, note, plain_text):
        clean_text = str(plain_text or "").strip()
        if not clean_text:
            self.statusBar().showMessage("That BeatNote does not have any text to reuse")
            return False

        target_node = self._selected_node_for_beatnote()
        if target_node is None:
            QApplication.clipboard().setText(clean_text)
            self.statusBar().showMessage("No node selected, so the BeatNote was copied to the clipboard")
            return False

        title = str(getattr(note, "title", "") or "").strip()
        note_block = clean_text if not title or clean_text.startswith(title) else f"{title}\n{clean_text}"
        existing_notes = str(target_node.data.get("notes", "") or "").strip()

        if note_block and note_block in existing_notes:
            self.statusBar().showMessage(f"'{title or 'BeatNote'}' is already in this node")
            return True

        target_node.data["notes"] = f"{existing_notes}\n\n{note_block}".strip() if existing_notes else note_block
        self.on_node_updated(target_node)
        self._refresh_selected_node_panel(target_node)
        self.graph_manager.save_state(f"Apply BeatNote to {target_node.type} node")
        self.update_undo_redo_buttons()
        self.statusBar().showMessage(f"Added '{title or 'BeatNote'}' to the selected {target_node.type} node")
        return True

    def _collect_nodes_for_duplication(self, preferred_node=None):
        selected_widgets = self._selected_node_widgets()
        if preferred_node is not None:
            if selected_widgets and any(widget.node.id == preferred_node.id for widget in selected_widgets):
                return [widget.node for widget in selected_widgets]
            return [preferred_node]
        return [widget.node for widget in selected_widgets]

    def _copy_nodes_to_clipboard(self, nodes) -> bool:
        unique_nodes = []
        seen_ids = set()
        for node in nodes or []:
            if node is None or node.id in seen_ids:
                continue
            seen_ids.add(node.id)
            unique_nodes.append(node)

        if not unique_nodes:
            return False

        origin_x = min(node.position.x() for node in unique_nodes)
        origin_y = min(node.position.y() for node in unique_nodes)
        self._node_clipboard = [
            {
                "type": node.type,
                "data": copy.deepcopy(node.data),
                "offset_x": float(node.position.x() - origin_x),
                "offset_y": float(node.position.y() - origin_y),
            }
            for node in unique_nodes
        ]
        self._node_clipboard_paste_count = 0
        return True

    def _clear_scene_selection(self):
        scene = getattr(self.canvas_widget, "scene", None)
        if scene is not None:
            scene.clearSelection()

    def _paste_nodes_from_clipboard(self, anchor_pos: QPointF | None = None):
        if not self._node_clipboard:
            self.statusBar().showMessage("No copied nodes to paste")
            return []

        if anchor_pos is None:
            viewport_center = self.canvas_widget.viewport().rect().center()
            anchor_pos = self.canvas_widget.mapToScene(viewport_center)

        self._node_clipboard_paste_count += 1
        paste_shift = 28.0 * self._node_clipboard_paste_count
        pasted_nodes = []

        self._clear_scene_selection()

        for entry in self._node_clipboard:
            position = QPointF(
                float(anchor_pos.x()) + float(entry.get("offset_x", 0.0)) + paste_shift,
                float(anchor_pos.y()) + float(entry.get("offset_y", 0.0)) + paste_shift,
            )
            node = self.graph_manager.add_node(
                str(entry.get("type") or ""),
                position,
                copy.deepcopy(entry.get("data") or {}),
                save_state=False,
            )
            self.create_node_visual(node)
            pasted_nodes.append(node)

            node_widget = self.node_widgets.get(node.id)
            if node_widget is not None:
                node_widget.setSelected(True)

        if pasted_nodes:
            self.graph_manager.save_state(
                "Paste node" if len(pasted_nodes) == 1 else f"Paste {len(pasted_nodes)} nodes"
            )
            self._mark_active_document_dirty()
            self.update_undo_redo_buttons()
            self.sync_custom_node_templates_metadata()
            self.statusBar().showMessage(
                f"Pasted {len(pasted_nodes)} node" if len(pasted_nodes) == 1 else f"Pasted {len(pasted_nodes)} nodes"
            )

        return pasted_nodes

    def duplicate_nodes(self, nodes):
        if not self._copy_nodes_to_clipboard(nodes):
            self.statusBar().showMessage("No nodes selected to duplicate")
            return []

        origin_x = min(node.position.x() for node in nodes)
        origin_y = min(node.position.y() for node in nodes)
        return self._paste_nodes_from_clipboard(QPointF(origin_x, origin_y))

    def duplicate_node(self, node):
        if node is None:
            return []
        target_nodes = self._collect_nodes_for_duplication(node)
        return self.duplicate_nodes(target_nodes)

    def copy_selected_nodes(self):
        nodes = self._collect_nodes_for_duplication()
        if not self._copy_nodes_to_clipboard(nodes):
            self.statusBar().showMessage("No nodes selected to copy")
            return False

        self.statusBar().showMessage(
            "Copied 1 node" if len(nodes) == 1 else f"Copied {len(nodes)} nodes"
        )
        return True

    def _apply_detail_panel_visibility(self, visible: bool):
        if not hasattr(self, "main_splitter") or not self.main_splitter:
            return

        sizes = self.main_splitter.sizes()
        if len(sizes) < 2:
            return

        if visible:
            self.detail_panel.show()
            detail_width = max(450, int(self._detail_panel_last_width or 460))
            available = max(720, sum(sizes))
            canvas_width = max(300, available - detail_width)
            self.main_splitter.setSizes([canvas_width, detail_width])
            return

        current_width = sizes[1]
        if current_width > 0:
            self._detail_panel_last_width = current_width

        self.detail_panel.hide()
        self.main_splitter.setSizes([sizes[0] + sizes[1], 0])

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
        if not missing_tools:
            self._emit_ndc_tool_event(
                "analysis_captured",
                tool_name="tools_downloader",
                surface="analysis_utility",
                result_summary="Required tools scan found no missing tools.",
                result_status="success",
                result_count=0,
            )
        
        # Se houver ferramentas em falta, perguntar se quer instalar
        if missing_tools:
            preview = ", ".join(missing_tools[:5])
            self._emit_ndc_tool_event(
                "analysis_captured",
                tool_name="tools_downloader",
                surface="analysis_utility",
                result_summary=compact_tool_summary(
                    f"Required tools scan found {len(missing_tools)} missing tool(s): {preview}."
                ),
                result_status="partial",
                result_count=len(missing_tools),
                artifact_refs=tuple(missing_tools[:5]),
            )
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
                install_success = download_manager.request_installation()
                self._emit_ndc_tool_event(
                    "executed",
                    tool_name="tools_downloader",
                    surface="helper_window",
                    result_summary=(
                        f"Automatic installation flow completed for {len(missing_tools)} missing tool(s)."
                        if install_success
                        else f"Automatic installation flow did not complete successfully for {len(missing_tools)} missing tool(s)."
                    ),
                    result_status="success" if install_success else "failure",
                    result_count=len(missing_tools),
                    artifact_refs=tuple(missing_tools[:5]),
                )
                if install_success:
                    QMessageBox.information(
                        self,
                        "Instalação Concluída",
                        "Ferramentas instaladas com sucesso! Agora você pode usá-las."
                    )
                    # Atualizar a UI do tools manager
                    if hasattr(self, 'tools_integration') and self.tools_integration.tools_manager:
                        self.tools_integration.tools_manager.check_available_tools()
            else:
                self._emit_ndc_tool_event(
                    "helper_invoked",
                    tool_name="tools_downloader",
                    surface="helper_window",
                    result_summary=f"Automatic installation prompt was declined for {len(missing_tools)} missing tool(s).",
                    result_status="cancelled",
                    result_count=len(missing_tools),
                    artifact_refs=tuple(missing_tools[:5]),
                )

    def _load_accessibility_preferences(self) -> None:
        settings = QSettings('BeatRooter', 'BeatRooter')
        self._suppress_missing_tools_prompt = bool(
            settings.value('accessibility/suppress_missing_tools_prompt', False, type=bool)
        )
        self._canvas_background_style = str(
            settings.value('accessibility/canvas_background_style', 'grid')
        ).strip().lower()
        if self._canvas_background_style not in {'grid', 'dots'}:
            self._canvas_background_style = 'grid'
        self._edge_render_style = DynamicEdge.normalize_render_style(
            settings.value('accessibility/edge_render_style', 'classic_dashed')
        )

    def _set_suppress_missing_tools_prompt(self, suppress: bool) -> None:
        self._suppress_missing_tools_prompt = bool(suppress)
        settings = QSettings('BeatRooter', 'BeatRooter')
        settings.setValue('accessibility/suppress_missing_tools_prompt', self._suppress_missing_tools_prompt)
        if self._suppress_missing_tools_prompt:
            self.statusBar().showMessage('Missing tools prompt silenced')
        else:
            self.statusBar().showMessage('Missing tools prompt enabled')

    def _set_canvas_background_style(self, style: str) -> None:
        normalized_style = (style or 'grid').strip().lower()
        if normalized_style not in {'grid', 'dots'}:
            normalized_style = 'grid'

        self._canvas_background_style = normalized_style
        self._apply_canvas_accessibility_preferences()

        settings = QSettings('BeatRooter', 'BeatRooter')
        settings.setValue('accessibility/canvas_background_style', self._canvas_background_style)

        if self._canvas_background_style == 'dots':
            self.statusBar().showMessage('Canvas background changed to dots')
        else:
            self.statusBar().showMessage('Canvas background changed to grid')

    def _set_edge_render_style(self, style_key: str) -> None:
        normalized_style = DynamicEdge.normalize_render_style(style_key)
        self._edge_render_style = normalized_style
        self._apply_canvas_accessibility_preferences()

        settings = QSettings('BeatRooter', 'BeatRooter')
        settings.setValue('accessibility/edge_render_style', self._edge_render_style)

        style_label = DynamicEdge.render_style_options().get(self._edge_render_style, 'Classic Dashed')
        self.statusBar().showMessage(f'Edge style changed to {style_label}')

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
        
        self._emit_ndc_tool_event(
            "helper_invoked",
            tool_name="beathelper_manual_finder",
            surface="helper_window",
            result_summary="BeatHelper manual finder opened.",
        )

        dialog = BeatHelperDialog(
            self,
            ndc_recorder=self._emit_ndc_tool_event,
            ndc_related_node_id=self._current_ndc_related_node_id(),
        )
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
        found_binaries = 0
        for binary in binaries:
            path = shutil.which(binary)
            if not path:
                lines.append(f"- {binary}: NOT FOUND in PATH")
                continue
            found_binaries += 1
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
        recommendations_count = len(recommendations)
        self._emit_ndc_tool_event(
            "analysis_captured",
            tool_name="permissions_diagnostics",
            surface="analysis_utility",
            result_summary=(
                f"Permissions diagnostics checked {len(binaries)} core binaries; "
                f"{found_binaries} found, {len(binaries) - found_binaries} missing, "
                f"{recommendations_count} recommendation(s) generated."
            ),
            result_status="success" if recommendations_count == 0 else "partial",
            result_count=len(binaries),
            command_ref="permissions_diagnostics",
            artifact_refs=tuple(binaries),
        )
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

    def _add_imported_node(self, node_type: str, position: QPointF, custom_data: dict, save_state: bool = True):
        node_data = NodeFactory.create_node_data(node_type, custom_data=custom_data, category=self.category)
        node = self.graph_manager.add_node(node_type, position, node_data, save_state=save_state)
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
                self._emit_ndc_tool_event(
                    "helper_invoked",
                    tool_name="flipper_workspace_importer",
                    surface="import_wizard",
                    result_summary="Flipper workspace import was cancelled before selecting a root folder.",
                    result_status="cancelled",
                )
                return

            manual_root = QFileDialog.getExistingDirectory(self, 'Select Flipper Root Folder')
            if not manual_root:
                self._emit_ndc_tool_event(
                    "helper_invoked",
                    tool_name="flipper_workspace_importer",
                    surface="import_wizard",
                    result_summary="Flipper workspace import was cancelled without choosing a folder.",
                    result_status="cancelled",
                )
                return
            root_paths = [manual_root]
            settings.setValue('flipper_last_root_path', manual_root)
        else:
            # Persist the first detected/resolved root for future RPC-only sessions.
            settings.setValue('flipper_last_root_path', root_paths[0])

        if self.flipper_explorer_dialog and self.flipper_explorer_dialog.isVisible():
            self.flipper_explorer_dialog.raise_()
            self.flipper_explorer_dialog.activateWindow()
            self._emit_ndc_tool_event(
                "helper_invoked",
                tool_name="flipper_workspace_importer",
                surface="import_wizard",
                result_summary="Flipper explorer was reused for the current workspace root.",
                result_status="success",
                result_count=len(root_paths),
                artifact_refs=build_artifact_refs(root_paths),
            )
            return

        dialog = FlipperExplorerDialog(root_paths, self)
        dialog.setModal(False)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.files_import_requested.connect(self.import_selected_flipper_files)
        dialog.destroyed.connect(self._on_flipper_explorer_closed)
        dialog.show()

        self.flipper_explorer_dialog = dialog
        self._emit_ndc_tool_event(
            "helper_invoked",
            tool_name="flipper_workspace_importer",
            surface="import_wizard",
            result_summary=compact_tool_summary(
                f"Flipper explorer opened with {len(root_paths)} root path(s)."
            ),
            result_status="success",
            result_count=len(root_paths),
            target_ref=selected_serial_port or None,
            artifact_refs=build_artifact_refs(root_paths),
        )
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
            self._emit_ndc_tool_event(
                "imported",
                tool_name="flipper_workspace_importer",
                surface="import_wizard",
                result_summary=f"Selected {len(valid_paths)} Flipper file(s), but none were parsed into canvas nodes.",
                result_status="failure",
                result_count=0,
                target_ref=root_path or None,
                artifact_refs=build_artifact_refs(valid_paths, root_path=root_path),
            )
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
            self._add_imported_node(node_type, position, file_data, save_state=False)
            imported.append(artifact)

        self.sync_custom_node_templates_metadata()
        self.toolbox.refresh_filter_categories()
        self.toolbox.create_sections()
        self.toolbox.filter_nodes()
        self.graph_manager.save_state(f"Import {len(imported)} Flipper file(s)")
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
        self._emit_ndc_tool_event(
            "imported",
            tool_name="flipper_workspace_importer",
            surface="import_wizard",
            result_summary=compact_tool_summary(
                f"Imported {len(imported)} Flipper file(s) into the canvas. Modules: {module_summary or 'general'}."
            ),
            result_status="success",
            result_count=len(imported),
            target_ref=root_path or None,
            artifact_refs=build_artifact_refs(valid_paths, root_path=root_path),
        )

    def toggle_external_tools(self):
        if hasattr(self, 'detail_panel'):
            self.detail_panel.show_tools_tab()
        self.tools_integration.toggle_tools_panel()
    
    def draw_connection(self, edge):
        source_widget = self._resolve_connection_widget(edge.source_id)
        target_widget = self._resolve_connection_widget(edge.target_id)
        if source_widget and target_widget:
            print(f"Creating connection from {edge.source_id} to {edge.target_id}")

            edge_item = DynamicEdge(source_widget, target_widget, edge)
            edge_item.setZValue(self._edge_z_value(edge))
            edge_item.set_render_style(self._edge_render_style)
            self.canvas_widget.scene.addItem(edge_item)
            self.edge_items[edge.id] = edge_item
            self._sync_edge_visibility()
    
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
                edge_item.dispose()
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
        self.undo_handler.trigger()
    
    def redo(self):
        self.redo_handler.trigger()
    
    def update_undo_redo_buttons(self):
        self.undo_handler.refresh()
        self.redo_handler.refresh()

    def _capture_nodes_for_move(self, preferred_node=None):
        selected_nodes = self._collect_nodes_for_duplication(preferred_node)
        if selected_nodes:
            return selected_nodes
        if preferred_node is not None:
            return [preferred_node]
        return []

    def _on_node_move_started(self, node):
        tracked_nodes = self._capture_nodes_for_move(node)
        if not tracked_nodes:
            self._active_node_move_snapshot = None
            return

        self._active_node_move_snapshot = {
            tracked_node.id: QPointF(tracked_node.position)
            for tracked_node in tracked_nodes
        }
        self._begin_drag_link_session("node", node.id)

    def _on_node_move_finished(self, node):
        snapshot = self._active_node_move_snapshot or {}
        self._active_node_move_snapshot = None
        state = self._drag_link_state or {}
        if (
            str(state.get("kind", "") or "").strip() == "node"
            and str(state.get("item_id", "") or "").strip() == str(node.id)
        ):
            self._apply_drag_link_action_if_needed()
        else:
            self._clear_drag_link_state()
        if not snapshot:
            return

        moved_node_ids = []
        for node_id, original_position in snapshot.items():
            current_node = self.graph_manager.get_node(node_id)
            if current_node is None:
                continue
            current_position = current_node.position
            if (
                abs(current_position.x() - original_position.x()) >= 0.01
                or abs(current_position.y() - original_position.y()) >= 0.01
            ):
                moved_node_ids.append(node_id)

        if not moved_node_ids:
            return

        description = "Move node" if len(moved_node_ids) == 1 else f"Move {len(moved_node_ids)} nodes"
        self.graph_manager.save_state(description)
        self.statusBar().showMessage(description)

    def _on_node_widget_position_changed(self, node_id: str):
        if self._applying_stacker_cascade:
            return

        node = self.graph_manager.get_node(node_id)
        if node is None:
            return

        parent_id = self._get_node_parent_stacker_id(node)
        if parent_id:
            self._refresh_stacker_parent_chain(parent_id)

        state = self._drag_link_state or {}
        if (
            str(state.get("kind", "") or "").strip() == "node"
            and str(state.get("item_id", "") or "").strip() == str(node_id or "").strip()
        ):
            self._update_drag_link_candidate()

    def _bind_node_widget_signals(self, node_widget):
        node_widget.node_updated.connect(self.on_node_selected)
        node_widget.connection_started.connect(self.start_connection)
        node_widget.duplicate_requested.connect(self.duplicate_node)
        node_widget.move_started.connect(self._on_node_move_started)
        node_widget.move_finished.connect(self._on_node_move_finished)
        node_widget.positionChanged.connect(
            lambda node_id=node_widget.node.id: self._on_node_widget_position_changed(node_id)
        )
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

        self._refresh_all_stacker_layouts()
        
        for edge in self.graph_manager.graph_data.edges.values():
            self.draw_connection(edge)

        self._sync_stacker_content_visibility()

        self.refresh_tool_nodes()
        
        if not self.detail_panel.current_node:
            return

        current_node_id = self.detail_panel.current_node.id
        current_node = self.graph_manager.get_node(current_node_id)
        if current_node:
            self.detail_panel.display_node(current_node)
            return

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
        parent_id = self._get_node_parent_stacker_id(node)
        if parent_id:
            self._refresh_stacker_parent_chain(parent_id)
        self._sync_stacker_content_visibility()

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
        wordlist_path = None
        login_value = None
        if custom_command:
            command_parts = shlex.split(custom_command, posix=not sys.platform.startswith("win"))
        else:
            options = str(node.data.get("options", "") or "").strip()
            if tool_name == "hydra":
                login_resolution = ToolNodeService.resolve_hydra_login(self.graph_manager, node)
                if not login_resolution.get("compatible"):
                    if node.id in self.node_widgets:
                        self.node_widgets[node.id].update_display()
                    QMessageBox.warning(self, "Tool Node", login_resolution.get("reason", "Hydra requires a login source."))
                    return
                login_value = str(login_resolution.get("login", "") or "").strip() or None

            requires_wordlist = ToolNodeService.tool_requires_wordlist(tool_name, options)
            wordlist_resolution = ToolNodeService.resolve_wordlist(self.graph_manager, node)
            if requires_wordlist and not wordlist_resolution.get("compatible"):
                if node.id in self.node_widgets:
                    self.node_widgets[node.id].update_display()
                QMessageBox.warning(self, "Tool Node", wordlist_resolution.get("reason", "Connect a compatible Wordlists node."))
                return

            wordlist_node_id = str(wordlist_resolution.get("source_node_id", "") or "").strip()
            if wordlist_node_id:
                wordlist_node = self.graph_manager.get_node(wordlist_node_id)
                if wordlist_node is None:
                    QMessageBox.warning(self, "Tool Node", "The resolved Wordlists node no longer exists.")
                    return
                try:
                    wordlist_path = WordlistService.materialize_node_to_temp(wordlist_node.id, wordlist_node.data)
                except WordlistValidationError as exc:
                    QMessageBox.warning(self, "Tool Node", str(exc))
                    return

            command_parts = tool_manager.get_command_for_tool(
                tool_name,
                target,
                options,
                wordlist_path=wordlist_path,
                login_value=login_value,
            )

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

        status_target = target or "configured input"
        if wordlist_path:
            self.statusBar().showMessage(
                f"Running {ToolNodeService.get_tool_display_name(tool_name)} against {status_target} with wordlist"
            )
        else:
            self.statusBar().showMessage(f"Running {ToolNodeService.get_tool_display_name(tool_name)} against {status_target}")

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
        exit_code = ToolNodeService.normalize_tool_exit_code(tool_name, output_text, exit_code)
        error_result_payload = ToolNodeService.build_tool_error_result_payload(tool_name, target, output_text)
        mapped_error = ToolNodeService.map_known_tool_error(tool_name, output_text)

        if mapped_error and error_result_payload:
            node.data["last_error"] = mapped_error

        created_nodes = []
        if exit_code == 0 and tool_name and not error_result_payload:
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
                if error_result_payload:
                    diagnostic_node = self._create_tool_error_result_node(node, error_result_payload)
                    if diagnostic_node:
                        created_nodes = [diagnostic_node]
                elif tool_name == "tshark":
                    node.data["output_summary"] = "TShark completed with no structured entities extracted."
                else:
                    fallback_nodes = self._create_tool_fallback_result_nodes(node, output_text, exit_code)
                    if fallback_nodes:
                        created_nodes = fallback_nodes

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
            if error_result_payload:
                diagnostic_node = self._create_tool_error_result_node(node, error_result_payload)
                if diagnostic_node:
                    created_nodes = [diagnostic_node]
                    node.data["created_node_ids"] = [diagnostic_node.id]
                    node.data["output_summary"] = error_result_payload.get("summary_text", str(node.data.get("last_error", "") or ""))
                else:
                    node.data["output_summary"] = str(node.data.get("last_error", "") or "")
            else:
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

    def _create_tool_fallback_result_nodes(self, tool_node, output_text, exit_code):
        tool_name = str(tool_node.data.get("tool_name", "") or "").strip().lower()
        target = str(tool_node.data.get("resolved_target", "") or tool_node.data.get("manual_target", ""))
        warning_payload = ToolNodeService.build_tool_warning_payload(
            tool_name,
            target,
            output_text,
            exit_code,
        )
        if warning_payload:
            warning_node = self._create_special_tool_result_node(tool_node, warning_payload)
            return [warning_node] if warning_node else []

        result_payloads = ToolNodeService.build_tool_result_payloads(
            tool_name,
            target,
            output_text,
            exit_code,
        )
        if result_payloads:
            return self._create_special_tool_result_nodes(tool_node, result_payloads)

        result_type = ToolNodeService.get_tool_spec(tool_name).get("result_node_type", "note")
        custom_data = ToolNodeService.build_fallback_result_data(
            tool_name,
            target,
            output_text,
            exit_code,
        )

        node_data = NodeFactory.create_node_data(result_type, custom_data=custom_data, category=self.category)
        fallback_position = QPointF(tool_node.position.x() + 210, tool_node.position.y())
        result_node = self.graph_manager.add_node(result_type, fallback_position, node_data, save_state=False)
        result_node.data["generated_by_tool_id"] = tool_node.id
        self.create_node_visual(result_node)
        self._connect_tool_node_to_result(tool_node, result_node)
        return [result_node]

    def _create_special_tool_result_nodes(self, tool_node, result_payloads):
        created_nodes = []
        for payload in result_payloads or []:
            result_node = self._create_special_tool_result_node(tool_node, payload)
            if result_node:
                created_nodes.append(result_node)
        return created_nodes

    def _create_special_tool_result_node(self, tool_node, result_payload):
        template = result_payload.get("template") or {}
        node_type = str(result_payload.get("node_type", "") or "").strip()
        if not node_type:
            return None

        NodeFactory.register_custom_node_template(
            name=template.get("name", node_type.replace("_", " ").title()),
            node_type=node_type,
            color=template.get("color"),
            default_data=template.get("default_data", {}),
            symbol=template.get("symbol"),
            category=template.get("category"),
            category_label=template.get("category_label"),
            overwrite=True,
        )
        NodeFactory.set_node_template_override(
            node_type=node_type,
            removed_fields=template.get("removed_fields", []),
        )
        self.sync_custom_node_templates_metadata()

        node_data = NodeFactory.create_node_data(node_type, custom_data=result_payload.get("data") or {})
        result_position = QPointF(tool_node.position.x() + 210, tool_node.position.y())
        result_node = self.graph_manager.add_node(node_type, result_position, node_data, save_state=False)
        result_node.data["generated_by_tool_id"] = tool_node.id
        self.create_node_visual(result_node)
        self._connect_tool_node_to_result(tool_node, result_node)
        return result_node

    def _create_tool_error_result_node(self, tool_node, error_payload):
        if not error_payload:
            return None

        template = error_payload.get("template") or {}
        node_type = str(error_payload.get("node_type", "") or "").strip()
        if not node_type:
            return None

        NodeFactory.register_custom_node_template(
            name=template.get("name", node_type.replace("_", " ").title()),
            node_type=node_type,
            color=template.get("color"),
            default_data=template.get("default_data", {}),
            symbol=template.get("symbol"),
            category=template.get("category"),
            category_label=template.get("category_label"),
            overwrite=True,
        )
        NodeFactory.set_node_template_override(
            node_type=node_type,
            removed_fields=template.get("removed_fields", []),
        )
        self.sync_custom_node_templates_metadata()

        node_data = NodeFactory.create_node_data(node_type, custom_data=error_payload.get("data") or {})
        error_position = QPointF(tool_node.position.x() + 210, tool_node.position.y())
        result_node = self.graph_manager.add_node(node_type, error_position, node_data, save_state=False)
        result_node.data["generated_by_tool_id"] = tool_node.id
        self.create_node_visual(result_node)
        self._connect_tool_node_to_result(tool_node, result_node)
        return result_node

    def _connect_tool_node_to_result(self, tool_node, result_node):
        try:
            edge = self.graph_manager.connect_nodes(tool_node.id, result_node.id, "", save_state=False)
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
                    source_id = getattr(getattr(edge_item.source_node, "node", None), "id", None) or getattr(edge_item.source_node, "stacker_id", "")
                    target_id = getattr(getattr(edge_item.target_node, "node", None), "id", None) or getattr(edge_item.target_node, "stacker_id", "")
                    if source_id == node.id or target_id == node.id:
                        edge_item.update_path()

        self.refresh_tool_nodes()

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
        parent_stacker_id = self._get_node_parent_stacker_id(node)

        running_thread = self.tool_run_threads.pop(node.id, None)
        self.tool_output_cache.pop(node.id, None)
        if running_thread and running_thread.isRunning():
            running_thread.terminate()
            running_thread.wait(1500)
            running_thread.deleteLater()

        self.graph_manager.remove_node(node.id, save_state=save_state)

        if node.id in self.node_widgets:
            node_widget = self.node_widgets[node.id]
            self.canvas_widget.scene.removeItem(node_widget)
            del self.node_widgets[node.id]

        edges_to_remove = []
        for edge_id, edge_item in self.edge_items.items():
            edge = self.graph_manager.get_edge(edge_id)
            if edge is None or edge.source_id == node.id or edge.target_id == node.id:
                edge_item.dispose()
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
        if parent_stacker_id:
            self._refresh_stacker_parent_chain(parent_stacker_id)

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
        source_id = getattr(getattr(source_widget, "node", None), "id", None) or getattr(source_widget, "stacker_id", "")
        print(f"Starting connection from item: {source_id}")
        self.connection_source = source_widget
        
        self.canvas_widget.viewport().installEventFilter(self)
        self.statusBar().showMessage("Connection mode: Click target node/stacker or ESC to cancel")
    
    def create_connection(self, source_id, target_id):
        try:
            print(f"Attempting to connect {source_id} to {target_id}")

            edge = self.graph_manager.connect_items(source_id, target_id, "")
            
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
            self._emit_ndc_project_event(
                "opened",
                graph_data=self.documents[tab_index]["graph_data"],
                reason="new_tab",
            )
        
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

    def load_graph_data(
        self,
        graph_data,
        node_counter=None,
        edge_counter=None,
        history=None,
        history_position=None,
    ):
        self._stop_all_tool_threads()
        if hasattr(graph_data, "metadata") and isinstance(graph_data.metadata, dict):
            self._ensure_ndc_project_id(graph_data.metadata)
        NodeFactory.load_custom_node_templates(graph_data.metadata.get('custom_node_templates', {}))
        NodeFactory.load_node_template_settings(graph_data.metadata.get('node_template_settings', {}))
        self.graph_manager.load_snapshot(
            graph_data,
            node_counter=node_counter,
            edge_counter=edge_counter,
            history=history,
            history_position=history_position,
            description="Loaded investigation",
        )
        self.refresh_canvas_from_graph()
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
                self._emit_ndc_project_event(
                    "opened",
                    graph_data=self.documents[tab_index]["graph_data"],
                    file_path=filename,
                    reason="open_dialog",
                )
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
                self._emit_ndc_snapshot_event(
                    "checkpoint_exported",
                    graph_data=self.graph_manager.graph_data,
                    trigger="export_png",
                    summary="Checkpoint captured on PNG export.",
                )
                self._emit_ndc_tool_event(
                    "exported",
                    tool_name="canvas_exporter",
                    surface="export_flow",
                    result_summary=f"Exported investigation canvas as PNG with {len(self.canvas_widget.scene.items())} scene item(s).",
                    result_status="success",
                    result_count=len(self.canvas_widget.scene.items()),
                    artifact_refs=(filename,),
                )
                self.statusBar().showMessage(f"Exported PNG: {filename}")
                QMessageBox.information(self, "Export Successful", f"PNG exported successfully to:\n{filename}")
            else:
                self._emit_ndc_tool_event(
                    "exported",
                    tool_name="canvas_exporter",
                    surface="export_flow",
                    result_summary="PNG export failed for the current investigation canvas.",
                    result_status="failure",
                    artifact_refs=(filename,),
                )
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
                self._emit_ndc_snapshot_event(
                    "checkpoint_exported",
                    graph_data=self.graph_manager.graph_data,
                    trigger="export_svg",
                    summary="Checkpoint captured on SVG export.",
                )
                self._emit_ndc_tool_event(
                    "exported",
                    tool_name="canvas_exporter",
                    surface="export_flow",
                    result_summary="Exported investigation canvas as SVG.",
                    result_status="success",
                    artifact_refs=(filename,),
                )
                self.statusBar().showMessage(f"Exported SVG: {filename}")
            else:
                self._emit_ndc_tool_event(
                    "exported",
                    tool_name="canvas_exporter",
                    surface="export_flow",
                    result_summary="SVG export failed for the current investigation canvas.",
                    result_status="failure",
                    artifact_refs=(filename,),
                )
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
                self._emit_ndc_snapshot_event(
                    "checkpoint_exported",
                    graph_data=self.graph_manager.graph_data,
                    trigger="export_json",
                    summary="Checkpoint captured on JSON export.",
                )
                self._emit_ndc_tool_event(
                    "exported",
                    tool_name="canvas_exporter",
                    surface="export_flow",
                    result_summary="Exported investigation graph as JSON.",
                    result_status="success",
                    artifact_refs=(filename,),
                )
                self.statusBar().showMessage(f"Exported JSON: {filename}")
            else:
                self._emit_ndc_tool_event(
                    "exported",
                    tool_name="canvas_exporter",
                    surface="export_flow",
                    result_summary="JSON export failed for the current investigation graph.",
                    result_status="failure",
                    artifact_refs=(filename,),
                )
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
        self.ndc_snapshot_timer.stop()
        for document in self.documents:
            self._emit_ndc_snapshot_event(
                "checkpoint_closed",
                graph_data=document.get("graph_data"),
                trigger="app_exit",
                summary="Checkpoint captured during application shutdown.",
            )
            self._emit_ndc_project_event(
                "closed",
                graph_data=document.get("graph_data"),
                file_path=document.get("file_path"),
                reason="app_exit",
            )
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
        focus_widget = QApplication.focusWidget()
        if focus_widget is not None and any(
            focus_widget.inherits(class_name)
            for class_name in ("QLineEdit", "QTextEdit", "QPlainTextEdit", "QAbstractSpinBox", "QComboBox")
        ):
            super().keyPressEvent(event)
            return

        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.undo()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_Y:
                self.redo()
                event.accept()
                return
            elif event.key() == Qt.Key.Key_C:
                if self.copy_selected_nodes():
                    event.accept()
                    return
            elif event.key() == Qt.Key.Key_V:
                if self._node_clipboard:
                    self._paste_nodes_from_clipboard()
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
            
            source_id = getattr(getattr(self.connection_source, "node", None), "id", None) or getattr(self.connection_source, "stacker_id", "")
            for item in items:
                target_id = getattr(getattr(item, "node", None), "id", None) or getattr(item, "stacker_id", "")
                if isinstance(item, (NodeWidget, StackerItem)) and item != self.connection_source and target_id:
                    print(f"Target item found: {target_id}")
                    self.create_connection(source_id, target_id)
                    
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
