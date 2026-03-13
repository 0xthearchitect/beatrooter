import re

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class CustomNodeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Custom Node")
        self.setMinimumWidth(520)
        self._field_rows = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Example: Threat Scenario")
        form.addRow("Name:", self.name_edit)

        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("Optional. Auto-generated from name.")
        form.addRow("Type Key:", self.type_edit)

        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        color_row.setSpacing(6)
        self.color_edit = QLineEdit("#7cb1ff")
        self.color_btn = QPushButton("Pick")
        self.color_btn.clicked.connect(self.pick_color)
        color_row.addWidget(self.color_edit)
        color_row.addWidget(self.color_btn)
        form.addRow("Color:", color_row)

        self.symbol_edit = QLineEdit()
        self.symbol_edit.setPlaceholderText("Optional. Example: [THRT]")
        form.addRow("Symbol:", self.symbol_edit)

        fields_block = QWidget()
        fields_block_layout = QVBoxLayout(fields_block)
        fields_block_layout.setContentsMargins(0, 0, 0, 0)
        fields_block_layout.setSpacing(6)

        self.add_field_btn = QPushButton("+ Add Field")
        self.add_field_btn.clicked.connect(lambda: self._add_field_row())
        fields_block_layout.addWidget(self.add_field_btn)

        self.fields_container = QWidget()
        self.fields_layout = QVBoxLayout(self.fields_container)
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(6)

        self.fields_scroll = QScrollArea()
        self.fields_scroll.setWidgetResizable(True)
        self.fields_scroll.setMinimumHeight(180)
        self.fields_scroll.setWidget(self.fields_container)
        fields_block_layout.addWidget(self.fields_scroll)

        self._add_field_row()
        form.addRow("Default Fields:", fields_block)

        root.addLayout(form)

        hint = QLabel("Each field has: name + content (text only).")
        hint.setStyleSheet("color: #7f8ea5;")
        root.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def pick_color(self):
        selected = QColorDialog.getColor(QColor(self.color_edit.text()), self, "Pick Node Color")
        if selected.isValid():
            self.color_edit.setText(selected.name())

    def _sanitize_field_key(self, field_key: str) -> str:
        key = re.sub(r"[^a-z0-9_]+", "_", (field_key or "").strip().lower())
        key = re.sub(r"_+", "_", key).strip("_")
        return key

    def _parse_fields(self) -> dict:
        parsed = {}
        for index, row in enumerate(self._field_rows, start=1):
            raw_key = row["key_edit"].text().strip()
            raw_value = row["value_edit"].text()

            if not raw_key and not raw_value.strip():
                continue
            if not raw_key:
                QMessageBox.warning(self, "Invalid Field", f"Field row {index} must include a field name.")
                return None

            clean_key = self._sanitize_field_key(raw_key)
            if not clean_key:
                QMessageBox.warning(self, "Invalid Field", f"Field row {index} has an invalid field name.")
                return None

            parsed[clean_key] = raw_value

        parsed.setdefault("notes", "")
        return parsed

    def _add_field_row(self, key: str = "", value: str = ""):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        key_edit = QLineEdit()
        key_edit.setPlaceholderText("field_name")
        key_edit.setText(key)

        value_edit = QLineEdit()
        value_edit.setPlaceholderText("content (text)")
        value_edit.setText(value)

        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(72)
        remove_btn.clicked.connect(lambda: self._remove_field_row(row_widget))

        row_layout.addWidget(key_edit, 1)
        row_layout.addWidget(value_edit, 2)
        row_layout.addWidget(remove_btn)
        self.fields_layout.addWidget(row_widget)
        self._field_rows.append(
            {
                "widget": row_widget,
                "key_edit": key_edit,
                "value_edit": value_edit,
            }
        )

    def _remove_field_row(self, row_widget: QWidget):
        if len(self._field_rows) <= 1:
            for row in self._field_rows:
                if row["widget"] == row_widget:
                    row["key_edit"].clear()
                    row["value_edit"].clear()
                    return

        self._field_rows = [row for row in self._field_rows if row["widget"] != row_widget]
        self.fields_layout.removeWidget(row_widget)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def get_template_payload(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please provide a node name.")
            return None

        fields = self._parse_fields()
        if fields is None:
            return None

        return {
            "name": name,
            "node_type": self.type_edit.text().strip(),
            "color": self.color_edit.text().strip(),
            "symbol": self.symbol_edit.text().strip(),
            "default_data": fields,
        }
