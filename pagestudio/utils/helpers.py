"""
PageStudio - Utility Helpers & Cross-Platform Normalization
Handles platform differences (macOS Command key vs Windows/Linux Ctrl, font defaults, coordinate math).
"""

import sys
from typing import Tuple

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
    return max(min_val, min(val, max_val))
