"""
Comprehensive edge-case unit tests for PageStudio state management,
hierarchy validation, deep copying, Z-order, and serialization.
"""

import unittest
import tempfile
import os
import copy
from typing import List, Dict, Any

from pagestudio.core.models import (
    WidgetInstance,
    MenuBarSpec,
    MenuItemSpec,
    WIDGET_CATALOG,
)
from pagestudio.core.state import ProjectState
from pagestudio.core.serializer import ProjectSerializer


class TestCircularHierarchyPrevention(unittest.TestCase):
    """Verifies that circular parent-child relationships are strictly prevented."""

    def setUp(self):
        self.state = ProjectState("Hierarchy Safety Test", 800, 600)

    def test_prevent_self_parenting_in_add_widget(self):
        """A widget cannot be added with itself as parent."""
        w = WidgetInstance.create("Frame", 10, 10)
        with self.assertRaises(ValueError):
            self.state.add_widget(w, parent_id=w.id)

    def test_prevent_self_parenting_when_preassigned(self):
        """A widget cannot be added if its pre-assigned parent_id is its own id."""
        w = WidgetInstance.create("Frame", 10, 10)
        w.parent_id = w.id
        with self.assertRaises(ValueError):
            self.state.add_widget(w)

    def test_prevent_self_parenting_in_set_widget_parent(self):
        """Calling set_widget_parent with widget's own id must raise ValueError."""
        w = WidgetInstance.create("Frame", 10, 10)
        self.state.add_widget(w)
        with self.assertRaises(ValueError):
            self.state.set_widget_parent(w.id, w.id)

    def test_prevent_direct_circular_hierarchy(self):
        """If A is parent of B, B cannot become parent of A."""
        frame_a = WidgetInstance.create("Frame", 10, 10, name_hint="frame_a")
        frame_b = WidgetInstance.create("Frame", 20, 20, name_hint="frame_b")
        self.state.add_widget(frame_a)
        self.state.add_widget(frame_b, parent_id=frame_a.id)

        self.assertEqual(frame_b.parent_id, frame_a.id)
        self.assertIn(frame_b.id, [d.id for d in self.state.get_all_descendants(frame_a.id)])

        # Attempt to make B the parent of A
        with self.assertRaises(ValueError) as ctx:
            self.state.set_widget_parent(frame_a.id, frame_b.id)
        self.assertIn("circular", str(ctx.exception).lower())

    def test_prevent_multilevel_circular_hierarchy(self):
        """A -> B -> C -> D: A cannot be parented to D, B cannot be parented to D, etc."""
        a = WidgetInstance.create("Frame", 0, 0, name_hint="a")
        b = WidgetInstance.create("Frame", 10, 10, name_hint="b")
        c = WidgetInstance.create("Frame", 20, 20, name_hint="c")
        d = WidgetInstance.create("Frame", 30, 30, name_hint="d")

        self.state.add_widget(a)
        self.state.add_widget(b, parent_id=a.id)
        self.state.add_widget(c, parent_id=b.id)
        self.state.add_widget(d, parent_id=c.id)

        # A cannot become child of D
        with self.assertRaises(ValueError):
            self.state.set_widget_parent(a.id, d.id)

        # B cannot become child of D
        with self.assertRaises(ValueError):
            self.state.set_widget_parent(b.id, d.id)

        # C cannot become child of D
        with self.assertRaises(ValueError):
            self.state.set_widget_parent(c.id, d.id)

        # A cannot become child of C
        with self.assertRaises(ValueError):
            self.state.set_widget_parent(a.id, c.id)

    def test_valid_reparenting_succeeds(self):
        """Moving a descendant up the tree or detaching to root canvas is valid."""
        a = WidgetInstance.create("Frame", 0, 0, name_hint="a")
        b = WidgetInstance.create("Frame", 10, 10, name_hint="b")
        c = WidgetInstance.create("Button", 20, 20, name_hint="c")

        self.state.add_widget(a)
        self.state.add_widget(b, parent_id=a.id)
        self.state.add_widget(c, parent_id=b.id)

        # Move C from B to A directly
        self.state.set_widget_parent(c.id, a.id)
        self.assertEqual(self.state.widgets[c.id].parent_id, a.id)
        self.assertIn(c.id, [w.id for w in self.state.get_children(a.id)])
        self.assertNotIn(c.id, [w.id for w in self.state.get_children(b.id)])

        # Move C to root canvas (None)
        self.state.set_widget_parent(c.id, None)
        self.assertIsNone(self.state.widgets[c.id].parent_id)
        self.assertIn(c.id, [w.id for w in self.state.get_children(None)])

    def test_is_valid_parent_query(self):
        """Verify is_valid_parent logic under various scenarios."""
        f1 = WidgetInstance.create("Frame", 0, 0, name_hint="f1")
        f2 = WidgetInstance.create("Frame", 0, 0, name_hint="f2")
        btn = WidgetInstance.create("Button", 0, 0, name_hint="btn")

        self.state.add_widget(f1)
        self.state.add_widget(f2, parent_id=f1.id)
        self.state.add_widget(btn, parent_id=f2.id)

        # None (root) is always valid
        self.assertTrue(self.state.is_valid_parent(f1.id, None))
        self.assertTrue(self.state.is_valid_parent(f2.id, None))

        # Self is invalid
        self.assertFalse(self.state.is_valid_parent(f1.id, f1.id))

        # Non-existent ID is invalid
        self.assertFalse(self.state.is_valid_parent(f1.id, "non_existent_id"))

        # Descendant is invalid
        self.assertFalse(self.state.is_valid_parent(f1.id, f2.id))
        self.assertFalse(self.state.is_valid_parent(f1.id, btn.id))
        self.assertFalse(self.state.is_valid_parent(f2.id, btn.id))

        # Non-descendant is valid
        self.assertTrue(self.state.is_valid_parent(btn.id, f1.id))

    def test_get_all_descendants_cycle_resilience(self):
        """Even if state had a cycle artificially forced into dict, get_all_descendants does not infinite-loop."""
        w1 = WidgetInstance.create("Frame", 0, 0, name_hint="w1")
        w2 = WidgetInstance.create("Frame", 0, 0, name_hint="w2")
        self.state.widgets[w1.id] = w1
        self.state.widgets[w2.id] = w2
        self.state.widget_order = [w1.id, w2.id]

        # Artificially force a loop: w1 -> w2 -> w1
        w1.parent_id = w2.id
        w2.parent_id = w1.id

        # Must terminate without RecursionError
        descendants = self.state.get_all_descendants(w1.id)
        self.assertTrue(len(descendants) <= 2)


