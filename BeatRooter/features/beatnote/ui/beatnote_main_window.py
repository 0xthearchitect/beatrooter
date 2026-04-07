from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStatusBar, QToolBar, QVBoxLayout, QWidget

from features.beatnote.ui.beatnote_panel import BeatNotePanel
from ui.theme import get_welcome_palette
from utils.path_utils import get_resource_path


class BeatNoteMainWindow(QMainWindow):
    _window_refs: list["BeatNoteMainWindow"] = []

    def __init__(self, parent=None, *, on_back_to_welcome=None) -> None:
        super().__init__(parent)
        BeatNoteMainWindow._window_refs.append(self)
        self.colors = get_welcome_palette()
        self.beatnote_panel: BeatNotePanel | None = None
        self.on_back_to_welcome = on_back_to_welcome
        self._welcome_restored = False
        self._setup_ui()
        self._setup_actions()
        self._refresh_status()

    @classmethod
    def launch(cls, parent=None, *, on_back_to_welcome=None) -> "BeatNoteMainWindow":
        for window in list(cls._window_refs):
            if window is None:
                continue
            if window.isVisible():
                if on_back_to_welcome is not None:
                    window.on_back_to_welcome = on_back_to_welcome
                window.raise_()
                window.activateWindow()
                return window

        window = cls(parent=parent, on_back_to_welcome=on_back_to_welcome)
        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def _setup_ui(self) -> None:
        self.setWindowTitle("BeatNote")
        self.setGeometry(140, 120, 1180, 860)
        self.setMinimumSize(980, 720)
        self.setWindowIcon(QIcon(get_resource_path("icons/app_icon.png", "assets")))
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {self.colors['page_bg']};
            }}
            QMenuBar {{
                background-color: rgba(20, 24, 35, 0.96);
                color: {self.colors['text_white']};
                border: none;
                padding: 6px 10px;
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 6px 10px;
                border-radius: 8px;
            }}
            QMenuBar::item:selected {{
                background-color: rgba(255, 255, 255, 0.08);
            }}
            QMenu {{
                background-color: rgba(20, 24, 35, 0.98);
                color: {self.colors['text_white']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 18px;
                border-radius: 8px;
            }}
            QMenu::item:selected {{
                background-color: rgba(46, 125, 50, 0.22);
            }}
            QStatusBar {{
                background-color: rgba(20, 24, 35, 0.96);
                color: rgba(255, 255, 255, 0.75);
                border: none;
            }}
            """
        )

        central_widget = QWidget()
        central_widget.setObjectName("BeatNoteWindowRoot")
        central_widget.setStyleSheet(
            f"""
            QWidget#BeatNoteWindowRoot {{
                background-color: {self.colors['page_bg']};
            }}
            """
        )
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(0)

        self.beatnote_panel = BeatNotePanel(colors=self.colors, parent=self)
        self.beatnote_panel.notes_changed.connect(self._refresh_status)
        self.beatnote_panel.search_input.textChanged.connect(self._refresh_status)
        self.beatnote_panel.category_filter.currentIndexChanged.connect(self._refresh_status)
        self.beatnote_panel.pinned_filter.stateChanged.connect(self._refresh_status)
        layout.addWidget(self.beatnote_panel)

        self.setStatusBar(QStatusBar())

    def _setup_actions(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        edit_menu = menubar.addMenu("Edit")
        tree_menu = menubar.addMenu("Tree")
        search_menu = menubar.addMenu("Search")
        view_menu = menubar.addMenu("View")

        new_note_action = QAction("New BeatNote", self)
        new_note_action.setShortcut(QKeySequence.StandardKey.New)
        new_note_action.triggered.connect(self._open_new_note)
        file_menu.addAction(new_note_action)

        download_json_action = QAction("Download JSON...", self)
        download_json_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        download_json_action.triggered.connect(self._download_json)
        file_menu.addAction(download_json_action)

        exit_action = QAction("Close", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Close)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        duplicate_action = QAction("Duplicate Note", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self._duplicate_current_note)
        edit_menu.addAction(duplicate_action)

        delete_action = QAction("Delete Note", self)
        delete_action.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        delete_action.triggered.connect(self._delete_current_note)
        edit_menu.addAction(delete_action)

        tree_menu.addAction(new_note_action)
        tree_menu.addAction(duplicate_action)
        tree_menu.addSeparator()

        expand_action = QAction("Expand All", self)
        expand_action.triggered.connect(self._expand_tree)
        tree_menu.addAction(expand_action)

        collapse_action = QAction("Collapse All", self)
        collapse_action.triggered.connect(self._collapse_tree)
        tree_menu.addAction(collapse_action)

        pinned_only_action = QAction("Pinned Only", self)
        pinned_only_action.setCheckable(True)
        pinned_only_action.toggled.connect(self._toggle_pinned_only)
        view_menu.addAction(pinned_only_action)

        toolbar = QToolBar("BeatNote")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        toolbar.setStyleSheet(
            """
            QToolBar {
                spacing: 8px;
                padding: 8px 10px;
                border: none;
                background-color: rgba(20, 24, 35, 0.92);
            }
            QToolButton {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 10px;
                padding: 8px 12px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            """
        )
        toolbar.addAction(new_note_action)
        toolbar.addAction(download_json_action)
        toolbar.addAction(duplicate_action)
        toolbar.addAction(delete_action)
        self.addToolBar(toolbar)

    def _open_new_note(self) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.start_new_note()
        self._refresh_status()

    def _duplicate_current_note(self) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.duplicate_current_note()
        self._refresh_status()

    def _delete_current_note(self) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.delete_current_note()
        self._refresh_status()

    def _reload_notes(self) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.reload_notes()
        self._refresh_status()

    def _expand_tree(self) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.expand_all()

    def _collapse_tree(self) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.collapse_all()

    def _focus_search(self) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.focus_search()

    def _toggle_pinned_only(self, enabled: bool) -> None:
        if self.beatnote_panel is None:
            return
        self.beatnote_panel.pinned_filter.setChecked(enabled)

    def _download_json(self) -> None:
        if self.beatnote_panel is None:
            return

        if self.beatnote_panel.has_unsaved_editor_changes():
            if not self.beatnote_panel.save_current_note():
                return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Download BeatNote JSON",
            "beatnote-export.json",
            "JSON Files (*.json)",
        )
        if not filename:
            return
        if not filename.lower().endswith(".json"):
            filename = f"{filename}.json"
        self._write_json_file(filename)

    def _write_json_file(self, filename: str) -> None:
        if self.beatnote_panel is None:
            return
        try:
            payload = self.beatnote_panel.export_notes_payload()
            with open(filename, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", f"Could not export BeatNote JSON: {exc}")
            return

        self.statusBar().showMessage("BeatNote JSON downloaded")
        self._refresh_status()

    def _go_back_to_welcome(self) -> None:
        self.close()

    def _restore_welcome(self) -> None:
        if self._welcome_restored:
            return
        self._welcome_restored = True
        if callable(self.on_back_to_welcome):
            self.on_back_to_welcome()

    def _refresh_status(self, *_args) -> None:
        if self.beatnote_panel is None:
            return

        total = len(self.beatnote_panel.notes)
        shown = len(self.beatnote_panel.filtered_notes)
        pinned = sum(1 for note in self.beatnote_panel.notes if note.pinned)
        self.statusBar().showMessage(
            f"BeatNotes: {shown} shown / {total} total · {pinned} pinned"
        )

    def closeEvent(self, event) -> None:
        try:
            BeatNoteMainWindow._window_refs.remove(self)
        except ValueError:
            pass
        self._restore_welcome()
        super().closeEvent(event)
