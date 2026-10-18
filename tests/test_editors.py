"""
Unit Tests for PageStudio Visual Dialogs and Editor Components.
Tests WidgetTree, MenuEditorDialog, NotebookTabEditorDialog,
TreeviewColumnEditorDialog, and FontChooserDialog in a virtual Tk environment.
"""

import unittest
import tkinter as tk
from typing import Optional, List, Dict, Any

from pagestudio.core.models import WidgetInstance
from pagestudio.core.state import ProjectState
from pagestudio.ui.widget_tree import WidgetTree
from pagestudio.ui.menu_editor import MenuEditorDialog, MenuItemSpec, MenuBarSpec
from pagestudio.ui.notebook_editor import NotebookTabEditorDialog
from pagestudio.ui.treeview_editor import TreeviewColumnEditorDialog
from pagestudio.ui.font_chooser import FontChooserDialog


class TestWidgetTree(unittest.TestCase):
    """Unit tests for WidgetTree component."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState(title="Test App", width=600, height=400)

        # Add sample hierarchy: Root -> Frame -> Button, and Root -> Entry
        self.frame = WidgetInstance.create("Frame", 10, 10, name_hint="main_frame")
        self.state.add_widget(self.frame)

        self.btn = WidgetInstance.create("Button", 20, 20, name_hint="click_btn")
        self.btn.parent_id = self.frame.id
        self.state.add_widget(self.btn)

        self.ttk_btn = WidgetInstance.create("TButton", 30, 30, name_hint="button_1")
        self.ttk_btn.parent_id = self.frame.id
        self.state.add_widget(self.ttk_btn)

        self.entry = WidgetInstance.create("Entry", 50, 50, name_hint="name_entry")
        self.state.add_widget(self.entry)

        self.tree_comp = WidgetTree(self.root, self.state)
        self.tree_comp.pack()
        self.root.update_idletasks()

    def tearDown(self):
        self.tree_comp.destroy()
        self.root.destroy()

    def test_tree_initialization_and_hierarchy(self):
        """Verify root item and nested child items are correctly populated."""
        self.assertTrue(self.tree_comp.tree.exists("__root__"))
        root_text = self.tree_comp.tree.item("__root__", "text")
        self.assertIn("Toplevel0: root", root_text)

        # Check frame is under root
        self.assertTrue(self.tree_comp.tree.exists(self.frame.id))
        self.assertEqual(self.tree_comp.tree.parent(self.frame.id), "__root__")

        # Check button is nested under frame
        self.assertTrue(self.tree_comp.tree.exists(self.btn.id))
        self.assertEqual(self.tree_comp.tree.parent(self.btn.id), self.frame.id)

        # Check button display label format: DisplayName: name
        btn_text = self.tree_comp.tree.item(self.btn.id, "text")
        self.assertIn("tk.Button: click_btn", btn_text)

        ttk_btn_text = self.tree_comp.tree.item(self.ttk_btn.id, "text")
        self.assertIn("ttk.Button: button_1", ttk_btn_text)

    def test_search_filter(self):
        """Verify filter entry filters tree items matching query."""
        self.tree_comp.filter_var.set("click")
        self.root.update_idletasks()

        # Button matches "click"
        self.assertTrue(self.tree_comp.tree.exists(self.btn.id))
        # Entry doesn't match and has no matching children
        self.assertFalse(self.tree_comp.tree.exists(self.entry.id))

        # Clear filter restores entry
        self.tree_comp.filter_var.set("")
        self.root.update_idletasks()
        self.assertTrue(self.tree_comp.tree.exists(self.entry.id))

    def test_selection_synchronization(self):
        """Verify clicking tree items updates state selection and vice-versa."""
        # Selecting item in treeview
        self.tree_comp.tree.selection_set(self.btn.id)
        self.tree_comp._on_tree_select(None)
        self.assertEqual(self.state.selected_ids, [self.btn.id])

        # Selecting root clears widget selection
        self.tree_comp.tree.selection_set("__root__")
        self.tree_comp._on_tree_select(None)
        self.assertEqual(self.state.selected_ids, [])

        # Selecting in state updates tree selection
        self.state.select_widget(self.entry.id)
        selected_in_tree = self.tree_comp.tree.selection()
        self.assertIn(self.entry.id, selected_in_tree)

    def test_context_menu_actions(self):
        """Verify cut, copy, paste, delete, lock, and fill container actions."""
        self.state.select_widget(self.entry.id)

        # Copy & Paste
        self.tree_comp.copy_selected()
        self.assertIsNotNone(WidgetTree._clipboard)
        initial_count = len(self.state.widgets)
        self.tree_comp.paste()
        self.assertEqual(len(self.state.widgets), initial_count + 1)

        # Toggle Lock
        self.state.select_widget(self.frame.id)
        self.assertFalse(getattr(self.frame, "locked", False))
        self.tree_comp.toggle_lock_selected()
        self.assertTrue(getattr(self.frame, "locked", False))
        # Unlock so we can modify geometry
        self.tree_comp.toggle_lock_selected()
        self.assertFalse(getattr(self.frame, "locked", False))

        # Fill Container
        self.tree_comp.fill_container_selected()
        self.assertEqual(self.frame.x, 0)
        self.assertEqual(self.frame.y, 0)
        self.assertEqual(self.frame.width, self.state.width)
        self.assertEqual(self.frame.height, self.state.height)

        # Delete
        self.tree_comp.delete_selected()
        self.assertNotIn(self.frame.id, self.state.widgets)

    def test_double_click_handlers(self):
        """Verify double clicking triggers appropriate editor callbacks."""
        notebook_widget = WidgetInstance.create("Frame", 0, 0, name_hint="my_nb")
        notebook_widget.widget_type = "Notebook"
        self.state.add_widget(notebook_widget)

        treeview_widget = WidgetInstance.create("Frame", 0, 0, name_hint="my_tv")
        treeview_widget.widget_type = "Treeview"
        self.state.add_widget(treeview_widget)

        callbacks_called = {"menu": False, "notebook": False, "treeview": False}

        self.tree_comp.on_edit_menu = lambda w: callbacks_called.update({"menu": True})
        self.tree_comp.on_edit_notebook = lambda w: callbacks_called.update({"notebook": True})
        self.tree_comp.on_edit_treeview = lambda w: callbacks_called.update({"treeview": True})

        # Mock event
        class DummyEvent:
            x = 10
            y = 10

        # Trigger for notebook
        self.tree_comp.tree.identify_row = lambda y: notebook_widget.id
        self.tree_comp._on_double_click(DummyEvent())
        self.assertTrue(callbacks_called["notebook"])

        # Trigger for treeview
        self.tree_comp.tree.identify_row = lambda y: treeview_widget.id
        self.tree_comp._on_double_click(DummyEvent())
        self.assertTrue(callbacks_called["treeview"])

        # Trigger for root menu
        self.tree_comp.tree.identify_row = lambda y: "__root__"
        self.tree_comp._on_double_click(DummyEvent())
        self.assertTrue(callbacks_called["menu"])


class TestMenuEditorDialog(unittest.TestCase):
    """Unit tests for MenuEditorDialog and MenuBarSpec."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_menu_models_serialization(self):
        """Verify MenuItemSpec and MenuBarSpec serialization and reconstruction."""
        item = MenuItemSpec(
            item_type="command",
            label="Save File",
            command="on_save",
            accelerator="Ctrl+S",
            underline=0
        )
        cascade = MenuItemSpec(
            item_type="cascade",
            label="File",
            children=[item]
        )
        menu_bar = MenuBarSpec(items=[cascade])

        d = menu_bar.to_dict()
        reconstructed = MenuBarSpec.from_dict(d)
        self.assertEqual(len(reconstructed.items), 1)
        self.assertEqual(reconstructed.items[0].label, "File")
        self.assertEqual(len(reconstructed.items[0].children), 1)
        self.assertEqual(reconstructed.items[0].children[0].label, "Save File")
        self.assertEqual(reconstructed.items[0].children[0].accelerator, "Ctrl+S")

    def test_dialog_ui_operations(self):
        """Verify dialog initialization, item modification, adding items, moving, and saving."""
        saved_spec: Optional[MenuBarSpec] = None

        def handle_save(spec: MenuBarSpec):
            nonlocal saved_spec
            saved_spec = spec

        dialog = MenuEditorDialog(self.root, on_save=handle_save, modal=False)
        self.root.update_idletasks()

        # Initial default spec has File and Edit cascades
        self.assertGreaterEqual(len(dialog.spec.items), 2)
        first_item = dialog.spec.items[0]
        self.assertEqual(first_item.label, "File")

        # Select first item and edit label
        dialog.tree.selection_set(first_item.id)
        dialog._on_tree_select(None)
        self.assertEqual(dialog.label_var.get(), "File")

        # Rename label
        dialog.label_var.set("Document")
        dialog._on_prop_edited()
        self.assertEqual(first_item.label, "Document")

        # Add a new separator
        dialog._on_add_separator()
        self.root.update_idletasks()

        # Add a new command item
        new_cmd = dialog._add_new_item("command", "Print")
        self.assertEqual(new_cmd.label, "Print")
        dialog.accel_var.set("Ctrl+P")
        dialog._on_prop_edited()
        self.assertEqual(new_cmd.accelerator, "Ctrl+P")

        # Save dialog
        dialog._on_save_clicked()
        self.assertIsNotNone(saved_spec)
        self.assertEqual(dialog.result, saved_spec)