class TestDeepCopyingAndHistoryIsolation(unittest.TestCase):
    """Verifies true deep copying in clipboard, undo/redo snapshots, and duplication."""

    def setUp(self):
        self.state = ProjectState("Deep Copy App", 800, 600)

    def test_clipboard_deep_copy_properties(self):
        """Mutating widget properties after copy does not mutate the clipboard item."""
        combo = WidgetInstance.create("Combobox", 10, 10)
        combo.properties["values"] = ["Alpha", "Beta", "Gamma"]
        combo.properties["nested_config"] = {"theme": "dark", "padding": [5, 10]}
        self.state.add_widget(combo)

        self.state.select_widget(combo.id)
        self.state.copy_selected()

        # Mutate the original widget's nested structures
        combo.properties["values"].append("Delta")
        combo.properties["nested_config"]["theme"] = "light"
        combo.properties["nested_config"]["padding"].append(15)

        # Clipboard must remain pristine
        clipboard_props = self.state._clipboard[0]["properties"]
        self.assertEqual(clipboard_props["values"], ["Alpha", "Beta", "Gamma"])
        self.assertEqual(clipboard_props["nested_config"]["theme"], "dark")
        self.assertEqual(clipboard_props["nested_config"]["padding"], [5, 10])

    def test_clipboard_deep_copy_events(self):
        """Mutating widget events after copy does not mutate the clipboard item."""
        btn = WidgetInstance.create("Button", 10, 10)
        btn.events["command"] = "on_btn_click"
        self.state.add_widget(btn)

        self.state.select_widget(btn.id)
        self.state.copy_selected()

        btn.events["command"] = "modified_handler"
        btn.events["<Button-1>"] = "extra_handler"

        clipboard_events = self.state._clipboard[0]["events"]
        self.assertEqual(clipboard_events["command"], "on_btn_click")
        self.assertNotIn("<Button-1>", clipboard_events)

    def test_paste_produces_independent_deep_copies(self):
        """Pasted widget has independent properties from original and clipboard."""
        notebook = WidgetInstance.create("TNotebook", 10, 10)
        notebook.properties["tabs"] = ["Tab 1", "Tab 2"]
        self.state.add_widget(notebook)

        self.state.select_widget(notebook.id)
        self.state.copy_selected()

        new_ids = self.state.paste()
        pasted = self.state.widgets[new_ids[0]]

        # Mutate pasted
        pasted.properties["tabs"].append("Tab 3")

        # Original widget unchanged
        self.assertEqual(notebook.properties["tabs"], ["Tab 1", "Tab 2"])
        # Clipboard unchanged
        self.assertEqual(self.state._clipboard[0]["properties"]["tabs"], ["Tab 1", "Tab 2"])

    def test_undo_redo_snapshot_isolation(self):
        """Mutating a widget after snapshot or undo does not alter snapshot history."""
        w = WidgetInstance.create("Treeview", 10, 10)
        w.properties["columns"] = ["Name", "Age"]
        self.state.add_widget(w)  # snapshot 1 saved

        # Change properties and push new state
        w.properties["columns"] = ["Name", "Age", "Email"]
        self.state.push_state()  # snapshot 2 saved

        # Undo to snapshot 1
        self.state.undo()
        restored = self.state.widgets[w.id]
        self.assertEqual(restored.properties["columns"], ["Name", "Age"])

        # Mutate restored object
        restored.properties["columns"].append("Corrupted")

        # Redo to snapshot 2
        self.state.redo()
        redo_w = self.state.widgets[w.id]
        self.assertEqual(redo_w.properties["columns"], ["Name", "Age", "Email"])

        # Undo back to snapshot 1 - must still have ["Name", "Age"] without "Corrupted"
        self.state.undo()
        re_restored = self.state.widgets[w.id]
        self.assertEqual(re_restored.properties["columns"], ["Name", "Age"])

    def test_duplicate_preserves_clipboard_and_deep_copies_hierarchy(self):
        """duplicate_selected duplicates container subtree with new IDs, offsets, and doesn't pollute clipboard."""
        frame = WidgetInstance.create("Frame", 50, 50)
        child = WidgetInstance.create("Button", 60, 60)
        child.properties["text"] = "Original"
        self.state.add_widget(frame)
        self.state.add_widget(child, parent_id=frame.id)

        # Set something in clipboard first
        self.state._clipboard = [{"id": "dummy", "widget_type": "Label"}]

        # Duplicate frame (which contains child)
        self.state.select_widget(frame.id)
        new_ids = self.state.duplicate_selected()

        self.assertEqual(len(new_ids), 2)
        dup_frame = next(self.state.widgets[wid] for wid in new_ids if self.state.widgets[wid].widget_type == "Frame")
        dup_child = next(self.state.widgets[wid] for wid in new_ids if self.state.widgets[wid].widget_type == "Button")

        # Child reparented to duplicate frame
        self.assertEqual(dup_child.parent_id, dup_frame.id)
        self.assertEqual(dup_frame.x, 70)
        self.assertEqual(dup_frame.y, 70)
        self.assertEqual(dup_child.x, 80)
        self.assertEqual(dup_child.y, 80)

        # Existing clipboard was preserved
        self.assertEqual(len(self.state._clipboard), 1)
        self.assertEqual(self.state._clipboard[0]["id"], "dummy")

        # Mutating duplicate does not mutate original
        dup_child.properties["text"] = "Modified Duplicate"
        self.assertEqual(child.properties["text"], "Original")


