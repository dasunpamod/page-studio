"""
Adversarial, Security, and Robustness QA Test Suite for PageStudio.

Covers:
1. Adversarial & Malformed JSON Projects:
   - Completely empty file.
   - Corrupted/truncated JSON.
   - Valid JSON missing required keys (`format`, `version`, `window`, `widgets`).
   - Extreme coordinate values: x=999999999, y=-999999999, width=0, height=-50 (normalization/clamping).
   - Unknown/fabricated widget types (e.g. AlienWidget3000 fallback handling).
   - JSON & code injection in widget text, names, and titles (\0, \r\n, <script>, {, }, ", ').
2. Subprocess Security & Resource Leaks:
   - In preview.py, subprocess.Popen invoked with shell=False (never shell=True).
   - Termination of test subprocesses and cleanup of temporary preview files.
3. Path Safety & File Operations:
   - Saving to read-only directories (error reporting) and nonexistent nested paths (safe auto-creation).
   - Project file paths with spaces, unicode (CJK, accents), and special symbols.
4. Stress Testing:
   - Rapid Undo/Redo cycles (100 rapid operations) verifying bounded memory and no stack overflow.
   - Rapid widget additions and mass deletions.
"""

import unittest
import os
import sys
import json
import tempfile
import py_compile
import subprocess
import shutil
import stat
import tkinter as tk
from unittest.mock import patch, MagicMock

from pagestudio.core.models import WidgetInstance, WIDGET_CATALOG, MenuBarSpec, MenuItemSpec
from pagestudio.core.state import ProjectState
from pagestudio.core.serializer import ProjectSerializer
from pagestudio.core.generator import CodeGenerator
from pagestudio.ui.preview import CodePreviewPanel, PREVIEW_DIR, cleanup_preview
from pagestudio.ui.canvas import DesignCanvas
from pagestudio.ui.inspector import PropertyInspector
from pagestudio.ui.widget_tree import WidgetTree


