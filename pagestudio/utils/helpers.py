"""
PageStudio - Utility Helpers & Cross-Platform Normalization
Handles platform differences (macOS Command key vs Windows/Linux Ctrl, font defaults, coordinate math).
"""

import sys

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

# Primary modifier key display and event binding
MOD_KEY = "Command" if IS_MAC else "Control"
MOD_SYMBOL = "⌘" if IS_MAC else "Ctrl"

def get_platform_shortcut(key: str) -> str:
    """Returns human-readable shortcut string e.g. '⌘S' or 'Ctrl+S'."""
    if IS_MAC:
        return f"{MOD_SYMBOL}{key.upper()}"
    return f"{MOD_SYMBOL}+{key.upper()}"

def point_in_rect(px: int, py: int, rx: int, ry: int, rw: int, rh: int) -> bool:
    """Check if point (px, py) is inside rectangle (rx, ry, rw, rh)."""
    return rx <= px <= rx + rw and ry <= py <= ry + rh

def clamp(val: int, min_val: int, max_val: int) -> int:
    """Clamp integer val to range [min_val, max_val]."""
    return max(min_val, min(val, max_val))


def is_text_editing(root_or_widget, event=None) -> bool:
    """
    Returns True if either the event's source widget or the currently focused
    widget is a text editing control (Entry, Text, Spinbox, Combobox, etc.).
    Guards global delete, backspace, and nudge shortcuts from interfering with text input.
    """
    import tkinter as tk
    from tkinter import ttk

    text_classes = (
        tk.Entry, ttk.Entry,
        tk.Text,
        tk.Spinbox, ttk.Spinbox,
        ttk.Combobox
    )
    # 1. Check event.widget if provided
    if event is not None and hasattr(event, "widget") and event.widget is not None:
        if isinstance(event.widget, text_classes):
            return True
        try:
            w_class = event.widget.winfo_class()
            if w_class in ("Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "Combobox", "TCombobox"):
                return True
        except Exception:
            pass

    # 2. Check currently focused widget
    try:
        focused = None
        if hasattr(root_or_widget, "focus_get"):
            focused = root_or_widget.focus_get()
        elif hasattr(root_or_widget, "winfo_toplevel"):
            top = root_or_widget.winfo_toplevel()
            if hasattr(top, "focus_get"):
                focused = top.focus_get()

        if focused is not None:
            if isinstance(focused, text_classes):
                return True
            try:
                w_class = focused.winfo_class()
                if w_class in ("Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "Combobox", "TCombobox"):
                    return True
            except Exception:
                pass
    except Exception:
        pass

    return False

