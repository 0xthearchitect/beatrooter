class ThemeManager:
    THEMES = {
        'cyber_modern': """
            QMainWindow {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QWidget {
                background-color: #2a2a3a;
                color: #cdd6f4;
                border: none;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #585b70;
                color: #cdd6f4;
                border: 1px solid #6c7086;
                border-radius: 6px;
                padding: 8px 12px;
                font-family: 'Segoe UI', 'Arial';
                font-weight: 600;
                font-size: 11px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #6c7086;
                border: 1px solid #89b4fa;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QPushButton:checked {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QTextEdit, QLineEdit, QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 5px;
                font-family: 'Segoe UI', 'Arial';
                padding: 6px 8px;
                font-size: 11px;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }
            QTextEdit:focus, QLineEdit:focus, QComboBox:focus {
                border: 1px solid #89b4fa;
                background-color: #363646;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #89b4fa;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }
            QGraphicsView {
                background-color: #1e1e2e;
                border: 2px solid #45475a;
                border-radius: 6px;
            }
            QLabel {
                color: #cdd6f4;
                font-family: 'Segoe UI', 'Arial';
                font-weight: 500;
                font-size: 11px;
                background-color: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
            }
            QGroupBox {
                color: #89b4fa;
                font-weight: bold;
                font-size: 12px;
                margin-top: 10px;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding-top: 10px;
                background-color: #2a2a3a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                background-color: #2a2a3a;
            }
            
            QMenu {
                background-color: #2a2a3a;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                background-color: transparent;
                color: #cdd6f4;
                padding: 6px 20px;
                border-radius: 4px;
                font-family: 'Segoe UI', 'Arial';
                font-size: 11px;
            }
            QMenu::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QMenu::item:disabled {
                color: #6c7086;
            }
            QMenu::separator {
                height: 1px;
                background-color: #45475a;
                margin: 4px 8px;
            }
            
            QMenuBar {
                background-color: #2a2a3a;
                color: #cdd6f4;
                border-bottom: 1px solid #45475a;
                font-weight: 600;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            
            QScrollBar:vertical {
                background: #313244;
                width: 14px;
                margin: 0px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical {
                background: #585b70;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #89b4fa;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar:horizontal {
                background: #313244;
                height: 14px;
                margin: 0px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal {
                background: #585b70;
                min-width: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #89b4fa;
            }
            QToolBar {
                background-color: #2a2a3a;
                border: none;
                spacing: 4px;
                padding: 4px;
            }
            QToolBar QToolButton {
                background-color: #585b70;
                border: 1px solid #6c7086;
                border-radius: 4px;
                padding: 5px;
                margin: 1px;
            }
            QToolBar QToolButton:hover {
                background-color: #89b4fa;
                border: 1px solid #89b4fa;
                color: #1e1e2e;
            }
            QStatusBar {
                background-color: #2a2a3a;
                color: #89b4fa;
                border-top: 1px solid #45475a;
                font-weight: 500;
            }
            QSplitter::handle {
                background-color: #45475a;
                margin: 2px;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #89b4fa;
            }
            QTabWidget::pane {
                border: 1px solid #45475a;
                background-color: #2a2a3a;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #313244;
                color: #a6adc8;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QTabBar::tab:hover:!selected {
                background-color: #585b70;
                color: #cdd6f4;
            }
            QProgressBar {
                border: 1px solid #45475a;
                border-radius: 4px;
                background-color: #313244;
                text-align: center;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 3px;
            }
        """,
        
        'hacker_dark': """
            QMainWindow {
                background-color: #0a0a0a;
                color: #00ff00;
            }
            QWidget {
                background-color: #1a1a1a;
                color: #00ff00;
                border: none;
            }
            QPushButton {
                background-color: #002800;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 8px;
                font-family: 'Courier New';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #004800;
                border: 2px solid #00ff00;
            }
            QPushButton:pressed {
                background-color: #006800;
            }
            QTextEdit, QLineEdit, QComboBox {
                background-color: #000000;
                color: #00ff00;
                border: 1px solid #333;
                font-family: 'Courier New';
                padding: 5px;
            }
            QGraphicsView {
                background-color: #000000;
                border: 2px solid #333;
            }
            QLabel {
                color: #00ff00;
                font-family: 'Courier New';
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #002800;
                width: 15px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #00ff00;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #80ff80;
            }
        """,
        
        'detective_classic': """
            QMainWindow {
                background-color: #f0e6d2;
                color: #333333;
            }
            QWidget {
                background-color: #e8dcc5;
                color: #333333;
                border: none;
            }
            QPushButton {
                background-color: #8b4513;
                color: #ffffff;
                border: 1px solid #654321;
                padding: 8px;
                font-family: 'Georgia';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a0522d;
            }
            QTextEdit, QLineEdit, QComboBox {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #b5a88a;
                font-family: 'Georgia';
                padding: 5px;
            }
            QGraphicsView {
                background-color: #ffffff;
                border: 2px solid #8b4513;
            }
            QLabel {
                color: #333333;
                font-family: 'Georgia';
                font-weight: bold;
                background-color: transparent;
                border: none;
            }
        """
    }
    
    @classmethod
    def get_theme(cls, theme_name: str) -> str:
        return cls.THEMES.get(theme_name, cls.THEMES['cyber_modern'])
    
    @classmethod
    def get_available_themes(cls) -> list:
        return list(cls.THEMES.keys())