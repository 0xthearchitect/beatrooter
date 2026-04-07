from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
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
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class OSWorkspaceWidget(QWidget):
    status_message = pyqtSignal(str)

    SERVICE_HEADERS = ["Service", "Port", "Proto", "Mode", "Status"]
    USER_HEADERS = ["User", "Role", "Policy"]
    PATH_HEADERS = ["Path", "Kind", "State"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_editor_font_size = 11
        self.current_editor_font_size = self.default_editor_font_size
        self._dirty = False
        self._loading_state = False
        self._build_ui()
        self._bind_events()
        self._apply_styles()
        self.reset_workspace()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("OSWorkspaceSplitter")
        root_layout.addWidget(self.main_splitter)

        self.main_splitter.addWidget(self._build_sidebar_panel())
        self.main_splitter.addWidget(self._build_lab_panel())
        self.main_splitter.addWidget(self._build_surface_panel())
        self.main_splitter.setSizes([320, 760, 340])

    def _build_sidebar_panel(self):
        panel = QFrame()
        panel.setObjectName("OSSidebarPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.activity_bar = QFrame()
        self.activity_bar.setObjectName("OSActivityBar")
        self.activity_bar.setFixedWidth(58)
        activity_layout = QVBoxLayout(self.activity_bar)
        activity_layout.setContentsMargins(8, 10, 8, 10)
        activity_layout.setSpacing(8)

        self.activity_snapshots_btn = self._create_activity_button("VM", "Snapshots")
        self.activity_services_btn = self._create_activity_button("SV", "Services")
        self.activity_users_btn = self._create_activity_button("ID", "Users & Policies")

        activity_layout.addWidget(self.activity_snapshots_btn)
        activity_layout.addWidget(self.activity_services_btn)
        activity_layout.addWidget(self.activity_users_btn)
        activity_layout.addStretch(1)

        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.setObjectName("OSSidebarStack")
        self.sidebar_stack.addWidget(self._build_snapshots_view())
        self.sidebar_stack.addWidget(self._build_services_view())
        self.sidebar_stack.addWidget(self._build_users_view())

        layout.addWidget(self.activity_bar)
        layout.addWidget(self.sidebar_stack, 1)
        self._set_activity_view(0)
        return panel

    def _build_snapshots_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("VM SNAPSHOTS")
        title.setObjectName("WorkspaceSectionTitle")
        layout.addWidget(title)

        identity_group = QGroupBox("Machine Identity")
        identity_layout = QFormLayout(identity_group)
        self.os_family_combo = QComboBox()
        self.os_family_combo.addItems(["Windows 11", "Ubuntu 24.04", "Kali Linux", "macOS", "Custom"])
        self.hostname_input = QLineEdit()
        self.primary_ip_input = QLineEdit()
        self.exposure_combo = QComboBox()
        self.exposure_combo.addItems(["Internal only", "Mixed exposure", "Internet facing honeypot"])
        identity_layout.addRow("OS Profile:", self.os_family_combo)
        identity_layout.addRow("Hostname:", self.hostname_input)
        identity_layout.addRow("Primary IP:", self.primary_ip_input)
        identity_layout.addRow("Exposure:", self.exposure_combo)
        layout.addWidget(identity_group)

        snapshot_group = QGroupBox("Checkpoint Timeline")
        snapshot_layout = QVBoxLayout(snapshot_group)
        self.snapshot_list = QListWidget()
        snapshot_layout.addWidget(self.snapshot_list, 1)

        button_row = QHBoxLayout()
        self.add_snapshot_button = QPushButton("New Snapshot")
        self.revert_snapshot_button = QPushButton("Revert")
        self.diff_snapshot_button = QPushButton("Diff")
        button_row.addWidget(self.add_snapshot_button)
        button_row.addWidget(self.revert_snapshot_button)
        button_row.addWidget(self.diff_snapshot_button)
        snapshot_layout.addLayout(button_row)
        layout.addWidget(snapshot_group, 1)
        return view

    def _build_services_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("SERVICES AND HONEYPOTS")
        title.setObjectName("WorkspaceSectionTitle")
        layout.addWidget(title)

        template_row = QHBoxLayout()
        self.service_template_combo = QComboBox()
        self.service_template_combo.addItems(["SSH", "HTTP", "HTTPS", "SMB", "MySQL", "RDP", "Custom"])
        self.add_service_button = QPushButton("Deploy")
        self.remove_service_button = QPushButton("Remove")
        template_row.addWidget(self.service_template_combo, 1)
        template_row.addWidget(self.add_service_button)
        template_row.addWidget(self.remove_service_button)
        layout.addLayout(template_row)

        self.services_table = self._create_table(self.SERVICE_HEADERS)
        layout.addWidget(self.services_table, 1)

        helper = QLabel(
            "Treat this as the inside of the VM: listeners, banners, and fake services live here."
        )
        helper.setObjectName("WorkspaceHelperLabel")
        helper.setWordWrap(True)
        layout.addWidget(helper)
        return view

    def _build_users_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("IDENTITY AND POLICY")
        title.setObjectName("WorkspaceSectionTitle")
        layout.addWidget(title)

        button_row = QHBoxLayout()
        self.add_user_button = QPushButton("Add User")
        self.remove_user_button = QPushButton("Remove")
        button_row.addWidget(self.add_user_button)
        button_row.addWidget(self.remove_user_button)
        layout.addLayout(button_row)

        self.users_table = self._create_table(self.USER_HEADERS)
        layout.addWidget(self.users_table, 1)

        self.policy_notes = QPlainTextEdit()
        self.policy_notes.setObjectName("WorkspaceEditor")
        self.policy_notes.setPlaceholderText("Security policy notes, MFA gaps, local admin findings...")
        layout.addWidget(self.policy_notes, 1)
        return view

    def _build_lab_panel(self):
        panel = QFrame()
        panel.setObjectName("OSLabPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("OS VM LAB")
        title.setObjectName("WorkspaceMainTitle")
        self.current_snapshot_label = QLabel("Snapshot: baseline")
        self.current_snapshot_label.setObjectName("WorkspaceContextLabel")
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.current_snapshot_label)
        layout.addLayout(header_row)

        self.lab_tabs = QTabWidget()
        self.lab_tabs.setObjectName("OSLabTabs")
        self.lab_tabs.addTab(self._build_overview_tab(), "Overview")
        self.lab_tabs.addTab(self._build_filesystem_tab(), "Filesystem")
        self.lab_tabs.addTab(self._build_timeline_tab(), "Timeline")
        layout.addWidget(self.lab_tabs, 1)
        return panel

    def _build_overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.overview_editor = QPlainTextEdit()
        self.overview_editor.setObjectName("WorkspaceEditor")
        self.overview_editor.setPlaceholderText(
            "Describe the current machine state, malware bait, logging hooks, or snapshot goal."
        )
        layout.addWidget(self.overview_editor, 1)
        return tab

    def _build_filesystem_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        button_row = QHBoxLayout()
        self.add_path_button = QPushButton("Add Path")
        self.remove_path_button = QPushButton("Remove")
        button_row.addWidget(self.add_path_button)
        button_row.addWidget(self.remove_path_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.filesystem_table = self._create_table(self.PATH_HEADERS)
        layout.addWidget(self.filesystem_table, 1)
        return tab

    def _build_timeline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.timeline_editor = QPlainTextEdit()
        self.timeline_editor.setObjectName("WorkspaceEditor")
        self.timeline_editor.setPlaceholderText(
            "Write forensic notes, attacker interactions, and what changed between checkpoints."
        )
        layout.addWidget(self.timeline_editor, 1)
        return tab

    def _build_surface_panel(self):
        panel = QFrame()
        panel.setObjectName("OSSurfacePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("ATTACK SURFACE")
        title.setObjectName("WorkspaceSectionTitle")
        layout.addWidget(title)

        self.surface_summary_label = QLabel()
        self.surface_summary_label.setObjectName("WorkspaceSummaryLabel")
        self.surface_summary_label.setWordWrap(True)
        layout.addWidget(self.surface_summary_label)

        self.run_surface_test_button = QPushButton("Run Exposure Test")
        layout.addWidget(self.run_surface_test_button)

        self.surface_test_output = QPlainTextEdit()
        self.surface_test_output.setObjectName("WorkspaceReadOnly")
        self.surface_test_output.setReadOnly(True)
        layout.addWidget(self.surface_test_output, 1)

        self.snapshot_diff_output = QPlainTextEdit()
        self.snapshot_diff_output.setObjectName("WorkspaceReadOnly")
        self.snapshot_diff_output.setReadOnly(True)
        self.snapshot_diff_output.setPlaceholderText("Snapshot diff summary appears here.")
        layout.addWidget(self.snapshot_diff_output, 1)
        return panel

    def _bind_events(self):
        self.activity_snapshots_btn.clicked.connect(lambda: self._set_activity_view(0))
        self.activity_services_btn.clicked.connect(lambda: self._set_activity_view(1))
        self.activity_users_btn.clicked.connect(lambda: self._set_activity_view(2))

        self.add_snapshot_button.clicked.connect(self._create_snapshot)
        self.revert_snapshot_button.clicked.connect(self._revert_to_selected_snapshot)
        self.diff_snapshot_button.clicked.connect(self._render_snapshot_diff)
        self.add_service_button.clicked.connect(self._deploy_service_template)
        self.remove_service_button.clicked.connect(lambda: self._remove_selected_rows(self.services_table))
        self.add_user_button.clicked.connect(self._add_user_row)
        self.remove_user_button.clicked.connect(lambda: self._remove_selected_rows(self.users_table))
        self.add_path_button.clicked.connect(self._add_path_row)
        self.remove_path_button.clicked.connect(lambda: self._remove_selected_rows(self.filesystem_table))
        self.run_surface_test_button.clicked.connect(self._run_exposure_test)

        self.snapshot_list.currentTextChanged.connect(self._on_snapshot_changed)

        for widget in [
            self.os_family_combo,
            self.exposure_combo,
            self.hostname_input,
            self.primary_ip_input,
            self.overview_editor,
            self.timeline_editor,
            self.policy_notes,
        ]:
            self._bind_dirty_signal(widget)

        self.services_table.itemChanged.connect(lambda _item=None: self._mark_dirty("Service surface updated"))
        self.users_table.itemChanged.connect(lambda _item=None: self._mark_dirty("Identity model updated"))
        self.filesystem_table.itemChanged.connect(lambda _item=None: self._mark_dirty("Filesystem model updated"))

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
            QFrame#OSSidebarPanel, QFrame#OSSurfacePanel {
                background-color: #0d1523;
                border-right: 1px solid #1f2d43;
            }
            QFrame#OSLabPanel {
                background-color: #09111d;
            }
            QFrame#OSActivityBar {
                background-color: #08101b;
                border-right: 1px solid #1f2d43;
            }
            QStackedWidget#OSSidebarStack, QTabWidget#OSLabTabs::pane {
                background-color: #0d1523;
            }
            QPushButton#WorkspaceActivityButton {
                background-color: #102036;
                color: #9fc3ff;
                border: 1px solid #18304e;
                border-radius: 8px;
                font-weight: 700;
            }
            QPushButton#WorkspaceActivityButton:checked,
            QPushButton#WorkspaceActivityButton:hover {
                background-color: #173053;
                color: #ffffff;
                border-color: #3874d8;
            }
            QLabel#WorkspaceSectionTitle {
                color: #dce9ff;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 0.08em;
            }
            QLabel#WorkspaceMainTitle {
                color: #f4f8ff;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#WorkspaceContextLabel {
                color: #94add2;
                font-size: 11px;
            }
            QLabel#WorkspaceHelperLabel, QLabel#WorkspaceSummaryLabel {
                color: #9fb1ca;
                font-size: 11px;
            }
            QGroupBox {
                color: #dce9ff;
                border: 1px solid #1f2d43;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 10px;
                background-color: #101b2d;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 4px;
            }
            QLineEdit, QComboBox, QListWidget, QTableWidget, QPlainTextEdit, QTabWidget::pane {
                background-color: #132138;
                color: #e5efff;
                border: 1px solid #1f2d43;
                border-radius: 8px;
                selection-background-color: #2b65c8;
            }
            QHeaderView::section {
                background-color: #102036;
                color: #cfe0ff;
                border: none;
                padding: 6px;
                font-weight: 700;
            }
            QPushButton {
                background-color: #173053;
                color: #f4f8ff;
                border: 1px solid #26568f;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1c4273;
                border-color: #3874d8;
            }
            QTabBar::tab {
                background-color: #101b2d;
                color: #92add8;
                padding: 8px 12px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #173053;
                color: #ffffff;
            }
            QPlainTextEdit#WorkspaceReadOnly {
                background-color: #0e1828;
                color: #c2d3ec;
            }
            """
        )
        self._apply_editor_font_size()

    def _create_activity_button(self, text, tooltip):
        button = QPushButton(text)
        button.setObjectName("WorkspaceActivityButton")
        button.setCheckable(True)
        button.setToolTip(tooltip)
        button.setFixedSize(40, 34)
        return button

    def _create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        return table

    def _set_activity_view(self, index):
        self.sidebar_stack.setCurrentIndex(index)
        self.activity_snapshots_btn.setChecked(index == 0)
        self.activity_services_btn.setChecked(index == 1)
        self.activity_users_btn.setChecked(index == 2)

    def _mark_dirty(self, status_message=None):
        if self._loading_state:
            return
        self._dirty = True
        self._update_surface_summary()
        if status_message:
            self.status_message.emit(status_message)

    def _create_snapshot(self):
        snapshot_name = f"snapshot-{self.snapshot_list.count() + 1:02d} @ {datetime.now().strftime('%H:%M:%S')}"
        self.snapshot_list.addItem(snapshot_name)
        self.snapshot_list.setCurrentRow(self.snapshot_list.count() - 1)
        self.current_snapshot_label.setText(f"Snapshot: {snapshot_name}")
        self._mark_dirty("Snapshot captured")

    def _revert_to_selected_snapshot(self):
        item = self.snapshot_list.currentItem()
        if not item:
            return
        self.current_snapshot_label.setText(f"Snapshot: {item.text()}")
        self.snapshot_diff_output.setPlainText(
            f"Reverted VM view to {item.text()}.\n\nUse the Timeline tab to describe what was restored."
        )
        self._mark_dirty("Snapshot restored")

    def _on_snapshot_changed(self, snapshot_name):
        if snapshot_name:
            self.current_snapshot_label.setText(f"Snapshot: {snapshot_name}")

    def _render_snapshot_diff(self):
        snapshots = [self.snapshot_list.item(index).text() for index in range(self.snapshot_list.count())]
        if len(snapshots) < 2:
            self.snapshot_diff_output.setPlainText("Create at least two snapshots to compare VM state.")
            return

        newer = snapshots[-1]
        older = snapshots[-2]
        service_count = self.services_table.rowCount()
        path_count = self.filesystem_table.rowCount()
        self.snapshot_diff_output.setPlainText(
            f"Diffing {older} -> {newer}\n"
            f"- Services tracked: {service_count}\n"
            f"- Filesystem artifacts tracked: {path_count}\n"
            f"- Policy notes length: {len(self.policy_notes.toPlainText().splitlines())} lines"
        )
        self.status_message.emit("Snapshot diff refreshed")

    def _deploy_service_template(self):
        template = self._service_template_payload(self.service_template_combo.currentText())
        row = self.services_table.rowCount()
        self.services_table.insertRow(row)
        for column, value in enumerate(template):
            self.services_table.setItem(row, column, QTableWidgetItem(value))
        self.services_table.selectRow(row)
        self._mark_dirty("Service template deployed")

    def _service_template_payload(self, template_name):
        templates = {
            "SSH": ["OpenSSH", "22", "TCP", "Honeypot", "Listening"],
            "HTTP": ["nginx", "80", "TCP", "Mock app", "Listening"],
            "HTTPS": ["Traefik", "443", "TCP", "Proxy honeypot", "Listening"],
            "SMB": ["SMB bait", "445", "TCP", "Honeypot", "Listening"],
            "MySQL": ["MySQL decoy", "3306", "TCP", "Credential trap", "Listening"],
            "RDP": ["RDP lure", "3389", "TCP", "Honeypot", "Listening"],
            "Custom": ["Custom listener", "0", "TCP", "Manual", "Draft"],
        }
        return templates.get(template_name, templates["Custom"])

    def _add_user_row(self):
        row = self.users_table.rowCount()
        self.users_table.insertRow(row)
        defaults = [f"user{row + 1}", "Analyst", "MFA optional"]
        for column, value in enumerate(defaults):
            self.users_table.setItem(row, column, QTableWidgetItem(value))
        self.users_table.selectRow(row)
        self._mark_dirty("User added")

    def _add_path_row(self):
        row = self.filesystem_table.rowCount()
        self.filesystem_table.insertRow(row)
        defaults = [f"/opt/lab/artifact-{row + 1}", "File", "Tracked"]
        for column, value in enumerate(defaults):
            self.filesystem_table.setItem(row, column, QTableWidgetItem(value))
        self.filesystem_table.selectRow(row)
        self._mark_dirty("Filesystem artifact added")

    def _remove_selected_rows(self, table):
        selected_rows = sorted({index.row() for index in table.selectionModel().selectedRows()}, reverse=True)
        if not selected_rows:
            return
        for row in selected_rows:
            table.removeRow(row)
        self._mark_dirty("Workspace rows removed")

    def _run_exposure_test(self):
        lines = [
            f"Hostname: {self.hostname_input.text().strip() or 'unnamed-vm'}",
            f"OS profile: {self.os_family_combo.currentText()}",
            f"Exposure: {self.exposure_combo.currentText()}",
            "",
        ]

        if self.services_table.rowCount() == 0:
            lines.append("No listeners are configured yet.")
        else:
            for row in range(self.services_table.rowCount()):
                service = self._table_cell_text(self.services_table, row, 0)
                port = self._table_cell_text(self.services_table, row, 1)
                proto = self._table_cell_text(self.services_table, row, 2)
                mode = self._table_cell_text(self.services_table, row, 3)
                status = self._table_cell_text(self.services_table, row, 4)
                visibility = "reachable" if status.lower() == "listening" else "staged"
                lines.append(f"- {service} on {proto}/{port}: {mode}, {status}, {visibility}")

        self.surface_test_output.setPlainText("\n".join(lines))
        self._update_surface_summary()
        self.status_message.emit("Exposure test simulated")

    def _update_surface_summary(self):
        total_services = self.services_table.rowCount()
        honeypots = 0
        listening = 0
        for row in range(total_services):
            mode = self._table_cell_text(self.services_table, row, 3).lower()
            status = self._table_cell_text(self.services_table, row, 4).lower()
            if "honeypot" in mode or "trap" in mode:
                honeypots += 1
            if status == "listening":
                listening += 1

        self.surface_summary_label.setText(
            "VM summary\n"
            f"- Snapshots: {self.snapshot_list.count()}\n"
            f"- Services tracked: {total_services}\n"
            f"- Honeypot listeners: {honeypots}\n"
            f"- Listening now: {listening}\n"
            f"- Users modeled: {self.users_table.rowCount()}"
        )

    def to_dict(self):
        return {
            "machine_profile": {
                "os_family": self.os_family_combo.currentText(),
                "hostname": self.hostname_input.text().strip(),
                "primary_ip": self.primary_ip_input.text().strip(),
                "exposure": self.exposure_combo.currentText(),
            },
            "snapshots": [self.snapshot_list.item(index).text() for index in range(self.snapshot_list.count())],
            "current_snapshot": self.current_snapshot_label.text().replace("Snapshot: ", "", 1),
            "services": self._table_to_dicts(self.services_table, self.SERVICE_HEADERS),
            "users": self._table_to_dicts(self.users_table, self.USER_HEADERS),
            "filesystem": self._table_to_dicts(self.filesystem_table, self.PATH_HEADERS),
            "overview": self.overview_editor.toPlainText(),
            "timeline": self.timeline_editor.toPlainText(),
            "policy_notes": self.policy_notes.toPlainText(),
            "surface_test_output": self.surface_test_output.toPlainText(),
            "snapshot_diff_output": self.snapshot_diff_output.toPlainText(),
        }

    def load_state(self, state):
        state = state or {}
        self._loading_state = True

        profile = state.get("machine_profile", {})
        self._set_combo_text(self.os_family_combo, profile.get("os_family", "Windows 11"))
        self.hostname_input.setText(profile.get("hostname", "lab-vm"))
        self.primary_ip_input.setText(profile.get("primary_ip", "10.0.0.10"))
        self._set_combo_text(self.exposure_combo, profile.get("exposure", "Mixed exposure"))

        self.snapshot_list.clear()
        snapshots = state.get("snapshots", ["baseline"])
        for snapshot_name in snapshots:
            self.snapshot_list.addItem(snapshot_name)
        if self.snapshot_list.count():
            current_snapshot = state.get("current_snapshot") or self.snapshot_list.item(self.snapshot_list.count() - 1).text()
            matching_items = self.snapshot_list.findItems(current_snapshot, Qt.MatchFlag.MatchExactly)
            self.snapshot_list.setCurrentItem(matching_items[0] if matching_items else self.snapshot_list.item(self.snapshot_list.count() - 1))
            self.current_snapshot_label.setText(f"Snapshot: {current_snapshot}")
        else:
            self.current_snapshot_label.setText("Snapshot: baseline")

        self._load_table_from_dicts(self.services_table, state.get("services", []), self.SERVICE_HEADERS)
        self._load_table_from_dicts(self.users_table, state.get("users", []), self.USER_HEADERS)
        self._load_table_from_dicts(self.filesystem_table, state.get("filesystem", []), self.PATH_HEADERS)

        self.overview_editor.setPlainText(state.get("overview", ""))
        self.timeline_editor.setPlainText(state.get("timeline", ""))
        self.policy_notes.setPlainText(state.get("policy_notes", ""))
        self.surface_test_output.setPlainText(state.get("surface_test_output", ""))
        self.snapshot_diff_output.setPlainText(state.get("snapshot_diff_output", ""))

        self._loading_state = False
        self._dirty = False
        self._update_surface_summary()

    def reset_workspace(self):
        self.load_state(
            {
                "machine_profile": {
                    "os_family": "Ubuntu 24.04",
                    "hostname": "decoy-app-01",
                    "primary_ip": "10.10.10.21",
                    "exposure": "Internet facing honeypot",
                },
                "snapshots": ["baseline", "pre-ssh-bait"],
                "current_snapshot": "pre-ssh-bait",
                "services": [
                    {
                        "Service": "OpenSSH",
                        "Port": "22",
                        "Proto": "TCP",
                        "Mode": "Honeypot",
                        "Status": "Listening",
                    },
                    {
                        "Service": "nginx",
                        "Port": "80",
                        "Proto": "TCP",
                        "Mode": "Mock app",
                        "Status": "Listening",
                    },
                ],
                "users": [{"User": "analyst", "Role": "Operator", "Policy": "MFA required"}],
                "filesystem": [
                    {"Path": "/var/www/html", "Kind": "Folder", "State": "Mounted"},
                    {"Path": "/etc/ssh/sshd_config", "Kind": "Config", "State": "Tracked"},
                ],
                "overview": "This VM is staged as a credential trap with two exposed services and quick snapshot rollback.",
                "timeline": "Baseline captured.\nSSH bait configured.\nWaiting for first interaction.",
                "policy_notes": "Local admin disabled.\nAuditd enabled.\nOutbound access reduced to package mirrors.",
                "surface_test_output": "Run Exposure Test to generate a fresh simulation report.",
                "snapshot_diff_output": "Diffing baseline -> pre-ssh-bait\n- SSH listener introduced\n- Web lure enabled",
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
        editor_widgets = [
            self.overview_editor,
            self.timeline_editor,
            self.policy_notes,
            self.surface_test_output,
            self.snapshot_diff_output,
        ]
        for widget in editor_widgets:
            font = widget.font() if widget.font().family() else QFont("JetBrains Mono")
            font.setPointSize(self.current_editor_font_size)
            widget.setFont(font)

    def load_analysis_results(self, objects):
        services = []
        users = []
        filesystem = []
        summary_lines = [f"Imported {len(objects)} observed components into the VM lab.", ""]

        for obj in objects:
            obj_type = getattr(getattr(obj, "object_type", None), "value", "").lower()
            props = getattr(obj, "properties", {}) or {}
            obj_name = getattr(obj, "name", obj_type or "object")

            if obj_type in {"service", "running_service"}:
                services.append(
                    {
                        "Service": obj_name,
                        "Port": str(props.get("port", props.get("local_port", "-"))),
                        "Proto": str(props.get("protocol", "TCP")).upper(),
                        "Mode": "Observed",
                        "Status": "Listening",
                    }
                )
            elif obj_type == "open_port":
                services.append(
                    {
                        "Service": str(props.get("service", obj_name)),
                        "Port": str(props.get("port", props.get("number", obj_name))),
                        "Proto": str(props.get("protocol", "TCP")).upper(),
                        "Mode": "Observed",
                        "Status": "Listening",
                    }
                )
            elif obj_type == "user_account":
                users.append(
                    {
                        "User": obj_name,
                        "Role": str(props.get("role", "Local account")),
                        "Policy": str(props.get("policy", "Observed")),
                    }
                )
            elif obj_type in {"file", "folder", "config_file", "registry_key", "security_policy", "system_info", "network_interface"}:
                filesystem.append(
                    {
                        "Path": str(props.get("path", obj_name)),
                        "Kind": obj_type.replace("_", " ").title(),
                        "State": str(props.get("state", "Observed")),
                    }
                )

            summary_lines.append(f"- {obj_name} ({obj_type or 'unknown'})")

        self.load_state(
            {
                "machine_profile": {
                    "os_family": "Observed System",
                    "hostname": "analysis-import",
                    "primary_ip": "",
                    "exposure": "Mixed exposure",
                },
                "snapshots": ["analysis-import"],
                "current_snapshot": "analysis-import",
                "services": services,
                "users": users,
                "filesystem": filesystem,
                "overview": "\n".join(summary_lines[:18]),
                "timeline": "Imported from system analysis.\nReview the modeled listeners and artifacts.",
                "policy_notes": "Imported content is observational. Refine roles, banners, and hardening manually.",
                "surface_test_output": "Run Exposure Test to turn observed listeners into a scenario report.",
                "snapshot_diff_output": "Analysis import does not have a prior snapshot for diffing yet.",
            }
        )
        self.status_message.emit("System analysis imported into OS VM Lab")

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
