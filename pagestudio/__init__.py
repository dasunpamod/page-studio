"""
PageStudio - Modern, Cross-Platform Visual GUI Generator for Python Tkinter.
Supports macOS, Windows, and Linux natively with zero third-party dependencies required.
"""

from .ui.app_window import PageStudioApp
from .core.models import WidgetInstance, WIDGET_CATALOG
from .core.state import ProjectState

__version__ = "1.0.0"

__all__ = [
    "PageStudioApp",
    "ProjectState",
    "WidgetInstance",
    "WIDGET_CATALOG",
    "__version__",
]
