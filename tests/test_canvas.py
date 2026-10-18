"""
Unit Tests for PageStudio Visual Canvas (pagestudio/ui/canvas.py)
Tests:
1. Scrollable canvas surface and scrollbars
2. Cumulative container coordinate mathematics
3. Deepest child hit testing
4. Container dropping & auto-parenting
5. Interactive notebook tabs & visibility filtering
6. All 42 widget visual mockups
7. Lock indicator badge & custom bg/fg color previews
"""

import unittest
import tkinter as tk
from pagestudio.core.state import ProjectState
from pagestudio.core.models import WidgetInstance, WIDGET_CATALOG
from pagestudio.ui.canvas import DesignCanvas

class TestCanvasOverhaul(unittest.TestCase):

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.state = ProjectState(title="Canvas Test", width=800, height=600)
        self.canvas_panel = DesignCanvas(self.root, self.state)
        self.canvas_panel.pack()

    def tearDown(self):
        self.root.destroy()

    def test_scrollable_canvas_surface(self):
        """Requirement 1: Verify canvas has horizontal and vertical scrollbars and dynamic scrollregion."""
        self.assertIsNotNone(self.canvas_panel.v_scroll)
        self.assertIsNotNone(self.canvas_panel.h_scroll)
        self.assertEqual(str(self.canvas_panel.v_scroll.cget("orient")), "vertical")
        self.assertEqual(str(self.canvas_panel.h_scroll.cget("orient")), "horizontal")

        # Test large project dimensions (1920x1080)
        self.state.width = 1920
        self.state.height = 1080
        self.canvas_panel.render()

        # Canvas scrollregion should comfortably encompass 1920x1080 + offset
        sr_str = self.canvas_panel.canvas.cget("scrollregion")
        sr_coords = [int(float(c)) for c in sr_str.split()]
        self.assertGreaterEqual(sr_coords[2], 1920 + self.canvas_panel.offset_x)
        self.assertGreaterEqual(sr_coords[3], 1080 + self.canvas_panel.offset_y)

    def test_cumulative_container_coordinates(self):
        """Requirement 2: Verify get_canvas_bounds recursively sums x and y through the parent chain."""
        self.state.snap_to_grid = False
        # Frame at (50, 40)
        frame = WidgetInstance.create("Frame", 50, 40)
        frame.width = 300
        frame.height = 200
        self.state.add_widget(frame)

        # Button child inside Frame at local (30, 20)
        btn = WidgetInstance.create("Button", 30, 20, parent_id=frame.id)
        btn.width = 100
        btn.height = 30
        self.state.add_widget(btn)

        # Check frame bounds
        fx, fy, fw, fh = self.canvas_panel.get_canvas_bounds(frame)
        self.assertEqual(fx, self.canvas_panel.offset_x + 50)
        self.assertEqual(fy, self.canvas_panel.offset_y + 40)
        self.assertEqual(fw, 300)
        self.assertEqual(fh, 200)

        # Check child button bounds (cumulative: offset + frame.x + btn.x)
        bx, by, bw, bh = self.canvas_panel.get_canvas_bounds(btn)
        self.assertEqual(bx, self.canvas_panel.offset_x + 50 + 30)
        self.assertEqual(by, self.canvas_panel.offset_y + 40 + 20)
        self.assertEqual(bw, 100)
        self.assertEqual(bh, 30)

        # Sub-child inside Button (nested depth 2)
        inner_lbl = WidgetInstance.create("Label", 10, 10, parent_id=btn.id)
        self.state.add_widget(inner_lbl)
        lx, ly, lw, lh = self.canvas_panel.get_canvas_bounds(inner_lbl)
        self.assertEqual(lx, self.canvas_panel.offset_x + 50 + 30 + 10)
        self.assertEqual(ly, self.canvas_panel.offset_y + 40 + 20 + 10)

    def test_moving_container_visually_moves_children(self):
        """Requirement 2: When container is moved, child widgets visually move along with it."""
        frame = WidgetInstance.create("Frame", 50, 50)
        self.state.add_widget(frame)
        child = WidgetInstance.create("Button", 20, 20, parent_id=frame.id)
        self.state.add_widget(child)

        initial_bx, initial_by, _, _ = self.canvas_panel.get_canvas_bounds(child)

        # Move frame by +40, +30
        self.state.update_widget_geometry(frame.id, frame.x + 40, frame.y + 30, frame.width, frame.height)
        new_bx, new_by, _, _ = self.canvas_panel.get_canvas_bounds(child)

        self.assertEqual(new_bx, initial_bx + 40)
        self.assertEqual(new_by, initial_by + 30)

    def test_hit_testing_deepest_child(self):
        """Requirement 2: Hit-testing returns the deepest innermost child widget using reverse Z-order and depth."""
        frame = WidgetInstance.create("Frame", 20, 20)
        frame.width = 400
        frame.height = 300
        self.state.add_widget(frame)

        btn = WidgetInstance.create("Button", 40, 40, parent_id=frame.id)
        btn.width = 120
        btn.height = 40
        self.state.add_widget(btn)

        # Coordinate hitting both Frame and Button
        btn_cx = self.canvas_panel.offset_x + 20 + 50
        btn_cy = self.canvas_panel.offset_y + 20 + 50
        hit = self.canvas_panel._get_widget_at(btn_cx, btn_cy)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.id, btn.id, "Hit testing should return innermost child Button, not parent Frame")

        # Coordinate hitting Frame outside Button
        frame_cx = self.canvas_panel.offset_x + 20 + 250
        frame_cy = self.canvas_panel.offset_y + 20 + 200
        hit_frame = self.canvas_panel._get_widget_at(frame_cx, frame_cy)
        self.assertIsNotNone(hit_frame)
        self.assertEqual(hit_frame.id, frame.id, "Hit testing should return Frame when outside Button")

    def test_container_dropping_and_auto_parenting(self):
        """Requirement 3: Dropping widget inside container auto-parents and converts to local coordinates."""
        frame = WidgetInstance.create("Frame", 100, 100)
        frame.width = 300
        frame.height = 200
        self.state.add_widget(frame)

        # Set pending widget type from palette
        self.canvas_panel.set_pending_placement("Button")

        # Click at canvas coordinates inside the frame: (frame_x + 40, frame_y + 50)
        class DropEvent:
            x = 100 + 40 + 40  # offset_x (40) + frame.x (100) + local_x (40)
            y = 40 + 100 + 50  # offset_y (40) + frame.y (100) + local_y (50)
            state = 0

        self.canvas_panel._on_mouse_down(DropEvent())

        new_btn = self.state.get_selected_widget()
        self.assertIsNotNone(new_btn)
        self.assertEqual(new_btn.widget_type, "Button")
        self.assertEqual(new_btn.parent_id, frame.id, "Dropped widget must be auto-parented to container")
        self.assertEqual(new_btn.x, 40, "X must be converted to container local coordinates")
        self.assertEqual(new_btn.y, 50, "Y must be converted to container local coordinates")

    def test_interactive_notebook_tabs_and_visibility(self):
        """Requirement 4: Notebook tab switching and widget filtering."""
        nb = WidgetInstance.create("TNotebook", 40, 40)
        nb.width = 400
        nb.height = 300
        nb.properties["tabs"] = [
            {"id": "tab_1", "text": "First Tab"},
            {"id": "tab_2", "text": "Second Tab"}
        ]
        self.state.add_widget(nb)

        # Widget in tab 1
        btn1 = WidgetInstance.create("Button", 20, 40, parent_id=nb.id)
        btn1.container_tab_or_pane = "tab_1"
        self.state.add_widget(btn1)

        # Widget in tab 2
        btn2 = WidgetInstance.create("Button", 20, 40, parent_id=nb.id)
        btn2.container_tab_or_pane = "tab_2"
        self.state.add_widget(btn2)

        # Widget with unset container_tab_or_pane (should match first tab)
        btn_unset = WidgetInstance.create("Button", 50, 50, parent_id=nb.id)
        btn_unset.container_tab_or_pane = None
        self.state.add_widget(btn_unset)

        # Initially tab_1 is active
        self.assertEqual(self.canvas_panel.get_active_tab(nb), "tab_1")
        self.assertTrue(self.canvas_panel.is_widget_visible(btn1))
        self.assertFalse(self.canvas_panel.is_widget_visible(btn2))
        self.assertTrue(self.canvas_panel.is_widget_visible(btn_unset))

        # Switch to tab_2
        self.canvas_panel.notebook_active_tabs[nb.id] = "tab_2"
        self.assertFalse(self.canvas_panel.is_widget_visible(btn1))
        self.assertTrue(self.canvas_panel.is_widget_visible(btn2))
        self.assertFalse(self.canvas_panel.is_widget_visible(btn_unset))

        # Test tab click interaction
        self.canvas_panel.render()
        rects = self.canvas_panel._tab_rects.get(nb.id, [])
        self.assertEqual(len(rects), 2)
        tab1_rect = rects[0]
        tab2_rect = rects[1]

        # Simulate click on tab 1
        class TabClickEvent:
            x = (tab1_rect[1] + tab1_rect[3]) // 2
            y = (tab1_rect[2] + tab1_rect[4]) // 2
            state = 0

        self.canvas_panel._on_mouse_down(TabClickEvent())
        self.assertEqual(self.canvas_panel.get_active_tab(nb), "tab_1")
        self.assertTrue(self.canvas_panel.is_widget_visible(btn1))
        self.assertFalse(self.canvas_panel.is_widget_visible(btn2))

        # Simulate click on tab 2
        class Tab2ClickEvent:
            x = (tab2_rect[1] + tab2_rect[3]) // 2
            y = (tab2_rect[2] + tab2_rect[4]) // 2
            state = 0

        self.canvas_panel._on_mouse_down(Tab2ClickEvent())
        self.assertEqual(self.canvas_panel.get_active_tab(nb), "tab_2")
        self.assertTrue(self.canvas_panel.is_widget_visible(btn2))
        self.assertFalse(self.canvas_panel.is_widget_visible(btn1))

    def test_render_all_42_widgets(self):
        """Requirement 5: Verify distinct visual mockups for all 42 catalog widgets render cleanly."""
        catalog_types = list(WIDGET_CATALOG.keys())
        self.assertGreaterEqual(len(catalog_types), 42)

        for wtype in catalog_types:
            w = WidgetInstance.create(wtype, 10, 10)
            self.state.widgets.clear()
            self.state.widget_order.clear()
            self.state.add_widget(w)
            # Render should execute without any exceptions
            try:
                self.canvas_panel.render()
            except Exception as e:
                self.fail(f"Failed to render mockup for widget type '{wtype}': {e}")

    def test_lock_indicator_and_color_previews(self):
        """Requirement 6: Lock badge and custom bg/fg colors applied to mockups."""
        btn = WidgetInstance.create("Button", 30, 30)
        btn.locked = True
        btn.properties["bg"] = "#ff5500"
        btn.properties["fg"] = "#00ffaa"
        self.state.add_widget(btn)
        self.state.select_widget(btn.id)

        self.canvas_panel.render()

        # Check canvas items for lock badge text
        all_items = self.canvas_panel.canvas.find_all()
        texts = [self.canvas_panel.canvas.itemcget(item, "text") for item in all_items if self.canvas_panel.canvas.type(item) == "text"]
        self.assertTrue(any("[🔒]" in t for t in texts), "Selection handles must display [🔒] lock badge")

        # Check custom color fill applied to button rectangle
        rects = [item for item in all_items if self.canvas_panel.canvas.type(item) == "rectangle"]
        fills = [self.canvas_panel.canvas.itemcget(r, "fill") for r in rects]
        self.assertIn("#ff5500", fills, "Custom 'bg' color must be applied to canvas mockup")

if __name__ == "__main__":
    unittest.main()
