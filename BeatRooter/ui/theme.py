import os

from PyQt6.QtGui import QFontDatabase


_APP_FONT = None


def get_app_font():
    """Return the preferred app font family string for use in Qt stylesheets."""
    global _APP_FONT
    if _APP_FONT is not None:
        return _APP_FONT

    preferred_font = "Inria Sans"
    _APP_FONT = f"'{preferred_font}'"

    candidate_font_paths = [
        os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'assets', 'fonts', 'inria-sans', 'InriaSans', 'TTF'
        ),
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'assets', 'fonts', 'inria-sans', 'InriaSans', 'TTF'
        ),
    ]
    font_files = [
        'InriaSans-Regular.ttf',
        'InriaSans-Bold.ttf',
        'InriaSans-Italic.ttf',
        'InriaSans-BoldItalic.ttf',
        'InriaSans-Light.ttf',
        'InriaSans-LightItalic.ttf',
    ]

    loaded_families = set()
    for font_path in candidate_font_paths:
        if not os.path.isdir(font_path):
            continue
        for font_file in font_files:
            full_path = os.path.join(font_path, font_file)
            if not os.path.exists(full_path):
                continue
            font_id = QFontDatabase.addApplicationFont(full_path)
            if font_id != -1:
                loaded_families.update(QFontDatabase.applicationFontFamilies(font_id))

    if preferred_font not in loaded_families:
        for fallback in ["Inria Sans", "Inter", "Segoe UI", "Roboto", "Arial"]:
            if fallback in QFontDatabase.families():
                _APP_FONT = f"'{fallback}'"
                break

    return _APP_FONT


def get_welcome_palette(**overrides):
    """Shared palette for welcome and selection surfaces."""
    palette = {
        'page_bg': '#141414',
        'tile_bg': '#C8558A',
        'tile_gradient_end': '#A8467A',
        'popup_tile': '#2E7D32',
        'popup_gradient': '#1B5E20',
        'popup_button': '#0E4F1B',
        'red_team_tile': '#D32F2F',
        'red_team_gradient': '#B71C1C',
        'blue_team_tile': '#1976D2',
        'blue_team_gradient': '#1565C0',
        'button_active': '#B3386C',
        'button_disabled': '#2A1820',
        'text_white': '#FFFFFF',
        'text_light_gray': '#E0E0E0',
        'version_badge_bg': '#1A2332',
        'red_rotten': '#FF0000',
        'accent_blue': '#1976D2',
        'accent_clean': '#C8558A',
        'accent_red': '#D32F2F',
        'card_bg': 'rgba(255, 255, 255, 0.07)',
        'card_hover': 'rgba(255, 255, 255, 0.12)',
        'text_primary': '#FFFFFF',
        'text_secondary': '#E0E0E0',
        'text_muted': 'rgba(255, 255, 255, 0.6)',
        'border': 'rgba(255, 255, 255, 0.20)',
    }
    palette.update(overrides)
    return palette


def lighten_color(hex_color, amount=20):
    if not isinstance(hex_color, str) or len(hex_color) != 7 or not hex_color.startswith('#'):
        return hex_color
    try:
        red = min(255, int(hex_color[1:3], 16) + amount)
        green = min(255, int(hex_color[3:5], 16) + amount)
        blue = min(255, int(hex_color[5:7], 16) + amount)
    except ValueError:
        return hex_color
    return f"#{red:02x}{green:02x}{blue:02x}"


def darken_color(hex_color, amount=20):
    if not isinstance(hex_color, str) or len(hex_color) != 7 or not hex_color.startswith('#'):
        return hex_color
    try:
        red = max(0, int(hex_color[1:3], 16) - amount)
        green = max(0, int(hex_color[3:5], 16) - amount)
        blue = max(0, int(hex_color[5:7], 16) - amount)
    except ValueError:
        return hex_color
    return f"#{red:02x}{green:02x}{blue:02x}"


def build_filled_button_qss(font_family, background_color, text_color, *,
                            radius=12, font_size=15, font_weight=600,
                            padding="10px 20px", hover_color=None,
                            pressed_color=None, border="none",
                            extra_base=""):
    hover_color = hover_color or lighten_color(background_color, 15)
    pressed_color = pressed_color or darken_color(background_color, 15)
    extra_base_line = f"\n                    {extra_base.strip()}" if extra_base.strip() else ""
    return f"""
            QPushButton {{
                background-color: {background_color};
                color: {text_color};
                border: {border};
                border-radius: {radius}px;
                font-size: {font_size}px;
                font-weight: {font_weight};
                font-family: {font_family};
                padding: {padding};{extra_base_line}
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """


def build_disabled_button_qss(font_family, background_color, text_color, *,
                              radius=12, font_size=15, font_weight=600,
                              padding="10px 20px", border="none",
                              extra_base=""):
    extra_base_line = f"\n                    {extra_base.strip()}" if extra_base.strip() else ""
    return f"""
            QPushButton {{
                background-color: {background_color};
                color: {text_color};
                border: {border};
                border-radius: {radius}px;
                font-size: {font_size}px;
                font-weight: {font_weight};
                font-family: {font_family};
                padding: {padding};{extra_base_line}
            }}
        """