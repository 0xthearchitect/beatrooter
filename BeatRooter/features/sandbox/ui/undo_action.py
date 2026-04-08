from PyQt6.QtGui import QAction, QKeySequence


class UndoActionHandler:
    def __init__(self, main_window):
        self.main_window = main_window
        self.actions = []

    def create_action(self, parent, include_shortcut=False):
        action = QAction("Undo", parent)
        if include_shortcut:
            action.setShortcut(QKeySequence.StandardKey.Undo)
        action.triggered.connect(self.trigger)
        action.setEnabled(False)
        self.actions.append(action)
        return action

    def refresh(self):
        is_enabled = (
            self.main_window.is_canvas_mode()
            and self.main_window.sandbox_manager.can_undo()
        )
        for action in self.actions:
            action.setEnabled(is_enabled)

    def trigger(self):
        if not self.main_window.is_canvas_mode():
            self.main_window.statusBar().showMessage(
                "Undo is not available in this workspace mode."
            )
            return

        if self.main_window.sandbox_manager.undo():
            self.main_window.refresh_canvas_from_environment()
            self.main_window.update_undo_redo_buttons()
            description = self.main_window.sandbox_manager.get_current_history_description()
            message = f"Undo: {description}" if description else "Undo completed."
            self.main_window.statusBar().showMessage(message)
