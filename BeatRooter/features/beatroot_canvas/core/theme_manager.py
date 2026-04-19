class ThemeManager:
    THEMES = {
        'cyber_modern': """
            QMainWindow {
                background-color: #1c1c1c;
                color: #e6e6e6;
            }
            QWidget {
                color: #cfcfcf;
                border: none;
                border-radius: 0px;
                font-family: 'JetBrains Mono', 'Consolas', 'DejaVu Sans Mono';
                font-size: 11px;
            }
            #MainRoot {
                background-color: #1c1c1c;
            }
            #ToolboxColumn, #DetailColumn {
                background-color: #232323;
            }
            #ToolboxColumn {
                background-color: transparent;
                border-right: none;
            }
            #DetailColumn {
                border-left: none;
            }
            QGraphicsView {
                background-color: #0f0f0f;
                border: none;
            }
            QSplitter::handle {
                background-color: transparent;
                width: 1px;
                margin: 0px;
            }
            QSplitter::handle:hover {
                background-color: transparent;
            }
            QMenuBar {
                background-color: #232323;
                color: #aaaaaa;
                border-bottom: 1px solid #3d3d3d;
                padding-left: 6px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
                margin: 1px 2px;
            }
            QMenuBar::item:selected {
                background-color: #352931;
                color: #ffddea;
            }
            QToolBar#MainToolbar {
                background-color: #232323;
                border-bottom: none;
                spacing: 4px;
                padding: 5px 8px;
            }
            QToolBar#MainToolbar QToolButton {
                background-color: #292929;
                color: #c8c8c8;
                border: 1px solid #3d3d3d;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QToolBar#MainToolbar QToolButton:hover {
                background-color: #352931;
                border: 1px solid #7a5567;
                color: #ffe5ef;
            }
            QToolBar#MainToolbar QToolButton:pressed {
                background-color: #402f39;
            }
            QStatusBar {
                background-color: #232323;
                color: #9c9c9c;
                border-top: 1px solid #3d3d3d;
            }
            QTabWidget#RightTabs::pane {
                border: 1px solid #3d3d3d;
                background-color: #232323;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #292929;
                color: #aaaaaa;
                border: 1px solid #3d3d3d;
                border-bottom: none;
                padding: 6px 14px;
                min-width: 60px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #352931;
                color: #ffddea;
                border: 1px solid #9c627d;
                border-bottom: 1px solid #352931;
            }
            QTabBar::tab:hover:!selected {
                background-color: #31272d;
                color: #f7d8e5;
            }
            QTabBar#DocumentTabs {
                background-color: #232323;
                border: none;
                border-bottom: 1px solid #3d3d3d;
                padding: 1px 6px 0px 6px;
            }
            QTabBar#DocumentTabs::tab {
                background-color: #232323;
                color: #b5b5b5;
                border: 1px solid #3d3d3d;
                border-bottom: 1px solid #1c1c1c;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                padding: 6px 16px 6px 12px;
                margin-right: 3px;
            }
            QTabBar#DocumentTabs::tab:selected {
                background-color: #352931;
                color: #ffddea;
                border: 1px solid #9c627d;
                border-bottom: 1px solid #1c1c1c;
            }
            QTabBar#DocumentTabs::tab:hover:!selected {
                background-color: #31272d;
                color: #f7d8e5;
                border: 1px solid #6f515f;
                border-bottom: 1px solid #1c1c1c;
            }
            QToolButton#DocumentTabCloseButton {
                background-color: transparent;
                color: #ff5f66;
                border: none;
                padding: 0px;
                min-width: 18px;
                min-height: 18px;
                max-width: 18px;
                max-height: 18px;
                font-size: 15px;
                font-weight: 800;
            }
            QToolButton#DocumentTabCloseButton:hover {
                color: #ff9aa0;
            }
            QToolButton#DocumentTabCloseButton:pressed {
                color: #ffd4d7;
            }
            QGroupBox {
                color: #9d9d9d;
                font-size: 10px;
                margin-top: 10px;
                border: 1px solid #3d3d3d;
                border-radius: 2px;
                padding-top: 10px;
                background-color: #232323;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                background-color: #232323;
            }
            QLabel {
                color: #cfcfcf;
                background: transparent;
                font-size: 11px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #292929;
                color: #e6e6e6;
                border: 1px solid #3d3d3d;
                border-radius: 2px;
                padding: 6px 8px;
                selection-background-color: #3a3a3a;
                selection-color: #ffffff;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #a76885;
                background-color: #332830;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #a7a7a7;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #292929;
                color: #e6e6e6;
                border: 1px solid #3d3d3d;
                selection-background-color: #3a3a3a;
            }
            QPushButton {
                background-color: #292929;
                color: #d0d0d0;
                border: 1px solid #3d3d3d;
                border-radius: 2px;
                padding: 7px 10px;
                min-height: 18px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #352931;
                border: 1px solid #7a5567;
                color: #ffe5ef;
            }
            QPushButton:pressed {
                background-color: #402f39;
            }
            QPushButton:checked {
                background-color: #4a3340;
                border: 1px solid #a76885;
            }
            QPushButton:disabled {
                background-color: #242424;
                color: #777777;
                border: 1px solid #333333;
            }
            QPushButton#SaveNodeBtn {
                background-color: #c8558a;
                border: 1px solid #db79a5;
                color: #fff7fb;
            }
            QPushButton#SaveNodeBtn:hover {
                background-color: #d86798;
                border: 1px solid #e594b6;
                color: #ffffff;
            }
            QPushButton#DeleteNodeBtn {
                background-color: #2d2323;
                border: 1px solid #4a3b3b;
                color: #e0baba;
            }
            QPushButton#DeleteNodeBtn:hover {
                background-color: #382828;
                border: 1px solid #5a4747;
                color: #f0d0d0;
            }
            QScrollArea, #DetailScrollArea {
                background-color: transparent;
            }
            QMenu {
                background-color: #292929;
                color: #e6e6e6;
                border: 1px solid #3d3d3d;
                border-radius: 2px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                color: #dcdcdc;
                padding: 6px 18px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #352931;
                color: #ffddea;
            }
            QMenu::item:disabled {
                color: #7d7d7d;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3d3d3d;
                margin: 4px 8px;
            }
            QScrollBar:vertical {
                background: #232323;
                width: 10px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #6b5360;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #876676;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar:horizontal {
                background: #232323;
                height: 10px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #6b5360;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #876676;
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
