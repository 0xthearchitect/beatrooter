import os
import ssl
import sys
from pathlib import Path

import certifi
from PyQt6.QtCore import QSettings, Qt, QTimer, QtMsgType, qInstallMessageHandler
from PyQt6.QtGui import QGuiApplication, QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen

from features.beatroot_canvas.ui.main_window import DigitalDetectiveBoard
from ui.file_icon_manager import FileIconManager
from ui.quick_menu_controller import DockedQuickMenuController
from features.sandbox.ui.sandbox_main_window import SandboxMainWindow
from ui.welcome_small_window import WelcomeSmallMenu
from ui.welcome_window import WelcomeWindow

# SSL
os.environ['SSL_CERT_FILE'] = certifi.where()
ssl._create_default_https_context = ssl._create_unverified_context


def qt_message_handler(mode, context, message):
    """Custom Qt message handler to filter noisy QPainter warnings."""
    if "QPainter" in message and ("not active" in message or "begin" in message):
        return

    if mode == QtMsgType.QtDebugMsg:
        print(f"Qt Debug: {message}")
    elif mode == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}")


def _create_main_window(project_type=None, category=None, template_json=None):
    if project_type == "sandbox":
        return SandboxMainWindow(project_type, category, template_json)
    return DigitalDetectiveBoard(project_type, category, template_json)


def _resolve_asset_path(filename: str) -> str:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "assets" / filename,
        here.parent / "assets" / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return str(candidates[0])


def main():
    qInstallMessageHandler(qt_message_handler)

    # Register file icons/associations when possible.
    icon_manager = FileIconManager()
    if icon_manager.is_admin():
        if icon_manager.register_file_associations():
            print("Ícones registrados com sucesso!")
        else:
            print("Aviso: Não foi possível registrar os ícones automaticamente.")
    else:
        print("Aviso: Execute como administrador para registrar ícones de arquivo.")

    app = QApplication(sys.argv)

    icon_path = _resolve_asset_path('beatrooter_logo.svg')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    splash = None
    splash_path = _resolve_asset_path('loadingscreen.png')
    if os.path.exists(splash_path):
        splash_pix = QPixmap(splash_path)
        if not splash_pix.isNull():
            scaled_pix = splash_pix.scaled(
                600,
                400,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            splash = QSplashScreen(scaled_pix)
            splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

            screen = QGuiApplication.primaryScreen()
            if screen is not None:
                geometry = screen.geometry()
                x = (geometry.width() - scaled_pix.width()) // 2
                y = (geometry.height() - scaled_pix.height()) // 2
                splash.move(x, y)

            splash.show()
            app.processEvents()

    settings = QSettings('BeatRooter', 'BeatRooter')
    last_saved_project = settings.value('last_saved_project', '', type=str) or ''
    if not last_saved_project:
        # Backward compatibility with older key.
        last_saved_project = settings.value('last_project', '', type=str) or ''

    has_last_project = bool(last_saved_project and os.path.exists(last_saved_project))

    main_window = None
    welcome = WelcomeWindow()
    quick_menu = None
    quick_menu_controller = None

    if has_last_project:
        quick_menu = WelcomeSmallMenu()
        quick_menu.set_previous_project_enabled(True)
        quick_menu.setWindowFlags(Qt.WindowType.Widget)
        quick_menu_controller = DockedQuickMenuController(quick_menu)

    def show_welcome_window(hide_quick_menu=True):
        def _show_welcome_now():
            if main_window is not None:
                main_window.hide()
            welcome.showMaximized()
            welcome.raise_()
            welcome.activateWindow()

        if (
            hide_quick_menu
            and quick_menu_controller is not None
            and quick_menu is not None
            and quick_menu.isVisible()
        ):
            quick_menu_controller.hide_panel(_show_welcome_now)
        else:
            _show_welcome_now()

    def open_project_file(file_path):
        nonlocal main_window

        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(None, "Project Missing", "The previous project could not be found.")
            if quick_menu is not None:
                quick_menu.set_previous_project_enabled(False)
            show_welcome_window(hide_quick_menu=False)
            return

        if main_window is None:
            main_window = DigitalDetectiveBoard()

        try:
            graph_data = main_window.storage_manager.load_graph(file_path)
            main_window.load_graph_data(graph_data)
            main_window.storage_manager.current_file = file_path
            if 0 <= main_window.active_document_index < len(main_window.documents):
                active_document = main_window.documents[main_window.active_document_index]
                active_document["file_path"] = file_path
                active_document["dirty"] = False
                main_window._update_document_tab_label(main_window.active_document_index)
            main_window._schedule_missing_tools_prompt_if_needed()
            project_title = os.path.basename(file_path)
            main_window.setWindowTitle(f"BeatRooter - {project_title}")
            main_window.statusBar().showMessage(f"Opened investigation: {file_path}")
            settings.setValue('last_saved_project', file_path)
            settings.setValue('last_project', file_path)
            if hasattr(main_window, "emit_ndc_project_opened"):
                main_window.emit_ndc_project_opened(file_path, reason="startup_previous_project")
        except Exception as exc:
            QMessageBox.critical(None, "Open Failed", f"Failed to open project: {exc}")
            main_window.close()
            main_window = None
            show_welcome_window(hide_quick_menu=False)
            return

        if quick_menu_controller is not None:
            quick_menu_controller.dispose()
        welcome.close()
        main_window.showMaximized()
        main_window.raise_()
        main_window.activateWindow()

    def on_project_selected(project_type, category, template_json):
        nonlocal main_window

        if project_type == "open":
            open_project_file(category)
            return

        if main_window is not None:
            main_window.close()
            main_window = None

        if quick_menu_controller is not None:
            quick_menu_controller.dispose()

        welcome.close()
        main_window = _create_main_window(project_type, category, template_json)
        main_window.showMaximized()

    welcome.project_selected.connect(on_project_selected)

    def launch_initial_ui():
        nonlocal main_window

        if has_last_project and quick_menu is not None and quick_menu_controller is not None:
            quick_menu.start_new_project.connect(
                lambda: quick_menu_controller.hide_panel(
                    lambda: show_welcome_window(hide_quick_menu=False)
                )
            )
            quick_menu.open_previous_project.connect(
                lambda: quick_menu_controller.hide_panel(
                    lambda: open_project_file(last_saved_project)
                )
            )

            # Launch workspace first and show the docked quick menu.
            main_window = DigitalDetectiveBoard()
            main_window.showMaximized()
            main_window.raise_()
            main_window.activateWindow()

            quick_menu_controller.attach(main_window)
            QTimer.singleShot(0, quick_menu_controller.sync_geometry)
            QTimer.singleShot(0, quick_menu_controller.show_panel)
        else:
            show_welcome_window()

    if splash is not None:
        def close_splash_and_launch():
            splash.close()
            launch_initial_ui()

        QTimer.singleShot(2500, close_splash_and_launch)
    else:
        launch_initial_ui()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
