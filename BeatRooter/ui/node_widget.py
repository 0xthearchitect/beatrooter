from PyQt6.QtWidgets import QGraphicsObject, QMenu
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QColor,
    QBrush,
    QFont,
    QFontMetrics,
    QAction,
)
from core.node_factory import NodeFactory


class NodeWidget(QGraphicsObject):
    node_updated = pyqtSignal(object)
    connection_started = pyqtSignal(object)
    positionChanged = pyqtSignal()
    node_deleted = pyqtSignal(object)

    def __init__(self, node, category=None):
        super().__init__()
        self.node = node
        self.category = category
        self.setPos(node.position)

        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.min_width = 164
        self.min_height = 78
        self.max_width = 360
        self.max_height = 420
        self.corner_radius = 3
        self.padding = 10
        self.title_height = 24
        self.line_height = 14
        self.port_radius = 3

        self.cyber_colors = {
            "panel_bg": QColor(16, 24, 36),
            "panel_bg_end": QColor(16, 24, 36),
            "panel_border": QColor(45, 62, 84),
            "text_primary": QColor(189, 203, 222),
            "text_secondary": QColor(125, 141, 165),
            "warning": QColor(216, 141, 108),
            "selection": QColor(108, 154, 220),
        }

        self.width = float(self.min_width)
        self.height = float(self.min_height)
        self._size_dirty = True
        self._cached_content_lines = []
        self._cached_header_text = ""

        self.calculate_size(force=True)
        self.setZValue(1)

    def calculate_size(self, force=False):
        if not force and not self._size_dirty:
            return

        content_lines = self.get_data_fields_to_display()
        self._cached_content_lines = content_lines
        self._cached_header_text = f"{self.get_node_symbol()} {self.get_node_display_name().upper()}"

        header_metrics = QFontMetrics(QFont("Consolas", 9, QFont.Weight.DemiBold))
        content_metrics = QFontMetrics(QFont("Consolas", 8))

        text_widths = [header_metrics.horizontalAdvance(self._cached_header_text)]
        text_widths.extend(content_metrics.horizontalAdvance(f"> {line}") for line in content_lines)
        max_text_width = max(text_widths) if text_widths else 0

        required_width = max_text_width + (self.padding * 2) + 8
        new_width = float(max(self.min_width, min(required_width, self.max_width)))

        content_height = self.title_height + (self.padding * 2) + (len(content_lines) * self.line_height)
        new_height = float(max(self.min_height, min(content_height, self.max_height)))

        if new_width != self.width or new_height != self.height:
            self.prepareGeometryChange()
            self.width = new_width
            self.height = new_height

        self._size_dirty = False

    def get_node_accent_color(self):
        return QColor(NodeFactory.get_node_color(self.node.type, self.category))

    def get_node_display_name(self):
        return NodeFactory.get_node_name(self.node.type, self.category)

    def get_node_symbol(self):
        return NodeFactory.get_node_symbol(self.node.type, self.category)

    def boundingRect(self):
        return QRectF(
            -self.width / 2 - self.port_radius,
            -self.height / 2,
            self.width + (self.port_radius * 2),
            self.height,
        )

    def paint(self, painter, option, widget):
        self.calculate_size()
        accent_color = self.get_node_accent_color()

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        main_rect = QRectF(-self.width / 2, -self.height / 2, self.width, self.height)
        header_rect = QRectF(-self.width / 2, -self.height / 2, self.width, self.title_height)

        painter.setBrush(QBrush(self.cyber_colors["panel_bg"]))
        painter.setPen(QPen(self.cyber_colors["panel_border"], 1.1))
        painter.drawRect(main_rect)

        header_color = QColor(accent_color)
        header_color.setAlpha(42)
        header_border = QColor(accent_color)
        header_border.setAlpha(145)

        painter.setBrush(QBrush(header_color))
        painter.setPen(QPen(header_border, 1.0))
        painter.drawRect(header_rect)

        painter.setPen(QPen(QColor(53, 70, 95), 1.0))
        painter.drawLine(
            QPointF(-self.width / 2, -self.height / 2 + self.title_height),
            QPointF(self.width / 2, -self.height / 2 + self.title_height),
        )

        self.draw_header_text(painter)
        self.draw_body_content(painter)
        self.draw_connection_ports(painter, accent_color)
        # Keep node cards visually minimal: no extra corner tag.

        if self.isSelected():
            selection_pen = QPen(self.cyber_colors["selection"], 1.0)
            selection_pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(selection_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(
                QRectF(
                    -self.width / 2 - 1,
                    -self.height / 2 - 1,
                    self.width + 2,
                    self.height + 2,
                )
            )

    def draw_header_text(self, painter):
        painter.setPen(QPen(QColor(203, 216, 236)))
        painter.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))

        metrics = painter.fontMetrics()
        elided = metrics.elidedText(
            self._cached_header_text,
            Qt.TextElideMode.ElideRight,
            int(self.width - self.padding * 2),
        )

        painter.drawText(
            int(-self.width / 2 + self.padding),
            int(-self.height / 2 + 15),
            elided,
        )

    def draw_body_content(self, painter):
        content_lines = self._cached_content_lines

        painter.setFont(QFont("Consolas", 8))
        max_width = int(self.width - (self.padding * 2))
        start_y = -self.height / 2 + self.title_height + self.padding + 2

        for i, line in enumerate(content_lines):
            y_pos = start_y + (i * self.line_height)
            if y_pos + self.line_height > self.height / 2 - self.padding:
                painter.setPen(QPen(self.cyber_colors["warning"]))
                painter.drawText(int(-self.width / 2 + self.padding), int(y_pos), "...")
                break

            prefix = "> " if i == 0 else "  "
            terminal_line = f"{prefix}{line}"
            painter.setPen(QPen(self.cyber_colors["text_secondary"]))
            elided_line = painter.fontMetrics().elidedText(
                terminal_line,
                Qt.TextElideMode.ElideRight,
                max_width,
            )
            painter.drawText(int(-self.width / 2 + self.padding), int(y_pos), elided_line)

    def draw_connection_ports(self, painter, accent_color):
        left_center = QPointF(-self.width / 2, 0)
        right_center = QPointF(self.width / 2, 0)

        port_fill = QColor(accent_color)
        port_fill.setAlpha(130)
        port_outline = QColor(accent_color)
        port_outline.setAlpha(165)

        painter.setPen(QPen(port_outline, 1.0))
        painter.setBrush(QBrush(port_fill))
        painter.drawEllipse(left_center, self.port_radius, self.port_radius)
        painter.drawEllipse(right_center, self.port_radius, self.port_radius)

    def get_input_connection_point(self):
        return QPointF(-self.width / 2, 0)

    def get_output_connection_point(self):
        return QPointF(self.width / 2, 0)

    def draw_corner_symbol(self, painter, accent_color):
        symbol = self.get_node_symbol()
        painter.setFont(QFont("Consolas", 7))
        metrics = painter.fontMetrics()

        color = QColor(accent_color)
        color.setAlpha(170)
        painter.setPen(QPen(color))
        painter.drawText(
            int(self.width / 2 - metrics.boundingRect(symbol).width() - 6),
            int(self.height / 2 - 6),
            symbol,
        )

    def get_data_fields_to_display(self):
        lines = self.get_all_possible_fields()
        max_lines = 6

        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append("...more")

        return lines

    def get_all_possible_fields(self):
        lines = []
        added_fields = set()

        def add_field(field_name, display_name=None, format_str="{}"):
            if field_name in self.node.data and self.node.data[field_name]:
                value = self.node.data[field_name]
                if value and str(value).strip() and str(value).strip() not in ["None", ""]:
                    display = display_name or field_name.replace("_", " ").title()
                    formatted_value = self._format_display_value(value, format_str)

                    if field_name == "compromised" and value:
                        lines.append("COMPROMISED")
                    elif field_name == "successful" and value:
                        lines.append("SUCCESSFUL")
                    elif field_name == "exploited" and value:
                        lines.append("EXPLOITED")
                    else:
                        if field_name not in added_fields:
                            lines.append(f"{display}: {formatted_value}")
                            added_fields.add(field_name)

        if self._add_flipper_priority_fields(add_field):
            for key, value in self.node.data.items():
                if (
                    key not in added_fields
                    and key not in self._flipper_generic_skip_fields()
                    and value
                    and str(value).strip()
                    and str(value).strip() not in ["None", ""]
                ):
                    display_name = key.replace("_", " ").title()
                    lines.append(f"{display_name}: {self._format_display_value(value)}")
                    added_fields.add(key)

            if not lines:
                lines.append(f"{self.get_node_display_name().upper()} Node")
            return lines

        if self.node.type == "analysis_environment":
            add_field("vm_name", "Vm Name")
            add_field("os_version", "Os Version")
            add_field("tools_installed", "Tools Installed")
            add_field("network_setup", "Network Setup")
            add_field("isolation_level", "Isolation Level")
        elif self.node.type == "malware_sample":
            add_field("sample_name", "Sample Name")
            add_field("file_type", "File Type")
            add_field("submission_source", "Submission Source")
            add_field("analysis_status", "Analysis Status")
        elif self.node.type == "behavior_analysis":
            add_field("process_activity", "Process Activity")
            add_field("network_connections", "Network Connections")
            add_field("file_system_changes", "File System Changes")
            add_field("registry_modifications", "Registry Modifications")
            add_field("persistence_mechanism", "Persistence Mechanism")
            add_field("anti_analysis_techniques", "Anti Analysis Techniques")

        for key, value in self.node.data.items():
            if (
                key not in added_fields
                and value
                and str(value).strip()
                and str(value).strip() not in ["None", ""]
            ):
                display_name = key.replace("_", " ").title()
                lines.append(f"{display_name}: {value}")
                added_fields.add(key)

        if not lines:
            lines.append(f"{self.get_node_display_name().upper()} Node")

        return lines

    def _format_display_value(self, value, format_str="{}"):
        if isinstance(value, (list, tuple, set)):
            joined = ", ".join(str(item) for item in value if str(item).strip())
            return format_str.format(joined)
        if isinstance(value, bool):
            return format_str.format("yes" if value else "no")
        return format_str.format(value)

    def _add_flipper_priority_fields(self, add_field):
        if not self.node.type.startswith("flipper_"):
            return False

        if self.node.type == "flipper_subghz_signal":
            add_field("frequency_mhz", "Frequency", "{:.3f} MHz")
            add_field("protocol", "Protocol")
            add_field("modulation", "Modulation")
            add_field("target_devices", "Targets")
            add_field("attack_surface", "Attack Surface")
            add_field("key_preview", "Key")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_badusb_script":
            add_field("script_type", "Script Type")
            add_field("objective", "Objective")
            add_field("target_os", "Target OS")
            add_field("command_count", "Commands")
            add_field("common_commands", "Common Cmds")
            add_field("binary_artifacts", "Binaries")
            add_field("external_urls", "URLs")
            add_field("script_preview", "Script")
            return True

        if self.node.type == "flipper_ir_signal":
            add_field("protocol", "Protocol")
            add_field("frequency_hz", "Frequency", "{} Hz")
            add_field("target_device_type", "Target Device")
            add_field("command", "Command")
            add_field("address", "Address")
            add_field("duty_cycle", "Duty Cycle")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_nfc_dump":
            add_field("technology", "Technology")
            add_field("protocol", "Protocol")
            add_field("frequency_khz", "Frequency", "{} kHz")
            add_field("uid", "UID")
            add_field("sak", "SAK")
            add_field("atqa", "ATQA")
            add_field("memory_layout", "Memory")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_rfid_dump":
            add_field("rfid_type", "RFID Type")
            add_field("frequency_khz", "Frequency", "{} kHz")
            add_field("key_value", "Key")
            add_field("bit_length", "Bits")
            add_field("facility_code", "Facility")
            add_field("card_id", "Card ID")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_ibutton_key":
            add_field("ibutton_type", "iButton Type")
            add_field("key_value", "Key")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_wifi_artifact":
            add_field("artifact_kind", "Artifact")
            add_field("attack_indicators", "Indicators")
            add_field("target_networks", "Targets")
            add_field("deauth_events", "Deauth")
            add_field("handshake_events", "Handshakes")
            add_field("attack_result", "Result")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_log_artifact":
            add_field("event_count", "Events")
            add_field("critical_events", "Critical")
            add_field("attack_indicators", "Indicators")
            add_field("attack_result", "Result")
            add_field("last_timestamp", "Last Seen")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_file":
            add_field("module", "Module")
            add_field("file_extension", "Extension")
            add_field("file_size_bytes", "Size", "{} B")
            add_field("parser_status", "Parser")
            add_field("content_preview", "Content")
            add_field("relative_path", "Path")
            return True

        add_field("module", "Module")
        add_field("file_name", "File")
        add_field("relative_path", "Path")
        return True

    def _flipper_generic_skip_fields(self):
        return {
            "title",
            "summary",
            "status",
            "severity",
            "confidence",
            "environment",
            "exposure",
            "data_classification",
            "notes",
            "scan_timestamp",
            "workspace_path",
        }

    def mouseDoubleClickEvent(self, event):
        self.node_updated.emit(self.node)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #141f31;
                color: #d4deec;
                border: 1px solid #2c3b52;
                font-family: 'Consolas';
                font-size: 10px;
            }
            QMenu::item {
                padding: 6px 18px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #2a3b56;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #2c3b52;
            }
            """
        )

        connect_action = QAction("Connect", self)
        connect_action.triggered.connect(lambda: self.connection_started.emit(self))
        menu.addAction(connect_action)

        menu.addSeparator()

        edit_action = QAction("Edit Node", self)
        edit_action.triggered.connect(lambda: self.node_updated.emit(self.node))
        menu.addAction(edit_action)

        delete_action = QAction("Delete Node", self)
        delete_action.triggered.connect(self.delete_node)
        menu.addAction(delete_action)

        menu.exec(event.screenPos())
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def delete_node(self):
        self.node_deleted.emit(self.node)

    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange and self.scene():
            self.node.position = value
            self.positionChanged.emit()
        return super().itemChange(change, value)

    def update_display(self):
        self._size_dirty = True
        self.calculate_size(force=True)
        self.update()
