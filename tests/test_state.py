"""Tests for project state and undo/redo operations in PageStudio."""
import unittest
from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance, MenuBarSpec, MenuItemSpec

class TestProjectState(unittest.TestCase):

    def test_state_init(self):
        state = ProjectState("Test App", 800, 600)
        self.assertEqual(state.title, "Test App")
        self.assertEqual(state.width, 800)
        self.assertEqual(state.height, 600)
        self.assertEqual(len(state.widgets), 0)
        self.assertEqual(len(state.menus), 0)
        self.assertEqual(len(state.popup_menus), 0)
        self.assertFalse(state.is_relative_mode)
        self.assertEqual(len(state._clipboard), 0)

    def test_add_and_remove_widget(self):
        state = ProjectState()
        w = WidgetInstance.create("Button", 10, 20)
        state.add_widget(w)
        self.assertIn(w.id, state.widgets)
        self.assertEqual(state.selected_ids, [w.id])

        state.remove_widget(w.id)
        self.assertNotIn(w.id, state.widgets)
        self.assertEqual(len(state.selected_ids), 0)

    def test_hierarchy_and_recursive_deletion(self):
        """Test parent-child hierarchy tracking and recursive removal of descendants."""
        state = ProjectState()
        f1 = WidgetInstance.create("Frame", 20, 20)
        state.add_widget(f1)

        b1 = WidgetInstance.create("Button", 30, 30)
        state.add_widget(b1, parent_id=f1.id)
        self.assertEqual(b1.parent_id, f1.id)

        e1 = WidgetInstance.create("Entry", 30, 70)
        state.add_widget(e1, parent_id=f1.id)

        # Grandchild
        lbl = WidgetInstance.create("Label", 35, 35)
        state.add_widget(lbl, parent_id=b1.id)

        # Check get_children
        root_children = state.get_children(None)
        self.assertEqual([w.id for w in root_children], [f1.id])

        f1_children = state.get_children(f1.id)
        self.assertEqual(sorted([w.id for w in f1_children]), sorted([b1.id, e1.id]))

        # Check get_all_descendants
        f1_descendants = state.get_all_descendants(f1.id)
        self.assertEqual(len(f1_descendants), 3)
        self.assertEqual(sorted([d.id for d in f1_descendants]), sorted([b1.id, e1.id, lbl.id]))

        # Removing f1 should delete f1 AND b1, e1, lbl
        state.remove_widget(f1.id)
        self.assertEqual(len(state.widgets), 0)
        self.assertEqual(len(state.widget_order), 0)
        self.assertEqual(len(state.selected_ids), 0)

        # Undo should restore all 4 with parent-child links intact
        self.assertTrue(state.can_undo())
        state.undo()
        self.assertEqual(len(state.widgets), 4)
        self.assertIn(f1.id, state.widgets)
        self.assertEqual(state.widgets[b1.id].parent_id, f1.id)
        self.assertEqual(state.widgets[lbl.id].parent_id, b1.id)

    def test_remove_selected_recursive(self):
        """Ensure remove_selected also deletes descendants recursively."""
        state = ProjectState()
        f1 = WidgetInstance.create("TFrame", 10, 10)
        state.add_widget(f1)
        b1 = WidgetInstance.create("TButton", 20, 20)
        state.add_widget(b1, parent_id=f1.id)

        state.select_widget(f1.id)
        state.remove_selected()
        self.assertEqual(len(state.widgets), 0)

    def test_clipboard_copy_cut_paste(self):
        """Verify copy, cut, and paste preserve hierarchy, assign new UUIDs, and apply offsets."""
        state = ProjectState()
        f1 = WidgetInstance.create("Frame", 40, 50)
        state.add_widget(f1)
        b1 = WidgetInstance.create("Button", 50, 60)
        state.add_widget(b1, parent_id=f1.id)

        # Select the container and copy
        state.select_widget(f1.id)
        state.copy_selected()
        self.assertEqual(len(state._clipboard), 2)

        # Paste with (30, 40) offset
        new_ids = state.paste(offset=(30, 40))
        self.assertEqual(len(new_ids), 2)
        self.assertEqual(len(state.widgets), 4)

        # Find the pasted container and child
        pasted_f1 = next(state.widgets[wid] for wid in new_ids if state.widgets[wid].widget_type == "Frame")
        pasted_b1 = next(state.widgets[wid] for wid in new_ids if state.widgets[wid].widget_type == "Button")

        self.assertNotEqual(pasted_f1.id, f1.id)
        self.assertNotEqual(pasted_b1.id, b1.id)
        # Position offset verified
        self.assertEqual(pasted_f1.x, 70)
        self.assertEqual(pasted_f1.y, 90)
        self.assertEqual(pasted_b1.x, 80)
        self.assertEqual(pasted_b1.y, 100)
        # Hierarchy link re-pointed to new parent
        self.assertEqual(pasted_b1.parent_id, pasted_f1.id)

        # Now test cut
        state.select_widget(pasted_b1.id)
        state.cut_selected()
        self.assertNotIn(pasted_b1.id, state.widgets)
        self.assertEqual(len(state._clipboard), 1)
        self.assertEqual(state._clipboard[0]["widget_type"], "Button")

        # Paste cut widget
        pasted_back_ids = state.paste(offset=(10, 10))
        self.assertEqual(len(pasted_back_ids), 1)
        self.assertIn(pasted_back_ids[0], state.widgets)

    def test_locking(self):
        """Verify locking prevents geometry updates and toggles cleanly."""
        state = ProjectState()
        w = WidgetInstance.create("Entry", 50, 50)
        state.add_widget(w)
        state.select_widget(w.id)
        self.assertFalse(w.locked)

        # Toggle lock on
        state.toggle_lock_selected()
        self.assertTrue(w.locked)

        # Geometry changes must be blocked when locked
        state.update_widget_geometry(w.id, 100, 100, 200, 40)
        self.assertEqual(w.x, 50)
        self.assertEqual(w.y, 50)

        # Toggle lock off
        state.toggle_lock_selected()
        self.assertFalse(w.locked)

        # Geometry changes should now succeed
        state.update_widget_geometry(w.id, 100, 100, 200, 40)
        self.assertEqual(w.x, 100)
        self.assertEqual(w.y, 100)

    def test_fill_parent_container(self):
        """Verify fill_parent_container expands widget to container (or canvas)."""
        state = ProjectState("Fill App", 600, 400)
        
        # Test 1: Fill root canvas
        root_btn = WidgetInstance.create("Button", 10, 10)
        state.add_widget(root_btn)
        state.fill_parent_container(root_btn.id)
        self.assertEqual(root_btn.x, 0)
        self.assertEqual(root_btn.y, 0)
        self.assertEqual(root_btn.width, 600)
        self.assertEqual(root_btn.height, 400)
        self.assertEqual(root_btn.rel_width, 1.0)
        self.assertEqual(root_btn.rel_height, 1.0)

        # Test 2: Fill container frame
        frame = WidgetInstance.create("Frame", 40, 50)
        frame.width = 300
        frame.height = 200
        state.add_widget(frame)

        child_btn = WidgetInstance.create("Button", 10, 10)
        state.add_widget(child_btn, parent_id=frame.id)
        state.fill_parent_container(child_btn.id)
        self.assertEqual(child_btn.x, frame.x)
        self.assertEqual(child_btn.y, frame.y)
        self.assertEqual(child_btn.width, frame.width)
        self.assertEqual(child_btn.height, frame.height)

    def test_menus_and_snapshots_undo_redo(self):
        """Ensure menus and relative mode are stored in undo/redo snapshots."""
        state = ProjectState()
        item = MenuItemSpec(id="i1", label="Exit", command="on_exit")
        menu = MenuBarSpec(id="m1", name="File", items=[item])
        state.menus["main_menu"] = menu
        state.is_relative_mode = True
        state.push_state()

        self.assertIn("main_menu", state.menus)
        self.assertTrue(state.is_relative_mode)

        # Undo
        state.undo()
        self.assertEqual(len(state.menus), 0)
        self.assertFalse(state.is_relative_mode)

        # Redo
        state.redo()
        self.assertIn("main_menu", state.menus)
        self.assertEqual(state.menus["main_menu"].name, "File")
        self.assertTrue(state.is_relative_mode)

    def test_undo_redo(self):
        state = ProjectState()
        self.assertFalse(state.can_undo())

        w1 = WidgetInstance.create("Label", 10, 10)
        state.add_widget(w1)
        self.assertTrue(state.can_undo())
        self.assertEqual(len(state.widgets), 1)

        # Undo addition
        state.undo()
        self.assertEqual(len(state.widgets), 0)
        self.assertTrue(state.can_redo())

        # Redo addition
        state.redo()
        self.assertEqual(len(state.widgets), 1)
        self.assertIn(w1.id, state.widgets)

    def test_duplicate(self):
        state = ProjectState()
        w1 = WidgetInstance.create("Button", 10, 10)
        state.add_widget(w1)
        state.select_widget(w1.id)
        state.duplicate_selected()

        self.assertEqual(len(state.widgets), 2)
        # Verify duplicate is offset
        duplicated = state.get_selected_widget()
        self.assertIsNotNone(duplicated)
        self.assertEqual(duplicated.x, 30)
        self.assertEqual(duplicated.y, 30)

if __name__ == "__main__":
    unittest.main()
