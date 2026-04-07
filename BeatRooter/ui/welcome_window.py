from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QFileDialog, QMessageBox,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QStackedWidget, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QTimer, pyqtProperty, QUrl, QRect, QRectF, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QPixmap, QPainter, QLinearGradient, QPainterPath, QDesktopServices, QIcon, QGuiApplication
from PyQt6.QtSvg import QSvgRenderer
import json
import os
import sys
from ui.theme import (
    get_app_font,
    get_welcome_palette,
    lighten_color,
    darken_color,
    build_filled_button_qss,
    build_disabled_button_qss,
)
from features.beatnote.ui.beatnote_main_window import BeatNoteMainWindow

# Import version checker
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from utils.version_checker import get_version_info, check_for_updates
except ImportError:
    # Fallback if version checker not available
    def get_version_info():
        return {'background_color': '#2563eb', 'text': 'v1.0.0', 'border_color': '#1e40af'}
    def check_for_updates():
        return {'is_outdated': False, 'message': 'v1.0.0'}


def _default_project_templates():
    """Fallback project catalog for environments where core.project_catalog is unavailable."""
    return {
        "redteam": {
            "name": "Red Team",
            "description": "Offensive security testing and penetration testing.",
            "specializations": [
                "Web Application Testing",
                "Network Assessment",
                "Social Engineering",
                "Reverse Engineering",
                "Mobile Hacking",
                "Infra",
            ],
            "categories": {
                "web_application_testing": {
                    "name": "Web Application Testing",
                    "description": "Assess web applications for vulnerabilities, business logic flaws, and exploit chains.",
                },
                "network_assessment": {
                    "name": "Network Assessment",
                    "description": "Map, test, and validate network exposure across internal and external attack surfaces.",
                },
                "social_engineering": {
                    "name": "Social Engineering",
                    "description": "Evaluate human-layer defenses with realistic phishing, pretexting, and awareness simulations.",
                },
                "reverse_engineering": {
                    "name": "Reverse Engineering",
                    "description": "Dissect binaries and scripts to uncover functionality, hidden behavior, and weak protections.",
                },
                "mobile_hacking": {
                    "name": "Mobile Hacking",
                    "description": "Test Android and iOS apps for insecure storage, auth bypasses, and API abuse paths.",
                },
                "infra": {
                    "name": "Infra",
                    "description": "Pressure-test cloud and on-prem infrastructure configuration, segmentation, and privilege boundaries.",
                },
            },
        },
        "clean": {
            "name": "Clean Project",
            "description": "Feel like no category fills what you need? Start a blank project with access to every single tool and node.",
            "specializations": [
                "Everything, have fun!",
            ],
            "categories": {
                "blank": {
                    "name": "Blank Project",
                    "description": "Full access to all tools and nodes",
                },
            },
        },
        "blueteam": {
            "name": "Blue Team and SOC Ops.",
            "description": "Defensive security operations, incident response and SOC monitoring and analysis.",
            "specializations": [
                "Alert Triage",
                "Compliance Analysis",
                "Correlation Analysis",
                "Incident Response",
                "Threat Hunting",
                "Malware Analysis",
                "SIEM Investigation",
            ],
            "categories": {
                "alert_triage": {
                    "name": "Alert Triage",
                    "description": "Prioritize incoming alerts, remove noise, and route high-confidence signals to responders.",
                },
                "compliance_analysis": {
                    "name": "Compliance Analysis",
                    "description": "Validate controls and evidence against policy baselines and regulatory requirements.",
                },
                "correlation_analysis": {
                    "name": "Correlation Analysis",
                    "description": "Link telemetry across sources to reconstruct attacker timelines and campaign patterns.",
                },
                "incident_response": {
                    "name": "Incident Response",
                    "description": "Contain, investigate, and recover from active incidents using structured response playbooks.",
                },
                "threat_hunting": {
                    "name": "Threat Hunting",
                    "description": "Proactively search for stealthy adversary behavior before alerts trigger.",
                },
                "malware_analysis": {
                    "name": "Malware Analysis",
                    "description": "Analyze suspicious payloads to classify threats, capabilities, and persistence methods.",
                },
                "siem_investigation": {
                    "name": "SIEM Investigation",
                    "description": "Investigate multi-source log evidence to confirm incidents and scope impact quickly.",
                },
            },
        },
    }


try:
    from core.project_catalog import PROJECT_TEMPLATES
except ImportError:
    PROJECT_TEMPLATES = _default_project_templates()


class GradientFrame(QFrame):
    """Custom frame with gradient background and subtle transparency"""
    def __init__(self, start_color, end_color, parent=None):
        super().__init__(parent)
        self.start_color = QColor(start_color)
        self.end_color = QColor(end_color)
        self.border_radius = 20  # Default border radius
        
        # Set semi-transparent background for glass effect
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.border_radius, self.border_radius)
        
        # Create gradient with 33% opacity
        gradient = QLinearGradient(0, 0, 0, self.height())
        
        # Apply 33% transparency to colors
        start_with_alpha = QColor(self.start_color)
        start_with_alpha.setAlpha(84)  # 33% opacity
        end_with_alpha = QColor(self.end_color)
        end_with_alpha.setAlpha(84)  # 33% opacity
        
        gradient.setColorAt(0, start_with_alpha)
        gradient.setColorAt(0.7, start_with_alpha)
        gradient.setColorAt(1, end_with_alpha)
        
        # Fill with gradient using the rounded path
        painter.fillPath(path, gradient)


class ReverseGradientFrame(QFrame):
    """Atmospheric gradient with smooth color transitions and wave animation - black to color fade"""
    def __init__(self, bottom_color, parent=None):
        super().__init__(parent)
        # Much stronger gradient for highly visible effect
        self._bottom_color = QColor(bottom_color)
        self._bottom_color.setAlpha(120)  # Increased opacity for aggressive visibility
        # Top starts as black/very dark
        self.top_color = QColor(20, 20, 35, 0)  # Very dark with transparency
        
        # Wave animation offset for slow sea effect
        self._wave_offset = 0.0
        
        # Animation for smooth color transitions
        self.color_animation = QPropertyAnimation(self, b"bottomColor")
        self.color_animation.setDuration(800)  # 800ms transition
        self.color_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Wave animation - slow continuous movement
        self.wave_animation = QPropertyAnimation(self, b"waveOffset")
        self.wave_animation.setDuration(6000)  # 6 seconds for full wave cycle
        self.wave_animation.setStartValue(0.0)
        self.wave_animation.setEndValue(1.0)
        self.wave_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.wave_animation.setLoopCount(-1)  # Infinite loop
        self.wave_animation.start()
    
    def get_wave_offset(self):
        """Get current wave offset"""
        return self._wave_offset
    
    def set_wave_offset(self, offset):
        """Set wave offset and trigger repaint"""
        self._wave_offset = offset
        self.update()
    
    waveOffset = pyqtProperty(float, get_wave_offset, set_wave_offset)
    
    def get_bottom_color(self):
        """Get current bottom color"""
        return self._bottom_color
    
    def set_bottom_color(self, color):
        """Set bottom color and trigger repaint"""
        if isinstance(color, QColor):
            self._bottom_color = color
        else:
            self._bottom_color = QColor(color)
            self._bottom_color.setAlpha(120)  # Strong opacity
        self.update()
    
    bottomColor = pyqtProperty(QColor, get_bottom_color, set_bottom_color)
    
    def set_gradient_color(self, color, animated=True):
        """Update the gradient color with smooth animation"""
        target_color = QColor(color)
        target_color.setAlpha(120)  # Strong opacity for visibility
        
        if animated:
            self.color_animation.stop()
            self.color_animation.setStartValue(self._bottom_color)
            self.color_animation.setEndValue(target_color)
            self.color_animation.start()
        else:
            self.set_bottom_color(target_color)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Create wave effect by shifting gradient position
        wave_shift = int(self.height() * 0.1 * abs(self._wave_offset - 0.5) * 2)  # Max 10% shift
        
        gradient = QLinearGradient(0, -wave_shift, 0, self.height() + wave_shift)
        gradient.setColorAt(0, self.top_color)  # Dark/transparent at top
        gradient.setColorAt(0.4, self.top_color)  # Stay dark, then transition faster
        gradient.setColorAt(1, self._bottom_color)  # Strong color at bottom
        painter.fillRect(self.rect(), gradient)


