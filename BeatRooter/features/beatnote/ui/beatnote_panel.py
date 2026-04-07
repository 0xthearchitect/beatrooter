from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import re
from typing import Any

from PyQt6.QtCore import QModelIndex, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QKeyEvent, QPainter, QPixmap, QTextCharFormat, QTextCursor, QTextOption
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QMenu,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt6.QtSvg import QSvgRenderer
except ImportError:
    QSvgRenderer = None

from features.beatnote.core.beatnote_model import (
    BEATNOTE_CATEGORIES,
    BEATNOTE_ICON_ASSETS,
    BEATNOTE_ICON_LABELS,
    BEATNOTE_ICON_OPTIONS,
    BeatNote,
    category_label,
    filter_beatnotes,
    ordered_categories,
)
from features.beatnote.core.beatnote_service import BeatNoteNotFoundError, BeatNoteService, BeatNoteServiceError
from ui.theme import build_disabled_button_qss, build_filled_button_qss, get_app_font
from utils.path_utils import get_resource_path


NOTE_COLOR_OPTIONS: list[tuple[str, str]] = [
    ("Azure", "#2D8CFF"),
    ("Green", "#2E7D32"),
    ("Purple", "#7E57C2"),
    ("Orange", "#FB8C00"),
    ("Pink", "#D81B60"),
    ("Red", "#C62828"),
    ("Teal", "#00897B"),
    ("Gray", "#607D8B"),
]

DEFAULT_NOTE_ICON = "note"
DEFAULT_NOTE_COLOR = "#2D8CFF"


