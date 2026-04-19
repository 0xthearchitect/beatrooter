import math
from PyQt6.QtWidgets import QGraphicsPathItem, QMenu, QGraphicsSimpleTextItem, QApplication
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPainter, QAction, QBrush, QFont, QPolygonF

class DynamicEdge(QGraphicsPathItem):
    EDGE_RENDER_STYLES = {
        "signal_flow": {
            "label": "Signal Flow",
            "pen_style": Qt.PenStyle.SolidLine,
            "dash_pattern": None,
            "line_width": 2.15,
            "glow_width": 4.8,
        },
        "classic_dashed": {
            "label": "Classic Dashed",
            "pen_style": Qt.PenStyle.DashLine,
            "dash_pattern": [5.0, 3.0],
            "line_width": 2.1,
            "glow_width": 4.8,
        },
        "soft_link": {
            "label": "Soft Link",
            "pen_style": Qt.PenStyle.SolidLine,
            "dash_pattern": None,
            "line_width": 1.8,
            "glow_width": 4.0,
        },
        "soft_dashed": {
            "label": "Soft Dashed",
            "pen_style": Qt.PenStyle.DashLine,
            "dash_pattern": [3.4, 2.4],
            "line_width": 1.85,
            "glow_width": 4.1,
        },
        "accent_arc": {
            "label": "Accent Arc",
            "pen_style": Qt.PenStyle.SolidLine,
            "dash_pattern": None,
            "line_width": 2.35,
            "glow_width": 5.2,
        },
    }

    def __init__(self, source_node, target_node, edge_data=None):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.edge_data = edge_data or {}
        
        self.setZValue(-1)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsFocusable, True)
        
        self.normal_color = QColor(198, 144, 170, 242)
        self.hover_color = QColor(231, 184, 206, 255)
        self.selected_color = QColor(167, 132, 255, 255)
        self.glow_color = QColor(24, 16, 23, 218)
        
        self.current_color = self.normal_color
        self._hovered = False
        self.render_style_key = self.normalize_render_style(self._edge_style_from_data())
        
        self.label_text = QGraphicsSimpleTextItem()
        self.label_text.setFont(QFont("Consolas", 10, QFont.Weight.DemiBold))
        self.label_text.setBrush(QBrush(QColor(255, 241, 247)))
        self.label_text.setZValue(0.2)
        self.label_text.setVisible(False)

        self.label_bg = QGraphicsPathItem()
        self.label_bg.setPen(QPen(QColor(164, 103, 131, 210), 1.0))
        self.label_bg.setBrush(QBrush(QColor(41, 41, 41, 238)))
        self.label_bg.setZValue(0.1)
        self.label_bg.setVisible(False)
        
        if hasattr(self.source_node, 'positionChanged'):
            self.source_node.positionChanged.connect(self.update_path)
        if hasattr(self.target_node, 'positionChanged'):
            self.target_node.positionChanged.connect(self.update_path)
        
        self.update_path()
        self.update_label()

    @classmethod
    def normalize_render_style(cls, style_key):
        normalized = str(style_key or "").strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in cls.EDGE_RENDER_STYLES:
            return normalized
        return "signal_flow"

    @classmethod
    def render_style_options(cls):
        return {
            style_key: style_data["label"]
            for style_key, style_data in cls.EDGE_RENDER_STYLES.items()
        }

    def _edge_style_from_data(self):
        legacy_style = str(getattr(self.edge_data, "style", "") or "").strip().lower()
        legacy_map = {
            "dashed": "classic_dashed",
            "dotted": "soft_dashed",
            "solid": "signal_flow",
            "dash_dot": "accent_arc",
        }
        return legacy_map.get(legacy_style, legacy_style or "signal_flow")

    def set_render_style(self, style_key):
        self.render_style_key = self.normalize_render_style(style_key)
        self.update()

    def _current_render_style(self):
        return self.EDGE_RENDER_STYLES[self.render_style_key]

    def _ensure_label_items_in_scene(self):
        scene = self.scene()
        if scene is None:
            return
        if self.label_bg.scene() is not scene:
            scene.addItem(self.label_bg)
        if self.label_text.scene() is not scene:
            scene.addItem(self.label_text)

    def dispose(self):
        for item in (self.label_bg, self.label_text):
            scene = item.scene()
            if scene is not None:
                scene.removeItem(item)
    
    def itemChange(self, change, value):
        result = super().itemChange(change, value)
        if change == QGraphicsPathItem.GraphicsItemChange.ItemSceneHasChanged:
            if self.scene() is None:
                self.dispose()
            else:
                self._ensure_label_items_in_scene()
                self.update_label_position()
        return result
        
    def update_path(self):
        if not self.source_node or not self.target_node:
            return

        start_point = self.get_node_output_point(self.source_node)
        end_point = self.get_node_input_point(self.target_node)
        shared_stacker_rect = self._shared_parent_stacker_rect()
        
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        path = QPainterPath()
        path.moveTo(start_point)

        if dx >= 80.0 and abs(dy) <= 18.0:
            path.lineTo(end_point)
        elif dx >= 36.0:
            control_offset_x = max(56.0, abs(dx) * 0.34)
            vertical_bias = min(42.0, abs(dy) * 0.16)
            ctrl1 = QPointF(start_point.x() + control_offset_x, start_point.y() + vertical_bias)
            ctrl2 = QPointF(end_point.x() - control_offset_x, end_point.y() - vertical_bias)
            path.cubicTo(ctrl1, ctrl2, end_point)
        else:
            lane_offset = max(42.0, min(92.0, abs(dy) * 0.35 + 46.0))
            lane_y = max(start_point.y(), end_point.y()) + lane_offset
            exit_x = start_point.x() + 34.0
            entry_x = end_point.x() - 34.0
            radius = 14.0

            if shared_stacker_rect is not None:
                lane_y = self._fit_lane_y_inside_stacker(
                    lane_y,
                    start_point,
                    end_point,
                    shared_stacker_rect,
                )
                exit_x, entry_x = self._fit_lane_x_inside_stacker(
                    exit_x,
                    entry_x,
                    shared_stacker_rect,
                )

            self._line_to(path, QPointF(exit_x - radius, start_point.y()))
            self._quad_to(path, QPointF(exit_x, start_point.y()), QPointF(exit_x, start_point.y() + radius))
            self._line_to(path, QPointF(exit_x, lane_y - radius))
            self._quad_to(path, QPointF(exit_x, lane_y), QPointF(exit_x - radius, lane_y))
            self._line_to(path, QPointF(entry_x + radius, lane_y))
            self._quad_to(path, QPointF(entry_x, lane_y), QPointF(entry_x, lane_y - radius))
            self._line_to(path, QPointF(entry_x, end_point.y() + radius))
            self._quad_to(path, QPointF(entry_x, end_point.y()), QPointF(entry_x + radius, end_point.y()))
            self._line_to(path, end_point)
        
        self.setPath(path)
        self._ensure_label_items_in_scene()
        self.update_label_position()
        self.update()

    def _shared_parent_stacker_rect(self):
        source_parent = self._node_parent_stacker_id(self.source_node)
        target_parent = self._node_parent_stacker_id(self.target_node)
        if not source_parent or source_parent != target_parent:
            return None

        scene = self.scene()
        if scene is None:
            return None

        for item in scene.items():
            if str(getattr(item, "stacker_id", "") or "").strip() != source_parent:
                continue
            item_rect = item.sceneBoundingRect()
            if item_rect.isNull() or item_rect.isEmpty():
                continue
            return item_rect

        return None

    def _node_parent_stacker_id(self, widget):
        node = getattr(widget, "node", None)
        if node is None:
            return ""
        data = getattr(node, "data", {}) or {}
        return str(data.get("parent_stacker_id", "") or "").strip()

    def _fit_lane_y_inside_stacker(self, lane_y, start_point, end_point, stacker_rect):
        header_clearance = 38.0
        bottom_clearance = 16.0
        top_limit = float(stacker_rect.top() + header_clearance)
        bottom_limit = float(stacker_rect.bottom() - bottom_clearance)

        if bottom_limit <= top_limit + 10.0:
            return lane_y

        # Prefer a path beneath both node bodies (not just anchor points).
        source_rect = self._scene_rect_for_widget(self.source_node)
        target_rect = self._scene_rect_for_widget(self.target_node)
        source_bottom = float(source_rect.bottom()) if source_rect is not None else float(start_point.y())
        target_bottom = float(target_rect.bottom()) if target_rect is not None else float(end_point.y())

        preferred = max(source_bottom, target_bottom) + 16.0
        preferred = max(preferred, top_limit)
        preferred = min(preferred, bottom_limit)

        return preferred

    def _scene_rect_for_widget(self, widget):
        if widget is None:
            return None
        try:
            rect = widget.sceneBoundingRect()
        except Exception:
            return None
        if rect.isNull() or rect.isEmpty():
            return None
        return rect

    def _fit_lane_x_inside_stacker(self, exit_x, entry_x, stacker_rect):
        side_clearance = 22.0
        left_limit = float(stacker_rect.left() + side_clearance)
        right_limit = float(stacker_rect.right() - side_clearance)

        if right_limit <= left_limit + 12.0:
            return exit_x, entry_x

        clamped_exit = max(left_limit, min(float(exit_x), right_limit))
        clamped_entry = max(left_limit, min(float(entry_x), right_limit))

        return clamped_exit, clamped_entry

    def _line_to(self, path: QPainterPath, point: QPointF):
        path.lineTo(point)

    def _quad_to(self, path: QPainterPath, control: QPointF, end: QPointF):
        path.quadTo(control, end)
    
    def update_label(self):
        if self.edge_data:
            label = self.edge_data.label
            
            if label and label.strip() and label != "Connected":
                self.label_text.setText(label)
                self.label_text.setVisible(True)
                self.label_bg.setVisible(True)
                self.update_label_position()
            else:
                self.label_text.setVisible(False)
                self.label_bg.setVisible(False)
    
    def update_label_position(self):
        if self.path().elementCount() > 0 and self.label_text.isVisible():
            path = self.path()
            point_at_50 = path.pointAtPercent(0.5)
            text_rect = self.label_text.boundingRect()
            padding_x = 7.0
            padding_y = 3.0
            bg_rect = QRectF(
                point_at_50.x() - (text_rect.width() / 2) - padding_x,
                point_at_50.y() - (text_rect.height() / 2) - padding_y,
                text_rect.width() + (padding_x * 2),
                text_rect.height() + (padding_y * 2),
            )

            bg_path = QPainterPath()
            bg_path.addRoundedRect(bg_rect, 6, 6)
            self.label_bg.setPath(bg_path)
            self.label_bg.setPos(0.0, 0.0)
            self.label_text.setPos(
                point_at_50.x() - (text_rect.width() / 2),
                point_at_50.y() - (text_rect.height() / 2),
            )

    def set_content_visible(self, visible: bool):
        visible = bool(visible)
        self.setVisible(visible)
        if not visible:
            self.label_text.setVisible(False)
            self.label_bg.setVisible(False)
            return
        self.update_label()

    def get_node_output_point(self, node_widget):
        if hasattr(node_widget, 'get_output_connection_point'):
            local_point = node_widget.get_output_connection_point()
            return node_widget.mapToScene(local_point)
        else:
            node_rect = node_widget.boundingRect()
            scene_pos = node_widget.scenePos()
            return QPointF(
                scene_pos.x() + node_rect.width(),
                scene_pos.y() + node_rect.height()/2
            )

    def get_node_input_point(self, node_widget):
        if hasattr(node_widget, 'get_input_connection_point'):
            local_point = node_widget.get_input_connection_point()
            return node_widget.mapToScene(local_point)
        else:
            node_rect = node_widget.boundingRect()
            scene_pos = node_widget.scenePos()
            return QPointF(
                scene_pos.x(),
                scene_pos.y() + node_rect.height()/2
            )

    def hoverEnterEvent(self, event):
        self.current_color = self.hover_color
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        if self.isSelected():
            self.current_color = self.selected_color
        else:
            self.current_color = self.normal_color
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self.isSelected():
            pen_color = self.selected_color
        else:
            pen_color = self.current_color

        solid_pen_color = QColor(pen_color)
        solid_pen_color.setAlpha(max(238, solid_pen_color.alpha()))

        path = self.path()
        style_data = self._current_render_style()
        line_width = float(style_data["line_width"]) + (0.35 if self._hovered else 0.0)
        glow_width = float(style_data["glow_width"]) + (0.35 if self._hovered else 0.0)
        if self.isSelected():
            glow_width += 0.8

        glow_pen = QPen(self.glow_color)
        glow_pen.setWidthF(glow_width)
        glow_pen.setStyle(Qt.PenStyle.SolidLine)
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(glow_pen)
        painter.drawPath(path)

        pen = QPen(solid_pen_color)
        pen.setWidthF(line_width)
        pen.setStyle(style_data["pen_style"])
        dash_pattern = style_data.get("dash_pattern")
        if dash_pattern:
            pen.setDashPattern(dash_pattern)
            
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

        inner_pen = QPen(QColor(255, 243, 248, 108 if not self._hovered else 132))
        inner_pen.setWidthF(max(0.75, line_width * 0.32))
        inner_pen.setStyle(Qt.PenStyle.SolidLine)
        inner_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        inner_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(inner_pen)
        painter.drawPath(path)
        self._draw_direction_arrow(painter, solid_pen_color, line_width)

    def _draw_direction_arrow(self, painter: QPainter, pen_color: QColor, line_width: float):
        path = self.path()
        if path.elementCount() < 2:
            return

        tip_percent = 1.0
        base_percent = 0.93
        try:
            total_length = float(path.length())
        except Exception:
            total_length = 0.0

        if total_length > 1.0:
            base_offset = min(max(16.0, line_width * 7.0), total_length * 0.42)
            base_percent = float(path.percentAtLength(max(0.0, total_length - base_offset)))

        if base_percent >= tip_percent:
            base_percent = max(0.0, tip_percent - 0.07)
        base_percent = min(0.985, max(0.02, base_percent))

        tip = path.pointAtPercent(tip_percent)
        base = path.pointAtPercent(base_percent)
        vector = QPointF(tip.x() - base.x(), tip.y() - base.y())
        length = (vector.x() ** 2 + vector.y() ** 2) ** 0.5

        if length < 0.001:
            try:
                angle_degrees = float(path.angleAtPercent(0.995))
                angle_radians = angle_degrees * 3.141592653589793 / 180.0
                unit_x = math.cos(angle_radians)
                unit_y = -math.sin(angle_radians)
            except Exception:
                return
        else:
            unit_x = vector.x() / length
            unit_y = vector.y() / length

        perp_x = -unit_y
        perp_y = unit_x

        arrow_length = max(10.5, line_width * 5.1)
        arrow_half_width = max(4.4, line_width * 2.35)
        back_point = QPointF(tip.x() - unit_x * arrow_length, tip.y() - unit_y * arrow_length)

        arrow = QPolygonF(
            [
                tip,
                QPointF(back_point.x() + perp_x * arrow_half_width, back_point.y() + perp_y * arrow_half_width),
                QPointF(back_point.x() - perp_x * arrow_half_width, back_point.y() - perp_y * arrow_half_width),
            ]
        )

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(pen_color)))
        painter.drawPolygon(arrow)
        painter.restore()
    
    def edit_edge(self):
        if not self.edge_data:
            return
            
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit
        
        dialog = QDialog()
        dialog.setWindowTitle("Edit Connection")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0f1a2b;
                color: #d0dced;
                font-family: 'Consolas';
            }
            QLabel {
                color: #78a9e8;
                font-weight: bold;
                font-size: 12px;
                margin-bottom: 5px;
            }
            QLineEdit, QTextEdit {
                background-color: #12233a;
                color: #d0dced;
                border: 1px solid #2f4666;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                selection-background-color: #4f77a9;
                selection-color: #d0dced;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4f77a9;
                background-color: #162a45;
            }
            QPushButton {
                background-color: #17253b;
                color: #d0dced;
                border: 1px solid #2f4666;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #213550;
                border: 1px solid #4f77a9;
                color: #e2edfb;
            }
            QPushButton#saveButton {
                background-color: #22456f;
                color: #e2edfb;
                border: 1px solid #4f77a9;
            }
            QPushButton#saveButton:hover {
                background-color: #2a5588;
                border: 1px solid #6e9ad3;
            }
            QPushButton#cancelButton {
                background-color: #17253b;
                color: #d0dced;
            }
            QPushButton#cancelButton:hover {
                background-color: #213550;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header_label = QLabel("EDIT CONNECTION")
        header_label.setStyleSheet("""
            QLabel {
                color: #78a9e8;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #13243b;
                border: 1px solid #2f4666;
                border-radius: 6px;
                margin-bottom: 15px;
            }
        """)
        layout.addWidget(header_label)
        
        # Connection info
        info_layout = QHBoxLayout()
        source_label = QLabel(f"From: {self.edge_data.source_id}")
        target_label = QLabel(f"To: {self.edge_data.target_id}")
        
        for label in [source_label, target_label]:
            label.setStyleSheet("""
                QLabel {
                    color: #9fb5d4;
                    font-size: 10px;
                    background-color: #13243b;
                    border: 1px solid #2f4666;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
            """)
        
        info_layout.addWidget(source_label)
        info_layout.addWidget(target_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        layout.addWidget(QLabel("Connection Label:"))
        label_input = QLineEdit(self.edge_data.label if self.edge_data.label != "Connected" else "")
        label_input.setPlaceholderText("Enter connection description...")
        layout.addWidget(label_input)
        
        layout.addWidget(QLabel("Description (optional):"))
        desc_input = QTextEdit()
        desc_input.setMaximumHeight(80)
        desc_input.setPlainText(self.edge_data.description if hasattr(self.edge_data, 'description') else "")
        desc_input.setPlaceholderText("Add detailed description...")
        layout.addWidget(desc_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.setObjectName("saveButton")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelButton")
        
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)
        
        label_input.setFocus()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_label = label_input.text().strip()
            new_description = desc_input.toPlainText().strip()
            
            # MODIFICAÇÃO: Permite label vazio
            self.edge_data.label = new_label
            if hasattr(self.edge_data, 'description'):
                self.edge_data.description = new_description
            
            self.update_label()
            self.call_main_window_method('on_edge_updated', self.edge_data)
    
    def delete_edge(self):
        if self.edge_data:
            self.call_main_window_method('on_edge_deleted', self.edge_data)

    def debug_context_menu(self):
        """Método para debug do menu de contexto"""
        print("=== DEBUG Context Menu ===")
        print(f"Edge ID: {self.edge_data.id if self.edge_data else 'None'}")
        print(f"Source: {self.edge_data.source_id if self.edge_data else 'None'}")
        print(f"Target: {self.edge_data.target_id if self.edge_data else 'None'}")
        
        found = False
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'on_edge_deleted'):
                print(f"Found main window: {widget}")
                found = True
                break
        
        if not found:
            print("ERROR: Could not find main window!")
        
        print("========================")
    
    def call_main_window_method(self, method_name, *args):
        """Encontra a main window e chama um método nela"""
        main_window = None
        
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, method_name):
                main_window = widget
                break
        
        if not main_window:
            parent = self.parent()
            while parent:
                if hasattr(parent, method_name):
                    main_window = parent
                    break
                parent = parent.parent()
        
        if not main_window and self.scene():
            views = self.scene().views()
            if views:
                parent = views[0].parent()
                while parent:
                    if hasattr(parent, method_name):
                        main_window = parent
                        break
                    parent = parent.parent()
        
        if main_window and hasattr(main_window, method_name):
            method = getattr(main_window, method_name)
            method(*args)
            return True
        
        print(f"Warning: Could not find main window with method {method_name}")
        return False
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            print(f"Double click detected on edge: {self.edge_data.id}")
            self.show_context_menu(event.screenPos())
        else:
            super().mouseDoubleClickEvent(event)

    def show_context_menu(self, screen_pos):
        print(f"Showing context menu for edge: {self.edge_data.id if self.edge_data else 'Unknown'}")
        
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1f2c;
                color: #d0d0d0;
                border: 2px solid #32384a;
                font-family: 'Consolas';
                font-size: 10px;
            }
            QMenu::item {
                padding: 6px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #2a5a8c;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #32384a;
            }
        """)
        
        edit_action = QAction("✎ EDIT EDGE", menu)
        edit_action.triggered.connect(self.edit_edge)
        menu.addAction(edit_action)
        
        delete_action = QAction("🗑 DELETE EDGE", menu)
        delete_action.triggered.connect(self.delete_edge)
        menu.addAction(delete_action)
        
        menu.exec(screen_pos)

    def contextMenuEvent(self, event):
        print(f"Right-click context menu on edge: {self.edge_data.id}")
        self.show_context_menu(event.screenPos())
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            print(f"Right click detected on edge: {self.edge_data.id}")
            self.setSelected(True)
            self.show_context_menu(event.screenPos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            print(f"Right click released on edge: {self.edge_data.id}")
            event.accept()
        else:
            super().mouseReleaseEvent(event)
