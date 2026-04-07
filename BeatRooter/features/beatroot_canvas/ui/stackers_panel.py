from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QColorDialog,
    QListWidget,
    QListWidgetItem,
    QGridLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QColor, QPixmap


class StackersPanel(QWidget):
    create_requested = pyqtSignal()
    edit_selected_requested = pyqtSignal()
    delete_selected_requested = pyqtSignal()
    stacker_selected = pyqtSignal(str)
    layer_action_requested = pyqtSignal(str, str)

    COLOR_PRESETS = [
        ("Sky Blue", "#5DADE2"),
        ("Mint Green", "#58D68D"),
        ("Amber", "#F5B041"),
        ("Lavender", "#AF7AC5"),
        ("Coral", "#EC7063"),
        ("Slate Blue", "#7FB3D5"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("Stackers")
        title.setObjectName("StackersTitle")
        layout.addWidget(title)

        hint = QLabel("Create para desenhar uma area no canvas.\nDepois escolhes o nome e a cor.")
        hint.setWordWrap(True)
        hint.setObjectName("StackersHint")
        layout.addWidget(hint)

        self.create_btn = QPushButton("Create Stacker")
        self.create_btn.setCheckable(True)
        self.create_btn.clicked.connect(self.create_requested.emit)
        layout.addWidget(self.create_btn)

        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_selected_requested.emit)
        layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected_requested.emit)
        layout.addWidget(self.delete_btn)

        list_title = QLabel("Created Stackers / Layers")
        list_title.setObjectName("StackersListTitle")
        layout.addWidget(list_title)

        self.stackers_list = QListWidget()
        self.stackers_list.setObjectName("StackersList")
        self.stackers_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.stackers_list, 1)

        layer_actions = QGridLayout()
        layer_actions.setContentsMargins(0, 0, 0, 0)
        layer_actions.setHorizontalSpacing(6)
        layer_actions.setVerticalSpacing(6)

        self.to_front_btn = QPushButton("Bring To Front")
        self.to_front_btn.clicked.connect(lambda: self._emit_layer_action("to_front"))
        layer_actions.addWidget(self.to_front_btn, 0, 0)

        self.forward_btn = QPushButton("Layer Up")
        self.forward_btn.clicked.connect(lambda: self._emit_layer_action("forward"))
        layer_actions.addWidget(self.forward_btn, 0, 1)

        self.backward_btn = QPushButton("Layer Down")
        self.backward_btn.clicked.connect(lambda: self._emit_layer_action("backward"))
        layer_actions.addWidget(self.backward_btn, 1, 0)

        self.to_back_btn = QPushButton("Send To Back")
        self.to_back_btn.clicked.connect(lambda: self._emit_layer_action("to_back"))
        layer_actions.addWidget(self.to_back_btn, 1, 1)

        layout.addLayout(layer_actions)

    def set_selection_mode(self, active: bool):
        self.create_btn.setText("Cancel Stacker" if active else "Create Stacker")
        self.create_btn.setChecked(active)

    def set_stackers(self, entries, selected_id: str = ""):
        selected_id = str(selected_id or "")
        self.stackers_list.blockSignals(True)
        self.stackers_list.clear()

        if not entries:
            placeholder = QListWidgetItem("No stackers created")
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.stackers_list.addItem(placeholder)
            self.stackers_list.blockSignals(False)
            return

        max_layer = max(int(entry.get("layer", 0)) for entry in entries)
        selected_row = -1

        for row, entry in enumerate(entries):
            stacker_id = str(entry.get("id", ""))
            name = str(entry.get("name", "Stacker")).strip() or "Stacker"
            layer = int(entry.get("layer", 0))

            if layer == max_layer:
                layer_label = f"Layer {layer + 1} (Front)"
            elif layer == 0:
                layer_label = "Layer 1 (Back)"
            else:
                layer_label = f"Layer {layer + 1}"

            item = QListWidgetItem(f"{name}  -  {layer_label}")
            item.setData(Qt.ItemDataRole.UserRole, stacker_id)
            self.stackers_list.addItem(item)

            if stacker_id == selected_id:
                selected_row = row

        if selected_row >= 0:
            self.stackers_list.setCurrentRow(selected_row)

        self.stackers_list.blockSignals(False)

    def set_selected_stacker(self, stacker_id: str):
        stacker_id = str(stacker_id or "")
        self.stackers_list.blockSignals(True)
        if not stacker_id:
            self.stackers_list.clearSelection()
            self.stackers_list.blockSignals(False)
            return

        for index in range(self.stackers_list.count()):
            item = self.stackers_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole) or "") == stacker_id:
                self.stackers_list.setCurrentItem(item)
                self.stackers_list.blockSignals(False)
                return
        self.stackers_list.blockSignals(False)

    def _on_selection_changed(self):
        item = self.stackers_list.currentItem()
        if not item:
            return
        stacker_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if stacker_id:
            self.stacker_selected.emit(stacker_id)

    def _emit_layer_action(self, action: str):
        item = self.stackers_list.currentItem()
        if not item:
            return
        stacker_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        if stacker_id:
            self.layer_action_requested.emit(stacker_id, action)


class StackerDetailsDialog(QDialog):
    def __init__(self, parent=None, default_name: str = "New Stacker", default_color: str = "#5DADE2"):
        super().__init__(parent)
        self._selected_color = default_color.upper()
        self._setup_ui(default_name)

    def _setup_ui(self, default_name: str):
        self.setWindowTitle("New Stacker")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        name_label = QLabel("Name")
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Azure Cloud")
        self.name_input.setText(default_name)
        self.name_input.selectAll()
        layout.addWidget(self.name_input)

        color_label = QLabel("Color")
        layout.addWidget(color_label)

        color_row = QHBoxLayout()
        color_row.setContentsMargins(0, 0, 0, 0)
        color_row.setSpacing(6)

        self.color_button = QPushButton()
        self.color_button.clicked.connect(self._pick_custom_color)
        color_row.addWidget(self.color_button, 1)

        layout.addLayout(color_row)
        self._refresh_color_button()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add_color_option(self, label: str, color_hex: str):
        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor(color_hex))
        icon = QIcon(pixmap)
        return icon, f"{label} ({color_hex})", color_hex

    def _pick_custom_color(self):
        current_hex = self._selected_color or "#7FB3D5"
        selected = QColorDialog.getColor(QColor(current_hex), self, "Pick Stacker Color")
        if not selected.isValid():
            return

        self._selected_color = selected.name().upper()
        self._refresh_color_button()

    def _refresh_color_button(self):
        label = next(
            (name for name, hex_color in StackersPanel.COLOR_PRESETS if hex_color == self._selected_color),
            "Custom",
        )
        icon, text, _ = self._add_color_option(label, self._selected_color)
        self.color_button.setIcon(icon)
        self.color_button.setText(text)

    def get_payload(self) -> dict:
        return {
            "name": self.name_input.text().strip() or "New Stacker",
            "color": self._selected_color,
        }
