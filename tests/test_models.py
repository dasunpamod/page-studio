"""Tests for widget models and catalog in PageStudio."""
import unittest
from pagestudio.core.models import WidgetInstance, WIDGET_CATALOG

class TestWidgetModels(unittest.TestCase):

    def test_catalog_completeness(self):
        """Ensure standard widgets exist in catalog."""
        expected = ["Button", "Entry", "Label", "Checkbutton", "Radiobutton", "Combobox", "Progressbar"]
        for name in expected:
            self.assertIn(name, WIDGET_CATALOG)
            spec = WIDGET_CATALOG[name]
            self.assertGreater(spec.default_width, 0)
            self.assertGreater(spec.default_height, 0)

    def test_widget_creation(self):
        """Test instantiating a widget with default properties."""
        w = WidgetInstance.create("Button", 50, 60, name_hint="my_button")
        self.assertEqual(w.widget_type, "Button")
        self.assertEqual(w.name, "my_button")
        self.assertEqual(w.x, 50)
        self.assertEqual(w.y, 60)
        self.assertEqual(w.properties.get("text"), "Button")
        self.assertIn("command", w.events)

    def test_widget_to_and_from_dict(self):
        """Test serialization round-trip of a single widget."""
        w1 = WidgetInstance.create("Entry", 100, 150)
        w1.properties["text"] = "Sample Value"
        data = w1.to_dict()
        w2 = WidgetInstance.from_dict(data)

        self.assertEqual(w1.id, w2.id)
        self.assertEqual(w1.widget_type, w2.widget_type)
        self.assertEqual(w1.x, w2.x)
        self.assertEqual(w1.y, w2.y)
        self.assertEqual(w1.properties, w2.properties)

if __name__ == "__main__":
    unittest.main()
