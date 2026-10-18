"""UI components for PageStudio."""
from .app_window import PageStudioApp
from .canvas import DesignCanvas
from .palette import WidgetPalette
from .inspector import PropertyInspector
from .preview import CodePreviewPanel
from .widget_tree import WidgetTree
from .menu_editor import MenuEditorDialog, MenuItemSpec, MenuBarSpec
from .notebook_editor import NotebookTabEditorDialog
from .treeview_editor import TreeviewColumnEditorDialog
from .font_chooser import FontChooserDialog

__all__ = [
    "PageStudioApp",
    "DesignCanvas",
    "WidgetPalette",
    "PropertyInspector",
    "CodePreviewPanel",
    "WidgetTree",
    "MenuEditorDialog",
    "MenuItemSpec",
    "MenuBarSpec",
    "NotebookTabEditorDialog",
    "TreeviewColumnEditorDialog",
    "FontChooserDialog",
]
