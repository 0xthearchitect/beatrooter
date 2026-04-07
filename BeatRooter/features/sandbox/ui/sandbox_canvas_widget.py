from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QInputDialog
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QLineF
from PyQt6.QtGui import QPainter, QPen, QColor, QAction, QFont, QBrush
from models.object_model import SandboxObject, ObjectType
from features.sandbox.ui.sandbox_object_widget import SandboxObjectWidget
from features.sandbox.ui.sandbox_connection import SandboxConnection
from models.object_model import SandboxObject, ObjectType, ObjectCategory

class SandboxCanvasWidget(QGraphicsView):
    object_created = pyqtSignal(object)
    connection_requested = pyqtSignal(str, str)
    parent_child_requested = pyqtSignal(str, str)
    
    def __init__(self, sandbox_manager):
        super().__init__()
        self.sandbox_manager = sandbox_manager
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.connection_source = None
        self.parent_child_source = None
        self.temp_connection_line = None
        self.connection_mode = False
        self.parent_child_mode = False

        self.dragging_view = False
        self.last_drag_pos = QPointF()
        
        self.connection_items = {}
        
        self.grid_size = 50
        self.show_grid = True
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setMinimumSize(600, 400)
    
    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor(25, 25, 35))

        if self.show_grid:
            painter.setPen(QPen(QColor(50, 50, 60), 1))
            
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)
            right = int(rect.right())
            bottom = int(rect.bottom())
            
            for x in range(left, right, self.grid_size):
                painter.drawLine(x, top, x, bottom)
            for y in range(top, bottom, self.grid_size):
                painter.drawLine(left, y, right, y)
    
    def mousePressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.AltModifier and event.button() == Qt.MouseButton.LeftButton:
            self.dragging_view = True
            self.last_drag_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if not item:
                self.scene.clearSelection()
        
        if self.connection_mode and event.button() == Qt.MouseButton.LeftButton:
            self.handle_connection_click(event)
        elif self.parent_child_mode and event.button() == Qt.MouseButton.LeftButton:
            self.handle_parent_child_click(event)
        elif event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.pos())
            if item and isinstance(item, SandboxConnection):
                super().mousePressEvent(event)
            else:
                self.handle_right_click(event)
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.dragging_view:
            delta = event.pos() - self.last_drag_pos
            self.last_drag_pos = event.pos()
            
            h_scroll = self.horizontalScrollBar()
            v_scroll = self.verticalScrollBar()
            
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            
            event.accept()
            return
        
        if (self.connection_mode or self.parent_child_mode) and self.temp_connection_line:
            mouse_pos = self.mapToScene(event.pos())
            self.update_temp_connection(mouse_pos)
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging_view and event.button() == Qt.MouseButton.LeftButton:
            self.dragging_view = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            if not self.dragging_view:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        
        if event.key() == Qt.Key.Key_Escape and (self.connection_mode or self.parent_child_mode):
            self.cancel_interaction()
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            if not self.dragging_view:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().keyReleaseEvent(event)
    
    def add_object_widget(self, object_widget):
        self.scene.addItem(object_widget)
        object_widget.setPos(object_widget.object.position)
    
    def remove_object_widget(self, object_widget):
        self.remove_connections_for_object(object_widget.object.id)

        self.scene.removeItem(object_widget)
    
    def remove_connection_item(self, connection_id):
        if connection_id in self.connection_items:
            connection_item = self.connection_items[connection_id]
            self.scene.removeItem(connection_item)
            del self.connection_items[connection_id]
    
    def handle_right_click(self, event):
        item = self.itemAt(event.pos())
        
        if item and isinstance(item, SandboxObjectWidget):
            return super().mousePressEvent(event)
        else:
            scene_pos = self.mapToScene(event.pos())
            self.show_context_menu(scene_pos, event.pos())

    def start_connection(self, source_widget):
        print(f"Starting connection from {source_widget.object.name}")
        self.connection_source = source_widget
        self.connection_mode = True
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.temp_connection_line = SandboxConnection(source_widget, None, {})
        self.temp_connection_line.setPen(QPen(QColor(255, 255, 0), 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self.temp_connection_line)
        
        self.update_temp_connection(source_widget.scenePos())

    def start_parent_child(self, source_widget):
        print(f"Starting parent-child from {source_widget.object.name}")
        self.parent_child_source = source_widget
        self.parent_child_mode = True
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.temp_connection_line = SandboxConnection(source_widget, None, {})
        self.temp_connection_line.setPen(QPen(QColor(0, 255, 255), 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self.temp_connection_line)
        
        self.update_temp_connection(source_widget.scenePos())

    def handle_connection_click(self, event):
        print("Handling connection click")
        items = self.items(event.pos())
        for item in items:
            if isinstance(item, SandboxObjectWidget) and item != self.connection_source:
                print(f"Found target: {item.object.name}")
                self.finalize_connection(item)
                return
        
        print("No valid target found, cancelling")
        self.cancel_interaction()

    def handle_parent_child_click(self, event):
        print("Handling parent-child click")
        items = self.items(event.pos())
        for item in items:
            if isinstance(item, SandboxObjectWidget) and item != self.parent_child_source:
                print(f"Found child: {item.object.name}")
                self.finalize_parent_child(item)
                return
        
        print("No valid child found, cancelling")
        self.cancel_interaction()

    def finalize_connection(self, target_widget):
        print(f"Finalizing connection to {target_widget.object.name}")
        if self.connection_source and target_widget:
            try:
                self.connection_requested.emit(
                    self.connection_source.object.id, 
                    target_widget.object.id
                )
                print("Connection signal emitted")
            except Exception as e:
                print(f"Connection failed: {e}")
        
        self.cleanup_interaction_mode()

    def finalize_parent_child(self, target_widget):
        print(f"Finalizing parent-child with {target_widget.object.name}")
        if self.parent_child_source and target_widget:
            try:
                self.parent_child_requested.emit(
                    self.parent_child_source.object.id,
                    target_widget.object.id
                )
                print("Parent-child signal emitted")
            except Exception as e:
                print(f"Parent-child relationship failed: {e}")
        
        self.cleanup_interaction_mode()

    def update_temp_connection(self, mouse_pos):
        if self.temp_connection_line:
            source_widget = self.connection_source if self.connection_mode else self.parent_child_source
            if source_widget:
                source_pos = source_widget.get_connection_point(is_source=True)
                self.temp_connection_line.update_path(source_pos, mouse_pos)

    def cancel_interaction(self):
        self.cleanup_interaction_mode()
    
    def cleanup_interaction_mode(self):
        if self.temp_connection_line:
            self.scene.removeItem(self.temp_connection_line)
            self.temp_connection_line = None
        
        self.connection_source = None
        self.parent_child_source = None
        self.connection_mode = False
        self.parent_child_mode = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def show_context_menu(self, scene_pos, screen_pos):
        menu = QMenu(self)
        
        create_object_menu = menu.addMenu("Create Object")
        
        categories = [
            ("Operating Systems", ObjectCategory.OPERATING_SYSTEM),
            ("Network Devices", ObjectCategory.NETWORK),
            ("Web Technologies", ObjectCategory.WEB)
        ]
        
        for category_name, category_enum in categories:
            category_menu = create_object_menu.addMenu(category_name)
            object_types = SandboxObjectFactory.get_objects_by_category(category_enum)
            
            for obj_type in object_types:
                name = SandboxObjectFactory.get_object_name(obj_type)
                action = QAction(name, self)
                action.setData((obj_type, scene_pos))
                action.triggered.connect(self.create_object_from_context)
                category_menu.addAction(action)
        
        menu.exec(self.mapToGlobal(screen_pos))
        
    def create_object_from_context(self):
        action = self.sender()
        if action:
            obj_type, scene_pos = action.data()
            self.create_object_at_position(obj_type, scene_pos)
    
    def create_object_at_position(self, obj_type, scene_pos):
        from features.sandbox.core.sandbox_object_factory import SandboxObjectFactory
        obj = self.sandbox_manager.add_object(obj_type, scene_pos)
        self.object_created.emit(obj)
    
    def draw_connection(self, source_id, target_id, connection_id):
        print(f"DEBUG: Drawing connection - Source: {source_id}, Target: {target_id}, ID: {connection_id}")
        
        source_widget = self.find_object_widget(source_id)
        target_widget = self.find_object_widget(target_id)
        
        print(f"DEBUG: Source widget found: {source_widget is not None}")
        print(f"DEBUG: Target widget found: {target_widget is not None}")
        
        if source_widget and target_widget:
            connection_data = {
                'id': connection_id,
                'type': 'network',
                'color': '#3b82f6'
            }
            
            connection_item = SandboxConnection(source_widget, target_widget, connection_data)
            self.scene.addItem(connection_item)
            self.connection_items[connection_id] = connection_item
            
            connection_item.update_path()
            print(f"DEBUG: Connection drawn successfully: {source_id} -> {target_id}")
        else:
            print(f"DEBUG: Failed to draw connection - widgets not found")
        
    def find_object_widget(self, object_id):
        for item in self.scene.items():
            if isinstance(item, SandboxObjectWidget) and item.object.id == object_id:
                return item
        return None
    
    def wheelEvent(self, event):
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1/zoom_factor, 1/zoom_factor)

    def remove_connections_for_object(self, obj_id: str):
        connections_to_remove = []
        
        for connection_id, connection_item in self.connection_items.items():
            if (connection_item.source_widget and connection_item.source_widget.object.id == obj_id) or \
            (connection_item.target_widget and connection_item.target_widget.object.id == obj_id):
                connections_to_remove.append(connection_id)
        
        for connection_id in connections_to_remove:
            self.remove_connection_item(connection_id)