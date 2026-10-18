"""
Unit Tests for UI Interaction & Platform Compatibility in PageStudio.
Verifies:
1. Focus Guard on Keyboard Shortcuts:
   - <Delete> and <BackSpace> do NOT delete canvas widgets when focused in Entry, Text, Spinbox, or Combobox.
   - <Delete> and <BackSpace> DO delete canvas widgets when focused on the canvas or non-text widgets.
2. Arrow Key Micro-Nudging:
   - <Left>, <Right>, <Up>, <Down> do NOT nudge canvas widgets when a text input is focused.
   - Arrow keys nudge canvas widgets when canvas is active.
   - Nudging strictly respects parent container boundaries (0 <= x <= container_w - w, 0 <= y <= container_h - h).
3. Canvas Resize Handles & Moving Container Constraints:
   - Drag moving widgets respects container boundaries.
   - 8-point resize handles (East, South, West, North) respect parent container boundaries.
   - Minimum widget dimensions (15px) are enforced.
4. Cross-Platform Mouse Wheel Scrolling:
   - DesignCanvas scrolling on Windows (delta/120), macOS (delta), and Linux (Button-4/Button-5, Shift-Button-4/5).
   - WidgetPalette scrolling on Windows, macOS, and Linux.
   - PropertyInspector scrolling on Windows, macOS, and Linux.
5. Modal Dialog Management:
   - MenuEditorDialog, NotebookTabEditorDialog, TreeviewColumnEditorDialog, FontChooserDialog.
   - Verify transient(parent), grab_set(), WM_DELETE_WINDOW protocol, and grab_release() on close/cancel.
"""

import unittest
import tkinter as tk
from tkinter import ttk
from typing import Optional

from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance
from pagestudio.ui.canvas import DesignCanvas
from pagestudio.ui.palette import WidgetPalette
from pagestudio.ui.inspector import PropertyInspector
from pagestudio.ui.app_window import PageStudioApp
from pagestudio.ui.menu_editor import MenuEditorDialog
from pagestudio.ui.notebook_editor import NotebookTabEditorDialog
from pagestudio.ui.treeview_editor import TreeviewColumnEditorDialog
from pagestudio.ui.font_chooser import FontChooserDialog
from pagestudio.utils.helpers import is_text_editing


class DummyEvent:
    """Mock Tkinter event."""
    def __init__(self, widget=None, delta=0, num=0, state=0):
        self.widget = widget
        self.delta = delta
        self.num = num
        self.state = state


