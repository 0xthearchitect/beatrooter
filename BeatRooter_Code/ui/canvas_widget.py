from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QInputDialog, QGraphicsLineItem
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QLineF
from PyQt6.QtGui import QPainter, QPen, QColor, QAction, QFont, QBrush, QCursor
from models.node import Node
from models.edge import Edge
from ui.node_widget import NodeWidget
from ui.dynamic_edge import DynamicEdge

class CanvasWidget(QGraphicsView):
    node_selected = pyqtSignal(object)
    connection_requested = pyqtSignal(str, str)
    node_created = pyqtSignal(object)
    
    def __init__(self, graph_manager):
        super().__init__()
        self.graph_manager = graph_manager
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.connection_source = None
        self.temp_connection_line = None
        self.connection_mode = False

        self.dragging_view = False
        self.last_drag_pos = QPointF()
        
        self.edge_items = {}
        
        self.grid_size = 50
        self.show_grid = True
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setMinimumSize(600, 400)
    
    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor(30, 30, 40))

        if self.show_grid:
            painter.setPen(QPen(QColor(60, 60, 70), 1))
            
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
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if not item:
                self.scene.clearSelection()
        
        if self.connection_mode and event.button() == Qt.MouseButton.LeftButton:
            self.handle_connection_click(event)
        elif event.button() == Qt.MouseButton.RightButton:
            item = self.itemAt(event.pos())
            if item and isinstance(item, DynamicEdge):
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
        
        if self.connection_mode and self.temp_connection_line:
            mouse_pos = self.mapToScene(event.pos())
            self.update_temp_connection(mouse_pos)
        
        super().mouseMoveEvent(event)

    def update_node_display(self, node):
        for item in self.scene.items():
            if isinstance(item, NodeWidget) and item.node.id == node.id:
                item.update_display()
                break
    
    def mouseReleaseEvent(self, event):
        if self.dragging_view and event.button() == Qt.MouseButton.LeftButton:
            self.dragging_view = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            if not self.dragging_view:
                self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        
        if event.key() == Qt.Key.Key_Escape and self.connection_mode:
            self.cancel_connection()
        else:
            super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Alt:
            if not self.dragging_view:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        
        super().keyReleaseEvent(event)
    
    def add_node_widget(self, node_widget):
        self.scene.addItem(node_widget)
        node_widget.setPos(node_widget.node.position)
    
    def remove_node_widget(self, node_widget):
        self.scene.removeItem(node_widget)
    
    def remove_edge_item(self, edge_id):
        if edge_id in self.edge_items:
            edge_item = self.edge_items[edge_id]
            self.scene.removeItem(edge_item)
            del self.edge_items[edge_id]
    
    def handle_connection_click(self, event):
        items = self.items(event.pos())
        for item in items:
            if isinstance(item, NodeWidget) and item != self.connection_source:
                self.finalize_connection(item)
                return
        
        self.cancel_connection()
    
    def handle_right_click(self, event):
        item = self.itemAt(event.pos())
        
        if item and isinstance(item, NodeWidget):
            return super().mousePressEvent(event)
        else:
            scene_pos = self.mapToScene(event.pos())
            self.show_context_menu(scene_pos, event.pos())
    
    def start_connection(self, source_widget):
        self.connection_source = source_widget
        self.connection_mode = True
        
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.temp_connection_line = QGraphicsLineItem()
        self.temp_connection_line.setPen(QPen(QColor(255, 255, 0), 2, Qt.PenStyle.DashLine))
        self.scene.addItem(self.temp_connection_line)
        
        self.update_temp_connection(source_widget.scenePos())
    
    def update_temp_connection(self, mouse_pos):
        if self.temp_connection_line and self.connection_source:
            if hasattr(self.connection_source, 'get_output_connection_point'):
                source_local_point = self.connection_source.get_output_connection_point()
                source_pos = self.connection_source.mapToScene(source_local_point)
            else:
                source_rect = self.connection_source.boundingRect()
                source_pos = self.connection_source.scenePos() + QPointF(
                    source_rect.width(),
                    source_rect.height()/2
                )
            
            line = QLineF(source_pos, mouse_pos)
            self.temp_connection_line.setLine(line)

    def finalize_connection(self, target_widget):
        if self.connection_source and target_widget:
            try:
                edge = self.graph_manager.connect_nodes(
                    self.connection_source.node.id, 
                    target_widget.node.id, 
                    ""
                )

                self.connection_requested.emit(
                    self.connection_source.node.id, 
                    target_widget.node.id
                )
                
                self.draw_connection(edge)
                
            except ValueError as e:
                print(f"Connection failed: {e}")
        
        self.cleanup_connection_mode()

    def cancel_connection(self):
        self.cleanup_connection_mode()
    
    def cleanup_connection_mode(self):
        if self.temp_connection_line:
            self.scene.removeItem(self.temp_connection_line)
            self.temp_connection_line = None
        
        self.connection_source = None
        self.connection_mode = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def show_context_menu(self, scene_pos, screen_pos):
        menu = QMenu(self)
        
        create_node_menu = menu.addMenu("Create Node")
        
        node_types = [
            ("IP", "ip"),
            ("Domain", "domain"),
            ("User", "user"),
            ("Credential", "credential"),
            ("Attack", "attack"),
            ("Vulnerability", "vulnerability"),
            ("Host", "host"),
            ("Note", "note"),
            ("Screenshot", "screenshot"),
            ("Command", "command"),
            ("Script", "script")
        ]
        
        for name, node_type in node_types:
            action = QAction(name, self)
            action.setData((node_type, scene_pos))
            action.triggered.connect(self.create_node_from_context)
            create_node_menu.addAction(action)
        
        menu.exec(self.mapToGlobal(screen_pos))
    
    def create_node_from_context(self):
        action = self.sender()
        if action:
            node_type, scene_pos = action.data()
            self.create_node_at_position(node_type, scene_pos)
    
    def create_node_at_position(self, node_type, scene_pos):
        from core.node_factory import NodeFactory
        
        node_data = NodeFactory.create_node_data(node_type)
        node = self.graph_manager.add_node(node_type, scene_pos, node_data)
        
        self.node_created.emit(node)
    
    def wheelEvent(self, event):
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1/zoom_factor, 1/zoom_factor)