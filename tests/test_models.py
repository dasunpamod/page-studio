"""Tests for widget models, menu models, and catalog in PageStudio."""
import unittest
from pagestudio.core.models import WidgetInstance, MenuItemSpec, MenuBarSpec, WIDGET_CATALOG

class TestWidgetModels(unittest.TestCase):

    def test_catalog_completeness(self):
        """Ensure standard widgets exist in catalog."""
        expected = ["Button", "Entry", "Label", "Checkbutton", "Radiobutton", "Combobox", "Progressbar"]
        for name in expected:
            self.assertIn(name, WIDGET_CATALOG)
            spec = WIDGET_CATALOG[name]
            self.assertGreater(spec.default_width, 0)
            self.assertGreater(spec.default_height, 0)

    def test_catalog_all_widget_groups(self):
        """Ensure all required widget categories and types exist with valid configurations."""
        # Standard Tk
        standard_tk = [
            "Button", "Entry", "Label", "Checkbutton", "Radiobutton", "Combobox",
            "Listbox", "Text", "Progressbar", "Scale", "Separator", "Frame",
            "LabelFrame", "Canvas", "Spinbox", "Message", "Menubutton", "Popupmenu", "Toplevel"
        ]
        for wname in standard_tk:
            self.assertIn(wname, WIDGET_CATALOG, f"Missing Standard Tk widget: {wname}")
            self.assertEqual(WIDGET_CATALOG[wname].category, "Standard Tk")

        # Themed ttk
        themed_ttk = [
            "TButton", "TCheckbutton", "TCombobox", "TEntry", "TFrame", "TLabel",
            "TLabelframe", "TMenubutton", "TNotebook", "TPanedwindow", "TProgressbar",
            "TRadiobutton", "TScale", "TSeparator", "TSizegrip", "TSpinbox"
        ]
        for wname in themed_ttk:
            self.assertIn(wname, WIDGET_CATALOG, f"Missing Themed ttk widget: {wname}")
            self.assertEqual(WIDGET_CATALOG[wname].category, "Themed ttk")

        # Scrolled Widgets
        scrolled = [
            "Scrolledtext", "Scrolledlistbox", "Scrolledtreeview", "Scrolledentry", "Scrolledwindow"
        ]
        for wname in scrolled:
            self.assertIn(wname, WIDGET_CATALOG, f"Missing Scrolled widget: {wname}")
            self.assertEqual(WIDGET_CATALOG[wname].category, "Scrolled Widgets")

        # Advanced
        advanced = ["Treeview", "Custom"]
        for wname in advanced:
            self.assertIn(wname, WIDGET_CATALOG, f"Missing Advanced widget: {wname}")
            self.assertEqual(WIDGET_CATALOG[wname].category, "Advanced")

    def test_container_flags(self):
        """Verify is_container is True for containers and False for leaves."""
        containers = ["Frame", "LabelFrame", "TFrame", "TLabelframe", "TNotebook", "TPanedwindow", "Canvas"]
        for cname in containers:
            self.assertIn(cname, WIDGET_CATALOG)
            self.assertTrue(WIDGET_CATALOG[cname].is_container, f"{cname} must have is_container=True")

        leaves = ["Button", "Entry", "TButton", "TEntry", "Label", "TLabel", "Progressbar"]
        for lname in leaves:
            self.assertFalse(WIDGET_CATALOG[lname].is_container, f"{lname} should have is_container=False")

    def test_widget_creation(self):
        """Test instantiating a widget with default properties."""
        w = WidgetInstance.create("Button", 50, 60, name_hint="my_button")
        self.assertEqual(w.widget_type, "Button")
        self.assertEqual(w.name, "my_button")
        self.assertEqual(w.x, 50)
        self.assertEqual(w.y, 60)
        self.assertEqual(w.properties.get("text"), "Button")
        self.assertIn("command", w.events)
        self.assertIsNone(w.parent_id)
        self.assertFalse(w.locked)
        self.assertFalse(w.is_relative)

    def test_widget_with_parent_and_relative(self):
        """Test instantiating a widget with parent_id and relative geometry fields."""
        w = WidgetInstance.create("TButton", 10, 20, parent_id="frame_123")
        self.assertEqual(w.parent_id, "frame_123")
        w.is_relative = True
        w.rel_x = 0.1
        w.rel_y = 0.2
        w.rel_width = 0.8
        w.rel_height = 0.4
        w.locked = True
        w.z_order = 5
        w.container_tab_or_pane = "Tab 1"

        data = w.to_dict()
        w2 = WidgetInstance.from_dict(data)
        self.assertEqual(w2.id, w.id)
        self.assertEqual(w2.parent_id, "frame_123")
        self.assertTrue(w2.is_relative)
        self.assertAlmostEqual(w2.rel_x, 0.1)
        self.assertAlmostEqual(w2.rel_y, 0.2)
        self.assertAlmostEqual(w2.rel_width, 0.8)
        self.assertAlmostEqual(w2.rel_height, 0.4)
        self.assertTrue(w2.locked)
        self.assertEqual(w2.z_order, 5)
        self.assertEqual(w2.container_tab_or_pane, "Tab 1")

    def test_widget_to_and_from_dict_backwards_compat(self):
        """Ensure older project dictionary formats load without error."""
        legacy_data = {
            "id": "old_1",
            "widget_type": "Label",
            "name": "lbl_old",
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 30,
            "properties": {"text": "Legacy"},
            "events": {}
        }
        w = WidgetInstance.from_dict(legacy_data)
        self.assertEqual(w.id, "old_1")
        self.assertIsNone(w.parent_id)
        self.assertFalse(w.is_relative)
        self.assertFalse(w.locked)
        self.assertEqual(w.z_order, 0)
        self.assertIsNone(w.rel_x)

    def test_menu_specs(self):
        """Test MenuItemSpec and MenuBarSpec construction and round-trip serialization."""
        item1 = MenuItemSpec(
            id="item_cut",
            item_type="command",
            label="Cut",
            command="on_cut",
            accelerator="Ctrl+X",
            underline=2
        )
        item2 = MenuItemSpec(
            id="item_sep",
            item_type="separator"
        )
        cascade = MenuItemSpec(
            id="menu_edit",
            item_type="cascade",
            label="Edit",
            children=[item1, item2]
        )

        menubar = MenuBarSpec(
            id="main_bar",
            name="app_menubar",
            items=[cascade]
        )

        data = menubar.to_dict()
        reconstructed = MenuBarSpec.from_dict(data)

        self.assertEqual(reconstructed.id, "main_bar")
        self.assertEqual(reconstructed.name, "app_menubar")
        self.assertEqual(len(reconstructed.items), 1)
        self.assertEqual(reconstructed.items[0].label, "Edit")
        self.assertEqual(len(reconstructed.items[0].children), 2)
        self.assertEqual(reconstructed.items[0].children[0].command, "on_cut")
        self.assertEqual(reconstructed.items[0].children[0].accelerator, "Ctrl+X")
        self.assertEqual(reconstructed.items[0].children[1].item_type, "separator")

if __name__ == "__main__":
    unittest.main()
