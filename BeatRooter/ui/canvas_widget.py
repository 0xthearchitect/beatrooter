from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu, QGraphicsLineItem, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QLineF
from PyQt6.QtGui import QPainter, QPen, QColor, QAction, QCursor, QLinearGradient, QBrush
from models.node import Node
from models.edge import Edge
from ui.node_widget import NodeWidget
from ui.dynamic_edge import DynamicEdge
from ui.custom_node_dialog import CustomNodeDialog
from core.node_factory import NodeFactory

class CanvasWidget(QGraphicsView):
    node_selected = pyqtSignal(object)
    connection_requested = pyqtSignal(str, str)
    node_created = pyqtSignal(object)
    custom_template_created = pyqtSignal(str)
    flipper_files_dropped = pyqtSignal(list, QPointF, str)
    
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
        
        self.grid_size = 22
        self.show_grid = True

        self.zoom_step = 1.12
        self.min_zoom = 0.45
        self.max_zoom = 2.4
        self.current_zoom = 1.0
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setMinimumSize(600, 400)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.scene.setSceneRect(-10000, -10000, 20000, 20000)
        self.setAcceptDrops(True)
        self.scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheNone)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, False)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, False)
    
    def drawBackground(self, painter, rect):
        background_gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        background_gradient.setColorAt(0.0, QColor(12, 19, 31))
        background_gradient.setColorAt(1.0, QColor(11, 18, 29))
        painter.fillRect(rect, background_gradient)

        if self.show_grid:
            painter.setPen(QPen(QColor(0, 0, 0, 0), 0))
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)
            right = int(rect.right())
            bottom = int(rect.bottom())
            
            for x in range(left, right, self.grid_size):
                for y in range(top, bottom, self.grid_size):
                    is_major = ((x // self.grid_size) % 5 == 0) and ((y // self.grid_size) % 5 == 0)
                    painter.setBrush(QColor(67, 91, 124, 74) if is_major else QColor(47, 68, 97, 38))
                    painter.drawRect(x, y, 1, 1)
    
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
        temp_pen = QPen(QColor(117, 156, 205, 165), 1.2, Qt.PenStyle.DashLine)
        temp_pen.setDashPattern([6, 4])
        self.temp_connection_line.setPen(temp_pen)
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
            self.connection_requested.emit(
                self.connection_source.node.id,
                target_widget.node.id
            )
        
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
        categories = {}
        for node_type in NodeFactory.get_all_node_types():
            category = NodeFactory.find_node_category(node_type) or "General"
            categories.setdefault(category, []).append(node_type)

        for category_name in sorted(categories.keys()):
            label = NodeFactory.get_category_display_name(category_name)
            category_menu = create_node_menu.addMenu(label)
            for node_type in sorted(categories[category_name], key=lambda item: NodeFactory.get_node_name(item).lower()):
                action = QAction(NodeFactory.get_node_name(node_type), self)
                action.setData((node_type, scene_pos))
                action.triggered.connect(self.create_node_from_context)
                category_menu.addAction(action)

        create_node_menu.addSeparator()
        custom_action = QAction("Custom Node...", self)
        custom_action.setData(scene_pos)
        custom_action.triggered.connect(self.create_custom_node_from_context)
        create_node_menu.addAction(custom_action)
        
        menu.exec(self.mapToGlobal(screen_pos))
    
    def create_node_from_context(self):
        action = self.sender()
        if action:
            node_type, scene_pos = action.data()
            self.create_node_at_position(node_type, scene_pos)
    
    def create_node_at_position(self, node_type, scene_pos):
        node_data = NodeFactory.create_node_data(node_type)
        node = self.graph_manager.add_node(node_type, scene_pos, node_data)
        
        self.node_created.emit(node)

    def create_custom_node_from_context(self):
        action = self.sender()
        if not action:
            return

        scene_pos = action.data()
        dialog = CustomNodeDialog(self)
        if not dialog.exec():
            return

        payload = dialog.get_template_payload()
        if not payload:
            return

        try:
            node_type = NodeFactory.register_custom_node_template(
                name=payload["name"],
                node_type=payload["node_type"],
                color=payload["color"],
                symbol=payload["symbol"],
                default_data=payload["default_data"],
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Custom Node", str(exc))
            return

        self.graph_manager.graph_data.metadata["custom_node_templates"] = NodeFactory.export_custom_node_templates()
        self.graph_manager.graph_data.metadata["node_template_settings"] = NodeFactory.export_node_template_settings()
        self.custom_template_created.emit(node_type)
        self.create_node_at_position(node_type, scene_pos)
    
    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_by(self.zoom_step)
        else:
            self.zoom_by(1 / self.zoom_step)
        event.accept()

    def zoom_by(self, factor):
        target_zoom = self.current_zoom * factor
        self.set_zoom(target_zoom)

    def set_zoom(self, target_zoom):
        clamped_zoom = max(self.min_zoom, min(target_zoom, self.max_zoom))
        if abs(clamped_zoom - self.current_zoom) < 0.0001:
            return

        scale_factor = clamped_zoom / self.current_zoom
        self.scale(scale_factor, scale_factor)
        self.current_zoom = clamped_zoom

    def zoom_in(self):
        self.zoom_by(self.zoom_step)

    def zoom_out(self):
        self.zoom_by(1 / self.zoom_step)

    def reset_zoom(self):
        self.resetTransform()
        self.current_zoom = 1.0

    def dragEnterEvent(self, event):
        if self._is_flipper_file_drop(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._is_flipper_file_drop(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if not self._is_flipper_file_drop(event):
            super().dropEvent(event)
            return

        mime_data = event.mimeData()
        urls = mime_data.urls() if mime_data else []
        file_paths = []
        for url in urls:
            if not url.isLocalFile():
                continue
            local_path = url.toLocalFile()
            if local_path:
                file_paths.append(local_path)

        if not file_paths:
            event.ignore()
            return

        root_path = ""
        if mime_data and mime_data.hasFormat("application/x-beatrooter-flipper-root"):
            try:
                root_path = bytes(mime_data.data("application/x-beatrooter-flipper-root")).decode("utf-8")
            except Exception:
                root_path = ""

        drop_pos = self.mapToScene(event.position().toPoint())
        self.flipper_files_dropped.emit(file_paths, drop_pos, root_path)
        event.acceptProposedAction()

    def _is_flipper_file_drop(self, event) -> bool:
        mime_data = event.mimeData()
        if not mime_data or not mime_data.hasUrls():
            return False

        for url in mime_data.urls():
            if url.isLocalFile():
                return True
        return False
