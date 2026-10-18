"""Tests for project state and undo/redo operations in PageStudio."""
import unittest
from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance

class TestProjectState(unittest.TestCase):

    def test_state_init(self):
        state = ProjectState("Test App", 800, 600)
        self.assertEqual(state.title, "Test App")
        self.assertEqual(state.width, 800)
        self.assertEqual(state.height, 600)
        self.assertEqual(len(state.widgets), 0)

    def test_add_and_remove_widget(self):
        state = ProjectState()
        w = WidgetInstance.create("Button", 10, 20)
        state.add_widget(w)
        self.assertIn(w.id, state.widgets)
        self.assertEqual(state.selected_ids, [w.id])

        state.remove_widget(w.id)
        self.assertNotIn(w.id, state.widgets)
        self.assertEqual(len(state.selected_ids), 0)

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
