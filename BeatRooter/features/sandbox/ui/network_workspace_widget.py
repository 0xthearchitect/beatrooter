from PyQt6.QtCore import QItemSelectionModel, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from features.sandbox.core.network_state import NetworkState
from features.sandbox.core.network_trace_engine import NetworkTraceEngine, TraceRequest, format_trace_result


class NetworkWorkspaceWidget(QWidget):
    status_message = pyqtSignal(str)

    DEVICE_HEADERS = ["Device", "Type", "Mgmt IP", "Role"]
    SEGMENT_HEADERS = ["VLAN", "Name", "CIDR", "Gateway"]
    RULE_HEADERS = ["Source", "Target", "Proto", "Port", "Action"]
    INTERFACE_HEADERS = ["Device", "Interface", "IP/CIDR", "VLAN", "Status"]
    EXPOSURE_HEADERS = ["Device", "Service", "Proto", "Port", "Visibility"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_editor_font_size = 11
        self.current_editor_font_size = self.default_editor_font_size
        self._dirty = False
        self._loading_state = False
        self.selected_topology_device = None
        self.selected_topology_segment = None
        self.selected_topology_interface = None
        self.last_trace_result = None
        self.focus_context = None
        self._build_ui()
        self._bind_events()
        self._apply_styles()
        self.reset_workspace()

    def _build_ui(self):
        self.step_definitions = [
            ("Overview", "Notes, context, and rough shape of the lab."),
            ("Devices", "Hosts, firewalls, switches, and appliances."),
            ("Wiring", "Segments, interfaces, and how things meet."),
            ("Expose", "Services, rules, and what can be reached."),
            ("Trace", "Packet tests and trace output."),
        ]

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("NetworkWorkspaceSplitter")
        root_layout.addWidget(self.main_splitter)

        self.main_splitter.addWidget(self._build_workspace_panel())
        self.main_splitter.addWidget(self._build_companion_panel())
        self.main_splitter.setSizes([1180, 330])
        self._set_activity_view(0)

    def _build_workspace_panel(self):
        panel = QFrame()
        panel.setObjectName("NetworkWorkspacePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        self.hero_card = QFrame()
        self.hero_card.setObjectName("NetworkHeroCard")
        hero_layout = QHBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(16)

        hero_copy_layout = QVBoxLayout()
        hero_copy_layout.setSpacing(6)
        hero_eyebrow = QLabel("Custom Network Workspace")
        hero_eyebrow.setObjectName("NetworkEyebrow")
        title = QLabel("Network Lab")
        title.setObjectName("NetworkMainTitle")
        self.hero_summary_label = QLabel("A modular lab for topology, policy, and packet testing.")
        self.hero_summary_label.setObjectName("NetworkHeroSummary")
        self.hero_summary_label.setWordWrap(True)
        hero_copy_layout.addWidget(hero_eyebrow)
        hero_copy_layout.addWidget(title)
        hero_copy_layout.addWidget(self.hero_summary_label)
        hero_layout.addLayout(hero_copy_layout, 1)

        hero_meta_layout = QVBoxLayout()
        hero_meta_layout.setSpacing(8)
        hero_meta_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.hero_step_chip = QLabel("Overview")
        self.hero_step_chip.setObjectName("NetworkHeroChip")
        self.lab_context_label = QLabel("Topology in the center, configuration modules around it.")
        self.lab_context_label.setObjectName("NetworkContextLabel")
        self.lab_context_label.setWordWrap(True)
        self.lab_context_label.setMaximumWidth(240)
        self.lab_context_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        hero_meta_layout.addWidget(self.hero_step_chip, 0, Qt.AlignmentFlag.AlignRight)
        hero_meta_layout.addWidget(self.lab_context_label)
        hero_layout.addLayout(hero_meta_layout)
        layout.addWidget(self.hero_card)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setObjectName("NetworkWorkbenchSplitter")
        self.workspace_splitter.addWidget(self._build_module_rail())
        self.workspace_splitter.addWidget(self._build_workbench_panel())
        self.workspace_splitter.setSizes([170, 980])
        layout.addWidget(self.workspace_splitter, 1)

        return panel

    def _build_module_rail(self):
        panel = QFrame()
        panel.setObjectName("NetworkModuleRail")
        panel.setFixedWidth(170)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Modules")
        title.setObjectName("NetworkRailTitle")
        layout.addWidget(title)

        self.step_buttons = []
        for step_name, _ in self.step_definitions:
            button = self._create_step_button(step_name)
            self.step_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)
        return panel

    def _build_workbench_panel(self):
        panel = QFrame()
        panel.setObjectName("NetworkWorkbenchPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.workbench_scroll = QScrollArea()
        self.workbench_scroll.setObjectName("NetworkWorkbenchScroll")
        self.workbench_scroll.setWidgetResizable(True)
        self.workbench_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.workbench_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.workbench_scroll)

        scroll_content = QWidget()
        scroll_content.setObjectName("NetworkWorkbenchScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(14)
        self.workbench_scroll.setWidget(scroll_content)

        self.topology_card = QFrame()
        self.topology_card.setObjectName("NetworkTopologyCard")
        topology_layout = QVBoxLayout(self.topology_card)
        topology_layout.setContentsMargins(16, 14, 16, 14)
        topology_layout.setSpacing(12)

        topology_header = QHBoxLayout()
        topology_title = QLabel("Topology View")
        topology_title.setObjectName("NetworkSectionTitle")
        self.topology_meta_label = QLabel("A live sketch of devices, segments, and exposed services.")
        self.topology_meta_label.setObjectName("NetworkSubtleLabel")
        topology_header.addWidget(topology_title)
        topology_header.addStretch(1)
        topology_header.addWidget(self.topology_meta_label)
        topology_layout.addLayout(topology_header)

        self.topology_canvas = QFrame()
        self.topology_canvas.setObjectName("NetworkTopologyCanvas")
        self.topology_canvas_layout = QVBoxLayout(self.topology_canvas)
        self.topology_canvas_layout.setContentsMargins(14, 14, 14, 14)
        self.topology_canvas_layout.setSpacing(10)
        topology_layout.addWidget(self.topology_canvas)
        scroll_layout.addWidget(self.topology_card)

        self.module_card = QFrame()
        self.module_card.setObjectName("NetworkModuleCard")
        module_layout = QVBoxLayout(self.module_card)
        module_layout.setContentsMargins(16, 14, 16, 16)
        module_layout.setSpacing(12)

        module_header = QVBoxLayout()
        module_header.setSpacing(4)
        self.module_title_label = QLabel("Overview")
        self.module_title_label.setObjectName("NetworkSectionTitle")
        self.module_hint_label = QLabel("Notes, context, and rough shape of the lab.")
        self.module_hint_label.setObjectName("NetworkSubtleLabel")
        self.module_hint_label.setWordWrap(True)
        module_header.addWidget(self.module_title_label)
        module_header.addWidget(self.module_hint_label)
        module_layout.addLayout(module_header)

        self.focus_context_card = QFrame()
        self.focus_context_card.setObjectName("NetworkFocusCard")
        focus_layout = QHBoxLayout(self.focus_context_card)
        focus_layout.setContentsMargins(12, 10, 12, 10)
        focus_layout.setSpacing(10)

        focus_copy = QVBoxLayout()
        focus_copy.setSpacing(2)
        self.focus_context_title = QLabel("Focused context")
        self.focus_context_title.setObjectName("NetworkHintTitle")
        self.focus_context_detail = QLabel("No active focus.")
        self.focus_context_detail.setObjectName("NetworkSubtleLabel")
        self.focus_context_detail.setWordWrap(True)
        focus_copy.addWidget(self.focus_context_title)
        focus_copy.addWidget(self.focus_context_detail)
        focus_layout.addLayout(focus_copy, 1)

        self.focus_devices_button = QPushButton("Devices")
        self.focus_devices_button.setObjectName("NetworkFocusButton")
        self.focus_wiring_button = QPushButton("Wiring")
        self.focus_wiring_button.setObjectName("NetworkFocusButton")
        self.focus_expose_button = QPushButton("Expose")
        self.focus_expose_button.setObjectName("NetworkFocusButton")
        self.focus_trace_button = QPushButton("Trace")
        self.focus_trace_button.setObjectName("NetworkFocusButton")
        self.focus_clear_button = QPushButton("Clear")
        self.focus_clear_button.setObjectName("NetworkFocusButton")
        focus_layout.addWidget(self.focus_devices_button)
        focus_layout.addWidget(self.focus_wiring_button)
        focus_layout.addWidget(self.focus_expose_button)
        focus_layout.addWidget(self.focus_trace_button)
        focus_layout.addWidget(self.focus_clear_button)
        self.focus_context_card.hide()
        module_layout.addWidget(self.focus_context_card)

        self.step_stack = QStackedWidget()
        self.step_stack.addWidget(self._build_sketch_step())
        self.step_stack.addWidget(self._build_devices_step())
        self.step_stack.addWidget(self._build_wiring_step())
        self.step_stack.addWidget(self._build_exposure_step())
        self.step_stack.addWidget(self._build_trace_step())
        module_layout.addWidget(self.step_stack, 1)
        scroll_layout.addWidget(self.module_card)
        scroll_layout.addStretch(1)
        return panel

    def _build_companion_panel(self):
        panel = QFrame()
        panel.setObjectName("NetworkCompanionPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.companion_scroll = QScrollArea()
        self.companion_scroll.setObjectName("NetworkCompanionScroll")
        self.companion_scroll.setWidgetResizable(True)
        self.companion_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.companion_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.companion_scroll)

        scroll_content = QWidget()
        scroll_content.setObjectName("NetworkCompanionScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(16, 18, 16, 18)
        scroll_layout.setSpacing(14)
        self.companion_scroll.setWidget(scroll_content)

        title = QLabel("Sidebar")
        title.setObjectName("NetworkSectionTitle")
        scroll_layout.addWidget(title)

        self.current_step_card = QFrame()
        self.current_step_card.setObjectName("NetworkGuideCard")
        current_step_layout = QVBoxLayout(self.current_step_card)
        current_step_layout.setContentsMargins(14, 12, 14, 12)
        current_step_layout.setSpacing(6)

        self.current_step_label = QLabel("Overview")
        self.current_step_label.setObjectName("NetworkGuideTitle")
        self.current_step_hint = QLabel()
        self.current_step_hint.setObjectName("NetworkSubtleLabel")
        self.current_step_hint.setWordWrap(True)
        current_step_layout.addWidget(self.current_step_label)
        current_step_layout.addWidget(self.current_step_hint)
        scroll_layout.addWidget(self.current_step_card)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("NetworkSummaryCard")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(6)

        summary_title = QLabel("Lab state")
        summary_title.setObjectName("NetworkHintTitle")
        self.lab_summary_label = QLabel()
        self.lab_summary_label.setObjectName("NetworkSummaryLabel")
        self.lab_summary_label.setWordWrap(True)
        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.lab_summary_label)
        scroll_layout.addWidget(self.summary_card)

        self.companion_trace_card = QFrame()
        self.companion_trace_card.setObjectName("NetworkTraceOverviewCard")
        companion_trace_layout = QVBoxLayout(self.companion_trace_card)
        companion_trace_layout.setContentsMargins(14, 12, 14, 12)
        companion_trace_layout.setSpacing(6)

        self.companion_trace_badge = QLabel("No trace yet")
        self.companion_trace_badge.setObjectName("TraceVerdictBadge")
        self.companion_trace_path = QLabel("Run a trace to see the packet path.")
        self.companion_trace_path.setObjectName("NetworkPathHighlight")
        self.companion_trace_path.setWordWrap(True)
        self.companion_trace_reason = QLabel("The detail view stays tucked away until you open it.")
        self.companion_trace_reason.setObjectName("NetworkSubtleLabel")
        self.companion_trace_reason.setWordWrap(True)

        companion_trace_layout.addWidget(self.companion_trace_badge)
        companion_trace_layout.addWidget(self.companion_trace_path)
        companion_trace_layout.addWidget(self.companion_trace_reason)
        scroll_layout.addWidget(self.companion_trace_card)
        scroll_layout.addStretch(1)
        return panel

    def _build_sketch_step(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        profile_group = QGroupBox("Lab identity")
        profile_layout = QFormLayout(profile_group)
        self.lab_name_input = QLineEdit()
        self.mgmt_subnet_input = QLineEdit()
        self.edge_type_combo = QComboBox()
        self.edge_type_combo.addItems(["Perimeter firewall", "Core router", "Cloud edge", "Hybrid branch"])
        profile_layout.addRow("Lab name:", self.lab_name_input)
        profile_layout.addRow("Mgmt subnet:", self.mgmt_subnet_input)
        profile_layout.addRow("Edge model:", self.edge_type_combo)
        layout.addWidget(profile_group)

        story_group = QGroupBox("Network story")
        story_layout = QVBoxLayout(story_group)
        self.topology_notes = QPlainTextEdit()
        self.topology_notes.setObjectName("NetworkEditor")
        self.topology_notes.setPlaceholderText(
            "Example: Internet reaches edge-fw, then only DMZ services are selectively published to dmz-web."
        )
        story_layout.addWidget(self.topology_notes)
        layout.addWidget(story_group, 1)

        notes_group = QGroupBox("Optional notes")
        notes_layout = QVBoxLayout(notes_group)
        self.operations_notes = QPlainTextEdit()
        self.operations_notes.setObjectName("NetworkEditor")
        self.operations_notes.setPlaceholderText("Assumptions, remediation ideas, or reminders for later.")
        self.operations_notes.setMaximumHeight(140)
        notes_layout.addWidget(self.operations_notes)
        layout.addWidget(notes_group)
        return view

    def _build_devices_step(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        button_row = QHBoxLayout()
        self.add_device_button = QPushButton("Add Device")
        self.remove_device_button = QPushButton("Remove")
        button_row.addWidget(self.add_device_button)
        button_row.addWidget(self.remove_device_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.devices_table = self._create_table(self.DEVICE_HEADERS)
        self.devices_table.setMinimumHeight(260)
        layout.addWidget(self.devices_table)
        layout.addStretch(1)
        return view

    def _build_wiring_step(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        segments_group = QGroupBox("Segments")
        segments_layout = QVBoxLayout(segments_group)
        segment_button_row = QHBoxLayout()
        self.add_segment_button = QPushButton("Add Segment")
        self.remove_segment_button = QPushButton("Remove")
        segment_button_row.addWidget(self.add_segment_button)
        segment_button_row.addWidget(self.remove_segment_button)
        segment_button_row.addStretch(1)
        segments_layout.addLayout(segment_button_row)
        self.segments_table = self._create_table(self.SEGMENT_HEADERS)
        self.segments_table.setMinimumHeight(180)
        segments_layout.addWidget(self.segments_table)
        layout.addWidget(segments_group)

        interfaces_group = QGroupBox("Interfaces")
        interfaces_layout = QVBoxLayout(interfaces_group)
        interface_button_row = QHBoxLayout()
        self.add_interface_button = QPushButton("Add Interface")
        self.remove_interface_button = QPushButton("Remove")
        interface_button_row.addWidget(self.add_interface_button)
        interface_button_row.addWidget(self.remove_interface_button)
        interface_button_row.addStretch(1)
        interfaces_layout.addLayout(interface_button_row)
        self.interfaces_table = self._create_table(self.INTERFACE_HEADERS)
        self.interfaces_table.setMinimumHeight(220)
        interfaces_layout.addWidget(self.interfaces_table)
        layout.addWidget(interfaces_group)
        layout.addStretch(1)
        return view

    def _build_exposure_step(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        exposure_group = QGroupBox("Published services")
        exposure_layout = QVBoxLayout(exposure_group)
        exposure_buttons = QHBoxLayout()
        self.add_exposure_button = QPushButton("Add Exposure")
        self.remove_exposure_button = QPushButton("Remove")
        exposure_buttons.addWidget(self.add_exposure_button)
        exposure_buttons.addWidget(self.remove_exposure_button)
        exposure_buttons.addStretch(1)
        exposure_layout.addLayout(exposure_buttons)
        self.exposures_table = self._create_table(self.EXPOSURE_HEADERS)
        self.exposures_table.setMinimumHeight(180)
        exposure_layout.addWidget(self.exposures_table)
        layout.addWidget(exposure_group)

        rules_group = QGroupBox("ACL rules")
        rules_layout = QVBoxLayout(rules_group)
        rules_buttons = QHBoxLayout()
        self.add_rule_button = QPushButton("Add Rule")
        self.remove_rule_button = QPushButton("Remove")
        rules_buttons.addWidget(self.add_rule_button)
        rules_buttons.addWidget(self.remove_rule_button)
        rules_buttons.addStretch(1)
        rules_layout.addLayout(rules_buttons)
        self.rules_table = self._create_table(self.RULE_HEADERS)
        self.rules_table.setMinimumHeight(220)
        rules_layout.addWidget(self.rules_table)
        layout.addWidget(rules_group)
        layout.addStretch(1)
        return view

    def _build_trace_step(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        trace_group = QGroupBox("Trace request")
        trace_layout = QFormLayout(trace_group)
        self.trace_source_combo = QComboBox()
        self.trace_target_combo = QComboBox()
        self.trace_protocol_combo = QComboBox()
        self.trace_protocol_combo.addItems(["TCP", "UDP", "ICMP"])
        self.trace_port_input = QLineEdit()
        self.trace_port_input.setPlaceholderText("443")
        self.run_trace_button = QPushButton("Simulate Path")
        self.run_trace_button.setObjectName("NetworkPrimaryButton")
        trace_layout.addRow("From:", self.trace_source_combo)
        trace_layout.addRow("To:", self.trace_target_combo)
        trace_layout.addRow("Protocol:", self.trace_protocol_combo)
        trace_layout.addRow("Port:", self.trace_port_input)
        trace_layout.addRow("", self.run_trace_button)
        layout.addWidget(trace_group)

        self.trace_overview_card = QFrame()
        self.trace_overview_card.setObjectName("NetworkTraceOverviewCard")
        overview_layout = QVBoxLayout(self.trace_overview_card)
        overview_layout.setContentsMargins(14, 12, 14, 12)
        overview_layout.setSpacing(6)

        self.trace_result_badge = QLabel("Ready")
        self.trace_result_badge.setObjectName("TraceVerdictBadge")
        self.trace_path_label = QLabel("Path will appear here after the first simulation.")
        self.trace_path_label.setObjectName("NetworkPathHighlight")
        self.trace_path_label.setWordWrap(True)
        self.trace_reason_label = QLabel("Pick a source, target, protocol, and port to test a packet path.")
        self.trace_reason_label.setObjectName("NetworkSubtleLabel")
        self.trace_reason_label.setWordWrap(True)
        self.trace_service_label = QLabel("No service matched yet.")
        self.trace_service_label.setObjectName("NetworkSubtleLabel")
        self.trace_service_label.setWordWrap(True)

        overview_layout.addWidget(self.trace_result_badge)
        overview_layout.addWidget(self.trace_path_label)
        overview_layout.addWidget(self.trace_reason_label)
        overview_layout.addWidget(self.trace_service_label)
        layout.addWidget(self.trace_overview_card)

        self.trace_details_group = QGroupBox("Show engine details")
        self.trace_details_group.setCheckable(True)
        self.trace_details_group.setChecked(False)
        details_layout = QVBoxLayout(self.trace_details_group)
        self.trace_output = QPlainTextEdit()
        self.trace_output.setObjectName("NetworkReadOnly")
        self.trace_output.setReadOnly(True)
        self.trace_output.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.trace_output.setPlaceholderText("Detailed engine trace will appear here after you simulate a path.")
        details_layout.addWidget(self.trace_output)
        self.trace_output.setVisible(False)
        self.trace_details_group.toggled.connect(self._set_trace_details_visibility)
        layout.addWidget(self.trace_details_group, 1)
        return view

    def _bind_events(self):
        for index, button in enumerate(self.step_buttons):
            button.clicked.connect(lambda _checked=False, idx=index: self._set_activity_view(idx))

        self.add_device_button.clicked.connect(self._add_device_row)
        self.remove_device_button.clicked.connect(lambda: self._remove_selected_rows(self.devices_table))
        self.add_segment_button.clicked.connect(self._add_segment_row)
        self.remove_segment_button.clicked.connect(lambda: self._remove_selected_rows(self.segments_table))
        self.add_rule_button.clicked.connect(self._add_rule_row)
        self.remove_rule_button.clicked.connect(lambda: self._remove_selected_rows(self.rules_table))
        self.add_interface_button.clicked.connect(self._add_interface_row)
        self.remove_interface_button.clicked.connect(lambda: self._remove_selected_rows(self.interfaces_table))
        self.add_exposure_button.clicked.connect(self._add_exposure_row)
        self.remove_exposure_button.clicked.connect(lambda: self._remove_selected_rows(self.exposures_table))
        self.run_trace_button.clicked.connect(self._simulate_packet_trace)
        self.focus_devices_button.clicked.connect(lambda: self._open_focus_context("devices"))
        self.focus_wiring_button.clicked.connect(lambda: self._open_focus_context("wiring"))
        self.focus_expose_button.clicked.connect(lambda: self._open_focus_context("expose"))
        self.focus_trace_button.clicked.connect(lambda: self._open_focus_context("trace"))
        self.focus_clear_button.clicked.connect(self._clear_focus_context)

        for widget in [
            self.lab_name_input,
            self.mgmt_subnet_input,
            self.edge_type_combo,
            self.topology_notes,
            self.operations_notes,
            self.trace_port_input,
            self.trace_source_combo,
            self.trace_target_combo,
            self.trace_protocol_combo,
        ]:
            self._bind_dirty_signal(widget)

        for table in [
            self.devices_table,
            self.segments_table,
            self.rules_table,
            self.interfaces_table,
            self.exposures_table,
        ]:
            table.itemChanged.connect(lambda _item=None: self._mark_dirty())

    def _bind_dirty_signal(self, widget):
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(lambda _=None: self._mark_dirty())
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(lambda _=None: self._mark_dirty())
        elif isinstance(widget, QPlainTextEdit):
            widget.textChanged.connect(lambda: self._mark_dirty())

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QWidget {
                color: #e8eef5;
                font-family: "DejaVu Sans";
            }
            QLabel {
                background: transparent;
            }
            QSplitter::handle {
                background-color: #111926;
                width: 1px;
            }
            QSplitter#NetworkWorkbenchSplitter::handle {
                background-color: #101723;
                width: 1px;
            }
            QFrame#NetworkWorkspacePanel {
                background-color: #0c121a;
                border-right: 1px solid #182230;
            }
            QFrame#NetworkCompanionPanel {
                background-color: #111925;
            }
            QFrame#NetworkModuleRail {
                background-color: #101723;
                border: 1px solid #162231;
                border-radius: 22px;
            }
            QFrame#NetworkWorkbenchPanel {
                background-color: transparent;
            }
            QScrollArea#NetworkWorkbenchScroll, QScrollArea#NetworkCompanionScroll {
                background: transparent;
                border: none;
            }
            QWidget#NetworkWorkbenchScrollContent, QWidget#NetworkCompanionScrollContent {
                background: transparent;
            }
            QFrame#NetworkHeroCard {
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #121d2b,
                    stop: 0.5 #13273a,
                    stop: 1 #0f1824
                );
                border: 1px solid #20384d;
                border-radius: 24px;
            }
            QFrame#NetworkTopologyCard, QFrame#NetworkModuleCard {
                background-color: #101723;
                border: 1px solid #172535;
                border-radius: 22px;
            }
            QFrame#NetworkFocusCard {
                background-color: #13202d;
                border: 1px solid #203245;
                border-radius: 18px;
            }
            QFrame#NetworkTopologyCanvas {
                background-color: #0d141c;
                border: 1px solid #15212f;
                border-radius: 18px;
            }
            QPushButton#NetworkStepButton {
                background-color: #121b27;
                color: #98aabc;
                border: 1px solid #1a2838;
                border-radius: 16px;
                padding: 11px 14px;
                font-weight: 700;
                font-size: 13px;
                text-align: left;
            }
            QPushButton#NetworkStepButton:hover {
                background-color: #162232;
                color: #f4f9fc;
                border-color: #233d56;
            }
            QPushButton#NetworkStepButton:checked {
                background-color: #183246;
                color: #f8fcff;
                border-color: #4a7392;
            }
            QLabel#NetworkSectionTitle {
                color: #f7fbff;
                font-size: 15px;
                font-weight: 800;
                letter-spacing: 0.04em;
            }
            QLabel#NetworkRailTitle {
                color: #7fd7ff;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.14em;
            }
            QLabel#NetworkMainTitle {
                color: #f4f8fb;
                font-size: 32px;
                font-weight: 900;
            }
            QLabel#NetworkEyebrow {
                color: #89d7ff;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.16em;
            }
            QLabel#NetworkHeroSummary {
                color: #c6d6e4;
                font-size: 14px;
            }
            QLabel#NetworkHeroChip {
                background-color: rgba(19, 31, 45, 0.58);
                color: #f3fbff;
                border: 1px solid #355874;
                border-radius: 999px;
                padding: 7px 12px;
                font-size: 11px;
                font-weight: 800;
            }
            QLabel#NetworkContextLabel, QLabel#NetworkSummaryLabel, QLabel#NetworkHelperLabel,
            QLabel#NetworkSubtleLabel {
                color: #99acbf;
                font-size: 13px;
            }
            QLabel#NetworkSummaryLabel {
                line-height: 1.45;
            }
            QFrame#NetworkGuideCard, QFrame#NetworkTraceOverviewCard, QFrame#NetworkHintCard,
            QFrame#NetworkSummaryCard {
                background-color: #121c28;
                border: 1px solid #1c2d3e;
                border-radius: 20px;
            }
            QFrame#NetworkDeviceCard {
                background-color: #13202d;
                border: 1px solid #203245;
                border-radius: 18px;
                min-width: 200px;
                max-width: 240px;
            }
            QFrame#NetworkDeviceCard[selected="true"] {
                background-color: #163047;
                border: 1px solid #6eb8e0;
            }
            QFrame#NetworkDeviceCard[trace="true"] {
                border: 1px solid #6fd394;
            }
            QLabel#NetworkGuideTitle {
                color: #f5f9fd;
                font-size: 18px;
                font-weight: 800;
            }
            QLabel#NetworkHintTitle {
                color: #eff7fb;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#NetworkPathHighlight {
                color: #f3fbff;
                font-size: 14px;
                font-weight: 700;
            }
            QLabel#NetworkDeviceTitle {
                color: #f4fbff;
                font-size: 16px;
                font-weight: 800;
            }
            QLabel#NetworkMetaChip, QLabel#NetworkSegmentChip, QLabel#NetworkServiceChip {
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#NetworkMetaChip {
                background-color: #182432;
                color: #c7d5e1;
                border: 1px solid #24384d;
            }
            QLabel#NetworkSegmentChip {
                background-color: #143244;
                color: #d7f2ff;
                border: 1px solid #2d607e;
            }
            QLabel#NetworkInterfaceChip {
                background-color: #182432;
                color: #d8e5ef;
                border: 1px solid #25384c;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#NetworkTraceInterfaceChip {
                background-color: #20432e;
                color: #e3f9eb;
                border: 1px solid #4e8b66;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#NetworkInterfaceChipButton {
                background-color: #182432;
                color: #d8e5ef;
                border: 1px solid #25384c;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#NetworkInterfaceChipButton:hover {
                background-color: #203041;
                border-color: #3e566d;
            }
            QPushButton#NetworkInterfaceChipButton:checked {
                background-color: #274158;
                border-color: #8fc8ef;
                color: #ffffff;
            }
            QPushButton#NetworkTraceInterfaceButton {
                background-color: #20432e;
                color: #e3f9eb;
                border: 1px solid #4e8b66;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#NetworkTraceInterfaceButton:hover {
                background-color: #28543a;
                border-color: #72a586;
            }
            QPushButton#NetworkTraceInterfaceButton:checked {
                background-color: #316a47;
                border-color: #b3f1cb;
                color: #ffffff;
            }
            QLabel#NetworkServiceChip {
                background-color: #212b1d;
                color: #e1f6d4;
                border: 1px solid #3d5731;
            }
            QLabel#NetworkServiceChipPublic {
                background-color: #1f3124;
                color: #e2f7da;
                border: 1px solid #416943;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#NetworkServiceChipInternal {
                background-color: #2b2619;
                color: #f0e3b1;
                border: 1px solid #665935;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#NetworkTraceHopChip {
                background-color: #183246;
                color: #e7f8ff;
                border: 1px solid #4d7c99;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#NetworkSegmentChipButton {
                background-color: #143244;
                color: #d7f2ff;
                border: 1px solid #2d607e;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#NetworkSegmentChipButton:hover {
                background-color: #1a4158;
                border-color: #5ea3cd;
            }
            QPushButton#NetworkSegmentChipButton:checked {
                background-color: #23506c;
                border-color: #8bdfff;
                color: #ffffff;
            }
            QPushButton#NetworkTraceSegmentChip {
                background-color: #23506c;
                color: #f2fbff;
                border: 1px solid #8bdfff;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#NetworkTraceSegmentChip:hover {
                background-color: #2b6488;
                border-color: #b7f0ff;
            }
            QPushButton#NetworkTraceSegmentChip:checked {
                background-color: #2f7098;
                border-color: #d2f7ff;
                color: #ffffff;
            }
            QPushButton#NetworkTraceHopButton {
                background-color: #183246;
                color: #e7f8ff;
                border: 1px solid #4d7c99;
                border-radius: 999px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#NetworkTraceHopButton:hover {
                background-color: #20425b;
                border-color: #76a6c2;
            }
            QPushButton#NetworkTraceHopButton:checked {
                background-color: #2a5674;
                border-color: #a6e4ff;
                color: #ffffff;
            }
            QLabel#TraceVerdictBadge {
                background-color: #1d2e3f;
                color: #edf8ff;
                border: 1px solid #34506a;
                border-radius: 999px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 800;
                max-width: 160px;
            }
            QGroupBox {
                color: #eff7fb;
                border: 1px solid #1a2a3a;
                border-radius: 22px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: #111925;
            }
            QGroupBox::title {
                left: 16px;
                padding: 0 4px;
                color: #8fdcff;
                font-size: 11px;
                font-weight: 700;
                subcontrol-origin: margin;
            }
            QLineEdit, QComboBox {
                font-family: "DejaVu Sans";
                font-size: 13px;
                background-color: #111b27;
                color: #edf5fb;
                border: 1px solid #1e3042;
                border-radius: 14px;
                min-height: 38px;
                padding: 6px 12px;
            }
            QTableWidget, QPlainTextEdit {
                font-family: "JetBrains Mono";
                font-size: 12px;
                background-color: #0f1823;
                color: #edf5fb;
                border: 1px solid #1b2c3d;
                border-radius: 16px;
                selection-background-color: #2a82b4;
                alternate-background-color: #121c29;
                gridline-color: #1d3042;
                padding: 10px 12px;
            }
            QHeaderView::section {
                background-color: #162332;
                color: #deecf7;
                border: none;
                border-bottom: 1px solid #203142;
                padding: 8px 10px;
                font-weight: 700;
            }
            QTableCornerButton::section {
                background-color: #162332;
                border: none;
                border-bottom: 1px solid #203142;
                border-right: 1px solid #203142;
            }
            QPushButton {
                background-color: #1c2d3e;
                color: #f6fbff;
                border: 1px solid #29435b;
                border-radius: 14px;
                padding: 9px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #22384d;
                border-color: #4f7ea0;
            }
            QPushButton#NetworkPrimaryButton {
                background-color: #2c79a5;
                border-color: #78bfe6;
                color: #ffffff;
            }
            QPushButton#NetworkPrimaryButton:hover {
                background-color: #358abe;
                border-color: #9dd6f3;
            }
            QPushButton#NetworkFocusButton {
                background-color: #162738;
                border: 1px solid #29435b;
                border-radius: 12px;
                padding: 7px 12px;
                min-width: 72px;
            }
            QPushButton#NetworkFocusButton:hover {
                background-color: #1d3448;
                border-color: #4f7ea0;
            }
            QPlainTextEdit#NetworkReadOnly {
                background-color: #0e151d;
                color: #c8d8e3;
            }
            QTableWidget::item:selected {
                background-color: #214e6c;
                color: #ffffff;
            }
            """
        )
        self._apply_editor_font_size()

    def _create_step_button(self, text):
        button = QPushButton(text)
        button.setObjectName("NetworkStepButton")
        button.setCheckable(True)
        button.setMinimumHeight(42)
        button.setMinimumWidth(110)
        return button

    def _create_hint_card(self, title_text, body_text):
        card = QFrame()
        card.setObjectName("NetworkHintCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        title = QLabel(title_text)
        title.setObjectName("NetworkHintTitle")
        body = QLabel(body_text)
        body.setObjectName("NetworkSubtleLabel")
        body.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(body)
        return card

    def _create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        return table

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _create_topology_chip(self, text, object_name):
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        return label

    def _create_topology_action_chip(self, text, object_name, callback=None, selected=False):
        chip = QPushButton(text)
        chip.setObjectName(object_name)
        chip.setCheckable(True)
        chip.setChecked(selected)
        if callback:
            chip.clicked.connect(callback)
        return chip

    def _create_topology_service_chip(self, service_name, port, visibility):
        label = QLabel(f"{service_name}:{port}")
        visibility_token = str(visibility or "").strip().lower()
        if visibility_token == "published":
            label.setObjectName("NetworkServiceChipPublic")
        elif visibility_token == "internal only":
            label.setObjectName("NetworkServiceChipInternal")
        else:
            label.setObjectName("NetworkServiceChip")
        label.setToolTip(visibility or "")
        return label

    def _interface_context(self, device_name, interface_name):
        context = {
            "type": "interface",
            "name": interface_name,
            "device_name": device_name,
            "device_rows": [],
            "interface_rows": [],
            "segment_rows": [],
            "segment_values": [],
        }

        for row in range(self.devices_table.rowCount()):
            if self._table_cell_text(self.devices_table, row, 0) == device_name:
                context["device_rows"].append(row)

        for row in range(self.interfaces_table.rowCount()):
            same_device = self._table_cell_text(self.interfaces_table, row, 0) == device_name
            same_interface = self._table_cell_text(self.interfaces_table, row, 1) == interface_name
            if same_device and same_interface:
                context["interface_rows"].append(row)
                vlan = self._table_cell_text(self.interfaces_table, row, 3)
                if vlan:
                    context["segment_values"].append(vlan)

        for row in range(self.segments_table.rowCount()):
            vlan = self._table_cell_text(self.segments_table, row, 0)
            if vlan and vlan in context["segment_values"]:
                context["segment_rows"].append(row)

        return context

    def _extract_trace_transport_context(self):
        trace_segments = set()
        trace_interfaces_by_device = {}

        for hop in getattr(self.last_trace_result, "hop_details", []) or []:
            note = str(getattr(hop, "note", "") or "").strip().lower()
            via = str(getattr(hop, "via", "") or "").strip()
            source = str(getattr(hop, "source", "") or "").strip()
            target = str(getattr(hop, "target", "") or "").strip()

            if not via:
                continue

            if note == "shared segment":
                trace_segments.add(via)
                continue

            if note == "edge ingress":
                if target and target != "Internet":
                    trace_interfaces_by_device.setdefault(target, set()).add(via)
                continue

            if note == "edge egress":
                if source and source != "Internet":
                    trace_interfaces_by_device.setdefault(source, set()).add(via)

        return trace_segments, trace_interfaces_by_device

    def _create_topology_device_card(
        self,
        device_name,
        role,
        segments,
        interfaces,
        services,
        selected=False,
        trace=False,
    ):
        card = QFrame()
        card.setObjectName("NetworkDeviceCard")
        card.setProperty("selected", selected)
        card.setProperty("trace", trace)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda _event, name=device_name: self._handle_topology_device_click(name)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title = QLabel(device_name)
        title.setObjectName("NetworkDeviceTitle")
        subtitle = QLabel(role or "Modeled device")
        subtitle.setObjectName("NetworkSubtleLabel")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        if segments:
            segments_row = QHBoxLayout()
            segments_row.setSpacing(6)
            segments_row.addWidget(self._create_topology_chip("Segments", "NetworkMetaChip"))
            for segment, trace_segment in segments:
                chip_name = "NetworkTraceSegmentChip" if trace_segment else "NetworkSegmentChipButton"
                segments_row.addWidget(
                    self._create_topology_action_chip(
                        str(segment),
                        chip_name,
                        callback=lambda _checked=False, name=str(segment): self._handle_topology_segment_click(name),
                        selected=self.selected_topology_segment == str(segment),
                    )
                )
            segments_row.addStretch(1)
            layout.addLayout(segments_row)
        if interfaces:
            interfaces_row = QHBoxLayout()
            interfaces_row.setSpacing(6)
            interfaces_row.addWidget(self._create_topology_chip("Interfaces", "NetworkMetaChip"))
            for interface_name, trace_interface in interfaces:
                interfaces_row.addWidget(
                    self._create_topology_action_chip(
                        interface_name,
                        "NetworkTraceInterfaceButton" if trace_interface else "NetworkInterfaceChipButton",
                        callback=lambda _checked=False, device=device_name, name=interface_name: self._handle_topology_interface_click(
                            device, name
                        ),
                        selected=self.selected_topology_device == device_name
                        and self.selected_topology_interface == interface_name,
                    )
                )
            interfaces_row.addStretch(1)
            layout.addLayout(interfaces_row)
        if services:
            services_row = QHBoxLayout()
            services_row.setSpacing(6)
            services_row.addWidget(self._create_topology_chip("Services", "NetworkMetaChip"))
            for service_name, port, visibility in services:
                services_row.addWidget(self._create_topology_service_chip(service_name, port, visibility))
            services_row.addStretch(1)
            layout.addLayout(services_row)
        return card

    def _select_table_row_by_value(self, table, column, value):
        if value is None:
            return False
        table.clearSelection()
        for row in range(table.rowCount()):
            if self._table_cell_text(table, row, column) == str(value):
                table.selectRow(row)
                table.scrollToItem(table.item(row, column))
                return True
        return False

    def _select_table_rows(self, table, rows):
        normalized_rows = sorted({row for row in rows if 0 <= row < table.rowCount()})
        table.clearSelection()
        if not normalized_rows:
            return False
        selection_model = table.selectionModel()
        for row in normalized_rows:
            index = table.model().index(row, 0)
            selection_model.select(
                index,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
        first_row = normalized_rows[0]
        anchor_item = table.item(first_row, 0)
        if anchor_item:
            table.scrollToItem(anchor_item)
        return True

    def _device_context(self, device_name):
        context = {
            "type": "device",
            "name": device_name,
            "device_rows": [],
            "interface_rows": [],
            "exposure_rows": [],
            "rule_rows": [],
            "segment_values": [],
        }

        for row in range(self.devices_table.rowCount()):
            if self._table_cell_text(self.devices_table, row, 0) == device_name:
                context["device_rows"].append(row)

        for row in range(self.interfaces_table.rowCount()):
            if self._table_cell_text(self.interfaces_table, row, 0) == device_name:
                context["interface_rows"].append(row)
                vlan = self._table_cell_text(self.interfaces_table, row, 3)
                if vlan and vlan not in context["segment_values"]:
                    context["segment_values"].append(vlan)

        for row in range(self.exposures_table.rowCount()):
            if self._table_cell_text(self.exposures_table, row, 0) == device_name:
                context["exposure_rows"].append(row)

        for row in range(self.rules_table.rowCount()):
            if device_name in {self._table_cell_text(self.rules_table, row, 0), self._table_cell_text(self.rules_table, row, 1)}:
                context["rule_rows"].append(row)

        return context

    def _trace_hop_context(self, hop_name):
        request = getattr(self.last_trace_result, "request", None)
        return {
            "type": "hop",
            "name": str(hop_name),
            "request": request,
        }

    def _segment_context(self, segment_name):
        segment_name = str(segment_name)
        context = {
            "type": "segment",
            "name": segment_name,
            "segment_rows": [],
            "interface_rows": [],
            "device_rows": [],
            "exposure_rows": [],
            "rule_rows": [],
        }

        matching_vlans = set()
        for row in range(self.segments_table.rowCount()):
            vlan = self._table_cell_text(self.segments_table, row, 0)
            name = self._table_cell_text(self.segments_table, row, 1)
            if segment_name in {vlan, name}:
                context["segment_rows"].append(row)
                if vlan:
                    matching_vlans.add(vlan)

        matching_devices = set()
        for row in range(self.interfaces_table.rowCount()):
            vlan = self._table_cell_text(self.interfaces_table, row, 3)
            if vlan == segment_name or vlan in matching_vlans:
                context["interface_rows"].append(row)
                device_name = self._table_cell_text(self.interfaces_table, row, 0)
                if device_name:
                    matching_devices.add(device_name)

        for row in range(self.devices_table.rowCount()):
            if self._table_cell_text(self.devices_table, row, 0) in matching_devices:
                context["device_rows"].append(row)

        for row in range(self.exposures_table.rowCount()):
            if self._table_cell_text(self.exposures_table, row, 0) in matching_devices:
                context["exposure_rows"].append(row)

        for row in range(self.rules_table.rowCount()):
            source = self._table_cell_text(self.rules_table, row, 0)
            target = self._table_cell_text(self.rules_table, row, 1)
            if source in matching_devices or target in matching_devices:
                context["rule_rows"].append(row)

        return context

    def _is_modeled_device(self, value):
        for row in range(self.devices_table.rowCount()):
            if self._table_cell_text(self.devices_table, row, 0) == str(value):
                return True
        return False

    def _update_focus_context_card(self):
        if not self.focus_context:
            self.focus_context_card.hide()
            return

        context_type = self.focus_context.get("type", "device")
        name = self.focus_context.get("name", "")
        if context_type == "device":
            self.focus_context_title.setText(f"Focused device · {name}")
            self.focus_context_detail.setText(
                f"{len(self.focus_context.get('interface_rows', []))} interfaces · "
                f"{len(self.focus_context.get('exposure_rows', []))} services · "
                f"{len(self.focus_context.get('rule_rows', []))} rules"
            )
            self.focus_devices_button.show()
            self.focus_wiring_button.show()
            self.focus_expose_button.show()
            self.focus_trace_button.show()
        elif context_type == "interface":
            device_name = self.focus_context.get("device_name", "")
            self.focus_context_title.setText(f"Focused interface · {name}")
            self.focus_context_detail.setText(
                f"Device {device_name or '-'} · "
                f"{len(self.focus_context.get('segment_rows', []))} segments attached"
            )
            self.focus_devices_button.show()
            self.focus_wiring_button.show()
            self.focus_expose_button.hide()
            self.focus_trace_button.show()
        elif context_type == "segment":
            self.focus_context_title.setText(f"Focused segment · {name}")
            self.focus_context_detail.setText(
                f"{len(self.focus_context.get('device_rows', []))} devices · "
                f"{len(self.focus_context.get('interface_rows', []))} interfaces · "
                f"{len(self.focus_context.get('exposure_rows', []))} services"
            )
            self.focus_devices_button.show()
            self.focus_wiring_button.show()
            self.focus_expose_button.show()
            self.focus_trace_button.show()
        else:
            request = self.focus_context.get("request")
            request_summary = ""
            if request:
                request_summary = f"{request.source} -> {request.target} {request.proto}/{request.port}"
            self.focus_context_title.setText(f"Trace hop · {name}")
            self.focus_context_detail.setText(
                request_summary or "External hop from the current packet trace."
            )
            self.focus_devices_button.hide()
            self.focus_wiring_button.hide()
            self.focus_expose_button.hide()
            self.focus_trace_button.show()

        self.focus_context_card.show()

    def _clear_focus_context(self):
        self.focus_context = None
        self.selected_topology_device = None
        self.selected_topology_segment = None
        self.selected_topology_interface = None
        for table in [
            self.devices_table,
            self.segments_table,
            self.interfaces_table,
            self.exposures_table,
            self.rules_table,
        ]:
            table.clearSelection()
        self._update_focus_context_card()
        self._refresh_topology_surface()
        self.status_message.emit("Topology focus cleared")

    def _open_focus_context(self, area):
        if not self.focus_context:
            return

        context_type = self.focus_context.get("type")
        if area == "devices":
            self._set_activity_view(1)
            self._select_table_rows(self.devices_table, self.focus_context.get("device_rows", []))
        elif area == "wiring":
            self._set_activity_view(2)
            if context_type in {"segment", "interface"}:
                self._select_table_rows(self.segments_table, self.focus_context.get("segment_rows", []))
            self._select_table_rows(self.interfaces_table, self.focus_context.get("interface_rows", []))
        elif area == "expose":
            self._set_activity_view(3)
            self._select_table_rows(self.exposures_table, self.focus_context.get("exposure_rows", []))
            self._select_table_rows(self.rules_table, self.focus_context.get("rule_rows", []))
        elif area == "trace":
            self._set_activity_view(4)

    def _handle_topology_device_click(self, device_name):
        self.selected_topology_device = device_name
        self.selected_topology_segment = None
        self.selected_topology_interface = None
        self.focus_context = self._device_context(device_name)
        self._set_activity_view(1)
        self._select_table_row_by_value(self.devices_table, 0, device_name)
        self._update_focus_context_card()
        self._refresh_topology_surface()
        self.status_message.emit(f"Focused device {device_name}")

    def _handle_topology_segment_click(self, segment_name):
        self.selected_topology_segment = str(segment_name)
        self.selected_topology_device = None
        self.selected_topology_interface = None
        self.focus_context = self._segment_context(segment_name)
        self._set_activity_view(2)
        if not self._select_table_row_by_value(self.segments_table, 1, segment_name):
            self._select_table_row_by_value(self.segments_table, 0, segment_name)
        self._select_table_rows(self.interfaces_table, self.focus_context.get("interface_rows", []))
        self._update_focus_context_card()
        self._refresh_topology_surface()
        self.status_message.emit(f"Focused segment {segment_name}")

    def _handle_topology_interface_click(self, device_name, interface_name):
        self.selected_topology_device = device_name
        self.selected_topology_segment = None
        self.selected_topology_interface = interface_name
        self.focus_context = self._interface_context(device_name, interface_name)
        self._set_activity_view(2)
        self._select_table_rows(self.interfaces_table, self.focus_context.get("interface_rows", []))
        self._select_table_rows(self.segments_table, self.focus_context.get("segment_rows", []))
        self._update_focus_context_card()
        self._refresh_topology_surface()
        self.status_message.emit(f"Focused interface {device_name} {interface_name}")

    def _handle_trace_hop_click(self, hop_name):
        if self._is_modeled_device(hop_name):
            self._handle_topology_device_click(hop_name)
            return

        self.selected_topology_device = None
        self.selected_topology_segment = None
        self.selected_topology_interface = None
        self.focus_context = self._trace_hop_context(hop_name)
        self._set_activity_view(4)
        self._update_focus_context_card()
        self._refresh_topology_surface()
        self.status_message.emit(f"Focused trace hop {hop_name}")

    def _refresh_topology_surface(self):
        self._clear_layout(self.topology_canvas_layout)
        trace_segments, trace_interfaces_by_device = self._extract_trace_transport_context()

        segment_names = []
        for row in range(self.segments_table.rowCount()):
            vlan = self._table_cell_text(self.segments_table, row, 0)
            name = self._table_cell_text(self.segments_table, row, 1)
            if vlan or name:
                segment_names.append((name or f"VLAN {vlan}", vlan))

        if segment_names:
            segment_row = QHBoxLayout()
            segment_row.setSpacing(8)
            segment_row.addWidget(self._create_topology_chip("Segments", "NetworkMetaChip"))
            for name, vlan in segment_names[:6]:
                segment_label = str(name)
                is_selected = self.selected_topology_segment in {str(name), str(vlan)}
                in_trace = segment_label in trace_segments or str(vlan) in trace_segments
                segment_row.addWidget(
                    self._create_topology_action_chip(
                        segment_label,
                        "NetworkTraceSegmentChip" if in_trace else "NetworkSegmentChipButton",
                        callback=lambda _checked=False, value=str(name or vlan): self._handle_topology_segment_click(value),
                        selected=is_selected,
                    )
                )
            segment_row.addStretch(1)
            self.topology_canvas_layout.addLayout(segment_row)

        if self.last_trace_result and self.last_trace_result.hops:
            trace_row = QHBoxLayout()
            trace_row.setSpacing(8)
            trace_row.addWidget(self._create_topology_chip("Trace path", "NetworkMetaChip"))
            for hop in self.last_trace_result.hops:
                trace_row.addWidget(
                    self._create_topology_action_chip(
                        str(hop),
                        "NetworkTraceHopButton",
                        callback=lambda _checked=False, value=str(hop): self._handle_trace_hop_click(value),
                        selected=self.focus_context is not None
                        and self.focus_context.get("type") == "hop"
                        and self.focus_context.get("name") == str(hop),
                    )
                )
            trace_row.addStretch(1)
            self.topology_canvas_layout.addLayout(trace_row)

        devices = []
        trace_hops = {str(hop) for hop in getattr(self.last_trace_result, "hops", [])}
        for row in range(self.devices_table.rowCount()):
            device_name = self._table_cell_text(self.devices_table, row, 0)
            role = self._table_cell_text(self.devices_table, row, 3)
            if not device_name:
                continue

            device_segments = []
            device_interfaces = []
            for iface_row in range(self.interfaces_table.rowCount()):
                if self._table_cell_text(self.interfaces_table, iface_row, 0) != device_name:
                    continue
                interface_name = self._table_cell_text(self.interfaces_table, iface_row, 1)
                vlan = self._table_cell_text(self.interfaces_table, iface_row, 3)
                if vlan and vlan not in device_segments:
                    device_segments.append(
                        (
                            vlan,
                            vlan in trace_segments,
                        )
                    )
                if interface_name:
                    traced_interfaces = trace_interfaces_by_device.get(device_name, set())
                    device_interfaces.append((interface_name, interface_name in traced_interfaces))

            device_services = []
            for exposure_row in range(self.exposures_table.rowCount()):
                if self._table_cell_text(self.exposures_table, exposure_row, 0) != device_name:
                    continue
                service = self._table_cell_text(self.exposures_table, exposure_row, 1)
                port = self._table_cell_text(self.exposures_table, exposure_row, 3)
                visibility = self._table_cell_text(self.exposures_table, exposure_row, 4)
                if service or port or visibility:
                    device_services.append((service or "-", port or "-", visibility or "custom"))

            devices.append(
                (
                    device_name,
                    role,
                    device_segments,
                    device_interfaces,
                    device_services,
                    device_name in trace_hops,
                )
            )

        if devices:
            devices_row = QHBoxLayout()
            devices_row.setSpacing(10)
            for device_name, role, device_segments, device_interfaces, device_services, in_trace in devices:
                devices_row.addWidget(
                    self._create_topology_device_card(
                        device_name,
                        role,
                        device_segments,
                        device_interfaces,
                        device_services,
                        selected=self.selected_topology_device == device_name,
                        trace=in_trace,
                    )
                )
            devices_row.addStretch(1)
            self.topology_canvas_layout.addLayout(devices_row)
        else:
            empty = QLabel("Add devices, segments, and services to populate the topology view.")
            empty.setObjectName("NetworkSubtleLabel")
            self.topology_canvas_layout.addWidget(empty)

        trace_hint = QLabel("Packet paths will reuse this shape when you run a trace.")
        trace_hint.setObjectName("NetworkSubtleLabel")
        self.topology_canvas_layout.addWidget(trace_hint)
        self.topology_canvas_layout.addStretch(1)

    def _set_activity_view(self, index):
        self.step_stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.step_buttons):
            button.setChecked(button_index == index)
        step_name, step_hint = self.step_definitions[index]
        self.hero_step_chip.setText(step_name)
        self.current_step_label.setText(step_name)
        self.current_step_hint.setText(step_hint)
        self.lab_context_label.setText(step_hint)
        self.module_title_label.setText(step_name)
        self.module_hint_label.setText(step_hint)

    def _set_trace_details_visibility(self, visible):
        self.trace_output.setVisible(visible)
        self.trace_details_group.setTitle("Hide engine details" if visible else "Show engine details")

    def _mark_dirty(self, status_message=None):
        if self._loading_state:
            return
        self._dirty = True
        self._refresh_device_selectors()
        self._update_lab_summary()
        self._update_focus_context_card()
        self._refresh_topology_surface()
        if status_message:
            self.status_message.emit(status_message)

    def _add_device_row(self):
        row = self.devices_table.rowCount()
        self.devices_table.insertRow(row)
        defaults = [f"device-{row + 1}", "Router", f"10.0.0.{row + 1}", "Distribution"]
        for column, value in enumerate(defaults):
            self.devices_table.setItem(row, column, QTableWidgetItem(value))
        self.devices_table.selectRow(row)
        self._mark_dirty("Device added")

    def _add_segment_row(self):
        row = self.segments_table.rowCount()
        self.segments_table.insertRow(row)
        defaults = [str((row + 1) * 10), f"SEG-{row + 1}", f"10.{row + 1}.0.0/24", f"10.{row + 1}.0.1"]
        for column, value in enumerate(defaults):
            self.segments_table.setItem(row, column, QTableWidgetItem(value))
        self.segments_table.selectRow(row)
        self._mark_dirty("Segment added")

    def _add_rule_row(self):
        row = self.rules_table.rowCount()
        self.rules_table.insertRow(row)
        defaults = ["Internet", "dmz-web", "TCP", "443", "allow"]
        for column, value in enumerate(defaults):
            self.rules_table.setItem(row, column, QTableWidgetItem(value))
        self.rules_table.selectRow(row)
        self._mark_dirty("ACL rule added")

    def _add_interface_row(self):
        device_name = self._table_cell_text(self.devices_table, 0, 0) or "edge-fw"
        vlan = self._table_cell_text(self.segments_table, 0, 0) or "10"
        row = self.interfaces_table.rowCount()
        self.interfaces_table.insertRow(row)
        defaults = [device_name, f"Gig0/{row}", f"10.{row + 1}.0.1/24", vlan, "up"]
        for column, value in enumerate(defaults):
            self.interfaces_table.setItem(row, column, QTableWidgetItem(value))
        self.interfaces_table.selectRow(row)
        self._mark_dirty("Interface added")

    def _add_exposure_row(self):
        device_name = self._table_cell_text(self.devices_table, 0, 0) or "dmz-web"
        row = self.exposures_table.rowCount()
        self.exposures_table.insertRow(row)
        defaults = [device_name, "HTTPS", "TCP", "443", "published"]
        for column, value in enumerate(defaults):
            self.exposures_table.setItem(row, column, QTableWidgetItem(value))
        self.exposures_table.selectRow(row)
        self._mark_dirty("Exposure published")

    def _remove_selected_rows(self, table):
        selected_rows = sorted({index.row() for index in table.selectionModel().selectedRows()}, reverse=True)
        if not selected_rows:
            return
        for row in selected_rows:
            table.removeRow(row)
        self._mark_dirty("Rows removed")

    def _refresh_device_selectors(self):
        current_source = self.trace_source_combo.currentText()
        current_target = self.trace_target_combo.currentText()

        device_names = [self._table_cell_text(self.devices_table, row, 0) for row in range(self.devices_table.rowCount())]
        device_names = [name for name in device_names if name]
        options = ["Internet"] + device_names

        self.trace_source_combo.blockSignals(True)
        self.trace_target_combo.blockSignals(True)
        self.trace_source_combo.clear()
        self.trace_target_combo.clear()
        self.trace_source_combo.addItems(options)
        self.trace_target_combo.addItems(device_names or ["No devices"])
        self._restore_combo_value(self.trace_source_combo, current_source)
        self._restore_combo_value(self.trace_target_combo, current_target if current_target in device_names else "")
        self.trace_source_combo.blockSignals(False)
        self.trace_target_combo.blockSignals(False)

    def _restore_combo_value(self, combo, value):
        index = combo.findText(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _simulate_packet_trace(self):
        source = self.trace_source_combo.currentText() or "Internet"
        target = self.trace_target_combo.currentText()
        proto = self.trace_protocol_combo.currentText()
        port = self.trace_port_input.text().strip() or "-"

        if not target or target == "No devices":
            self.trace_output.setPlainText("Add at least one device before running the packet tracer.")
            return

        engine = NetworkTraceEngine.from_network_state(self.to_network_state())
        result = engine.trace(
            TraceRequest(
                source=source,
                target=target,
                proto=proto,
                port=port,
            )
        )
        self.last_trace_result = result
        self._update_trace_summary(result)
        self._refresh_topology_surface()
        self.trace_output.setPlainText(format_trace_result(result))
        self.status_message.emit("Packet trace simulated")

    def _update_lab_summary(self):
        device_count = self.devices_table.rowCount()
        segment_count = self.segments_table.rowCount()
        interface_count = self.interfaces_table.rowCount()
        rule_count = self.rules_table.rowCount()
        exposure_count = self.exposures_table.rowCount()
        lab_name = self.lab_name_input.text().strip() or "Untitled lab"

        self.lab_summary_label.setText(
            f"{lab_name}\n"
            f"{device_count} devices · {segment_count} segments · {interface_count} interfaces\n"
            f"{rule_count} rules · {exposure_count} services"
        )
        self.topology_meta_label.setText(
            f"{device_count} devices · {segment_count} segments · {exposure_count} services"
        )

    def _update_trace_summary(self, result):
        self.trace_result_badge.setText(result.verdict.title())
        self.trace_path_label.setText(" -> ".join(result.hops) if result.hops else "No path inferred")
        self.trace_reason_label.setText(result.reason)

        if result.matched_service:
            self.trace_service_label.setText(
                f"Matched service: {result.matched_service.device} "
                f"{result.matched_service.service or '-'} "
                f"{result.matched_service.proto}/{result.matched_service.port}"
            )
        else:
            self.trace_service_label.setText("No published service matched this request.")

        self.companion_trace_badge.setText(result.verdict.title())
        self.companion_trace_path.setText(" -> ".join(result.hops) if result.hops else "No path inferred yet")
        self.companion_trace_reason.setText(result.reason)

        badge_colors = {
            "ALLOWED": ("#1f8f57", "#52e29c"),
            "FILTERED": ("#8a6a1f", "#e0b24d"),
            "BLOCKED": ("#8f3c3c", "#ef7c7c"),
            "UNREACHABLE": ("#5f6875", "#a8b3c5"),
        }
        bg_color, border_color = badge_colors.get(result.verdict.upper(), ("#243243", "#33465b"))
        badge_style = (
            f"background-color: {bg_color}; color: #ffffff; border: 1px solid {border_color}; "
            "border-radius: 999px; padding: 6px 14px; font-size: 12px; font-weight: 800;"
        )
        self.trace_result_badge.setStyleSheet(badge_style)
        self.companion_trace_badge.setStyleSheet(badge_style)

    def _collect_workspace_state(self):
        return {
            "lab_profile": {
                "lab_name": self.lab_name_input.text().strip(),
                "mgmt_subnet": self.mgmt_subnet_input.text().strip(),
                "edge_type": self.edge_type_combo.currentText(),
            },
            "devices": self._table_to_dicts(self.devices_table, self.DEVICE_HEADERS),
            "segments": self._table_to_dicts(self.segments_table, self.SEGMENT_HEADERS),
            "rules": self._table_to_dicts(self.rules_table, self.RULE_HEADERS),
            "interfaces": self._table_to_dicts(self.interfaces_table, self.INTERFACE_HEADERS),
            "exposures": self._table_to_dicts(self.exposures_table, self.EXPOSURE_HEADERS),
            "topology_notes": self.topology_notes.toPlainText(),
            "operations_notes": self.operations_notes.toPlainText(),
            "trace_output": self.trace_output.toPlainText(),
            "trace_defaults": {
                "source": self.trace_source_combo.currentText(),
                "target": self.trace_target_combo.currentText(),
                "protocol": self.trace_protocol_combo.currentText(),
                "port": self.trace_port_input.text().strip(),
            },
        }

    def to_network_state(self):
        return NetworkState.from_workspace_dict(self._collect_workspace_state())

    def to_dict(self):
        return self.to_network_state().to_workspace_dict()

    def load_state(self, state):
        if isinstance(state, NetworkState):
            state = state.to_workspace_dict()
        state = state or {}
        self._loading_state = True

        profile = state.get("lab_profile", {})
        self.lab_name_input.setText(profile.get("lab_name", ""))
        self.mgmt_subnet_input.setText(profile.get("mgmt_subnet", ""))
        self._set_combo_text(self.edge_type_combo, profile.get("edge_type", "Perimeter firewall"))

        self._load_table_from_dicts(self.devices_table, state.get("devices", []), self.DEVICE_HEADERS)
        self._load_table_from_dicts(self.segments_table, state.get("segments", []), self.SEGMENT_HEADERS)
        self._load_table_from_dicts(self.rules_table, state.get("rules", []), self.RULE_HEADERS)
        self._load_table_from_dicts(self.interfaces_table, state.get("interfaces", []), self.INTERFACE_HEADERS)
        self._load_table_from_dicts(self.exposures_table, state.get("exposures", []), self.EXPOSURE_HEADERS)
        self.selected_topology_device = None
        self.selected_topology_segment = None
        self.selected_topology_interface = None
        self.last_trace_result = None
        self.focus_context = None

        self.topology_notes.setPlainText(state.get("topology_notes", ""))
        self.operations_notes.setPlainText(state.get("operations_notes", ""))
        self.trace_output.setPlainText(state.get("trace_output", ""))
        self.trace_result_badge.setText("Ready")
        ready_badge_style = (
            "background-color: #243243; color: #dfeaf3; border: 1px solid #33465b; "
            "border-radius: 999px; padding: 6px 14px; font-size: 12px; font-weight: 800;"
        )
        self.trace_result_badge.setStyleSheet(ready_badge_style)
        self.trace_path_label.setText("Path will appear here after the first simulation.")
        self.trace_reason_label.setText("Pick a source, target, protocol, and port to test a packet path.")
        self.trace_service_label.setText("No service matched yet.")
        self.companion_trace_badge.setText("No trace yet")
        self.companion_trace_badge.setStyleSheet(ready_badge_style)
        self.companion_trace_path.setText("Run a trace to see the packet path.")
        self.companion_trace_reason.setText("The detail view stays tucked away until you open it.")
        self.trace_details_group.setChecked(False)
        self._set_trace_details_visibility(False)
        self._set_activity_view(0)

        self._refresh_device_selectors()
        defaults = state.get("trace_defaults", {})
        self._restore_combo_value(self.trace_source_combo, defaults.get("source", "Internet"))
        self._restore_combo_value(self.trace_target_combo, defaults.get("target", ""))
        self._set_combo_text(self.trace_protocol_combo, defaults.get("protocol", "TCP"))
        self.trace_port_input.setText(defaults.get("port", ""))

        self._loading_state = False
        self._dirty = False
        self._update_lab_summary()
        self._update_focus_context_card()
        self._refresh_topology_surface()

    def reset_workspace(self):
        self.load_state(
            {
                "lab_profile": {
                    "lab_name": "DMZ Exposure Lab",
                    "mgmt_subnet": "10.0.0.0/24",
                    "edge_type": "Perimeter firewall",
                },
                "devices": [
                    {"Device": "edge-fw", "Type": "Firewall", "Mgmt IP": "10.0.0.1", "Role": "Perimeter"},
                    {"Device": "dist-sw1", "Type": "Switch", "Mgmt IP": "10.0.0.2", "Role": "Distribution"},
                    {"Device": "dmz-web", "Type": "Server", "Mgmt IP": "10.0.0.20", "Role": "DMZ app"},
                ],
                "segments": [
                    {"VLAN": "10", "Name": "MGMT", "CIDR": "10.0.0.0/24", "Gateway": "10.0.0.1"},
                    {"VLAN": "30", "Name": "DMZ", "CIDR": "172.16.30.0/24", "Gateway": "172.16.30.1"},
                ],
                "rules": [
                    {"Source": "Internet", "Target": "dmz-web", "Proto": "TCP", "Port": "443", "Action": "allow"},
                    {"Source": "Internet", "Target": "dist-sw1", "Proto": "TCP", "Port": "22", "Action": "deny"},
                ],
                "interfaces": [
                    {"Device": "edge-fw", "Interface": "Gig0/0", "IP/CIDR": "203.0.113.10/29", "VLAN": "WAN", "Status": "up"},
                    {"Device": "edge-fw", "Interface": "Gig0/1", "IP/CIDR": "172.16.30.1/24", "VLAN": "30", "Status": "up"},
                    {"Device": "dmz-web", "Interface": "eth0", "IP/CIDR": "172.16.30.20/24", "VLAN": "30", "Status": "up"},
                ],
                "exposures": [
                    {"Device": "dmz-web", "Service": "HTTPS", "Proto": "TCP", "Port": "443", "Visibility": "published"},
                    {"Device": "dmz-web", "Service": "SSH", "Proto": "TCP", "Port": "22", "Visibility": "internal only"},
                ],
                "topology_notes": "Internet hits edge-fw, then DMZ services are selectively published to dmz-web.",
                "operations_notes": "Keep admin SSH internal only.\nValidate east-west restrictions before exposing more apps.",
                "trace_output": "Run Simulate Path to evaluate a flow.",
                "trace_defaults": {"source": "Internet", "target": "dmz-web", "protocol": "TCP", "port": "443"},
            }
        )

    def has_unsaved_changes(self):
        return self._dirty

    def zoom_in(self):
        self.current_editor_font_size = min(self.current_editor_font_size + 1, 26)
        self._apply_editor_font_size()

    def zoom_out(self):
        self.current_editor_font_size = max(self.current_editor_font_size - 1, 8)
        self._apply_editor_font_size()

    def reset_zoom(self):
        self.current_editor_font_size = self.default_editor_font_size
        self._apply_editor_font_size()

    def _apply_editor_font_size(self):
        for widget in [self.topology_notes, self.operations_notes, self.trace_output]:
            font = widget.font() if widget.font().family() else QFont("JetBrains Mono")
            font.setPointSize(self.current_editor_font_size)
            widget.setFont(font)

    def load_legacy_topology(self, objects, connections):
        devices = []
        exposures = []
        topology_lines = ["Imported from legacy sandbox objects.", ""]

        network_types = {
            "computer": "Computer",
            "server": "Server",
            "router": "Router",
            "switch": "Switch",
            "firewall": "Firewall",
            "access_point": "Access Point",
            "modem": "Modem",
            "container": "Container",
        }

        service_ports = {
            "apache": "80",
            "nginx": "80",
            "iis": "80",
            "tomcat": "8080",
            "mysql": "3306",
            "postgresql": "5432",
            "mongodb": "27017",
            "redis": "6379",
        }

        for obj in objects:
            obj_type = getattr(getattr(obj, "object_type", None), "value", "").lower()
            obj_name = getattr(obj, "name", obj_type or "object")
            props = getattr(obj, "properties", {}) or {}

            if obj_type in network_types:
                devices.append(
                    {
                        "Device": obj_name,
                        "Type": network_types[obj_type],
                        "Mgmt IP": str(props.get("ip_address", props.get("ip", ""))),
                        "Role": str(props.get("role", "Modeled device")),
                    }
                )
            elif obj_type in service_ports:
                exposures.append(
                    {
                        "Device": obj_name,
                        "Service": obj_type.upper(),
                        "Proto": "TCP",
                        "Port": service_ports[obj_type],
                        "Visibility": "published",
                    }
                )

            topology_lines.append(f"- {obj_name} ({obj_type or 'unknown'})")

        for connection in connections:
            source_id = getattr(connection, "source_id", "")
            target_id = getattr(connection, "target_id", "")
            topology_lines.append(f"- Link: {source_id} -> {target_id}")

        self.load_state(
            {
                "lab_profile": {
                    "lab_name": "Imported legacy topology",
                    "mgmt_subnet": "",
                    "edge_type": "Perimeter firewall",
                },
                "devices": devices,
                "segments": [],
                "rules": [],
                "interfaces": [],
                "exposures": exposures,
                "topology_notes": "\n".join(topology_lines[:24]),
                "operations_notes": "Legacy import completed. Add VLANs, ACLs, and interfaces manually to refine the lab.",
                "trace_output": "Imported legacy sandbox. Build policy before simulating paths.",
                "trace_defaults": {"source": "Internet", "target": devices[0]["Device"] if devices else "", "protocol": "TCP", "port": "443"},
            }
        )
        self.status_message.emit("Legacy topology imported into Network Lab")

    def _table_to_dicts(self, table, headers):
        rows = []
        for row in range(table.rowCount()):
            entry = {}
            for column, header in enumerate(headers):
                entry[header] = self._table_cell_text(table, row, column)
            rows.append(entry)
        return rows

    def _load_table_from_dicts(self, table, rows, headers):
        table.blockSignals(True)
        table.setRowCount(0)
        for row_data in rows:
            row = table.rowCount()
            table.insertRow(row)
            for column, header in enumerate(headers):
                table.setItem(row, column, QTableWidgetItem(str(row_data.get(header, ""))))
        table.blockSignals(False)

    def _table_cell_text(self, table, row, column):
        item = table.item(row, column)
        return item.text().strip() if item else ""

    def _set_combo_text(self, combo, value):
        index = combo.findText(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
