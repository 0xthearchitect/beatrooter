from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from features.beatnote.core.beatnote_model import (
    BEATNOTE_CATEGORIES,
    BEATNOTE_CATEGORY_LABELS,
    BEATNOTE_CONTENT_MAX_LENGTH,
    BEATNOTE_TITLE_MAX_LENGTH,
    BeatNote,
    BeatNoteValidationError,
    validate_note_input,
)
from ui.theme import build_disabled_button_qss, build_filled_button_qss, get_app_font


class BeatNoteDialog(QDialog):
    DELETE_RESULT = 2

    def __init__(
        self,
        *,
        note: BeatNote | None = None,
        colors: dict[str, str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.note = note
        self.colors = colors or {}
        self.app_font = get_app_font()
        self._payload: dict[str, Any] | None = None
        self._allow_close = False

        self.setModal(True)
        self.setWindowTitle("Edit BeatNote" if self.note else "Create BeatNote")
        self.setMinimumWidth(640)
        self.setup_ui()
        self._connect_dirty_signals()
        self._populate()
        self._initial_state = self._serialize_state()
        self._update_counters()
        QTimer.singleShot(0, self._focus_title)

    def setup_ui(self) -> None:
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: #16131d;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
            }}
            QLabel {{
                color: {self.colors.get('text_white', '#FFFFFF')};
                font-family: {self.app_font};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: rgba(255, 255, 255, 0.08);
                color: {self.colors.get('text_white', '#FFFFFF')};
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 14px;
                font-family: {self.app_font};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid {self.colors.get('popup_tile', '#2E7D32')};
            }}
            QCheckBox {{
                spacing: 10px;
                font-size: 14px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("BeatNote")
        header.setStyleSheet(
            f"""
            font-size: 22px;
            font-weight: 700;
            color: {self.colors.get('text_white', '#FFFFFF')};
            """
        )
        layout.addWidget(header)

        subtitle = QLabel(
            "Capture the note cleanly, then get back to the investigation."
            if self.note is None
            else "Update the note without losing the flow."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"""
            font-size: 14px;
            color: {self.colors.get('text_light_gray', '#E0E0E0')};
            """
        )
        layout.addWidget(subtitle)

        self.error_label = QLabel("")
        self.error_label.setObjectName("BeatNoteErrorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.error_label.setStyleSheet("color: #ff8a80; font-size: 13px;")
        layout.addWidget(self.error_label)

        title_row = QVBoxLayout()
        title_row.setSpacing(8)
        title_label = QLabel("Title")
        title_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.title_input = QLineEdit()
        self.title_input.setObjectName("BeatNoteTitleInput")
        self.title_input.setPlaceholderText("E.g. tighten kick transient before bounce")
        self.title_counter = QLabel("")
        self.title_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.title_counter.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6);")
        title_row.addWidget(title_label)
        title_row.addWidget(self.title_input)
        title_row.addWidget(self.title_counter)
        layout.addLayout(title_row)

        content_row = QVBoxLayout()
        content_row.setSpacing(8)
        content_label = QLabel("Content")
        content_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.content_input = QTextEdit()
        self.content_input.setObjectName("BeatNoteContentInput")
        self.content_input.setPlaceholderText("Dump the idea, tweak, reference or task here...")
        self.content_input.setMinimumHeight(220)
        self.content_counter = QLabel("")
        self.content_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.content_counter.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.6);")
        content_row.addWidget(content_label)
        content_row.addWidget(self.content_input)
        content_row.addWidget(self.content_counter)
        layout.addLayout(content_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(14)

        category_col = QVBoxLayout()
        category_col.setSpacing(8)
        category_label = QLabel("Category")
        category_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.category_input = QComboBox()
        self.category_input.setObjectName("BeatNoteCategoryInput")
        for category in BEATNOTE_CATEGORIES:
            self.category_input.addItem(BEATNOTE_CATEGORY_LABELS[category], category)
        category_col.addWidget(category_label)
        category_col.addWidget(self.category_input)

        tags_col = QVBoxLayout()
        tags_col.setSpacing(8)
        tags_label = QLabel("Tags")
        tags_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        self.tags_input = QLineEdit()
        self.tags_input.setObjectName("BeatNoteTagsInput")
        self.tags_input.setPlaceholderText("arrangement, bounce, vocal")
        tags_col.addWidget(tags_label)
        tags_col.addWidget(self.tags_input)

        meta_row.addLayout(category_col, 1)
        meta_row.addLayout(tags_col, 1)
        layout.addLayout(meta_row)

        toggle_frame = QFrame()
        toggle_frame.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.04); border-radius: 12px;"
        )
        toggle_layout = QHBoxLayout(toggle_frame)
        toggle_layout.setContentsMargins(14, 12, 14, 12)
        toggle_layout.setSpacing(10)
        self.pinned_input = QCheckBox("Pin this BeatNote")
        self.pinned_input.setObjectName("BeatNotePinnedInput")
        self.pinned_input.setStyleSheet(
            f"""
            color: {self.colors.get('text_white', '#FFFFFF')};
            font-family: {self.app_font};
            """
        )
        toggle_layout.addWidget(self.pinned_input)
        toggle_layout.addStretch()
        layout.addWidget(toggle_frame)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("BeatNoteDeleteButton")
        self.delete_button.setVisible(self.note is not None)
        self.delete_button.setStyleSheet(
            build_disabled_button_qss(
                self.app_font,
                "#5a1d1d",
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=14,
                border="1px solid rgba(255, 255, 255, 0.1)",
                extra_base="padding: 10px 18px;",
            )
        )
        self.delete_button.clicked.connect(self.request_delete)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("BeatNoteCancelButton")
        self.cancel_button.setStyleSheet(
            build_disabled_button_qss(
                self.app_font,
                "rgba(255, 255, 255, 0.08)",
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=14,
                border="1px solid rgba(255, 255, 255, 0.1)",
                extra_base="padding: 10px 18px;",
            )
        )
        self.cancel_button.clicked.connect(self.reject)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("BeatNoteSaveButton")
        self.save_button.setStyleSheet(
            build_filled_button_qss(
                self.app_font,
                self.colors.get("popup_button", "#0E4F1B"),
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=14,
                padding="10px 18px",
            )
        )
        self.save_button.clicked.connect(self.attempt_save)

        buttons.addWidget(self.delete_button)
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.save_shortcut.activated.connect(self.attempt_save)
        self.meta_save_shortcut = QShortcut(QKeySequence("Meta+Return"), self)
        self.meta_save_shortcut.activated.connect(self.attempt_save)

    def _populate(self) -> None:
        if self.note is None:
            self.category_input.setCurrentIndex(0)
            return

        self.title_input.setText(self.note.title)
        self.content_input.setPlainText(self.note.content)
        category_index = self.category_input.findData(self.note.category)
        if category_index >= 0:
            self.category_input.setCurrentIndex(category_index)
        self.tags_input.setText(", ".join(self.note.tags))
        self.pinned_input.setChecked(self.note.pinned)

    def _connect_dirty_signals(self) -> None:
        self.title_input.textChanged.connect(self._update_counters)
        self.content_input.textChanged.connect(self._update_counters)
        self.category_input.currentIndexChanged.connect(self._clear_error)
        self.tags_input.textChanged.connect(self._clear_error)
        self.pinned_input.stateChanged.connect(self._clear_error)

    def _focus_title(self) -> None:
        self.title_input.setFocus()
        self.title_input.selectAll()

    def _serialize_state(self) -> tuple[Any, ...]:
        return (
            self.title_input.text(),
            self.content_input.toPlainText(),
            self.category_input.currentData(),
            self.tags_input.text(),
            self.pinned_input.isChecked(),
        )

    def has_unsaved_changes(self) -> bool:
        return self._serialize_state() != self._initial_state

    def _clear_error(self, *_args) -> None:
        self.error_label.clear()
        self.error_label.setVisible(False)

    def _update_counters(self) -> None:
        title_length = len(self.title_input.text())
        content_length = len(self.content_input.toPlainText())
        self.title_counter.setText(f"{title_length}/{BEATNOTE_TITLE_MAX_LENGTH}")
        self.content_counter.setText(f"{content_length}/{BEATNOTE_CONTENT_MAX_LENGTH}")
        self._clear_error()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def attempt_save(self) -> None:
        try:
            self._payload = validate_note_input(
                {
                    "title": self.title_input.text(),
                    "content": self.content_input.toPlainText(),
                    "category": self.category_input.currentData(),
                    "tags": self.tags_input.text(),
                    "pinned": self.pinned_input.isChecked(),
                }
            )
        except BeatNoteValidationError as exc:
            self._show_error(str(exc))
            return

        self._allow_close = True
        self.accept()

    def request_delete(self) -> None:
        reply = QMessageBox.question(
            self,
            "Delete BeatNote",
            "Delete this BeatNote? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._allow_close = True
        self.done(self.DELETE_RESULT)

    def get_payload(self) -> dict[str, Any] | None:
        return self._payload

    def _confirm_discard(self) -> bool:
        reply = QMessageBox.question(
            self,
            "Unsaved BeatNote",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def reject(self) -> None:
        if self._allow_close or not self.has_unsaved_changes() or self._confirm_discard():
            self._allow_close = True
            super().reject()
