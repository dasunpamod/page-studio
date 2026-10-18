"""
Unit Tests for PageStudio Hierarchy, Relative Coordinates, and Recursive Deletion.
Validates:
1. Parent-child container relationships & multi-level nesting
2. Relative coordinate calculation (for root canvas and nested containers)
3. Recursive deletion of container subtrees (including undo/redo and clipboard cut/paste)
"""

import unittest

from pagestudio.core.models import WidgetInstance, WIDGET_CATALOG
from pagestudio.core.state import ProjectState
from pagestudio.core.generator import CodeGenerator


class TestParentChildHierarchy(unittest.TestCase):
    """Tests for parent-child container relationships."""

    def setUp(self):
        self.state = ProjectState("Hierarchy App", width=800, height=600)

    def test_container_and_leaf_catalog_flags(self):
        """Verify all container types have is_container=True and leaf types have False."""
        container_types = ["Frame", "LabelFrame", "TFrame", "TLabelframe", "TNotebook", "TPanedwindow", "Canvas"]
        for ctype in container_types:
            self.assertIn(ctype, WIDGET_CATALOG)
            self.assertTrue(WIDGET_CATALOG[ctype].is_container, f"{ctype} should be flagged as container")

        leaf_types = ["Button", "Entry", "Label", "Checkbutton", "Radiobutton", "TButton", "TEntry", "TLabel"]
        for ltype in leaf_types:
            self.assertIn(ltype, WIDGET_CATALOG)
            self.assertFalse(WIDGET_CATALOG[ltype].is_container, f"{ltype} should be flagged as leaf")

    def test_direct_children_and_root_children(self):
        """Verify get_children returns direct children for both root and containers."""
        # Root level widgets
        root_btn = WidgetInstance.create("Button", 10, 10, name_hint="root_btn")
        self.state.add_widget(root_btn)

        outer_frame = WidgetInstance.create("Frame", 40, 40, name_hint="outer_frame")
        self.state.add_widget(outer_frame)

        # Children under outer_frame
        child_btn = WidgetInstance.create("Button", 50, 50, name_hint="child_btn")
        self.state.add_widget(child_btn, parent_id=outer_frame.id)

        child_entry = WidgetInstance.create("Entry", 50, 90, name_hint="child_entry")
        self.state.add_widget(child_entry, parent_id=outer_frame.id)

        # Verify root children
        root_children = self.state.get_children(None)
        root_ids = [w.id for w in root_children]
        self.assertEqual(len(root_ids), 2)
        self.assertIn(root_btn.id, root_ids)
        self.assertIn(outer_frame.id, root_ids)
        self.assertNotIn(child_btn.id, root_ids)
        self.assertNotIn(child_entry.id, root_ids)

        # Verify outer_frame children
        frame_children = self.state.get_children(outer_frame.id)
        frame_ids = [w.id for w in frame_children]
        self.assertEqual(len(frame_ids), 2)
        self.assertIn(child_btn.id, frame_ids)
        self.assertIn(child_entry.id, frame_ids)

    def test_multilevel_nested_hierarchy_descendants(self):
        """Verify get_all_descendants traverses multiple nesting levels correctly."""
        # Level 0: Root -> Level 1: Frame1 -> Level 2: Frame2 -> Level 3: Button
        frame1 = WidgetInstance.create("TFrame", 20, 20, name_hint="frame1")
        self.state.add_widget(frame1)

        frame2 = WidgetInstance.create("TLabelframe", 40, 40, name_hint="frame2")
        self.state.add_widget(frame2, parent_id=frame1.id)

        leaf_btn = WidgetInstance.create("TButton", 60, 60, name_hint="deep_btn")
        self.state.add_widget(leaf_btn, parent_id=frame2.id)

        sibling_lbl = WidgetInstance.create("TLabel", 60, 100, name_hint="deep_lbl")
        self.state.add_widget(sibling_lbl, parent_id=frame2.id)

        # Descendants of frame2 (Level 2)
        desc_f2 = self.state.get_all_descendants(frame2.id)
        self.assertEqual(len(desc_f2), 2)
        self.assertEqual(sorted([w.id for w in desc_f2]), sorted([leaf_btn.id, sibling_lbl.id]))

        # Descendants of frame1 (Level 1)
        desc_f1 = self.state.get_all_descendants(frame1.id)
        self.assertEqual(len(desc_f1), 3)
        self.assertEqual(sorted([w.id for w in desc_f1]), sorted([frame2.id, leaf_btn.id, sibling_lbl.id]))

    def test_reparenting_widget(self):
        """Verify reparenting a child to a different container updates hierarchy."""
        f1 = WidgetInstance.create("Frame", 10, 10, name_hint="f1")
        f2 = WidgetInstance.create("Frame", 200, 10, name_hint="f2")
        btn = WidgetInstance.create("Button", 20, 20, name_hint="moving_btn")

        self.state.add_widget(f1)
        self.state.add_widget(f2)
        self.state.add_widget(btn, parent_id=f1.id)

        self.assertEqual(btn.parent_id, f1.id)
        self.assertEqual(len(self.state.get_children(f1.id)), 1)
        self.assertEqual(len(self.state.get_children(f2.id)), 0)

        # Reparent to f2
        btn.parent_id = f2.id
        self.state.push_state()

        self.assertEqual(len(self.state.get_children(f1.id)), 0)
        self.assertEqual(len(self.state.get_children(f2.id)), 1)
        self.assertEqual(self.state.get_children(f2.id)[0].id, btn.id)