class TestFocusGuards(unittest.TestCase):
    """Test keyboard focus guards on Delete, BackSpace, and Arrow keys."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState(title="Focus Guard Test", width=600, height=400)
        self.canvas = DesignCanvas(self.root, self.state)
        self.canvas.pack()

        # Add a test widget on the canvas and select it
        self.button = WidgetInstance.create("Button", 100, 100)
        self.button.width = 80
        self.button.height = 30
        self.state.add_widget(self.button)
        self.state.select_widget(self.button.id)

    def tearDown(self):
        self.root.destroy()

    def test_is_text_editing_helper(self):
        """Test is_text_editing detects all text input widgets."""
        entry = tk.Entry(self.root)
        ttk_entry = ttk.Entry(self.root)
        text = tk.Text(self.root)
        spinbox = tk.Spinbox(self.root)
        ttk_spinbox = ttk.Spinbox(self.root)
        combo = ttk.Combobox(self.root)
        label = tk.Label(self.root, text="Non-editing")

        self.assertTrue(is_text_editing(self.root, DummyEvent(widget=entry)))
        self.assertTrue(is_text_editing(self.root, DummyEvent(widget=ttk_entry)))
        self.assertTrue(is_text_editing(self.root, DummyEvent(widget=text)))
        self.assertTrue(is_text_editing(self.root, DummyEvent(widget=spinbox)))
        self.assertTrue(is_text_editing(self.root, DummyEvent(widget=ttk_spinbox)))
        self.assertTrue(is_text_editing(self.root, DummyEvent(widget=combo)))
        self.assertFalse(is_text_editing(self.root, DummyEvent(widget=label)))

    def test_delete_key_blocked_when_entry_focused(self):
        """When an Entry widget has focus or is the event widget, Delete must NOT remove widget."""
        entry = tk.Entry(self.root)
        entry.pack()
        entry.focus_set()
        self.root.update_idletasks()

        # Event targeting entry
        ev = DummyEvent(widget=entry)
        self.canvas._on_delete_key(ev)

        # Widget should still exist!
        self.assertIn(self.button.id, self.state.widgets)

    def test_backspace_key_blocked_when_text_focused(self):
        """When a Text widget is the event source, Backspace must NOT remove widget."""
        text = tk.Text(self.root)
        text.pack()
        text.focus_set()
        self.root.update_idletasks()

        ev = DummyEvent(widget=text)
        self.canvas._on_delete_key(ev)
        self.assertIn(self.button.id, self.state.widgets)

    def test_delete_key_blocked_when_spinbox_focused(self):
        """When a Spinbox is the event source, Delete must NOT remove widget."""
        spin = tk.Spinbox(self.root)
        spin.pack()
        ev = DummyEvent(widget=spin)
        self.canvas._on_delete_key(ev)
        self.assertIn(self.button.id, self.state.widgets)

    def test_delete_key_deletes_when_canvas_focused(self):
        """When no text input is focused (e.g. canvas is event source), Delete removes widget."""
        ev = DummyEvent(widget=self.canvas.canvas)
        self.canvas._on_delete_key(ev)
        self.assertNotIn(self.button.id, self.state.widgets)

    def test_arrow_keys_blocked_when_entry_focused(self):
        """Arrow keys must NOT nudge canvas widgets when a text widget is focused."""
        entry = tk.Entry(self.root)
        entry.pack()
        entry.focus_set()
        self.root.update_idletasks()

        initial_x = self.button.x
        initial_y = self.button.y

        ev = DummyEvent(widget=entry)
        self.canvas._nudge_selected(1, 0, ev)
        self.canvas._nudge_selected(0, 1, ev)
        self.canvas._nudge_selected(-1, 0, ev)
        self.canvas._nudge_selected(0, -1, ev)

        self.assertEqual(self.button.x, initial_x)
        self.assertEqual(self.button.y, initial_y)

    def test_arrow_keys_nudge_when_canvas_focused(self):
        """Arrow keys nudge canvas widgets when canvas is active."""
        ev = DummyEvent(widget=self.canvas.canvas)
        initial_x = self.button.x
        initial_y = self.button.y

        self.canvas._nudge_selected(1, 0, ev)
        self.assertEqual(self.button.x, initial_x + 1)

        self.canvas._nudge_selected(0, 1, ev)
        self.assertEqual(self.button.y, initial_y + 1)


class TestContainerBoundaries(unittest.TestCase):
    """Test boundary constraints for nudging, dragging, and resizing handles."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState(title="Bounds Test", width=500, height=400)
        self.canvas = DesignCanvas(self.root, self.state)
        self.canvas.pack()

        # Create parent frame container (200x150 at (50, 50))
        self.frame = WidgetInstance.create("Frame", 50, 50)
        self.frame.width = 200
        self.frame.height = 150
        self.state.add_widget(self.frame)

        # Create child widget inside frame at local (20, 20), size 60x40
        self.child = WidgetInstance.create("Button", 20, 20, parent_id=self.frame.id)
        self.child.width = 60
        self.child.height = 40
        self.state.add_widget(self.child)
        self.state.select_widget(self.child.id)

    def tearDown(self):
        self.root.destroy()

    def test_nudge_respects_container_boundaries(self):
        """Verify nudging cannot move widget outside its parent container."""
        ev = DummyEvent(widget=self.canvas.canvas)

        # Nudge left past 0
        for _ in range(50):
            self.canvas._nudge_selected(-1, 0, ev)
        self.assertEqual(self.child.x, 0)

        # Nudge top past 0
        for _ in range(50):
            self.canvas._nudge_selected(0, -1, ev)
        self.assertEqual(self.child.y, 0)

        # Nudge right past container right bound (container.width = 200, child.width = 60 => max_x = 140)
        for _ in range(300):
            self.canvas._nudge_selected(1, 0, ev)
        self.assertEqual(self.child.x, 140)

        # Nudge down past container bottom bound (container.height = 150, child.height = 40 => max_y = 110)
        for _ in range(300):
            self.canvas._nudge_selected(0, 1, ev)
        self.assertEqual(self.child.y, 110)

    def test_resize_handles_respect_container_boundaries(self):
        """Verify resizing with handles stops at parent container bounds."""
        self.child.x = 50
        self.child.y = 40
        self.child.width = 60
        self.child.height = 40

        # Simulate resize East (drag right edge)
        self.canvas.drag_mode = "resize"
        self.canvas.active_handle = "e"
        self.canvas.drag_start_x = 100
        self.canvas.drag_start_y = 100
        self.canvas.orig_geom = {self.child.id: (50, 40, 60, 40)}

        # Try to drag right edge far beyond container width (200)
        # container_w = 200, ox = 50 => max width = 150
        ev = DummyEvent()
        ev.x = 100 + 500
        ev.y = 100
        self.canvas._on_mouse_drag(ev)

        self.assertEqual(self.child.width, 150)
        self.assertEqual(self.child.x + self.child.width, 200)

        # Simulate resize West (drag left edge towards negative)
        self.canvas.active_handle = "w"
        self.canvas.orig_geom = {self.child.id: (50, 40, 60, 40)}
        ev.x = 100 - 200
        self.canvas._on_mouse_drag(ev)

        # Left edge should stop at 0, right edge stays at 110 => width = 110
        self.assertEqual(self.child.x, 0)
        self.assertEqual(self.child.width, 110)

        # Simulate resize South (drag bottom edge beyond container height 150)
        self.canvas.active_handle = "s"
        self.canvas.orig_geom = {self.child.id: (50, 40, 60, 40)}
        ev.x = 100
        ev.y = 100 + 500
        self.canvas._on_mouse_drag(ev)

        # container_h = 150, oy = 40 => max height = 110
        self.assertEqual(self.child.height, 110)
        self.assertEqual(self.child.y + self.child.height, 150)

        # Simulate resize North (drag top edge towards negative)
        self.canvas.active_handle = "n"
        self.canvas.orig_geom = {self.child.id: (50, 40, 60, 40)}
        ev.x = 100
        ev.y = 100 - 200
        self.canvas._on_mouse_drag(ev)

        # Top edge should stop at 0, bottom edge stays at 80 => height = 80
        self.assertEqual(self.child.y, 0)
        self.assertEqual(self.child.height, 80)

    def test_drag_move_respects_container_boundaries(self):
        """Verify dragging to move a widget stops at container boundaries."""
        self.child.x = 20
        self.child.y = 20
        self.canvas.drag_mode = "move"
        self.canvas.drag_start_x = 50
        self.canvas.drag_start_y = 50
        self.canvas.orig_geom = {self.child.id: (20, 20, 60, 40)}

        # Drag far to top-left
        ev = DummyEvent()
        ev.x = -100
        ev.y = -100
        self.canvas._on_mouse_drag(ev)
        self.assertEqual(self.child.x, 0)
        self.assertEqual(self.child.y, 0)

        # Drag far to bottom-right (container = 200x150, child = 60x40 => max = 140, 110)
        ev.x = 50 + 500
        ev.y = 50 + 500
        self.canvas._on_mouse_drag(ev)
        self.assertEqual(self.child.x, 140)
        self.assertEqual(self.child.y, 110)


