from PyQt6.QtGui import QAction, QKeySequence


class RedoActionHandler:
    def __init__(self, main_window):
        self.main_window = main_window
        self.actions = []

    def create_action(self, parent, include_shortcut=False):
        action = QAction("Redo", parent)
        if include_shortcut:
            action.setShortcut(QKeySequence.StandardKey.Redo)
        action.triggered.connect(self.trigger)
        action.setEnabled(False)
        self.actions.append(action)
        return action

    def refresh(self):
        is_enabled = self.main_window.graph_manager.can_redo()
        for action in self.actions:
            action.setEnabled(is_enabled)

    def trigger(self):
        if self.main_window.graph_manager.redo():
            self.main_window.refresh_canvas_from_graph()
            self.main_window.update_undo_redo_buttons()
            description = self.main_window.graph_manager.get_current_history_description()
            message = f"Redo: {description}" if description else "Redo completed."
            self.main_window.statusBar().showMessage(message)
