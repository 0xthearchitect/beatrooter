from PyQt6.QtWidgets import QGraphicsObject, QMenu
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QAction, QFontMetrics

from features.beatroot_canvas.core import NodeFactory


class StackerItem(QGraphicsObject):
    moved = pyqtSignal(str, QPointF)
    dragged_delta = pyqtSignal(str, QPointF)
    position_changed = pyqtSignal(str, QPointF)
    drag_started = pyqtSignal(str)
    drag_finished = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    node_creation_requested = pyqtSignal(str, QPointF)
    stacker_creation_requested = pyqtSignal()
    delete_selected_requested = pyqtSignal()
    toggle_requested = pyqtSignal(str)
    connection_requested = pyqtSignal(object)

    STACKER_BG = QColor("#292929")
    STACKER_BORDER = QColor("#3d3d3d")
    STACKER_BORDER_ACTIVE = QColor("#3d3d3d")
    STACKER_TEXT = QColor(244, 244, 244)
    STACKER_SUBTEXT = QColor(210, 210, 210, 180)
    STACKER_DIVIDER = QColor(76, 76, 76, 220)
    HINT_BG = QColor(244, 244, 244, 230)
    HINT_TEXT = QColor(22, 22, 22)

    def __init__(self, payload: dict):
        super().__init__()
        self.stacker_id = str(payload.get("id", "")).strip()
        self.name = str(payload.get("name", "Stacker")).strip() or "Stacker"
        self.stacker_type = str(payload.get("type", "")).strip()
        self.color_hex = "#292929"
        self.min_height = 108.0
        # Calculate min_width based on title text
        self.min_width = self._calculate_min_width_for_title(self.name)
        self.width = max(self.min_width, float(payload.get("width", self.min_width)))
        self.height = max(self.min_height, float(payload.get("height", self.min_height)))
        self.is_collapsed = bool(payload.get("collapsed", False))
        self.child_node_count = int(payload.get("child_node_count", 0) or 0)
        self.child_stacker_count = int(payload.get("child_stacker_count", 0) or 0)

        self._moved_during_drag = False
        self._drag_active = False
        self._paint_margin = 6.0
        self._hint_top_margin = 28.0
        self._hint_text = ""

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
        return QRectF(
            -m,
            -(m + self._hint_top_margin),
            self.width + (m * 2.0),
            self.height + (m * 2.0) + self._hint_top_margin,
        )

    def paint(self, painter: QPainter, option, widget):
        content_rect = QRectF(0.0, 0.0, self.width, self.height)
        header_rect = self._header_rect(content_rect)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QBrush(self.STACKER_BG))

        border_color = QColor(self.STACKER_BORDER_ACTIVE if (self.isSelected() or self._hint_text) else self.STACKER_BORDER)
        border_pen = QPen(border_color, 1.25)
        border_pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(border_pen)
        painter.drawRoundedRect(content_rect, 14, 14)

        if self.is_collapsed:
            self._draw_collapsed_content(painter, content_rect)
        else:
            title_rect = self._title_rect(content_rect)
            meta_rect = self._meta_rect(content_rect)

            painter.setPen(QPen(self.STACKER_TEXT))
            painter.setFont(QFont("Consolas", 9, QFont.Weight.DemiBold))
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.name)

            painter.setFont(QFont("Consolas", 7, QFont.Weight.DemiBold))
            painter.setPen(QPen(self.STACKER_SUBTEXT))
            painter.drawText(meta_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._meta_text())

            divider_pen = QPen(self.STACKER_DIVIDER, 1.0)
            painter.setPen(divider_pen)
            painter.drawLine(
                QPointF(content_rect.left() + 10.0, header_rect.bottom()),
                QPointF(content_rect.right() - 10.0, header_rect.bottom()),
            )

        if self.isSelected():
            select_pen = QPen(QColor("#3d3d3d"), 1.1)
            painter.setPen(select_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(content_rect.adjusted(-1, -1, 1, 1), 15, 15)

        self._draw_hint_badge(painter, content_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._moved_during_drag = False
            self.drag_started.emit(self.stacker_id)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            self.drag_finished.emit(self.stacker_id)
            if self._moved_during_drag:
                self.moved.emit(self.stacker_id, self.scenePos())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            content_rect = QRectF(0.0, 0.0, self.width, self.height)
            if self._header_hit_rect(content_rect).contains(event.pos()):
                self._drag_active = False
                self.toggle_requested.emit(self.stacker_id)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def itemChange(self, change, value):
        if self._drag_active and change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            new_pos = QPointF(value)
            delta = new_pos - self.pos()
            if abs(delta.x()) > 0.01 or abs(delta.y()) > 0.01:
                self.dragged_delta.emit(self.stacker_id, delta)
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            self._moved_during_drag = True
            self.position_changed.emit(self.stacker_id, self.scenePos())
        return super().itemChange(change, value)

    def hoverMoveEvent(self, event):
        content_rect = QRectF(0.0, 0.0, self.width, self.height)
        if self._header_hit_rect(content_rect).contains(event.pos()):
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._drag_active:
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
        connect_action = QAction("Start Connection", menu)
        connect_action.triggered.connect(lambda: self.connection_requested.emit(self))
        menu.addAction(connect_action)
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

    def set_geometry(self, rect: QRectF):
        rect = QRectF(rect)
        new_width = max(self.min_width, float(rect.width()))
        new_height = max(self.min_height, float(rect.height()))
        size_changed = abs(new_width - self.width) > 0.01 or abs(new_height - self.height) > 0.01

        if size_changed:
            self.prepareGeometryChange()
            self.width = new_width
            self.height = new_height

        new_pos = QPointF(float(rect.x()), float(rect.y()))
        if (
            abs(new_pos.x() - self.pos().x()) > 0.01
            or abs(new_pos.y() - self.pos().y()) > 0.01
        ):
            self.setPos(new_pos)

        if size_changed:
            self.update()

    def set_link_hint(self, text: str):
        normalized = str(text or "").strip().upper()
        if normalized == self._hint_text:
            return
        self._hint_text = normalized
        self.update()

    def clear_link_hint(self):
        self.set_link_hint("")

    def set_collapsed(self, collapsed: bool):
        collapsed = bool(collapsed)
        if collapsed == self.is_collapsed:
            return
        self.is_collapsed = collapsed
        self.update()

    def set_child_counts(self, node_count: int, stacker_count: int):
        node_count = max(0, int(node_count or 0))
        stacker_count = max(0, int(stacker_count or 0))
        if node_count == self.child_node_count and stacker_count == self.child_stacker_count:
            return
        self.child_node_count = node_count
        self.child_stacker_count = stacker_count
        self.update()

    def _calculate_min_width_for_title(self, title: str) -> float:
        """Calculate minimum width based on title text length."""
        # Create a temporary font to measure text
        font = QFont("Consolas", 9, QFont.Weight.DemiBold)
        metrics = self._get_font_metrics(font)
        
        # Text width for title + padding (left 10 + right 10) + meta area (78) + spacing
        title_width = metrics.horizontalAdvance(title) if title else 0
        # Add margins: left padding (10) + right padding (10) + meta area (78) + minimum spacing
        min_width = title_width + 10 + 10 + 78 + 10
        
        # Ensure minimum width of 124
        return max(124.0, float(min_width))
    
    def _get_font_metrics(self, font: QFont):
        """Get font metrics for text measurement."""
        return QFontMetrics(font)

    def to_payload(self) -> dict:
        return {
            "id": self.stacker_id,
            "name": self.name,
            "type": self.stacker_type,
            "color": self.color_hex,
            "collapsed": self.is_collapsed,
            "width": float(self.width),
            "height": float(self.height),
            "x": float(self.scenePos().x()),
            "y": float(self.scenePos().y()),
        }

    def _draw_hint_badge(self, painter: QPainter, content_rect: QRectF):
        if not self._hint_text:
            return

        painter.save()
        painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(self._hint_text) + 16
        badge_width = max(82, text_width)
        badge_rect = QRectF(
            content_rect.center().x() - (badge_width / 2.0),
            content_rect.top() - 22.0,
            badge_width,
            16.0,
        )

        painter.setBrush(QBrush(self.HINT_BG))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(badge_rect, 8, 8)

        painter.setPen(QPen(self.HINT_TEXT))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._hint_text)
        painter.restore()

    def _meta_text(self) -> str:
        return f"{self.child_node_count}N  {self.child_stacker_count}S"

    def _header_rect(self, content_rect: QRectF) -> QRectF:
        return QRectF(content_rect.left() + 10.0, content_rect.top() + 8.0, self.width - 20.0, 24.0)

    def _title_rect(self, content_rect: QRectF) -> QRectF:
        header_rect = self._header_rect(content_rect)
        return QRectF(header_rect.left(), header_rect.top(), max(40.0, header_rect.width() - 82.0), header_rect.height())

    def _meta_rect(self, content_rect: QRectF) -> QRectF:
        header_rect = self._header_rect(content_rect)
        return QRectF(header_rect.right() - 78.0, header_rect.top(), 78.0, header_rect.height())

    def _header_hit_rect(self, content_rect: QRectF) -> QRectF:
        if self.is_collapsed:
            return content_rect
        header_rect = self._header_rect(content_rect)
        return QRectF(content_rect.left(), content_rect.top(), content_rect.width(), header_rect.bottom() + 4.0)

    def _draw_collapsed_content(self, painter: QPainter, content_rect: QRectF):
        title_rect = QRectF(content_rect.left() + 12.0, content_rect.top() + 10.0, content_rect.width() - 24.0, 18.0)
        badge_rect = QRectF(content_rect.left() + 12.0, content_rect.bottom() - 22.0, content_rect.width() - 24.0, 12.0)

        painter.setPen(QPen(self.STACKER_TEXT))
        painter.setFont(QFont("Consolas", 10, QFont.Weight.DemiBold))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self.name)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(49, 49, 49, 235)))
        painter.drawRoundedRect(badge_rect, 6, 6)

        painter.setPen(QPen(QColor(228, 228, 228, 190)))
        painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._meta_text())

    def get_input_connection_point(self):
        anchor_y = self.height / 2.0
        return QPointF(0.0, anchor_y)

    def get_output_connection_point(self):
        anchor_y = self.height / 2.0
        return QPointF(self.width, anchor_y)
