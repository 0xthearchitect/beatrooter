from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from features.tools.core.tool_node_service import ToolNodeService


class ToolNodeConfigDialog(QDialog):
    def __init__(self, node, parent=None):
        super().__init__(parent)
        self.node = node
        self.setWindowTitle(f"Configure {ToolNodeService.get_tool_display_name(node.data.get('tool_name', 'tool'))}")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        info_group = QGroupBox("Resolved Input")
        info_layout = QFormLayout(info_group)
        info_layout.setContentsMargins(10, 14, 10, 10)
        info_layout.setSpacing(8)

        resolved_target = str(self.node.data.get("resolved_target", "") or "").strip() or "-"
        source_label = str(self.node.data.get("target_source_label", "") or "").strip() or "-"
        compatibility_reason = str(self.node.data.get("compatibility_reason", "") or "").strip() or "-"

        resolved_label = QLabel(resolved_target)
        resolved_label.setWordWrap(True)
        source_value_label = QLabel(source_label)
        source_value_label.setWordWrap(True)
        info_layout.addRow("Target:", resolved_label)
        info_layout.addRow("Source:", source_value_label)
        reason_label = QLabel(compatibility_reason)
        reason_label.setWordWrap(True)
        info_layout.addRow("Status:", reason_label)
        root.addWidget(info_group)

        edit_group = QGroupBox("Advanced Options")
        edit_layout = QFormLayout(edit_group)
        edit_layout.setContentsMargins(10, 14, 10, 10)
        edit_layout.setSpacing(8)

        self.manual_target_input = QLineEdit()
        self.manual_target_input.setPlaceholderText("Optional override target")
        self.manual_target_input.setText(str(self.node.data.get("manual_target", "") or ""))
        edit_layout.addRow("Manual Target:", self.manual_target_input)

        self.options_input = QLineEdit()
        self.options_input.setPlaceholderText("CLI options, e.g. -sV -Pn")
        self.options_input.setText(str(self.node.data.get("options", "") or ""))
        edit_layout.addRow("Options:", self.options_input)

        self.custom_command_input = QLineEdit()
        self.custom_command_input.setPlaceholderText("Optional full custom command")
        self.custom_command_input.setText(str(self.node.data.get("custom_command", "") or ""))
        edit_layout.addRow("Custom Command:", self.custom_command_input)

        root.addWidget(edit_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_payload(self) -> dict:
        return {
            "manual_target": self.manual_target_input.text().strip(),
            "options": self.options_input.text().strip(),
            "custom_command": self.custom_command_input.text().strip(),
        }


class ToolNodeOutputDialog(QDialog):
    def __init__(self, node, output_text="", parent=None):
        super().__init__(parent)
        self.node = node
        self.output_text = output_text
        tool_name = ToolNodeService.get_tool_display_name(node.data.get("tool_name", "tool"))
        self.setWindowTitle(f"{tool_name} Output")
        self.resize(780, 520)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        summary_group = QGroupBox("Execution Summary")
        summary_layout = QFormLayout(summary_group)
        summary_layout.setContentsMargins(10, 14, 10, 10)
        summary_layout.setSpacing(8)
        summary_layout.addRow("Target:", QLabel(str(self.node.data.get("resolved_target", "") or "-")))
        summary_layout.addRow("Status:", QLabel(str(self.node.data.get("last_status", "") or "-").upper()))
        summary_layout.addRow("Run At:", QLabel(str(self.node.data.get("last_run_at", "") or "-")))
        command_label = QLabel(str(self.node.data.get("last_command", "") or "-"))
        command_label.setWordWrap(True)
        summary_layout.addRow("Command:", command_label)
        root.addWidget(summary_group)

        output_group = QGroupBox("Raw Output")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(10, 14, 10, 10)

        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setFont(QFont("Consolas", 9))
        output_text = str(self.output_text or self.node.data.get("last_output_preview", "") or self.node.data.get("last_error", "") or "")
        self.output_view.setPlainText(output_text if output_text else "No output recorded yet.")
        output_layout.addWidget(self.output_view)

        root.addWidget(output_group)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.accept)
        root.addWidget(buttons)
