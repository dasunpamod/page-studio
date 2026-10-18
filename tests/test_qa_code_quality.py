"""
PageStudio Quality Assurance & Static Analysis Tests
Validates:
1. Syntax and compilation integrity of all Python files in the repository.
2. Dynamic module importability without side-effects or circular import crashes.
3. Clean package exports for pagestudio and pagestudio.ui.
4. Comprehensive metadata validation for all 42 entries in WIDGET_CATALOG.
5. Presence of module-level docstrings across all pagestudio source files.
"""

import unittest
import py_compile
import importlib
import os
import sys
from pathlib import Path

# Ensure repository root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pagestudio.core.models import WIDGET_CATALOG, WidgetTypeSpec
import pagestudio
import pagestudio.ui


class TestQACodeQuality(unittest.TestCase):
    """Static analysis and code hygiene test suite for PageStudio."""

    def test_py_compile_all_files(self):
        """Programmatically discover all .py files and verify they compile with py_compile."""
        py_files = []
        for root, dirs, files in os.walk(REPO_ROOT):
            # Skip hidden and cache directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    py_files.append(os.path.join(root, file))

        self.assertGreater(len(py_files), 15, "Expected at least 15 Python files in repository")

        for py_file in py_files:
            with self.subTest(file=os.path.relpath(py_file, REPO_ROOT)):
                try:
                    py_compile.compile(py_file, doraise=True)
                except py_compile.PyCompileError as err:
                    self.fail(f"Compilation error in {py_file}: {err}")

    def test_import_all_pagestudio_modules(self):
        """Validate every module in pagestudio can be imported dynamically without circular crashes."""
        pagestudio_dir = REPO_ROOT / "pagestudio"
        self.assertTrue(pagestudio_dir.is_dir(), "pagestudio package directory must exist")

        module_names = []
        for root, dirs, files in os.walk(pagestudio_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(REPO_ROOT)
                    parts = list(rel_path.with_suffix("").parts)
                    if parts[-1] == "__init__":
                        parts.pop()
                    mod_name = ".".join(parts)
                    if mod_name:
                        module_names.append(mod_name)

        self.assertIn("pagestudio", module_names)
        self.assertIn("pagestudio.core.models", module_names)
        self.assertIn("pagestudio.ui.app_window", module_names)

        for mod_name in module_names:
            with self.subTest(module=mod_name):
                try:
                    mod = importlib.import_module(mod_name)
                    self.assertIsNotNone(mod, f"Module {mod_name} should not be None")
                except Exception as err:
                    self.fail(f"Failed to dynamically import {mod_name}: {err}")

    def test_widget_catalog_metadata_and_dimensions(self):
        """Assert WIDGET_CATALOG has valid metadata for all 42 entries."""
        self.assertEqual(len(WIDGET_CATALOG), 42, "WIDGET_CATALOG must contain exactly 42 entries")

        valid_categories = {"Standard Tk", "Themed ttk", "Scrolled Widgets", "Advanced"}

        for widget_type, spec in WIDGET_CATALOG.items():
            with self.subTest(widget=widget_type):
                self.assertIsInstance(spec, WidgetTypeSpec)
                self.assertEqual(spec.type_name, widget_type, "type_name must match catalog key")
                self.assertTrue(len(spec.display_name.strip()) > 0, "display_name must be non-empty")
                self.assertIn(spec.category, valid_categories, f"Invalid category {spec.category} for {widget_type}")
                self.assertGreater(spec.default_width, 0, f"default_width must be positive for {widget_type}")
                self.assertGreater(spec.default_height, 0, f"default_height must be positive for {widget_type}")
                self.assertIsInstance(spec.is_container, bool)
                self.assertIsInstance(spec.supported_events, list)
                self.assertIsInstance(spec.supported_props, list)
                self.assertGreater(len(spec.supported_props), 0, f"supported_props must be non-empty for {widget_type}")

    def test_clean_package_exports(self):
        """Verify pagestudio and pagestudio.ui have clean and complete exports in __all__."""
        # Top-level package exports
        self.assertTrue(hasattr(pagestudio, "__all__"), "pagestudio must define __all__")
        self.assertIn("PageStudioApp", pagestudio.__all__)
        self.assertIn("__version__", pagestudio.__all__)
        for name in pagestudio.__all__:
            self.assertTrue(hasattr(pagestudio, name), f"pagestudio missing exported attribute: {name}")

        # UI package exports
        self.assertTrue(hasattr(pagestudio.ui, "__all__"), "pagestudio.ui must define __all__")
        self.assertIn("PageStudioApp", pagestudio.ui.__all__)
        self.assertIn("DesignCanvas", pagestudio.ui.__all__)
        self.assertIn("WidgetPalette", pagestudio.ui.__all__)
        self.assertIn("PropertyInspector", pagestudio.ui.__all__)
        self.assertIn("MenuEditorDialog", pagestudio.ui.__all__)
        self.assertIn("NotebookTabEditorDialog", pagestudio.ui.__all__)
        self.assertIn("TreeviewColumnEditorDialog", pagestudio.ui.__all__)
        self.assertIn("FontChooserDialog", pagestudio.ui.__all__)
        for name in pagestudio.ui.__all__:
            self.assertTrue(hasattr(pagestudio.ui, name), f"pagestudio.ui missing exported attribute: {name}")

    def test_module_level_docstrings(self):
        """Verify every Python module in pagestudio has a descriptive module-level docstring."""
        pagestudio_dir = REPO_ROOT / "pagestudio"
        for root, dirs, files in os.walk(pagestudio_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(REPO_ROOT)
                    with self.subTest(file=str(rel_path)):
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        import ast
                        tree = ast.parse(content, filename=str(full_path))
                        doc = ast.get_docstring(tree)
                        self.assertIsNotNone(doc, f"Module {rel_path} is missing a module docstring")
                        self.assertGreater(len(doc.strip()), 10, f"Module {rel_path} docstring is too short")


if __name__ == "__main__":
    unittest.main()
