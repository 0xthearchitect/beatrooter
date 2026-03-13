import os
import re
import subprocess
import webbrowser
from PyQt6.QtCore import QDir, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QBrush, QFont, QColor
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QGridLayout,
    QLineEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QFrame,
    QHBoxLayout,
    QStackedWidget,
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None
    WEB_ENGINE_AVAILABLE = False


def detect_project_preview_url(project_folder: str) -> str:
    if not project_folder:
        return "http://localhost:3000"

    compose_candidates = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
    port_pattern = re.compile(r'["\']?(?P<host>\d{2,5})\s*:\s*(?P<container>\d{2,5})["\']?')
    preferred_ports = [80, 3000, 5173, 8080, 5000, 8000, 4200]

    ignored_dirs = {".git", "venv", ".venv", "__pycache__", "node_modules", ".idea", ".vscode"}
    compose_paths = []
    for root, dirs, files in os.walk(project_folder):
        dirs[:] = [directory for directory in dirs if directory not in ignored_dirs]
        for compose_file in compose_candidates:
            if compose_file in files:
                compose_paths.append(os.path.join(root, compose_file))

    compose_paths.sort(key=lambda path: (path.count(os.sep), path.lower()))

    traefik_hosts = []
    host_rule_pattern = re.compile(r"Host\(`([^`]+)`\)")

    for compose_path in compose_paths:

        try:
            with open(compose_path, "r", encoding="utf-8", errors="ignore") as handle:
                compose_content = handle.read()
        except OSError:
            continue

        ports = [int(match.group("host")) for match in port_pattern.finditer(compose_content)]
        if ports:
            for preferred in preferred_ports:
                if preferred in ports:
                    if preferred == 80:
                        return "http://localhost"
                    return f"http://localhost:{preferred}"
            return f"http://localhost:{ports[0]}"

        for host_match in host_rule_pattern.finditer(compose_content):
            host_value = host_match.group(1).strip()
            if host_value and host_value not in traefik_hosts:
                traefik_hosts.append(host_value)

    if traefik_hosts:
        # Prefer non-www domain for cleaner preview URL when available.
        preferred_host = next((host for host in traefik_hosts if not host.startswith("www.")), traefik_hosts[0])
        return f"https://{preferred_host}"

    package_json_path = os.path.join(project_folder, "package.json")
    if os.path.isfile(package_json_path):
        try:
            with open(package_json_path, "r", encoding="utf-8", errors="ignore") as handle:
                package_text = handle.read().lower()
            if "vite" in package_text:
                return "http://localhost:5173"
            if "next" in package_text:
                return "http://localhost:3000"
            return "http://localhost:3000"
        except OSError:
            pass

    if os.path.isfile(os.path.join(project_folder, "manage.py")) and not compose_paths:
        return "http://localhost:8000"
    if os.path.isfile(os.path.join(project_folder, "app.py")):
        return "http://localhost:5000"
    return "http://localhost:3000"