class TestDeepContainerDeletionAndUndo(unittest.TestCase):
    """Verifies that deleting a container Frame with 10 nested children properly cleans up and restores."""

    def setUp(self):
        self.state = ProjectState("Deep Container App", 1000, 800)

    def test_delete_10_nested_children_and_undo_restore(self):
        """Create Frame0 -> Frame1 -> ... -> Frame9 -> Button (11 widgets total). Delete Frame0 and Undo."""
        frames: List[WidgetInstance] = []
        prev_parent_id = None

        # Build 10 nested frames: Frame0 -> Frame1 -> ... -> Frame9
        for i in range(10):
            frame = WidgetInstance.create("Frame", 10 + i * 5, 10 + i * 5, name_hint=f"frame_{i}")
            self.state.add_widget(frame, parent_id=prev_parent_id)
            frames.append(frame)
            prev_parent_id = frame.id

        # Add leaf button inside Frame9
        leaf = WidgetInstance.create("Button", 70, 70, name_hint="leaf_btn")
        self.state.add_widget(leaf, parent_id=frames[-1].id)

        # Add unrelated sibling at root canvas to ensure it's not touched
        sibling = WidgetInstance.create("Label", 300, 300, name_hint="sibling_lbl")
        self.state.add_widget(sibling)

        total_widgets_before = 12  # 10 frames + 1 leaf + 1 sibling
        self.assertEqual(len(self.state.widgets), total_widgets_before)
        self.assertEqual(len(self.state.widget_order), total_widgets_before)

        # Verify all descendants of Frame0
        f0_descendants = self.state.get_all_descendants(frames[0].id)
        self.assertEqual(len(f0_descendants), 10)  # 9 frames + 1 leaf

        # Delete root container Frame0
        self.state.remove_widget(frames[0].id)

        # Everything in Frame0 hierarchy must be cleaned up from widgets and widget_order
        self.assertEqual(len(self.state.widgets), 1)
        self.assertEqual(len(self.state.widget_order), 1)
        self.assertIn(sibling.id, self.state.widgets)
        self.assertEqual(self.state.widget_order, [sibling.id])

        for f in frames:
            self.assertNotIn(f.id, self.state.widgets)
            self.assertNotIn(f.id, self.state.widget_order)
        self.assertNotIn(leaf.id, self.state.widgets)
        self.assertNotIn(leaf.id, self.state.widget_order)

        # UNDO: Verify complete restoration with exact parent-child links intact
        self.assertTrue(self.state.can_undo())
        self.state.undo()

        self.assertEqual(len(self.state.widgets), total_widgets_before)
        self.assertEqual(len(self.state.widget_order), total_widgets_before)

        # Check hierarchy links
        self.assertIsNone(self.state.widgets[frames[0].id].parent_id)
        for i in range(1, 10):
            self.assertEqual(self.state.widgets[frames[i].id].parent_id, frames[i - 1].id)
        self.assertEqual(self.state.widgets[leaf.id].parent_id, frames[-1].id)

        # REDO: Verify deletion re-executed cleanly
        self.assertTrue(self.state.can_redo())
        self.state.redo()
        self.assertEqual(len(self.state.widgets), 1)
        self.assertEqual(self.state.widget_order, [sibling.id])


