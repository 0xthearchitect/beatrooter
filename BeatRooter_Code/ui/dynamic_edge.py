from PyQt6.QtWidgets import QGraphicsPathItem, QMenu, QInputDialog, QGraphicsSimpleTextItem, QApplication
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPainter, QAction, QBrush, QFont
import math

class DynamicEdge(QGraphicsPathItem):
    def __init__(self, source_node, target_node, edge_data=None):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node
        self.edge_data = edge_data or {}
        
        self.setZValue(-1)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsFocusable, True)
        
        self.normal_color = QColor(0, 180, 255)
        self.hover_color = QColor(255, 200, 50)
        self.selected_color = QColor(255, 100, 100)
        
        self.current_color = self.normal_color
        self.line_width = 2
        
        # Label text - INÍCIO: definir como invisível
        self.label_text = QGraphicsSimpleTextItem(self)
        self.label_text.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.label_text.setBrush(QBrush(QColor(255, 255, 255)))
        self.label_text.setZValue(1)
        self.label_text.setVisible(False)  # INÍCIO: invisível por padrão
        
        if hasattr(self.source_node, 'positionChanged'):
            self.source_node.positionChanged.connect(self.update_path)
        if hasattr(self.target_node, 'positionChanged'):
            self.target_node.positionChanged.connect(self.update_path)
        
        self.update_path()
        self.update_label()
        
    def update_path(self):
        if not self.source_node or not self.target_node:
            return
            
        start_point = self.get_node_output_point(self.source_node)
        end_point = self.get_node_input_point(self.target_node)
        
        path = QPainterPath()
        path.moveTo(start_point)
        
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()
        
        control_offset_x = dx * 0.5
        
        ctrl1 = QPointF(start_point.x() + control_offset_x, start_point.y())
        ctrl2 = QPointF(end_point.x() - control_offset_x, end_point.y())
        
        path.cubicTo(ctrl1, ctrl2, end_point)
        
        self.setPath(path)
        self.update_label_position()
        self.update()
    
    def update_label(self):
        if self.edge_data:
            label = self.edge_data.label
            
            # MODIFICAÇÃO: Só mostra o label se não estiver vazio e não for "Connected"
            if label and label.strip() and label != "Connected":
                self.label_text.setText(label)
                self.label_text.setVisible(True)
                self.update_label_position()
            else:
                self.label_text.setVisible(False)
    
    def update_label_position(self):
        if self.path().elementCount() > 0 and self.label_text.isVisible():
            path = self.path()
            point_at_50 = path.pointAtPercent(0.5)
            self.label_text.setPos(point_at_50.x() - self.label_text.boundingRect().width()/2,
                                 point_at_50.y() - self.label_text.boundingRect().height()/2)

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
        self.line_width = 3
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        if self.isSelected():
            self.current_color = self.selected_color
        else:
            self.current_color = self.normal_color
        self.line_width = 2
        self.update()
        super().hoverLeaveEvent(event)
    
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self.isSelected():
            pen_color = self.selected_color
        else:
            pen_color = self.current_color

        pen = QPen(pen_color)
        pen.setWidth(self.line_width)
        
        if self.edge_data and self.edge_data.style == "dashed":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif self.edge_data and self.edge_data.style == "dotted":
            pen.setStyle(Qt.PenStyle.DotLine)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)
            
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        self.setPen(pen)
        super().paint(painter, option, widget)
    
    def edit_edge(self):
        if not self.edge_data:
            return
            
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit
        
        dialog = QDialog()
        dialog.setWindowTitle("Edit Connection")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1a1f2c;
                color: #d0d0d0;
                font-family: 'Segoe UI', 'Arial';
            }
            QLabel {
                color: #89b4fa;
                font-weight: bold;
                font-size: 12px;
                margin-bottom: 5px;
            }
            QLineEdit, QTextEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #89b4fa;
                background-color: #363646;
            }
            QPushButton {
                background-color: #585b70;
                color: #cdd6f4;
                border: 1px solid #6c7086;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #6c7086;
                border: 1px solid #89b4fa;
                color: #ffffff;
            }
            QPushButton#saveButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: 1px solid #89b4fa;
            }
            QPushButton#saveButton:hover {
                background-color: #a6c8ff;
                border: 1px solid #a6c8ff;
            }
            QPushButton#cancelButton {
                background-color: #585b70;
                color: #cdd6f4;
            }
            QPushButton#cancelButton:hover {
                background-color: #6c7086;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Header
        header_label = QLabel("EDIT CONNECTION")
        header_label.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                background-color: #2a2a3a;
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
                    color: #a6adc8;
                    font-size: 10px;
                    background-color: #2a2a3a;
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