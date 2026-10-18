"""UI components for PageStudio."""
from .app_window import PageStudioApp
from .canvas import DesignCanvas
from .palette import WidgetPalette
from .inspector import PropertyInspector
from .preview import CodePreviewPanel

__all__ = [
    "PageStudioApp",
    "DesignCanvas",
    "WidgetPalette",
    "PropertyInspector",
    "CodePreviewPanel",
]