class TestZOrderManagement(unittest.TestCase):
    """Verifies Z-order and widget_order operations: bring_to_front, send_to_back, bring_forward, send_backward."""

    def setUp(self):
        self.state = ProjectState("ZOrder App", 600, 400)
        self.w1 = WidgetInstance.create("Button", 10, 10, name_hint="w1")
        self.w2 = WidgetInstance.create("Label", 20, 20, name_hint="w2")
        self.w3 = WidgetInstance.create("Entry", 30, 30, name_hint="w3")
        self.state.add_widget(self.w1)
        self.state.add_widget(self.w2)
        self.state.add_widget(self.w3)

    def test_initial_z_order_sync(self):
        """Initial creation synchronizes widget_order and z_order."""
        self.assertEqual(self.state.widget_order, [self.w1.id, self.w2.id, self.w3.id])
        self.assertEqual(self.state.widgets[self.w1.id].z_order, 0)
        self.assertEqual(self.state.widgets[self.w2.id].z_order, 1)
        self.assertEqual(self.state.widgets[self.w3.id].z_order, 2)

    def test_bring_to_front(self):
        """bring_to_front moves item to top of stack and updates z_orders."""
        self.state.bring_to_front(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w2.id, self.w3.id, self.w1.id])
        self.assertEqual(self.state.widgets[self.w2.id].z_order, 0)
        self.assertEqual(self.state.widgets[self.w3.id].z_order, 1)
        self.assertEqual(self.state.widgets[self.w1.id].z_order, 2)

    def test_send_to_back(self):
        """send_to_back moves item to bottom of stack and updates z_orders."""
        self.state.send_to_back(self.w3.id)
        self.assertEqual(self.state.widget_order, [self.w3.id, self.w1.id, self.w2.id])
        self.assertEqual(self.state.widgets[self.w3.id].z_order, 0)
        self.assertEqual(self.state.widgets[self.w1.id].z_order, 1)
        self.assertEqual(self.state.widgets[self.w2.id].z_order, 2)

    def test_bring_forward_and_send_backward(self):
        """bring_forward and send_backward step through the order."""
        # Initial: [w1, w2, w3]
        self.state.bring_forward(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w2.id, self.w1.id, self.w3.id])

        self.state.bring_forward(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w2.id, self.w3.id, self.w1.id])

        # At the top, bring_forward is a no-op
        self.state.bring_forward(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w2.id, self.w3.id, self.w1.id])

        # Step back
        self.state.send_backward(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w2.id, self.w1.id, self.w3.id])

        self.state.send_backward(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w1.id, self.w2.id, self.w3.id])

        # At bottom, send_backward is a no-op
        self.state.send_backward(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w1.id, self.w2.id, self.w3.id])

    def test_container_and_descendants_move_together(self):
        """Moving a container forward or to front preserves its children being on top of it."""
        state = ProjectState("Container Z App", 600, 400)
        frame = WidgetInstance.create("Frame", 10, 10, name_hint="f")
        child1 = WidgetInstance.create("Button", 20, 20, name_hint="c1")
        child2 = WidgetInstance.create("Label", 30, 30, name_hint="c2")
        other = WidgetInstance.create("Entry", 100, 100, name_hint="other")

        state.add_widget(frame)
        state.add_widget(child1, parent_id=frame.id)
        state.add_widget(child2, parent_id=frame.id)
        state.add_widget(other)

        # Initial order: [frame, child1, child2, other]
        self.assertEqual(state.widget_order, [frame.id, child1.id, child2.id, other.id])

        # Bring frame to front: frame and its children must move together past other
        state.bring_to_front(frame.id)
        self.assertEqual(state.widget_order, [other.id, frame.id, child1.id, child2.id])

        # Send frame to back: frame and its children move to beginning together
        state.send_to_back(frame.id)
        self.assertEqual(state.widget_order, [frame.id, child1.id, child2.id, other.id])

    def test_undo_redo_z_order_changes(self):
        """Undoing a Z-order operation restores exact previous order."""
        self.state.bring_to_front(self.w1.id)
        self.assertEqual(self.state.widget_order, [self.w2.id, self.w3.id, self.w1.id])

        self.state.undo()
        self.assertEqual(self.state.widget_order, [self.w1.id, self.w2.id, self.w3.id])
        self.assertEqual(self.state.widgets[self.w1.id].z_order, 0)


