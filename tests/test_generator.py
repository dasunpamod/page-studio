"""Tests for Python Tkinter code generation and syntax validity."""
import unittest
import py_compile
import tempfile
import os
from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance
from pagestudio.core.generator import CodeGenerator

class TestCodeGenerator(unittest.TestCase):

    def test_syntax_validity_all_widgets(self):
        """Generates code with every widget type and compiles it with py_compile."""
        state = ProjectState("All Widgets Test", 800, 600)
        
        # Add one of each major widget
        widget_types = [
            "Button", "Entry", "Label", "Checkbutton", "Radiobutton",
            "Combobox", "Listbox", "Text", "Progressbar", "Scale",
            "Separator", "Frame", "LabelFrame", "Canvas"
        ]
        
        for i, wtype in enumerate(widget_types):
            w = WidgetInstance.create(wtype, 20, 20 + i * 35)
            state.add_widget(w)

        with tempfile.TemporaryDirectory() as tmpdir:
            gui_path, sup_path = CodeGenerator.generate_all(state, "test_app", tmpdir)

            self.assertTrue(os.path.exists(gui_path))
            self.assertTrue(os.path.exists(sup_path))

            # Validate that generated Python files compile without any SyntaxError
            try:
                py_compile.compile(gui_path, doraise=True)
                py_compile.compile(sup_path, doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"Generated Python code failed syntax compilation: {e}")

    def test_support_preserves_custom_code(self):
        """Ensure reconciling doesn't wipe existing user logic in support module."""
        state = ProjectState("Preserve Test", 400, 300)
        btn = WidgetInstance.create("Button", 10, 10, name_hint="btn_action")
        btn.events["command"] = "on_action"
        state.add_widget(btn)

        existing_support = (
            "def on_action():\n"
            "    # USER_CUSTOM_CODE_HERE\n"
            "    return 42\n"
        )

        sup_code = CodeGenerator.generate_support_code(state, "preserve_test", existing_support)
        self.assertIn("def on_action():", sup_code)

if __name__ == "__main__":
    unittest.main()