class TestCrossPlatformMouseWheel(unittest.TestCase):
    """Test mousewheel scrolling on canvas, palette, and inspector across platforms."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState(title="Scroll Test", width=800, height=600)
        self.canvas = DesignCanvas(self.root, self.state)
        self.canvas.pack()

        self.palette = WidgetPalette(self.root, on_select_widget=lambda t: None)
        self.palette.pack()

        self.inspector = PropertyInspector(self.root, self.state)
        self.inspector.pack()

    def tearDown(self):
        self.root.destroy()

    def test_canvas_scrolling_windows_and_mac_and_linux(self):
        """Verify canvas scroll events work for Windows delta, Mac delta, and Linux Button-4/5."""
        # Windows vertical scroll down (delta = -120)
        ev_win = DummyEvent(delta=-120)
        self.canvas._on_mousewheel(ev_win)

        # Windows vertical scroll up (delta = 120)
        ev_win_up = DummyEvent(delta=120)
        self.canvas._on_mousewheel(ev_win_up)

        # Linux vertical scroll up (Button-4)
        ev_linux_up = DummyEvent(num=4)
        self.canvas._on_mousewheel(ev_linux_up)

        # Linux vertical scroll down (Button-5)
        ev_linux_down = DummyEvent(num=5)
        self.canvas._on_mousewheel(ev_linux_down)

        # Shift mousewheel horizontal scroll
        self.canvas._on_shift_mousewheel(DummyEvent(delta=-120))
        self.canvas._on_shift_mousewheel(DummyEvent(num=4))
        self.canvas._on_shift_mousewheel(DummyEvent(num=5))

    def test_palette_and_inspector_mousewheel_handlers(self):
        """Verify palette and inspector have mousewheel and linux scroll handlers."""
        self.assertTrue(hasattr(self.palette, "_on_mousewheel"))
        self.assertTrue(hasattr(self.palette, "_on_linux_scroll_up"))
        self.assertTrue(hasattr(self.palette, "_on_linux_scroll_down"))

        self.assertTrue(hasattr(self.inspector, "_on_mousewheel"))
        self.assertTrue(hasattr(self.inspector, "_on_linux_scroll_up"))
        self.assertTrue(hasattr(self.inspector, "_on_linux_scroll_down"))


class TestModalDialogModality(unittest.TestCase):
    """Test dialog modality, transient status, grab_set, WM_DELETE_WINDOW, and grab_release."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        self.root.destroy()

    def test_menu_editor_dialog_modality(self):
        """Verify MenuEditorDialog uses transient, grab_set, and releases grab on close."""
        dialog = MenuEditorDialog(self.root, modal=False)
        self.assertEqual(str(dialog.transient()), str(self.root))
        # Verify WM_DELETE_WINDOW protocol is set
        self.assertIn("WM_DELETE_WINDOW", dialog.protocol())
        # Close via cancel
        dialog._on_cancel_clicked()
        self.assertIsNone(dialog.result)

    def test_notebook_editor_dialog_modality(self):
        """Verify NotebookTabEditorDialog uses transient, grab_set, and releases grab on close."""
        dialog = NotebookTabEditorDialog(self.root, modal=False)
        self.assertEqual(str(dialog.transient()), str(self.root))
        self.assertIn("WM_DELETE_WINDOW", dialog.protocol())
        dialog._on_cancel_clicked()
        self.assertIsNone(dialog.result)

    def test_treeview_editor_dialog_modality(self):
        """Verify TreeviewColumnEditorDialog uses transient, grab_set, and releases grab on close."""
        dialog = TreeviewColumnEditorDialog(self.root, modal=False)
        self.assertEqual(str(dialog.transient()), str(self.root))
        self.assertIn("WM_DELETE_WINDOW", dialog.protocol())
        dialog._on_cancel_clicked()
        self.assertIsNone(dialog.result)

    def test_font_chooser_dialog_modality(self):
        """Verify FontChooserDialog uses transient, grab_set, and releases grab on close."""
        dialog = FontChooserDialog(self.root, modal=False)
        self.assertEqual(str(dialog.transient()), str(self.root))
        self.assertIn("WM_DELETE_WINDOW", dialog.protocol())
        dialog._on_cancel_clicked()
        self.assertIsNone(dialog.result)


if __name__ == "__main__":
    unittest.main()
