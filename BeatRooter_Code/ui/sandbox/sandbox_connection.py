from PyQt6.QtWidgets import QGraphicsPathItem, QMenu, QGraphicsSimpleTextItem
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainterPath, QPen, QColor, QPainter, QAction, QBrush, QFont

class SandboxConnection(QGraphicsPathItem):
    def __init__(self, source_widget, target_widget, connection_data):
        super().__init__()
        self.source_widget = source_widget
        self.target_widget = target_widget
        self.connection_data = connection_data
        
        self.setZValue(-1)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        self.normal_color = QColor(59, 130, 246)
        self.hover_color = QColor(96, 165, 250)
        self.selected_color = QColor(239, 68, 68)
        
        self.current_color = self.normal_color
        self.line_width = 2

        if source_widget:
            source_widget.positionChanged.connect(self.on_object_moved)
        if target_widget:
            target_widget.positionChanged.connect(self.on_object_moved)
        
        if source_widget and target_widget:
            self.update_path()
    
    def on_object_moved(self):
        self.update_path()
        
    def update_path(self, start_point=None, end_point=None):
        if not self.source_widget:
            return
            
        if start_point is None:
            start_point = self.source_widget.get_connection_point(is_source=True)
        
        if end_point is None and self.target_widget:
            end_point = self.target_widget.get_connection_point(is_source=False)
        elif end_point is None:
            end_point = start_point
        
        path = QPainterPath()
        path.moveTo(start_point)
        
        dx = end_point.x() - start_point.x()
        dy = end_point.y() - start_point.y()

        control_offset_x = dx * 0.5
        control_offset_y = dy * 0.2
        
        ctrl1 = QPointF(start_point.x() + control_offset_x, start_point.y() + control_offset_y)
        ctrl2 = QPointF(end_point.x() - control_offset_x, end_point.y() - control_offset_y)
        
        path.cubicTo(ctrl1, ctrl2, end_point)
        
        self.setPath(path)
        
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self.isSelected():
            pen_color = self.selected_color
        else:
            pen_color = self.current_color

        pen = QPen(pen_color)
        pen.setWidth(self.line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        self.setPen(pen)
        super().paint(painter, option, widget)
    
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