class TestRelativeCoordinateCalculation(unittest.TestCase):
    """Tests for relative coordinate calculation and mode transitions."""

    def setUp(self):
        self.state = ProjectState("Relative Test App", width=800, height=600)

    def test_calculate_relative_coordinates_root(self):
        """Test relative coordinate calculation for root canvas widget."""
        w = WidgetInstance.create("Button", 100, 150)
        w.width = 200
        w.height = 60
        self.state.add_widget(w)

        rel = self.state.calculate_relative_coordinates(w.id)
        # Expected:
        # rel_x = 100 / 800 = 0.125
        # rel_y = 150 / 600 = 0.25
        # rel_w = 200 / 800 = 0.25
        # rel_h = 60 / 600 = 0.1
        self.assertAlmostEqual(rel[0], 0.125, places=3)
        self.assertAlmostEqual(rel[1], 0.25, places=3)
        self.assertAlmostEqual(rel[2], 0.25, places=3)
        self.assertAlmostEqual(rel[3], 0.1, places=3)

        self.assertAlmostEqual(w.rel_x, 0.125, places=3)
        self.assertAlmostEqual(w.rel_y, 0.25, places=3)
        self.assertAlmostEqual(w.rel_width, 0.25, places=3)
        self.assertAlmostEqual(w.rel_height, 0.1, places=3)

    def test_calculate_relative_coordinates_nested_container(self):
        """Test relative coordinate calculation for child inside container."""
        # Container at (100, 100) with size (400, 200)
        parent = WidgetInstance.create("Frame", 100, 100)
        parent.width = 400
        parent.height = 200
        self.state.add_widget(parent)

        # Child at (140, 150) with size (100, 40)
        # Offset inside container: x_offset = 40, y_offset = 50
        # rel_x = 40 / 400 = 0.1
        # rel_y = 50 / 200 = 0.25
        # rel_w = 100 / 400 = 0.25
        # rel_h = 40 / 200 = 0.2
        child = WidgetInstance.create("Button", 140, 150)
        child.width = 100
        child.height = 40
        self.state.add_widget(child, parent_id=parent.id)

        rel = self.state.calculate_relative_coordinates(child.id)
        self.assertAlmostEqual(rel[0], 0.1, places=3)
        self.assertAlmostEqual(rel[1], 0.25, places=3)
        self.assertAlmostEqual(rel[2], 0.25, places=3)
        self.assertAlmostEqual(rel[3], 0.2, places=3)

    def test_calculate_absolute_coordinates_from_relative(self):
        """Test reconstructing absolute coordinates from relative fractions."""
        parent = WidgetInstance.create("Frame", 100, 100)
        parent.width = 400
        parent.height = 200
        self.state.add_widget(parent)

        child = WidgetInstance.create("Button", 0, 0)
        child.rel_x = 0.25
        child.rel_y = 0.50
        child.rel_width = 0.50
        child.rel_height = 0.25
        self.state.add_widget(child, parent_id=parent.id)

        abs_geom = self.state.calculate_absolute_coordinates(child.id)
        # Expected:
        # x = 100 + 0.25 * 400 = 200
        # y = 100 + 0.50 * 200 = 200
        # width = 0.50 * 400 = 200
        # height = 0.25 * 200 = 50
        self.assertEqual(abs_geom[0], 200)
        self.assertEqual(abs_geom[1], 200)
        self.assertEqual(abs_geom[2], 200)
        self.assertEqual(abs_geom[3], 50)

    def test_set_relative_mode(self):
        """Test enabling relative mode converts all widgets to relative."""
        self.assertFalse(self.state.is_relative_mode)

        w1 = WidgetInstance.create("Button", 80, 60)
        w1.width = 160
        w1.height = 40
        self.state.add_widget(w1)
        self.assertFalse(w1.is_relative)

        # Toggle relative mode
        self.state.set_relative_mode(True)
        self.assertTrue(self.state.is_relative_mode)
        self.assertTrue(w1.is_relative)
        self.assertAlmostEqual(w1.rel_x, 80 / 800, places=3)
        self.assertAlmostEqual(w1.rel_y, 60 / 600, places=3)
        self.assertAlmostEqual(w1.rel_width, 160 / 800, places=3)
        self.assertAlmostEqual(w1.rel_height, 40 / 600, places=3)

        # Add widget while relative mode is on
        w2 = WidgetInstance.create("Label", 200, 300)
        self.state.add_widget(w2)
        self.assertTrue(w2.is_relative)
        self.assertIsNotNone(w2.rel_x)
        self.assertIsNotNone(w2.rel_y)

    def test_relative_code_generation(self):
        """Test CodeGenerator outputs place(relx=..., rely=...) for relative widgets."""
        w = WidgetInstance.create("Button", 100, 100, name_hint="rel_btn")
        w.is_relative = True
        w.rel_x = 0.2
        w.rel_y = 0.3
        w.rel_width = 0.4
        w.rel_height = 0.1
        self.state.add_widget(w)

        code = CodeGenerator.generate_gui_code(self.state, "test_app", "test_app_support")
        self.assertIn("self.rel_btn.place(", code)
        self.assertIn("relx=0.2000", code)
        self.assertIn("rely=0.3000", code)
        self.assertIn("relwidth=0.4000", code)
        self.assertIn("relheight=0.1000", code)


