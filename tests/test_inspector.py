"""
Unit Tests for PageStudio PropertyInspector Component.
Verifies all 6 collapsible sections:
1. Identification
2. Geometry (Absolute vs Relative, Anchor, Lock, Fill)
3. Appearance (Color fields, relief, borderwidth, cursor)
4. Text & Typography (text, textvariable, font, justify, anchor, wraplength, underline)
5. Behavior & Bindings (state, takefocus, command, variable, value, show)
6. Widget-Specific Editors (Menu, Notebook tabs, Treeview columns, Values, From/To, Orient)
"""

import unittest
import tkinter as tk
from pagestudio.core.models import WidgetInstance
from pagestudio.core.state import ProjectState
from pagestudio.ui.inspector import PropertyInspector


class TestPropertyInspector(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState("Test App", 700, 500)
        self.inspector = PropertyInspector(self.root, self.state)
        self.inspector.pack()
        self.root.update_idletasks()

    def tearDown(self):
        self.inspector.destroy()
        self.root.destroy()

    def test_window_settings_when_no_selection(self):
        """Inspector renders window settings when no widget is selected."""
        self.assertIsNone(self.state.get_selected_widget())
        self.assertEqual(self.inspector.header_label.cget("text"), "WINDOW SETTINGS")

        # Test changing window title
        self.inspector._on_window_title_change("New Window Title")
        self.assertEqual(self.state.title, "New Window Title")

        # Test changing window dimensions
        self.inspector._on_window_width_change("850")
        self.assertEqual(self.state.width, 850)
        self.inspector._on_window_height_change("650")
        self.assertEqual(self.state.height, 650)

        # Test changing grid settings
        self.inspector._on_snap_grid_change(False)
        self.assertFalse(self.state.snap_to_grid)
        self.inspector._on_grid_size_change("25")
        self.assertEqual(self.state.grid_size, 25)

    def test_collapsible_sections_structure(self):
        """Selecting a widget renders all 6 collapsible sections with toggles."""
        btn = WidgetInstance.create("Button", 30, 40, name_hint="my_button")
        self.state.add_widget(btn)
        self.root.update_idletasks()

        self.assertIn("PROPERTIES: BUTTON", self.inspector.header_label.cget("text"))

        # Verify all 6 section keys exist in dictionary
        required_sections = ["identification", "geometry", "appearance", "text", "behavior", "specific"]
        for sec in required_sections:
            self.assertIn(sec, self.inspector.section_expanded)
            self.assertTrue(self.inspector.section_expanded[sec])

    def test_section_identification(self):
        """Test identification fields: name (spaces to underscores), class, type, parent container."""
        frame = WidgetInstance.create("Frame", 10, 10, name_hint="container_frame")
        self.state.add_widget(frame)

        btn = WidgetInstance.create("Button", 20, 20, name_hint="sample_btn")
        self.state.add_widget(btn)
        self.root.update_idletasks()

        # Name change with auto underscore replacement
        self.inspector._on_widget_name_change(btn, "my awesome button")
        self.assertEqual(btn.name, "my_awesome_button")

        # Set parent container
        btn.parent_id = frame.id
        self.state.push_state()
        self.assertEqual(btn.parent_id, frame.id)

    def test_section_geometry(self):
        """Test absolute vs relative mode, coordinates, anchor, locking, and fill container."""
        btn = WidgetInstance.create("Button", 50, 60, name_hint="geo_btn")
        self.state.add_widget(btn)
        self.root.update_idletasks()

        # Absolute coordinates
        self.inspector._on_geom_change(btn, "x", "120")
        self.inspector._on_geom_change(btn, "y", "90")
        self.inspector._on_geom_change(btn, "width", "140")
        self.inspector._on_geom_change(btn, "height", "45")
        self.assertEqual(btn.x, 120)
        self.assertEqual(btn.y, 90)
        self.assertEqual(btn.width, 140)
        self.assertEqual(btn.height, 45)

        # Mode toggle to relative
        self.inspector._set_geometry_mode(btn, True)
        self.assertTrue(btn.is_relative)
        self.assertIsNotNone(btn.rel_x)
        self.assertIsNotNone(btn.rel_y)

        # Edit relative coordinates
        self.inspector._on_rel_geom_change(btn, "rel_x", "0.25")
        self.inspector._on_rel_geom_change(btn, "rel_y", "0.15")
        self.assertEqual(btn.rel_x, 0.25)
        self.assertEqual(btn.rel_y, 0.15)

        # Anchor
        self.inspector._on_prop_change(btn, "anchor", "center")
        self.assertEqual(btn.properties["anchor"], "center")

        # Toggle Lock
        self.assertFalse(btn.locked)
        btn.locked = True
        self.state.push_state()
        self.assertTrue(btn.locked)

        # Fill Container
        btn.locked = False
        self.state.fill_parent_container(btn.id)
        self.assertEqual(btn.x, 0)
        self.assertEqual(btn.y, 0)
        self.assertEqual(btn.width, self.state.width)
        self.assertEqual(btn.height, self.state.height)

    def test_section_appearance(self):
        """Test appearance colors, relief, borderwidth, and cursor."""
        btn = WidgetInstance.create("Button", 20, 20, name_hint="app_btn")
        self.state.add_widget(btn)

        self.inspector._on_color_prop_change(btn, "bg", "#ff00aa")
        self.inspector._on_color_prop_change(btn, "fg", "#00ff55")
        self.inspector._on_prop_change(btn, "relief", "raised")
        self.inspector._on_prop_change(btn, "borderwidth", 3)
        self.inspector._on_prop_change(btn, "cursor", "hand2")

        self.assertEqual(btn.properties["bg"], "#ff00aa")
        self.assertEqual(btn.properties["fg"], "#00ff55")
        self.assertEqual(btn.properties["relief"], "raised")
        self.assertEqual(btn.properties["borderwidth"], 3)
        self.assertEqual(btn.properties["cursor"], "hand2")

    def test_section_text_and_typography(self):
        """Test text, textvariable, font, justify, anchor, wraplength, underline."""
        lbl = WidgetInstance.create("Label", 10, 10, name_hint="test_lbl")
        self.state.add_widget(lbl)

        self.inspector._on_prop_change(lbl, "text", "Hello World")
        self.inspector._on_prop_change(lbl, "textvariable", "custom_txt_var")
        self.inspector._on_prop_change(lbl, "font", "{Arial} 14 bold")
        self.inspector._on_prop_change(lbl, "justify", "center")
        self.inspector._on_prop_change(lbl, "text_anchor", "e")
        self.inspector._on_prop_change(lbl, "wraplength", 200)
        self.inspector._on_prop_change(lbl, "underline", 1)

        self.assertEqual(lbl.properties["text"], "Hello World")
        self.assertEqual(lbl.properties["textvariable"], "custom_txt_var")
        self.assertEqual(lbl.properties["font"], "{Arial} 14 bold")
        self.assertEqual(lbl.properties["justify"], "center")
        self.assertEqual(lbl.properties["text_anchor"], "e")
        self.assertEqual(lbl.properties["wraplength"], 200)
        self.assertEqual(lbl.properties["underline"], 1)

    def test_section_behavior_and_bindings(self):
        """Test state, takefocus, command, variable, value, show."""
        entry = WidgetInstance.create("Entry", 10, 10, name_hint="pwd_entry")
        self.state.add_widget(entry)

        self.inspector._on_prop_change(entry, "state", "disabled")
        self.inspector._on_prop_change(entry, "takefocus", False)
        self.inspector._on_event_change(entry, "command", "on_submit_action")
        self.inspector._on_prop_change(entry, "variable", "pwd_var")
        self.inspector._on_prop_change(entry, "value", "secret_val")
        self.inspector._on_prop_change(entry, "show", "*")

        self.assertEqual(entry.properties["state"], "disabled")
        self.assertFalse(entry.properties["takefocus"])
        self.assertEqual(entry.events["command"], "on_submit_action")
        self.assertEqual(entry.properties["variable"], "pwd_var")
        self.assertEqual(entry.properties["value"], "secret_val")
        self.assertEqual(entry.properties["show"], "*")

    def test_section_widget_specific_editors(self):
        """Test widget-specific editors for notebook, treeview, combobox, and scales."""
        # Combobox values
        combo = WidgetInstance.create("Combobox", 10, 10, name_hint="my_cb")
        self.state.add_widget(combo)
        self.inspector._on_prop_change(combo, "values", ["Apple", "Banana", "Cherry"])
        self.assertEqual(combo.properties["values"], ["Apple", "Banana", "Cherry"])

        # Scale From / To / Orient
        scale = WidgetInstance.create("Scale", 10, 50, name_hint="my_sc")
        self.state.add_widget(scale)
        self.inspector._on_prop_change(scale, "from_", 10)
        self.inspector._on_prop_change(scale, "to", 200)
        self.inspector._on_prop_change(scale, "orient", "vertical")
        self.assertEqual(scale.properties["from_"], 10)
        self.assertEqual(scale.properties["to"], 200)
        self.assertEqual(scale.properties["orient"], "vertical")

        # Notebook tabs
        nb = WidgetInstance.create("TNotebook", 10, 100, name_hint="my_nb")
        self.state.add_widget(nb)
        self.inspector._on_prop_change(nb, "tabs", [{"id": "t1", "text": "Tab One"}])
        self.assertEqual(nb.properties["tabs"], [{"id": "t1", "text": "Tab One"}])

        # Treeview columns
        tv = WidgetInstance.create("Treeview", 10, 200, name_hint="my_tv")
        self.state.add_widget(tv)
        self.inspector._on_prop_change(tv, "columns", [{"id": "c1", "heading": "Name"}])
        self.assertEqual(tv.properties["columns"], [{"id": "c1", "heading": "Name"}])


if __name__ == "__main__":
    unittest.main()
