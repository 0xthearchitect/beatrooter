from PyQt6.QtWidgets import QGraphicsObject, QMenu, QInputDialog
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import (QPainter, QPen, QColor, QBrush, QFont, QAction, 
                         QLinearGradient, QPainterPath)
from models.node import Node
from core.node_factory import NodeFactory
import math

class NodeWidget(QGraphicsObject):
    node_updated = pyqtSignal(object)
    connection_started = pyqtSignal(object)
    positionChanged = pyqtSignal()
    node_deleted = pyqtSignal(object)
    
    def __init__(self, node, category=None):
        super().__init__()
        self.node = node
        self.category = category
        self.setPos(node.position)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.min_width = 160
        self.min_height = 100
        self.max_width = 300
        self.max_height = 400
        self.corner_radius = 4
        self.padding = 12
        self.line_height = 14
        self.title_height = 28
        self.field_padding = 4
        
        self.cyber_colors = {
            'background': QColor(20, 25, 35),
            'border': QColor(50, 60, 80),
            'text_primary': QColor(220, 220, 220),
            'text_secondary': QColor(150, 160, 180),
            'accent': QColor(0, 200, 255),
            'warning': QColor(255, 100, 50),
            'success': QColor(50, 200, 100)
        }
        
        self.width = self.min_width
        self.height = self.min_height
        
        self.calculate_size()
        self.setZValue(1)
    
    def calculate_size(self):
        content_lines = self.get_data_fields_to_display()
        
        font = QFont("Consolas", 9)
        temp_painter = QPainter()
        
        max_text_width = 0
        for line in content_lines:
            text_width = temp_painter.fontMetrics().boundingRect(line).width()
            max_text_width = max(max_text_width, text_width)
        
        required_width = max_text_width + (self.padding * 3)
        self.width = max(self.min_width, min(required_width, self.max_width))
        
        content_height = self.title_height + (self.padding * 2) + (len(content_lines) * self.line_height)
        self.height = max(self.min_height, min(content_height, self.max_height))
    
    def get_node_accent_color(self):
        if self.category and self.category in NodeFactory.CATEGORY_TEMPLATES:
            if self.node.type in NodeFactory.CATEGORY_TEMPLATES[self.category]:
                color_hex = NodeFactory.CATEGORY_TEMPLATES[self.category][self.node.type]['color']
                return QColor(color_hex)
        
        for category in NodeFactory.CATEGORY_TEMPLATES:
            if self.node.type in NodeFactory.CATEGORY_TEMPLATES[category]:
                color_hex = NodeFactory.CATEGORY_TEMPLATES[category][self.node.type]['color']
                return QColor(color_hex)
        
        return QColor(NodeFactory.NODE_TYPES.get(self.node.type, {}).get('color', '#ffffff'))
    
    def get_node_display_name(self):
        if self.category and self.category in NodeFactory.CATEGORY_TEMPLATES:
            if self.node.type in NodeFactory.CATEGORY_TEMPLATES[self.category]:
                return NodeFactory.CATEGORY_TEMPLATES[self.category][self.node.type]['name']
        
        for category in NodeFactory.CATEGORY_TEMPLATES:
            if self.node.type in NodeFactory.CATEGORY_TEMPLATES[category]:
                return NodeFactory.CATEGORY_TEMPLATES[category][self.node.type]['name']
        
        return NodeFactory.NODE_TYPES.get(self.node.type, {}).get('name', 'Unknown')
    
    def get_node_symbol(self):
        symbols = {
            'user': "[USER]",
            'ip': "[IP]",
            'domain': "[DOMAIN]",
            'credential': "[PASS]",
            'attack': "[ATTACK]",
            'vulnerability': "[VULN]",
            'host': "[HOST]",
            'note': "[NOTE]",
            'screenshot': "[IMG]",
            'command': "[CMD]",
            'script': "[SCRIPT]",
            
            'web_application': "[WEB]",
            'endpoint': "[ENDPT]",
            'vulnerability_finding': "[FIND]",
            'payload': "[PAYLD]",

            'network_range': "[NET]",
            'port_service': "[PORT]",
            'exploit': "[EXPL]",
            'lateral_movement': "[MOVE]",
            
            'target_person': "[TARGET]",
            'phishing_email': "[EMAIL]",
            'credential_harvest': "[HARV]",
            'physical_access': "[PHYS]",
            
            'security_incident': "[INCIDENT]",
            'incident_timeline': "[TIMELINE]",
            'forensic_artifact': "[ARTIFACT]",
            'containment_action': "[CONTAIN]",

            'hypothesis': "[HYPOTH]",
            'ioc': "[IOC]",
            'hunting_rule': "[RULE]",
            'ttp': "[TTP]",

            'malware_sample': "[MALWARE]",
            'analysis_environment': "[ENV]",
            'behavior_analysis': "[BEHAV]",
            'yara_rule': "[YARA]",
            
            'security_alert': "[ALERT]",
            'correlation_rule': "[CORR]",
            'log_source': "[LOG]",
            'investigation_note': "[INVEST]",

            'ticket': "[TICKET]",
            'triage_decision': "[TRIAGE]",
            'escalation': "[ESCAL]",
            'sla_check': "[SLA]",

            'correlated_event': "[CORREL]",
            'attack_chain': "[CHAIN]",
            'context_enrichment': "[ENRICH]",
            'pattern_analysis': "[PATTERN]",
            
            'compliance_requirement': "[REQ]",
            'control_gap': "[GAP]",
            'audit_finding': "[AUDIT]",
            'remediation_plan': "[PLAN]"
        }
        return symbols.get(self.node.type, "[NODE]")
    
    def boundingRect(self):
        return QRectF(-self.width/2, -self.height/2, self.width, self.height)
    
    def paint(self, painter, option, widget):
        self.calculate_size()
        
        # CORREÇÃO: Usa o método corrigido para obter a cor
        accent_color = self.get_node_accent_color()
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        painter.setBrush(QBrush(self.cyber_colors['background']))
        painter.setPen(QPen(self.cyber_colors['border'], 2))
        
        main_rect = QRectF(-self.width/2, -self.height/2, self.width, self.height)
        painter.drawRect(main_rect)
        
        self.draw_connection_ports(painter, accent_color)

        if self.isSelected():
            selection_pen = QPen(accent_color, 3)
            selection_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(selection_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            selection_rect = QRectF(
                -self.width/2 + 1, 
                -self.height/2 + 1, 
                self.width - 2, 
                self.height - 2
            )
            painter.drawRect(selection_rect)
        else:
            border_pen = QPen(self.cyber_colors['border'], 1)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(main_rect)
        
        self.draw_terminal_header(painter, accent_color)
        self.draw_ascii_content(painter)
        self.draw_corner_symbol(painter, accent_color)

    def draw_connection_ports(self, painter, accent_color):
        port_width = 6
        port_height = 12
        
        left_port_rect = QRectF(
            -self.width/2 - port_width/2,
            -port_height/2,
            port_width,
            port_height
        )
        
        right_port_rect = QRectF(
            self.width/2 - port_width/2,
            -port_height/2,
            port_width,
            port_height
        )
        
        painter.setBrush(QBrush(accent_color.darker(150)))
        painter.setPen(QPen(accent_color.lighter(100), 1))
        painter.drawRect(left_port_rect)
        painter.drawRect(right_port_rect)
        
        painter.setPen(QPen(accent_color, 1))
        
        painter.drawLine(
            QPointF(-self.width/2 - port_width/2 + 1, 0),
            QPointF(-self.width/2 + port_width/2 - 1, 0)
        )
        
        painter.drawLine(
            QPointF(self.width/2 - port_width/2 + 1, 0),
            QPointF(self.width/2 + port_width/2 - 1, 0)
        )

    def get_input_connection_point(self):
        return QPointF(-self.width/2, 0)

    def get_output_connection_point(self):
        return QPointF(self.width/2, 0)
    
    def boundingRect(self):
        port_width = 6
        return QRectF(
            -self.width/2 - port_width/2,
            -self.height/2, 
            self.width + port_width,
            self.height
        )
    
    def draw_terminal_header(self, painter, accent_color):
        header_rect = QRectF(
            -self.width/2, 
            -self.height/2, 
            self.width, 
            self.title_height
        )
        
        header_gradient = QLinearGradient(
            QPointF(-self.width/2, -self.height/2), 
            QPointF(self.width/2, -self.height/2 + self.title_height)
        )
        header_gradient.setColorAt(0, accent_color.darker(200))
        header_gradient.setColorAt(1, accent_color.darker(150))
        
        painter.setBrush(QBrush(header_gradient))
        painter.setPen(QPen(accent_color.lighter(120), 1))
        painter.drawRect(header_rect)
        
        painter.setPen(QPen(self.cyber_colors['text_primary']))
        font = QFont("Consolas", 10, QFont.Weight.Bold)
        painter.setFont(font)
        
        symbol = self.get_node_symbol()
        # CORREÇÃO: Usa o método corrigido para obter o nome
        type_text = self.get_node_display_name().upper()
        header_text = f"{symbol} {type_text}"
        
        metrics = painter.fontMetrics()
        elided_text = metrics.elidedText(header_text, Qt.TextElideMode.ElideRight, 
                                       int(self.width - self.padding * 2))
        
        painter.drawText(
            int(-self.width/2 + self.padding), 
            int(-self.height/2 + 18), 
            elided_text
        )
    
    def draw_ascii_content(self, painter):
        content_lines = self.get_data_fields_to_display()
        
        painter.setPen(QPen(self.cyber_colors['text_secondary']))
        font = QFont("Consolas", 8)
        painter.setFont(font)
        
        start_y = -self.height/2 + self.title_height + self.padding
        
        max_width = self.width - (self.padding * 2)
        
        for i, line in enumerate(content_lines):
            y_pos = start_y + (i * self.line_height)
            
            if y_pos + self.line_height > self.height/2 - self.padding:
                painter.setPen(QPen(self.cyber_colors['warning']))
                painter.drawText(
                    int(-self.width/2 + self.padding), 
                    int(y_pos), 
                    "..."
                )
                break
            
            if i % 2 == 0:
                painter.setPen(QPen(self.cyber_colors['text_primary']))
            else:
                painter.setPen(QPen(self.cyber_colors['text_secondary']))

            prefix = "> " if i == 0 else "  "
            terminal_line = f"{prefix}{line}"
            
            metrics = painter.fontMetrics()
            elided_line = metrics.elidedText(terminal_line, Qt.TextElideMode.ElideRight, max_width)
            
            painter.drawText(
                int(-self.width/2 + self.padding), 
                int(y_pos), 
                elided_line
            )
    
    def draw_corner_symbol(self, painter, accent_color):
        symbol = self.get_node_symbol()
        font = QFont("Consolas", 7)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        
        painter.setPen(QPen(accent_color))
        painter.drawText(
            int(self.width/2 - metrics.boundingRect(symbol).width() - 4),
            int(self.height/2 - 4),
            symbol
        )
    
    def get_data_fields_to_display(self):
        lines = self.get_all_possible_fields()
        
        max_lines = 10
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append("...more")
            
        return lines
    
    def get_all_possible_fields(self):
        lines = []
        added_fields = set()
        
        def add_field(field_name, display_name=None, format_str="{}"):
            if field_name in self.node.data and self.node.data[field_name]:
                value = self.node.data[field_name]
                if value and str(value).strip() and str(value).strip() not in ['None', '']:
                    display = display_name or field_name.replace('_', ' ').title()
                    formatted_value = format_str.format(value)
                    
                    if field_name == 'compromised' and value:
                        lines.append("COMPROMISED")
                    elif field_name == 'successful' and value:
                        lines.append("SUCCESSFUL")
                    elif field_name == 'exploited' and value:
                        lines.append("EXPLOITED")
                    else:
                        line_content = f"{display}: {formatted_value}"
                        if field_name not in added_fields:
                            lines.append(line_content)
                            added_fields.add(field_name)
        
        # Mapeamento de campos específicos por tipo de node
        if self.node.type == 'analysis_environment':
            add_field('vm_name', 'Vm Name')
            add_field('os_version', 'Os Version')
            add_field('tools_installed', 'Tools Installed')
            add_field('network_setup', 'Network Setup')
            add_field('isolation_level', 'Isolation Level')
            
        elif self.node.type == 'malware_sample':
            add_field('sample_name', 'Sample Name')
            add_field('file_type', 'File Type')
            add_field('submission_source', 'Submission Source')
            add_field('analysis_status', 'Analysis Status')
            
        elif self.node.type == 'behavior_analysis':
            add_field('process_activity', 'Process Activity')
            add_field('network_connections', 'Network Connections')
            add_field('file_system_changes', 'File System Changes')
            add_field('registry_modifications', 'Registry Modifications')
            add_field('persistence_mechanism', 'Persistence Mechanism')
            add_field('anti_analysis_techniques', 'Anti Analysis Techniques')
            
        # Adiciona fallback para mostrar campos genéricos
        for key, value in self.node.data.items():
            if (key not in added_fields and 
                value and str(value).strip() and 
                str(value).strip() not in ['None', '']):
                
                display_name = key.replace('_', ' ').title()
                lines.append(f"{display_name}: {value}")
                added_fields.add(key)
        
        # Se não há campos para mostrar, mostra pelo menos o nome do node
        if not lines:
            node_name = self.get_node_display_name()
            lines.append(f"{node_name.upper()} Node")
            
        return lines

    def mouseDoubleClickEvent(self, event):
        self.node_updated.emit(self.node)
        super().mouseDoubleClickEvent(event)
    
    def contextMenuEvent(self, event):
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
        
        connect_action = QAction("CONNECT", self)
        connect_action.triggered.connect(lambda: self.connection_started.emit(self))
        menu.addAction(connect_action)
        
        menu.addSeparator()
        
        edit_action = QAction("EDIT NODE", self)
        edit_action.triggered.connect(lambda: self.node_updated.emit(self.node))
        menu.addAction(edit_action)

        delete_action = QAction("DELETE NODE", self)
        delete_action.triggered.connect(self.delete_node)
        menu.addAction(delete_action)
        
        menu.exec(event.screenPos())
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def delete_node(self):
        self.node_deleted.emit(self.node)
    
    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange and self.scene():
            self.node.position = value
            self.positionChanged.emit()
        return super().itemChange(change, value)
    
    def update_display(self):
        self.calculate_size()
        self.update()