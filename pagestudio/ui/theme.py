"""
PageStudio - Modern Theme & Styling Configuration
Defines consistent color palettes, fonts, and ttk styling for the IDE.
"""

import tkinter as tk
from tkinter import ttk
from ..utils.helpers import IS_MAC

# UI Palette Constants
COLOR_BG_DARK = "#1e1e24"
COLOR_BG_PANEL = "#25252d"
COLOR_BG_CANVAS = "#2e2e38"
COLOR_CANVAS_PAPER = "#ffffff"
COLOR_CANVAS_GRID = "#e6e6ea"

COLOR_ACCENT = "#3a86ff"
COLOR_ACCENT_HOVER = "#2670e8"
COLOR_ACCENT_ACTIVE = "#1d5dc4"

COLOR_TEXT_MAIN = "#ffffff"
COLOR_TEXT_MUTED = "#a0a0ab"
COLOR_TEXT_DARK = "#2b2b2b"

COLOR_SELECTION = "#3a86ff"
COLOR_HANDLE_FILL = "#ffffff"
COLOR_HANDLE_OUTLINE = "#3a86ff"

# Fonts
FONT_UI_FAMILY = "Helvetica" if IS_MAC else "Segoe UI"
FONT_CODE_FAMILY = "Menlo" if IS_MAC else "Consolas"

def apply_theme(root: tk.Tk) -> ttk.Style:
    """Applies modern styling to ttk widgets inside the PageStudio IDE."""
    style = ttk.Style(root)
    
    # Try selecting a modern base theme if available
    available_themes = style.theme_names()
    if IS_MAC and "aqua" in available_themes:
        style.theme_use("aqua")
    elif "clam" in available_themes:
        style.theme_use("clam")
        
    return style
