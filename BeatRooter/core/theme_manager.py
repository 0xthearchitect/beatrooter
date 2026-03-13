class ThemeManager:
    THEMES = {
        'cyber_modern': """
            QMainWindow {
                background-color: #0b111a;
                color: #c8d1e0;
            }
            QWidget {
                color: #aeb9cd;
                border: none;
                border-radius: 0px;
                font-family: 'JetBrains Mono', 'Consolas', 'DejaVu Sans Mono';
                font-size: 11px;
            }
            #MainRoot {
                background-color: #0b111a;
            }
            #ToolboxColumn, #DetailColumn {
                background-color: #0f1622;
            }
            #ToolboxColumn {
                border-right: 1px solid #273347;
            }
            #DetailColumn {
                border-left: 1px solid #273347;
            }
            QGraphicsView {
                background-color: #0b111a;
                border: none;
            }
            QSplitter::handle {
                background-color: #273347;
                width: 1px;
                margin: 0px;
            }
            QSplitter::handle:hover {
                background-color: #3b4f68;
            }
            QMenuBar {
                background-color: #0e1520;
                color: #8797b0;
                border-bottom: 1px solid #273347;
                padding-left: 6px;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
                margin: 1px 2px;
            }
            QMenuBar::item:selected {
                background-color: #1d293b;
                color: #dce6f7;
            }
            QToolBar#MainToolbar {
                background-color: #0e1520;
                border-bottom: 1px solid #273347;
                spacing: 4px;
                padding: 5px 8px;
            }
            QToolBar#MainToolbar QToolButton {
                background-color: #182235;
                color: #95a6c0;
                border: 1px solid #2a3950;
                border-radius: 3px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QToolBar#MainToolbar QToolButton:hover {
                background-color: #22304a;
                border: 1px solid #3f5777;
                color: #e3ecfb;
            }
            QToolBar#MainToolbar QToolButton:pressed {
                background-color: #263756;
            }
            QStatusBar {
                background-color: #0e1520;
                color: #7f8da3;
                border-top: 1px solid #273347;
            }
            QTabWidget#RightTabs::pane {
                border: 1px solid #1e2c3f;
                background-color: #0f1928;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #111a2b;
                color: #8ea1bf;
                border: 1px solid #25374f;
                border-bottom: none;
                padding: 6px 14px;
                min-width: 60px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0f1928;
                color: #d7e2f2;
                border: 1px solid #3e5778;
                border-bottom: 1px solid #0f1928;
            }
            QTabBar::tab:hover:!selected {
                background-color: #17243a;
                color: #c9d5e8;
            }
            QGroupBox {
                color: #7688a3;
                font-size: 10px;
                margin-top: 10px;
                border: 1px solid #1e2c3f;
                border-radius: 2px;
                padding-top: 10px;
                background-color: #0f1928;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                background-color: #111b2b;
            }
            QLabel {
                color: #9fb0c8;
                background: transparent;
                font-size: 11px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #131d2d;
                color: #ced8e8;
                border: 1px solid #26364c;
                border-radius: 2px;
                padding: 6px 8px;
                selection-background-color: #355a82;
                selection-color: #eff4ff;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #4e79ab;
                background-color: #172538;
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
                border-top: 5px solid #7f93ae;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background-color: #162033;
                color: #d5deec;
                border: 1px solid #2d3d55;
                selection-background-color: #2c405f;
            }
            QPushButton {
                background-color: #182336;
                color: #a7b7cf;
                border: 1px solid #2b3b52;
                border-radius: 2px;
                padding: 7px 10px;
                min-height: 18px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #1d2c44;
                border: 1px solid #38506f;
                color: #eef4ff;
            }
            QPushButton:pressed {
                background-color: #202f49;
            }
            QPushButton:checked {
                background-color: #202f49;
                border: 1px solid #4f79a9;
            }
            QPushButton:disabled {
                background-color: #132033;
                color: #5f7087;
                border: 1px solid #243348;
            }
            QPushButton#SaveNodeBtn {
                background-color: #2f3f57;
                border: 1px solid #495f7d;
            }
            QPushButton#SaveNodeBtn:hover {
                background-color: #385174;
                border: 1px solid #5a7ea8;
            }
            QPushButton#DeleteNodeBtn {
                background-color: #3b242e;
                border: 1px solid #6b3748;
                color: #f0aab8;
            }
            QPushButton#DeleteNodeBtn:hover {
                background-color: #522d3a;
                border: 1px solid #8f465b;
                color: #ffced8;
            }
            QScrollArea, #DetailScrollArea {
                background-color: transparent;
            }
            QMenu {
                background-color: #141f31;
                color: #d4deec;
                border: 1px solid #2c3b52;
                border-radius: 2px;
                padding: 5px;
            }
            QMenu::item {
                background-color: transparent;
                color: #c8d1e0;
                padding: 6px 18px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background-color: #283a55;
                color: #ecf3ff;
            }
            QMenu::item:disabled {
                color: #66788f;
            }
            QMenu::separator {
                height: 1px;
                background-color: #2c3b52;
                margin: 4px 8px;
            }
            QScrollBar:vertical {
                background: #0f1828;
                width: 10px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #2c405c;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #436287;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar:horizontal {
                background: #0f1828;
                height: 10px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #2c405c;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #436287;
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
