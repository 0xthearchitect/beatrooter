from PyQt6.QtWidgets import QGraphicsObject, QMenu
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QAction
from features.beatroot_canvas.core import NodeFactory


class StackerItem(QGraphicsObject):
    moved = pyqtSignal(str, QPointF)
    dragged_delta = pyqtSignal(str, QPointF)
    resized = pyqtSignal(str, float, float)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    node_creation_requested = pyqtSignal(str, QPointF)
    stacker_creation_requested = pyqtSignal()
    delete_selected_requested = pyqtSignal()

    def __init__(self, payload: dict):
        super().__init__()
        self.stacker_id = str(payload.get("id", "")).strip()
        self.name = str(payload.get("name", "Stacker")).strip() or "Stacker"
        self.stacker_type = str(payload.get("type", "")).strip()
        self.color_hex = str(payload.get("color", "#000000")).strip() or "#000000"
        self.width = max(120.0, float(payload.get("width", 320)))
        self.height = max(90.0, float(payload.get("height", 180)))
        self.min_width = 120.0
        self.min_height = 90.0

        self._moved_during_drag = False
        self._drag_active = False
        self._paint_margin = 4.0
        self._resizing = False
        self._resize_start_scene_pos = QPointF()
        self._resize_start_width = self.width
        self._resize_start_height = self.height
        self._resize_handle_size = 12.0
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(-12)

        self.setPos(
            float(payload.get("x", 0.0)),
            float(payload.get("y", 0.0)),
        )

    def boundingRect(self):
        m = self._paint_margin
        return QRectF(-m, -m, self.width + (m * 2.0), self.height + (m * 2.0))

    def paint(self, painter: QPainter, option, widget):
        content_rect = QRectF(0.0, 0.0, self.width, self.height)
        base_color = QColor(self.color_hex)
        fill_color = QColor(base_color)
        fill_color.setAlpha(255)

        border_color = QColor(base_color)
        border_color.setAlpha(255)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QBrush(fill_color))
        border_pen = QPen(border_color, 1.3, Qt.PenStyle.DashLine)
        border_pen.setDashPattern([5, 4])
        painter.setPen(border_pen)
        painter.drawRoundedRect(content_rect, 10, 10)

        text_primary, text_secondary = self._text_colors_for_background(base_color)

        painter.setFont(QFont("Consolas", 9, QFont.Weight.DemiBold))
        painter.setPen(QPen(text_primary))
        painter.drawText(
            QRectF(content_rect.left() + 10, content_rect.top() + 8, self.width - 20, 20),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.name,
        )

        if self.stacker_type:
            painter.setFont(QFont("Consolas", 8))
            painter.setPen(QPen(text_secondary))
            painter.drawText(
                QRectF(content_rect.left() + 10, content_rect.top() + 26, self.width - 20, 16),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.stacker_type.upper(),
            )

        if self.isSelected():
            select_pen = QPen(QColor(130, 180, 255, 180), 1.2)
            painter.setPen(select_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(content_rect.adjusted(-1, -1, 1, 1), 11, 11)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_on_resize_handle(event.pos()):
            self._resizing = True
            self._drag_active = False
            self._moved_during_drag = False
            self._resize_start_scene_pos = event.scenePos()
            self._resize_start_width = self.width
            self._resize_start_height = self.height
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
        self._moved_during_drag = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.scenePos() - self._resize_start_scene_pos
            new_width = max(self.min_width, self._resize_start_width + delta.x())
            new_height = max(self.min_height, self._resize_start_height + delta.y())
            if abs(new_width - self.width) > 0.01 or abs(new_height - self.height) > 0.01:
                self.prepareGeometryChange()
                self.width = float(new_width)
                self.height = float(new_height)
                self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing and event.button() == Qt.MouseButton.LeftButton:
            self._resizing = False
            self._drag_active = False
            if (
                abs(self.width - self._resize_start_width) > 0.01
                or abs(self.height - self._resize_start_height) > 0.01
            ):
                self.resized.emit(self.stacker_id, float(self.width), float(self.height))
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
        if self._moved_during_drag:
            self.moved.emit(self.stacker_id, self.scenePos())

    def itemChange(self, change, value):
        if self._resizing and change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            return self.pos()
        if self._drag_active and change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            new_pos = QPointF(value)
            delta = new_pos - self.pos()
            if abs(delta.x()) > 0.01 or abs(delta.y()) > 0.01:
                self.dragged_delta.emit(self.stacker_id, delta)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            self._moved_during_drag = True
        return super().itemChange(change, value)

    def hoverMoveEvent(self, event):
        if self._is_on_resize_handle(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self._resizing:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._resizing:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()

        create_node_menu = menu.addMenu("Create Node")
        categories = {}
        for node_type in NodeFactory.get_all_node_types():
            category = NodeFactory.find_node_category(node_type) or "General"
            categories.setdefault(category, []).append(node_type)

        scene_pos = QPointF(event.scenePos())
        for category_name in sorted(categories.keys()):
            label = NodeFactory.get_category_display_name(category_name)
            category_menu = create_node_menu.addMenu(label)
            for node_type in sorted(categories[category_name], key=lambda item: NodeFactory.get_node_name(item).lower()):
                action = QAction(NodeFactory.get_node_name(node_type), menu)
                action.triggered.connect(
                    lambda checked=False, nt=node_type, pos=scene_pos: self.node_creation_requested.emit(nt, QPointF(pos))
                )
                category_menu.addAction(action)

        create_stacker_action = QAction("Create Stacker", menu)
        create_stacker_action.triggered.connect(self.stacker_creation_requested.emit)
        menu.addAction(create_stacker_action)
        menu.addSeparator()

        edit_action = QAction("Edit Stacker", menu)
        edit_action.triggered.connect(lambda: self.edit_requested.emit(self.stacker_id))
        menu.addAction(edit_action)
        delete_action = QAction("Delete Stacker", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.stacker_id))
        menu.addAction(delete_action)

        selected_items = []
        scene = self.scene()
        if scene is not None:
            selected_items = [
                item
                for item in scene.selectedItems()
                if hasattr(item, "node") or hasattr(item, "stacker_id")
            ]
        if self.isSelected() and len(selected_items) > 1:
            menu.addSeparator()
            delete_all_action = QAction(f"Delete All Selected ({len(selected_items)})", menu)
            delete_all_action.triggered.connect(self.delete_selected_requested.emit)
            menu.addAction(delete_all_action)

        menu.exec(event.screenPos())
        event.accept()

    def _resize_handle_rect(self) -> QRectF:
        size = self._resize_handle_size
        return QRectF(self.width - size - 3.0, self.height - size - 3.0, size, size)

    def _is_on_resize_handle(self, pos: QPointF) -> bool:
        return self._resize_handle_rect().contains(pos)

    def _text_colors_for_background(self, bg: QColor):
        brightness = (bg.red() * 299 + bg.green() * 587 + bg.blue() * 114) / 1000
        if brightness >= 150:
            return QColor(20, 20, 20), QColor(40, 40, 40)
        return QColor(244, 244, 244), QColor(220, 220, 220)

    def to_payload(self) -> dict:
        return {
            "id": self.stacker_id,
            "name": self.name,
            "type": self.stacker_type,
            "color": self.color_hex,
            "width": float(self.width),
            "height": float(self.height),
            "x": float(self.scenePos().x()),
            "y": float(self.scenePos().y()),
        }