class TestRecursiveDeletion(unittest.TestCase):
    """Tests for recursive deletion of container hierarchies."""

    def setUp(self):
        self.state = ProjectState("Deletion Test App", width=600, height=400)

    def test_recursive_remove_widget(self):
        """Verify removing a parent container deletes it and all nested descendants."""
        # Tree:
        # root_sibling
        # outer_frame
        #   ├── child_btn
        #   └── inner_frame
        #         └── grandchild_entry
        root_sibling = WidgetInstance.create("Label", 10, 10, name_hint="sibling")
        self.state.add_widget(root_sibling)

        outer_frame = WidgetInstance.create("Frame", 30, 30, name_hint="outer")
        self.state.add_widget(outer_frame)

        child_btn = WidgetInstance.create("Button", 40, 40, name_hint="btn")
        self.state.add_widget(child_btn, parent_id=outer_frame.id)

        inner_frame = WidgetInstance.create("Frame", 40, 80, name_hint="inner")
        self.state.add_widget(inner_frame, parent_id=outer_frame.id)

        grandchild_entry = WidgetInstance.create("Entry", 50, 90, name_hint="entry")
        self.state.add_widget(grandchild_entry, parent_id=inner_frame.id)

        self.assertEqual(len(self.state.widgets), 5)
        self.assertEqual(len(self.state.widget_order), 5)

        # Delete outer_frame
        self.state.remove_widget(outer_frame.id)

        # outer_frame, child_btn, inner_frame, grandchild_entry must be gone
        self.assertEqual(len(self.state.widgets), 1)
        self.assertIn(root_sibling.id, self.state.widgets)
        self.assertEqual(self.state.widget_order, [root_sibling.id])

        self.assertNotIn(outer_frame.id, self.state.widgets)
        self.assertNotIn(child_btn.id, self.state.widgets)
        self.assertNotIn(inner_frame.id, self.state.widgets)
        self.assertNotIn(grandchild_entry.id, self.state.widgets)

    def test_recursive_remove_selected(self):
        """Verify remove_selected deletes container and all descendants."""
        f = WidgetInstance.create("Frame", 10, 10)
        self.state.add_widget(f)

        b = WidgetInstance.create("Button", 20, 20)
        self.state.add_widget(b, parent_id=f.id)

        e = WidgetInstance.create("Entry", 20, 50)
        self.state.add_widget(e, parent_id=f.id)

        self.assertEqual(len(self.state.widgets), 3)

        # Select the container and remove selected
        self.state.select_widget(f.id)
        self.state.remove_selected()

        self.assertEqual(len(self.state.widgets), 0)
        self.assertEqual(len(self.state.widget_order), 0)
        self.assertEqual(len(self.state.selected_ids), 0)

    def test_undo_and_redo_recursive_deletion(self):
        """Verify undo restores the entire deleted subtree with hierarchy links intact."""
        f = WidgetInstance.create("Frame", 10, 10, name_hint="f_undo")
        self.state.add_widget(f)

        b = WidgetInstance.create("Button", 20, 20, name_hint="b_undo")
        self.state.add_widget(b, parent_id=f.id)

        # Delete container
        self.state.remove_widget(f.id)
        self.assertEqual(len(self.state.widgets), 0)

        # Undo
        self.assertTrue(self.state.can_undo())
        self.state.undo()
        self.assertEqual(len(self.state.widgets), 2)
        self.assertIn(f.id, self.state.widgets)
        self.assertIn(b.id, self.state.widgets)
        self.assertEqual(self.state.widgets[b.id].parent_id, f.id)

        # Redo
        self.assertTrue(self.state.can_redo())
        self.state.redo()
        self.assertEqual(len(self.state.widgets), 0)

    def test_cut_and_paste_container_hierarchy(self):
        """Verify cut removes container and all children, and paste recreates subtree."""
        f = WidgetInstance.create("Frame", 40, 40)
        self.state.add_widget(f)

        b = WidgetInstance.create("Button", 50, 50)
        self.state.add_widget(b, parent_id=f.id)

        self.state.select_widget(f.id)
        self.state.cut_selected()

        # Cut removed both
        self.assertEqual(len(self.state.widgets), 0)
        self.assertEqual(len(self.state._clipboard), 2)

        # Paste back with offset
        new_ids = self.state.paste(offset=(30, 30))
        self.assertEqual(len(new_ids), 2)
        self.assertEqual(len(self.state.widgets), 2)

        pasted_f = next(self.state.widgets[wid] for wid in new_ids if self.state.widgets[wid].widget_type == "Frame")
        pasted_b = next(self.state.widgets[wid] for wid in new_ids if self.state.widgets[wid].widget_type == "Button")

        self.assertEqual(pasted_b.parent_id, pasted_f.id)
        self.assertEqual(pasted_f.x, 70)
        self.assertEqual(pasted_f.y, 70)
        self.assertEqual(pasted_b.x, 80)
        self.assertEqual(pasted_b.y, 80)


if __name__ == "__main__":
    unittest.main()
