"""
PageStudio - Visual WYSIWYG Canvas
Provides the interactive design surface, widget rendering, 8-point resize handles,
grid snapping, and direct manipulation.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Tuple, List
from ..core.state import ProjectState
from ..core.models import WidgetInstance, WIDGET_CATALOG
from ..ui.theme import (
    COLOR_BG_CANVAS, COLOR_CANVAS_PAPER, COLOR_CANVAS_GRID,
    COLOR_SELECTION, COLOR_HANDLE_FILL, COLOR_HANDLE_OUTLINE,
    FONT_UI_FAMILY
)
from ..utils.helpers import IS_MAC

HANDLE_SIZE = 8

class DesignCanvas(tk.Frame):
    """Interactive drag-and-drop design workspace."""

    def __init__(self, parent, state: ProjectState, **kwargs):
        super().__init__(parent, **kwargs)
        self.state = state
        self.pending_widget_type: Optional[str] = None
        
        # Interaction state
        self.drag_mode: Optional[str] = None  # "move", "resize", or None
        self.active_handle: Optional[str] = None # "nw", "n", "ne", "e", "se", "s", "sw", "w"
        self.drag_start_x: int = 0
        self.drag_start_y: int = 0
        self.orig_geom: Dict[str, Tuple[int, int, int, int]] = {} # id -> (x, y, w, h)
        
        # Canvas offset for the paper/window
        self.offset_x: int = 40
        self.offset_y: int = 40
        
        self._build_ui()
        self._bind_events()
        self.state.add_listener(self.render)

    def _build_ui(self):
        self.canvas = tk.Canvas(
            self,
            bg=COLOR_BG_CANVAS,
            highlightthickness=0,
            cursor="arrow"
        )
        self.canvas.pack(fill="both", expand=True)

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Motion>", self._on_mouse_hover)
        
        # Keyboard shortcuts
        self.bind_all("<Delete>", self._on_delete_key)
        self.bind_all("<BackSpace>", self._on_delete_key)
        
        # Arrow key micro-nudging
        self.bind_all("<Left>", lambda e: self._nudge_selected(-1, 0, e))
        self.bind_all("<Right>", lambda e: self._nudge_selected(1, 0, e))
        self.bind_all("<Up>", lambda e: self._nudge_selected(0, -1, e))
        self.bind_all("<Down>", lambda e: self._nudge_selected(0, 1, e))

    def set_pending_placement(self, widget_type: Optional[str]):
        """Sets the widget type ready to be dropped on next canvas click."""
        self.pending_widget_type = widget_type
        if widget_type:
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="arrow")

    def render(self):
        """Redraws the entire canvas (paper, grid, widgets, handles)."""
        self.canvas.delete("all")
        
        # Draw paper / Root Window area
        paper_w = self.state.width
        paper_h = self.state.height
        px1 = self.offset_x
        py1 = self.offset_y
        px2 = px1 + paper_w
        py2 = py1 + paper_h
        
        # Shadow
        self.canvas.create_rectangle(
            px1 + 4, py1 + 4, px2 + 4, py2 + 4,
            fill="#181820", outline=""
        )
        
        # Window Surface
        self.canvas.create_rectangle(
            px1, py1, px2, py2,
            fill=COLOR_CANVAS_PAPER,
            outline="#454555",
            width=2,
            tags="paper"
        )

        # Draw Grid (dots or lines)
        if self.state.snap_to_grid and self.state.grid_size >= 5:
            grid = self.state.grid_size
            for gx in range(px1 + grid, px2, grid):
                for gy in range(py1 + grid, py2, grid):
                    self.canvas.create_line(
                        gx, gy, gx + 1, gy + 1,
                        fill=COLOR_CANVAS_GRID,
                        tags="grid"
                    )

        # Draw titlebar indicator on top of paper
        title_text = f"Window: {self.state.title} ({paper_w}x{paper_h})"
        self.canvas.create_text(
            px1 + 8, py1 - 12,
            text=title_text,
            fill="#a0a0b0",
            anchor="w",
            font=(FONT_UI_FAMILY, 9, "bold")
        )

        # Render Widgets in Z-Order
        for wid in self.state.widget_order:
            w = self.state.widgets.get(wid)
            if not w:
                continue
            self._render_widget(w)

        # Render Selection & Resize Handles for Selected Widgets
        selected_widget = self.state.get_selected_widget()
        if selected_widget:
            self._render_selection_handles(selected_widget)

    def _render_widget(self, w: WidgetInstance):
        """Renders an individual widget visual mockup on canvas."""
        wx = self.offset_x + w.x
        wy = self.offset_y + w.y
        ww = w.width
        wh = w.height
        tag = f"widget_{w.id}"

        wtype = w.widget_type
        text = w.properties.get("text", "")

        if wtype == "Button":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#f0f0f4", outline="#b0b0bc", width=1, tags=(tag, "widget")
            )
            self.canvas.create_text(
                wx + ww // 2, wy + wh // 2,
                text=text or "Button", fill="#222228",
                font=(FONT_UI_FAMILY, 9), tags=(tag, "widget")
            )

        elif wtype == "Label":
            self.canvas.create_text(
                wx + 4, wy + wh // 2,
                text=text or "Label", fill="#222228",
                anchor="w", font=(FONT_UI_FAMILY, 9), tags=(tag, "widget")
            )

        elif wtype == "Entry":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#ffffff", outline="#a0a0ab", width=1, tags=(tag, "widget")
            )
            sample = text or ""
            self.canvas.create_text(
                wx + 6, wy + wh // 2,
                text=sample, fill="#666670" if not text else "#222228",
                anchor="w", font=(FONT_UI_FAMILY, 9), tags=(tag, "widget")
            )

        elif wtype == "Checkbutton":
            box_sz = 14
            by = wy + (wh - box_sz) // 2
            self.canvas.create_rectangle(
                wx, by, wx + box_sz, by + box_sz,
                fill="#ffffff", outline="#777788", tags=(tag, "widget")
            )
            self.canvas.create_text(
                wx + box_sz + 8, wy + wh // 2,
                text=text or "Option", fill="#222228",
                anchor="w", font=(FONT_UI_FAMILY, 9), tags=(tag, "widget")
            )

        elif wtype == "Radiobutton":
            rad = 7
            rcx = wx + rad
            rcy = wy + wh // 2
            self.canvas.create_oval(
                rcx - rad, rcy - rad, rcx + rad, rcy + rad,
                fill="#ffffff", outline="#777788", tags=(tag, "widget")
            )
            self.canvas.create_text(
                wx + rad * 2 + 8, wy + wh // 2,
                text=text or "Radio", fill="#222228",
                anchor="w", font=(FONT_UI_FAMILY, 9), tags=(tag, "widget")
            )

        elif wtype == "Combobox":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#ffffff", outline="#a0a0ab", tags=(tag, "widget")
            )
            arrow_w = 20
            self.canvas.create_rectangle(
                wx + ww - arrow_w, wy, wx + ww, wy + wh,
                fill="#e6e6ec", outline="#a0a0ab", tags=(tag, "widget")
            )
            # Down arrow
            acx = wx + ww - arrow_w // 2
            acy = wy + wh // 2
            self.canvas.create_polygon(
                acx - 4, acy - 2, acx + 4, acy - 2, acx, acy + 3,
                fill="#444450", tags=(tag, "widget")
            )
            self.canvas.create_text(
                wx + 6, wy + wh // 2,
                text="Select...", fill="#777785",
                anchor="w", font=(FONT_UI_FAMILY, 9), tags=(tag, "widget")
            )

        elif wtype == "Progressbar":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#e0e0e6", outline="#b0b0bc", tags=(tag, "widget")
            )
            val_pct = min(1.0, max(0.0, w.properties.get("value", 50) / max(1, w.properties.get("maximum", 100))))
            fill_w = int(ww * val_pct)
            self.canvas.create_rectangle(
                wx, wy, wx + fill_w, wy + wh,
                fill=COLOR_SELECTION, outline="", tags=(tag, "widget")
            )

        elif wtype == "Scale":
            cy = wy + wh // 2
            self.canvas.create_line(
                wx, cy, wx + ww, cy,
                fill="#a0a0b0", width=4, tags=(tag, "widget")
            )
            # Thumb knob
            kx = wx + ww // 2
            self.canvas.create_oval(
                kx - 7, cy - 7, kx + 7, cy + 7,
                fill=COLOR_SELECTION, outline="#ffffff", width=2, tags=(tag, "widget")
            )

        elif wtype == "Separator":
            cy = wy + wh // 2
            self.canvas.create_line(
                wx, cy, wx + ww, cy,
                fill="#c0c0cc", width=1, tags=(tag, "widget")
            )

        elif wtype == "LabelFrame":
            self.canvas.create_rectangle(
                wx, wy + 8, wx + ww, wy + wh,
                fill="", outline="#b0b0bc", width=1, tags=(tag, "widget")
            )
            # Title badge
            title = text or "Group"
            self.canvas.create_rectangle(
                wx + 10, wy, wx + 16 + len(title) * 7, wy + 16,
                fill=COLOR_CANVAS_PAPER, outline=""
            )
            self.canvas.create_text(
                wx + 14, wy + 8,
                text=title, fill="#33333e",
                anchor="w", font=(FONT_UI_FAMILY, 8, "bold"), tags=(tag, "widget")
            )

        elif wtype == "Frame":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#f5f5f9", outline="#cccccc", dash=(3, 3), tags=(tag, "widget")
            )

        elif wtype == "Listbox":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#ffffff", outline="#a0a0ab", tags=(tag, "widget")
            )
            for i, item_text in enumerate(["Item 1", "Item 2", "Item 3"]):
                iy = wy + 6 + (i * 18)
                if iy + 14 < wy + wh:
                    self.canvas.create_text(
                        wx + 8, iy, text=item_text, fill="#33333e",
                        anchor="w", font=(FONT_UI_FAMILY, 8), tags=(tag, "widget")
                    )

        elif wtype == "Text":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#ffffff", outline="#a0a0ab", tags=(tag, "widget")
            )
            self.canvas.create_text(
                wx + 6, wy + 8, text="Text Editor Area...", fill="#888896",
                anchor="nw", font=(FONT_UI_FAMILY, 8), tags=(tag, "widget")
            )

        elif wtype == "Canvas":
            self.canvas.create_rectangle(
                wx, wy, wx + ww, wy + wh,
                fill="#fafafa", outline="#888899", dash=(4, 2), tags=(tag, "widget")
            )
            self.canvas.create_text(
                wx + ww // 2, wy + wh // 2,
                text="[Canvas]", fill="#888899",
                font=(FONT_UI_FAMILY, 8), tags=(tag, "widget")
            )

    def _render_selection_handles(self, w: WidgetInstance):
        """Draws bounding box and 8 handles around active selection."""
        wx = self.offset_x + w.x
        wy = self.offset_y + w.y
        ww = w.width
        wh = w.height
        
        # Bounding box
        self.canvas.create_rectangle(
            wx - 1, wy - 1, wx + ww + 1, wy + wh + 1,
            outline=COLOR_SELECTION, width=2, tags="selection"
        )
        
        # Coordinate badge
        badge_text = f"{w.name}  ({w.x}, {w.y}) {w.width}x{w.height}"
        self.canvas.create_text(
            wx, wy - 10,
            text=badge_text,
            fill=COLOR_SELECTION,
            anchor="w",
            font=(FONT_UI_FAMILY, 8, "bold"),
            tags="selection"
        )

        # 8 handles
        handles = {
            "nw": (wx, wy),
            "n": (wx + ww // 2, wy),
            "ne": (wx + ww, wy),
            "e": (wx + ww, wy + wh // 2),
            "se": (wx + ww, wy + wh),
            "s": (wx + ww // 2, wy + wh),
            "sw": (wx, wy + wh),
            "w": (wx, wy + wh // 2),
        }
        
        hs = HANDLE_SIZE // 2
        for h_name, (hx, hy) in handles.items():
            self.canvas.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill=COLOR_HANDLE_FILL,
                outline=COLOR_HANDLE_OUTLINE,
                width=1.5,
                tags=("selection", f"handle_{h_name}")
            )

    # --------------------------------------------------------------------------
    # Event Handlers: Dragging, Resizing & Placement
    # --------------------------------------------------------------------------

    def _get_widget_at(self, cx: int, cy: int) -> Optional[WidgetInstance]:
        """Hit test for widgets on canvas in reverse Z-order (topmost first)."""
        rx = cx - self.offset_x
        ry = cy - self.offset_y
        for wid in reversed(self.state.widget_order):
            w = self.state.widgets.get(wid)
            if not w:
                continue
            if w.x <= rx <= w.x + w.width and w.y <= ry <= w.y + w.height:
                return w
        return None

    def _get_handle_at(self, cx: int, cy: int) -> Optional[str]:
        """Checks if mouse is over any resize handle of the selected widget."""
        w = self.state.get_selected_widget()
        if not w:
            return None
        wx = self.offset_x + w.x
        wy = self.offset_y + w.y
        ww = w.width
        wh = w.height
        
        handles = {
            "nw": (wx, wy),
            "n": (wx + ww // 2, wy),
            "ne": (wx + ww, wy),
            "e": (wx + ww, wy + wh // 2),
            "se": (wx + ww, wy + wh),
            "s": (wx + ww // 2, wy + wh),
            "sw": (wx, wy + wh),
            "w": (wx, wy + wh // 2),
        }
        tol = HANDLE_SIZE
        for h_name, (hx, hy) in handles.items():
            if abs(cx - hx) <= tol and abs(cy - hy) <= tol:
                return h_name
        return None

    def _on_mouse_down(self, event):
        # 1. Check if placement mode is active
        if self.pending_widget_type:
            rx = event.x - self.offset_x
            ry = event.y - self.offset_y
            # Clamp inside window
            rx = max(0, min(rx, self.state.width - 20))
            ry = max(0, min(ry, self.state.height - 20))
            new_widget = WidgetInstance.create(self.pending_widget_type, rx, ry)
            self.state.add_widget(new_widget)
            self.set_pending_placement(None)
            return

        # 2. Check if clicked a resize handle
        handle = self._get_handle_at(event.x, event.y)
        if handle:
            self.drag_mode = "resize"
            self.active_handle = handle
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            w = self.state.get_selected_widget()
            if w:
                self.orig_geom = {w.id: (w.x, w.y, w.width, w.height)}
            return

        # 3. Check if clicked a widget
        clicked_widget = self._get_widget_at(event.x, event.y)
        if clicked_widget:
            is_shift = (event.state & 0x0001) != 0
            self.state.select_widget(clicked_widget.id, additive=is_shift)
            self.drag_mode = "move"
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            self.orig_geom = {
                wid: (self.state.widgets[wid].x, self.state.widgets[wid].y,
                      self.state.widgets[wid].width, self.state.widgets[wid].height)
                for wid in self.state.selected_ids if wid in self.state.widgets
            }
        else:
            # Clicked empty paper or canvas
            self.state.select_widget(None)
            self.drag_mode = None

    def _on_mouse_drag(self, event):
        if not self.drag_mode:
            return

        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        if self.drag_mode == "move":
            for wid in self.state.selected_ids:
                if wid not in self.orig_geom:
                    continue
                ox, oy, ow, oh = self.orig_geom[wid]
                new_x = max(0, ox + dx)
                new_y = max(0, oy + dy)
                self.state.update_widget_geometry(wid, new_x, new_y, ow, oh, commit=False)

        elif self.drag_mode == "resize" and self.active_handle:
            w = self.state.get_selected_widget()
            if not w or w.id not in self.orig_geom:
                return
            ox, oy, ow, oh = self.orig_geom[w.id]
            h = self.active_handle

            new_x, new_y, new_w, new_h = ox, oy, ow, oh

            if "e" in h:
                new_w = max(15, ow + dx)
            if "s" in h:
                new_h = max(15, oh + dy)
            if "w" in h:
                constrained_dx = min(dx, ow - 15)
                new_x = ox + constrained_dx
                new_w = ow - constrained_dx
            if "n" in h:
                constrained_dy = min(dy, oh - 15)
                new_y = oy + constrained_dy
                new_h = oh - constrained_dy

            self.state.update_widget_geometry(w.id, new_x, new_y, new_w, new_h, commit=False)

    def _on_mouse_up(self, event):
        if self.drag_mode:
            self.state.push_state()
            self.drag_mode = None
            self.active_handle = None
            self.orig_geom.clear()

    def _on_mouse_hover(self, event):
        if self.drag_mode or self.pending_widget_type:
            return
        handle = self._get_handle_at(event.x, event.y)
        if handle:
            cursors = {
                "nw": "top_left_corner", "se": "bottom_right_corner",
                "ne": "top_right_corner", "sw": "bottom_left_corner",
                "n": "top_side", "s": "bottom_side",
                "e": "right_side", "w": "left_side"
            }
            self.canvas.config(cursor=cursors.get(handle, "cross"))
        elif self._get_widget_at(event.x, event.y):
            self.canvas.config(cursor="fleur")
        else:
            self.canvas.config(cursor="arrow")

    def _on_delete_key(self, event):
        if self.state.selected_ids:
            self.state.remove_selected()

    def _nudge_selected(self, dx: int, dy: int, event):
        if not self.state.selected_ids:
            return
        step = 10 if (event.state & 0x0001) else 1
        for wid in self.state.selected_ids:
            w = self.state.widgets.get(wid)
            if not w:
                continue
            self.state.update_widget_geometry(
                wid, max(0, w.x + dx * step), max(0, w.y + dy * step),
                w.width, w.height, commit=False, snap=False
            )
        self.state.push_state()