class TestNotebookTabEditorDialog(unittest.TestCase):
    """Unit tests for NotebookTabEditorDialog."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState()
        self.widget = WidgetInstance.create("Frame", 0, 0, name_hint="test_nb")
        self.widget.widget_type = "Notebook"
        self.widget.properties["tabs"] = [
            {"id": "tab_1", "text": "Overview", "state": "normal"},
            {"id": "tab_2", "text": "Settings", "state": "normal"}
        ]
        self.state.add_widget(self.widget)

    def tearDown(self):
        self.root.destroy()

    def test_notebook_tabs_management(self):
        """Verify adding, renaming, moving, and saving tabs."""
        saved_tabs: Optional[List[Dict[str, Any]]] = None

        def on_save(tabs):
            nonlocal saved_tabs
            saved_tabs = tabs

        dialog = NotebookTabEditorDialog(
            self.root,
            widget=self.widget,
            state=self.state,
            on_save=on_save,
            modal=False
        )
        self.root.update_idletasks()

        self.assertEqual(len(dialog.tabs), 2)
        # Select tab 0
        dialog.tree.selection_set("0")
        dialog._on_tab_selected(None)
        self.assertEqual(dialog.text_var.get(), "Overview")

        # Rename tab
        dialog.text_var.set("Dashboard")
        dialog._on_field_changed()
        self.assertEqual(dialog.tabs[0]["text"], "Dashboard")

        # Add a tab
        dialog._on_add_tab()
        self.assertEqual(len(dialog.tabs), 3)

        # Move tab up
        dialog.selected_index = 2
        dialog._on_move_up()
        self.assertEqual(dialog.selected_index, 1)

        # Save tabs
        dialog._on_save_clicked()
        self.assertIsNotNone(saved_tabs)
        self.assertEqual(len(self.widget.properties["tabs"]), 3)
        self.assertEqual(self.widget.properties["tabs"][0]["text"], "Dashboard")


class TestTreeviewColumnEditorDialog(unittest.TestCase):
    """Unit tests for TreeviewColumnEditorDialog."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState()
        self.widget = WidgetInstance.create("Frame", 0, 0, name_hint="test_tv")
        self.widget.widget_type = "Treeview"
        self.widget.properties["columns"] = [
            {"id": "col1", "heading": "First Name", "width": 100, "anchor": "w", "stretch": True},
            {"id": "col2", "heading": "Last Name", "width": 120, "anchor": "w", "stretch": True}
        ]
        self.state.add_widget(self.widget)

    def tearDown(self):
        self.root.destroy()

    def test_treeview_column_management(self):
        """Verify adding, editing, moving, and saving treeview columns."""
        saved_cols: Optional[List[Dict[str, Any]]] = None

        def on_save(cols):
            nonlocal saved_cols
            saved_cols = cols

        dialog = TreeviewColumnEditorDialog(
            self.root,
            widget=self.widget,
            state=self.state,
            on_save=on_save,
            modal=False
        )
        self.root.update_idletasks()

        self.assertEqual(len(dialog.columns), 2)
        # Select column 1
        dialog.tree.selection_set("0")
        dialog._on_column_selected(None)
        self.assertEqual(dialog.heading_var.get(), "First Name")

        # Modify heading and width
        dialog.heading_var.set("Given Name")
        dialog.width_var.set("180")
        dialog.anchor_var.set("center")
        dialog._on_field_changed()

        self.assertEqual(dialog.columns[0]["heading"], "Given Name")
        self.assertEqual(dialog.columns[0]["width"], 180)
        self.assertEqual(dialog.columns[0]["anchor"], "center")

        # Add column
        dialog._on_add_column()
        self.assertEqual(len(dialog.columns), 3)

        # Remove column
        dialog.selected_index = 2
        dialog._on_remove_column()
        self.assertEqual(len(dialog.columns), 2)

        # Save
        dialog._on_save_clicked()
        self.assertIsNotNone(saved_cols)
        self.assertEqual(self.widget.properties["columns"][0]["heading"], "Given Name")


