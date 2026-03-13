# main.py - ATUALIZADO COM WELCOME SMALL MENU
import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen, QWidget
from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QPixmap, QIcon
from ui.welcome_window import WelcomeWindow
from ui.welcome_small_window import WelcomeSmallMenu  # ADICIONE ESTA IMPORT
from ui.main_window import DigitalDetectiveBoard
from ui.sandbox.sandbox_main_window import SandboxMainWindow
from ui.file_icon_manager import FileIconManager
import ssl
import certifi

# Configurar SSL para Windows
os.environ['SSL_CERT_FILE'] = certifi.where()
ssl._create_default_https_context = ssl._create_unverified_context

def main():
    # Registrar ícones
    icon_manager = FileIconManager()
    if icon_manager.is_admin():
        success = icon_manager.register_file_associations()
        if success:
            print("Ícones registrados com sucesso!")
        else:
            print("Aviso: Não foi possível registrar os ícones automaticamente.")
    else:
        print("Aviso: Execute como administrador para registrar ícones de arquivo.")
    
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'small logo.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Create and show splash screen (opcional)
    splash_path = os.path.join(os.path.dirname(__file__), 'assets', 'loadingscreen.png')
    if os.path.exists(splash_path):
        splash_pix = QPixmap(splash_path)
        scaled_pix = splash_pix.scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        splash = QSplashScreen(scaled_pix, Qt.WindowType.WindowStaysOnTopHint)
        splash.show()
        app.processEvents()
    else:
        splash = None
    
    # Initialize settings
    settings = QSettings('BeatRooter', 'BeatRooter')
    
    # Check if there's a last project
    last_project = settings.value('last_project', None)
    has_last_project = bool(last_project and os.path.exists(last_project))
    
    main_window = None
    
    def show_main_interface():
        """Show the main interface after splash screen"""
        nonlocal main_window
        
        if splash:
            splash.close()
        
        # If there's a last project, load it with quick menu embedded
        if has_last_project:
            try:
                # Create and load the main window
                main_window = DigitalDetectiveBoard()
                
                # Load the project file using the main window's storage manager
                graph_data = main_window.storage_manager.load_graph(last_project)
                main_window.load_graph_data(graph_data)
                main_window.statusBar().showMessage(f"Loaded previous project: {last_project}")
                
                # Create dark overlay
                overlay = QWidget(main_window)
                overlay.setStyleSheet("background-color: rgba(0, 0, 0, 150);")
                
                # Create quick menu as a sliding panel
                quick_menu = WelcomeSmallMenu(main_window)
                
                # Function to update overlay size when window resizes
                def update_overlay_size():
                    overlay.setGeometry(0, 0, main_window.width(), main_window.height())
                    quick_menu.setGeometry(0, 0, 280, main_window.height())
                
                # Store original resize event
                original_resize = main_window.resizeEvent
                
                # Override resize event
                def custom_resize(event):
                    update_overlay_size()
                    if original_resize:
                        original_resize(event)
                
                main_window.resizeEvent = custom_resize
                
                update_overlay_size()
                overlay.show()
                
                def on_open_previous_project():
                    # Hide both the quick menu and overlay
                    quick_menu.hide()
                    overlay.hide()
                
                def on_start_new_project():
                    # Hide overlay and close main window, then open welcome window
                    overlay.hide()
                    main_window.close()
                    
                    welcome = WelcomeWindow()
                    
                    def on_project_selected(project_type, category, template_json):
                        nonlocal main_window
                        if project_type == 'sandbox':
                            main_window = SandboxMainWindow(project_type, category, template_json)
                        else:
                            main_window = DigitalDetectiveBoard(project_type, category, template_json)
                        main_window.show()
                        welcome.close()
                    
                    welcome.project_selected.connect(on_project_selected)
                    welcome.show()
                
                # Connect signals
                quick_menu.open_previous_project.connect(on_open_previous_project)
                quick_menu.start_new_project.connect(on_start_new_project)
                
                # Position quick menu on the left side of the main window
                quick_menu.setGeometry(0, 0, 280, main_window.height())
                quick_menu.show()
                quick_menu.raise_()
                
                main_window.show()
                    
            except Exception as e:
                # If loading fails, show welcome window instead (no error popup)
                print(f"Failed to load previous project: {e}")
                welcome = WelcomeWindow()
                
                def on_project_selected(project_type, category, template_json):
                    nonlocal main_window
                    if project_type == 'sandbox':
                        main_window = SandboxMainWindow(project_type, category, template_json)
                    else:
                        main_window = DigitalDetectiveBoard(project_type, category, template_json)
                    main_window.show()
                    welcome.close()
                
                welcome.project_selected.connect(on_project_selected)
                welcome.show()
        
        else:
            # No last project, show welcome window directly
            welcome = WelcomeWindow()
            
            def on_project_selected(project_type, category, template_json):
                nonlocal main_window
                if project_type == 'sandbox':
                    main_window = SandboxMainWindow(project_type, category, template_json)
                else:
                    main_window = DigitalDetectiveBoard(project_type, category, template_json)
                main_window.show()
                welcome.close()
            
            welcome.project_selected.connect(on_project_selected)
            welcome.show()
    
    # Show splash screen for 3 seconds, then show main interface
    if splash:
        QTimer.singleShot(3000, show_main_interface)
    else:
        show_main_interface()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()