class WelcomeWindow(QMainWindow):
    project_selected = pyqtSignal(str, str, str)  # project_type, category, template_json
    SCREEN_WELCOME = 0
    SCREEN_PROJECT_TYPE = 1
    SCREEN_CATEGORY = 2
    SCREEN_POPUP = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeatRooter - Your Tool for Forensics and Security Analysis")
        
        screen = QGuiApplication.primaryScreen().geometry()
        
        # Use 85% of screen size for better fit, but respect minimum
        window_width = max(1100, int(screen.width() * 0.85))
        window_height = max(750, int(screen.height() * 0.85))
        
        # Center window on screen
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        
        self.setGeometry(x, y, window_width, window_height)
        # Enforce minimum size to prevent layout collapse and clipping
        # Width: 1200px to fit carousel (1100px) + arrows (100px) + margins
        # Height: 900px to ensure back button always visible (header 80 + content 700 + footer 60 + margins 60)
        self.setMinimumSize(1200, 900)

        # New Color Palette - Execution-Critical
        self.colors = get_welcome_palette()

        # Check version and update badge
        version_check = check_for_updates()
        version_info = get_version_info()
        
        self.version_text = version_info['text']
        self.colors['version_badge_bg'] = version_info['background_color']
        
        if version_check['is_outdated']:
            self.freshness_message = "Your vegetables are rotting!"
            self.freshness_color = self.colors['red_rotten']
        else:
            self.freshness_message = "Your vegetables are Fresh!"
            self.freshness_color = self.colors['text_white']

        # Load Inria Sans from local files and keep the name quoted for QSS.
        self.app_font = get_app_font()

        # Paths to assets
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.logo_path = os.path.join(self.base_path, 'assets', 'beatrooter_logo.svg')

        self.project_templates = PROJECT_TEMPLATES

        # Cache category widgets per project type to avoid visible first-open construction.
        self.category_tile_cache = {}
        self.category_list_cache = {}
        self._team_pages = {}
        self._category_caches_warmed = False
        self._responsive_header_targets = []

        self.setup_ui()
        self.apply_styles()
        self.setup_animations()

    def setup_ui(self):
        """Build the entire UI structure"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
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
        self.popup_stuff_screen = self.create_popup_stuff_screen()

        # Add screens to stacked widget
        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.project_type_screen)
        self.stacked_widget.addWidget(self.category_screen)
        self.stacked_widget.addWidget(self.popup_stuff_screen)

        main_layout.addWidget(self.stacked_widget, 1)
        # Footer
        footer = self.create_footer()
        main_layout.addWidget(footer)

        # Ensure gradient is visible but behind interactive elements
        self.gradient_overlay.raise_()
        header.raise_()
        self.stacked_widget.raise_()
        footer.raise_()
        # Company logo overlay (bottom-right) that does not consume layout space.
        self.company_corner_logo = QLabel(central_widget)
        self.company_corner_logo.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.company_corner_logo.setStyleSheet("background-color: transparent;")
        self.company_corner_logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        company_logo_path = os.path.join(self.base_path, 'assets', 'icons', 'category', 'Reinvicta cix.svg')
        if os.path.exists(company_logo_path):
            company_icon = QIcon(company_logo_path)
            self.company_corner_logo.setPixmap(company_icon.pixmap(QSize(320, 80)))
            self.company_corner_logo.setFixedSize(320, 80)
        else:
            self.company_corner_logo.setText("Reinvicta cix")
            self.company_corner_logo.setStyleSheet(f"""
                color: {self.colors['text_white']};
                font-size: 18px;
                font-weight: 600;
                font-family: {self.app_font};
                background-color: transparent;
            """)
            self.company_corner_logo.adjustSize()
        self._update_company_logo_position()
        self._update_company_logo_visibility(self.stacked_widget.currentIndex())
        self.stacked_widget.currentChanged.connect(self._update_company_logo_visibility)
        self.stacked_widget.currentChanged.connect(lambda _: self._apply_responsive_header_sizes())
        self.company_corner_logo.raise_()

        # Warm caches once the first event loop starts so first open feels instant.
        QTimer.singleShot(0, self._warmup_category_caches)
        # Re-apply responsive text/icon sizes after initial layout settles.
        QTimer.singleShot(0, self._apply_responsive_header_sizes)
    
    def _warmup_category_caches(self):
        """Build category carousel tiles and list items once per project type."""
        for project_type, cfg in self.project_templates.items():
            tile_bucket = self.category_tile_cache.setdefault(project_type, {})
            list_bucket = self.category_list_cache.setdefault(project_type, {})

            for cat_id, cat_conf in cfg['categories'].items():
                if cat_id not in tile_bucket:
                    tile_bucket[cat_id] = self.create_category_tile(project_type, cat_id, cat_conf)
                if cat_id not in list_bucket:
                    list_bucket[cat_id] = self.create_category_list_item(project_type, cat_id, cat_conf)

        # Pre-build full page scaffolding for instant first open
        for pt in self.project_templates:
            if pt not in self._team_pages:
                self._build_team_page(pt)

        self._category_caches_warmed = True

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

        # GitHub button with logo
        github_button = QPushButton()
        github_button.setCursor(Qt.CursorShape.PointingHandCursor)
        github_button.clicked.connect(self.open_github)
        github_button.setFixedHeight(35)
        
        # Load GitHub logo
        github_logo_path = os.path.join(self.base_path, 'designs', 'icons', 'github logo.png')
        
        github_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                padding: 5px 12px;
                text-align: left;
                color: {self.colors['text_white']};
                font-size: 14px;
                font-family: {self.app_font};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }}
        """)
        
        # Set icon and text with purple filter
        if os.path.exists(github_logo_path):
            github_pixmap = QPixmap(github_logo_path)
            
            # Apply purple tint to the image
            purple_pixmap = QPixmap(github_pixmap.size())
            purple_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(purple_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw original image
            painter.drawPixmap(0, 0, github_pixmap)
            
            # Apply purple overlay
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
            painter.fillRect(purple_pixmap.rect(), QColor(200, 85, 138, 150))  # Purple tint with transparency
            painter.end()
            
            icon = QIcon(purple_pixmap)
            github_button.setIcon(icon)
            github_button.setIconSize(QSize(20, 20))
        
        github_button.setText("GitHub")


        # Mail
        contact_button = QPushButton("Message  Contact")
        contact_button.setCursor(Qt.CursorShape.PointingHandCursor)
        contact_button.clicked.connect(self.open_contact_email)
        contact_button.setFixedHeight(35)
        contact_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                padding: 5px 12px;
                text-align: left;
                color: {self.colors['text_white']};
                font-size: 14px;
                font-family: {self.app_font};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
            }}
        """)

        left_layout.addWidget(github_button)
        left_layout.addWidget(contact_button)

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
            font-family: {self.app_font};
            padding: 6px 12px;
        """)
        version_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Freshness message
        freshness_label = QLabel(self.freshness_message)
        freshness_label.setStyleSheet(f"""
            color: {self.freshness_color};
            font-size: 11px;
            font-weight: {'700' if self.freshness_color == self.colors['red_rotten'] else '400'};
            font-family: {self.app_font};
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(25)

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
        layout.setSpacing(15)

        # Logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("background-color: transparent;")
        logo_label.setScaledContents(False)
        
        if os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            # Scale to 140px height for compact layout
            scaled_pixmap = pixmap.scaledToHeight(140, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback text if logo not found
            logo_label.setText("🥕")
            logo_label.setStyleSheet("font-size: 70px; background-color: transparent;")

        # Welcome Text - Line 1 (Bold)
        welcome_line1 = QLabel("Welcome to BeatRooter!")
        welcome_line1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_line1.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 28px;
            font-weight: 700;
            font-family: {self.app_font};
            background-color: transparent;
        """)

        # Welcome Text - Line 2 (Regular with emphasis)
        welcome_line2 = QLabel("Your Tool for Forensics and Security Analysis.")
        welcome_line2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_line2.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 16px;
            font-weight: 500;
            font-style: italic;
            font-family: {self.app_font};
            background-color: transparent;
        """)

        # Welcome Text - Line 3 (Lighter)
        welcome_line3 = QLabel("Ready to start Farming?")
        welcome_line3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_line3.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 14px;
            font-weight: 300;
            font-family: {self.app_font};
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
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(5, 0, 5, 0)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

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

        # Tile 4: Pop Up Stuff
        tile4 = self.create_feature_tile(
            title="Pop Up Stuff",
            description="Open pop-ups to help you use the app. This includes Notes, Hints, and Mini Games.",
            button_text="Open Pop-Ups",
            callback=self.show_popup_stuff_menu,
            enabled=True,
            tile_color=self.colors['popup_tile'],
            tile_gradient_end=self.colors['popup_gradient'],
            button_base_color=self.colors['popup_button']
        )

        grid_layout.addWidget(tile1)
        grid_layout.addWidget(tile2)
        grid_layout.addWidget(tile3)
        grid_layout.addWidget(tile4)

        return grid_layout

    def create_feature_tile(self, title, description, button_text, callback, enabled, tile_color=None, tile_gradient_end=None, button_base_color=None, tile_height=280, description_font_size=16):
        """Create a single feature tile with gradient background and transparency"""
        # Use custom gradient frame with optional color overrides
        tile_color = tile_color or '#923A5F'
        tile_gradient_end = tile_gradient_end or '#7A2E4F'
        tile = GradientFrame(tile_color, tile_gradient_end)
        # Narrower tiles
        tile.setMinimumWidth(220)
        tile.setMaximumWidth(280)
        tile.setMinimumHeight(tile_height)
        tile.setMaximumHeight(tile_height)
        tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        tile.setGraphicsEffect(shadow)
        
        # Round corners styling
        tile.setStyleSheet(f"""
            border-radius: 20px;
        """)

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(24, 28, 24, 28)  # More padding
        layout.setSpacing(0)  # Manual spacing
        
        # Title - at the top of the bubble, centered, Inter, font-weight: 600
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 20px;
            font-weight: 600;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(title_label)
        layout.addSpacing(16)  # 16px after title

        # Description - centered, Inter, font-weight: 400, line-height: 1.5
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: {description_font_size}px;
            font-weight: 400;
            font-family: {self.app_font};
            line-height: 1.5;
            background-color: transparent;
        """)
        layout.addWidget(desc_label)
        
        layout.addStretch()  # Push button to bottom
        layout.addSpacing(20)  # 20px before button

        # Button
        button = QPushButton(button_text)
        button.setFixedHeight(40)
        button.setCursor(Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor)
        
        if enabled:
            button_base_color = button_base_color or self.colors['button_active']
            button.setStyleSheet(build_filled_button_qss(
                self.app_font,
                button_base_color,
                self.colors['text_white'],
                radius=12,
                font_size=15,
                padding="10px 20px"
            ))
            if callback:
                button.clicked.connect(callback)
        else:
            button.setStyleSheet(build_disabled_button_qss(
                self.app_font,
                self.colors['button_disabled'],
                self.colors['text_light_gray'],
                radius=12,
                font_size=15,
                padding="10px 20px"
            ))
            button.setEnabled(False)

        layout.addWidget(button)

        return tile

    def create_popup_stuff_screen(self):
        """UI-only submenu screen for future popup-related features"""
        screen = QWidget()
        screen.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(screen)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(25)

        header, _ = self._build_selection_header(
            title_text="Pop Up Stuff",
            subtitle_text="Open dedicated assistive spaces like BeatNote, plus future hints and mini games",
            accent_color=self.colors['popup_tile'],
        )

        cards_container = QWidget()
        cards_container.setStyleSheet("background-color: transparent;")
        cards_layout = QHBoxLayout(cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(20)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        notes_card = self.create_feature_tile(
            title="Notes",
            description="Open the dedicated BeatNote window for recon notes, credentials, evidence and attack planning.",
            button_text="Open BeatNote",
            callback=self.open_beatnote_window,
            enabled=True,
            tile_color=self.colors['popup_tile'],
            tile_gradient_end=self.colors['popup_gradient'],
            button_base_color=self.colors['popup_button'],
            tile_height=380,
            description_font_size=16
        )
        hints_card = self.create_feature_tile(
            title="Hints",
            description="Future workflow hints and assistive prompts integrated into key app moments.",
            button_text="Planned",
            callback=None,
            enabled=False,
            tile_color=self.colors['popup_tile'],
            tile_gradient_end=self.colors['popup_gradient'],
            tile_height=380,
            description_font_size=16
        )
        games_card = self.create_feature_tile(
            title="Mini Games",
            description="Future lightweight assistive games section for engagement and learning support.",
            button_text="Planned",
            callback=None,
            enabled=False,
            tile_color='#7C4F00',
            tile_gradient_end='#5C3A00',
            tile_height=380,
            description_font_size=16
        )

        cards_layout.addWidget(notes_card)
        cards_layout.addWidget(hints_card)
        cards_layout.addWidget(games_card)

        layout.addWidget(header)
        # Keep card row aligned with the welcome menu card band
        layout.addSpacing(35)
        layout.addWidget(cards_container)
        layout.addStretch()

        return screen

    def _header_scale_factor(self):
        """Return a clamped scale factor so large screens stay structured."""
        base_width = 1366
        base_height = 900
        width_factor = self.width() / base_width if self.width() > 0 else 1.0
        height_factor = self.height() / base_height if self.height() > 0 else 1.0
        return max(0.92, min(1.14, min(width_factor, height_factor)))

    def _register_responsive_header(self, logo_label, title_label, subtitle_label, accent_line,
                                    top_layout=None, title_block_layout=None, title_text_layout=None,
                                    accent_color=None, scalable=True):
        """Track header widgets so font/icon sizing can respond to window size changes."""
        self._responsive_header_targets.append({
            'logo_label': logo_label,
            'title_label': title_label,
            'subtitle_label': subtitle_label,
            'accent_line': accent_line,
            'top_layout': top_layout,
            'title_block_layout': title_block_layout,
            'title_text_layout': title_text_layout,
            'accent_color': accent_color or "rgba(255, 255, 255, 0.65)",
            'has_logo_pixmap': os.path.exists(self.logo_path),
            'scalable': scalable,
        })
        self._apply_responsive_header_sizes()

    def _apply_responsive_header_sizes(self):
        """Keep all menu headers visually consistent across resolutions."""
        if not hasattr(self, '_responsive_header_targets'):
            return

        scale = self._header_scale_factor()
        logo_height = max(64, int(round(80 * scale)))
        title_px = max(24, int(round(28 * scale)))
        subtitle_px = max(14, int(round(15 * scale)))
        accent_width = max(3, int(round(4 * scale)))
        top_spacing = max(10, int(round(12 * scale)))
        block_spacing = max(8, int(round(10 * scale)))
        text_spacing = max(2, int(round(2 * scale)))

        stale_targets = []
        for target in self._responsive_header_targets:
            try:
                target_scale = scale if target.get('scalable', True) else 1.0
                logo_height = max(64, int(round(80 * target_scale)))
                title_px = max(24, int(round(28 * target_scale)))
                subtitle_px = max(14, int(round(15 * target_scale)))
                accent_width = max(3, int(round(4 * target_scale)))
                top_spacing = max(10, int(round(12 * target_scale)))
                block_spacing = max(8, int(round(10 * target_scale)))
                text_spacing = max(2, int(round(2 * target_scale)))
                logo_label = target['logo_label']
                title_label = target['title_label']
                subtitle_label = target['subtitle_label']
                accent_line = target['accent_line']

                if target['has_logo_pixmap'] and os.path.exists(self.logo_path):
                    pixmap = QPixmap(self.logo_path)
                    logo_label.setPixmap(pixmap.scaledToHeight(logo_height, Qt.TransformationMode.SmoothTransformation))
                else:
                    logo_label.setStyleSheet(f"""
                        color: {self.colors['text_white']};
                        font-size: {max(26, int(round(30 * target_scale)))}px;
                        font-weight: 700;
                        font-family: {self.app_font};
                        background-color: transparent;
                    """)

                title_label.setStyleSheet(f"""
                    color: {self.colors['text_white']};
                    font-size: {title_px}px;
                    font-weight: 500;
                    font-family: {self.app_font};
                    background-color: transparent;
                """)
                subtitle_label.setStyleSheet(f"""
                    color: {self.colors['text_white']};
                    font-size: {subtitle_px}px;
                    font-weight: 400;
                    font-family: {self.app_font};
                    background-color: transparent;
                """)

                accent_line.setFixedWidth(accent_width)
                accent_line.setStyleSheet(f"background-color: {target['accent_color']}; border-radius: 2px;")

                if target['top_layout'] is not None:
                    target['top_layout'].setSpacing(top_spacing)
                if target['title_block_layout'] is not None:
                    target['title_block_layout'].setSpacing(block_spacing)
                if target['title_text_layout'] is not None:
                    target['title_text_layout'].setSpacing(text_spacing)

            except RuntimeError:
                stale_targets.append(target)

        if stale_targets:
            self._responsive_header_targets = [t for t in self._responsive_header_targets if t not in stale_targets]

    def _build_selection_header(self, title_text, subtitle_text, accent_color, fallback_logo_text="BeatRooter"):
        """Create the shared selection header used by project and team screens."""
        header_container = QWidget()
        header_container.setStyleSheet("background-color: transparent;")
        header_main_layout = QHBoxLayout(header_container)
        header_main_layout.setContentsMargins(0, 0, 0, 0)
        header_main_layout.setSpacing(20)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(12)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        logo_label.setStyleSheet("background-color: transparent;")
        logo_label.setScaledContents(False)
        if os.path.exists(self.logo_path):
            pixmap = QPixmap(self.logo_path)
            scaled_pixmap = pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText(fallback_logo_text)
            if fallback_logo_text == "🥕":
                logo_label.setStyleSheet("font-size: 50px; background-color: transparent;")
            else:
                logo_label.setStyleSheet(f"""
                    color: {self.colors['text_white']};
                    font-size: 28px;
                    font-weight: 700;
                    font-family: {self.app_font};
                    background-color: transparent;
                """)

        title_label = QLabel(title_text)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 28px;
            font-weight: 500;
            font-family: {self.app_font};
            background-color: transparent;
        """)

        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        subtitle_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 15px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
        """)

        title_block = QWidget()
        title_block.setStyleSheet("background-color: transparent;")
        title_block.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        title_block_layout = QHBoxLayout(title_block)
        title_block_layout.setContentsMargins(0, 0, 0, 0)
        title_block_layout.setSpacing(10)
        title_block_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        accent_line = QFrame()
        accent_line.setFixedWidth(4)
        accent_line.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        accent_line.setStyleSheet(f"background-color: {accent_color}; border-radius: 2px;")

        title_text_container = QWidget()
        title_text_container.setStyleSheet("background-color: transparent;")
        title_text_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        title_text_layout = QVBoxLayout(title_text_container)
        title_text_layout.setContentsMargins(0, 0, 0, 0)
        title_text_layout.setSpacing(2)
        title_text_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title_text_layout.addWidget(title_label)
        title_text_layout.addWidget(subtitle_label)

        title_text_container.adjustSize()
        text_size_hint = title_text_container.sizeHint()
        title_text_container.setFixedSize(text_size_hint)
        accent_line.setFixedHeight(text_size_hint.height())
        title_block.setFixedSize(text_size_hint.width() + 10 + accent_line.width(), text_size_hint.height())

        title_block_layout.addWidget(accent_line, 0, Qt.AlignmentFlag.AlignTop)
        title_block_layout.addWidget(title_text_container, 0, Qt.AlignmentFlag.AlignTop)

        header_layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        header_layout.addWidget(title_block, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._register_responsive_header(
            logo_label=logo_label,
            title_label=title_label,
            subtitle_label=subtitle_label,
            accent_line=accent_line,
            top_layout=header_layout,
            title_block_layout=title_block_layout,
            title_text_layout=title_text_layout,
            accent_color=accent_color,
            scalable=False,
        )

        back_button_container = QWidget()
        back_button_container.setStyleSheet("background-color: transparent;")
        back_button_layout = QVBoxLayout(back_button_container)
        back_button_layout.setContentsMargins(0, 0, 0, 0)
        back_button_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        back_button = self._make_back_button()
        back_button.clicked.connect(self.handle_back_navigation)
        back_button_layout.addWidget(back_button)
        back_button_layout.addStretch()

        header_main_layout.addLayout(header_layout)
        header_main_layout.addStretch()
        header_main_layout.addWidget(back_button_container)

        return header_container, back_button

    def create_project_type_screen(self):
        """Project type selection screen with three horizontal tiles"""
        screen = QWidget()
        screen.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(screen)
        layout.setContentsMargins(40, 20, 40, 20)
        layout.setSpacing(20)

        header_container, _ = self._build_selection_header(
            title_text="Select Project Type",
            subtitle_text="Choose the specialized workflow for your analysis",
            accent_color="rgba(255, 255, 255, 0.65)",
            fallback_logo_text="🥕",
        )

        # Tiles container with horizontal layout and center alignment
        tiles_container = QWidget()
        tiles_container.setStyleSheet("background-color: transparent;")
        tiles_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tiles_layout = QHBoxLayout(tiles_container)
        tiles_layout.setSpacing(20)
        tiles_layout.setContentsMargins(0, 15, 0, 15)
        tiles_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Order: Red Team, Clean Project, Blue Team
        red_tile = self.create_project_type_tile("redteam", self.project_templates["redteam"])
        clean_tile = self.create_project_type_tile("clean", self.project_templates["clean"])
        blue_tile = self.create_project_type_tile("blueteam", self.project_templates["blueteam"])

        tiles_layout.addWidget(red_tile)
        tiles_layout.addWidget(clean_tile)
        tiles_layout.addWidget(blue_tile)

        # Add everything to content layout
        layout.addWidget(header_container)
        layout.addWidget(tiles_container)
        layout.addStretch()

        return screen

    def create_project_type_tile(self, project_type, config):
        """Create a single project type tile"""
        tile_color, tile_gradient = self._tile_colors(project_type)

        # Use GradientFrame for consistent styling with transparency
        tile = GradientFrame(tile_color, tile_gradient)
        # Reduced width for less fat cards
        tile.setMinimumWidth(240)
        tile.setMaximumWidth(320)
        tile.setMinimumHeight(380)
        tile.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        tile.setGraphicsEffect(shadow)
        
        # Glass effect styling
        tile.setStyleSheet(f"""
            border-radius: 16px;
        """)

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(32, 32, 32, 32)  # Increased padding
        layout.setSpacing(0)  # Manual spacing below
        
        # Title - at the top of the bubble (white, headings) - font-weight: 600
        title_label = QLabel(config['name'])
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 24px;
            font-weight: 600;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(title_label)
        layout.addSpacing(18)  # 18px space after title

        # Description (light gray/white body text) - font-weight: 400
        desc_label = QLabel(config['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 16px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(desc_label)
        layout.addSpacing(22)  # 22px space before specializations

        # Specializations header - font-weight: 500
        spec_header = QLabel("Available Specializations:")
        spec_header.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 17px;
            font-weight: 500;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(spec_header)
        layout.addSpacing(10)  # 10px space before list

        # Specializations list (using bullet points from config) - font-weight: 400
        spec_text = "\n".join(f"• {item}" for item in config['specializations'])
        spec_label = QLabel(spec_text)
        spec_label.setWordWrap(True)
        spec_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        spec_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 16px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(spec_label)
        
        layout.addStretch()  # Push button to bottom
        layout.addSpacing(24)  # 24px space before button
        
        # Button text mapping
        button_text_map = {
            "redteam": "Start Red Project",
            "clean": "Start Blank Project",
            "blueteam": "Start Blue/SOC Project"
        }
        button_text = button_text_map.get(project_type, f"Start {config['name']} Project")
        
        # Button - exactly matching the working welcome screen pattern
        button = QPushButton(button_text)
        button.setObjectName("project_type_cta")
        button.setFixedHeight(46)
        button.setFixedWidth(252)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Calculate lighter button color
        button_color = self.lighten_color(tile_color, 30)
        button_hover = self.lighten_color(tile_color, 40)
        
        button.setStyleSheet(f"""
            QPushButton#project_type_cta {{
                background-color: {button_color};
                color: {self.colors['text_white']};
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 12px;
                font-size: 17px;
                font-weight: 600;
                font-family: {self.app_font};
                padding: 0px;
                margin: 0px;
                text-align: center;
            }}
            QPushButton#project_type_cta:hover {{
                background-color: {button_hover};
            }}
            QPushButton#project_type_cta:pressed {{
                background-color: {tile_color};
            }}
        """)
        
        # For clean project, go directly to project creation (skip category selection)
        if project_type == "clean":
            button.clicked.connect(lambda: self.start_project(project_type, "blank"))
        else:
            button.clicked.connect(lambda: self.show_category_selection(project_type))
        
        layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)

        return tile

    def create_category_screen(self):
        """Thin container; content is swapped in by update_category_screen."""
        screen = QWidget()
        screen.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(screen)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._team_page_slot = QStackedWidget()
        self._team_page_slot.setStyleSheet("background-color: transparent;")
        self._team_page_slot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._team_page_slot)

        self.carousel_mode = True
        self.current_carousel_index = 0

        return screen

    def update_category_screen(self, project_type):
        """Swap in the pre-built team page — no widget construction at click time."""
        self.cleanup_carousel_state()
        self.current_project_type = project_type

        if not self._category_caches_warmed:
            self._warmup_category_caches()

        if project_type not in self._team_pages:
            self._build_team_page(project_type)

        page_data = self._team_pages[project_type]
        slot = self._team_page_slot
        if slot.indexOf(page_data['widget']) == -1:
            slot.addWidget(page_data['widget'])
        slot.setCurrentWidget(page_data['widget'])

        # Update instance refs so navigate_carousel, switch_view_mode, etc. work correctly
        self.carousel_btn            = page_data['carousel_btn']
        self.list_btn                = page_data['list_btn']
        self.category_back_button    = page_data['back_button']
        self.carousel_viewport       = page_data['carousel_viewport']
        self.all_category_tiles      = page_data['all_category_tiles']
        self.all_category_list_items = page_data['all_category_list_items']
        self.carousel_slots          = page_data['carousel_slots']
        self.category_view_stack     = page_data['view_stack']
        self.left_arrow_btn          = page_data['left_arrow_btn']
        self.right_arrow_btn         = page_data['right_arrow_btn']

        # Reset to carousel at index 0
        self.carousel_mode = True
        self.current_carousel_index = 0
        self._position_carousel_tiles(animate=False)
        self.category_view_stack.setCurrentIndex(0)
        self.update_toggle_styles()

        # Collapse any list items left open from a previous visit
        for _, item in self.all_category_list_items:
            try:
                if hasattr(item, '_collapse'):
                    item._collapse()
            except RuntimeError:
                continue
    
    def switch_view_mode(self, is_carousel):
        """Switch between carousel and list view"""
        if self.carousel_mode == is_carousel:
            return

        self.carousel_mode = is_carousel
        self.update_toggle_styles()

        if hasattr(self, 'category_view_stack') and self.category_view_stack is not None:
            self.category_view_stack.setCurrentIndex(0 if is_carousel else 1)
            if is_carousel:
                self._position_carousel_tiles(animate=False)
    
    def update_toggle_styles(self):
        """Update toggle button styles based on active view"""
        team_color, _ = self._tile_colors(getattr(self, 'current_project_type', 'clean'))

        active_style = f"""
            QPushButton {{
                background-color: {team_color};
                color: {self.colors['text_white']};
                border: 1px solid {team_color};
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                font-family: {self.app_font};
                padding: 0px 16px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {self.lighten_color(team_color, 15)};
            }}
        """
        
        inactive_style = f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: {self.colors['text_light_gray']};
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                font-family: {self.app_font};
                padding: 0px 16px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
            }}
        """
        
        if self.carousel_mode:
            self.carousel_btn.setStyleSheet(active_style)
            self.list_btn.setStyleSheet(inactive_style)
        else:
            self.carousel_btn.setStyleSheet(inactive_style)
            self.list_btn.setStyleSheet(active_style)

    def _build_team_page(self, project_type):
        """Pre-build a complete category page (header + carousel + list) for instant first open."""
        config = self.project_templates[project_type]
        categories = list(config['categories'].items())
        team_color, _ = self._tile_colors(project_type)
        tile_bucket = self.category_tile_cache.get(project_type, {})
        list_bucket = self.category_list_cache.get(project_type, {})
        all_tiles = [(cat_id, tile_bucket[cat_id]) for cat_id, _ in categories if cat_id in tile_bucket]
        all_list_items = [(cat_id, list_bucket[cat_id]) for cat_id, _ in categories if cat_id in list_bucket]

        # ── Outer page (fills _team_page_slot) ─────────────────────────
        page = QWidget()
        page.setStyleSheet("background-color: transparent;")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(40, 20, 40, 20)
        page_layout.setSpacing(20)

        header_container, back_button = self._build_selection_header(
            title_text=f"Choose {config['name']} Specialization",
            subtitle_text="Select the specific investigation workflow that matches your requirements",
            accent_color=team_color,
        )
        page_layout.addWidget(header_container)

        # ── Toggle buttons ───────────────────────────────────────────────
        toggle_container = QWidget()
        toggle_container.setStyleSheet("background-color: transparent;")
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 10, 0, 6)
        toggle_layout.addStretch()

        carousel_btn = QPushButton("⟲ Carousel View")
        list_btn = QPushButton("☰ List View")
        for btn in [carousel_btn, list_btn]:
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.1);
                    color: {self.colors['text_light_gray']};
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 500;
                    font-family: {self.app_font};
                    padding: 0px 16px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.15);
                    border-color: rgba(255, 255, 255, 0.3);
                }}
            """)
        carousel_btn.clicked.connect(lambda: self.switch_view_mode(True))
        list_btn.clicked.connect(lambda: self.switch_view_mode(False))
        toggle_layout.addWidget(carousel_btn)
        toggle_layout.addSpacing(10)
        toggle_layout.addWidget(list_btn)
        toggle_layout.addStretch()
        page_layout.addWidget(toggle_container)

        # ── View stack (carousel=0, list=1) ────────────────────────────
        view_stack = QStackedWidget()
        view_stack.setStyleSheet("background-color: transparent;")
        view_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        page_layout.addWidget(view_stack, 1)

        # ── Carousel page ───────────────────────────────────────────────
        carousel_page = QWidget()
        carousel_page.setStyleSheet("background-color: transparent;")
        carousel_layout = QVBoxLayout(carousel_page)
        carousel_layout.setContentsMargins(0, 0, 0, 20)
        carousel_layout.setSpacing(0)

        nav_container = QWidget()
        nav_container.setStyleSheet("background-color: transparent;")
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(20)

        left_arrow_btn = QPushButton("◀")
        left_arrow_btn.setFixedSize(50, 50)
        left_arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        arrow_style = f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: {self.colors['text_white']};
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 25px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
                border-color: rgba(255, 255, 255, 0.5);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """
        left_arrow_btn.setStyleSheet(arrow_style)
        left_arrow_btn.clicked.connect(lambda: self.navigate_carousel(-1))

        carousel_viewport = QWidget()
        carousel_viewport.setStyleSheet("QWidget { background-color: transparent; }")
        carousel_viewport.setFixedSize(1100, 440)
        carousel_viewport.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        carousel_viewport.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        carousel_viewport.setAutoFillBackground(False)

        for cat_id, tile in all_tiles:
            try:
                tile.setParent(carousel_viewport)
                if not hasattr(tile, 'opacity_effect'):
                    tile.opacity_effect = QGraphicsOpacityEffect()
                    tile.setGraphicsEffect(tile.opacity_effect)
                tile.opacity_effect.setOpacity(0.0)
                tile.hide()
            except RuntimeError:
                continue

        carousel_slots = {
            'center': {'x': 390, 'y': 10, 'width': 320, 'height': 380, 'opacity': 1.0, 'z_order': 10},
            'left':   {'x': 10,  'y': 10, 'width': 320, 'height': 380, 'opacity': 0.7, 'z_order': 5},
            'right':  {'x': 770, 'y': 10, 'width': 320, 'height': 380, 'opacity': 0.7, 'z_order': 5},
            'hidden': {'x': 1200,'y': 10, 'width': 320, 'height': 380, 'opacity': 0.0, 'z_order': 0},
        }

        right_arrow_btn = QPushButton("▶")
        right_arrow_btn.setFixedSize(50, 50)
        right_arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        right_arrow_btn.setStyleSheet(arrow_style)
        right_arrow_btn.clicked.connect(lambda: self.navigate_carousel(1))

        nav_layout.addStretch()
        nav_layout.addWidget(left_arrow_btn)
        nav_layout.addWidget(carousel_viewport)
        nav_layout.addWidget(right_arrow_btn)
        nav_layout.addStretch()
        carousel_layout.addWidget(nav_container)
        view_stack.addWidget(carousel_page)

        # ── List page ───────────────────────────────────────────────────
        list_page = QWidget()
        list_page.setStyleSheet("background-color: transparent;")
        list_page_layout = QVBoxLayout(list_page)
        list_page_layout.setContentsMargins(0, 0, 0, 0)
        list_page_layout.setSpacing(0)

        list_scroll_area = QScrollArea()
        list_scroll_area.setWidgetResizable(True)
        list_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        list_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        list_scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        list_scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 255, 255, 0.05),
                    stop:0.5 rgba(255, 255, 255, 0.15),
                    stop:1 rgba(255, 255, 255, 0.05));
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {team_color},
                    stop:0.5 {self.lighten_color(team_color, 20)},
                    stop:1 {team_color});
                border-radius: 7px;
                min-height: 30px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
            QScrollBar::handle:vertical:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.lighten_color(team_color, 20)},
                    stop:0.5 {self.lighten_color(team_color, 35)},
                    stop:1 {self.lighten_color(team_color, 20)});
                border: 1px solid rgba(255, 255, 255, 0.4);
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {self.lighten_color(team_color, 40)};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        list_container = QWidget()
        list_container.setStyleSheet("background-color: transparent;")
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(20, 6, 20, 20)
        list_container_layout.setSpacing(14)
        list_container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for cat_id, list_item in all_list_items:
            try:
                list_item.setParent(list_container)
                list_item.show()
                list_container_layout.addWidget(list_item)
            except RuntimeError:
                continue

        list_scroll_area.setWidget(list_container)
        list_page_layout.addWidget(list_scroll_area, 1)
        view_stack.addWidget(list_page)

        # ── Position tiles at index 0 (initial warmup render) ───────────
        self.all_category_tiles = all_tiles
        self.carousel_viewport = carousel_viewport
        self.carousel_slots = carousel_slots
        self.current_carousel_index = 0
        self._position_carousel_tiles(animate=False)

        # ── Store page data for instant swap ─────────────────────────────
        self._team_pages[project_type] = {
            'widget':               page,
            'carousel_btn':         carousel_btn,
            'list_btn':             list_btn,
            'back_button':          back_button,
            'carousel_viewport':    carousel_viewport,
            'all_category_tiles':   all_tiles,
            'all_category_list_items': all_list_items,
            'carousel_slots':       carousel_slots,
            'view_stack':           view_stack,
            'left_arrow_btn':       left_arrow_btn,
            'right_arrow_btn':      right_arrow_btn,
        }

    def _position_carousel_tiles(self, animate=False):
        """Position tiles in carousel slots based on current index - prevents drift
        
        This function assigns each tile to a slot (LEFT, CENTER, RIGHT, or HIDDEN)
        based on its distance from the current_carousel_index.
        
        The slot positions are FIXED - they never change.
        Only which tile occupies which slot changes.
        
        This creates a rotating carousel effect where tiles move between
        fixed positions, preventing any drift or accumulation errors.
        """
        if not self.all_category_tiles:
            return
        
        num_tiles = len(self.all_category_tiles)
        
        # Calculate which tiles go in which slots
        # Current tile is always in CENTER
        # Previous tile is in LEFT
        # Next tile is in RIGHT
        # All others are HIDDEN
        
        center_idx = self.current_carousel_index
        left_idx = (center_idx - 1) % num_tiles
        right_idx = (center_idx + 1) % num_tiles
        
        # Prepare animation group if animating
        if animate:
            if hasattr(self, 'carousel_animation_group') and self.carousel_animation_group is not None:
                self.carousel_animation_group.stop()
            self.carousel_animation_group = QParallelAnimationGroup()
        
        # Position each tile in its assigned slot
        for i, (cat_id, tile) in enumerate(self.all_category_tiles):
            # Safety check: skip deleted tiles
            try:
                # Determine which slot this tile should occupy
                if i == center_idx:
                    slot = self.carousel_slots['center']
                elif i == left_idx:
                    slot = self.carousel_slots['left']
                elif i == right_idx:
                    slot = self.carousel_slots['right']
                else:
                    slot = self.carousel_slots['hidden']
                
                # Target position and properties
                target_x = slot['x']
                target_y = slot['y']
                target_width = slot.get('width', 320)
                target_height = slot.get('height', 380)
                target_opacity = slot['opacity']
                z_order = slot['z_order']
                
                # Set z-order for proper layering (center on top)
                if z_order > 7:
                    tile.raise_()
                else:
                    tile.lower()
                
                if animate:
                    # Show tile before animating if it's becoming visible
                    if target_opacity > 0:
                        tile.show()
                    
                    # Animate geometry with scaling (position + size)
                    geom_anim = QPropertyAnimation(tile, b"geometry")
                    geom_anim.setDuration(450)  # Longer for smoother, more seamless transitions
                    geom_anim.setStartValue(tile.geometry())
                    geom_anim.setEndValue(QRect(target_x, target_y, target_width, target_height))
                    geom_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                    self.carousel_animation_group.addAnimation(geom_anim)
                    
                    # Animate opacity
                    opacity_anim = QPropertyAnimation(tile.opacity_effect, b"opacity")
                    opacity_anim.setDuration(450)  # Longer for smoother, more seamless transitions
                    opacity_anim.setStartValue(tile.opacity_effect.opacity())
                    opacity_anim.setEndValue(target_opacity)
                    opacity_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                    self.carousel_animation_group.addAnimation(opacity_anim)
                    
                    # Hide tile after animation if it's becoming hidden
                    if target_opacity == 0:
                        opacity_anim.finished.connect(tile.hide)
                else:
                    tile.setGeometry(QRect(target_x, target_y, target_width, target_height))
                    tile.opacity_effect.setOpacity(target_opacity)
                    
                    # Show/hide based on opacity
                    if target_opacity > 0:
                        tile.show()
                    else:
                        tile.hide()
            except RuntimeError:
                # Tile was deleted, skip it
                continue
        
        # Start animations if animating
        if animate:
            self.carousel_animation_group.start()
    

    def navigate_carousel(self, direction):
        """Navigate carousel left (-1) or right (1)"""
        if not self.all_category_tiles or (hasattr(self, '_animating') and self._animating):
            return
        
        self._animating = True
        num_tiles = len(self.all_category_tiles)
        
        # Update current index
        self.current_carousel_index = (self.current_carousel_index + direction) % num_tiles
        
        # Animate tiles to new positions
        self._position_carousel_tiles(animate=True)

        # Reset animation flag after animation completes
        QTimer.singleShot(470, lambda: setattr(self, '_animating', False))

    def _collapse_cached_category_list_items(self, project_type, except_widget=None):
        list_bucket = self.category_list_cache.get(project_type, {})
        for widget in list_bucket.values():
            if widget is except_widget:
                continue
            try:
                if hasattr(widget, '_collapse'):
                    widget._collapse()
            except RuntimeError:
                continue

    def create_category_list_item(self, project_type, category_id, config):
        """Collapsible accordion row: click the header to reveal description + Start button."""
        team_color, _ = self._tile_colors(project_type)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-left: 5px solid {team_color};
                border-radius: 12px;
            }}
        """)
        frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(16, 0, 16, 0)
        frame_layout.setSpacing(0)

        # ── Always-visible header row ─────────────────────────────────────
        row = QWidget()
        row.setStyleSheet("background-color: transparent; border: none;")
        row.setFixedHeight(80)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 8, 4, 8)
        row_layout.setSpacing(12)

        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "assets", "icons", "category", f"{config['name']}.svg"
        )
        if os.path.exists(icon_path):
            icon_label = QLabel()
            icon_label.setPixmap(QIcon(icon_path).pixmap(QSize(40, 40)))
            icon_label.setFixedSize(48, 48)
            icon_label.setStyleSheet("background-color: transparent; border: none;")
            row_layout.addWidget(icon_label)

        name_label = QLabel(config['name'])
        name_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 19px;
            font-weight: 600;
            font-family: {self.app_font};
            background-color: transparent;
            border: none;
        """)
        row_layout.addWidget(name_label, 1)

        arrow_label = QLabel("▶")
        arrow_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 11px;
            background-color: transparent;
            border: none;
        """)
        row_layout.addWidget(arrow_label)
        frame_layout.addWidget(row)

        # ── Collapsible detail panel ──────────────────────────────────────
        detail_panel = QWidget()
        detail_panel.setStyleSheet("background-color: transparent; border: none;")
        detail_panel.setVisible(False)
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(4, 4, 4, 16)
        detail_layout.setSpacing(14)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255,255,255,0.15); border: none; max-height: 1px;")
        detail_layout.addWidget(sep)

        desc_label = QLabel(config['description'])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 16px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
            border: none;
        """)
        detail_layout.addWidget(desc_label)

        btn_color = self.lighten_color(team_color, 25)
        start_btn = QPushButton("Start Investigation")
        start_btn.setObjectName("start_investigation_btn")
        start_btn.setFixedHeight(46)
        start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_btn.setStyleSheet(f"""
            QPushButton#start_investigation_btn {{
                background-color: {btn_color};
                color: {self.colors['text_white']};
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                font-family: {self.app_font};
                padding: 0px 20px;
                text-align: center;
            }}
            QPushButton#start_investigation_btn:hover {{
                background-color: {self.lighten_color(team_color, 35)};
            }}
            QPushButton#start_investigation_btn:pressed {{
                background-color: {team_color};
            }}
        """)
        start_btn.clicked.connect(lambda: self.start_project(project_type, category_id))
        detail_layout.addWidget(start_btn)

        frame_layout.addWidget(detail_panel)

        # ── Toggle expand/collapse on row click ───────────────────────────
        def _toggle(event=None):
            expanded = detail_panel.isVisible()
            if expanded:
                _collapse()
                return

            self._collapse_cached_category_list_items(project_type, except_widget=frame)
            detail_panel.setVisible(True)
            arrow_label.setText("▼")

        def _collapse():
            detail_panel.setVisible(False)
            arrow_label.setText("▶")

        row.mousePressEvent = _toggle
        frame._collapse = _collapse
        return frame

    def create_category_tile(self, project_type, category_id, config):
        """Create a tile for category selection - using proven working bubble pattern"""
        tile_color, tile_gradient = self._tile_colors(project_type)

        tile = GradientFrame(tile_color, tile_gradient)
        # Fixed size to ensure consistency across all teams in carousel
        tile.setMinimumWidth(320)
        tile.setMaximumWidth(320)
        tile.setMinimumHeight(380)
        tile.setMaximumHeight(380)
        tile.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Shadow - using proven working settings from project type screen
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        tile.setGraphicsEffect(shadow)
        
        # Glass effect styling - matching working bubbles
        tile.setStyleSheet("border-radius: 16px;")

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(32, 32, 32, 32)  # Consistent padding like working bubbles
        layout.setSpacing(0)  # Manual spacing control

        # SVG Icon - centered at the top
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons", "category", f"{config['name']}.svg")
        if os.path.exists(icon_path):
            icon_size = 90

            icon_widget = QLabel()
            icon_widget.setFixedSize(120, 120)
            icon_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_widget.setStyleSheet("background-color: transparent; border: none;")

            icon_pixmap = self._render_icon_pixmap(icon_path, icon_size=icon_size, padding=10)
            if not icon_pixmap.isNull():
                icon_widget.setPixmap(icon_pixmap)

            # Center the icon
            icon_container = QWidget()
            icon_container.setStyleSheet("background-color: transparent;")
            icon_layout = QHBoxLayout(icon_container)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon_layout.addStretch()
            icon_layout.addWidget(icon_widget)
            icon_layout.addStretch()
            layout.addWidget(icon_container)
            layout.addSpacing(16)

        # Title - at the top (matching working pattern)
        title_label = QLabel(config['name'])
        title_label.setWordWrap(True)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 24px;
            font-weight: 600;
            font-family: {self.app_font};
            background-color: transparent;
        """)
        layout.addWidget(title_label)
        layout.addSpacing(18)  # Controlled spacing

        # Description - centered content
        desc_label = QLabel(config['description'])
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"""
            color: {self.colors['text_light_gray']};
            font-size: 16px;
            font-weight: 400;
            font-family: {self.app_font};
            line-height: 1.6;
            background-color: transparent;
        """)
        layout.addWidget(desc_label)
        
        # Push button to bottom - matching working pattern
        layout.addStretch()
        layout.addSpacing(24)  # Space before button
        
        button = QPushButton("Start Investigation")
        button.setObjectName("start_investigation_btn")
        button.setFixedHeight(46)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button_color = self.lighten_color(tile_color, 30)
        button_hover = self.lighten_color(tile_color, 40)
        
        button.setStyleSheet(f"""
            QPushButton#start_investigation_btn {{
                background-color: {button_color};
                color: {self.colors['text_white']};
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                font-family: {self.app_font};
                padding: 0px 20px;
                text-align: center;
            }}
            QPushButton#start_investigation_btn:hover {{
                background-color: {button_hover};
            }}
            QPushButton#start_investigation_btn:pressed {{
                background-color: {tile_color};
            }}
        """)
        button.clicked.connect(lambda: self.start_project(project_type, category_id))
        
        layout.addWidget(button)

        return tile

    def _render_icon_pixmap(self, icon_path: str, icon_size: int = 90, padding: int = 10) -> QPixmap:
        """Render SVG/bitmap icon in a safe canvas to avoid edge clipping."""
        canvas_size = icon_size + (padding * 2)
        pixmap = QPixmap(canvas_size, canvas_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        if icon_path.lower().endswith('.svg'):
            renderer = QSvgRenderer(icon_path)
            if renderer.isValid():
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                renderer.render(painter, QRectF(padding, padding, icon_size, icon_size))
                painter.end()
                return pixmap

        fallback = QPixmap(icon_path)
        if fallback.isNull():
            return QPixmap()

        fitted = fallback.scaled(
            icon_size,
            icon_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x = (canvas_size - fitted.width()) // 2
        y = (canvas_size - fitted.height()) // 2
        painter.drawPixmap(x, y, fitted)
        painter.end()
        return pixmap

    def cleanup_carousel_state(self):
        """Stop any running carousel animation before navigating away."""
        if hasattr(self, 'carousel_animation_group') and self.carousel_animation_group:
            self.carousel_animation_group.stop()
            self.carousel_animation_group = None
        if hasattr(self, '_animating'):
            self._animating = False
    
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
        # Change gradient overlay color based on project type with smooth animation
        if project_type == "redteam":
            self.gradient_overlay.set_gradient_color(self.colors['red_team_tile'], animated=True)
        elif project_type == "blueteam":
            self.gradient_overlay.set_gradient_color(self.colors['blue_team_tile'], animated=True)
        else:
            self.gradient_overlay.set_gradient_color('#923A5F', animated=True)  # Purple for clean
        
        self.update_category_screen(project_type)
        self.stacked_widget.setCurrentIndex(self.SCREEN_CATEGORY)

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
        footer.setFixedHeight(36)
        footer.setStyleSheet("background-color: transparent; border: none;")

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(40, 8, 40, 8)

        copyright_label = QLabel("© 2026 Reinvicta Technologies")
        copyright_label.setStyleSheet(f"""
            color: {self.colors['text_white']};
            font-size: 12px;
            font-weight: 400;
            font-family: {self.app_font};
            background-color: transparent;
        """)

        layout.addWidget(copyright_label)
        layout.addStretch()

        return footer

    def _update_company_logo_position(self):
        if not hasattr(self, 'company_corner_logo') or self.company_corner_logo is None:
            return
        margin_right = 40
        margin_bottom = 8
        x = max(0, self.width() - self.company_corner_logo.width() - margin_right)
        y = max(0, self.height() - self.company_corner_logo.height() - margin_bottom)
        self.company_corner_logo.move(x, y)

    def _update_company_logo_visibility(self, screen_index):
        if not hasattr(self, 'company_corner_logo') or self.company_corner_logo is None:
            return
        # Hide on category screen so carousel bubbles stay unobstructed.
        self.company_corner_logo.setVisible(screen_index != self.SCREEN_CATEGORY)

    def _tile_colors(self, project_type):
        """Return (tile_color, tile_gradient) for the given project type."""
        if project_type == "redteam":
            return self.colors['red_team_tile'], self.colors['red_team_gradient']
        if project_type == "blueteam":
            return self.colors['blue_team_tile'], self.colors['blue_team_gradient']
        return self.colors['tile_bg'], self.colors['tile_gradient_end']

    def _make_back_button(self):
        """Create the standard ← Back button used on all sub-screens."""
        btn = QPushButton("← Back")
        btn.setFixedSize(120, 45)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: {self.colors['text_white']};
                border: 2px solid {self.colors['text_white']};
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
                font-family: {self.app_font};
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
                border-color: {self.colors['text_white']};
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """)
        return btn

    def handle_back_navigation(self):
        """Handle back button clicks based on current screen"""
        current_index = self.stacked_widget.currentIndex()
        if current_index == self.SCREEN_PROJECT_TYPE:
            self.gradient_overlay.set_gradient_color('#923A5F', animated=True)  # Reset to purple with animation
            self.stacked_widget.setCurrentIndex(self.SCREEN_WELCOME)
        elif current_index == self.SCREEN_CATEGORY:
            # Clean up carousel state when leaving category screen
            self.cleanup_carousel_state()
            self.gradient_overlay.set_gradient_color('#923A5F', animated=True)  # Reset to purple with animation
            self.stacked_widget.setCurrentIndex(self.SCREEN_PROJECT_TYPE)
        elif current_index == self.SCREEN_POPUP:
            self.gradient_overlay.set_gradient_color('#923A5F', animated=True)
            self.stacked_widget.setCurrentIndex(self.SCREEN_WELCOME)

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

    # ----- Color Utilities -----
    def lighten_color(self, hex_color, amount=20):
        """Lighten a hex color."""
        return lighten_color(hex_color, amount)

    def darken_color(self, hex_color, amount=20):
        """Darken a hex color."""
        return darken_color(hex_color, amount)

    # ----- Action Handlers -----
    def start_new_project(self):
        """Navigate to project type selection"""
        self.stacked_widget.setCurrentIndex(self.SCREEN_PROJECT_TYPE)

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
        """Open the BeatBox category picker and launch the sandbox."""
        from features.sandbox.ui.sandbox_category_dialog import SandboxCategoryDialog

        category_dialog = SandboxCategoryDialog(self)
        if category_dialog.exec() != category_dialog.DialogCode.Accepted:
            return

        selected_category = category_dialog.selected_category
        if not selected_category:
            return

        category_names = {
            "operating_systems": "Operating Systems",
            "network_devices": "Network Devices",
            "web_technologies": "Web Technologies",
        }

        template_data = {
            "project_type": "sandbox",
            "category": selected_category,
            "template": f"sandbox_{selected_category}",
            "metadata": {
                "title": f"BeatBox - {category_names.get(selected_category, selected_category.replace('_', ' ').title())}",
                "created": "",
                "template": f"sandbox_{selected_category}",
            }
        }

        self.project_selected.emit("sandbox", selected_category, json.dumps(template_data))
        self.close()

    def show_popup_stuff_menu(self):
        """Navigate to the Pop Up Stuff submenu (UI-only section)"""
        self.gradient_overlay.set_gradient_color(self.colors['popup_tile'], animated=True)
        self.stacked_widget.setCurrentIndex(self.SCREEN_POPUP)

    def open_beatnote_window(self):
        """Launch the dedicated BeatNote main window."""
        self.hide()
        BeatNoteMainWindow.launch(parent=None, on_back_to_welcome=self._return_from_beatnote)

    def _return_from_beatnote(self):
        self.showMaximized()
        self.raise_()
        self.activateWindow()

    def open_contact_email(self):
        """Open the default mail client for BeatRooter contact."""
        contact_url = QUrl("mailto:contact@reinvicta.tech?subject=BeatRooter%20Contact")
        QDesktopServices.openUrl(contact_url)

    def open_github(self):
        """Open the GitHub repository in the default browser"""
        github_url = "https://github.com/AntiXerox/BeatRooter"
        QDesktopServices.openUrl(QUrl(github_url))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'gradient_overlay'):
            self.gradient_overlay.setGeometry(0, 0, self.width(), self.height())
            self.gradient_overlay.lower()
        self._update_company_logo_position()
        self._apply_responsive_header_sizes()