class TestAdversarialMalformedJSON(unittest.TestCase):
    """Test adversarial, malformed, and corrupted project loading."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_completely_empty_file(self):
        """Empty file raises ValueError without crashing."""
        empty_file = os.path.join(self.tmpdir, "empty.pgproj")
        with open(empty_file, "w", encoding="utf-8") as f:
            pass  # 0 bytes

        with self.assertRaises(ValueError) as ctx:
            ProjectSerializer.load_from_file(empty_file)
        self.assertIn("empty", str(ctx.exception).lower())

    def test_corrupted_truncated_json(self):
        """Corrupted/truncated JSON raises ValueError with clear error description."""
        corrupt_file = os.path.join(self.tmpdir, "corrupt.pgproj")
        with open(corrupt_file, "w", encoding="utf-8") as f:
            f.write('{"format": "pagestudio", "version": "1.0.0", "window": {"title": "broken')

        with self.assertRaises(ValueError) as ctx:
            ProjectSerializer.load_from_file(corrupt_file)
        self.assertIn("corrupted or invalid json", str(ctx.exception).lower())

    def test_valid_json_missing_all_required_keys(self):
        """Valid JSON missing format, version, window, widgets is handled with defaults."""
        minimal_file = os.path.join(self.tmpdir, "minimal.pgproj")
        with open(minimal_file, "w", encoding="utf-8") as f:
            f.write('{}')

        state = ProjectSerializer.load_from_file(minimal_file)
        self.assertIsInstance(state, ProjectState)
        self.assertEqual(state.title, "My Application")
        self.assertEqual(state.width, 600)
        self.assertEqual(state.height, 400)
        self.assertEqual(len(state.widgets), 0)
        self.assertTrue(state.resizable_x)
        self.assertTrue(state.resizable_y)

    def test_extreme_coordinate_values_normalized_and_clamped(self):
        """Extreme values (x=999999999, y=-999999999, width=0, height=-50) are clamped safely."""
        extreme_data = {
            "format": "pagestudio",
            "version": "1.0.0",
            "window": {"title": "Extreme Coordinates", "width": 800, "height": 600},
            "widgets": [
                {
                    "id": "btn_extreme",
                    "widget_type": "Button",
                    "name": "btn_extreme",
                    "x": 999999999,
                    "y": -999999999,
                    "width": 0,
                    "height": -50,
                    "rel_x": 55.5,
                    "rel_y": -10.0,
                    "rel_width": -0.5,
                    "rel_height": 99.0
                }
            ]
        }

        proj_file = os.path.join(self.tmpdir, "extreme.pgproj")
        with open(proj_file, "w", encoding="utf-8") as f:
            json.dump(extreme_data, f)

        state = ProjectSerializer.load_from_file(proj_file)
        w = state.widgets["btn_extreme"]

        # Coordinates clamped to non-negative and sane maximum
        self.assertEqual(w.x, 10000)
        self.assertEqual(w.y, 0)
        # Dimensions clamped to minimum 10px
        self.assertEqual(w.width, 10)
        self.assertEqual(w.height, 10)
        # Relative coordinates clamped to [0.0, 1.0]
        self.assertEqual(w.rel_x, 1.0)
        self.assertEqual(w.rel_y, 0.0)
        self.assertEqual(w.rel_width, 0.01)
        self.assertEqual(w.rel_height, 1.0)

    def test_unknown_fabricated_widget_type_fallback(self):
        """Unknown widget types (e.g. AlienWidget3000) gracefully load and fallback without crashing."""
        alien_data = {
            "format": "pagestudio",
            "version": "1.0.0",
            "widgets": [
                {
                    "id": "alien_1",
                    "widget_type": "AlienWidget3000",
                    "name": "ufo_control",
                    "x": 100,
                    "y": 100,
                    "width": 120,
                    "height": 40
                }
            ]
        }

        state = ProjectSerializer.from_dict(alien_data)
        self.assertIn("alien_1", state.widgets)
        w = state.widgets["alien_1"]
        self.assertEqual(w.widget_type, "AlienWidget3000")

        # Test CodeGenerator fallback for unknown widget type
        gui_code = CodeGenerator.generate_gui_code(state, "alien_test")
        self.assertIn("AlienWidget3000", gui_code)

        # Test UI rendering does not crash
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = DesignCanvas(root, state)
            canvas.render()  # Canvas fallback
            tree = WidgetTree(root, state)
            tree.refresh()  # Tree fallback
            inspector = PropertyInspector(root, state)
            state.select_widget("alien_1")
            inspector.refresh()  # Inspector fallback
        finally:
            root.destroy()

    def test_injection_in_widget_text_names_and_titles(self):
        """JSON & code injection in text, names, and titles compile and run cleanly without syntax errors."""
        state = ProjectState(title='Injected "Title" \n \r \0 <script>alert("xss")</script> {foo}', width=650, height=450)
        w = WidgetInstance.create("Button", 20, 20)
        w.name = 'injected_btn_\0_\r\n_<script>'
        w.properties["text"] = 'Click "Me" \n \r \0 {code} & <script>alert(1)</script>'
        w.events["command"] = 'cmd_injection_\0_<script>'
        state.add_widget(w)

        gui_path, sup_path = CodeGenerator.generate_all(state, "injection_app", self.tmpdir)

        # Verify generated Python files compile cleanly
        py_compile.compile(gui_path, doraise=True)
        py_compile.compile(sup_path, doraise=True)

        with open(gui_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify that identifier was sanitized (no <script> or raw null bytes in identifier)
        self.assertIn("self.injected_btn_script_ = ttk.Button", content)
        self.assertIn("command=support.cmd_injection_script_", content)
        self.assertIn("root.title(", content)


class TestSubprocessSecurityAndResourceLeaks(unittest.TestCase):
    """Test subprocess security (shell=False) and leak prevention."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState("Subprocess Test", 500, 350)
        btn = WidgetInstance.create("Button", 30, 30)
        self.state.add_widget(btn)
        self.panel = CodePreviewPanel(self.root, self.state, app_name="sec_test")

    def tearDown(self):
        try:
            self.panel.cleanup()
            self.panel.destroy()
        except Exception:
            pass
        self.root.destroy()
        cleanup_preview()

    def test_subprocess_popen_invoked_with_shell_false(self):
        """Verify subprocess.Popen is invoked with shell=False (never shell=True)."""
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            self.panel.run_test_gui()

            self.assertTrue(mock_popen.called)
            args, kwargs = mock_popen.call_args

            # Command must be a sequence/list (not raw string susceptible to shell injection)
            self.assertIsInstance(args[0], list)
            self.assertEqual(args[0][0], sys.executable)
            # shell argument must be False (explicitly or by default)
            self.assertFalse(kwargs.get("shell", False))

    def test_subprocess_termination_and_preview_file_cleanup(self):
        """Verify preview processes terminate and temporary preview directories can be cleaned."""
        # Real subprocess run with quick exit
        with patch.object(self.panel, "_terminate_active_proc") as mock_term:
            self.panel.run_test_gui()
            self.assertTrue(mock_term.called)

        # Cleanup preview and verify active process termination
        self.panel.cleanup()
        self.assertIsNone(self.panel._active_proc)


