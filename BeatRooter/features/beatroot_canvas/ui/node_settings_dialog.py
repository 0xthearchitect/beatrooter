import json

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from features.beatroot_canvas.core import NodeFactory


class NodeSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Node Settings")
        self.setMinimumSize(950, 720)
        self.resize(1000, 780)
        self.setMaximumSize(1100, 860)
        self.core_field_checks = {}
        self.core_fields_all_checkbox = None
        self._syncing_core_field_toggle = False
        self._node_type_options = []
        self._added_field_rows = []
        self._changes_applied = False
        self._build_ui()
        self._load_core_field_settings()
        self._load_node_type_options()
        self._load_current_override()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        info = QLabel(
            "Disable core defaults and customize node templates (predefined and custom) with field_name + content (text only).\n"
            "Changes affect new nodes and are saved with the investigation file."
        )
        info.setStyleSheet("color: #8aa0bf;")
        info.setWordWrap(True)
        root.addWidget(info)

        core_group = QGroupBox("Core Default Fields")
        core_layout = QGridLayout(core_group)
        core_layout.setContentsMargins(10, 14, 10, 10)
        core_layout.setHorizontalSpacing(12)
        core_layout.setVerticalSpacing(6)

        self.core_fields_all_checkbox = QCheckBox("All")
        self.core_fields_all_checkbox.setTristate(True)
        self.core_fields_all_checkbox.stateChanged.connect(self._on_core_fields_all_changed)
        core_layout.addWidget(self.core_fields_all_checkbox, 0, 0, 1, 2)

        for index, field_name in enumerate(NodeFactory.get_core_field_schema().keys()):
            checkbox = QCheckBox(field_name.replace("_", " ").title())
            checkbox.stateChanged.connect(self._sync_core_fields_all_checkbox)
            row = (index // 2) + 1
            col = index % 2
            core_layout.addWidget(checkbox, row, col)
            self.core_field_checks[field_name] = checkbox

        root.addWidget(core_group)

        override_group = QGroupBox("Node Template Override")
        override_layout = QFormLayout(override_group)
        override_layout.setContentsMargins(10, 14, 10, 10)
        override_layout.setSpacing(8)
        override_layout.setLabelAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        override_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        override_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        node_selector = QWidget()
        node_selector_layout = QVBoxLayout(node_selector)
        node_selector_layout.setContentsMargins(0, 0, 0, 0)
        node_selector_layout.setSpacing(6)

        self.node_category_combo = QComboBox()
        self.node_category_combo.currentIndexChanged.connect(self._filter_node_type_options)

        self.node_type_search = QLineEdit()
        self.node_type_search.setPlaceholderText("Search node type...")
        self.node_type_search.textChanged.connect(self._filter_node_type_options)
        node_selector_layout.addWidget(self.node_type_search)

        self.node_type_combo = QComboBox()
        self.node_type_combo.setMaxVisibleItems(18)
        self.node_type_combo.currentIndexChanged.connect(self._load_current_override)
        node_selector_layout.addWidget(self.node_type_combo)
        override_layout.addRow("Category:", self.node_category_combo)
        override_layout.addRow("Node Type:", node_selector)

        self.add_field_btn = QPushButton("+ Add Field")
        self.add_field_btn.clicked.connect(lambda: self._add_added_field_row())

        self.added_fields_container = QWidget()
        self.added_fields_layout = QVBoxLayout(self.added_fields_container)
        self.added_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.added_fields_layout.setSpacing(6)
        self.added_fields_layout.addStretch()

        self.added_fields_scroll = QScrollArea()
        self.added_fields_scroll.setWidgetResizable(True)
        self.added_fields_scroll.setMinimumHeight(150)
        self.added_fields_scroll.setMaximumHeight(200)
        self.added_fields_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.added_fields_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.added_fields_scroll.setFrameShape(QFrame.Shape.StyledPanel)
        self.added_fields_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.added_fields_scroll.setStyleSheet(
            "QScrollArea { background-color: #0c1a31; border: 1px solid #1c2e4a; }"
            "QScrollArea > QWidget > QWidget { background-color: #0c1a31; }"
        )
        self.added_fields_scroll.setWidget(self.added_fields_container)

        self.no_added_fields_label = QLabel("No added fields yet. Click '+ Add Field'.")
        self.no_added_fields_label.setStyleSheet("color: #7f8ea5;")

        added_block = QWidget()
        added_block_layout = QVBoxLayout(added_block)
        added_block_layout.setContentsMargins(0, 0, 0, 0)
        added_block_layout.setSpacing(6)
        added_block_layout.addWidget(self.add_field_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        added_block_layout.addWidget(self.no_added_fields_label)
        added_block_layout.addWidget(self.added_fields_scroll)
        added_block.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        override_layout.addRow("Added / Overridden Fields:", added_block)

        self.removed_fields_list = QListWidget()
        self.removed_fields_list.setMinimumHeight(130)
        self.removed_fields_list.setMaximumHeight(210)
        self.removed_fields_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.removed_fields_list.setUniformItemSizes(True)
        self.removed_fields_list.setStyleSheet(
            "QListWidget { background-color: #111b2b; border: 1px solid #26364c; }"
            "QListWidget::item { padding: 2px 4px; }"
        )
        override_layout.addRow("Removed Fields:", self.removed_fields_list)

        action_row = QHBoxLayout()
        self.apply_override_btn = QPushButton("Apply Override")
        self.clear_override_btn = QPushButton("Clear Override")
        self.reset_defaults_btn = QPushButton("Reset All Defaults")
        action_row.addWidget(self.apply_override_btn)
        action_row.addWidget(self.clear_override_btn)
        action_row.addStretch()
        action_row.addWidget(self.reset_defaults_btn)
        override_layout.addRow(action_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #7f8ea5;")
        override_layout.addRow("Status:", self.status_label)

        root.addWidget(override_group)

        self.apply_override_btn.clicked.connect(self._apply_current_override_with_feedback)
        self.clear_override_btn.clicked.connect(self._clear_current_override)
        self.reset_defaults_btn.clicked.connect(self._reset_defaults)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_with_validation)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        QTimer.singleShot(0, self._update_adaptive_heights)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_adaptive_heights()

    def _update_adaptive_heights(self):
        height = max(1, self.height())
        # Keep sections stable and avoid overlap across DPI/scales.
        available = max(380, height - 360)
        shared = int(available * 0.42)
        added_height = max(120, min(210, shared))
        removed_height = max(130, min(210, shared))

        self.added_fields_scroll.setMinimumHeight(added_height)
        self.added_fields_scroll.setMaximumHeight(added_height)
        self.removed_fields_list.setMinimumHeight(removed_height)
        self.removed_fields_list.setMaximumHeight(removed_height)

    def _load_core_field_settings(self):
        settings = NodeFactory.get_core_field_settings()
        for field_name, checkbox in self.core_field_checks.items():
            checkbox.setChecked(bool(settings.get(field_name, True)))
        self._sync_core_fields_all_checkbox()

    def _on_core_fields_all_changed(self, state):
        if self._syncing_core_field_toggle:
            return

        if state == Qt.CheckState.PartiallyChecked.value:
            return

        checked = state == Qt.CheckState.Checked.value
        self._syncing_core_field_toggle = True
        try:
            for checkbox in self.core_field_checks.values():
                checkbox.setChecked(checked)
        finally:
            self._syncing_core_field_toggle = False

        self._sync_core_fields_all_checkbox()

    def _sync_core_fields_all_checkbox(self):
        if not self.core_fields_all_checkbox:
            return

        total = len(self.core_field_checks)
        checked_count = sum(1 for checkbox in self.core_field_checks.values() if checkbox.isChecked())

        self._syncing_core_field_toggle = True
        try:
            if checked_count == 0:
                self.core_fields_all_checkbox.setCheckState(Qt.CheckState.Unchecked)
            elif checked_count == total:
                self.core_fields_all_checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                self.core_fields_all_checkbox.setCheckState(Qt.CheckState.PartiallyChecked)
        finally:
            self._syncing_core_field_toggle = False

    def _load_node_type_options(self):
        self._node_type_options = []
        predefined_types = NodeFactory.list_predefined_node_types()
        custom_types = NodeFactory.list_custom_node_types()

        for node_type in predefined_types:
            category_key = NodeFactory.find_node_category(node_type)
            self._node_type_options.append(
                {
                    "node_type": node_type,
                    "name": NodeFactory.get_node_name(node_type),
                    "category_key": category_key,
                    "category_name": NodeFactory.get_category_display_name(category_key),
                    "kind": "Predefined",
                }
            )

        for node_type in custom_types:
            category_key = NodeFactory.find_node_category(node_type)
            self._node_type_options.append(
                {
                    "node_type": node_type,
                    "name": NodeFactory.get_node_name(node_type),
                    "category_key": category_key,
                    "category_name": NodeFactory.get_category_display_name(category_key),
                    "kind": "Custom",
                }
            )

        self._node_type_options.sort(key=lambda item: (item["kind"], item["category_name"].lower(), item["name"].lower()))
        self._reload_category_options()
        self._filter_node_type_options()

    def _reload_category_options(self):
        selected_category = self.node_category_combo.currentData() if self.node_category_combo.count() else "__all__"
        self.node_category_combo.blockSignals(True)
        self.node_category_combo.clear()

        total = len(self._node_type_options)
        self.node_category_combo.addItem(f"All Categories ({total})", "__all__")

        buckets = {}
        for option in self._node_type_options:
            category_key = option["category_key"] or "general"
            buckets.setdefault(category_key, {"name": option["category_name"], "count": 0})
            buckets[category_key]["count"] += 1

        for category_key, payload in sorted(buckets.items(), key=lambda item: item[1]["name"].lower()):
            label = f"{payload['name']} ({payload['count']})"
            self.node_category_combo.addItem(label, category_key)

        selected_index = self.node_category_combo.findData(selected_category)
        self.node_category_combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        self.node_category_combo.blockSignals(False)

    def _filter_node_type_options(self):
        search = self.node_type_search.text().strip().lower()
        selected_category = self.node_category_combo.currentData()
        selected_node_type = self._selected_node_type()

        self.node_type_combo.blockSignals(True)
        self.node_type_combo.clear()
        for option in self._node_type_options:
            node_type = option["node_type"]
            category_key = option["category_key"] or "general"
            if selected_category and selected_category != "__all__" and category_key != selected_category:
                continue
            display = f"[{option['kind']}] {option['name']} ({node_type})"
            haystack = " ".join([display, option["category_name"], node_type]).lower()
            if search and search not in haystack:
                continue
            self.node_type_combo.addItem(display, node_type)

        if self.node_type_combo.count() == 0:
            self.node_type_combo.addItem("No matching node types", None)

        if selected_node_type:
            found_index = self.node_type_combo.findData(selected_node_type)
            if found_index >= 0:
                self.node_type_combo.setCurrentIndex(found_index)
        self.node_type_combo.blockSignals(False)
        self._load_current_override()

    def _selected_node_type(self):
        return self.node_type_combo.currentData()

    def _load_current_override(self):
        node_type = self._selected_node_type()
        if not node_type:
            self._clear_added_field_rows()
            self.removed_fields_list.clear()
            self.status_label.setText("No node types available.")
            return

        override = NodeFactory.get_node_template_override(node_type)
        added_fields = override.get("added_fields", {})
        removed_fields = override.get("removed_fields", [])

        self._clear_added_field_rows()
        if added_fields:
            for field_name, field_value in added_fields.items():
                self._add_added_field_row(field_name, field_value)

        self._load_removed_fields_list(node_type, removed_fields)
        self._update_added_fields_hint()

        if added_fields or removed_fields:
            self.status_label.setText(f"Loaded override for '{node_type}'.")
        else:
            self.status_label.setText(f"No override configured for '{node_type}'.")

    def _template_field_keys(self, node_type: str) -> list:
        core_settings = NodeFactory.get_core_field_settings()
        keys = [field_name for field_name in NodeFactory.get_core_field_schema() if core_settings.get(field_name, True)]

        template = NodeFactory._resolve_template(node_type)
        if template:
            keys.extend(template.get("default_data", {}).keys())

        normalized = []
        for key in keys:
            clean_key = NodeFactory._sanitize_node_type(key)
            if clean_key and clean_key != "notes" and clean_key not in normalized:
                normalized.append(clean_key)
        return sorted(normalized)

    def _load_removed_fields_list(self, node_type: str, removed_fields: list):
        removed_set = set(removed_fields if isinstance(removed_fields, list) else [])
        self.removed_fields_list.clear()
        for field_name in self._template_field_keys(node_type):
            item = QListWidgetItem(field_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            state = Qt.CheckState.Checked if field_name in removed_set else Qt.CheckState.Unchecked
            item.setCheckState(state)
            self.removed_fields_list.addItem(item)

    def _clear_added_field_rows(self):
        for row in self._added_field_rows:
            self.added_fields_layout.removeWidget(row["widget"])
            row["widget"].setParent(None)
            row["widget"].deleteLater()
        self._added_field_rows = []

    def _add_added_field_row(self, key: str = "", value=None):
        row_widget = QFrame()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        key_edit = QLineEdit()
        key_edit.setPlaceholderText("field_name")
        key_edit.setText("" if key is None else str(key))

        value_edit = QLineEdit()
        value_edit.setPlaceholderText("content (text)")
        if value is not None:
            if isinstance(value, (dict, list)):
                value_edit.setText(json.dumps(value, ensure_ascii=False))
            else:
                value_edit.setText(str(value))

        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(72)
        remove_btn.clicked.connect(lambda: self._remove_added_field_row(row_widget))

        row_layout.addWidget(key_edit, 1)
        row_layout.addWidget(value_edit, 2)
        row_layout.addWidget(remove_btn)
        insert_index = max(0, self.added_fields_layout.count() - 1)
        self.added_fields_layout.insertWidget(insert_index, row_widget)
        self._added_field_rows.append(
            {
                "widget": row_widget,
                "key_edit": key_edit,
                "value_edit": value_edit,
            }
        )
        self._update_added_fields_hint()

    def _remove_added_field_row(self, row_widget: QWidget):
        self._added_field_rows = [row for row in self._added_field_rows if row["widget"] != row_widget]
        self.added_fields_layout.removeWidget(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()
        self._update_added_fields_hint()

    def _update_added_fields_hint(self):
        self.no_added_fields_label.setVisible(len(self._added_field_rows) == 0)

    def _parse_added_fields(self):
        parsed = {}
        for row in self._added_field_rows:
            key_raw = row["key_edit"].text().strip()
            value_raw = row["value_edit"].text()
            if not key_raw and not value_raw.strip():
                continue
            if not key_raw:
                raise ValueError("Each added field must have a field name.")

            clean_key = NodeFactory._sanitize_node_type(key_raw)
            if not clean_key or clean_key == "notes":
                raise ValueError(f"Invalid field name: '{key_raw}'")

            parsed[clean_key] = value_raw
        return parsed

    def _parse_removed_fields(self):
        removed = []
        for index in range(self.removed_fields_list.count()):
            item = self.removed_fields_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                removed.append(item.text())
        return removed

    def _apply_current_override(self, show_feedback: bool = False) -> bool:
        node_type = self._selected_node_type()
        if not node_type:
            return True

        try:
            added_fields = self._parse_added_fields()
            removed_fields = self._parse_removed_fields()
            NodeFactory.set_node_template_override(node_type, added_fields, removed_fields)
        except ValueError as exc:
            QMessageBox.warning(self, "Node Settings", str(exc))
            return False

        if show_feedback:
            self.status_label.setText(f"Override saved for '{node_type}'.")
        return True

    def _apply_current_override_with_feedback(self):
        core_settings = {field_name: checkbox.isChecked() for field_name, checkbox in self.core_field_checks.items()}
        NodeFactory.set_core_field_settings(core_settings)
        if self._apply_current_override(show_feedback=True):
            self._changes_applied = True
            self._load_current_override()

    def _clear_current_override(self):
        node_type = self._selected_node_type()
        if not node_type:
            return
        NodeFactory.clear_node_template_override(node_type)
        self._changes_applied = True
        self._load_current_override()
        self.status_label.setText(f"Override cleared for '{node_type}'.")

    def _reset_defaults(self):
        NodeFactory.reset_node_template_settings()
        self._changes_applied = True
        self._load_core_field_settings()
        self._load_current_override()
        self.status_label.setText("All node settings reset to defaults.")

    def _accept_with_validation(self):
        core_settings = {field_name: checkbox.isChecked() for field_name, checkbox in self.core_field_checks.items()}
        NodeFactory.set_core_field_settings(core_settings)

        if not self._apply_current_override(show_feedback=False):
            return

        self._changes_applied = True
        self.accept()

    def did_apply_changes(self) -> bool:
        return self._changes_applied