class BeatNoteContentEdit(QTextEdit):
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Backspace and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if self._remove_empty_list_prefix_on_backspace():
                event.accept()
                return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if self._continue_list_on_enter():
                event.accept()
                return
        super().keyPressEvent(event)

    def _remove_empty_list_prefix_on_backspace(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False

        block = cursor.block()
        text = block.text()
        position = cursor.positionInBlock()

        prefix = None
        for pattern in (r"^(\s*•\s+)$", r"^(\s*\d+\.\s+)$"):
            match = re.match(pattern, text)
            if match:
                prefix = match.group(1)
                break

        if prefix is None or position != len(text):
            return False

        cursor.beginEditBlock()
        for _ in range(len(prefix)):
            cursor.deletePreviousChar()
        cursor.endEditBlock()
        return True

    def _continue_list_on_enter(self) -> bool:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return False

        block = cursor.block()
        text = block.text()

        bullet_match = re.match(r"^(\s*)•\s+(.*)$", text)
        numbered_match = re.match(r"^(\s*)(\d+)\.\s+(.*)$", text)

        if bullet_match:
            prefix = f"{bullet_match.group(1)}• "
        elif numbered_match:
            prefix = f"{numbered_match.group(1)}{int(numbered_match.group(2)) + 1}. "
        else:
            return False

        cursor.beginEditBlock()
        cursor.insertBlock()
        cursor.insertText(prefix, cursor.charFormat())
        cursor.endEditBlock()
        return True


class BeatNoteToast(QFrame):
    def __init__(self, parent, *, app_font: str) -> None:
        super().__init__(parent)
        self.app_font = app_font
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet(
            f"color: #ffffff; font-size: 13px; font-weight: 600; font-family: {self.app_font};"
        )
        layout.addWidget(self.message_label)

    def show_message(self, message: str, *, error: bool = False) -> None:
        accent = "#b3261e" if error else "#0E4F1B"
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {accent};
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            """
        )
        self.message_label.setText(message)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()
        self.hide_timer.start(2600)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 20
        self.adjustSize()
        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.height() - margin)
        self.move(x, y)


class BeatNoteIconPicker(QPushButton):
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, *, app_font: str, icon_provider, parent=None) -> None:
        super().__init__(parent)
        self.app_font = app_font
        self._icon_provider = icon_provider
        self._items: list[tuple[str, str]] = []
        self._current_index = -1
        self.setObjectName("BeatNoteEditorIconPicker")
        self.setFixedSize(60, 60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QPushButton#BeatNoteEditorIconPicker {{
                background-color: rgba(255, 255, 255, 0.045);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
                padding: 0px;
            }}
            QPushButton#BeatNoteEditorIconPicker:hover {{
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }}
            """
        )
        self.clicked.connect(self._open_picker)

    def addItem(self, icon: QIcon, label: str, data: str) -> None:
        self._items.append((label, data))
        if self._current_index == -1:
            self.setCurrentIndex(0)

    def count(self) -> int:
        return len(self._items)

    def findData(self, data: str) -> int:
        for index, (_label, item_data) in enumerate(self._items):
            if item_data == data:
                return index
        return -1

    def currentData(self) -> str | None:
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][1]
        return None

    def setCurrentIndex(self, index: int) -> None:
        if not (0 <= index < len(self._items)):
            return
        self._current_index = index
        label, data = self._items[index]
        self.setText("")
        self.setToolTip(label)
        self.setIcon(self._icon_provider(data))
        self.setIconSize(QSize(26, 26))
        self.currentIndexChanged.emit(index)

    def _open_picker(self) -> None:
        if not self._items:
            return

        dialog = QDialog(self, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        dialog.setStyleSheet(
            f"""
            QDialog {{
                background-color: rgba(20, 24, 35, 0.98);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }}
            QLabel {{
                color: rgba(255, 255, 255, 0.7);
                font-size: 12px;
                font-family: {self.app_font};
                letter-spacing: 0.5px;
            }}
            QPushButton[iconChoice="true"] {{
                background-color: transparent;
                border: none;
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.88);
                padding: 6px 8px;
                font-size: 13px;
                font-family: {self.app_font};
                font-weight: 600;
            }}
            QPushButton[iconChoice="true"]:hover {{
                background-color: rgba(255, 255, 255, 0.05);
            }}
            """
        )

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        columns = 4

        for index, (label, data) in enumerate(self._items):
            choice = QPushButton("")
            choice.setProperty("iconChoice", True)
            choice.setCheckable(True)
            choice.setChecked(index == self._current_index)
            choice.setToolTip(label)
            choice.setFixedSize(54, 54)
            choice.setIcon(self._icon_provider(data))
            choice.setIconSize(QSize(24, 24))
            if index == self._current_index:
                choice.setStyleSheet(
                    f"""
                    QPushButton[iconChoice="true"] {{
                        background-color: rgba(255, 255, 255, 0.06);
                        border: none;
                        border-radius: 14px;
                        padding: 0px;
                    }}
                    """
                )
            choice.clicked.connect(lambda _checked=False, idx=index: self._choose_index(dialog, idx))
            grid.addWidget(choice, index // columns, index % columns)

        layout.addLayout(grid)
        dialog.adjustSize()
        dialog.move(self.mapToGlobal(self.rect().bottomLeft() + QPoint(0, 8)))
        dialog.exec()

    def _choose_index(self, dialog: QDialog, index: int) -> None:
        self.setCurrentIndex(index)
        dialog.accept()


class BeatNoteComboBox(QComboBox):
    def __init__(self, *, app_font: str, parent=None) -> None:
        super().__init__(parent)
        self.app_font = app_font
        view = QListView(self)
        view.setUniformItemSizes(True)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setView(view)
        self.setMaxVisibleItems(6)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"""
            QComboBox {{
                combobox-popup: 0;
                background-color: rgba(255, 255, 255, 0.045);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 14px;
                font-family: {self.app_font};
            }}
            QComboBox:hover {{
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: rgba(20, 24, 35, 0.98);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 0px;
                outline: none;
                selection-background-color: rgba(255, 255, 255, 0.08);
                font-size: 14px;
                font-family: {self.app_font};
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 30px;
                padding: 6px 10px;
                border-radius: 0px;
            }}
            QComboBox QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 8px 4px 8px 0;
            }}
            QComboBox QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.16);
                border-radius: 4px;
                min-height: 28px;
            }}
            QComboBox QScrollBar::add-line:vertical,
            QComboBox QScrollBar::sub-line:vertical,
            QComboBox QScrollBar::add-page:vertical,
            QComboBox QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0px;
            }}
            """
        )

    def showPopup(self) -> None:
        super().showPopup()
        popup = self.view().window()
        popup.setFixedWidth(self.width())
        popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup.setStyleSheet(
            """
            background-color: rgba(20, 24, 35, 0.98);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            """
        )
        popup.move(self.mapToGlobal(QPoint(0, self.height() + 4)))
        self.view().setFixedWidth(self.width())
        self.view().setContentsMargins(0, 0, 0, 0)
        self.view().scrollTo(self.model().index(self.currentIndex(), 0), QListView.ScrollHint.PositionAtCenter)

    def wheelEvent(self, event) -> None:
        event.ignore()


class BeatNoteCategoryDialog(QDialog):
    def __init__(self, parent=None, *, app_font: str, title: str, label: str, initial_text: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(320, 160)
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: rgba(20, 24, 35, 0.98);
                color: #FFFFFF;
            }}
            QLabel {{
                color: #FFFFFF;
                font-size: 13px;
                font-family: {app_font};
            }}
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.045);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 14px;
                font-family: {app_font};
            }}
            QPushButton {{
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 13px;
                font-family: {app_font};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        prompt = QLabel(label)
        layout.addWidget(prompt)

        self.input = QLineEdit()
        self.input.setText(initial_text)
        self.input.selectAll()
        layout.addWidget(self.input)

        buttons = QDialogButtonBox()
        ok_button = buttons.addButton("OK", QDialogButtonBox.ButtonRole.AcceptRole)
        ok_button.setStyleSheet("background-color: rgba(14, 79, 27, 0.95); color: #FFFFFF; border: none;")
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        cancel_button.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.1);")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.input.setFocus()

    def category_name(self) -> str:
        return self.input.text().strip()


class BeatNoteCategoryReplaceDialog(QDialog):
    def __init__(self, parent=None, *, app_font: str, category_name: str, replacement_options: list[str]) -> None:
        super().__init__(parent)
        self.setWindowTitle("Delete Category")
        self.setModal(True)
        self.setFixedSize(360, 190)
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: rgba(20, 24, 35, 0.98);
                color: #FFFFFF;
            }}
            QLabel {{
                color: #FFFFFF;
                font-size: 13px;
                font-family: {app_font};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        prompt = QLabel(f"Delete '{category_name}' and move its notes to:")
        prompt.setWordWrap(True)
        layout.addWidget(prompt)

        self.replacement_combo = BeatNoteComboBox(app_font=app_font)
        for option in replacement_options:
            self.replacement_combo.addItem(category_label(option), option)
        layout.addWidget(self.replacement_combo)

        buttons = QDialogButtonBox()
        delete_button = buttons.addButton("Delete", QDialogButtonBox.ButtonRole.AcceptRole)
        delete_button.setStyleSheet("background-color: #7a2626; color: #FFFFFF; border: none; border-radius: 10px; padding: 8px 14px;")
        cancel_button = buttons.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        cancel_button.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 8px 14px;")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def replacement_category(self) -> str | None:
        return self.replacement_combo.currentData()


class BeatNoteCategoryManagerDialog(QDialog):
    renamed = pyqtSignal(str, str)
    deleted = pyqtSignal(str, str)

    def __init__(self, parent=None, *, app_font: str, categories: list[str], service: BeatNoteService) -> None:
        super().__init__(parent)
        self.app_font = app_font
        self.service = service
        self.categories = list(categories)
        self.setWindowTitle("Manage Categories")
        self.setModal(True)
        self.setFixedSize(420, 360)
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: rgba(20, 24, 35, 0.98);
                color: #FFFFFF;
            }}
            QLabel {{
                color: rgba(255, 255, 255, 0.74);
                font-size: 13px;
                font-family: {app_font};
            }}
            QListWidget {{
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 6px;
                color: #FFFFFF;
                font-size: 14px;
                font-family: {app_font};
            }}
            QListWidget::item {{
                padding: 10px 12px;
                border-radius: 10px;
                margin: 2px 0;
                border: 1px solid transparent;
            }}
            QListWidget::item:selected {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.035);
            }}
            QPushButton {{
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                font-family: {app_font};
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        description = QLabel("Rename or delete custom categories. Built-in categories stay untouched.")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setFrameShape(QListWidget.Shape.NoFrame)
        layout.addWidget(self.list_widget, 1)

        actions = QHBoxLayout()
        self.rename_button = QPushButton("Rename")
        self.rename_button.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.1);")
        self.rename_button.clicked.connect(self._rename_selected)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet("background-color: #7a2626; color: #FFFFFF; border: none;")
        self.delete_button.clicked.connect(self._delete_selected)
        close_button = QPushButton("Close")
        close_button.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #FFFFFF; border: 1px solid rgba(255,255,255,0.1);")
        close_button.clicked.connect(self.accept)
        actions.addWidget(self.rename_button)
        actions.addWidget(self.delete_button)
        actions.addStretch()
        actions.addWidget(close_button)
        layout.addLayout(actions)

        self._rebuild_list()

    def _rebuild_list(self) -> None:
        self.list_widget.clear()
        for category in self.categories:
            item = QListWidgetItem(category_label(category))
            item.setData(Qt.ItemDataRole.UserRole, category)
            self.list_widget.addItem(item)
        enabled = bool(self.categories)
        self.rename_button.setEnabled(enabled)
        self.delete_button.setEnabled(enabled)

    def _selected_category(self) -> str | None:
        item = self.list_widget.currentItem()
        if item is None and self.list_widget.count() > 0:
            item = self.list_widget.item(0)
            self.list_widget.setCurrentItem(item)
        if item is None:
            return None
        return str(item.data(Qt.ItemDataRole.UserRole) or "")

    def _rename_selected(self) -> None:
        current = self._selected_category()
        if not current:
            return
        dialog = BeatNoteCategoryDialog(
            self,
            app_font=self.app_font,
            title="Rename Category",
            label="New category name:",
            initial_text=category_label(current),
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = self.service.rename_category(current, dialog.category_name())
        except BeatNoteServiceError as exc:
            QMessageBox.warning(self, "Rename Category", str(exc))
            return
        self.categories = [updated if category.casefold() == current.casefold() else category for category in self.categories]
        self.categories = ordered_categories(self.categories)
        self._rebuild_list()
        self.renamed.emit(current, updated)

    def _delete_selected(self) -> None:
        current = self._selected_category()
        if not current:
            return
        replacement_options = [category for category in self.service.list_categories() if category.casefold() != current.casefold()]
        dialog = BeatNoteCategoryReplaceDialog(
            self,
            app_font=self.app_font,
            category_name=category_label(current),
            replacement_options=replacement_options,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        replacement = dialog.replacement_category()
        if not replacement:
            return
        try:
            final_replacement = self.service.delete_category(current, replacement_category=replacement)
        except BeatNoteServiceError as exc:
            QMessageBox.warning(self, "Delete Category", str(exc))
            return
        self.categories = [category for category in self.categories if category.casefold() != current.casefold()]
        self._rebuild_list()
        self.deleted.emit(current, final_replacement)


class BeatNotePanel(QWidget):
    notes_changed = pyqtSignal()

    def __init__(
        self,
        *,
        service: BeatNoteService | None = None,
        colors: dict[str, str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.service = service or BeatNoteService()
        self.colors = colors or {}
        self.app_font = get_app_font()
        self.notes: list[BeatNote] = []
        self.filtered_notes: list[BeatNote] = []
        self.available_categories: list[str] = list(BEATNOTE_CATEGORIES)
        self.current_note_id: str | None = None
        self._editor_snapshot: tuple[Any, ...] | None = None
        self._loading_editor = False
        self._selection_guard = False
        self._category_expansion_state: dict[str, bool] = {}

        self.setup_ui()
        self._refresh_category_controls()
        self.reload_notes()

    def setup_ui(self) -> None:
        self.setObjectName("BeatNotePanel")
        self.setStyleSheet(
            f"""
            QWidget#BeatNotePanel {{
                background-color: transparent;
            }}
            QLabel {{
                color: {self.colors.get('text_white', '#FFFFFF')};
                font-family: {self.app_font};
            }}
            QLineEdit, QTextEdit, QComboBox {{
                background-color: rgba(255, 255, 255, 0.045);
                color: {self.colors.get('text_white', '#FFFFFF')};
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
                padding: 10px 12px;
                font-size: 14px;
                font-family: {self.app_font};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border: 1px solid rgba(46, 125, 50, 0.6);
            }}
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        workspace_shell = QFrame()
        workspace_shell.setStyleSheet(
            """
            background-color: rgba(14, 18, 27, 0.94);
            border-radius: 22px;
            border: none;
            """
        )
        shell_shadow = QGraphicsDropShadowEffect()
        shell_shadow.setBlurRadius(28)
        shell_shadow.setOffset(0, 12)
        shell_shadow.setColor(QColor(0, 0, 0, 85))
        workspace_shell.setGraphicsEffect(shell_shadow)

        shell_layout = QVBoxLayout(workspace_shell)
        shell_layout.setContentsMargins(18, 18, 18, 18)
        shell_layout.setSpacing(16)

        hero = QFrame()
        hero.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 0.022);
            border-radius: 18px;
            border: none;
            """
        )
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(18)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(4)
        hero_title = QLabel("BeatNote")
        hero_title.setStyleSheet("font-size: 24px; font-weight: 700; background: transparent;")
        hero_title.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        hero_subtitle = QLabel("Track reconnaissance, attack paths, credentials, evidence and next steps in one notebook.")
        hero_subtitle.setWordWrap(True)
        hero_subtitle.setMaximumWidth(520)
        hero_subtitle.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.72); background: transparent;")
        hero_subtitle.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        hero_text.addWidget(hero_title)
        hero_text.addWidget(hero_subtitle)

        self.new_note_button = QPushButton("New BeatNote")
        self.new_note_button.setObjectName("BeatNoteCreateButton")
        self.new_note_button.setStyleSheet(
            build_filled_button_qss(
                self.app_font,
                self.colors.get("popup_button", "#0E4F1B"),
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=14,
                padding="10px 18px",
            )
        )
        self.new_note_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.new_note_button.clicked.connect(self.start_new_note)

        hero_actions = QHBoxLayout()
        hero_actions.setSpacing(10)
        hero_actions.addStretch()
        hero_actions.addWidget(self.new_note_button)

        hero_layout.addLayout(hero_text, 1)
        hero_layout.addLayout(hero_actions)
        shell_layout.addWidget(hero)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        sidebar = QFrame()
        sidebar.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 0.025);
            border-radius: 18px;
            border: none;
            """
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        notebook_label = QLabel("Attack Tree")
        notebook_label.setStyleSheet("font-size: 18px; font-weight: 700; background: transparent;")
        notebook_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sidebar_layout.addWidget(notebook_label)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("BeatNoteSearchInput")
        self.search_input.setPlaceholderText("Search notes, hosts, vulnerabilities or credentials")
        self.search_input.textChanged.connect(self.apply_filters)
        sidebar_layout.addWidget(self.search_input)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        self.category_filter = BeatNoteComboBox(app_font=self.app_font)
        self.category_filter.setObjectName("BeatNoteCategoryFilter")
        self.category_filter.currentIndexChanged.connect(self.apply_filters)

        self.pinned_filter = QCheckBox("Pinned")
        self.pinned_filter.setObjectName("BeatNotePinnedFilter")
        self.pinned_filter.setStyleSheet(
            f"color: {self.colors.get('text_white', '#FFFFFF')}; font-size: 14px; font-family: {self.app_font};"
        )
        self.pinned_filter.stateChanged.connect(self.apply_filters)

        filter_row.addWidget(self.category_filter, 1)
        filter_row.addWidget(self.pinned_filter)
        sidebar_layout.addLayout(filter_row)

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("BeatNoteStatsLabel")
        self.stats_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.58); background: transparent;")
        self.stats_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sidebar_layout.addWidget(self.stats_label)

        self.tree = QTreeWidget()
        self.tree.setObjectName("BeatNoteTree")
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setAnimated(True)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setStyleSheet(
            f"""
            QTreeWidget {{
                background-color: rgba(255, 255, 255, 0.02);
                border-radius: 14px;
                border: none;
                padding: 8px;
                outline: none;
                show-decoration-selected: 1;
                color: {self.colors.get('text_white', '#FFFFFF')};
                font-family: {self.app_font};
                font-size: 14px;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-radius: 8px;
                border: 1px solid transparent;
            }}
            QTreeWidget::item:has-children {{
                background-color: rgba(255, 255, 255, 0.035);
                font-weight: 700;
                padding: 8px 10px;
                border: 1px solid rgba(255, 255, 255, 0.06);
            }}
            QTreeWidget::item:has-children:hover {{
                background-color: rgba(255, 255, 255, 0.065);
            }}
            QTreeWidget::item:selected {{
                background-color: transparent;
                border: 1px solid transparent;
                color: {self.colors.get('text_white', '#FFFFFF')};
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QTreeWidget::branch {{
                background: transparent;
                border-image: none;
                image: none;
            }}
            QTreeWidget::branch:selected {{
                background: transparent;
            }}
            """
        )
        self.tree.currentItemChanged.connect(self._on_tree_current_item_changed)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        self.tree.itemExpanded.connect(self._on_tree_item_expanded)
        self.tree.itemCollapsed.connect(self._on_tree_item_collapsed)
        sidebar_layout.addWidget(self.tree, 1)

        editor_shell = QFrame()
        editor_shell.setStyleSheet(
            """
            background-color: rgba(18, 24, 35, 0.92);
            border-radius: 18px;
            border: none;
            """
        )
        editor_layout = QVBoxLayout(editor_shell)
        editor_layout.setContentsMargins(16, 16, 16, 16)
        editor_layout.setSpacing(14)

        self.editor_stack = QStackedWidget()

        self.empty_state = QFrame()
        self.empty_state.setObjectName("BeatNoteEmptyState")
        self.empty_state.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 0.02);
            border-radius: 18px;
            border: none;
            """
        )
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(30, 38, 30, 38)
        empty_layout.setSpacing(14)
        self.empty_title = QLabel("Start an operation notebook")
        self.empty_title.setStyleSheet("font-size: 22px; font-weight: 700;")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.empty_body = QLabel("Create a first note for recon, hosts, credentials or next steps.")
        self.empty_body.setWordWrap(True)
        self.empty_body.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.empty_body.setStyleSheet("font-size: 14px; color: rgba(255, 255, 255, 0.72);")
        self.empty_action = QPushButton("Create first BeatNote")
        self.empty_action.setObjectName("BeatNoteEmptyCreateButton")
        self.empty_action.setStyleSheet(
            build_filled_button_qss(
                self.app_font,
                self.colors.get("popup_button", "#0E4F1B"),
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=14,
                padding="10px 18px",
            )
        )
        self.empty_action.clicked.connect(self.start_new_note)
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_title)
        empty_layout.addWidget(self.empty_body)
        empty_layout.addWidget(self.empty_action, 0, Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addStretch()

        self.editor_page = QWidget()
        form_layout = QVBoxLayout(self.editor_page)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(14)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        self.editor_title = QLineEdit()
        self.editor_title.setObjectName("BeatNoteEditorTitle")
        self.editor_title.setPlaceholderText("Untitled BeatNote")
        self.editor_title.setStyleSheet(
            f"""
            font-size: 28px;
            font-weight: 700;
            padding: 14px 16px;
            background-color: rgba(255, 255, 255, 0.025);
            border: none;
            """
        )

        self.editor_icon = BeatNoteIconPicker(app_font=self.app_font, icon_provider=self._icon_qicon)
        for icon_key in BEATNOTE_ICON_OPTIONS:
            self.editor_icon.addItem(self._icon_qicon(icon_key), BEATNOTE_ICON_LABELS.get(icon_key, icon_key.title()), icon_key)

        title_row.addWidget(self.editor_title, 1)
        title_row.addWidget(self.editor_icon)
        form_layout.addLayout(title_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(12)

        self.editor_category = BeatNoteComboBox(app_font=self.app_font)
        self.editor_category.setObjectName("BeatNoteEditorCategory")

        self.add_category_button = QPushButton("+ Category")
        self.add_category_button.setObjectName("BeatNoteAddCategoryButton")
        self.add_category_button.setStyleSheet(
            build_disabled_button_qss(
                self.app_font,
                "rgba(255, 255, 255, 0.05)",
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=13,
                border="1px solid rgba(255, 255, 255, 0.08)",
                extra_base="padding: 9px 12px;",
            )
        )
        self.add_category_button.clicked.connect(self._prompt_new_category)

        self.manage_categories_button = QPushButton("Manage")
        self.manage_categories_button.setObjectName("BeatNoteManageCategoriesButton")
        self.manage_categories_button.setStyleSheet(
            build_disabled_button_qss(
                self.app_font,
                "rgba(255, 255, 255, 0.05)",
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=13,
                border="1px solid rgba(255, 255, 255, 0.08)",
                extra_base="padding: 9px 12px;",
            )
        )
        self.manage_categories_button.clicked.connect(self._manage_categories)

        self.editor_tags = QLineEdit()
        self.editor_tags.setObjectName("BeatNoteEditorTags")
        self.editor_tags.setPlaceholderText("hostnames, CVEs, users, tools")

        self.editor_pinned = QCheckBox("Pinned")
        self.editor_pinned.setStyleSheet(
            f"color: {self.colors.get('text_white', '#FFFFFF')}; font-size: 14px; font-family: {self.app_font};"
        )

        self.updated_label = QLabel("Updated just now")
        self.updated_label.setStyleSheet("font-size: 12px; color: rgba(255, 255, 255, 0.58);")

        meta_row.addWidget(self.editor_category)
        meta_row.addWidget(self.add_category_button)
        meta_row.addWidget(self.manage_categories_button)
        meta_row.addWidget(self.editor_tags, 1)
        meta_row.addWidget(self.editor_pinned)
        meta_row.addWidget(self.updated_label)
        form_layout.addLayout(meta_row)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        self.save_button = QPushButton("Save")
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
        self.save_button.clicked.connect(self.save_current_note)

        self.duplicate_button = QPushButton("Duplicate")
        self.duplicate_button.setStyleSheet(
            build_disabled_button_qss(
                self.app_font,
                "rgba(255, 255, 255, 0.08)",
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=14,
                border="1px solid rgba(255, 255, 255, 0.12)",
                extra_base="padding: 10px 18px;",
            )
        )
        self.duplicate_button.clicked.connect(self.duplicate_current_note)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(
            build_disabled_button_qss(
                self.app_font,
                "#5a1d1d",
                self.colors.get("text_white", "#FFFFFF"),
                radius=12,
                font_size=14,
                border="1px solid rgba(255, 255, 255, 0.12)",
                extra_base="padding: 10px 18px;",
            )
        )
        self.delete_button.clicked.connect(self.delete_current_note)

        actions_row.addWidget(self.save_button)
        actions_row.addWidget(self.duplicate_button)
        actions_row.addStretch()
        actions_row.addWidget(self.delete_button)
        form_layout.addLayout(actions_row)

        content_toolbar = QHBoxLayout()
        content_toolbar.setSpacing(8)

        self.bold_button = QPushButton("B")
        self.bold_button.setCheckable(True)
        self.bold_button.clicked.connect(self._toggle_bold)

        self.italic_button = QPushButton("I")
        self.italic_button.setCheckable(True)
        self.italic_button.clicked.connect(self._toggle_italic)

        self.underline_button = QPushButton("U")
        self.underline_button.setCheckable(True)
        self.underline_button.clicked.connect(self._toggle_underline)

        self.bullets_button = QPushButton("Bullets")
        self.bullets_button.clicked.connect(self._toggle_bullet_list)

        self.numbered_button = QPushButton("Numbered")
        self.numbered_button.clicked.connect(self._toggle_numbered_list)

        self.font_size_combo = BeatNoteComboBox(app_font=self.app_font)
        self.font_size_combo.setObjectName("BeatNoteFontSize")
        self.font_size_combo.setFixedWidth(92)
        for size in (12, 13, 14, 15, 16, 18, 20, 24):
            self.font_size_combo.addItem(f"{size}px", size)
        self.font_size_combo.currentIndexChanged.connect(self._apply_font_size)

        for button in (
            self.bold_button,
            self.italic_button,
            self.underline_button,
            self.bullets_button,
            self.numbered_button,
        ):
            button.setStyleSheet(
                build_disabled_button_qss(
                    self.app_font,
                    "rgba(255, 255, 255, 0.05)",
                    self.colors.get("text_white", "#FFFFFF"),
                    radius=10,
                    font_size=13,
                    border="1px solid rgba(255, 255, 255, 0.08)",
                    extra_base="padding: 8px 12px;",
                )
            )
            content_toolbar.addWidget(button)

        content_toolbar.addSpacing(8)
        content_toolbar.addWidget(self.font_size_combo)
        content_toolbar.addStretch()
        form_layout.addLayout(content_toolbar)

        self.content_edit = BeatNoteContentEdit()
        self.content_edit.setObjectName("BeatNoteEditorContent")
        self.content_edit.setPlaceholderText(
            "Write the note like an operation log: findings, targets, tooling, paths, credentials, follow-up tasks or evidence."
        )
        self.content_edit.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.content_edit.setMinimumHeight(420)
        self.content_edit.setStyleSheet(
            f"""
            QTextEdit {{
                font-size: 15px;
                line-height: 1.45;
                padding: 16px;
                background-color: rgba(7, 10, 17, 0.88);
                border: none;
            }}
            """
        )
        form_layout.addWidget(self.content_edit, 1)

        self.editor_stack.addWidget(self.empty_state)
        self.editor_stack.addWidget(self.editor_page)
        editor_layout.addWidget(self.editor_stack, 1)

        self.splitter.addWidget(sidebar)
        self.splitter.addWidget(editor_shell)
        self.splitter.setSizes([320, 860])
        shell_layout.addWidget(self.splitter, 1)

        root.addWidget(workspace_shell, 1)

        self.toast = BeatNoteToast(self, app_font=self.app_font)
        self._connect_editor_signals()
        self._sync_format_controls()
        self._show_empty_state()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.toast.reposition()

    def _icon_qicon(self, icon_key: str) -> QIcon:
        asset = BEATNOTE_ICON_ASSETS.get(icon_key)
        if not asset:
            return QIcon()
        return QIcon(get_resource_path(asset, "assets"))

    def _render_icon_pixmap(self, icon_key: str, size: int) -> QPixmap:
        icon = self._icon_qicon(icon_key)
        if not icon.isNull():
            icon_pixmap = icon.pixmap(size, size)
            if not icon_pixmap.isNull():
                return icon_pixmap

        icon_path = get_resource_path(BEATNOTE_ICON_ASSETS.get(icon_key, ""), "assets")
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        if QSvgRenderer is None or not icon_path.lower().endswith(".svg"):
            return pixmap

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer = QSvgRenderer(icon_path)
        if renderer.isValid():
            renderer.render(painter, pixmap.rect().toRectF())
        painter.end()
        return pixmap

    def _color_chip_icon(self, hex_color: str) -> QIcon:
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = QColor(hex_color)
        painter.setBrush(color)
        painter.setPen(QColor(255, 255, 255, 120))
        painter.drawRoundedRect(1, 1, 12, 12, 3, 3)
        painter.end()
        return QIcon(pixmap)

    def _note_swatch_icon(self, icon_key: str, hex_color: str) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg = QColor(hex_color)
        if not bg.isValid():
            bg = QColor(DEFAULT_NOTE_COLOR)

        painter.setBrush(bg)
        painter.setPen(QColor(255, 255, 255, 130))
        painter.drawRoundedRect(1, 1, 16, 16, 4, 4)

        icon_pixmap = self._render_icon_pixmap(icon_key, 10)
        if not icon_pixmap.isNull():
            painter.drawPixmap(4, 4, icon_pixmap)

        painter.end()
        return QIcon(pixmap)

    def _tree_note_icon(self, icon_key: str) -> QIcon:
        pixmap = self._render_icon_pixmap(icon_key, 22)
        icon = QIcon()
        if not pixmap.isNull():
            icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
            icon.addPixmap(pixmap, QIcon.Mode.Selected, QIcon.State.Off)
            icon.addPixmap(pixmap, QIcon.Mode.Active, QIcon.State.Off)
        return icon

    def _connect_editor_signals(self) -> None:
        self.editor_title.textChanged.connect(self._on_editor_changed)
        self.editor_category.currentIndexChanged.connect(self._on_editor_changed)
        self.editor_tags.textChanged.connect(self._on_editor_changed)
        self.editor_icon.currentIndexChanged.connect(self._on_editor_changed)
        self.editor_pinned.stateChanged.connect(self._on_editor_changed)
        self.content_edit.textChanged.connect(self._on_editor_changed)
        self.content_edit.cursorPositionChanged.connect(self._sync_format_controls)

    def _editor_state(self) -> tuple[Any, ...]:
        return (
            self.editor_title.text(),
            self.editor_category.currentData(),
            self.editor_tags.text(),
            self.editor_icon.currentData(),
            self.editor_pinned.isChecked(),
            self.content_edit.toHtml(),
        )

    def has_unsaved_editor_changes(self) -> bool:
        if self._editor_snapshot is None:
            return bool(self.editor_title.text().strip() or self.content_edit.toPlainText().strip())
        return self._editor_state() != self._editor_snapshot

    def _set_editor_snapshot(self) -> None:
        self._editor_snapshot = self._editor_state()
        self._update_editor_buttons()

    def _update_editor_buttons(self) -> None:
        dirty = self.has_unsaved_editor_changes()
        self.save_button.setText("Create note" if self.current_note_id is None else "Save note")
        self.save_button.setEnabled(dirty or self.current_note_id is None)
        has_current = self.current_note_id is not None
        self.delete_button.setEnabled(has_current)
        self.duplicate_button.setEnabled(has_current)

    def _on_editor_changed(self, *_args) -> None:
        if self._loading_editor:
            return
        self._update_editor_buttons()

    def _show_empty_state(self, *, title: str | None = None, body: str | None = None, action_text: str | None = None) -> None:
        self.empty_title.setText(title or "Start an operation notebook")
        self.empty_body.setText(
            body or "Create a first note for recon, vulnerabilities, credentials or next steps."
        )
        self.empty_action.setText(action_text or "Create first BeatNote")
        self.editor_stack.setCurrentWidget(self.empty_state)

    def _show_editor(self) -> None:
        self.editor_stack.setCurrentWidget(self.editor_page)

    def _merge_format_on_selection(self, formatter) -> None:
        cursor = self.content_edit.textCursor()
        formatter(cursor)
        self.content_edit.setFocus()
        self._sync_format_controls()

    def _current_font_point_size(self) -> float:
        current_size = self.content_edit.currentFont().pointSizeF()
        if current_size and current_size > 0:
            return current_size
        combo_size = self.font_size_combo.currentData()
        return float(combo_size or 15)

    def _apply_char_format(self, fmt: QTextCharFormat) -> None:
        cursor = self.content_edit.textCursor()
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        self.content_edit.mergeCurrentCharFormat(fmt)

    def _selected_blocks(self) -> list[Any]:
        cursor = self.content_edit.textCursor()
        document = self.content_edit.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        if start == end:
            block = document.findBlock(cursor.position())
            return [block] if block.isValid() else []

        start_block = document.findBlock(start)
        end_block = document.findBlock(max(start, end - 1))
        blocks = []
        block = start_block
        while block.isValid():
            blocks.append(block)
            if block.position() == end_block.position():
                break
            block = block.next()
        return blocks

    def _replace_block_prefix(self, block: Any, *, remove_pattern: str | None = None, add_prefix: str | None = None) -> None:
        block_cursor = QTextCursor(block)
        block_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        text = block.text()

        if remove_pattern:
            match = re.match(remove_pattern, text)
            if match:
                for _ in range(len(match.group(0))):
                    block_cursor.deleteChar()

        if add_prefix:
            block_cursor.insertText(add_prefix, self.content_edit.currentCharFormat())

    def _toggle_bold(self) -> None:
        def formatter(cursor: QTextCursor) -> None:
            fmt = QTextCharFormat()
            is_bold = self.content_edit.fontWeight() >= int(QFont.Weight.Bold)
            fmt.setFontWeight(int(QFont.Weight.Normal if is_bold else QFont.Weight.Bold))
            self._apply_char_format(fmt)

        self._merge_format_on_selection(formatter)

    def _toggle_italic(self) -> None:
        def formatter(cursor: QTextCursor) -> None:
            fmt = QTextCharFormat()
            fmt.setFontItalic(not self.content_edit.fontItalic())
            self._apply_char_format(fmt)

        self._merge_format_on_selection(formatter)

    def _toggle_underline(self) -> None:
        def formatter(cursor: QTextCursor) -> None:
            fmt = QTextCharFormat()
            fmt.setFontUnderline(not self.content_edit.fontUnderline())
            self._apply_char_format(fmt)

        self._merge_format_on_selection(formatter)

    def _toggle_bullet_list(self) -> None:
        blocks = self._selected_blocks()
        if not blocks:
            return
        cursor = self.content_edit.textCursor()
        cursor.beginEditBlock()
        is_bullet_list = all(block.text().lstrip().startswith("• ") for block in blocks)
        for block in blocks:
            self._replace_block_prefix(
                block,
                remove_pattern=r"^\s*(?:•\s+|\d+\.\s+)",
                add_prefix=None if is_bullet_list else "• ",
            )
        cursor.endEditBlock()
        self.content_edit.setFocus()

    def _toggle_numbered_list(self) -> None:
        blocks = self._selected_blocks()
        if not blocks:
            return
        cursor = self.content_edit.textCursor()
        cursor.beginEditBlock()
        is_numbered_list = all(re.match(r"^\s*\d+\.\s+", block.text()) for block in blocks)
        for index, block in enumerate(blocks, start=1):
            self._replace_block_prefix(
                block,
                remove_pattern=r"^\s*(?:•\s+|\d+\.\s+)",
                add_prefix=None if is_numbered_list else f"{index}. ",
            )
        cursor.endEditBlock()
        self.content_edit.setFocus()

    def _apply_font_size(self, _index: int) -> None:
        if self._loading_editor:
            return
        size = self.font_size_combo.currentData()
        if not size:
            return
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        self._apply_char_format(fmt)
        self.content_edit.setFocus()
        self._sync_format_controls()

    def _sync_format_controls(self) -> None:
        if not hasattr(self, "content_edit"):
            return
        self.bold_button.setChecked(self.content_edit.fontWeight() >= int(QFont.Weight.Bold))
        self.italic_button.setChecked(self.content_edit.fontItalic())
        self.underline_button.setChecked(self.content_edit.fontUnderline())
        active_style = build_filled_button_qss(
            self.app_font,
            "rgba(45, 140, 255, 0.22)",
            self.colors.get("text_white", "#FFFFFF"),
            radius=10,
            font_size=13,
            padding="8px 12px",
            border="1px solid rgba(45, 140, 255, 0.35)",
        )
        inactive_style = build_disabled_button_qss(
            self.app_font,
            "rgba(255, 255, 255, 0.05)",
            self.colors.get("text_white", "#FFFFFF"),
            radius=10,
            font_size=13,
            border="1px solid rgba(255, 255, 255, 0.08)",
            extra_base="padding: 8px 12px;",
        )
        for button in (self.bold_button, self.italic_button, self.underline_button):
            button.setStyleSheet(active_style if button.isChecked() else inactive_style)
        size = int(round(self.content_edit.fontPointSize() or 15))
        size_index = self.font_size_combo.findData(size)
        if size_index >= 0:
            self.font_size_combo.blockSignals(True)
            self.font_size_combo.setCurrentIndex(size_index)
            self.font_size_combo.blockSignals(False)

    def focus_search(self) -> None:
        self.search_input.setFocus()
        self.search_input.selectAll()

    def reset_filters(self) -> None:
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)
        self.pinned_filter.setChecked(False)

    def show_toast(self, message: str, *, error: bool = False) -> None:
        self.toast.show_message(message, error=error)

    def _refresh_category_controls(self, *, selected_category: str | None = None) -> None:
        try:
            categories = self.service.list_categories()
        except BeatNoteServiceError:
            categories = list(BEATNOTE_CATEGORIES)

        note_categories = [note.category for note in self.notes]
        categories = ordered_categories((*categories, *note_categories))
        self.available_categories = categories or list(BEATNOTE_CATEGORIES)

        current_filter = selected_category or str(self.category_filter.currentData() or "all")
        current_editor = selected_category or str(self.editor_category.currentData() or "objective")

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All categories", "all")
        for category in self.available_categories:
            self.category_filter.addItem(category_label(category), category)
        filter_index = self.category_filter.findData(current_filter)
        self.category_filter.setCurrentIndex(filter_index if filter_index >= 0 else 0)
        self.category_filter.blockSignals(False)

        self.editor_category.blockSignals(True)
        self.editor_category.clear()
        for category in self.available_categories:
            self.editor_category.addItem(category_label(category), category)
        editor_index = self.editor_category.findData(current_editor)
        self.editor_category.setCurrentIndex(editor_index if editor_index >= 0 else 0)
        self.editor_category.blockSignals(False)

    def _prompt_new_category(self) -> None:
        dialog = BeatNoteCategoryDialog(
            self,
            app_font=self.app_font,
            title="New Category",
            label="Category name:",
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            created_category = self.service.create_category(dialog.category_name())
        except BeatNoteServiceError as exc:
            self.show_toast(str(exc), error=True)
            return
        except Exception as exc:
            self.show_toast(str(exc), error=True)
            return

        self._refresh_category_controls(selected_category=created_category)
        self._on_editor_changed()
        self.show_toast(f"Created category '{category_label(created_category)}'.")

    def _manage_categories(self) -> None:
        custom_categories = [category for category in self.service.list_categories() if category not in BEATNOTE_CATEGORIES]
        dialog = BeatNoteCategoryManagerDialog(
            self,
            app_font=self.app_font,
            categories=custom_categories,
            service=self.service,
        )
        dialog.renamed.connect(self._on_category_renamed)
        dialog.deleted.connect(self._on_category_deleted)
        dialog.exec()

    def _on_category_renamed(self, old_category: str, new_category: str) -> None:
        if str(self.editor_category.currentData() or "").casefold() == old_category.casefold():
            self._refresh_category_controls(selected_category=new_category)
        else:
            self._refresh_category_controls()
        self.reload_notes(select_note_id=self.current_note_id)
        self.show_toast(f"Renamed category to '{category_label(new_category)}'.")

    def _on_category_deleted(self, old_category: str, replacement_category: str) -> None:
        if str(self.editor_category.currentData() or "").casefold() == old_category.casefold():
            self._refresh_category_controls(selected_category=replacement_category)
        else:
            self._refresh_category_controls()
        self.reload_notes(select_note_id=self.current_note_id)
        self.show_toast(
            f"Deleted '{category_label(old_category)}' and moved notes to '{category_label(replacement_category)}'."
        )

    def reload_notes(self, *, select_note_id: str | None = None) -> None:
        try:
            self.notes = self.service.list()
        except BeatNoteServiceError as exc:
            self.notes = []
            self.show_toast(f"Could not load BeatNotes: {exc}", error=True)
        self._refresh_category_controls()
        self._rebuild_view(select_note_id=select_note_id)

    def apply_filters(self, *_args) -> None:
        self._rebuild_view(select_note_id=self.current_note_id)

    def _rebuild_view(self, *, select_note_id: str | None = None) -> None:
        self.filtered_notes = filter_beatnotes(
            self.notes,
            search_text=self.search_input.text(),
            category=self.category_filter.currentData() or "all",
            pinned_only=self.pinned_filter.isChecked(),
        )
        self._rebuild_tree()

        if not self.notes:
            self.stats_label.setText("0 notes in BeatNote")
            self.current_note_id = None
            self._show_empty_state()
            return

        if not self.filtered_notes:
            self.stats_label.setText(f"{len(self.notes)} total notes · 0 matching current filters")
            self._show_empty_state(
                title="No BeatNotes match the current filters",
                body="Try a broader search, switch category, or clear pinned-only mode.",
                action_text="Reset filters",
            )
            self.empty_action.clicked.disconnect()
            self.empty_action.clicked.connect(self.reset_filters)
            return

        try:
            self.empty_action.clicked.disconnect()
        except TypeError:
            pass
        self.empty_action.clicked.connect(self.start_new_note)
        self.stats_label.setText(
            f"{len(self.filtered_notes)} shown · {len(self.notes)} total · {sum(1 for note in self.notes if note.pinned)} pinned"
        )

        desired_id = select_note_id if select_note_id and any(note.id == select_note_id for note in self.filtered_notes) else None
        if desired_id is not None:
            self._load_note(desired_id)
            self._select_tree_note(desired_id)
            return

        if self.current_note_id and self._find_note(self.current_note_id) is not None:
            if self._select_tree_note(self.current_note_id):
                return
            self._selection_guard = True
            self.tree.setCurrentItem(None)
            self._selection_guard = False
            self._show_editor()
            return

        if self.filtered_notes:
            self._load_note(self.filtered_notes[0].id)
            self._select_tree_note(self.filtered_notes[0].id)

    def _rebuild_tree(self) -> None:
        self._selection_guard = True
        self._snapshot_category_expansion_state()
        self.tree.clear()

        grouped: dict[str, list[BeatNote]] = defaultdict(list)
        for note in self.filtered_notes:
            grouped[note.category].append(note)

        for category in ordered_categories(grouped.keys()):
            notes = grouped.get(category, [])
            if not notes:
                continue

            root_item = QTreeWidgetItem([""])
            root_item.setData(0, Qt.ItemDataRole.UserRole, None)
            root_item.setData(0, Qt.ItemDataRole.UserRole + 1, category)
            root_item.setData(0, Qt.ItemDataRole.UserRole + 2, len(notes))
            root_item.setFlags(root_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font = root_item.font(0)
            font.setBold(True)
            root_item.setFont(0, font)
            root_item.setSizeHint(0, QSize(0, 34))
            self.tree.addTopLevelItem(root_item)
            top_index = self.tree.indexOfTopLevelItem(root_item)
            self.tree.setFirstColumnSpanned(top_index, QModelIndex(), True)

            expanded = self._category_expansion_state.get(category, True)
            root_item.setExpanded(expanded)
            self._set_category_item_label(root_item, expanded=expanded)

            for note in notes:
                title = note.title
                if note.pinned:
                    title = f"📌 {title}"
                child = QTreeWidgetItem([title])
                child.setData(0, Qt.ItemDataRole.UserRole, note.id)
                child.setToolTip(0, self._tree_tooltip(note))
                child.setSizeHint(0, QSize(0, 30))
                child.setIcon(0, self._tree_note_icon(note.icon or DEFAULT_NOTE_ICON))
                root_item.addChild(child)
        self._refresh_tree_item_styles()
        self._selection_guard = False

    def _snapshot_category_expansion_state(self) -> None:
        for root_index in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(root_index)
            if root is None:
                continue
            category = root.data(0, Qt.ItemDataRole.UserRole + 1)
            if category:
                self._category_expansion_state[str(category)] = root.isExpanded()

    def _refresh_tree_item_styles(self) -> None:
        current = self.tree.currentItem()
        text_white = QColor(self.colors.get("text_white", "#FFFFFF"))
        muted_text = QColor(255, 255, 255, 220)
        root_bg = QBrush(QColor(255, 255, 255, 10))
        selected_bg = QBrush(QColor(255, 255, 255, 24))
        transparent = QBrush(QColor(0, 0, 0, 0))

        for root_index in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(root_index)
            if root is None:
                continue

            root.setBackground(0, root_bg)
            root.setForeground(0, QBrush(text_white))

            for child_index in range(root.childCount()):
                child = root.child(child_index)
                if child is None:
                    continue

                child_font = child.font(0)
                is_selected = child is current
                child_font.setBold(is_selected)
                child.setFont(0, child_font)
                child.setForeground(0, QBrush(text_white if is_selected else muted_text))
                child.setBackground(0, selected_bg if is_selected else transparent)

    def _is_category_root_item(self, item: QTreeWidgetItem | None) -> bool:
        return item is not None and item.data(0, Qt.ItemDataRole.UserRole) is None and item.childCount() > 0

    def _set_category_item_label(self, item: QTreeWidgetItem, *, expanded: bool) -> None:
        category = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if not category:
            return
        count = int(item.data(0, Qt.ItemDataRole.UserRole + 2) or item.childCount())
        arrow = "▼" if expanded else "▶"
        item.setText(0, f"{arrow} {category_label(str(category))} ({count})")

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if not self._is_category_root_item(item):
            return

        expanded = not item.isExpanded()
        item.setExpanded(expanded)

    def _on_tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if not self._is_category_root_item(item):
            return
        category = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if category:
            self._category_expansion_state[str(category)] = True
        self._set_category_item_label(item, expanded=True)

    def _on_tree_item_collapsed(self, item: QTreeWidgetItem) -> None:
        if not self._is_category_root_item(item):
            return
        category = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if category:
            self._category_expansion_state[str(category)] = False
        self._set_category_item_label(item, expanded=False)

    def _open_note_style_menu(self, note_id: str, anchor: QWidget, *, section: str = "both") -> None:
        note = self._find_note(note_id)
        if note is None:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background-color: rgba(20, 24, 35, 0.98);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.12);
                padding: 6px;
            }
            QMenu::item {
                padding: 7px 12px;
                border-radius: 8px;
            }
            QMenu::item:selected {
                background-color: rgba(45, 140, 255, 0.25);
            }
            """
        )

        if section in ("both", "icon"):
            icons_menu = menu.addMenu("Icon")
            for icon_key in BEATNOTE_ICON_OPTIONS:
                action = icons_menu.addAction(self._icon_qicon(icon_key), BEATNOTE_ICON_LABELS.get(icon_key, icon_key.title()))
                action.setCheckable(True)
                action.setChecked(note.icon == icon_key)
                action.triggered.connect(
                    lambda _checked=False, selected_icon=icon_key, current_color=note.color: self._apply_note_style(
                        note_id, selected_icon, current_color
                    )
                )

        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _apply_note_style(self, note_id: str, icon: str, color: str) -> None:
        try:
            updated = self.service.update(note_id, {"icon": icon, "color": color})
        except (BeatNoteServiceError, BeatNoteNotFoundError) as exc:
            self.show_toast(str(exc), error=True)
            return

        if self.current_note_id == note_id:
            self._loading_editor = True
            icon_index = self.editor_icon.findData(updated.icon)
            if icon_index >= 0:
                self.editor_icon.setCurrentIndex(icon_index)
            self._loading_editor = False

        self.reload_notes(select_note_id=note_id)
        self.notes_changed.emit()

    def _tree_tooltip(self, note: BeatNote) -> str:
        tags = ", ".join(note.tags) if note.tags else "No tags"
        return f"{category_label(note.category)}\n{tags}\nUpdated {self._format_timestamp(note.updatedAt)}"

    def _select_tree_note(self, note_id: str | None) -> bool:
        if not note_id:
            return False

        for root_index in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(root_index)
            for child_index in range(root.childCount()):
                child = root.child(child_index)
                if child.data(0, Qt.ItemDataRole.UserRole) != note_id:
                    continue
                category = root.data(0, Qt.ItemDataRole.UserRole + 1)
                root.setExpanded(True)
                if category:
                    self._category_expansion_state[str(category)] = True
                self._set_category_item_label(root, expanded=True)
                self._selection_guard = True
                self.tree.setCurrentItem(child)
                self._selection_guard = False
                self._refresh_tree_item_styles()
                return True
        return False

    def _find_note(self, note_id: str | None) -> BeatNote | None:
        return next((note for note in self.notes if note.id == note_id), None)

    def _load_note(self, note_id: str) -> None:
        note = self._find_note(note_id)
        if note is None:
            self.current_note_id = None
            self._show_empty_state(
                title="This BeatNote no longer exists",
                body="It may have been removed from another action. Reloading the notebook helps resync the tree.",
                action_text="Reload notebook",
            )
            try:
                self.empty_action.clicked.disconnect()
            except TypeError:
                pass
            self.empty_action.clicked.connect(self.reload_notes)
            return

        self._loading_editor = True
        self.current_note_id = note.id
        self.editor_title.setText(note.title)
        self.editor_category.setCurrentIndex(max(0, self.editor_category.findData(note.category)))
        self.editor_tags.setText(", ".join(note.tags))
        icon_index = self.editor_icon.findData(note.icon)
        self.editor_icon.setCurrentIndex(icon_index if icon_index >= 0 else 0)
        self.editor_pinned.setChecked(note.pinned)
        if "<" in note.content and ">" in note.content:
            self.content_edit.setHtml(note.content)
        else:
            self.content_edit.setPlainText(note.content)
        self.updated_label.setText(f"Updated {self._format_timestamp(note.updatedAt)}")
        self._loading_editor = False
        self._sync_format_controls()
        self._show_editor()
        self._set_editor_snapshot()

    def _clear_editor_for_draft(self) -> None:
        self._loading_editor = True
        self.current_note_id = None
        self.editor_title.clear()
        self.editor_category.setCurrentIndex(0)
        self.editor_tags.clear()
        default_icon_index = self.editor_icon.findData(DEFAULT_NOTE_ICON)
        self.editor_icon.setCurrentIndex(default_icon_index if default_icon_index >= 0 else 0)
        self.editor_pinned.setChecked(False)
        self.content_edit.clear()
        self.updated_label.setText("Unsaved note")
        self._loading_editor = False
        self._sync_format_controls()
        self._show_editor()
        self._set_editor_snapshot()
        self._update_editor_buttons()

    def _format_timestamp(self, timestamp: str) -> str:
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return parsed.astimezone().strftime("%d %b %Y • %H:%M")
        except ValueError:
            return timestamp

    def _prompt_unsaved_changes(self) -> bool:
        if not self.has_unsaved_editor_changes():
            return True

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Unsaved BeatNote")
        dialog.setText("Save your changes before leaving this note?")
        save_button = dialog.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard_button = dialog.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked is save_button:
            return self.save_current_note()
        if clicked is discard_button:
            return True
        return False

    def _on_tree_current_item_changed(self, current, previous) -> None:
        if self._selection_guard:
            return

        self._refresh_tree_item_styles()

        new_id = current.data(0, Qt.ItemDataRole.UserRole) if current is not None else None
        if new_id is None:
            return
        if new_id == self.current_note_id:
            return

        if not self._prompt_unsaved_changes():
            self._selection_guard = True
            self.tree.setCurrentItem(previous)
            self._selection_guard = False
            return

        self._load_note(new_id)

    def start_new_note(self) -> None:
        if not self._prompt_unsaved_changes():
            return
        self._clear_editor_for_draft()
        self.editor_title.setFocus()

    def _current_payload(self) -> dict[str, Any]:
        return {
            "title": self.editor_title.text(),
            "content": self.content_edit.toHtml(),
            "category": self.editor_category.currentData(),
            "tags": self.editor_tags.text(),
            "icon": self.editor_icon.currentData(),
            "color": DEFAULT_NOTE_COLOR,
            "pinned": self.editor_pinned.isChecked(),
        }

    def save_current_note(self) -> bool:
        payload = self._current_payload()
        try:
            if self.current_note_id is None:
                created = self.service.create(payload)
                self.show_toast(f"Created '{created.title}'.")
                self.reload_notes(select_note_id=created.id)
            else:
                updated = self.service.update(self.current_note_id, payload)
                self.show_toast(f"Saved '{updated.title}'.")
                self.reload_notes(select_note_id=updated.id)
        except (BeatNoteServiceError, BeatNoteNotFoundError) as exc:
            self.show_toast(str(exc), error=True)
            return False

        self.notes_changed.emit()
        return True

    def delete_current_note(self) -> None:
        if self.current_note_id is None:
            self._clear_editor_for_draft()
            return

        reply = QMessageBox.question(
            self,
            "Delete BeatNote",
            "Delete this BeatNote?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = self.service.delete(self.current_note_id)
        except (BeatNoteServiceError, BeatNoteNotFoundError) as exc:
            self.show_toast(str(exc), error=True)
            return

        self.current_note_id = None
        self.show_toast(f"Deleted '{deleted.title}'.")
        self.reload_notes()
        self.notes_changed.emit()

    def duplicate_current_note(self) -> None:
        if self.current_note_id is None:
            return
        try:
            duplicate = self.service.duplicate(self.current_note_id)
        except (BeatNoteServiceError, BeatNoteNotFoundError) as exc:
            self.show_toast(str(exc), error=True)
            return

        self.show_toast(f"Duplicated '{duplicate.title}'.")
        self.reload_notes(select_note_id=duplicate.id)
        self.notes_changed.emit()

    def export_notes_payload(self) -> list[dict[str, Any]]:
        return self.service.export_notes()

    def import_notes_payload(self, notes_payload: list[dict[str, Any]], *, replace: bool = True) -> None:
        try:
            imported = self.service.import_notes(notes_payload, replace=replace)
        except BeatNoteServiceError as exc:
            self.show_toast(str(exc), error=True)
            return

        self.show_toast(f"Imported {len(imported)} BeatNotes.")
        self.reload_notes(select_note_id=imported[0].id if imported else None)
        self.notes_changed.emit()

    def expand_all(self) -> None:
        self.tree.expandAll()

    def collapse_all(self) -> None:
        self.tree.collapseAll()
