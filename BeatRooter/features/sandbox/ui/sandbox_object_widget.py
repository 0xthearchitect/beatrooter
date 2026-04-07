from PyQt6.QtWidgets import QGraphicsObject, QMenu
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QAction, QLinearGradient, QPixmap
from models.object_model import SandboxObject
from features.sandbox.core.sandbox_object_factory import SandboxObjectFactory
import os
from utils.path_utils import get_resource_path

class SandboxObjectWidget(QGraphicsObject):
    object_updated = pyqtSignal(object)
    connection_started = pyqtSignal(object)
    parent_child_started = pyqtSignal(object)
    positionChanged = pyqtSignal()
    object_deleted = pyqtSignal(object)
    
    def __init__(self, obj):
        super().__init__()
        self.object = obj
        self.setPos(obj.position)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.size = 80
        self.icon_size = 48
        self.corner_radius = 12
        self.padding = 8
        
        self.icon_pixmap = self.load_icon()
        
        self.setZValue(1)
    
    def get_object_color(self):
        return SandboxObjectFactory.get_object_color(self.object.object_type)

    def load_icon(self):
        try:
            if self.object.object_type.value == 'code_file' and self.object.code_content:
                language = self.object.code_content.language.lower()
                icon_file = self.get_language_icon_file(language)
                if icon_file:
                    icon_path = get_resource_path(f"icons/languages/{icon_file}")
                    if os.path.exists(icon_path):
                        return self.load_and_scale_icon(icon_path)

            icon_file = self.get_icon_file_name()
            if not icon_file:
                return self.create_fallback_icon()
                
            icon_path = get_resource_path(f"icons/{icon_file}")
            
            if os.path.exists(icon_path):
                return self.load_and_scale_icon(icon_path)
            else:
                print(f"[WARNING] Icon not found at: {icon_path}")
                return self.create_fallback_icon()
                
        except Exception as e:
            print(f"[ERROR] Failed to load icon: {e}")
            import traceback
            traceback.print_exc()
            return self.create_fallback_icon()

    def get_language_icon_file(self, language):
        language_icons = {
            'python': 'python.png',
            'javascript': 'javascript.png',
            'java': 'java.png',
            'ruby': 'ruby.png',
            'php': 'php.png',
            'html': 'html.png',
            'css': 'css.png',
            'sql': 'sql.png',
            'yaml': 'yaml.png',
            'json': 'json.png',
            'typescript': 'typescript.png',
            'c++': 'cpp.png',
            'c#': 'csharp.png',
            'go': 'go.png',
            'rust': 'rust.png',
            'swift': 'swift.png',
            'kotlin': 'kotlin.png',
            'bash': 'bash.png',
            'powershell': 'powershell.png'
        }
        return language_icons.get(language, None)

    def get_icon_file_name(self):
        icon_mapping = {
            # Operating Systems
            'windows_10': 'operating_systems/windows_10.png',
            'windows_11': 'operating_systems/windows_11.png',
            'ubuntu': 'operating_systems/ubuntu.png',
            'arch': 'operating_systems/arch.png',
            'folder': 'operating_systems/folder.png',
            'file': 'operating_systems/file.png',

            'network_interface': 'operating_systems/network_interface.png',
            'open_port': 'operating_systems/open_port.png',
            'running_service': 'operating_systems/running_service.png',
            'security_policy': 'operating_systems/security_policy.png',
            'user_account': 'operating_systems/user_account.png',
            'system_info': 'operating_systems/system_info.png',
            
            # Network Devices
            'computer': 'network/computer.png',
            'server': 'network/server.png',
            'router': 'network/router.png',
            'switch': 'network/switch.png',
            'firewall': 'network/firewall.png',
            'access_point': 'network/access_point.png',
            
            # Web Technologies
            'apache': 'web/apache.png',
            'nginx': 'web/nginx.png',
            'iis': 'web/iis.png',
            'tomcat': 'web/tomcat.png',
            
            'mysql': 'web/mysql.png',
            'postgresql': 'web/postgresql.png',
            'mongodb': 'web/mongodb.png',
            'redis': 'web/redis.png',
            
            'django': 'web/django.png',
            'flask': 'web/flask.png',
            'nodejs': 'web/nodejs.png',
            'spring': 'web/spring.png',
            'express': 'web/express.png',
            'nestjs': 'web/nestjs.png',
            'rails': 'web/rails.png',
            
            'react': 'web/react.png',
            'angular': 'web/angular.png',
            'vue': 'web/vue.png',
            
            'web_folder': 'web/folder.png',
            'web_app': 'web/web_app.png',
            'code_file': 'web/code_file.png',
            'config_file': 'web/config_file.png',
            'api_endpoint': 'web/api_endpoint.png',
            
            'oauth': 'web/oauth.png',
            'jwt': 'web/jwt.png',
            'saml': 'web/saml.png',
            
            # Organization
            'project': 'organization/project.png',
            'team': 'organization/team.png',
            'user': 'organization/user.png',
            'group': 'organization/group.png'
        }
        
        return icon_mapping.get(self.object.object_type.value, None)
    
    def load_and_scale_icon(self, icon_path):
        pixmap = QPixmap(icon_path)
        return pixmap.scaled(self.icon_size, self.icon_size, 
                           Qt.AspectRatioMode.KeepAspectRatio, 
                           Qt.TransformationMode.SmoothTransformation)
    
    def create_fallback_icon(self):
        pixmap = QPixmap(self.icon_size, self.icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        color = QColor(self.get_object_color())
        
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(150), 2))
        painter.drawEllipse(4, 4, self.icon_size - 8, self.icon_size - 8)
        
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        painter.setFont(font)
        
        abbrev = self.get_icon_abbreviation()
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, abbrev)
        
        painter.end()
        return pixmap
    
    def get_icon_abbreviation(self):
        if self.object.object_type.value == 'code_file' and self.object.code_content:
            lang = self.object.code_content.language
            if lang:
                return lang[:3].upper()
        
        abbreviations = {
            'python': 'PY',
            'javascript': 'JS',
            'java': 'JV',
            'html': 'HT',
            'css': 'CS',
            'sql': 'SQL'
        }
        
        name_words = self.object.name.split()
        if len(name_words) >= 2:
            return f"{name_words[0][0]}{name_words[1][0]}".upper()
        elif len(self.object.name) >= 2:
            return self.object.name[:2].upper()
        else:
            return "OB"
    
    def update_icon(self):
        self.icon_pixmap = self.load_icon()
        self.update()
    
    def boundingRect(self):
        return QRectF(-self.size/2, -self.size/2, self.size, self.size)
    
    def paint(self, painter, option, widget):
        accent_color = QColor(self.get_object_color())
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Fundo do ícone
        main_rect = QRectF(-self.size/2, -self.size/2, self.size, self.size)
        
        # Gradiente de fundo suave
        gradient = QLinearGradient(
            QPointF(-self.size/2, -self.size/2), 
            QPointF(self.size/2, self.size/2)
        )
        gradient.setColorAt(0, QColor(250, 250, 250))
        gradient.setColorAt(0.7, QColor(245, 245, 245))
        gradient.setColorAt(1, QColor(240, 240, 240))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(220, 220, 220), 1))
        painter.drawRoundedRect(main_rect, self.corner_radius, self.corner_radius)
        
        # Borda colorida sutil
        border_rect = QRectF(-self.size/2 + 1, -self.size/2 + 1, self.size - 2, self.size - 2)
        painter.setPen(QPen(accent_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(border_rect, self.corner_radius - 1, self.corner_radius - 1)
        
        if not self.icon_pixmap.isNull():
            icon_x = -self.icon_size / 2
            icon_y = -self.icon_size / 2 - 5
            
            painter.drawPixmap(int(icon_x), int(icon_y), self.icon_pixmap)
        
        painter.setPen(QPen(QColor(60, 60, 60)))
        font = QFont("Arial", 8, QFont.Weight.Normal)
        painter.setFont(font)
        
        object_name = self.object.name
        metrics = painter.fontMetrics()
        elided_name = metrics.elidedText(object_name, Qt.TextElideMode.ElideRight, self.size - 10)
        
        text_width = metrics.horizontalAdvance(elided_name)
        text_x = -text_width / 2
        text_y = self.size/2 - 15
        
        painter.drawText(int(text_x), int(text_y), elided_name)
        
        self.draw_connection_ports(painter, accent_color)
        
        if self.isSelected():
            selection_pen = QPen(accent_color, 3)
            selection_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(selection_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            selection_rect = QRectF(
                -self.size/2 + 2, 
                -self.size/2 + 2, 
                self.size - 4, 
                self.size - 4
            )
            painter.drawRoundedRect(selection_rect, self.corner_radius - 2, self.corner_radius - 2)
    
    def get_connection_point(self, is_source=True):
        if is_source:
            return self.scenePos() + QPointF(self.size/2, 0)
        else:
            return self.scenePos() + QPointF(-self.size/2, 0)

    def draw_connection_ports(self, painter, accent_color):
        port_radius = 5
        
        left_port = QPointF(-self.size/2, 0)
        painter.setBrush(QBrush(accent_color))
        painter.setPen(QPen(accent_color.darker(150), 1))
        painter.drawEllipse(left_port, port_radius, port_radius)
        
        right_port = QPointF(self.size/2, 0)
        painter.drawEllipse(right_port, port_radius, port_radius)
    
    def mouseDoubleClickEvent(self, event):
        self.object_updated.emit(self.object)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
        menu = QMenu()
        
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #cccccc;
                font-family: 'Arial';
                font-size: 9px;
            }
            QMenu::item {
                padding: 6px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #e6e6e6;
                color: #000000;
            }
            QMenu::separator {
                height: 1px;
                background: #cccccc;
            }
        """)
        
        connect_action = QAction("Create Connection", self)
        connect_action.triggered.connect(lambda: self.connection_started.emit(self))
        menu.addAction(connect_action)
        
        parent_child_action = QAction("Set as Parent", self)
        parent_child_action.triggered.connect(lambda: self.parent_child_started.emit(self))
        menu.addAction(parent_child_action)
        
        menu.addSeparator()
        
        edit_action = QAction("Edit Object", self)
        edit_action.triggered.connect(lambda: self.object_updated.emit(self.object))
        menu.addAction(edit_action)

        delete_action = QAction("Delete Object", self)
        delete_action.triggered.connect(self.delete_object)
        menu.addAction(delete_action)
        
        menu.exec(event.screenPos())
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def delete_object(self):
        self.object_deleted.emit(self.object)
    
    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange and self.scene():
            self.object.position = value
            self.positionChanged.emit()
        return super().itemChange(change, value)
    
    def update_display(self):
        self.update_icon()
        self.update()