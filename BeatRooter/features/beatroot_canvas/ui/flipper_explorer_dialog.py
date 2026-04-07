from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QUrl
from PyQt6.QtGui import QDrag, QFileSystemModel
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
)


class FlipperFileTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.flipper_root_path = ""

    def startDrag(self, supported_actions):
        model = self.model()
        if not model:
            return

        selected_indexes = self.selectionModel().selectedRows()
        file_paths = []
        for index in selected_indexes:
            path = model.filePath(index)
            if path and Path(path).is_file():
                file_paths.append(path)

        if not file_paths:
            return

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path) for path in file_paths])
        mime.setData("application/x-beatrooter-flipper-root", self.flipper_root_path.encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class FlipperExplorerDialog(QDialog):
    files_import_requested = pyqtSignal(list, str)

    def __init__(self, root_paths: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Flipper Device Explorer")
        self.setMinimumSize(640, 460)
        self.root_paths = list(root_paths or [])

        self.model = QFileSystemModel(self)
        self.model.setReadOnly(True)

        self._build_ui()
        self._load_roots()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        top_row.addWidget(QLabel("Flipper root:"))

        self.root_combo = QComboBox()
        self.root_combo.currentIndexChanged.connect(self._on_root_changed)
        top_row.addWidget(self.root_combo, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._on_refresh)
        top_row.addWidget(self.refresh_btn)

        root_layout.addLayout(top_row)

        hint_label = QLabel(
            "Arrasta ficheiros para o canvas do BeatRooter ou usa 'Import Selected'."
        )
        hint_label.setStyleSheet("color: #7f8ea5;")
        root_layout.addWidget(hint_label)

        self.file_tree = FlipperFileTreeView()
        self.file_tree.setModel(self.model)
        self.file_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_tree.setDragEnabled(True)
        self.file_tree.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.file_tree.setAlternatingRowColors(True)
        self.file_tree.setHeaderHidden(False)
        self.file_tree.doubleClicked.connect(self._import_current_selection)
        root_layout.addWidget(self.file_tree, 1)

        bottom_row = QHBoxLayout()
        bottom_row.addStretch(1)

        self.import_btn = QPushButton("Import Selected")
        self.import_btn.clicked.connect(self._import_current_selection)
        bottom_row.addWidget(self.import_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        bottom_row.addWidget(self.close_btn)

        root_layout.addLayout(bottom_row)

    def _load_roots(self):
        self.root_combo.blockSignals(True)
        self.root_combo.clear()
        for root_path in self.root_paths:
            self.root_combo.addItem(root_path, root_path)
        self.root_combo.blockSignals(False)

        if self.root_combo.count() > 0:
            self.root_combo.setCurrentIndex(0)
            self._on_root_changed()

    def _on_refresh(self):
        # QFileSystemModel watches filesystem changes, but this forces tree reset.
        self._on_root_changed()

    def _on_root_changed(self):
        root_path = self.root_combo.currentData()
        if not root_path:
            return

        root_path_obj = Path(root_path)
        if not root_path_obj.exists():
            QMessageBox.warning(self, "Flipper Explorer", f"Path no longer exists:\n{root_path}")
            return

        root_index = self.model.setRootPath(root_path)
        self.file_tree.setRootIndex(root_index)
        self.file_tree.flipper_root_path = str(root_path_obj)

        # Hide extra columns from QFileSystemModel.
        for column in (1, 2, 3):
            self.file_tree.hideColumn(column)

    def _selected_files(self) -> list:
        indexes = self.file_tree.selectionModel().selectedRows() if self.file_tree.selectionModel() else []
        files = []
        for index in indexes:
            path = self.model.filePath(index)
            if path and Path(path).is_file():
                files.append(path)
        return files

    def _import_current_selection(self):
        selected_files = self._selected_files()
        if not selected_files:
            return

        root_path = self.root_combo.currentData() or ""
        self.files_import_requested.emit(selected_files, root_path)
