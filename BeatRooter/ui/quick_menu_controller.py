from PyQt6.QtCore import QObject, QEvent, QPropertyAnimation, QParallelAnimationGroup, QRect, QEasingCurve, Qt
from PyQt6.QtWidgets import QFrame, QGraphicsOpacityEffect


class DockedQuickMenuController(QObject):
    """Owns the docked quick menu lifecycle, blocker overlay, and show/hide animation."""

    def __init__(self, quick_menu, parent=None):
        super().__init__(parent)
        self.quick_menu = quick_menu
        self.main_window = None
        self.overlay = None
        self.overlay_effect = None
        self.animation_group = None

    def attach(self, main_window):
        if self.main_window is not None and self.main_window is not main_window:
            self.dispose()
        self.main_window = main_window
        self.quick_menu.setParent(main_window)
        self.quick_menu.hide()
        self.main_window.installEventFilter(self)
        self._ensure_overlay()
        self.sync_geometry()

    def dispose(self):
        if self.main_window is not None:
            self.main_window.removeEventFilter(self)
        if self.animation_group is not None:
            self.animation_group.stop()
            self.animation_group = None
        if self.overlay is not None:
            self.overlay.hide()
            self.overlay.deleteLater()
            self.overlay = None
            self.overlay_effect = None
        if self.quick_menu is not None:
            self.quick_menu.hide()
            self.quick_menu.setParent(None)
            self.quick_menu.setGeometry(0, 0, 1, 1)
        self.main_window = None

    def eventFilter(self, watched, event):
        if watched is not self.main_window or self.quick_menu is None:
            return False

        if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show, QEvent.Type.WindowStateChange):
            self.sync_geometry()
        return False

    def sync_geometry(self):
        if self.main_window is None or self.quick_menu is None or not self.main_window.isVisible():
            return

        height = self.main_window.height()
        width = getattr(self.quick_menu, 'panel_width', self.quick_menu.width())
        self.quick_menu.setFixedHeight(height)
        if self.quick_menu.isVisible():
            self.quick_menu.setGeometry(0, 0, width, height)
        else:
            self.quick_menu.setGeometry(0, 0, 1, height)

        self._sync_overlay_geometry()
        if self.quick_menu.isVisible():
            self.quick_menu.raise_()

    def show_panel(self, on_finished=None):
        self._animate(show=True, on_finished=on_finished)

    def hide_panel(self, on_finished=None):
        self._animate(show=False, on_finished=on_finished)

    def _ensure_overlay(self):
        if self.main_window is None:
            return None

        if self.overlay is None or self.overlay.parent() is not self.main_window:
            self.overlay = QFrame(self.main_window)
            self.overlay.setObjectName('quick_menu_overlay')
            self.overlay.setStyleSheet(
                """
                QFrame#quick_menu_overlay {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0 rgba(0, 0, 0, 230),
                        stop: 0.45 rgba(0, 0, 0, 214),
                        stop: 1 rgba(0, 0, 0, 198)
                    );
                }
                """
            )
            self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self.overlay_effect = QGraphicsOpacityEffect(self.overlay)
            self.overlay.setGraphicsEffect(self.overlay_effect)
            self.overlay.hide()

        return self.overlay

    def _sync_overlay_geometry(self):
        if self.overlay is None or self.main_window is None or not self.main_window.isVisible():
            return
        self.overlay.setGeometry(self.main_window.rect())
        self.overlay.raise_()

    def _animate(self, show, on_finished=None):
        if self.main_window is None or self.quick_menu is None or not self.main_window.isVisible():
            if on_finished is not None:
                on_finished()
            return

        if self.animation_group is not None:
            self.animation_group.stop()

        cover = self._ensure_overlay()
        if cover is None:
            if on_finished is not None:
                on_finished()
            return

        height = self.main_window.height()
        width = getattr(self.quick_menu, 'panel_width', self.quick_menu.width())

        panel_animation = QPropertyAnimation(self.quick_menu, b'geometry')
        panel_animation.setDuration(320)
        panel_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade_animation = None
        self._sync_overlay_geometry()

        if show:
            self.quick_menu.setGeometry(0, 0, 1, height)
            self.quick_menu.show()
            cover.show()
            cover.raise_()
            self.quick_menu.raise_()

            if self.overlay_effect is not None:
                self.overlay_effect.setOpacity(0.0)

            panel_animation.setStartValue(QRect(0, 0, 1, height))
            panel_animation.setEndValue(QRect(0, 0, width, height))

            if self.overlay_effect is not None:
                fade_animation = QPropertyAnimation(self.overlay_effect, b'opacity')
                fade_animation.setDuration(260)
                fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                fade_animation.setStartValue(0.0)
                fade_animation.setEndValue(1.0)
        else:
            if not self.quick_menu.isVisible():
                cover.hide()
                if on_finished is not None:
                    on_finished()
                return

            panel_animation.setStartValue(QRect(0, 0, width, height))
            panel_animation.setEndValue(QRect(0, 0, 1, height))

            if self.overlay_effect is not None:
                fade_animation = QPropertyAnimation(self.overlay_effect, b'opacity')
                fade_animation.setDuration(240)
                fade_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
                fade_animation.setStartValue(1.0)
                fade_animation.setEndValue(0.0)

        group = QParallelAnimationGroup()
        group.addAnimation(panel_animation)
        if fade_animation is not None:
            group.addAnimation(fade_animation)

        def _finish():
            if not show:
                self.quick_menu.hide()
                cover.hide()
            if on_finished is not None:
                on_finished()

        group.finished.connect(_finish)
        self.animation_group = group
        group.start()