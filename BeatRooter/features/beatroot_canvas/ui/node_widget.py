from pathlib import Path
import base64
from PyQt6.QtWidgets import QGraphicsObject, QMenu
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QPainter,
    QPainterPath,
    QPen,
    QColor,
    QBrush,
    QFont,
    QFontMetrics,
    QAction,
    QIcon,
    QPolygonF,
    QPixmap,
)
try:
    from PyQt6.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None
from features.beatroot_canvas.core import NodeFactory
from features.tools.core.tool_node_service import ToolNodeService


class NodeWidget(QGraphicsObject):
    node_updated = pyqtSignal(object)
    connection_started = pyqtSignal(object)
    duplicate_requested = pyqtSignal(object)
    move_started = pyqtSignal(object)
    move_finished = pyqtSignal(object)
    positionChanged = pyqtSignal()
    node_deleted = pyqtSignal(object)
    tool_run_requested = pyqtSignal(object)
    tool_edit_requested = pyqtSignal(object)
    tool_output_requested = pyqtSignal(object)
    output_details_requested = pyqtSignal(object)
    delete_selected_requested = pyqtSignal()
    _PROJECT_ROOT = Path(__file__).resolve().parents[4]
    _PACKAGE_ROOT = Path(__file__).resolve().parents[3]
    ICONS_DIRS = (
        _PROJECT_ROOT / "assets" / "icons" / "node",
        _PACKAGE_ROOT / "assets" / "icons" / "node",
        _PROJECT_ROOT / "assets" / "Beatrooter Icones",
        _PACKAGE_ROOT / "assets" / "Beatrooter Icones",
    )
    ICON_EXTENSIONS = (".svg", ".png", ".jpg", ".jpeg", ".webp")
    _ICON_INDEX = None
    _ICON_PIXMAP_CACHE = {}
    _SVG_RENDERER_CACHE = {}
    MORE_MARKER = "__OUTPUT_MORE__"
    Z_COLLAPSED = 1.0
    Z_EXPANDED = 2.0
    CORE_PREVIEW_SKIP_FIELDS = {
        "title",
        "summary",
        "owner",
        "asset_ref",
        "tags",
        "status",
        "severity",
        "confidence",
        "environment",
        "exposure",
        "data_classification",
        "image_data",
        "metadata",
        "exif_data",
        "png_info",
    }

    def __init__(self, node, category=None, project_type=None):
        super().__init__()
        self.node = node
        self.category = category
        self.project_type = str(project_type or "").strip().lower()

        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        self.is_expanded = False
        self.compact_size = 62
        self.compact_corner_radius = 14
        self.expanded_min_width = 244
        self.expanded_max_width = 430
        self.expanded_max_height = 480
        self.expanded_header_height = 48
        self.expanded_body_gap = 0
        self.expanded_body_inset = 0
        self.expanded_body_corner_radius = 5
        self.padding = 10
        self.line_height = 14
        self.output_label_height = 14
        self.port_radius = 3.5
        self.paint_margin = 3.0
        self.tool_bubble_width = 30.0
        self.tool_bubble_height = 20.0
        self.tool_bubble_gap = 4.0
        self.tool_pointer_height = 4.0

        self.cyber_colors = {
            "panel_bg": QColor(16, 24, 36),
            "panel_border": QColor(45, 62, 84),
            "text_primary": QColor(189, 203, 222),
            "text_secondary": QColor(125, 141, 165),
            "warning": QColor(216, 141, 108),
            "selection": QColor(108, 154, 220),
        }

        self.width = float(self.compact_size)
        self.height = float(self.compact_size)
        self._size_dirty = True
        self._cached_content_lines = []
        self._cached_header_text = ""
        self._truncated_indicator_rect = QRectF()
        self._output_preview_rect = QRectF()
        self._resizing_preview = False
        self._preview_resize_start_scene_pos = QPointF()
        self._preview_resize_start_width = 0.0
        self._preview_resize_start_height = 0.0
        self._preview_target_width = None
        self._preview_target_height = None
        self._preview_resize_handle_size = 12.0
        self._preview_pixmap_cache = None
        self._preview_pixmap_cache_key = None
        self._preview_target_initialized = False
        self._drag_origin_pos = QPointF()
        self._move_tracking_active = False

        self.setPos(node.position)

        self.calculate_size(force=True)
        self._update_stacking_order()

    def _update_stacking_order(self):
        self.setZValue(self.Z_EXPANDED if self.is_expanded else self.Z_COLLAPSED)

    def is_tool_node(self):
        return ToolNodeService.is_tool_node(self.node)

    def calculate_size(self, force=False):
        if not force and not self._size_dirty:
            return

        content_lines = self.get_data_fields_to_display()
        self._cached_content_lines = content_lines
        self._cached_header_text = self.get_node_display_name().upper()
        compact_size = float(82 if self.is_tool_node() else self.compact_size)

        if self.is_expanded:
            header_metrics = QFontMetrics(QFont("Consolas", 14, QFont.Weight.DemiBold))
            content_metrics = QFontMetrics(QFont("Consolas", 8))

            text_widths = [header_metrics.horizontalAdvance(self._cached_header_text) + 46]
            text_widths.extend(content_metrics.horizontalAdvance(line) for line in content_lines)
            max_text_width = max(text_widths) if text_widths else 0

            if self.node.type == "screenshot" and self._has_output_preview():
                self._ensure_preview_target_from_source()
                preview_width = float(self._preview_target_width or 280.0)
                preview_width = max(170.0, min(preview_width, self._expanded_width_limit() - (self.padding * 2)))
                required_width = max(self.expanded_min_width, preview_width + (self.padding * 2))
                new_width = float(max(self.expanded_min_width, min(required_width, self._expanded_width_limit())))

                preview_height = self._get_output_preview_height(new_width - (self.padding * 2))
                visible_lines = min(len(content_lines), 6)
                output_height = (
                    self.output_label_height
                    + (self.padding * 2)
                    + preview_height
                    + 12
                    + (visible_lines * self.line_height)
                    + 12
                )
                expanded_height = self.expanded_header_height + self.expanded_body_gap + output_height + 10
                new_height = float(min(expanded_height, self._expanded_height_limit()))
            else:
                required_width = max_text_width + (self.padding * 2) + 22
                new_width = float(max(self.expanded_min_width, min(required_width, self._expanded_width_limit())))

                visible_lines = min(len(content_lines), 8)
                output_height = self.output_label_height + (self.padding * 2) + (visible_lines * self.line_height)
                output_height = max(output_height, 108)
                if self._has_output_preview():
                    preview_height = self._get_output_preview_height(new_width - (self.padding * 2))
                    output_height += preview_height + 26

                expanded_height = self.expanded_header_height + self.expanded_body_gap + output_height + 10
                new_height = float(min(expanded_height, self._expanded_height_limit()))
        else:
            new_width = compact_size
            new_height = compact_size

        if new_width != self.width or new_height != self.height:
            self.prepareGeometryChange()
            self.width = new_width
            self.height = new_height

        self._size_dirty = False

    def get_node_accent_color(self):
        if self.is_tool_node():
            return QColor(ToolNodeService.get_tool_color(self.node.data.get("tool_name", "")))
        return QColor(NodeFactory.get_node_color(self.node.type, self.category))

    def get_team_border_color(self):
        if self.project_type == "redteam":
            return QColor(226, 88, 96)
        if self.project_type in ("blueteam", "soc_team"):
            return QColor(79, 182, 255)
        return None

    def get_node_display_name(self):
        if self.is_tool_node():
            tool_name = str(self.node.data.get("tool_name", "") or "").strip()
            return ToolNodeService.get_tool_display_name(tool_name)
        return NodeFactory.get_node_name(self.node.type, self.category)

    def get_node_symbol(self):
        if self.is_tool_node():
            tool_name = str(self.node.data.get("tool_name", "") or "").strip()
            return ToolNodeService.get_tool_short_label(tool_name)
        return NodeFactory.get_node_symbol(self.node.type, self.category)

    @classmethod
    def _normalize_icon_key(cls, value: str) -> str:
        raw = str(value or "").lower()
        return "".join(ch for ch in raw if ch.isalnum())

    @classmethod
    def _ensure_icon_index(cls):
        if cls._ICON_INDEX is not None:
            return

        cls._ICON_INDEX = {}
        for icons_dir in cls.ICONS_DIRS:
            if not icons_dir.exists():
                continue
            for icon_path in icons_dir.iterdir():
                if not icon_path.is_file() or icon_path.suffix.lower() not in cls.ICON_EXTENSIONS:
                    continue
                key = cls._normalize_icon_key(icon_path.stem)
                if key and key not in cls._ICON_INDEX:
                    cls._ICON_INDEX[key] = str(icon_path)

    def _resolve_icon_path(self):
        if self.is_tool_node():
            return None

        self._ensure_icon_index()
        if not self._ICON_INDEX:
            return None

        raw_candidates = [
            self.node.data.get("icon"),
            self.node.data.get("symbol"),
            self.node.data.get("name"),
            self.node.data.get("label"),
            self.get_node_display_name(),
            self.get_node_symbol(),
            self.node.type,
            str(self.node.type).replace("_", " "),
            str(self.node.type).replace("-", " "),
        ]

        key_candidates = []
        for candidate in raw_candidates:
            key = self._normalize_icon_key(candidate)
            if not key:
                continue
            key_candidates.append(key)
            if key.endswith("s") and len(key) > 1:
                key_candidates.append(key[:-1])
            else:
                key_candidates.append(f"{key}s")

        for key in key_candidates:
            icon_path = self._ICON_INDEX.get(key)
            if icon_path:
                return icon_path
        return None

    def _get_node_icon_pixmap(self, size: int):
        icon_path = self._resolve_icon_path()
        if not icon_path:
            return None

        if str(icon_path).lower().endswith(".svg"):
            return None

        cache_key = (icon_path, int(size))
        if cache_key in self._ICON_PIXMAP_CACHE:
            return self._ICON_PIXMAP_CACHE[cache_key]

        icon = QIcon(icon_path)
        base = icon.pixmap(int(size), int(size))
        if base.isNull():
            return None
        scaled = base.scaled(
            int(size),
            int(size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._ICON_PIXMAP_CACHE[cache_key] = scaled
        return scaled

    @classmethod
    def _get_svg_renderer(cls, icon_path: str):
        if QSvgRenderer is None:
            return None
        if not str(icon_path).lower().endswith(".svg"):
            return None

        renderer = cls._SVG_RENDERER_CACHE.get(icon_path)
        if renderer is not None:
            return renderer

        renderer = QSvgRenderer(icon_path)
        if not renderer.isValid():
            return None
        cls._SVG_RENDERER_CACHE[icon_path] = renderer
        return renderer

    def _draw_icon_in_rect(self, painter: QPainter, target_rect: QRectF, nominal_size: int) -> bool:
        icon_path = self._resolve_icon_path()
        if not icon_path:
            return False

        svg_renderer = self._get_svg_renderer(icon_path)
        if svg_renderer is not None:
            svg_renderer.render(painter, target_rect)
            return True

        icon_pixmap = self._get_node_icon_pixmap(nominal_size)
        if icon_pixmap and not icon_pixmap.isNull():
            draw_rect = QRectF(
                target_rect.center().x() - (icon_pixmap.width() / 2),
                target_rect.center().y() - (icon_pixmap.height() / 2),
                icon_pixmap.width(),
                icon_pixmap.height(),
            )
            painter.drawPixmap(draw_rect.toRect(), icon_pixmap)
            return True

        return False

    def boundingRect(self):
        top_extra = self._tool_top_extent()
        bottom_extra = self._tool_bottom_extent()
        return QRectF(
            -self.width / 2 - self.paint_margin,
            -self.height / 2 - top_extra - self.paint_margin,
            self.width + (self.paint_margin * 2),
            self.height + top_extra + bottom_extra + (self.paint_margin * 2),
        )

    def paint(self, painter, option, widget):
        self.calculate_size()
        accent_color = self.get_node_accent_color()

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        if self.is_expanded:
            self.draw_expanded_node(painter, accent_color)
        else:
            self.draw_compact_node(painter, accent_color)

        self.draw_connection_ports(painter, accent_color)
        self.draw_tool_controls(painter, accent_color)

        if self.isSelected():
            selection_pen = QPen(self.cyber_colors["selection"], 1.2)
            selection_pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(selection_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.is_expanded:
                painter.drawRoundedRect(self._expanded_outer_rect().adjusted(-1, -1, 1, 1), 12, 12)
            else:
                painter.drawRoundedRect(
                    QRectF(-self.width / 2 - 1, -self.height / 2 - 1, self.width + 2, self.height + 2),
                    self.compact_corner_radius + 1,
                    self.compact_corner_radius + 1,
                )

    def draw_compact_node(self, painter, accent_color):
        card_rect = QRectF(-self.width / 2, -self.height / 2, self.width, self.height)
        border_color = self.cyber_colors["panel_border"]

        painter.setBrush(QBrush(self.cyber_colors["panel_bg"]))
        painter.setPen(QPen(border_color, 1.25))
        painter.drawRoundedRect(card_rect, self.compact_corner_radius, self.compact_corner_radius)

        glow = QColor(accent_color)
        glow.setAlpha(120)
        painter.setPen(QPen(glow, 1.0))
        painter.drawRoundedRect(card_rect.adjusted(2, 2, -2, -2), self.compact_corner_radius - 2, self.compact_corner_radius - 2)

        if self.is_tool_node():
            self.draw_tool_compact_content(painter, card_rect, accent_color)
            return

        icon_size = int(min(card_rect.width(), card_rect.height()) * 0.76)
        icon_target = QRectF(
            card_rect.center().x() - (icon_size / 2),
            card_rect.center().y() - (icon_size / 2),
            icon_size,
            icon_size,
        )
        if self._draw_icon_in_rect(painter, icon_target, icon_size):
            return

        painter.setPen(QPen(self.cyber_colors["text_primary"]))
        painter.setFont(QFont("Consolas", 9, QFont.Weight.DemiBold))
        painter.drawText(card_rect, Qt.AlignmentFlag.AlignCenter, self._short_symbol())

    def draw_tool_compact_content(self, painter, card_rect, accent_color):
        short_label = self._short_symbol()
        status = str(self.node.data.get("last_status", "idle") or "idle").lower()
        target = str(self.node.data.get("resolved_target", "") or self.node.data.get("manual_target", "")).strip()

        painter.setPen(QPen(QColor(236, 242, 251)))
        painter.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        painter.drawText(
            QRectF(card_rect.left() + 4, card_rect.top() + 6, card_rect.width() - 8, 22),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            short_label,
        )

        painter.setPen(QPen(QColor(accent_color)))
        painter.setFont(QFont("Consolas", 7))
        status_text = {
            "running": "RUN",
            "success": "OK",
            "error": "ERR",
        }.get(status, "IDLE")
        painter.drawText(
            QRectF(card_rect.left() + 6, card_rect.center().y() - 2, card_rect.width() - 12, 12),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            status_text,
        )

        painter.setPen(QPen(self.cyber_colors["text_secondary"]))
        painter.setFont(QFont("Consolas", 6))
        footer = painter.fontMetrics().elidedText(
            target if target else "LINK INPUT",
            Qt.TextElideMode.ElideMiddle,
            int(card_rect.width() - 12),
        )
        painter.drawText(
            QRectF(card_rect.left() + 6, card_rect.bottom() - 18, card_rect.width() - 12, 12),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            footer,
        )

    def draw_expanded_node(self, painter, accent_color):
        outer_rect = self._expanded_outer_rect()
        header_rect = self._header_rect()
        output_rect = self._output_rect()
        border_color = self.cyber_colors["panel_border"]
        accent_line_color = QColor(accent_color)

        painter.setBrush(QBrush(QColor(13, 21, 32)))
        painter.setPen(QPen(border_color, 1.25))
        painter.drawRoundedRect(outer_rect, 12, 12)

        header_fill = QColor(20, 31, 46)
        accent_wash = QColor(accent_color)
        accent_wash.setAlpha(56)

        # Clip header fill to the rounded outer card, preventing rectangular overflow on corners.
        rounded_clip = QPainterPath()
        rounded_clip.addRoundedRect(outer_rect, 12, 12)
        painter.save()
        painter.setClipPath(rounded_clip)

        painter.setBrush(QBrush(header_fill))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(header_rect.adjusted(1, 1, -1, 0))

        painter.setBrush(QBrush(accent_wash))
        painter.drawRect(header_rect.adjusted(1, 1, -1, 0))
        painter.restore()

        painter.setPen(QPen(QColor(accent_line_color), 1.0))
        painter.drawLine(
            QPointF(header_rect.left() + 1, header_rect.bottom()),
            QPointF(header_rect.right() - 1, header_rect.bottom()),
        )

        icon_box = QRectF(header_rect.left() + 8, header_rect.top() + 8, 32, 32)
        painter.setBrush(QBrush(QColor(18, 25, 35)))
        painter.setPen(QPen(border_color, 1.0))
        painter.drawRoundedRect(icon_box, 4, 4)
        header_icon_target = QRectF(icon_box.left() + 4, icon_box.top() + 4, 24, 24)
        if not self._draw_icon_in_rect(painter, header_icon_target, 24):
            painter.setPen(QPen(self.cyber_colors["text_primary"]))
            painter.setFont(QFont("Consolas", 7, QFont.Weight.DemiBold))
            painter.drawText(icon_box, Qt.AlignmentFlag.AlignCenter, self._short_symbol())

        painter.setPen(QPen(QColor(235, 241, 252)))
        painter.setFont(QFont("Consolas", 14, QFont.Weight.DemiBold))
        title = painter.fontMetrics().elidedText(
            self._cached_header_text,
            Qt.TextElideMode.ElideRight,
            int(header_rect.width() - 58),
        )
        painter.drawText(
            QRectF(header_rect.left() + 50, header_rect.top(), header_rect.width() - 58, header_rect.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            title,
        )

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(38, 55, 78), 1.0, Qt.PenStyle.DotLine))
        painter.drawLine(
            QPointF(output_rect.left() + self.padding, output_rect.top() + self.output_label_height + 4),
            QPointF(output_rect.right() - self.padding, output_rect.top() + self.output_label_height + 4),
        )

        painter.setPen(QPen(QColor(accent_color)))
        painter.setFont(QFont("Consolas", 8, QFont.Weight.DemiBold))
        painter.drawText(
            int(output_rect.left() + self.padding),
            int(output_rect.top() + self.padding + 2),
            "OUTPUT",
        )

        self.draw_output_preview(painter, output_rect)
        self.draw_output_lines(painter, output_rect)
        self.draw_preview_resize_handle(painter)

    def draw_output_preview(self, painter, output_rect):
        self._output_preview_rect = QRectF()
        preview_pixmap = self._get_output_preview_pixmap()
        if preview_pixmap is None or preview_pixmap.isNull():
            return
        preview_height = self._get_output_preview_height(output_rect.width() - (self.padding * 2))
        output_lines_count = len(self._cached_content_lines or [])
        reserved_lines = min(max(output_lines_count, 2), 6)
        max_available_height = max(
            64.0,
            float(output_rect.height())
            - (self.output_label_height + self.padding * 2 + (self.line_height * (reserved_lines + 1))),
        )
        preview_height = min(preview_height, max_available_height)
        if preview_height <= 0:
            return

        preview_rect = QRectF(
            output_rect.left() + self.padding,
            output_rect.top() + self.output_label_height + self.padding + 10,
            output_rect.width() - (self.padding * 2),
            preview_height,
        )
        painter.setBrush(QBrush(QColor(42, 42, 42)))
        painter.setPen(QPen(QColor(90, 98, 110), 1.0))
        painter.drawRect(preview_rect)

        scaled = preview_pixmap.scaled(
            int(preview_rect.width() - 4),
            int(preview_rect.height() - 4),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image_rect = QRectF(
            preview_rect.center().x() - (scaled.width() / 2),
            preview_rect.center().y() - (scaled.height() / 2),
            scaled.width(),
            scaled.height(),
        )
        painter.drawPixmap(image_rect.toRect(), scaled)
        self._output_preview_rect = preview_rect
        self._sync_current_dimensions(float(scaled.width()), float(scaled.height()))

    def draw_output_lines(self, painter, output_rect):
        content_lines = self._cached_content_lines or ["No output yet."]
        self._truncated_indicator_rect = QRectF()

        painter.setFont(QFont("Consolas", 8))
        max_width = int(output_rect.width() - (self.padding * 2))
        start_y = output_rect.top() + self.output_label_height + self.padding + 5
        if not self._output_preview_rect.isNull():
            start_y = self._output_preview_rect.bottom() + self.padding + 8
        max_lines = max(1, int((output_rect.height() - (self.output_label_height + self.padding * 2 + 8)) / self.line_height))
        if not self._output_preview_rect.isNull():
            max_lines = max(
                1,
                int((output_rect.bottom() - start_y - self.padding - 6) / self.line_height),
            )

        ellipsis_drawn = False
        ellipsis_x = float(output_rect.left() + self.padding)
        ellipsis_y = float(output_rect.bottom() - self.padding - 2)

        for i, line in enumerate(content_lines):
            y_pos = start_y + (i * self.line_height)
            if line == self.MORE_MARKER:
                painter.setPen(QPen(self.cyber_colors["warning"]))
                painter.drawText(int(ellipsis_x), int(y_pos), "...")
                self._truncated_indicator_rect = QRectF(ellipsis_x - 2, y_pos - self.line_height + 2, 28, self.line_height + 4)
                ellipsis_drawn = True
                break

            if i >= max_lines:
                painter.setPen(QPen(self.cyber_colors["warning"]))
                painter.drawText(int(ellipsis_x), int(y_pos), "...")
                self._truncated_indicator_rect = QRectF(ellipsis_x - 2, y_pos - self.line_height + 2, 28, self.line_height + 4)
                ellipsis_drawn = True
                break

            painter.setPen(QPen(self.cyber_colors["text_secondary"]))
            elided_line = painter.fontMetrics().elidedText(
                line,
                Qt.TextElideMode.ElideRight,
                max_width,
            )
            painter.drawText(int(output_rect.left() + self.padding), int(y_pos), elided_line)
            ellipsis_y = min(float(y_pos + self.line_height), float(output_rect.bottom() - self.padding - 2))

        # Always show clickable output details marker in expanded nodes.
        if not ellipsis_drawn:
            painter.setPen(QPen(self.cyber_colors["warning"]))
            painter.drawText(int(ellipsis_x), int(ellipsis_y), "...")
            self._truncated_indicator_rect = QRectF(ellipsis_x - 2, ellipsis_y - self.line_height + 2, 28, self.line_height + 4)

    def _expanded_outer_rect(self):
        return QRectF(-self.width / 2, -self.height / 2, self.width, self.height)

    def _header_rect(self):
        outer_rect = self._expanded_outer_rect()
        return QRectF(outer_rect.left(), outer_rect.top(), outer_rect.width(), self.expanded_header_height)

    def _output_rect(self):
        outer_rect = self._expanded_outer_rect()
        output_top = outer_rect.top() + self.expanded_header_height + self.expanded_body_gap
        return QRectF(
            outer_rect.left() + self.expanded_body_inset,
            output_top,
            outer_rect.width() - (self.expanded_body_inset * 2),
            outer_rect.height() - self.expanded_header_height - self.expanded_body_gap,
        )

    def _connection_anchor_y(self):
        if self.is_expanded:
            return -self.height / 2 + (self.expanded_header_height / 2)
        return 0.0

    def _short_symbol(self):
        raw_symbol = (self.get_node_symbol() or "[NODE]").strip()
        normalized = raw_symbol.strip("[]").strip()
        if not normalized:
            return "N"
        if len(normalized) <= 4:
            return normalized
        return normalized[:3]

    def draw_connection_ports(self, painter, accent_color):
        # Connection anchors still exist for edges, but visual port dots are hidden.
        return

    def draw_preview_resize_handle(self, painter):
        if not self._can_resize_preview() or self._output_preview_rect.isNull():
            return
        handle_rect = self._preview_resize_handle_rect()
        painter.setPen(QPen(QColor(108, 154, 220, 185), 1.2))
        painter.setBrush(QBrush(QColor(32, 46, 70, 160)))
        painter.drawRoundedRect(handle_rect, 2, 2)
        painter.setPen(QPen(QColor(168, 204, 255, 190), 1.0))
        painter.drawLine(
            QPointF(handle_rect.left() + 4, handle_rect.bottom() - 2),
            QPointF(handle_rect.right() - 2, handle_rect.top() + 4),
        )
        painter.drawLine(
            QPointF(handle_rect.left() + 7, handle_rect.bottom() - 2),
            QPointF(handle_rect.right() - 2, handle_rect.top() + 7),
        )

    def draw_tool_controls(self, painter, accent_color):
        if not self.is_tool_node():
            return

        self._draw_tool_bubble(painter, self._tool_run_rect(), accent_color, top_bubble=True, mode="run")
        self._draw_tool_bubble(painter, self._tool_edit_rect(), accent_color, top_bubble=False, mode="edit")

    def _draw_tool_bubble(self, painter, rect, accent_color, top_bubble, mode):
        is_running = str(self.node.data.get("last_status", "") or "").lower() == "running"
        compatible = bool(self.node.data.get("compatible")) or bool(str(self.node.data.get("manual_target", "")).strip())

        background = QColor(18, 26, 38)
        border = QColor(56, 76, 101)
        if mode == "run" and compatible:
            border = QColor(48, 214, 122) if not is_running else QColor(240, 173, 78)
            background = QColor(16, 39, 28) if not is_running else QColor(54, 41, 14)
        elif mode == "run" and not compatible:
            border = QColor(244, 63, 94)
            background = QColor(44, 20, 29)
        elif mode == "edit":
            border = QColor(96, 165, 250)
            background = QColor(16, 31, 54)

        center_x = rect.center().x()
        if top_bubble:
            tip_base_y = rect.bottom() - 0.5
            tip_y = -self.height / 2 - 2
            tip = [
                QPointF(center_x - 5, tip_base_y),
                QPointF(center_x, tip_y),
                QPointF(center_x + 5, tip_base_y),
            ]
        else:
            tip_base_y = rect.top() + 0.5
            tip_y = self.height / 2 + 2
            tip = [
                QPointF(center_x + 5, tip_base_y),
                QPointF(center_x, tip_y),
                QPointF(center_x - 5, tip_base_y),
            ]

        bubble_path = QPainterPath()
        bubble_path.addRoundedRect(rect, 8, 8)
        tip_path = QPainterPath()
        tip_path.addPolygon(QPolygonF(tip))
        bubble_path = bubble_path.united(tip_path)

        painter.setBrush(QBrush(background))
        painter.setPen(QPen(border, 1.15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(bubble_path)

        if mode == "run":
            self._draw_tool_run_icon(painter, rect, compatible, is_running)
        else:
            self._draw_tool_edit_icon(painter, rect)

    def _draw_tool_run_icon(self, painter, rect, compatible, is_running):
        painter.save()
        if is_running:
            painter.setPen(QPen(QColor(255, 233, 175), 1.2))
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "...")
            painter.restore()
            return

        if not compatible:
            painter.setPen(QPen(QColor(255, 118, 144), 2.0))
            painter.drawLine(
                QPointF(rect.left() + 9, rect.top() + 6),
                QPointF(rect.right() - 9, rect.bottom() - 6),
            )
            painter.drawLine(
                QPointF(rect.right() - 9, rect.top() + 6),
                QPointF(rect.left() + 9, rect.bottom() - 6),
            )
            painter.restore()
            return

        triangle = QPainterPath()
        triangle.moveTo(rect.left() + 11, rect.top() + 5)
        triangle.lineTo(rect.right() - 9, rect.center().y())
        triangle.lineTo(rect.left() + 11, rect.bottom() - 5)
        triangle.closeSubpath()
        painter.setPen(QPen(QColor(170, 255, 202), 1.0))
        painter.setBrush(QBrush(QColor(95, 235, 144)))
        painter.drawPath(triangle)
        painter.restore()

    def _draw_tool_edit_icon(self, painter, rect):
        painter.save()
        painter.setPen(QPen(QColor(150, 204, 255), 1.8))
        painter.drawLine(
            QPointF(rect.left() + 10, rect.bottom() - 6),
            QPointF(rect.right() - 10, rect.top() + 6),
        )
        painter.setPen(QPen(QColor(96, 165, 250), 1.4))
        painter.drawLine(
            QPointF(rect.left() + 12, rect.bottom() - 7),
            QPointF(rect.right() - 8, rect.top() + 8),
        )
        painter.setPen(QPen(QColor(196, 230, 255), 1.2))
        painter.drawLine(
            QPointF(rect.left() + 8, rect.bottom() - 4),
            QPointF(rect.left() + 12, rect.bottom() - 8),
        )
        painter.restore()

    def _tool_top_extent(self):
        if not self.is_tool_node():
            return 0.0
        return self.tool_bubble_height + self.tool_bubble_gap + self.tool_pointer_height

    def _tool_bottom_extent(self):
        if not self.is_tool_node():
            return 0.0
        return self.tool_bubble_height + self.tool_bubble_gap + self.tool_pointer_height

    def _tool_run_rect(self):
        return QRectF(
            -(self.tool_bubble_width / 2),
            (-self.height / 2) - self.tool_bubble_gap - self.tool_pointer_height - self.tool_bubble_height,
            self.tool_bubble_width,
            self.tool_bubble_height,
        )

    def _tool_edit_rect(self):
        return QRectF(
            -(self.tool_bubble_width / 2),
            (self.height / 2) + self.tool_bubble_gap + self.tool_pointer_height,
            self.tool_bubble_width,
            self.tool_bubble_height,
        )

    def get_input_connection_point(self):
        return QPointF(-self.width / 2, self._connection_anchor_y())

    def get_output_connection_point(self):
        return QPointF(self.width / 2, self._connection_anchor_y())

    def draw_corner_symbol(self, painter, accent_color):
        symbol = self.get_node_symbol()
        painter.setFont(QFont("Consolas", 7))
        metrics = painter.fontMetrics()

        color = QColor(accent_color)
        color.setAlpha(170)
        painter.setPen(QPen(color))
        painter.drawText(
            int(self.width / 2 - metrics.boundingRect(symbol).width() - 6),
            int(self.height / 2 - 6),
            symbol,
        )

    def get_data_fields_to_display(self):
        lines = self.get_all_possible_fields()
        max_lines = 6 if (self.is_expanded and self._has_output_preview()) else (10 if self.is_expanded else 6)

        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append(self.MORE_MARKER)

        return lines

    def get_all_possible_fields(self):
        if self.is_tool_node():
            return self._get_tool_display_lines()

        lines = []
        added_fields = set()

        def add_field(field_name, display_name=None, format_str="{}"):
            if field_name in self.CORE_PREVIEW_SKIP_FIELDS:
                return
            if field_name in self.node.data and self.node.data[field_name]:
                value = self.node.data[field_name]
                if value and str(value).strip() and str(value).strip() not in ["None", ""]:
                    display = display_name or field_name.replace("_", " ").title()
                    formatted_value = self._format_display_value(value, format_str)

                    if field_name == "compromised" and value:
                        lines.append("COMPROMISED")
                    elif field_name == "successful" and value:
                        lines.append("SUCCESSFUL")
                    elif field_name == "exploited" and value:
                        lines.append("EXPLOITED")
                    else:
                        if field_name not in added_fields:
                            lines.append(f"{display}: {formatted_value}")
                            added_fields.add(field_name)

        if self._add_flipper_priority_fields(add_field):
            for key, value in self.node.data.items():
                if (
                    key not in added_fields
                    and key not in self.CORE_PREVIEW_SKIP_FIELDS
                    and key not in self._flipper_generic_skip_fields()
                    and value
                    and str(value).strip()
                    and str(value).strip() not in ["None", ""]
                ):
                    display_name = key.replace("_", " ").title()
                    lines.append(f"{display_name}: {self._format_display_value(value)}")
                    added_fields.add(key)

            if not lines:
                lines.append(f"{self.get_node_display_name().upper()} Node")
            return lines

        if self.node.type == "analysis_environment":
            add_field("vm_name", "Vm Name")
            add_field("os_version", "Os Version")
            add_field("tools_installed", "Tools Installed")
            add_field("network_setup", "Network Setup")
            add_field("isolation_level", "Isolation Level")
        elif self.node.type == "malware_sample":
            add_field("sample_name", "Sample Name")
            add_field("file_type", "File Type")
            add_field("submission_source", "Submission Source")
            add_field("analysis_status", "Analysis Status")
        elif self.node.type == "behavior_analysis":
            add_field("process_activity", "Process Activity")
            add_field("network_connections", "Network Connections")
            add_field("file_system_changes", "File System Changes")
            add_field("registry_modifications", "Registry Modifications")
            add_field("persistence_mechanism", "Persistence Mechanism")
            add_field("anti_analysis_techniques", "Anti Analysis Techniques")

        for key, value in self.node.data.items():
            if (
                key not in added_fields
                and key not in self.CORE_PREVIEW_SKIP_FIELDS
                and value
                and str(value).strip()
                and str(value).strip() not in ["None", ""]
            ):
                display_name = key.replace("_", " ").title()
                lines.append(f"{display_name}: {value}")
                added_fields.add(key)

        if not lines:
            lines.append(f"{self.get_node_display_name().upper()} Node")

        return lines

    def _format_display_value(self, value, format_str="{}"):
        if isinstance(value, (list, tuple, set)):
            joined = ", ".join(str(item) for item in value if str(item).strip())
            return format_str.format(joined)
        if isinstance(value, bool):
            return format_str.format("yes" if value else "no")
        return format_str.format(value)

    def _add_flipper_priority_fields(self, add_field):
        if not self.node.type.startswith("flipper_"):
            return False

        if self.node.type == "flipper_subghz_signal":
            add_field("frequency_mhz", "Frequency", "{:.3f} MHz")
            add_field("protocol", "Protocol")
            add_field("modulation", "Modulation")
            add_field("target_devices", "Targets")
            add_field("attack_surface", "Attack Surface")
            add_field("key_preview", "Key")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_badusb_script":
            add_field("script_type", "Script Type")
            add_field("objective", "Objective")
            add_field("target_os", "Target OS")
            add_field("command_count", "Commands")
            add_field("common_commands", "Common Cmds")
            add_field("binary_artifacts", "Binaries")
            add_field("external_urls", "URLs")
            add_field("script_preview", "Script")
            return True

        if self.node.type == "flipper_ir_signal":
            add_field("protocol", "Protocol")
            add_field("frequency_hz", "Frequency", "{} Hz")
            add_field("target_device_type", "Target Device")
            add_field("command", "Command")
            add_field("address", "Address")
            add_field("duty_cycle", "Duty Cycle")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_nfc_dump":
            add_field("technology", "Technology")
            add_field("protocol", "Protocol")
            add_field("frequency_khz", "Frequency", "{} kHz")
            add_field("uid", "UID")
            add_field("sak", "SAK")
            add_field("atqa", "ATQA")
            add_field("memory_layout", "Memory")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_rfid_dump":
            add_field("rfid_type", "RFID Type")
            add_field("frequency_khz", "Frequency", "{} kHz")
            add_field("key_value", "Key")
            add_field("bit_length", "Bits")
            add_field("facility_code", "Facility")
            add_field("card_id", "Card ID")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_ibutton_key":
            add_field("ibutton_type", "iButton Type")
            add_field("key_value", "Key")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_wifi_artifact":
            add_field("artifact_kind", "Artifact")
            add_field("attack_indicators", "Indicators")
            add_field("target_networks", "Targets")
            add_field("deauth_events", "Deauth")
            add_field("handshake_events", "Handshakes")
            add_field("attack_result", "Result")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_log_artifact":
            add_field("event_count", "Events")
            add_field("critical_events", "Critical")
            add_field("attack_indicators", "Indicators")
            add_field("attack_result", "Result")
            add_field("last_timestamp", "Last Seen")
            add_field("content_preview", "Content")
            return True

        if self.node.type == "flipper_file":
            add_field("module", "Module")
            add_field("file_extension", "Extension")
            add_field("file_size_bytes", "Size", "{} B")
            add_field("parser_status", "Parser")
            add_field("content_preview", "Content")
            add_field("relative_path", "Path")
            return True

        add_field("module", "Module")
        add_field("file_name", "File")
        add_field("relative_path", "Path")
        return True

    def _flipper_generic_skip_fields(self):
        return {
            "title",
            "summary",
            "status",
            "severity",
            "confidence",
            "environment",
            "exposure",
            "data_classification",
            "notes",
            "scan_timestamp",
            "workspace_path",
        }

    def _get_tool_display_lines(self):
        lines = []
        target = str(self.node.data.get("resolved_target", "") or self.node.data.get("manual_target", "")).strip()
        source_label = str(self.node.data.get("target_source_label", "") or "").strip()
        status = str(self.node.data.get("last_status", "idle") or "idle").strip().upper()
        summary = str(self.node.data.get("output_summary", "") or "").strip()
        reason = str(self.node.data.get("compatibility_reason", "") or "").strip()
        command = str(self.node.data.get("last_command", "") or "").strip()

        if target:
            lines.append(f"Target: {target}")
        elif reason:
            lines.append(f"Input: {reason}")

        lines.append(f"Status: {status}")

        if source_label:
            lines.append(f"Source: {source_label}")

        if summary:
            lines.append(f"Result: {summary}")

        if command:
            lines.append(f"Cmd: {command}")

        return lines or [f"{self.get_node_display_name().upper()} Node"]

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            has_output = (
                bool(self.node.data.get("has_output"))
                or bool(
                    str(
                        self.node.data.get("last_output_preview", "")
                        or self.node.data.get("last_output", "")
                        or self.node.data.get("last_error", "")
                    ).strip()
                )
            )
            if self.is_tool_node() and has_output:
                self.tool_output_requested.emit(self.node)
                event.accept()
                return
            self.toggle_expanded()
            self.node_updated.emit(self.node)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #141f31;
                color: #d4deec;
                border: 1px solid #2c3b52;
                font-family: 'Consolas';
                font-size: 10px;
            }
            QMenu::item {
                padding: 6px 18px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #2a3b56;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #2c3b52;
            }
            """
        )

        connect_action = QAction("Connect", self)
        connect_action.triggered.connect(lambda: self.connection_started.emit(self))
        menu.addAction(connect_action)

        menu.addSeparator()

        if self.is_tool_node():
            run_action = QAction("Run Tool", self)
            run_action.triggered.connect(lambda: self.tool_run_requested.emit(self.node))
            menu.addAction(run_action)

            edit_tool_action = QAction("Edit Tool", self)
            edit_tool_action.triggered.connect(lambda: self.tool_edit_requested.emit(self.node))
            menu.addAction(edit_tool_action)

            view_output_action = QAction("View Output", self)
            view_output_action.triggered.connect(lambda: self.tool_output_requested.emit(self.node))
            menu.addAction(view_output_action)

            menu.addSeparator()

        edit_action = QAction("Edit Node", self)
        edit_action.triggered.connect(lambda: self.node_updated.emit(self.node))
        menu.addAction(edit_action)

        duplicate_action = QAction("Duplicate Node", self)
        duplicate_action.triggered.connect(lambda: self.duplicate_requested.emit(self.node))
        menu.addAction(duplicate_action)

        delete_action = QAction("Delete Node", self)
        delete_action.triggered.connect(self.delete_node)
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
            delete_all_action = QAction(f"Delete All Selected ({len(selected_items)})", self)
            delete_all_action.triggered.connect(self.delete_selected_requested.emit)
            menu.addAction(delete_all_action)

        menu.exec(event.screenPos())
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            if self._can_resize_preview() and self._is_on_preview_resize_handle(event.pos()):
                self._resizing_preview = True
                self._preview_resize_start_scene_pos = event.scenePos()
                self._preview_resize_start_width = float(self._output_preview_rect.width())
                self._preview_resize_start_height = float(self._output_preview_rect.height())
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                event.accept()
                return
            if self._truncated_indicator_rect.contains(event.pos()):
                self.output_details_requested.emit(self.node)
                event.accept()
                return
            if self.is_tool_node():
                if self._tool_run_rect().contains(event.pos()):
                    self.node_updated.emit(self.node)
                    self.tool_run_requested.emit(self.node)
                    event.accept()
                    return
                if self._tool_edit_rect().contains(event.pos()):
                    self.node_updated.emit(self.node)
                    self.tool_edit_requested.emit(self.node)
                    event.accept()
                    return
            self._drag_origin_pos = QPointF(self.pos())
            self._move_tracking_active = True
            self.move_started.emit(self.node)
            self.node_updated.emit(self.node)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing_preview:
            delta = event.scenePos() - self._preview_resize_start_scene_pos
            target_width = self._preview_resize_start_width + delta.x()
            target_height = self._preview_resize_start_height + delta.y()
            self._preview_target_width = max(170.0, min(target_width, self._expanded_width_limit() - (self.padding * 2)))
            self._preview_target_height = max(64.0, min(target_height, self._preview_height_limit()))
            self._size_dirty = True
            self.calculate_size(force=True)
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing_preview and event.button() == Qt.MouseButton.LeftButton:
            self._resizing_preview = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._size_dirty = True
            self.calculate_size(force=True)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)
        if self._move_tracking_active and event.button() == Qt.MouseButton.LeftButton:
            self._move_tracking_active = False
            self.move_finished.emit(self.node)

    def hoverMoveEvent(self, event):
        if self._can_resize_preview() and self._is_on_preview_resize_handle(event.pos()):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif not self._resizing_preview:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._resizing_preview:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def delete_node(self):
        self.node_deleted.emit(self.node)

    def itemChange(self, change, value):
        if getattr(self, "_resizing_preview", False) and change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            return self.pos()
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange and self.scene():
            self.node.position = value
            self.positionChanged.emit()
        return super().itemChange(change, value)

    def update_display(self):
        self._size_dirty = True
        self.calculate_size(force=True)
        self.update()
        self.positionChanged.emit()

    def toggle_expanded(self):
        self.is_expanded = not self.is_expanded
        if not self.is_expanded:
            self._preview_target_width = None
            self._preview_target_height = None
        self._update_stacking_order()
        self._size_dirty = True
        self.calculate_size(force=True)
        self.update()
        self.positionChanged.emit()

    def _has_output_preview(self):
        return self._get_output_preview_pixmap() is not None

    def _get_output_preview_pixmap(self):
        if self.node.type != "screenshot":
            return None

        image_data = str(self.node.data.get("image_data", "") or "").strip()
        file_path = str(self.node.data.get("file_path", "") or "").strip()
        cache_key = (image_data[:96], len(image_data), file_path)
        if self._preview_pixmap_cache_key == cache_key:
            return self._preview_pixmap_cache
        self._preview_target_initialized = False

        if image_data:
            try:
                raw = base64.b64decode(image_data)
                pixmap = QPixmap()
                if pixmap.loadFromData(raw):
                    self._preview_pixmap_cache = pixmap
                    self._preview_pixmap_cache_key = cache_key
                    return pixmap
            except Exception:
                pass

        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self._preview_pixmap_cache = pixmap
                self._preview_pixmap_cache_key = cache_key
                return pixmap

        self._preview_pixmap_cache = None
        self._preview_pixmap_cache_key = cache_key
        return None

    def _ensure_preview_target_from_source(self):
        if self._preview_target_initialized:
            return
        pixmap = self._get_output_preview_pixmap()
        if pixmap is None or pixmap.isNull():
            return
        original_w = float(max(1, int(pixmap.width())))
        original_h = float(max(1, int(pixmap.height())))
        self._preview_target_width = max(170.0, min(original_w, self._expanded_width_limit() - (self.padding * 2)))
        self._preview_target_height = max(64.0, min(original_h, self._preview_height_limit()))
        self._sync_current_dimensions(self._preview_target_width, self._preview_target_height)
        self._preview_target_initialized = True

    def _get_output_preview_height(self, available_width):
        preview_pixmap = self._get_output_preview_pixmap()
        if preview_pixmap is None or preview_pixmap.isNull():
            return 0.0

        if self.node.type == "screenshot" and self._preview_target_height is not None:
            return max(64.0, min(float(self._preview_target_height), self._preview_height_limit()))

        image_width = max(1, int(preview_pixmap.width()))
        image_height = max(1, int(preview_pixmap.height()))
        drawable_width = max(40.0, float(available_width) - 4.0)
        scaled_height = drawable_width * (image_height / image_width)
        return max(64.0, min(scaled_height, self._preview_height_limit()))

    def _preview_height_limit(self):
        if self.node.type == "screenshot":
            # Screenshot preview should be allowed to consume nearly all available body space.
            return 9999.0
        return 220.0

    def _expanded_width_limit(self):
        if self.node.type == "screenshot":
            return 12000.0
        return float(self.expanded_max_width)

    def _expanded_height_limit(self):
        if self.node.type == "screenshot":
            return 12000.0
        return float(self.expanded_max_height)

    def _can_resize_preview(self):
        return self.is_expanded and self.node.type == "screenshot"

    def _preview_resize_handle_rect(self):
        size = self._preview_resize_handle_size
        rect = self._output_preview_rect
        return QRectF(rect.right() - size - 3.0, rect.bottom() - size - 3.0, size, size)

    def _is_on_preview_resize_handle(self, pos):
        return self._preview_resize_handle_rect().contains(pos)

    def _sync_current_dimensions(self, preview_width: float, preview_height: float):
        if self.node.type != "screenshot":
            return
        width = max(1, int(round(float(preview_width))))
        height = max(1, int(round(float(preview_height))))
        self.node.data["current_dimensions"] = f"{width} x {height}"
