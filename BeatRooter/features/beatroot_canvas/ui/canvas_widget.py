from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QMenu,
    QGraphicsLineItem,
    QMessageBox,
    QRubberBand,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QLineF, QRect, QRectF, QPoint, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QAction, QCursor, QLinearGradient, QBrush
from features.beatroot_canvas.models.node import Node
from features.beatroot_canvas.models.edge import Edge
from features.beatroot_canvas.ui.node_widget import NodeWidget
from features.beatroot_canvas.ui.dynamic_edge import DynamicEdge
from features.beatroot_canvas.ui.custom_node_dialog import CustomNodeDialog
from features.beatroot_canvas.core import NodeFactory
from features.tools.core.tool_node_service import ToolNodeService

class CanvasWidget(QGraphicsView):
    node_selected = pyqtSignal(object)
    connection_requested = pyqtSignal(str, str)
    node_created = pyqtSignal(object)
    custom_template_created = pyqtSignal(str)
    flipper_files_dropped = pyqtSignal(list, QPointF, str)
    tool_dropped = pyqtSignal(str, QPointF)
    stacker_selection_completed = pyqtSignal(QRectF)
    stacker_selection_cancelled = pyqtSignal()
    stacker_creation_requested = pyqtSignal()
    delete_selected_requested = pyqtSignal()
    viewport_resized = pyqtSignal()
    
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
        self.stacker_selection_mode = False
        self._stacker_rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport())
        self._stacker_rubber_band.setStyleSheet(
            "background-color: rgba(135, 188, 202, 90); border: 1px solid rgba(135, 188, 202, 190);"
        )
        self._stacker_origin = QPoint()
        self._stacker_dragging = False

        self.dragging_view = False
        self.last_drag_pos = QPointF()
        
        self.edge_items = {}
        
        self.grid_size = 22
        self.show_grid = True
        self.background_style = "grid"

        self.zoom_step = 1.12
        self.min_zoom = 0.45
        self.max_zoom = 2.4
        self.current_zoom = 1.0
        self._scene_bounds_timer = QTimer(self)
        self._scene_bounds_timer.setSingleShot(True)
        self._scene_bounds_timer.setInterval(80)
        self._scene_bounds_timer.timeout.connect(self._update_scene_bounds_now)
        
        self.setup_ui()
        self.scene.changed.connect(self._schedule_scene_bounds_update)
    
    def setup_ui(self):
        self.setMinimumSize(600, 400)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.scene.setSceneRect(-1200, -900, 2400, 1800)
        self.setAcceptDrops(True)
        self.scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheNone)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, False)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, False)
        self._stacker_rubber_band.hide()
        self._update_scene_bounds_now()

    def _schedule_scene_bounds_update(self, *args):
        if not self._scene_bounds_timer.isActive():
            self._scene_bounds_timer.start()

    def _update_scene_bounds_now(self):
        relevant_items = [item for item in self.scene.items() if item is not self.temp_connection_line]
        if not relevant_items:
            self.scene.setSceneRect(-1200, -900, 2400, 1800)
            return

        bounds = self.scene.itemsBoundingRect()
        if not bounds.isValid() or bounds.width() <= 0 or bounds.height() <= 0:
            self.scene.setSceneRect(-1200, -900, 2400, 1800)
            return

        viewport_rect = self.viewport().rect()
        min_width = max(1200.0, float(viewport_rect.width()) * 1.15 / max(0.4, self.current_zoom))
        min_height = max(850.0, float(viewport_rect.height()) * 1.15 / max(0.4, self.current_zoom))

        if bounds.width() < min_width:
            extra = (min_width - bounds.width()) / 2.0
            bounds.adjust(-extra, 0.0, extra, 0.0)
        if bounds.height() < min_height:
            extra = (min_height - bounds.height()) / 2.0
            bounds.adjust(0.0, -extra, 0.0, extra)

        padding = max(180.0, self.grid_size * 6.0)
        self.scene.setSceneRect(bounds.adjusted(-padding, -padding, padding, padding))
    
    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#0f0f0f"))

        if self.background_style == "dots":
            self._draw_dotted_background(painter, rect)
        elif self.show_grid:
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)
            right = int(rect.right())
            bottom = int(rect.bottom())

            minor_pen = QPen(QColor(235, 235, 235, 34), 1)
            major_pen = QPen(QColor(245, 245, 245, 52), 1)

            for x in range(left, right, self.grid_size):
                is_major_x = (x // self.grid_size) % 5 == 0
                painter.setPen(major_pen if is_major_x else minor_pen)
                painter.drawLine(x, top, x, bottom)

            for y in range(top + self.grid_size, bottom, self.grid_size):
                is_major_y = (y // self.grid_size) % 5 == 0
                painter.setPen(major_pen if is_major_y else minor_pen)
                painter.drawLine(left, y, right, y)

    def _draw_dotted_background(self, painter, rect):
        dot_spacing = 55
        dot_radius = 1.7
        left = int(rect.left()) - (int(rect.left()) % dot_spacing)
        top = int(rect.top()) - (int(rect.top()) % dot_spacing)
        right = int(rect.right())
        bottom = int(rect.bottom())

        dot_brush = QBrush(QColor(244, 244, 244, 90))
        painter.setPen(Qt.PenStyle.NoPen)

        for x in range(left, right + dot_spacing, dot_spacing):
            for y in range(top, bottom + dot_spacing, dot_spacing):
                painter.setBrush(dot_brush)
                painter.drawEllipse(QPointF(float(x), float(y)), dot_radius, dot_radius)

    def set_background_style(self, style: str):
        normalized_style = (style or "grid").lower()
        if normalized_style not in {"grid", "dots"}:
            normalized_style = "grid"

        self.background_style = normalized_style
        self.show_grid = normalized_style == "grid"
        self.viewport().update()

    def _is_overlay_event(self, viewport_pos) -> bool:
        point = viewport_pos.toPoint() if hasattr(viewport_pos, "toPoint") else viewport_pos
        widget = self.viewport().childAt(point)
        while widget is not None and widget is not self.viewport():
            if bool(widget.property("blocksCanvasInteraction")):
                return True
            widget = widget.parentWidget()
        return False
    
    def mousePressEvent(self, event):
        if self._is_overlay_event(event.pos()):
            event.ignore()
            return

        if self.stacker_selection_mode and event.button() == Qt.MouseButton.LeftButton:
            self._stacker_origin = event.pos()
            self._stacker_dragging = True
            self._stacker_rubber_band.setGeometry(QRect(self._stacker_origin, self._stacker_origin))
            self._stacker_rubber_band.show()
            event.accept()
            return

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
        if (
            not self.dragging_view
            and not self._stacker_dragging
            and self._is_overlay_event(event.pos())
        ):
            event.ignore()
            return

        if self.stacker_selection_mode and self._stacker_dragging:
            rect = QRect(self._stacker_origin, event.pos()).normalized()
            self._stacker_rubber_band.setGeometry(rect)
            event.accept()
            return

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
        if self.stacker_selection_mode and self._stacker_dragging and event.button() == Qt.MouseButton.LeftButton:
            self._stacker_dragging = False
            viewport_rect = QRect(self._stacker_origin, event.pos()).normalized()
            scene_rect = self._viewport_rect_to_scene_rect(viewport_rect)
            self.finish_stacker_selection()
            if scene_rect.width() >= 40.0 and scene_rect.height() >= 40.0:
                self.stacker_selection_completed.emit(scene_rect)
            else:
                self.stacker_selection_cancelled.emit()
            event.accept()
            return

        if self.dragging_view and event.button() == Qt.MouseButton.LeftButton:
            self.dragging_view = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
            return
        
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.stacker_selection_mode:
            self.cancel_stacker_selection()
            event.accept()
            return

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewport_resized.emit()
        self._schedule_scene_bounds_update()
    
    def add_node_widget(self, node_widget):
        self.scene.addItem(node_widget)
        node_widget.setPos(node_widget.node.position)
        self._schedule_scene_bounds_update()
    
    def remove_node_widget(self, node_widget):
        self.scene.removeItem(node_widget)
        self._schedule_scene_bounds_update()
    
    def remove_edge_item(self, edge_id):
        if edge_id in self.edge_items:
            edge_item = self.edge_items[edge_id]
            self.scene.removeItem(edge_item)
            del self.edge_items[edge_id]
            self._schedule_scene_bounds_update()
    
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
        if item:
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

        selected_items = [
            item
            for item in self.scene.selectedItems()
            if hasattr(item, "node") or hasattr(item, "stacker_id")
        ]
        if len(selected_items) > 1:
            delete_all_action = QAction(f"Delete All Selected ({len(selected_items)})", self)
            delete_all_action.triggered.connect(self.delete_selected_requested.emit)
            menu.addAction(delete_all_action)
            menu.addSeparator()
        
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

        menu.addSeparator()
        create_stacker_action = QAction("Create Stacker", self)
        create_stacker_action.triggered.connect(self._request_stacker_creation_from_context)
        menu.addAction(create_stacker_action)
        
        menu.exec(self.mapToGlobal(screen_pos))

    def _request_stacker_creation_from_context(self):
        self.stacker_creation_requested.emit()
    
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
                category=payload["category"],
                category_label=payload["category_label"],
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
        if self._is_overlay_event(event.position()):
            event.ignore()
            return

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
        self._schedule_scene_bounds_update()

    def zoom_in(self):
        self.zoom_by(self.zoom_step)

    def zoom_out(self):
        self.zoom_by(1 / self.zoom_step)

    def reset_zoom(self):
        self.resetTransform()
        self.current_zoom = 1.0

    def start_stacker_selection(self):
        self.stacker_selection_mode = True
        self._stacker_dragging = False
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def cancel_stacker_selection(self):
        self.stacker_selection_mode = False
        self._stacker_dragging = False
        self._stacker_rubber_band.hide()
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.stacker_selection_cancelled.emit()

    def finish_stacker_selection(self):
        self.stacker_selection_mode = False
        self._stacker_dragging = False
        self._stacker_rubber_band.hide()
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def _viewport_rect_to_scene_rect(self, viewport_rect: QRect) -> QRectF:
        top_left = self.mapToScene(viewport_rect.topLeft())
        bottom_right = self.mapToScene(viewport_rect.bottomRight())
        return QRectF(top_left, bottom_right).normalized()

    def dragEnterEvent(self, event):
        if self._is_tool_drop(event):
            event.acceptProposedAction()
            return
        if self._is_flipper_file_drop(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._is_tool_drop(event):
            event.acceptProposedAction()
            return
        if self._is_flipper_file_drop(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if self._is_tool_drop(event):
            mime_data = event.mimeData()
            tool_name = ""
            try:
                tool_name = bytes(mime_data.data(ToolNodeService.TOOL_MIME_TYPE)).decode("utf-8").strip()
            except Exception:
                tool_name = ""

            if not tool_name:
                event.ignore()
                return

            drop_pos = self.mapToScene(event.position().toPoint())
            self.tool_dropped.emit(tool_name, drop_pos)
            event.acceptProposedAction()
            return

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

    def _is_tool_drop(self, event) -> bool:
        mime_data = event.mimeData()
        return bool(mime_data and mime_data.hasFormat(ToolNodeService.TOOL_MIME_TYPE))