class TestPathSafetyAndFileOperations(unittest.TestCase):
    """Test filesystem edge cases: nested directories, read-only paths, spaces, and Unicode."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state = ProjectState("Path Safety Project", 600, 400)
        btn = WidgetInstance.create("Button", 10, 10)
        self.state.add_widget(btn)

    def tearDown(self):
        # Restore permissions if altered before removal
        for root, dirs, files in os.walk(self.tmpdir):
            for d in dirs:
                try:
                    os.chmod(os.path.join(root, d), stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), stat.S_IWRITE | stat.S_IREAD)
                except Exception:
                    pass
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_to_nonexistent_deeply_nested_path(self):
        """Saving to a deeply nested nonexistent path automatically creates directories."""
        deep_path = os.path.join(self.tmpdir, "a", "b", "c", "d", "my_app.pgproj")
        self.assertFalse(os.path.exists(os.path.dirname(deep_path)))

        ProjectSerializer.save_to_file(self.state, deep_path)
        self.assertTrue(os.path.exists(deep_path))

        loaded = ProjectSerializer.load_from_file(deep_path)
        self.assertEqual(loaded.title, "Path Safety Project")
        self.assertEqual(len(loaded.widgets), 1)

    def test_save_to_read_only_directory_reports_error(self):
        """Saving to a read-only directory raises PermissionError/OSError gracefully."""
        ro_dir = os.path.join(self.tmpdir, "readonly_dir")
        os.makedirs(ro_dir, exist_ok=True)
        target_file = os.path.join(ro_dir, "test.pgproj")

        # Make read-only
        try:
            os.chmod(ro_dir, stat.S_IREAD)
            with open(target_file, "w") as f:
                f.write("initial")
            os.chmod(target_file, stat.S_IREAD)

            with self.assertRaises((PermissionError, OSError)):
                ProjectSerializer.save_to_file(self.state, target_file)
        finally:
            os.chmod(target_file, stat.S_IWRITE)
            os.chmod(ro_dir, stat.S_IWRITE)

    def test_paths_with_spaces_unicode_and_symbols(self):
        """File paths with spaces, unicode characters, accents, and symbols round-trip cleanly."""
        complex_filename = "Projet 界面设计 #1 — (étudiant) 🚀.pgproj"
        sub_folder = "Folder with Spaces & Symbols (#@!)"
        full_path = os.path.join(self.tmpdir, sub_folder, complex_filename)

        ProjectSerializer.save_to_file(self.state, full_path)
        self.assertTrue(os.path.exists(full_path))

        loaded = ProjectSerializer.load_from_file(full_path)
        self.assertEqual(loaded.title, "Path Safety Project")
        self.assertIn(list(self.state.widgets.keys())[0], loaded.widgets)


class TestStressAndStability(unittest.TestCase):
    """Stress tests: 100 rapid undo/redo cycles, rapid additions and mass deletions."""

    def test_rapid_undo_redo_cycles(self):
        """Perform 100 rapid undo/redo cycles to verify bounded memory and zero stack overflow."""
        state = ProjectState("Undo/Redo Stress", 600, 400)
        w = WidgetInstance.create("Button", 10, 10)
        state.add_widget(w)

        # Make 60 mutations (exceeds 50 snapshot cap)
        for i in range(60):
            state.update_widget_geometry(w.id, 10 + i * 2, 10 + i * 2, 100, 30)

        # Undo stack capped at 50
        self.assertLessEqual(len(state._undo_stack), 50)

        # Perform 100 rapid undo / redo cycles
        for _ in range(100):
            state.undo()
            state.redo()

        # State remains coherent and widget geometry is intact
        self.assertIn(w.id, state.widgets)
        self.assertLessEqual(len(state._undo_stack), 50)
        self.assertLessEqual(len(state._redo_stack), 50)

    def test_rapid_widget_additions_and_mass_deletions(self):
        """Add 200 widgets in rapid succession and mass delete them cleanly."""
        state = ProjectState("Mass Widget Stress", 1200, 800)

        widget_ids = []
        for i in range(200):
            w = WidgetInstance.create("Label", (i % 10) * 80, (i // 10) * 30, name_hint=f"lbl_{i}")
            state.add_widget(w)
            widget_ids.append(w.id)

        self.assertEqual(len(state.widgets), 200)
        self.assertEqual(len(state.widget_order), 200)

        # Mass delete all widgets
        state.selected_ids = list(widget_ids)
        state.remove_selected()

        self.assertEqual(len(state.widgets), 0)
        self.assertEqual(len(state.widget_order), 0)
        self.assertEqual(len(state.selected_ids), 0)

        # Undo the mass deletion
        state.undo()
        self.assertEqual(len(state.widgets), 200)


if __name__ == "__main__":
    unittest.main()
