"""
Test PageStudioApp window instantiation, layout architecture, toolbar controls,
palette categorization, theme selector, relative mode toggle, and menus.
"""

import unittest
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

from pagestudio.ui.app_window import PageStudioApp
from pagestudio.ui.palette import PALETTE_SECTIONS
from pagestudio.core.models import WidgetInstance, WIDGET_CATALOG


class TestAppWindow(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = PageStudioApp(self.root)

    def tearDown(self):
        self.root.destroy()

    def test_app_window_initialization(self):
        """Verify PageStudioApp initializes all panels, menus, and widgets without error."""
        self.assertIsNotNone(self.app.palette)
        self.assertIsNotNone(self.app.widget_tree)
        self.assertIsNotNone(self.app.canvas)
        self.assertIsNotNone(self.app.inspector)
        self.assertIsNotNone(self.app.preview_panel)
        self.assertEqual(self.app.state.title, "My Application")

    def test_rearchitected_paned_layout(self):
        """Verify left pane has Palette and WidgetTree, center has Canvas and Preview, right has Inspector."""
        self.assertIsInstance(self.app.h_paned, ttk.PanedWindow)
        self.assertIsInstance(self.app.left_paned, ttk.PanedWindow)
        self.assertIsInstance(self.app.center_paned, ttk.PanedWindow)

        # Left pane contains palette and widget_tree
        left_panes = self.app.left_paned.panes()
        self.assertIn(str(self.app.palette), left_panes)
        self.assertIn(str(self.app.widget_tree), left_panes)

        # Center pane contains canvas and preview
        center_panes = self.app.center_paned.panes()
        self.assertIn(str(self.app.canvas), center_panes)
        self.assertIn(str(self.app.preview_panel), center_panes)

    def test_palette_categories_and_all_42_widgets(self):
        """Verify widget palette categorizes all 42 catalog widgets."""
        # Check all 5 categories are in palette
        for sec in [
            "Basic Controls", "Themed Controls", "Containers & Windows",
            "Data & Choices", "Scrolled & Advanced"
        ]:
            self.assertIn(sec, PALETTE_SECTIONS)
            self.assertIn(sec, self.app.palette.section_frames)

        # Check all 42 widgets in catalog have a button
        self.assertEqual(len(self.app.palette.buttons), len(WIDGET_CATALOG))
        for wname in WIDGET_CATALOG:
            self.assertIn(wname, self.app.palette.buttons)

    def test_palette_search_filter(self):
        """Verify typing in palette search filters widget buttons."""
        palette = self.app.palette
        palette.filter_var.set("button")
        self.root.update_idletasks()

        # Matching buttons (Button, Checkbutton, Radiobutton, TButton, etc.) must be mapped
        self.assertTrue(palette.buttons["Button"].winfo_ismapped())
        self.assertTrue(palette.buttons["TButton"].winfo_ismapped())

        # Non-matching (Entry, Canvas, Treeview) must be hidden
        self.assertFalse(palette.buttons["Entry"].winfo_ismapped())
        self.assertFalse(palette.buttons["Canvas"].winfo_ismapped())

        # Clear button restores visibility
        palette.clear_btn.invoke()
        self.root.update_idletasks()
        self.assertEqual(palette.filter_var.get(), "")
        self.assertTrue(palette.buttons["Entry"].winfo_ismapped())

    def test_theme_selector_dropdown(self):
        """Verify theme selector dropdown changes the active ttk theme."""
        themes = self.app.theme_combo["values"]
        self.assertGreater(len(themes), 0)

        # Select a theme
        target_theme = themes[0]
        self.app.theme_var.set(target_theme)
        self.app._on_theme_changed()
        self.assertEqual(self.app.style.theme_use(), target_theme)

    def test_relative_mode_toggle(self):
        """Verify toggling relative mode in toolbar updates ProjectState."""
        self.assertFalse(self.app.state.is_relative_mode)

        # Toggle on
        self.app.relative_mode_var.set(True)
        self.app._on_relative_toggle()
        self.assertTrue(self.app.state.is_relative_mode)

        # Toggle off
        self.app.relative_mode_var.set(False)
        self.app._on_relative_toggle()
        self.assertFalse(self.app.state.is_relative_mode)

    def test_window_toggle_widget_tree_and_reset_layout(self):
        """Verify toggling widget tree hides and shows the tree pane."""
        self.assertTrue(self.app._widget_tree_visible)

        # Toggle hide
        self.app.toggle_widget_tree()
        self.assertFalse(self.app._widget_tree_visible)
        self.assertNotIn(str(self.app.widget_tree), self.app.left_paned.panes())

        # Toggle show
        self.app.toggle_widget_tree()
        self.assertTrue(self.app._widget_tree_visible)
        self.assertIn(str(self.app.widget_tree), self.app.left_paned.panes())

        # Hide again and test reset_layout
        self.app.toggle_widget_tree()
        self.assertFalse(self.app._widget_tree_visible)
        self.app.reset_layout()
        self.assertTrue(self.app._widget_tree_visible)
        self.assertIn(str(self.app.widget_tree), self.app.left_paned.panes())

    def test_edit_actions_cut_copy_paste_duplicate_delete(self):
        """Verify toolbar/menu edit actions work on selected widgets."""
        btn = WidgetInstance.create("Button", 50, 50, name_hint="edit_btn")
        self.app.state.add_widget(btn)
        self.app.state.select_widget(btn.id)

        # Duplicate
        self.app.duplicate()
        self.assertEqual(len(self.app.state.widgets), 2)

        # Copy
        self.app.copy()
        self.assertGreater(len(self.app.state._clipboard), 0)

        # Paste
        self.app.paste()
        self.assertEqual(len(self.app.state.widgets), 3)

        # Cut
        self.app.cut()
        self.assertEqual(len(self.app.state.widgets), 2)

        # Delete
        self.app.state.select_widget(self.app.state.widget_order[0])
        self.app.delete_selected()
        self.assertEqual(len(self.app.state.widgets), 1)

    @patch("pagestudio.ui.app_window.simpledialog.askstring")
    @patch("pagestudio.ui.app_window.filedialog.askdirectory")
    @patch("pagestudio.ui.app_window.CodeGenerator.generate_all")
    @patch("pagestudio.ui.app_window.messagebox.showinfo")
    def test_export_python_code_prompt(self, mock_info, mock_gen, mock_dir, mock_ask):
        """Verify export_python_code prompts for application base name."""
        mock_ask.return_value = "custom_app"
        mock_dir.return_value = "/tmp/export"
        mock_gen.return_value = ("/tmp/export/custom_app.py", "/tmp/export/custom_app_support.py")

        self.app.export_python_code()

        mock_ask.assert_called_once_with("Export Python", "Enter application base name:", initialvalue="app")
        mock_dir.assert_called_once()
        mock_gen.assert_called_once_with(self.app.state, "custom_app", "/tmp/export")
        mock_info.assert_called_once()


if __name__ == "__main__":
    unittest.main()
