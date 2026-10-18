"""Test PageStudioApp window instantiation."""
import unittest
import tkinter as tk
from pagestudio.ui.app_window import PageStudioApp

class TestAppWindow(unittest.TestCase):

    def test_app_window_initialization(self):
        """Verify PageStudioApp initializes all panels, menus, and widgets without error."""
        root = tk.Tk()
        # Withdraw so it doesn't display a visible window during test
        root.withdraw()
        try:
            app = PageStudioApp(root)
            self.assertIsNotNone(app.palette)
            self.assertIsNotNone(app.canvas)
            self.assertIsNotNone(app.inspector)
            self.assertIsNotNone(app.preview_panel)
            self.assertEqual(app.state.title, "My Application")
        finally:
            root.destroy()

if __name__ == "__main__":
    unittest.main()
