from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QFileDialog, QMessageBox,
    QGraphicsDropShadowEffect, QStackedWidget, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPixmap, QFont, QPainter, QLinearGradient
import json
import os
import sys
from utils.version_checker import check_version_freshness
from utils.path_utils import get_resource_path
from core.node_factory import NodeFactory

class GradientFrame(QFrame):
    """Custom frame with gradient background - smooth vertical fade, barely noticeable"""
    def __init__(self, start_color, end_color, parent=None):
        super().__init__(parent)
        self.start_color = QColor(start_color)
        self.end_color = QColor(end_color)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        # Smooth, barely noticeable fade from start to slightly darker variant
        gradient.setColorAt(0, self.start_color)
        gradient.setColorAt(0.7, self.start_color)  # Keep same color for most of the tile
        gradient.setColorAt(1, self.end_color)  # Only darken at very bottom
        painter.fillRect(self.rect(), gradient)


class ReverseGradientFrame(QFrame):
    """Subtle atmospheric gradient - soft purple wash, not intense"""
    def __init__(self, bottom_color, parent=None):
        super().__init__(parent)
        # Subtle purple tone - much lower opacity for atmosphere only
        self.bottom_color = QColor(bottom_color)
        self.bottom_color.setAlpha(15)  # Very subtle ~6% opacity for weaker atmosphere
        # Top is completely transparent
        self.top_color = QColor(0, 0, 0, 0)  # Fully transparent
    
    def set_gradient_color(self, color):
        """Update the gradient color"""
        self.bottom_color = QColor(color)
        self.bottom_color.setAlpha(15)  # Keep same weak opacity
        self.update()  # Trigger repaint
    
    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, self.top_color)  # Completely transparent at top
        gradient.setColorAt(0.6, self.top_color)  # Stay transparent longer
        gradient.setColorAt(1, self.bottom_color)  # Subtle purple at bottom only
        painter.fillRect(self.rect(), gradient)


