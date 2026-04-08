from PyQt6.QtWidgets import QGraphicsPathItem, QMenu, QGraphicsSimpleTextItem, QApplication
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPainter, QAction, QBrush, QFont

class DynamicEdge(QGraphicsPathItem):
    EDGE_RENDER_STYLES = {
        "classic_dashed": {
            "label": "Classic Dashed",
            "pen_style": Qt.PenStyle.DashLine,
            "dash_pattern": [4.5, 3.0],
            "line_width": 2.35,
            "glow_width": 5.8,
        },
        "compact_dashed": {
            "label": "Compact Dashed",
            "pen_style": Qt.PenStyle.DashLine,
            "dash_pattern": [3.0, 2.1],
            "line_width": 2.2,
            "glow_width": 5.4,
        },
        "bold_dashed": {
            "label": "Bold Dashed",
            "pen_style": Qt.PenStyle.DashLine,
            "dash_pattern": [6.5, 3.2],
            "line_width": 2.55,
            "glow_width": 6.15,
        },
        "dotted": {
            "label": "Dotted",
            "pen_style": Qt.PenStyle.DotLine,
            "dash_pattern": None,
            "line_width": 2.15,
            "glow_width": 5.4,
        },
        "dash_dot": {
            "label": "Dash Dot",
            "pen_style": Qt.PenStyle.DashDotLine,
            "dash_pattern": [6.0, 2.8, 1.6, 2.8],
            "line_width": 2.3,
            "glow_width": 5.9,
        },
        "solid": {
            "label": "Solid",
            "pen_style": Qt.PenStyle.SolidLine,
            "dash_pattern": None,
            "line_width": 2.45,
            "glow_width": 6.0,
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
        
        self.normal_color = QColor(122, 168, 232, 225)
        self.hover_color = QColor(166, 206, 255, 245)
        self.selected_color = QColor(255, 152, 196, 250)
        self.glow_color = QColor(6, 12, 24, 210)
        
        self.current_color = self.normal_color
        self._hovered = False
        self.render_style_key = self.normalize_render_style(self._edge_style_from_data())
        
        self.label_text = QGraphicsSimpleTextItem()
        self.label_text.setFont(QFont("Consolas", 10, QFont.Weight.DemiBold))
        self.label_text.setBrush(QBrush(QColor(238, 245, 255)))
        self.label_text.setZValue(0.2)
        self.label_text.setVisible(False)

        self.label_bg = QGraphicsPathItem()
        self.label_bg.setPen(QPen(QColor(104, 150, 215, 210), 1.0))
        self.label_bg.setBrush(QBrush(QColor(10, 18, 31, 228)))
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
        return "classic_dashed"

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
            "dotted": "dotted",
            "solid": "solid",
            "dash_dot": "dash_dot",
        }
        return legacy_map.get(legacy_style, legacy_style or "classic_dashed")

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
        
        path = QPainterPath()
        path.moveTo(start_point)
        
        dx = end_point.x() - start_point.x()
        control_offset_x = max(70.0, abs(dx) * 0.45)
        if dx < 0:
            control_offset_x = -control_offset_x
        
        ctrl1 = QPointF(start_point.x() + control_offset_x, start_point.y())
        ctrl2 = QPointF(end_point.x() - control_offset_x, end_point.y())
        
        path.cubicTo(ctrl1, ctrl2, end_point)
        
        self.setPath(path)
        self._ensure_label_items_in_scene()
        self.update_label_position()
        self.update()
    
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

        path = self.path()
        style_data = self._current_render_style()
        line_width = float(style_data["line_width"]) + (0.45 if self._hovered else 0.0)
        glow_width = float(style_data["glow_width"]) + (0.45 if self._hovered else 0.0)
        if self.isSelected():
            glow_width += 1.0

        glow_pen = QPen(self.glow_color)
        glow_pen.setWidthF(glow_width)
        glow_pen.setStyle(Qt.PenStyle.SolidLine)
        glow_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        glow_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(glow_pen)
        painter.drawPath(path)

        pen = QPen(pen_color)
        pen.setWidthF(line_width)
        pen.setStyle(style_data["pen_style"])
        dash_pattern = style_data.get("dash_pattern")
        if dash_pattern:
            pen.setDashPattern(dash_pattern)
            
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
    
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