class TestFontChooserDialog(unittest.TestCase):
    """Unit tests for FontChooserDialog."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_font_spec_parsing(self):
        """Verify various font spec formats parse correctly."""
        dialog = FontChooserDialog(self.root, initial_font=("Courier", 14, "bold italic"), modal=False)
        self.root.update_idletasks()
        self.assertEqual(dialog.current_family, "Courier")
        self.assertEqual(dialog.current_size, 14)
        self.assertTrue(dialog.bold_var.get())
        self.assertTrue(dialog.italic_var.get())
        self.assertFalse(dialog.underline_var.get())
        dialog.destroy()

    def test_font_selection_and_preview(self):
        """Verify modifying family, size, styles, and saving result."""
        saved_font = None

        def on_save(f):
            nonlocal saved_font
            saved_font = f

        dialog = FontChooserDialog(self.root, initial_font="Arial 12", on_save=on_save, modal=False)
        self.root.update_idletasks()

        # Check font families populated
        self.assertGreater(len(dialog.all_families), 0)

        # Change size
        dialog.size_var.set("16")
        dialog._on_size_entry_changed()
        self.assertEqual(dialog.current_size, 16)

        # Toggle bold
        dialog.bold_var.set(True)
        dialog._update_preview()
        self.assertIsNotNone(dialog.preview_font)

        # Verify font tuple property
        tup = dialog.font_tuple
        self.assertEqual(tup[1], 16)
        self.assertIn("bold", tup[2])

        # Save
        dialog._on_ok_clicked()
        self.assertIsNotNone(saved_font)
        self.assertEqual(saved_font[1], 16)
        self.assertIn("bold", saved_font[2])


if __name__ == "__main__":
    unittest.main()
