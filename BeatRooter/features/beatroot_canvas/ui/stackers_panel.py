from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import pyqtSignal, Qt


class StackersPanel(QWidget):
    create_requested = pyqtSignal()
    edit_selected_requested = pyqtSignal()
    delete_selected_requested = pyqtSignal()
    stacker_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("StackersPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 6)
        layout.setSpacing(8)

        title = QLabel("Stackers")
        title.setObjectName("StackersTitle")
        layout.addWidget(title)

        hint = QLabel(
            "Create adiciona um stacker com tamanho base.\n"
            "Depois ele ajusta-se automaticamente aos nodes e stackers linkados."
        )
        hint.setWordWrap(True)
        hint.setObjectName("StackersHint")
        layout.addWidget(hint)

        self.create_btn = QPushButton("Create Stacker")
        self.create_btn.clicked.connect(self.create_requested.emit)
        layout.addWidget(self.create_btn)

        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_selected_requested.emit)
        layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_selected_requested.emit)
        layout.addWidget(self.delete_btn)

        list_title = QLabel("Created Stackers")
        list_title.setObjectName("StackersListTitle")
        layout.addWidget(list_title)

        self.stackers_list = QListWidget()
        self.stackers_list.setObjectName("StackersList")
        self.stackers_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.stackers_list, 1)
        self.setStyleSheet(
            """
            QWidget#StackersPanel {
                background: transparent;
            }
            QLabel#StackersTitle, QLabel#StackersListTitle {
                color: #9f9f9f;
                font-size: 10px;
                font-weight: 600;
            }
            QLabel#StackersHint {
                color: #8e8e8e;
                font-size: 10px;
                line-height: 1.35em;
                padding-bottom: 4px;
            }
            QPushButton {
                background-color: #2b2b2b;
                color: #dddddd;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px 10px;
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #313131;
                border: 1px solid #4a4a4a;
                color: #f5f5f5;
            }
            QListWidget#StackersList {
                background-color: #242424;
                color: #d6d6d6;
                border: 1px solid #343434;
                border-radius: 8px;
                outline: none;
                padding: 4px;
            }
            QListWidget#StackersList::item {
                padding: 8px 10px;
                border-radius: 6px;
                margin: 2px 0px;
            }
            QListWidget#StackersList::item:selected {
                background-color: #343434;
                color: #f2f2f2;
            }
            QListWidget#StackersList::item:hover:!selected {
                background-color: #2d2d2d;
            }
            """
        )

    def set_selection_mode(self, active: bool):
        self.create_btn.setText("Create Stacker")

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

        selected_row = -1

        for row, entry in enumerate(entries):
            stacker_id = str(entry.get("id", ""))
            name = str(entry.get("name", "Stacker")).strip() or "Stacker"
            parent_name = str(entry.get("parent_name", "")).strip()
            subtitle = f"  (inside {parent_name})" if parent_name else ""
            item = QListWidgetItem(f"{name}{subtitle}")
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

class StackerDetailsDialog(QDialog):
    def __init__(self, parent=None, default_name: str = "New Stacker", default_color: str = "#292929"):
        super().__init__(parent)
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_payload(self) -> dict:
        return {
            "name": self.name_input.text().strip() or "New Stacker",
            "color": "#292929",
        }
