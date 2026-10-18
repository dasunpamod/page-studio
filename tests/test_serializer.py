"""Tests for project serialization and file round-tripping."""
import unittest
import tempfile
import os
from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance
from pagestudio.core.serializer import ProjectSerializer

class TestProjectSerializer(unittest.TestCase):

    def test_save_and_load(self):
        state = ProjectState("My Test Project", 640, 480)
        w1 = WidgetInstance.create("Button", 20, 30)
        w2 = WidgetInstance.create("Entry", 20, 80)
        state.add_widget(w1)
        state.add_widget(w2)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.pgproj")
            ProjectSerializer.save_to_file(state, file_path)

            loaded_state = ProjectSerializer.load_from_file(file_path)
            self.assertEqual(loaded_state.title, "My Test Project")
            self.assertEqual(loaded_state.width, 640)
            self.assertEqual(loaded_state.height, 480)
            self.assertEqual(len(loaded_state.widgets), 2)
            self.assertIn(w1.id, loaded_state.widgets)
            self.assertIn(w2.id, loaded_state.widgets)

if __name__ == "__main__":
    unittest.main()