class AttackSimulatorDialog(QDialog):
    def __init__(self, project_folder: str = "", default_url: str = "http://localhost:3000", parent=None):
        super().__init__(parent)
        self.project_folder = project_folder
        self.default_url = default_url
        self.web_view = None
        self.active_fake_domain = ""
        self.active_target_url = default_url

        self.setWindowTitle("Attack Motor - Simulation Preview")
        self.resize(1100, 720)
        self._build_ui()
        self._prefill_configuration()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.config_tab = QWidget()
        self.preview_tab = QWidget()
        self.tabs.addTab(self.config_tab, "Configuration")
        self.tabs.addTab(self.preview_tab, "Preview")
        layout.addWidget(self.tabs)

        self._build_config_tab()
        self._build_preview_tab()

    def _build_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        form_group = QGroupBox("Simulation Setup")
        form_layout = QFormLayout(form_group)

        self.fake_domain_input = QLineEdit("sandbox.local.test")
        self.preview_url_input = QLineEdit(self.default_url)

        self.server_combo = QComboBox()
        self.server_combo.addItems(["Nginx", "Apache", "Node.js", "Django", "Flask", "Custom"])

        db_widget = QWidget()
        db_layout = QGridLayout(db_widget)
        db_layout.setContentsMargins(0, 0, 0, 0)
        db_layout.setSpacing(4)
        self.db_postgres = QCheckBox("PostgreSQL")
        self.db_mongo = QCheckBox("MongoDB")
        self.db_mysql = QCheckBox("MySQL")
        self.db_redis = QCheckBox("Redis")
        db_layout.addWidget(self.db_postgres, 0, 0)
        db_layout.addWidget(self.db_mongo, 0, 1)
        db_layout.addWidget(self.db_mysql, 1, 0)
        db_layout.addWidget(self.db_redis, 1, 1)

        form_layout.addRow("Fake Domain:", self.fake_domain_input)
        form_layout.addRow("Preview URL:", self.preview_url_input)
        form_layout.addRow("Server Simulation:", self.server_combo)
        form_layout.addRow("Database Simulation:", db_widget)
        layout.addWidget(form_group)

        button_row = QHBoxLayout()
        self.apply_config_button = QPushButton("Apply Simulation")
        self.open_preview_tab_button = QPushButton("Open Preview")
        self.open_external_button = QPushButton("Open External Browser")
        button_row.addWidget(self.apply_config_button)
        button_row.addWidget(self.open_preview_tab_button)
        button_row.addWidget(self.open_external_button)
        layout.addLayout(button_row)

        self.config_summary = QTextEdit()
        self.config_summary.setReadOnly(True)
        self.config_summary.setPlaceholderText("Simulation summary will appear here.")
        layout.addWidget(self.config_summary, 1)

        self.fake_domain_notice = QLabel(
            "Fake domain is mapped only inside this simulator.\n"
            "System browser needs DNS/hosts mapping to resolve it directly."
        )
        self.fake_domain_notice.setWordWrap(True)
        self.fake_domain_notice.setStyleSheet("color: #9aa8bf; font-size: 11px;")
        layout.addWidget(self.fake_domain_notice)

        self.apply_config_button.clicked.connect(self.apply_configuration)
        self.open_preview_tab_button.clicked.connect(self.open_preview_tab)
        self.open_external_button.clicked.connect(self.open_external_preview)

    def _build_preview_tab(self):
        layout = QVBoxLayout(self.preview_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        controls = QHBoxLayout()
        self.preview_address_input = QLineEdit(self.default_url)
        self.load_preview_button = QPushButton("Load")
        self.reload_preview_button = QPushButton("Reload")
        controls.addWidget(self.preview_address_input, 1)
        controls.addWidget(self.load_preview_button)
        controls.addWidget(self.reload_preview_button)
        layout.addLayout(controls)

        if WEB_ENGINE_AVAILABLE:
            self.web_view = QWebEngineView()
            layout.addWidget(self.web_view, 1)
            self.load_preview_button.clicked.connect(self.load_preview_from_bar)
            self.reload_preview_button.clicked.connect(self.reload_preview)
        else:
            fallback = QLabel(
                "Embedded preview requires PyQt WebEngine.\n"
                "Install: pip install PyQt6-WebEngine\n"
                "Use 'Open External Browser' in the Configuration tab for now."
            )
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setWordWrap(True)
            layout.addWidget(fallback, 1)
            self.load_preview_button.setEnabled(False)
            self.reload_preview_button.setEnabled(False)

    def _prefill_configuration(self):
        if self.project_folder:
            try:
                project_files = set(os.listdir(self.project_folder))
            except OSError:
                project_files = set()
            lowered_names = {name.lower() for name in project_files}

            if "nginx.conf" in lowered_names:
                self.server_combo.setCurrentText("Nginx")
            elif "apache2.conf" in lowered_names or ".htaccess" in lowered_names:
                self.server_combo.setCurrentText("Apache")
            elif "package.json" in lowered_names:
                self.server_combo.setCurrentText("Node.js")
            elif "manage.py" in lowered_names:
                self.server_combo.setCurrentText("Django")
            elif "app.py" in lowered_names:
                self.server_combo.setCurrentText("Flask")

            compose_candidates = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
            ignored_dirs = {".git", "venv", ".venv", "__pycache__", "node_modules", ".idea", ".vscode"}
            compose_content = ""

            for root, dirs, files in os.walk(self.project_folder):
                dirs[:] = [directory for directory in dirs if directory not in ignored_dirs]
                match = next((name for name in compose_candidates if name in files), None)
                if not match:
                    continue
                compose_path = os.path.join(root, match)
                try:
                    with open(compose_path, "r", encoding="utf-8", errors="ignore") as handle:
                        compose_content = handle.read().lower()
                except OSError:
                    compose_content = ""
                break

            if "postgres" in compose_content:
                self.db_postgres.setChecked(True)
            if "mongo" in compose_content:
                self.db_mongo.setChecked(True)
            if "mysql" in compose_content:
                self.db_mysql.setChecked(True)
            if "redis" in compose_content:
                self.db_redis.setChecked(True)

        summary_lines = [
            f"Project folder: {self.project_folder or 'Not selected'}",
            f"Detected preview URL: {self.default_url}",
            "",
            "Note: Fake domain simulation is UI-only for now.",
        ]
        self.config_summary.setPlainText("\n".join(summary_lines))

        if WEB_ENGINE_AVAILABLE:
            self.load_preview(self.default_url)

    def _selected_databases(self):
        dbs = []
        if self.db_postgres.isChecked():
            dbs.append("PostgreSQL")
        if self.db_mongo.isChecked():
            dbs.append("MongoDB")
        if self.db_mysql.isChecked():
            dbs.append("MySQL")
        if self.db_redis.isChecked():
            dbs.append("Redis")
        return dbs or ["None selected"]

    def apply_configuration(self):
        url = self.preview_url_input.text().strip() or self.default_url
        fake_domain = self.fake_domain_input.text().strip() or "sandbox.local.test"
        server = self.server_combo.currentText()
        dbs = ", ".join(self._selected_databases())
        self.active_fake_domain = fake_domain.lower()
        self.active_target_url = url

        summary_lines = [
            "Simulation Applied",
            f"- Fake domain: {fake_domain}",
            f"- Preview URL: {url}",
            f"- Server simulation: {server}",
            f"- Database simulation: {dbs}",
            "",
            "If Docker/localhost is running, Preview tab should load the app.",
            f"- Internal mapping: {fake_domain} -> {url}",
        ]
        self.config_summary.setPlainText("\n".join(summary_lines))
        self.preview_address_input.setText(url)
        self.load_preview(url)

    def open_preview_tab(self):
        self.tabs.setCurrentWidget(self.preview_tab)
        url = self.preview_url_input.text().strip() or self.default_url
        self.preview_address_input.setText(url)
        self.load_preview(url)

    def open_external_preview(self):
        url = self.preview_url_input.text().strip() or self.default_url
        webbrowser.open(self._resolve_url(url))

    def load_preview_from_bar(self):
        self.load_preview(self.preview_address_input.text().strip())

    def load_preview(self, raw_url: str):
        if not self.web_view:
            return
        self.web_view.setUrl(QUrl(self._resolve_url(raw_url or self.default_url)))

    def reload_preview(self):
        if self.web_view:
            self.web_view.reload()

    def _resolve_url(self, raw_url: str) -> str:
        url_text = (raw_url or self.default_url).strip()
        if not url_text.startswith(("http://", "https://")):
            url_text = f"http://{url_text}"

        parsed_input = QUrl(url_text)
        host = parsed_input.host().lower()

        fake_domain = (self.active_fake_domain or self.fake_domain_input.text().strip().lower())
        target_url_text = self.active_target_url or self.preview_url_input.text().strip() or self.default_url
        if not target_url_text.startswith(("http://", "https://")):
            target_url_text = f"http://{target_url_text}"
        parsed_target = QUrl(target_url_text)

        if fake_domain and host == fake_domain and parsed_target.isValid():
            # Keep user path/query/fragment but route host/port to actual preview endpoint.
            parsed_input.setScheme(parsed_target.scheme() or "http")
            parsed_input.setHost(parsed_target.host() or "localhost")
            parsed_input.setPort(parsed_target.port())
        return parsed_input.toString()


class WebWorkspaceWidget(QWidget):
    folder_loaded = pyqtSignal(str)
    file_opened = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_folder_path = ""
        self.current_file_path = ""
        self.detected_compose_files = []
        self.default_editor_font_size = 11
        self.current_editor_font_size = self.default_editor_font_size

        self._build_ui()
        self._bind_events()
        self._apply_styles()
        self.reset_workspace()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("WebWorkspaceSplitter")
        root_layout.addWidget(self.main_splitter)

        self.explorer_panel = self._build_explorer_panel()
        self.editor_panel = self._build_editor_panel()
        self.attack_panel = self._build_attack_panel()

        self.main_splitter.addWidget(self.explorer_panel)
        self.main_splitter.addWidget(self.editor_panel)
        self.main_splitter.addWidget(self.attack_panel)
        self.main_splitter.setSizes([280, 760, 320])

    def _build_explorer_panel(self):
        panel = QFrame()
        panel.setObjectName("WebExplorerPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.activity_bar = QFrame()
        self.activity_bar.setObjectName("WebActivityBar")
        self.activity_bar.setFixedWidth(48)
        activity_layout = QVBoxLayout(self.activity_bar)
        activity_layout.setContentsMargins(6, 8, 6, 8)
        activity_layout.setSpacing(6)

        self.activity_explorer_btn = self._create_activity_button("E", "Explorer")
        self.activity_search_btn = self._create_activity_button("S", "Search")
        self.activity_containers_btn = self._create_activity_button("C", "Containers")

        activity_layout.addWidget(self.activity_explorer_btn)
        activity_layout.addWidget(self.activity_search_btn)
        activity_layout.addWidget(self.activity_containers_btn)
        activity_layout.addStretch(1)

        self.sidebar_stack = QStackedWidget()
        self.sidebar_stack.setObjectName("WebSidebarStack")
        self.sidebar_stack.addWidget(self._build_explorer_view())
        self.sidebar_stack.addWidget(self._build_search_view())
        self.sidebar_stack.addWidget(self._build_containers_view())

        layout.addWidget(self.activity_bar)
        layout.addWidget(self.sidebar_stack, 1)

        self._set_activity_view(0)
        return panel

    def _create_activity_button(self, text: str, tooltip: str):
        button = QPushButton(text)
        button.setObjectName("ActivityBarButton")
        button.setCheckable(True)
        button.setToolTip(tooltip)
        button.setFixedHeight(34)
        return button

    def _build_explorer_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        title = QLabel("EXPLORER")
        title.setObjectName("WebSectionTitle")
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("WebOpenFolderButton")
        self.open_folder_button.setFixedHeight(26)

        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.open_folder_button)
        layout.addLayout(header_row)

        self.folder_label = QLabel("No folder selected")
        self.folder_label.setObjectName("WebFolderLabel")
        self.folder_label.setWordWrap(True)
        layout.addWidget(self.folder_label)

        self.file_model = QFileSystemModel(self)
        self.file_model.setRootPath(QDir.rootPath())
        self.file_model.setFilter(
            QDir.Filter.AllEntries
            | QDir.Filter.NoDotAndDotDot
            | QDir.Filter.AllDirs
            | QDir.Filter.Files
        )

        self.file_tree = QTreeView()
        self.file_tree.setObjectName("WebFileTree")
        self.file_tree.setModel(self.file_model)
        self.file_tree.setHeaderHidden(False)
        self.file_tree.setColumnWidth(0, 220)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setColumnHidden(1, True)
        self.file_tree.setColumnHidden(2, True)
        self.file_tree.setColumnHidden(3, True)

        self.explorer_empty_label = QLabel("Open Folder to load a project structure.")
        self.explorer_empty_label.setObjectName("WebExplorerEmptyState")
        self.explorer_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.explorer_stack = QStackedWidget()
        self.explorer_stack.setObjectName("WebExplorerStack")
        self.explorer_stack.addWidget(self.explorer_empty_label)
        self.explorer_stack.addWidget(self.file_tree)
        self.explorer_stack.setCurrentIndex(0)

        layout.addWidget(self.explorer_stack, 1)
        return view

    def _build_search_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("SEARCH")
        title.setObjectName("WebSectionTitle")
        layout.addWidget(title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in project files...")
        layout.addWidget(self.search_input)

        self.search_results = QListWidget()
        self.search_results.setObjectName("WebSearchResults")
        layout.addWidget(self.search_results, 1)
        return view

    def _build_containers_view(self):
        view = QWidget()
        layout = QVBoxLayout(view)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("CONTAINERS")
        title.setObjectName("WebSectionTitle")
        layout.addWidget(title)

        self.compose_status_label = QLabel("No docker-compose file detected.")
        self.compose_status_label.setObjectName("WebFolderLabel")
        self.compose_status_label.setWordWrap(True)
        layout.addWidget(self.compose_status_label)

        self.frontend_url_label = QLabel("Frontend URL detected: -")
        self.frontend_url_label.setObjectName("WebFolderLabel")
        self.frontend_url_label.setWordWrap(True)
        layout.addWidget(self.frontend_url_label)

        self.api_url_label = QLabel("API URL detected: -")
        self.api_url_label.setObjectName("WebFolderLabel")
        self.api_url_label.setWordWrap(True)
        layout.addWidget(self.api_url_label)

        self.compose_selector = QComboBox()
        self.compose_selector.setObjectName("WebComposeSelector")
        self.compose_selector.setEnabled(False)
        layout.addWidget(self.compose_selector)

        self.containers_list = QListWidget()
        self.containers_list.setObjectName("WebContainersList")
        layout.addWidget(self.containers_list, 1)

        button_row = QHBoxLayout()
        self.refresh_containers_button = QPushButton("Refresh")
        self.start_containers_button = QPushButton("Start")
        self.start_all_containers_button = QPushButton("Start All")
        self.stop_containers_button = QPushButton("Stop")
        button_row.addWidget(self.refresh_containers_button)
        button_row.addWidget(self.start_containers_button)
        button_row.addWidget(self.start_all_containers_button)
        button_row.addWidget(self.stop_containers_button)
        layout.addLayout(button_row)

        self.open_docker_tool_button = QPushButton("Open Docker Tool")
        layout.addWidget(self.open_docker_tool_button)
        return view

    def _set_activity_view(self, index: int):
        self.sidebar_stack.setCurrentIndex(index)
        self.activity_explorer_btn.setChecked(index == 0)
        self.activity_search_btn.setChecked(index == 1)
        self.activity_containers_btn.setChecked(index == 2)

    def _build_editor_panel(self):
        panel = QFrame()
        panel.setObjectName("WebEditorPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        title = QLabel("EDITOR")
        title.setObjectName("WebSectionTitle")
        self.current_file_label = QLabel("No file opened")
        self.current_file_label.setObjectName("WebCurrentFileLabel")
        self.current_file_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.current_file_label.setWordWrap(True)

        self.save_file_button = QPushButton("Save")
        self.save_file_button.setObjectName("WebSaveButton")
        self.save_file_button.setFixedHeight(26)
        self.save_file_button.setEnabled(False)

        header_row.addWidget(title)
        header_row.addWidget(self.current_file_label, 1)
        header_row.addWidget(self.save_file_button)
        layout.addLayout(header_row)

        self.code_editor = QPlainTextEdit()
        self.code_editor.setObjectName("WebCodeEditor")
        self.code_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code_editor.setReadOnly(True)
        self.code_editor.setPlainText(
            "Open a project folder on the left and click a file to edit it."
        )

        editor_font = QFont("JetBrains Mono")
        editor_font.setStyleHint(QFont.StyleHint.Monospace)
        editor_font.setPointSize(self.default_editor_font_size)
        self.code_editor.setFont(editor_font)

        layout.addWidget(self.code_editor, 1)
        return panel

    def _build_attack_panel(self):
        panel = QFrame()
        panel.setObjectName("WebAttackPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("MOTOR DE ATAQUE")
        title.setObjectName("WebSectionTitle")

        badge = QLabel("EM DESENVOLVIMENTO")
        badge.setObjectName("WebDevBadge")

        self.attack_context_label = QLabel(
            "Open a project folder to connect simulation settings\n"
            "with your codebase preview."
        )
        self.attack_context_label.setObjectName("WebAttackBody")
        self.attack_context_label.setWordWrap(True)
        self.attack_context_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.attack_simulator_button = QPushButton("Open Attack Simulator")
        self.attack_simulator_button.setObjectName("WebAttackButton")
        self.attack_simulator_button.setFixedHeight(30)

        self.attack_hint_label = QLabel(
            "The simulator opens two tabs:\n"
            "1. Configuration (domain/server/database simulation)\n"
            "2. Preview (embedded browser for localhost)"
        )
        self.attack_hint_label.setObjectName("WebAttackHint")
        self.attack_hint_label.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(badge)
        layout.addWidget(self.attack_context_label)
        layout.addWidget(self.attack_simulator_button)
        layout.addWidget(self.attack_hint_label)
        layout.addStretch(1)
        return panel

    def _bind_events(self):
        self.open_folder_button.clicked.connect(self.open_project_folder_dialog)
        self.file_tree.doubleClicked.connect(self._on_tree_double_click)
        self.save_file_button.clicked.connect(self.save_current_file)
        self.attack_simulator_button.clicked.connect(self.open_attack_simulator)
        self.activity_explorer_btn.clicked.connect(lambda: self._set_activity_view(0))
        self.activity_search_btn.clicked.connect(lambda: self._set_activity_view(1))
        self.activity_containers_btn.clicked.connect(lambda: self._set_activity_view(2))
        self.search_input.textChanged.connect(self._search_project_files)
        self.search_results.itemDoubleClicked.connect(self._open_search_result)
        self.compose_selector.currentIndexChanged.connect(self._render_selected_compose_services)
        self.refresh_containers_button.clicked.connect(self._refresh_containers_panel)
        self.start_containers_button.clicked.connect(self.start_detected_containers)
        self.start_all_containers_button.clicked.connect(self.start_all_detected_containers)
        self.stop_containers_button.clicked.connect(self.stop_detected_containers)
        self.open_docker_tool_button.clicked.connect(self._open_docker_tool)

    def _refresh_attack_context(self):
        if self.current_folder_path:
            suggested_url = detect_project_preview_url(self.current_folder_path)
            self.attack_context_label.setText(
                f"Project: {os.path.basename(self.current_folder_path)}\n"
                f"Suggested preview URL: {suggested_url}"
            )
        else:
            self.attack_context_label.setText(
                "Open a project folder to connect simulation settings\n"
                "with your codebase preview."
            )

    def open_attack_simulator(self):
        suggested_url = detect_project_preview_url(self.current_folder_path)
        dialog = AttackSimulatorDialog(
            project_folder=self.current_folder_path,
            default_url=suggested_url,
            parent=self,
        )
        dialog.exec()

    def _search_project_files(self, query: str):
        self.search_results.clear()
        query = (query or "").strip().lower()
        if not query or not self.current_folder_path:
            return

        results_added = 0
        max_results = 60

        for root, _, files in os.walk(self.current_folder_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, self.current_folder_path)
                matched_line = ""

                if query in filename.lower():
                    matched_line = "Filename match"
                else:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                            for line_no, line in enumerate(handle, start=1):
                                if query in line.lower():
                                    snippet = line.strip()[:110]
                                    matched_line = f"L{line_no}: {snippet}"
                                    break
                    except OSError:
                        continue

                if matched_line:
                    item = QListWidgetItem(f"{rel_path}  |  {matched_line}")
                    item.setData(Qt.ItemDataRole.UserRole, file_path)
                    self.search_results.addItem(item)
                    results_added += 1

                if results_added >= max_results:
                    return

    def _open_search_result(self, item: QListWidgetItem):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self.open_file(file_path)
            self._set_activity_view(0)

    def _find_compose_files(self):
        if not self.current_folder_path:
            return []

        candidates = {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
        ignored_dirs = {".git", "venv", ".venv", "__pycache__", "node_modules", ".idea", ".vscode"}
        compose_files = []

        for root, dirs, files in os.walk(self.current_folder_path):
            dirs[:] = [directory for directory in dirs if directory not in ignored_dirs]
            for filename in files:
                if filename in candidates:
                    compose_files.append(os.path.join(root, filename))

        compose_files.sort(key=lambda path: (path.count(os.sep), path.lower()))
        return compose_files

    def _detect_compose_file(self):
        if not self.detected_compose_files:
            return ""
        index = self.compose_selector.currentIndex()
        if 0 <= index < len(self.detected_compose_files):
            return self.detected_compose_files[index]
        return self.detected_compose_files[0]

    @staticmethod
    def _extract_urls_from_compose_text(compose_text: str):
        lower_text = compose_text.lower()
        host_rule_pattern = re.compile(r"Host\(`([^`]+)`\)")
        port_pattern = re.compile(r'["\']?(?P<host>\d{2,5})\s*:\s*(?P<container>\d{2,5})["\']?')

        frontend_url = ""
        api_url = ""

        hosts = [match.group(1).strip() for match in host_rule_pattern.finditer(compose_text)]
        for host in hosts:
            if "api." in host and not api_url:
                api_url = f"https://{host}/docs"
            elif not frontend_url:
                frontend_url = f"https://{host}"

        host_ports = [int(match.group("host")) for match in port_pattern.finditer(compose_text)]
        for port in host_ports:
            if port in (80, 8080, 3000, 5173, 4200) and not frontend_url:
                frontend_url = "http://localhost" if port == 80 else f"http://localhost:{port}"
            if port in (8000, 5000, 8081) and not api_url:
                api_url = f"http://localhost:{port}/docs"

        if "traefik.http.routers.api.rule" in lower_text and not api_url:
            host_match = next((host for host in hosts if "api." in host), "")
            if host_match:
                api_url = f"https://{host_match}/docs"

        return frontend_url, api_url

    def _update_detected_urls_labels(self):
        frontend_candidates = []
        api_candidates = []

        for compose_path in self.detected_compose_files:
            try:
                with open(compose_path, "r", encoding="utf-8", errors="ignore") as handle:
                    compose_text = handle.read()
            except OSError:
                continue

            frontend_url, api_url = self._extract_urls_from_compose_text(compose_text)
            if frontend_url:
                frontend_candidates.append(frontend_url)
            if api_url:
                api_candidates.append(api_url)

        frontend_value = frontend_candidates[0] if frontend_candidates else "-"
        api_value = api_candidates[0] if api_candidates else "-"
        self.frontend_url_label.setText(f"Frontend URL detected: {frontend_value}")
        self.api_url_label.setText(f"API URL detected: {api_value}")

    def _parse_compose_services(self, compose_path: str):
        services = []
        try:
            with open(compose_path, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
        except OSError:
            return services

        in_services = False
        services_indent = 0

        for raw_line in lines:
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            stripped = raw_line.strip()

            if not in_services:
                if stripped.startswith("services:"):
                    in_services = True
                    services_indent = indent
                continue

            if indent <= services_indent and stripped.endswith(":"):
                break

            if indent == services_indent + 2 and stripped.endswith(":") and not stripped.startswith("-"):
                services.append(stripped[:-1].strip())

        return services

    def _parse_external_networks(self, compose_path: str):
        external_networks = []
        try:
            with open(compose_path, "r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()
        except OSError:
            return external_networks

        in_networks = False
        networks_indent = 0
        current_network = ""
        current_network_indent = 0

        for raw_line in lines:
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            stripped = raw_line.strip()

            if not in_networks:
                if stripped == "networks:":
                    in_networks = True
                    networks_indent = indent
                continue

            if indent <= networks_indent and stripped.endswith(":"):
                break

            if indent == networks_indent + 2 and stripped.endswith(":") and not stripped.startswith("-"):
                current_network = stripped[:-1].strip()
                current_network_indent = indent
                continue

            if (
                current_network
                and indent > current_network_indent
                and stripped.lower().startswith("external:")
                and "true" in stripped.lower()
            ):
                external_networks.append(current_network)

        return sorted(set(external_networks))

    def _ensure_external_networks(self, compose_path: str):
        created = []
        missing = self._parse_external_networks(compose_path)
        if not missing:
            return created

        for network_name in missing:
            inspect_result = subprocess.run(
                ["docker", "network", "inspect", network_name],
                cwd=self.current_folder_path,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if inspect_result.returncode == 0:
                continue

            create_result = subprocess.run(
                ["docker", "network", "create", network_name],
                cwd=self.current_folder_path,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if create_result.returncode == 0:
                created.append(network_name)

        return created

    def _extract_missing_external_network(self, stderr_text: str, stdout_text: str = ""):
        merged = "\n".join([part for part in [stderr_text, stdout_text] if part]).strip()
        if not merged:
            return ""
        match = re.search(
            r"network\s+([a-zA-Z0-9_.-]+)\s+declared as external,\s+but could not be found",
            merged,
            flags=re.IGNORECASE,
        )
        return match.group(1) if match else ""

    def _create_network_if_missing(self, network_name: str):
        if not network_name:
            return False, "Missing network name."

        inspect_result = subprocess.run(
            ["docker", "network", "inspect", network_name],
            cwd=self.current_folder_path,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if inspect_result.returncode == 0:
            return True, ""

        create_result = subprocess.run(
            ["docker", "network", "create", network_name],
            cwd=self.current_folder_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if create_result.returncode == 0:
            return True, ""
        error_msg = create_result.stderr.strip() or create_result.stdout.strip() or "Unknown Docker error."
        return False, error_msg

    def _refresh_containers_panel(self):
        previous_selection = self._detect_compose_file()
        self.detected_compose_files = self._find_compose_files()

        self.compose_selector.blockSignals(True)
        self.compose_selector.clear()
        for compose_file in self.detected_compose_files:
            rel_path = os.path.relpath(compose_file, self.current_folder_path)
            self.compose_selector.addItem(rel_path)

        if self.detected_compose_files:
            self.compose_selector.setEnabled(True)
            if previous_selection in self.detected_compose_files:
                self.compose_selector.setCurrentIndex(self.detected_compose_files.index(previous_selection))
            else:
                self.compose_selector.setCurrentIndex(0)
            self.compose_status_label.setText(f"Compose files detected: {len(self.detected_compose_files)}")
            self.start_containers_button.setEnabled(True)
            self.start_all_containers_button.setEnabled(True)
            self.stop_containers_button.setEnabled(True)
        else:
            self.compose_selector.setEnabled(False)
            self.compose_status_label.setText("No docker-compose file detected.")
            self.start_containers_button.setEnabled(False)
            self.start_all_containers_button.setEnabled(False)
            self.stop_containers_button.setEnabled(False)
        self.compose_selector.blockSignals(False)

        self._update_detected_urls_labels()
        self._render_selected_compose_services()

    def _render_selected_compose_services(self):
        self.containers_list.clear()
        compose_path = self._detect_compose_file()
        if not compose_path:
            return

        rel_path = os.path.relpath(compose_path, self.current_folder_path)
        self.compose_status_label.setText(
            f"Compose {self.compose_selector.currentIndex() + 1}/{len(self.detected_compose_files)}: {rel_path}"
        )

        services = self._parse_compose_services(compose_path)
        if not services:
            self.containers_list.addItem("No services found under 'services:'")
            return

        running_services = set()
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", compose_path, "ps", "--services", "--status", "running"],
                cwd=self.current_folder_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode == 0:
                running_services = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        except (subprocess.SubprocessError, FileNotFoundError):
            running_services = set()

        for service in services:
            is_running = service in running_services
            status_text = "RUNNING" if is_running else "STOPPED"
            item = QListWidgetItem(f"{service}  [{status_text}]")
            item.setForeground(QBrush(QColor("#20c997") if is_running else QColor("#f6ad55")))
            self.containers_list.addItem(item)

    @staticmethod
    def _format_docker_error(stderr_text: str, stdout_text: str = ""):
        merged = "\n".join([part for part in [stderr_text, stdout_text] if part]).strip()
        if not merged:
            return "Docker command failed. Check Docker daemon and compose configuration."

        port_conflict = re.search(
            r"bind for [^:]*:(\d+)\s+failed:\s+port is already allocated",
            merged,
            flags=re.IGNORECASE,
        )
        if port_conflict:
            port = port_conflict.group(1)
            return (
                f"Port {port} is already in use on your machine.\n"
                "Stop the service using that port or change the mapping in docker-compose.yml."
            )

        external_net_missing = re.search(
            r"network\s+([a-zA-Z0-9_.-]+)\s+declared as external,\s+but could not be found",
            merged,
            flags=re.IGNORECASE,
        )
        if external_net_missing:
            net_name = external_net_missing.group(1)
            return (
                f"External Docker network '{net_name}' was not found.\n"
                "Create it first (docker network create ...) or let BeatRooter auto-create it on Start."
            )

        lines = [line.strip() for line in merged.splitlines() if line.strip()]
        error_lines = []
        for line in lines:
            lowered = line.lower()
            if any(token in lowered for token in ("error", "failed", "denied", "not found", "cannot", "invalid")):
                error_lines.append(line)

        if error_lines:
            return "\n".join(error_lines[-6:])
        return "\n".join(lines[-6:])

    def _run_compose_up(self, compose_path: str):
        created_networks = []
        try:
            created_networks = self._ensure_external_networks(compose_path)

            command = ["docker", "compose", "-f", compose_path, "up", "-d", "--quiet-pull"]
            result = subprocess.run(
                command,
                cwd=self.current_folder_path,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )

            if result.returncode != 0 and "unknown flag" in (result.stderr or "").lower():
                result = subprocess.run(
                    ["docker", "compose", "-f", compose_path, "up", "-d"],
                    cwd=self.current_folder_path,
                    capture_output=True,
                    text=True,
                    timeout=900,
                    check=False,
                )

            if result.returncode != 0:
                missing_external = self._extract_missing_external_network(result.stderr, result.stdout)
                if missing_external:
                    created_ok, create_error = self._create_network_if_missing(missing_external)
                    if created_ok:
                        result = subprocess.run(
                            ["docker", "compose", "-f", compose_path, "up", "-d"],
                            cwd=self.current_folder_path,
                            capture_output=True,
                            text=True,
                            timeout=900,
                            check=False,
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Docker Network Error",
                            f"Could not auto-create network '{missing_external}'.\n{create_error}",
                        )
                        self._refresh_containers_panel()
                        return False, f"Could not auto-create network '{missing_external}'.\n{create_error}", created_networks

            if result.returncode != 0:
                message = self._format_docker_error(result.stderr, result.stdout)
                return False, message, created_networks
            return True, "", created_networks
        except subprocess.TimeoutExpired:
            return False, "Starting containers is taking too long. Pull images manually in terminal and retry.", created_networks
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            return False, str(exc), created_networks

    def start_detected_containers(self):
        compose_path = self._detect_compose_file()
        if not compose_path:
            QMessageBox.information(self, "Containers", "No compose file detected in this project.")
            return

        success, message, created_networks = self._run_compose_up(compose_path)
        if not success:
            QMessageBox.warning(self, "Docker Error", message)
        elif created_networks:
            QMessageBox.information(
                self,
                "Docker Networks",
                "Created missing external networks: " + ", ".join(created_networks),
            )
        self._refresh_containers_panel()

    def start_all_detected_containers(self):
        if not self.detected_compose_files:
            QMessageBox.information(self, "Containers", "No compose files detected in this project.")
            return

        failures = []
        all_created_networks = []
        started_count = 0
        for compose_path in self.detected_compose_files:
            success, message, created_networks = self._run_compose_up(compose_path)
            all_created_networks.extend(created_networks)
            if not success:
                rel_path = os.path.relpath(compose_path, self.current_folder_path)
                failures.append(f"{rel_path}: {message}")
            else:
                started_count += 1

        self._refresh_containers_panel()

        if failures:
            summary = [
                f"Started {started_count}/{len(self.detected_compose_files)} compose files.",
                "",
                "Failures:",
                "\n\n".join(failures[:4]),
            ]
            if len(failures) > 4:
                summary.append(f"\n...and {len(failures) - 4} more.")
            QMessageBox.warning(self, "Docker Start All", "\n".join(summary))
            return

        summary = f"Started {len(self.detected_compose_files)} compose files."
        if all_created_networks:
            unique_created = sorted(set(all_created_networks))
            summary += "\nCreated networks: " + ", ".join(unique_created)
        QMessageBox.information(self, "Docker Start All", summary)

    def stop_detected_containers(self):
        compose_path = self._detect_compose_file()
        if not compose_path:
            QMessageBox.information(self, "Containers", "No compose file detected in this project.")
            return
        try:
            result = subprocess.run(
                ["docker", "compose", "-f", compose_path, "down"],
                cwd=self.current_folder_path,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if result.returncode != 0:
                message = self._format_docker_error(result.stderr, result.stdout)
                QMessageBox.warning(self, "Docker Error", message)
            self._refresh_containers_panel()
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            QMessageBox.warning(self, "Docker Error", str(exc))

    def _open_docker_tool(self):
        parent_window = self.window()
        if hasattr(parent_window, "show_docker_automation"):
            parent_window.show_docker_automation()
            return
        QMessageBox.information(self, "Docker Tool", "Docker automation tool is not available in this context.")

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QFrame#WebExplorerPanel, QFrame#WebAttackPanel {
                background-color: #0f1622;
                border: 1px solid #273347;
            }
            QFrame#WebActivityBar {
                background-color: #0b111a;
                border-right: 1px solid #273347;
            }
            QFrame#WebEditorPanel {
                background-color: #0b111a;
                border-top: 1px solid #273347;
                border-bottom: 1px solid #273347;
            }
            QPushButton#ActivityBarButton {
                background-color: #0f1622;
                color: #8ea1bf;
                border: 1px solid #24354b;
                border-radius: 3px;
                font-weight: 700;
            }
            QPushButton#ActivityBarButton:hover {
                background-color: #18273d;
                color: #dce6f7;
            }
            QPushButton#ActivityBarButton:checked {
                background-color: #203450;
                color: #e7f0ff;
                border: 1px solid #4b6c96;
            }
            QLabel#WebSectionTitle {
                color: #d5deec;
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 1px;
            }
            QLabel#WebFolderLabel {
                color: #7f8ea5;
                font-size: 10px;
                padding: 2px 0px;
            }
            QLabel#WebCurrentFileLabel {
                color: #9fb0c8;
                font-size: 10px;
                padding: 2px 4px;
                border: 1px solid #273347;
                border-radius: 2px;
                background-color: #101827;
            }
            QTreeView#WebFileTree {
                background-color: #0b111a;
                border: 1px solid #273347;
                color: #aeb9cd;
                padding: 2px;
                alternate-background-color: #0e1725;
            }
            QLabel#WebExplorerEmptyState {
                color: #7f8ea5;
                border: 1px dashed #273347;
                background-color: #0b111a;
                padding: 16px;
            }
            QListWidget#WebSearchResults, QListWidget#WebContainersList {
                background-color: #0b111a;
                border: 1px solid #273347;
                color: #b7c4d8;
            }
            QComboBox#WebComposeSelector {
                background-color: #131d2d;
                color: #ced8e8;
                border: 1px solid #26364c;
                border-radius: 2px;
                padding: 4px 6px;
            }
            QListWidget#WebSearchResults::item:selected, QListWidget#WebContainersList::item:selected {
                background-color: #1e3550;
                color: #e6efff;
            }
            QTreeView#WebFileTree::item:selected {
                background-color: #1e3550;
                color: #e6efff;
            }
            QPlainTextEdit#WebCodeEditor {
                background-color: #0a0f17;
                color: #d5deec;
                border: 1px solid #273347;
                selection-background-color: #355a82;
            }
            QPushButton#WebOpenFolderButton, QPushButton#WebSaveButton {
                background-color: #182235;
                color: #95a6c0;
                border: 1px solid #2a3950;
                border-radius: 3px;
                padding: 3px 10px;
            }
            QPushButton#WebAttackButton {
                background-color: #203450;
                color: #dce6f7;
                border: 1px solid #38506f;
                border-radius: 3px;
                padding: 5px 10px;
                font-weight: 600;
            }
            QPushButton#WebOpenFolderButton:hover, QPushButton#WebSaveButton:hover {
                background-color: #22304a;
                border: 1px solid #3f5777;
                color: #e3ecfb;
            }
            QPushButton#WebAttackButton:hover {
                background-color: #2a4567;
                border: 1px solid #4b6c96;
            }
            QLabel#WebDevBadge {
                color: #fbbf24;
                border: 1px solid #6b4f1d;
                border-radius: 3px;
                background-color: #2c210e;
                font-size: 10px;
                font-weight: 600;
                padding: 4px 8px;
                max-width: 160px;
            }
            QLabel#WebAttackBody {
                color: #9fb0c8;
                line-height: 1.4;
                padding: 6px 2px;
            }
            QLabel#WebAttackHint {
                color: #7f8ea5;
                padding: 4px 2px;
            }
            """
        )

    def open_project_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Open Project Folder",
            self.current_folder_path or QDir.homePath(),
            QFileDialog.Option.ShowDirsOnly,
        )
        if folder_path:
            self.load_project_folder(folder_path)
            return folder_path
        return ""

    def load_project_folder(self, folder_path: str):
        if not folder_path or not os.path.isdir(folder_path):
            raise ValueError("Invalid project folder")

        self.current_folder_path = folder_path
        root_index = self.file_model.setRootPath(folder_path)
        self.file_tree.setRootIndex(root_index)
        self.folder_label.setText(folder_path)
        self.explorer_stack.setCurrentIndex(1)
        self.clear_editor()
        self._refresh_attack_context()
        self._refresh_containers_panel()
        self.folder_loaded.emit(folder_path)

    def clear_editor(self):
        self.current_file_path = ""
        self.current_file_label.setText("No file opened")
        self.code_editor.setReadOnly(True)
        self.code_editor.setPlainText(
            "Open a project folder on the left and click a file to edit it."
        )
        self.code_editor.document().setModified(False)
        self.save_file_button.setEnabled(False)

    def reset_workspace(self):
        self.current_folder_path = ""
        self.detected_compose_files = []
        self.explorer_stack.setCurrentIndex(0)
        self.folder_label.setText("No folder selected")
        self.containers_list.clear()
        self.compose_selector.clear()
        self.compose_selector.setEnabled(False)
        self.compose_status_label.setText("No docker-compose file detected.")
        self.frontend_url_label.setText("Frontend URL detected: -")
        self.api_url_label.setText("API URL detected: -")
        self.start_containers_button.setEnabled(False)
        self.start_all_containers_button.setEnabled(False)
        self.stop_containers_button.setEnabled(False)
        self.clear_editor()
        self._refresh_attack_context()

    def _on_tree_double_click(self, index):
        if not index.isValid():
            return
        path = self.file_model.filePath(index)
        if os.path.isdir(path):
            return
        self.open_file(path)

    def open_file(self, file_path: str):
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "File Error", "Selected item is not a valid file.")
            return

        try:
            with open(file_path, "rb") as handle:
                raw = handle.read()
            if self._is_binary(raw):
                QMessageBox.information(
                    self,
                    "Unsupported File",
                    "Binary files are not previewed in the editor yet.",
                )
                return

            content = raw.decode("utf-8", errors="replace")
            self.code_editor.setReadOnly(False)
            self.code_editor.setPlainText(content)
            self.code_editor.document().setModified(False)
            self.current_file_path = file_path
            self.current_file_label.setText(self._format_file_label(file_path))
            self.save_file_button.setEnabled(True)
            self.file_opened.emit(file_path)

        except OSError as exc:
            QMessageBox.critical(self, "Open File Error", f"Could not open file:\n{exc}")

    def save_current_file(self):
        if not self.current_file_path:
            return

        try:
            with open(self.current_file_path, "w", encoding="utf-8") as handle:
                handle.write(self.code_editor.toPlainText())
            self.code_editor.document().setModified(False)
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{exc}")

    def has_unsaved_changes(self) -> bool:
        return bool(self.current_file_path and self.code_editor.document().isModified())

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
        editor_font = self.code_editor.font()
        editor_font.setPointSize(self.current_editor_font_size)
        self.code_editor.setFont(editor_font)

    def _format_file_label(self, file_path: str) -> str:
        if self.current_folder_path:
            try:
                relative = os.path.relpath(file_path, self.current_folder_path)
                return relative
            except ValueError:
                pass
        return os.path.basename(file_path)

    @staticmethod
    def _is_binary(raw_content: bytes) -> bool:
        if not raw_content:
            return False
        if b"\x00" in raw_content:
            return True
        sample = raw_content[:1024]
        non_text_bytes = sum(byte < 9 or (13 < byte < 32) for byte in sample)
        return (non_text_bytes / len(sample)) > 0.3 if sample else False