class TestJSONSerializationRobustness(unittest.TestCase):
    """Verifies complete serialization across all 42 widget types, menus, special characters, and corruption."""

    def test_serialize_all_42_widget_types(self):
        """Create all 42 widget types, serialize to JSON file, and load back."""
        state = ProjectState("Catalog Project", 1200, 900)
        all_types = list(WIDGET_CATALOG.keys())
        self.assertEqual(len(all_types), 42, f"Expected 42 widget types, got {len(all_types)}")

        created_widgets: List[WidgetInstance] = []
        for i, wtype in enumerate(all_types):
            w = WidgetInstance.create(wtype, (i % 6) * 180, (i // 6) * 70, name_hint=f"widget_{i}")
            state.add_widget(w)
            created_widgets.append(w)

        self.assertEqual(len(state.widgets), 42)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "all_widgets.pgproj")
            ProjectSerializer.save_to_file(state, file_path)
            self.assertTrue(os.path.exists(file_path))

            loaded_state = ProjectSerializer.load_from_file(file_path)
            self.assertEqual(len(loaded_state.widgets), 42)
            self.assertEqual(loaded_state.widget_order, state.widget_order)

            for original_w in created_widgets:
                self.assertIn(original_w.id, loaded_state.widgets)
                loaded_w = loaded_state.widgets[original_w.id]
                self.assertEqual(loaded_w.widget_type, original_w.widget_type)
                self.assertEqual(loaded_w.x, original_w.x)
                self.assertEqual(loaded_w.y, original_w.y)
                self.assertEqual(loaded_w.width, original_w.width)
                self.assertEqual(loaded_w.height, original_w.height)

    def test_special_characters_escaping(self):
        """Quotes, backslashes, tabs, newlines, and unicode survive serialization cleanly."""
        state = ProjectState("Special Chars App \" ' \\ \n \t 🚀", 700, 500)
        complex_text = "Line 1\nLine 2 with \"double quotes\" and 'single' and \\backslashes\\ and \t tabs and unicode: 🚀 日本語 €"
        w = WidgetInstance.create("Label", 20, 20)
        w.properties["text"] = complex_text
        w.properties["regex_pattern"] = r"^[\w\.-]+@[\w\.-]+\.\w{2,}$"
        w.events["command"] = "on_special_click(\"arg1\", '\\path\\to\\file')"
        state.add_widget(w)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "special.pgproj")
            ProjectSerializer.save_to_file(state, file_path)

            loaded_state = ProjectSerializer.load_from_file(file_path)
            loaded_w = loaded_state.widgets[w.id]

            self.assertEqual(loaded_state.title, "Special Chars App \" ' \\ \n \t 🚀")
            self.assertEqual(loaded_w.properties["text"], complex_text)
            self.assertEqual(loaded_w.properties["regex_pattern"], r"^[\w\.-]+@[\w\.-]+\.\w{2,}$")
            self.assertEqual(loaded_w.events["command"], "on_special_click(\"arg1\", '\\path\\to\\file')")

    def test_menus_and_popup_menus_serialization(self):
        """Menubars and popup menus with nested cascades and options round-trip cleanly."""
        state = ProjectState("Menu App", 600, 400)

        # Build main menubar with nested cascade
        sub_item1 = MenuItemSpec(id="s1", label="Sub item 1", command="on_sub1")
        sub_item2 = MenuItemSpec(id="s2", label="Check item", item_type="checkbutton", variable="chk_var")
        cascade_menu = MenuItemSpec(id="c1", label="More", item_type="cascade", children=[sub_item1, sub_item2])
        file_item = MenuItemSpec(id="f1", label="Open", command="on_open", accelerator="Ctrl+O")
        sep = MenuItemSpec(id="sep1", item_type="separator")

        menubar = MenuBarSpec(id="mb1", name="MainMenuBar", items=[file_item, sep, cascade_menu])
        state.menus["main_menu"] = menubar

        # Build popup menu
        pop_item = MenuItemSpec(id="p1", label="Context Action", command="on_ctx")
        popup = MenuBarSpec(id="pop1", name="ContextPopup", items=[pop_item])
        state.popup_menus["context_menu"] = popup

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "menus.pgproj")
            ProjectSerializer.save_to_file(state, file_path)

            loaded_state = ProjectSerializer.load_from_file(file_path)
            self.assertIn("main_menu", loaded_state.menus)
            self.assertIn("context_menu", loaded_state.popup_menus)

            loaded_mb = loaded_state.menus["main_menu"]
            self.assertEqual(len(loaded_mb.items), 3)
            self.assertEqual(loaded_mb.items[0].label, "Open")
            self.assertEqual(loaded_mb.items[0].accelerator, "Ctrl+O")
            self.assertEqual(loaded_mb.items[1].item_type, "separator")
            self.assertEqual(loaded_mb.items[2].item_type, "cascade")
            self.assertEqual(len(loaded_mb.items[2].children), 2)
            self.assertEqual(loaded_mb.items[2].children[1].item_type, "checkbutton")

    def test_corrupt_parent_id_repair(self):
        """Serializer repairs dangling or self-referential or circular parent_id when loading."""
        data = {
            "format": "pagestudio",
            "version": "1.0.0",
            "window": {"title": "Repaired App", "width": 600, "height": 400},
            "widgets": [
                # w1 has dangling parent_id (pointing to non-existent 'phantom')
                {"id": "w1", "widget_type": "Button", "name": "btn1", "x": 0, "y": 0, "width": 100, "height": 30, "parent_id": "phantom"},
                # w2 has self-referential parent_id
                {"id": "w2", "widget_type": "Label", "name": "lbl2", "x": 0, "y": 0, "width": 100, "height": 30, "parent_id": "w2"},
                # w3 and w4 have circular parent_id: w3 -> w4 -> w3
                {"id": "w3", "widget_type": "Frame", "name": "f3", "x": 0, "y": 0, "width": 100, "height": 30, "parent_id": "w4"},
                {"id": "w4", "widget_type": "Frame", "name": "f4", "x": 0, "y": 0, "width": 100, "height": 30, "parent_id": "w3"},
            ]
        }
        loaded_state = ProjectSerializer.from_dict(data)

        # Dangling and self-referential parent IDs must be repaired to None
        self.assertIsNone(loaded_state.widgets["w1"].parent_id)
        self.assertIsNone(loaded_state.widgets["w2"].parent_id)

        # Circular parent reference must be broken
        cycle_parents = [loaded_state.widgets["w3"].parent_id, loaded_state.widgets["w4"].parent_id]
        self.assertTrue(None in cycle_parents, "At least one parent_id in cycle must be broken to None")

    def test_null_fields_tolerance(self):
        """Serializer tolerates JSON with null values for menus, popup_menus, widgets, canvas."""
        data = {
            "format": "pagestudio",
            "version": "1.0.0",
            "window": None,
            "canvas": None,
            "menus": None,
            "popup_menus": None,
            "widgets": None
        }
        loaded_state = ProjectSerializer.from_dict(data)
        self.assertEqual(loaded_state.title, "My Application")
        self.assertEqual(len(loaded_state.widgets), 0)
        self.assertEqual(len(loaded_state.menus), 0)
        self.assertEqual(len(loaded_state.popup_menus), 0)

    def test_save_creates_nested_directory(self):
        """Saving to a path where parent folders do not exist automatically creates them."""
        state = ProjectState("Dir Test", 400, 300)
        with tempfile.TemporaryDirectory() as tmpdir:
            deep_path = os.path.join(tmpdir, "level1", "level2", "subfolder", "project.pgproj")
            ProjectSerializer.save_to_file(state, deep_path)
            self.assertTrue(os.path.exists(deep_path))

    def test_loaded_project_initial_undo_state(self):
        """Loading a project sets initial state so can_undo is False until an edit is made."""
        state = ProjectState("Original", 500, 400)
        w = WidgetInstance.create("Button", 10, 10)
        state.add_widget(w)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "initial.pgproj")
            ProjectSerializer.save_to_file(state, file_path)

            loaded = ProjectSerializer.load_from_file(file_path)
            self.assertFalse(loaded.can_undo(), "Loaded project should not allow undoing to empty state")
            self.assertFalse(loaded.can_redo())

            # Making a modification allows undo
            loaded.remove_widget(w.id)
            self.assertTrue(loaded.can_undo())
            loaded.undo()
            self.assertIn(w.id, loaded.widgets)


if __name__ == "__main__":
    unittest.main()