class WelcomeWindow(QMainWindow):
    project_selected = pyqtSignal(str, str, str)  # project_type, category, template_json

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeatRooter - Your Tool for Forensics and Security Analysis")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

        # New Color Palette - Execution-Critical
        self.colors = {
            'page_bg': '#141414',           # Page background (solid black)
            'tile_bg': '#C8558A',           # Tile blocks (stronger purple-pink)
            'tile_gradient_end': '#A8467A', # Slightly darker variant for subtle fade
            'red_team_tile': '#D32F2F',     # Red Team color (stronger red)
            'red_team_gradient': '#B71C1C', # Red Team darker variant
            'blue_team_tile': '#1976D2',    # Blue Team color (stronger blue)
            'blue_team_gradient': '#1565C0', # Blue Team darker variant
            'blue_team_button': '#42A5F5',  # Lighter blue for buttons (more appealing)
            'blue_team_button_hover': '#64B5F6', # Even lighter for hover
            'button_active': '#A8496E',     # Slightly lighter/pinker for active buttons
            'button_disabled': '#2A1820',   # Dark-burgundy/near-black for "Coming Soon"
            'text_white': '#FFFFFF',        # Pure white for text
            'text_light_gray': '#E0E0E0',   # Light gray for body text
            'version_badge_bg': '#1A2332',  # Dark navy-blue for version badge
            'red_rotten': '#FF0000',        # Red for "rotten" message
        }

        # Check version freshness
        self.freshness_message, self.freshness_color, self.version_text = check_version_freshness()

        # Paths to assets
        self.logo_path = get_resource_path(f"icons/app_icon.png")

        red_categories = NodeFactory.get_project_categories("redteam")
        blue_categories = NodeFactory.get_project_categories("blueteam")

        # Project templates for Red Team, Clean Project, Blue Team & SOC
        self.project_templates = {
            "redteam": {
                "name": "Red Team",
                "description": "Offensive security testing and penetration testing.",
                "specializations": [meta["name"] for meta in list(red_categories.values())[:4]],
                "categories": {
                    category_id: {
                        "name": meta["name"],
                        "description": meta["description"],
                    }
                    for category_id, meta in red_categories.items()
                },
            },
            "clean": {
                "name": "Clean Project",
                "description": "Feel like no category fills what you need? Start a blank project with access to every single tool and node.",
                "specializations": [
                    "Everything, have fun!"
                ],
                "categories": {
                    "blank": {
                        "name": "Blank Project",
                        "description": "Full access to all tools and nodes"
                    }
                }
            },
            "blueteam": {
                "name": "Blue Team and SOC Ops.",
                "description": "Defensive security operations, incident response and SOC monitoring and analysis.",
                "specializations": [meta["name"] for meta in list(blue_categories.values())[:4]] + ["... and more!"],
                "categories": {
                    category_id: {
                        "name": meta["name"],
                        "description": meta["description"],
                    }
                    for category_id, meta in blue_categories.items()
                },
            }
        }

        self.setup_ui()
        self.apply_styles()
        self.setup_animations()

    def setup_ui(self):
        """Build the entire UI structure"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.central_widget = central_widget  # Store reference for background color changes
        central_widget.setStyleSheet(f"background-color: {self.colors['page_bg']};")

        # Add gradient overlay to entire page (cosmetic layer)
        self.gradient_overlay = ReverseGradientFrame('#923A5F', central_widget)
        self.gradient_overlay.setGeometry(0, 0, central_widget.width(), central_widget.height())
        self.gradient_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.gradient_overlay.lower()

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Bar (Header)
        header = self.create_header()
        main_layout.addWidget(header)

        # Stacked Widget for multi-screen navigation
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: transparent;")

        # Create all screens
        self.welcome_screen = self.create_welcome_screen()
        self.project_type_screen = self.create_project_type_screen()
        self.category_screen = self.create_category_screen()

        # Add screens to stacked widget
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.project_type_screen)
        self.stacked_widget.addWidget(self.category_screen)

        main_layout.addWidget(self.stacked_widget, 1)

        # Footer
        footer = self.create_footer()
        main_layout.addWidget(footer)

        # Ensure gradient is visible but behind interactive elements
        self.gradient_overlay.raise_()
        header.raise_()
        self.stacked_widget.raise_()
        footer.raise_()

    def create_header(self):
        """Top bar with icons, links, and version info"""
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("background-color: transparent; border: none;")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(40, 15, 40, 15)

        # Left side: GitHub and mail icons with labels
        left_layout = QHBoxLayout()
        left_layout.setSpacing(30)

        # GitHub
        github_layout = QHBoxLayout()
        github_layout.setSpacing(8)
        github_icon = QLabel("⚙")  # Using gear icon as placeholder
        github_icon.setStyleSheet(f"color: {self.colors['text_white']}; font-size: 20px; background-color: transparent;")
        github_label = QLabel("GitHub")
        github_label.setStyleSheet(f"color: {self.colors['text_white']}; font-size: 14px; background-color: transparent;")
        github_layout.addWidget(github_icon)
        github_layout.addWidget(github_label)

        # Mail
        mail_layout = QHBoxLayout()
        mail_layout.setSpacing(8)
        mail_icon = QLabel("✉")  # Using envelope icon as placeholder
        mail_icon.setStyleSheet(f"color: {self.colors['text_white']}; font-size: 20px; background-color: transparent;")
        mail_label = QLabel("Contact")
        mail_label.setStyleSheet(f"color: {self.colors['text_white']}; font-size: 14px; background-color: transparent;")
        mail_layout.addWidget(mail_icon)
        mail_layout.addWidget(mail_label)

        left_layout.addLayout(github_layout)
        left_layout.addLayout(mail_layout)

        # Right side: Version badge and freshness message
        right_layout = QVBoxLayout()
        right_layout.setSpacing(5)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Version badge
        version_badge = QLabel(self.version_text)
        version_badge.setStyleSheet(f"""
            background-color: {self.colors['version_badge_bg']};
            color: {self.colors['text_white']};
            border-radius: 6px;
            font-size: 10px;
            font-weight: 600;
            padding: 6px 12px;
        """)
        version_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Freshness message
        freshness_label = QLabel(self.freshness_message)
        freshness_label.setStyleSheet(f"""
            color: {self.freshness_color};
            font-size: 11px;
            font-weight: {'700' if self.freshness_color == self.colors['red_rotten'] else '400'};
            background-color: transparent;
        """)
        freshness_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        right_layout.addWidget(version_badge)
        right_layout.addWidget(freshness_label)

        layout.addLayout(left_layout)
        layout.addStretch()
        layout.addLayout(right_layout)

        return header

    def create_welcome_screen(self):
        """Main welcome screen content"""
        screen = QWidget()
        screen.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(screen)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(40)

        # Main Content (Logo, Welcome Text)
        centerpiece = self.create_centerpiece()
        layout.addWidget(centerpiece)

        # Feature Grid
        feature_grid = self.create_feature_grid()
        layout.addLayout(feature_grid)

        layout.addStretch()

        return screen

    def create_centerpiece(self):
        """Logo and welcome text centered"""
        centerpiece = QWidget()
        centerpiece.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(centerpiece)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("background-color: transparent;")
        logo_label.setScaledContents(False)
        
        if os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            # Scale to 200px height while maintaining aspect ratio
            scaled_pixmap = pixmap.scaledToHeight(200, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback text if logo not found
            logo_label.setText("🥕")
            logo_label.setStyleSheet("font-size: 100px; background-color: transparent;")

        # Welcome Text - Line 1 (Bold)
        welcome_line1 = QLabel("Welcome to BeatRooter!")
        welcome_line1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_line1.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 36px;
            font-weight: 700;
            background-color: transparent;
        """)

        # Welcome Text - Line 2 (Regular with emphasis)
        welcome_line2 = QLabel("Your Tool for Forensics and Security Analysis.")
        welcome_line2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_line2.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 20px;
            font-weight: 500;
            font-style: italic;
            background-color: transparent;
        """)

        # Welcome Text - Line 3 (Lighter)
        welcome_line3 = QLabel("Ready to start Farming?")
        welcome_line3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_line3.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 16px;
            font-weight: 300;
            background-color: transparent;
        """)

        layout.addWidget(logo_label)
        layout.addSpacing(10)
        layout.addWidget(welcome_line1)
        layout.addWidget(welcome_line2)
        layout.addWidget(welcome_line3)

        return centerpiece

    def create_feature_grid(self):
        """Four horizontal tiles for main features"""
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(25)
        grid_layout.setContentsMargins(20, 0, 20, 0)

        # Tile 1: Start a new Project
        tile1 = self.create_feature_tile(
            title="Start a new Project",
            description="Begin a fresh forensic investigation with customizable templates and workflows tailored for security analysis.",
            button_text="Start Project",
            callback=self.start_new_project,
            enabled=True
        )

        # Tile 2: Open Project
        tile2 = self.create_feature_tile(
            title="Open Project",
            description="Reopen and continue working on your previous investigations with full context restoration.",
            button_text="Open File",
            callback=self.open_existing_project,
            enabled=True
        )

        # Tile 3: BeatBox
        tile3 = self.create_feature_tile(
            title="BeatBox",
            description="Enter the interactive sandbox environment for network simulation and security testing scenarios.",
            button_text="Start Sandbox",
            callback=self.start_beatbox,
            enabled=True
        )

        # Tile 4: API & Integrations
        tile4 = self.create_feature_tile(
            title="API & Integrations",
            description="Connect to external threat intelligence feeds, SIEM systems, and automation platforms.",
            button_text="Coming Soon…",
            callback=None,
            enabled=False
        )

        grid_layout.addWidget(tile1)
        grid_layout.addWidget(tile2)
        grid_layout.addWidget(tile3)
        grid_layout.addWidget(tile4)

        return grid_layout

    def create_feature_tile(self, title, description, button_text, callback, enabled):
        """Create a single feature tile with gradient background"""
        # Use custom gradient frame
        tile = GradientFrame(self.colors['tile_bg'], self.colors['tile_gradient_end'])
        tile.setFixedWidth(300)
        tile.setMinimumHeight(350)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        tile.setGraphicsEffect(shadow)
        
        # Round corners
        tile.setStyleSheet(f"""
            border-radius: 15px;
        """)

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(25, 30, 25, 30)
        layout.setSpacing(15)

        # Title
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 20px;
            font-weight: 600;
            background-color: transparent;
        """)

        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 14px;
            font-weight: 400;
            line-height: 1.5;
            background-color: transparent;
        """)

        # Button
        button = QPushButton(button_text)
        button.setFixedHeight(45)
        button.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        
        if enabled:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['button_active']};
                    color: {self.colors['text_white']};
                    border: none;
                    border-radius: 10px;
                    font-size: 15px;
                    font-weight: 600;
                    padding: 10px 20px;
                }}
                QPushButton:hover {{
                    background-color: {self.lighten_color(self.colors['button_active'], 15)};
                }}
                QPushButton:pressed {{
                    background-color: {self.darken_color(self.colors['button_active'], 15)};
                }}
            """)
            if callback:
                button.clicked.connect(callback)
        else:
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['button_disabled']};
                    color: {self.colors['text_light_gray']};
                    border: none;
                    border-radius: 10px;
                    font-size: 15px;
                    font-weight: 600;
                    padding: 10px 20px;
                }}
            """)
            button.setEnabled(False)

        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(button)

        return tile

    def create_project_type_screen(self):
        """Project type selection screen with three horizontal tiles"""
        screen = QWidget()
        screen.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(screen)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(30)

        # Top section: Logo and Title (left-aligned)
        top_section = QWidget()
        top_section.setStyleSheet("background-color: transparent;")
        top_layout = QVBoxLayout(top_section)
        top_layout.setSpacing(15)

        # Logo (flush-left)
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        logo_label.setStyleSheet("background-color: transparent;")
        logo_label.setScaledContents(False)
        
        if os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            scaled_pixmap = pixmap.scaledToHeight(100, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("🥕")
            logo_label.setStyleSheet("font-size: 60px; background-color: transparent;")

        # Title (left-aligned, medium weight)
        title_label = QLabel("Select Project Type")
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 32px;
            font-weight: 500;
            background-color: transparent;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Subtitle (left-aligned, smaller white text)
        subtitle_label = QLabel("Choose the specialized workflow for your analysis")
        subtitle_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 16px;
            font-weight: 400;
            background-color: transparent;
        """)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        top_layout.addWidget(logo_label)
        top_layout.addWidget(title_label)
        top_layout.addWidget(subtitle_label)

        # Tiles container with proper spacing
        tiles_container = QWidget()
        tiles_container.setStyleSheet("background-color: transparent;")
        tiles_layout = QHBoxLayout(tiles_container)
        tiles_layout.setSpacing(30)
        tiles_layout.setContentsMargins(0, 20, 0, 20)

        # Order: Red Team, Clean Project, Blue Team
        red_tile = self.create_project_type_tile("redteam", self.project_templates["redteam"])
        clean_tile = self.create_project_type_tile("clean", self.project_templates["clean"])
        blue_tile = self.create_project_type_tile("blueteam", self.project_templates["blueteam"])

        tiles_layout.addWidget(red_tile)
        tiles_layout.addWidget(clean_tile)
        tiles_layout.addWidget(blue_tile)

        # Add everything to main layout in correct vertical order
        layout.addWidget(top_section)
        layout.addWidget(tiles_container)
        layout.addStretch()

        return screen

    def create_project_type_tile(self, project_type, config):
        """Create a single project type tile"""
        # Use team-specific colors
        if project_type == "redteam":
            tile_color = self.colors['red_team_tile']
            tile_gradient = self.colors['red_team_gradient']
        elif project_type == "blueteam":
            tile_color = self.colors['blue_team_tile']
            tile_gradient = self.colors['blue_team_gradient']
        else:  # clean project uses purple
            tile_color = self.colors['tile_bg']
            tile_gradient = self.colors['tile_gradient_end']
        
        # Use regular QFrame instead of GradientFrame temporarily for debugging
        tile = QFrame()
        tile.setMinimumWidth(350)
        tile.setMinimumHeight(400)
        tile.setStyleSheet(f"""
            QFrame {{
                background-color: {tile_color};
                border-radius: 15px;
            }}
        """)

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(30, 35, 30, 35)
        layout.setSpacing(20)

        # Title (white, headings)
        title_label = QLabel(config['name'])
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 24px;
            font-weight: 600;
            background-color: transparent;
        """)

        # Description (light gray/white body text)
        desc_label = QLabel(config['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 14px;
            font-weight: 400;
            line-height: 1.6;
            background-color: transparent;
        """)

        # Specializations header
        spec_header = QLabel("Available Specializations:")
        spec_header.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 13px;
            font-weight: 500;
            background-color: transparent;
            margin-top: 10px;
        """)

        # Specializations list (using bullet points from config)
        spec_text = "\n".join([f"• {spec}" for spec in config['specializations']])
        spec_label = QLabel(spec_text)
        spec_label.setWordWrap(True)
        spec_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 13px;
            font-weight: 400;
            background-color: transparent;
        """)

        # Button text mapping
        button_text_map = {
            "redteam": "Start Red Project",
            "clean": "Start Blank Project",
            "blueteam": "Start Blue/SOC Project"
        }
        button_text = button_text_map.get(project_type, f"Start {config['name']} Project")

        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addWidget(spec_header)
        layout.addWidget(spec_label)
        layout.addStretch()
        
        # Button - exactly matching the working welcome screen pattern
        button = QPushButton(button_text)
        button.setFixedHeight(45)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Calculate lighter button color
        button_color = self.lighten_color(tile_color, 30)
        button_hover = self.lighten_color(tile_color, 40)
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {button_color};
                color: {self.colors['text_white']};
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {button_hover};
            }}
            QPushButton:pressed {{
                background-color: {tile_color};
            }}
        """)
        
        # For clean project, go directly to project creation (skip category selection)
        if project_type == "clean":
            button.clicked.connect(lambda: self.start_project(project_type, "blank"))
        else:
            button.clicked.connect(lambda: self.show_category_selection(project_type))
        
        layout.addWidget(button)

        return tile

    def create_category_screen(self):
        """Screen for selecting specific category within a project type"""
        screen = QWidget()
        screen.setStyleSheet("background-color: transparent;")

        # Main layout for the screen
        main_layout = QVBoxLayout(screen)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1A1A1A;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #777777;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Content widget inside scroll area
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        
        # Store reference for dynamic updates
        self.category_layout = QVBoxLayout(content_widget)
        self.category_layout.setContentsMargins(40, 30, 40, 30)
        self.category_layout.setSpacing(40)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        return screen

    def update_category_screen(self, project_type):
        """Update category screen based on selected project type"""
        # Clear previous content
        while self.category_layout.count():
            item = self.category_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

        config = self.project_templates[project_type]

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)

        title_label = QLabel(f"Choose {config['name']} Specialization")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 32px;
            font-weight: 700;
            background-color: transparent;
        """)

        subtitle_label = QLabel("Select the specific investigation workflow that matches your requirements")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 16px;
            font-weight: 400;
            background-color: transparent;
        """)

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        self.category_layout.addLayout(header_layout)

        # Category tiles in grid layout (3 per row)
        from PyQt6.QtWidgets import QGridLayout
        categories_container = QWidget()
        categories_container.setStyleSheet("background-color: transparent;")
        categories_layout = QGridLayout(categories_container)
        categories_layout.setSpacing(25)
        categories_layout.setContentsMargins(20, 20, 20, 20)

        # Arrange tiles in grid: 3 per row
        categories = list(config['categories'].items())
        row = 0
        col = 0
        
        for cat_id, cat_conf in categories:
            tile = self.create_category_tile(project_type, cat_id, cat_conf)
            categories_layout.addWidget(tile, row, col)
            
            col += 1
            if col >= 3:  # Move to next row after 3 tiles
                col = 0
                row += 1

        self.category_layout.addWidget(categories_container)
        self.category_layout.addStretch()

    def create_category_tile(self, project_type, category_id, config):
        """Create a tile for category selection"""
        # Use team-specific colors
        if project_type == "redteam":
            tile_color = self.colors['red_team_tile']
            tile_gradient = self.colors['red_team_gradient']
        elif project_type == "blueteam":
            tile_color = self.colors['blue_team_tile']
            tile_gradient = self.colors['blue_team_gradient']
        else:  # clean or other
            tile_color = self.colors['tile_bg']
            tile_gradient = self.colors['tile_gradient_end']
        
        tile = GradientFrame(tile_color, tile_gradient)
        tile.setFixedWidth(350)
        tile.setMinimumHeight(280)  # Increased to fit all content
        tile.setMaximumHeight(400)  # Allow some growth
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        tile.setGraphicsEffect(shadow)
        
        tile.setStyleSheet("border-radius: 15px;")

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(25, 30, 25, 30)
        layout.setSpacing(15)

        # Title
        title_label = QLabel(config['name'])
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 20px;
            font-weight: 600;
            background-color: transparent;
        """)

        # Description
        desc_label = QLabel(config['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 14px;
            font-weight: 400;
            line-height: 1.5;
            background-color: transparent;
        """)

        # Button with team-specific color
        button = QPushButton("Start Investigation")
        button.setFixedHeight(45)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.lighten_color(tile_color, 30)};
                color: {self.colors['text_white']};
                border: none;
                border-radius: 22px;
                font-size: 15px;
                font-weight: 600;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(tile_color, 40)};
            }}
            QPushButton:pressed {{
                background-color: {tile_color};
            }}
        """)
        button.clicked.connect(lambda: self.start_project(project_type, category_id))

        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addStretch()
        layout.addWidget(button)

        return tile

    def clear_layout(self, layout):
        """Helper to recursively clear a layout"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def show_category_selection(self, project_type):
        """Navigate to category selection screen"""
        # Change gradient overlay color based on project type
        if project_type == "redteam":
            self.gradient_overlay.set_gradient_color(self.colors['red_team_tile'])
        elif project_type == "blueteam":
            self.gradient_overlay.set_gradient_color(self.colors['blue_team_tile'])
        else:
            self.gradient_overlay.set_gradient_color('#923A5F')  # Purple for clean
        
        self.update_category_screen(project_type)
        self.stacked_widget.setCurrentIndex(2)
        self.footer_back_button.setVisible(True)

    def start_project(self, project_type, category):
        """Emit signal with project details and close window"""
        template_data = {
            'project_type': project_type,
            'category': category,
            'template': f"{project_type}_{category}",
            'metadata': {
                'title': f"{self.project_templates[project_type]['name']} - {self.project_templates[project_type]['categories'][category]['name']}",
                'created': '',
                'template': f"{project_type}_{category}"
            }
        }
        self.project_selected.emit(project_type, category, json.dumps(template_data))
        self.close()

    def create_footer(self):
        """Footer with copyright and navigation"""
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background-color: transparent; border: none;")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(40, 15, 40, 15)

        copyright_label = QLabel("© 2025 BeatRooter – One more project from the AntiXerox team.")
        copyright_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 12px;
            font-weight: 400;
            background-color: transparent;
        """)

        # Back button (hidden by default, shown on other screens)
        self.footer_back_button = QPushButton("← Back")
        self.footer_back_button.setFixedHeight(40)
        self.footer_back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.footer_back_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.colors['text_white']};
                border: 2px solid {self.colors['text_white']};
                border-radius: 10px;
                font-size: 14px;
                font-weight: 500;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        self.footer_back_button.setVisible(False)
        self.footer_back_button.clicked.connect(self.handle_back_navigation)

        layout.addWidget(copyright_label)
        layout.addStretch()
        layout.addWidget(self.footer_back_button)

        return footer

    def handle_back_navigation(self):
        """Handle back button clicks based on current screen"""
        current_index = self.stacked_widget.currentIndex()
        if current_index == 1:  # Project type screen
            self.gradient_overlay.set_gradient_color('#923A5F')  # Reset to purple
            self.stacked_widget.setCurrentIndex(0)
            self.footer_back_button.setVisible(False)
        elif current_index == 2:  # Category screen
            self.gradient_overlay.set_gradient_color('#923A5F')  # Reset to purple
            self.stacked_widget.setCurrentIndex(1)
            self.footer_back_button.setText("← Back")

    def apply_styles(self):
        """Apply global stylesheet"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.colors['page_bg']};
            }}
            QWidget {{
                background-color: transparent;
            }}
        """)

    def setup_animations(self):
        """Fade-in animation"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()

    def resizeEvent(self, event):
        """Keep gradient overlay sized properly"""
        super().resizeEvent(event)
        if hasattr(self, 'gradient_overlay'):
            central = self.centralWidget()
            if central:
                self.gradient_overlay.setGeometry(0, 0, central.width(), central.height())
                self.gradient_overlay.lower()

    # ----- Color Utilities -----
    def lighten_color(self, hex_color, amount=20):
        """Lighten a hex color"""
        try:
            r = min(255, int(hex_color[1:3], 16) + amount)
            g = min(255, int(hex_color[3:5], 16) + amount)
            b = min(255, int(hex_color[5:7], 16) + amount)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    def darken_color(self, hex_color, amount=20):
        """Darken a hex color"""
        try:
            r = max(0, int(hex_color[1:3], 16) - amount)
            g = max(0, int(hex_color[3:5], 16) - amount)
            b = max(0, int(hex_color[5:7], 16) - amount)
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    # ----- Action Handlers -----
    def start_new_project(self):
        """Navigate to project type selection"""
        self.stacked_widget.setCurrentIndex(1)
        self.footer_back_button.setVisible(True)

    def open_existing_project(self):
        """Open existing project file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, 'Open Investigation', '',
            'BeatRooter Tree Files (*.brt);;JSON Files (*.json);;All Files (*)'
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)

                # Emit with proper 3-parameter signature
                # For 'open' action, we use special values
                self.project_selected.emit("open", filename, json.dumps(project_data))
                self.close()

            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to open project: {e}")

    def start_beatbox(self):
        """Start BeatBox sandbox with category selection"""
        from ui.sandbox.sandbox_category_dialog import SandboxCategoryDialog
        
        # Show category selection dialog
        dialog = SandboxCategoryDialog(self)
        
        def on_category_selected(category_id):
            # Emit signal with sandbox project type and selected category
            template_data = {
                'project_type': 'sandbox',
                'category': category_id,
                'template': f"sandbox_{category_id}",
                'metadata': {
                    'title': f"Sandbox - {category_id.replace('_', ' ').title()}",
                    'created': '',
                    'template': f"sandbox_{category_id}"
                }
            }
            self.project_selected.emit('sandbox', category_id, json.dumps(template_data))
            self.close()
        
        dialog.category_selected.connect(on_category_selected)
        dialog.exec()
