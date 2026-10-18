"""
PageStudio - Visual WYSIWYG Canvas
Provides the interactive design surface, scrollable surface, cumulative container
coordinate mathematics, 8-point resize handles, interactive notebook tabs,
lock badges, color previews, and distinct renderers for all 42 widgets.
"""

import sys
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
from ..utils.helpers import IS_MAC, is_text_editing

HANDLE_SIZE = 8

CONTAINER_TYPES = {
    "Frame", "TFrame", "LabelFrame", "TLabelframe",
    "TNotebook", "Notebook", "Canvas", "TPanedwindow",
    "Scrolledwindow", "Toplevel"
}


class DesignCanvas(tk.Frame):
    """Interactive drag-and-drop design workspace with scrollable surface and cumulative coordinate system."""

    def __init__(self, parent, state: ProjectState, **kwargs):
        super().__init__(parent, **kwargs)
        self.state = state
        self.pending_widget_type: Optional[str] = None

        # Interaction state
        self.drag_mode: Optional[str] = None  # "move", "resize", or None
        self.active_handle: Optional[str] = None  # "nw", "n", "ne", "e", "se", "s", "sw", "w"
        self.drag_start_x: int = 0
        self.drag_start_y: int = 0
        self.orig_geom: Dict[str, Tuple[int, int, int, int]] = {}  # id -> (x, y, w, h)

        # Canvas offset for the paper/window
        self.offset_x: int = 40
        self.offset_y: int = 40

        # Interactive notebook tab tracking: widget_id -> active_tab_id
        self.notebook_active_tabs: Dict[str, str] = {}
        # Tab bounding rects on canvas: widget_id -> list of (tab_id, x1, y1, x2, y2)
        self._tab_rects: Dict[str, List[Tuple[str, int, int, int, int]]] = {}

        self._build_ui()
        self._bind_events()
        self.state.add_listener(self.render)

    def _build_ui(self):
        """Constructs canvas wrapped with horizontal and vertical scrollbars."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            bg=COLOR_BG_CANVAS,
            highlightthickness=0,
            cursor="arrow"
        )
        self.v_scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

        self.canvas.configure(
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set
        )

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Motion>", self._on_mouse_hover)

        # Mousewheel scrolling (vertical & horizontal across Windows, macOS, and Linux)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Shift-Button-4>", lambda e: self.canvas.xview_scroll(-1, "units"))
        if not sys.platform.startswith("win"):
            try:
                self.canvas.bind("<Button-6>", lambda e: self.canvas.xview_scroll(-1, "units"))
                self.canvas.bind("<Button-7>", lambda e: self.canvas.xview_scroll(1, "units"))
            except tk.TclError:
                pass

        # Keyboard shortcuts
        self.bind_all("<Delete>", self._on_delete_key)
        self.bind_all("<BackSpace>", self._on_delete_key)

        # Arrow key micro-nudging
        self.bind_all("<Left>", lambda e: self._nudge_selected(-1, 0, e))
        self.bind_all("<Right>", lambda e: self._nudge_selected(1, 0, e))
        self.bind_all("<Up>", lambda e: self._nudge_selected(0, -1, e))
        self.bind_all("<Down>", lambda e: self._nudge_selected(0, 1, e))

    def _is_text_editing(self, event=None) -> bool:
        """Returns True if the focused widget or event source is a text input field."""
        return is_text_editing(self, event)

    def _get_parent_container_dimensions(self, w: WidgetInstance) -> Tuple[int, int]:
        """Returns (width, height) of the widget's parent container or the main canvas paper."""
        if w.parent_id and w.parent_id in self.state.widgets:
            parent = self.state.widgets[w.parent_id]
            return parent.width, parent.height
        return self.state.width, self.state.height

    def _on_mousewheel(self, event):
        if hasattr(event, "num") and event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif hasattr(event, "num") and event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, "delta") and event.delta:
            if IS_MAC:
                units = int(-1 * event.delta)
            else:
                units = int(-1 * (event.delta / 120)) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
            self.canvas.yview_scroll(units, "units")

    def _on_shift_mousewheel(self, event):
        if hasattr(event, "num") and event.num in (4, 6):
            self.canvas.xview_scroll(-1, "units")
        elif hasattr(event, "num") and event.num in (5, 7):
            self.canvas.xview_scroll(1, "units")
        elif hasattr(event, "delta") and event.delta:
            if IS_MAC:
                units = int(-1 * event.delta)
            else:
                units = int(-1 * (event.delta / 120)) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
            self.canvas.xview_scroll(units, "units")

    def set_pending_placement(self, widget_type: Optional[str]):
        """Sets the widget type ready to be dropped on next canvas click."""
        self.pending_widget_type = widget_type
        if widget_type:
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="arrow")

    # --------------------------------------------------------------------------
    # Cumulative Container Coordinates & Hierarchy
    # --------------------------------------------------------------------------

    def get_canvas_bounds(self, w: WidgetInstance) -> Tuple[int, int, int, int]:
        """
        Recursively sums x and y through the parent chain up to root,
        adding self.offset_x and self.offset_y.
        Returns: (canvas_x, canvas_y, width, height)
        """
        total_x = 0
        total_y = 0
        curr: Optional[WidgetInstance] = w
        visited = set()

        while curr:
            if curr.id in visited:
                break
            visited.add(curr.id)
            total_x += curr.x
            total_y += curr.y
            if curr.parent_id and curr.parent_id in self.state.widgets:
                curr = self.state.widgets[curr.parent_id]
            else:
                curr = None

        canvas_x = self.offset_x + total_x
        canvas_y = self.offset_y + total_y
        return (canvas_x, canvas_y, w.width, w.height)

    def _get_widget_depth(self, w: WidgetInstance) -> int:
        """Returns the nesting depth of a widget (0 for root widgets)."""
        depth = 0
        curr = w
        visited = set()
        while curr and curr.parent_id and curr.parent_id in self.state.widgets:
            if curr.id in visited:
                break
            visited.add(curr.id)
            depth += 1
            curr = self.state.widgets[curr.parent_id]
        return depth

    def _has_selected_ancestor(self, wid: str) -> bool:
        """Checks if any ancestor in the parent chain is also currently selected."""
        curr = self.state.widgets.get(wid)
        visited = set()
        while curr and curr.parent_id and curr.parent_id in self.state.widgets:
            if curr.id in visited:
                break
            visited.add(curr.id)
            if curr.parent_id in self.state.selected_ids:
                return True
            curr = self.state.widgets[curr.parent_id]
        return False

    def _is_container(self, w: WidgetInstance) -> bool:
        """Determines if a widget instance can act as a parent container."""
        spec = WIDGET_CATALOG.get(w.widget_type)
        if spec and spec.is_container:
            return True
        return w.widget_type in CONTAINER_TYPES

    def _get_container_at(self, cx: int, cy: int) -> Optional[WidgetInstance]:
        """Finds the innermost visible container containing canvas point (cx, cy)."""
        candidates: List[Tuple[int, int, WidgetInstance]] = []
        for wid, w in self.state.widgets.items():
            if not self._is_container(w):
                continue
            if not self.is_widget_visible(w):
                continue
            bx, by, bw, bh = self.get_canvas_bounds(w)
            if bx <= cx <= bx + bw and by <= cy <= by + bh:
                depth = self._get_widget_depth(w)
                z_idx = self.state.widget_order.index(w.id) if w.id in self.state.widget_order else 0
                candidates.append((depth, z_idx, w))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][2]

    def _get_widget_at(self, cx: int, cy: int) -> Optional[WidgetInstance]:
        """
        Hit test for widgets on canvas. Returns the deepest (innermost) child
        widget at the coordinate, using reverse Z-order and hierarchy depth.
        """
        candidates: List[Tuple[int, int, WidgetInstance]] = []
        for wid, w in self.state.widgets.items():
            if not self.is_widget_visible(w):
                continue
            bx, by, bw, bh = self.get_canvas_bounds(w)
            if bx <= cx <= bx + bw and by <= cy <= by + bh:
                depth = self._get_widget_depth(w)
                z_idx = self.state.widget_order.index(w.id) if w.id in self.state.widget_order else 0
                candidates.append((depth, z_idx, w))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return candidates[0][2]

    # --------------------------------------------------------------------------
    # Notebook Tabs & Visibility Filtering
    # --------------------------------------------------------------------------

    def _get_notebook_tabs(self, w: WidgetInstance) -> List[Dict[str, str]]:
        """Extracts normalized list of tab specs [{id, text, state}] from a notebook widget."""
        raw_tabs = w.properties.get("tabs", [])
        if not raw_tabs:
            return [
                {"id": "tab_1", "text": "Tab 1", "state": "normal"},
                {"id": "tab_2", "text": "Tab 2", "state": "normal"}
            ]
        tabs: List[Dict[str, str]] = []
        for i, t in enumerate(raw_tabs):
            if isinstance(t, dict):
                tid = str(t.get("id") or f"tab_{i + 1}")
                ttext = str(t.get("text") or tid)
                tstate = str(t.get("state", "normal"))
                tabs.append({"id": tid, "text": ttext, "state": tstate})
            else:
                tstr = str(t)
                tabs.append({"id": tstr, "text": tstr, "state": "normal"})
        return tabs

    def get_active_tab(self, w: WidgetInstance) -> str:
        """Returns the active tab ID (or label) for a given notebook."""
        tabs = self._get_notebook_tabs(w)
        if not tabs:
            return "tab_1"

        active = self.notebook_active_tabs.get(w.id)
        if not active:
            active = w.properties.get("active_tab")

        tab_ids = [t["id"] for t in tabs]
        tab_texts = [t["text"] for t in tabs]

        if active not in tab_ids and active not in tab_texts:
            active = tabs[0]["id"]

        self.notebook_active_tabs[w.id] = active
        return active

    def is_widget_visible(self, w: WidgetInstance) -> bool:
        """
        Checks whether widget w is currently visible on the canvas.
        If parented to a notebook, it is visible only if container_tab_or_pane
        matches the active tab (or if unset/first tab). All ancestors must also be visible.
        """
        curr: Optional[WidgetInstance] = w
        visited = set()

        while curr and curr.parent_id and curr.parent_id in self.state.widgets:
            if curr.id in visited:
                break
            visited.add(curr.id)
            parent = self.state.widgets[curr.parent_id]
            if parent.widget_type in ("TNotebook", "Notebook"):
                tabs = self._get_notebook_tabs(parent)
                active_tab = self.get_active_tab(parent)
                first_tab_id = tabs[0]["id"] if tabs else ""
                first_tab_text = tabs[0]["text"] if tabs else ""
                is_first = (active_tab == first_tab_id or active_tab == first_tab_text or not active_tab)

                tab_val = curr.container_tab_or_pane
                if not tab_val:
                    # Unset container_tab_or_pane defaults to first tab
                    if not is_first:
                        return False
                else:
                    # Check exact or normalized match
                    is_match = (
                        tab_val == active_tab or
                        tab_val.lower() == str(active_tab).lower() or
                        any(
                            (t["id"] == tab_val or t["text"] == tab_val or t["id"].lower() == tab_val.lower() or t["text"].lower() == tab_val.lower()) and
                            (t["id"] == active_tab or t["text"] == active_tab or t["id"].lower() == str(active_tab).lower() or t["text"].lower() == str(active_tab).lower())
                            for t in tabs
                        )
                    )
                    if not is_match:
                        return False

            curr = parent
        return True

    def _get_notebook_tab_at(self, cx: int, cy: int) -> Optional[Tuple[WidgetInstance, str]]:
        """Checks if canvas point (cx, cy) hits any tab header of a visible notebook."""
        for wid in reversed(self.state.widget_order):
            w = self.state.widgets.get(wid)
            if not w or w.widget_type not in ("TNotebook", "Notebook") or not self.is_widget_visible(w):
                continue
            rects = self._tab_rects.get(w.id, [])
            for tab_id, x1, y1, x2, y2 in rects:
                if x1 <= cx <= x2 and y1 <= cy <= y2:
                    return (w, tab_id)
        return None

    # --------------------------------------------------------------------------
    # Main Render Pipeline
    # --------------------------------------------------------------------------

    def render(self):
        """Redraws the entire canvas (paper, grid, widgets, handles)."""
        self.canvas.delete("all")
        self._tab_rects.clear()

        # Paper / Root Window area
        paper_w = self.state.width
        paper_h = self.state.height
        px1 = self.offset_x
        py1 = self.offset_y
        px2 = px1 + paper_w
        py2 = py1 + paper_h

        # Update scrollregion so canvas surface can scroll to accommodate any project dimensions
        sr_w = max(px2 + 80, 800)
        sr_h = max(py2 + 80, 600)
        for w in self.state.widgets.values():
            bx, by, bw, bh = self.get_canvas_bounds(w)
            sr_w = max(sr_w, bx + bw + 80)
            sr_h = max(sr_h, by + bh + 80)
        self.canvas.config(scrollregion=(0, 0, sr_w, sr_h))

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

        # Render Widgets in order sorted by hierarchy depth so parent containers draw behind children
        render_order = self._get_render_order()
        for wid in render_order:
            w = self.state.widgets.get(wid)
            if not w or not self.is_widget_visible(w):
                continue
            self._render_widget(w)

        # Render Selection & Resize Handles for Selected Widgets
        selected_widget = self.state.get_selected_widget()
        if selected_widget and self.is_widget_visible(selected_widget):
            self._render_selection_handles(selected_widget)

    def _get_render_order(self) -> List[str]:
        """Stable sort by hierarchy depth so parent containers are drawn behind children."""
        widgets = [self.state.widgets[wid] for wid in self.state.widget_order if wid in self.state.widgets]
        widgets.sort(key=lambda w: self._get_widget_depth(w))
        return [w.id for w in widgets]

    # --------------------------------------------------------------------------
    # Distinct Visual Mockup Renderers for all 42 Widgets
    # --------------------------------------------------------------------------

    def _render_widget(self, w: WidgetInstance):
        """Renders an individual widget visual mockup on canvas."""
        wx, wy, ww, wh = self.get_canvas_bounds(w)
        tag = f"widget_{w.id}"
        tags = (tag, "widget")

        wtype = w.widget_type
        props = w.properties
        text = str(props.get("text", ""))

        # Support color overrides from properties
        custom_bg = props.get("bg") or props.get("background")
        custom_fg = props.get("fg") or props.get("foreground")

        # -------------------------------------------------------------
        # Buttons / TButton
        # -------------------------------------------------------------
        if wtype == "Button":
            b_bg = custom_bg or "#f0f0f4"
            b_fg = custom_fg or "#222228"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=b_bg, outline="#9c9ca8", width=1, tags=tags)
            # Bevel highlights
            self.canvas.create_line(wx + 1, wy + 1, wx + ww - 1, wy + 1, fill="#ffffff", tags=tags)
            self.canvas.create_line(wx + 1, wy + 1, wx + 1, wy + wh - 1, fill="#ffffff", tags=tags)
            self.canvas.create_line(wx + 1, wy + wh - 1, wx + ww - 1, wy + wh - 1, fill="#b0b0bc", tags=tags)
            self.canvas.create_line(wx + ww - 1, wy + 1, wx + ww - 1, wy + wh - 1, fill="#b0b0bc", tags=tags)
            self.canvas.create_text(
                wx + ww // 2, wy + wh // 2,
                text=text or "Button", fill=b_fg, font=(FONT_UI_FAMILY, 9), tags=tags
            )

        elif wtype == "TButton":
            b_bg = custom_bg or "#e8eaf0"
            b_fg = custom_fg or "#1e293b"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=b_bg, outline="#b8c0cc", width=1, tags=tags)
            self.canvas.create_rectangle(wx + 1, wy + 1, wx + ww - 1, wy + wh - 1, fill="", outline="#ffffff", width=1, tags=tags)
            self.canvas.create_text(
                wx + ww // 2, wy + wh // 2,
                text=text or "TButton", fill=b_fg, font=(FONT_UI_FAMILY, 9), tags=tags
            )

        # -------------------------------------------------------------
        # Entry / TEntry
        # -------------------------------------------------------------
        elif wtype == "Entry":
            e_bg = custom_bg or "#ffffff"
            e_fg = custom_fg or ("#222228" if text else "#888896")
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=e_bg, outline="#9ca3af", width=1, tags=tags)
            show_char = props.get("show")
            display_text = ("*" * len(text)) if (show_char and text) else text
            self.canvas.create_text(
                wx + 6, wy + wh // 2,
                text=display_text, fill=e_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags
            )
            # Subtle cursor indicator
            cursor_x = wx + 7 + len(display_text) * 7
            if cursor_x < wx + ww - 6:
                self.canvas.create_line(cursor_x, wy + 5, cursor_x, wy + wh - 5, fill="#4b5563", tags=tags)

        elif wtype == "TEntry":
            e_bg = custom_bg or "#ffffff"
            e_fg = custom_fg or ("#1e293b" if text else "#94a3b8")
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=e_bg, outline="#94a3b8", width=1, tags=tags)
            show_char = props.get("show")
            display_text = ("*" * len(text)) if (show_char and text) else text
            self.canvas.create_text(
                wx + 6, wy + wh // 2,
                text=display_text, fill=e_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags
            )

        # -------------------------------------------------------------
        # Label / TLabel
        # -------------------------------------------------------------
        elif wtype in ("Label", "TLabel"):
            l_fg = custom_fg or ("#222228" if wtype == "Label" else "#1e293b")
            if custom_bg:
                self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=custom_bg, outline="", tags=tags)
            anchor = props.get("anchor", "w")
            if anchor in ("center", "c"):
                tx, anchor_pos = wx + ww // 2, "center"
            elif anchor in ("e", "east"):
                tx, anchor_pos = wx + ww - 4, "e"
            else:
                tx, anchor_pos = wx + 4, "w"
            self.canvas.create_text(
                tx, wy + wh // 2,
                text=text or ("Label" if wtype == "Label" else "TLabel"),
                fill=l_fg, anchor=anchor_pos, font=(FONT_UI_FAMILY, 9), tags=tags
            )

        # -------------------------------------------------------------
        # Checkbutton / TCheckbutton
        # -------------------------------------------------------------
        elif wtype in ("Checkbutton", "TCheckbutton"):
            c_fg = custom_fg or "#222228"
            box_sz = 14
            by = wy + (wh - box_sz) // 2
            box_fill = custom_bg or ("#ffffff" if wtype == "Checkbutton" else "#f8fafc")
            border_col = "#64748b" if wtype == "Checkbutton" else "#3b82f6"
            self.canvas.create_rectangle(wx + 2, by, wx + 2 + box_sz, by + box_sz, fill=box_fill, outline=border_col, tags=tags)
            self.canvas.create_text(
                wx + 2 + box_sz // 2, by + box_sz // 2,
                text="✓", fill=border_col, font=(FONT_UI_FAMILY, 8, "bold"), tags=tags
            )
            self.canvas.create_text(
                wx + box_sz + 8, wy + wh // 2,
                text=text or ("Check Option" if wtype == "Checkbutton" else "TCheck"),
                fill=c_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags
            )

        # -------------------------------------------------------------
        # Radiobutton / TRadiobutton
        # -------------------------------------------------------------
        elif wtype in ("Radiobutton", "TRadiobutton"):
            r_fg = custom_fg or "#222228"
            rad = 7
            rcx = wx + 2 + rad
            rcy = wy + wh // 2
            oval_fill = custom_bg or ("#ffffff" if wtype == "Radiobutton" else "#f8fafc")
            border_col = "#64748b" if wtype == "Radiobutton" else "#3b82f6"
            self.canvas.create_oval(rcx - rad, rcy - rad, rcx + rad, rcy + rad, fill=oval_fill, outline=border_col, tags=tags)
            self.canvas.create_oval(rcx - 3, rcy - 3, rcx + 3, rcy + 3, fill=border_col, outline="", tags=tags)
            self.canvas.create_text(
                rcx + rad + 6, rcy,
                text=text or ("Radio Option" if wtype == "Radiobutton" else "TRadio"),
                fill=r_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags
            )

        # -------------------------------------------------------------
        # Combobox / TCombobox
        # -------------------------------------------------------------
        elif wtype in ("Combobox", "TCombobox"):
            cb_bg = custom_bg or "#ffffff"
            cb_fg = custom_fg or "#1e293b"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=cb_bg, outline="#94a3b8", tags=tags)
            arrow_w = 20
            self.canvas.create_rectangle(wx + ww - arrow_w, wy, wx + ww, wy + wh, fill="#e2e8f0", outline="#94a3b8", tags=tags)
            acx = wx + ww - arrow_w // 2
            acy = wy + wh // 2
            self.canvas.create_polygon(acx - 4, acy - 2, acx + 4, acy - 2, acx, acy + 3, fill="#334155", tags=tags)
            val_text = text or (props.get("values", ["Option 1"])[0] if props.get("values") else "Select...")
            self.canvas.create_text(
                wx + 6, wy + wh // 2,
                text=val_text, fill=cb_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags
            )

        # -------------------------------------------------------------
        # Listbox / Scrolledlistbox
        # -------------------------------------------------------------
        elif wtype == "Listbox":
            lb_bg = custom_bg or "#ffffff"
            lb_fg = custom_fg or "#1e293b"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=lb_bg, outline="#94a3b8", tags=tags)
            self.canvas.create_rectangle(wx + 2, wy + 2, wx + ww - 2, wy + 22, fill="#e0f2fe", outline="", tags=tags)
            for i, item_text in enumerate(["Item 1 (selected)", "Item 2", "Item 3", "Item 4", "Item 5"]):
                iy = wy + 4 + (i * 20)
                if iy + 16 < wy + wh:
                    self.canvas.create_text(
                        wx + 6, iy + 8, text=item_text, fill=lb_fg,
                        anchor="w", font=(FONT_UI_FAMILY, 8), tags=tags
                    )

        elif wtype == "Scrolledlistbox":
            lb_bg = custom_bg or "#ffffff"
            lb_fg = custom_fg or "#1e293b"
            sb_w = 16
            main_w = max(20, ww - sb_w)
            self.canvas.create_rectangle(wx, wy, wx + main_w, wy + wh, fill=lb_bg, outline="#94a3b8", tags=tags)
            for i, item_text in enumerate(["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"]):
                iy = wy + 4 + (i * 20)
                if iy + 16 < wy + wh:
                    self.canvas.create_text(
                        wx + 6, iy + 8, text=item_text, fill=lb_fg,
                        anchor="w", font=(FONT_UI_FAMILY, 8), tags=tags
                    )
            sx1 = wx + main_w
            self.canvas.create_rectangle(sx1, wy, wx + ww, wy + wh, fill="#f1f5f9", outline="#94a3b8", tags=tags)
            self.canvas.create_text(sx1 + sb_w // 2, wy + 7, text="▲", fill="#64748b", font=(FONT_UI_FAMILY, 6), tags=tags)
            self.canvas.create_text(sx1 + sb_w // 2, wy + wh - 7, text="▼", fill="#64748b", font=(FONT_UI_FAMILY, 6), tags=tags)
            self.canvas.create_rectangle(sx1 + 2, wy + 16, wx + ww - 2, wy + min(wh - 16, 45), fill="#cbd5e1", outline="", tags=tags)

        # -------------------------------------------------------------
        # Text / Scrolledtext
        # -------------------------------------------------------------
        elif wtype == "Text":
            t_bg = custom_bg or "#ffffff"
            t_fg = custom_fg or "#334155"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=t_bg, outline="#94a3b8", tags=tags)
            sample = text or "Text Editor Area...\nLine 2 content\nLine 3 content"
            self.canvas.create_text(
                wx + 6, wy + 8, text=sample, fill=t_fg,
                anchor="nw", font=(FONT_UI_FAMILY, 8), tags=tags
            )

        elif wtype == "Scrolledtext":
            t_bg = custom_bg or "#ffffff"
            t_fg = custom_fg or "#334155"
            sb_w = 16
            main_w = max(20, ww - sb_w)
            self.canvas.create_rectangle(wx, wy, wx + main_w, wy + wh, fill=t_bg, outline="#94a3b8", tags=tags)
            sample = text or "ScrolledText Editor Area...\nLine 2 content\nLine 3 content\nLine 4 content"
            self.canvas.create_text(
                wx + 6, wy + 8, text=sample, fill=t_fg,
                anchor="nw", font=(FONT_UI_FAMILY, 8), tags=tags
            )
            sx1 = wx + main_w
            self.canvas.create_rectangle(sx1, wy, wx + ww, wy + wh, fill="#f1f5f9", outline="#94a3b8", tags=tags)
            self.canvas.create_text(sx1 + sb_w // 2, wy + 7, text="▲", fill="#64748b", font=(FONT_UI_FAMILY, 6), tags=tags)
            self.canvas.create_text(sx1 + sb_w // 2, wy + wh - 7, text="▼", fill="#64748b", font=(FONT_UI_FAMILY, 6), tags=tags)
            self.canvas.create_rectangle(sx1 + 2, wy + 16, wx + ww - 2, wy + min(wh - 16, 50), fill="#cbd5e1", outline="", tags=tags)

        # -------------------------------------------------------------
        # Progressbar / TProgressbar
        # -------------------------------------------------------------
        elif wtype in ("Progressbar", "TProgressbar"):
            pb_bg = "#e2e8f0"
            pb_fill = custom_bg or COLOR_SELECTION
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=pb_bg, outline="#cbd5e1", tags=tags)
            val = float(props.get("value", 50))
            max_val = max(1.0, float(props.get("maximum", 100)))
            pct = min(1.0, max(0.0, val / max_val))
            fill_w = int(ww * pct)
            if fill_w > 0:
                self.canvas.create_rectangle(wx + 1, wy + 1, wx + fill_w, wy + wh - 1, fill=pb_fill, outline="", tags=tags)
                self.canvas.create_line(wx + 1, wy + 2, wx + fill_w, wy + 2, fill="#93c5fd", tags=tags)

        # -------------------------------------------------------------
        # Scale / TScale
        # -------------------------------------------------------------
        elif wtype in ("Scale", "TScale"):
            orient = props.get("orient", "horizontal")
            knob_color = custom_bg or COLOR_SELECTION
            if orient == "vertical":
                scx = wx + ww // 2
                self.canvas.create_line(scx, wy + 4, scx, wy + wh - 4, fill="#cbd5e1", width=4, tags=tags)
                ky = wy + wh // 2
                self.canvas.create_oval(scx - 7, ky - 7, scx + 7, ky + 7, fill=knob_color, outline="#ffffff", width=2, tags=tags)
            else:
                scy = wy + wh // 2
                self.canvas.create_line(wx + 4, scy, wx + ww - 4, scy, fill="#cbd5e1", width=4, tags=tags)
                kx = wx + ww // 2
                self.canvas.create_oval(kx - 7, scy - 7, kx + 7, scy + 7, fill=knob_color, outline="#ffffff", width=2, tags=tags)

        # -------------------------------------------------------------
        # Separator / TSeparator
        # -------------------------------------------------------------
        elif wtype in ("Separator", "TSeparator"):
            orient = props.get("orient", "horizontal")
            sep_col = custom_fg or "#cbd5e1"
            if orient == "vertical":
                cx = wx + ww // 2
                self.canvas.create_line(cx, wy, cx, wy + wh, fill=sep_col, width=1, tags=tags)
            else:
                cy = wy + wh // 2
                self.canvas.create_line(wx, cy, wx + ww, cy, fill=sep_col, width=1, tags=tags)

        # -------------------------------------------------------------
        # Frame / TFrame
        # -------------------------------------------------------------
        elif wtype in ("Frame", "TFrame"):
            f_bg = custom_bg or ("#f8fafc" if wtype == "Frame" else "#f1f5f9")
            f_border = "#cbd5e1"
            dash_pattern = (3, 3) if wtype == "Frame" else ()
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=f_bg, outline=f_border, dash=dash_pattern, tags=tags)
            lbl_text = f"[{wtype}: {w.name}]"
            self.canvas.create_text(wx + 6, wy + 8, text=lbl_text, fill="#94a3b8", anchor="w", font=(FONT_UI_FAMILY, 7), tags=tags)

        # -------------------------------------------------------------
        # LabelFrame / TLabelframe
        # -------------------------------------------------------------
        elif wtype in ("LabelFrame", "TLabelframe"):
            lf_bg = custom_bg or ""
            lf_fg = custom_fg or "#1e293b"
            title = text or ("Group Box" if wtype == "LabelFrame" else "TLabelframe")
            self.canvas.create_rectangle(wx, wy + 8, wx + ww, wy + wh, fill=lf_bg, outline="#cbd5e1", width=1, tags=tags)
            badge_w = len(title) * 7 + 12
            self.canvas.create_rectangle(wx + 8, wy, wx + 8 + badge_w, wy + 16, fill=COLOR_CANVAS_PAPER, outline="", tags=tags)
            self.canvas.create_text(wx + 14, wy + 8, text=title, fill=lf_fg, anchor="w", font=(FONT_UI_FAMILY, 8, "bold"), tags=tags)

        # -------------------------------------------------------------
        # Canvas
        # -------------------------------------------------------------
        elif wtype == "Canvas":
            c_bg = custom_bg or "#fafafa"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=c_bg, outline="#94a3b8", dash=(4, 3), tags=tags)
            self.canvas.create_text(
                wx + ww // 2, wy + wh // 2,
                text=f"[Canvas: {w.name}]", fill="#94a3b8", font=(FONT_UI_FAMILY, 8), tags=tags
            )

        # -------------------------------------------------------------
        # Spinbox / TSpinbox
        # -------------------------------------------------------------
        elif wtype in ("Spinbox", "TSpinbox"):
            sp_bg = custom_bg or "#ffffff"
            sp_fg = custom_fg or "#1e293b"
            btn_w = 18
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=sp_bg, outline="#94a3b8", tags=tags)
            val_str = text or str(props.get("from_", 0))
            self.canvas.create_text(wx + 6, wy + wh // 2, text=val_str, fill=sp_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags)
            bx1 = wx + ww - btn_w
            mid_y = wy + wh // 2
            self.canvas.create_rectangle(bx1, wy, wx + ww, mid_y, fill="#e2e8f0", outline="#94a3b8", tags=tags)
            self.canvas.create_rectangle(bx1, mid_y, wx + ww, wy + wh, fill="#e2e8f0", outline="#94a3b8", tags=tags)
            self.canvas.create_text(bx1 + btn_w // 2, wy + (mid_y - wy) // 2, text="▲", fill="#475569", font=(FONT_UI_FAMILY, 6), tags=tags)
            self.canvas.create_text(bx1 + btn_w // 2, mid_y + (wy + wh - mid_y) // 2, text="▼", fill="#475569", font=(FONT_UI_FAMILY, 6), tags=tags)

        # -------------------------------------------------------------
        # Message
        # -------------------------------------------------------------
        elif wtype == "Message":
            m_bg = custom_bg or "#f8fafc"
            m_fg = custom_fg or "#1e293b"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=m_bg, outline="#cbd5e1", tags=tags)
            msg_text = text or "Message: Multiline wrapped label text."
            self.canvas.create_text(
                wx + 6, wy + 6, text=msg_text, fill=m_fg,
                anchor="nw", width=max(20, ww - 12), font=(FONT_UI_FAMILY, 8), tags=tags
            )

        # -------------------------------------------------------------
        # Menubutton / TMenubutton
        # -------------------------------------------------------------
        elif wtype in ("Menubutton", "TMenubutton"):
            mb_bg = custom_bg or "#f0f0f4"
            mb_fg = custom_fg or "#1e293b"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=mb_bg, outline="#94a3b8", tags=tags)
            self.canvas.create_text(wx + 8, wy + wh // 2, text=text or "Menu", fill=mb_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags)
            self.canvas.create_text(wx + ww - 12, wy + wh // 2, text="▼", fill="#64748b", font=(FONT_UI_FAMILY, 7), tags=tags)

        # -------------------------------------------------------------
        # TNotebook / Notebook (Interactive Tab Container)
        # -------------------------------------------------------------
        elif wtype in ("TNotebook", "Notebook"):
            tabs = self._get_notebook_tabs(w)
            active_tab = self.get_active_tab(w)
            tab_h = 24
            content_y = wy + tab_h
            nb_bg = custom_bg or "#ffffff"

            # Content area
            self.canvas.create_rectangle(wx, content_y, wx + ww, wy + wh, fill=nb_bg, outline="#cbd5e1", tags=tags)

            # Render tabs along top
            cur_x = wx + 2
            self._tab_rects[w.id] = []
            for i, tab in enumerate(tabs):
                tid = tab["id"]
                ttxt = tab["text"]
                is_active = (tid == active_tab or ttxt == active_tab or (not active_tab and i == 0))
                tw = max(65, len(ttxt) * 8 + 18)
                tx2 = min(wx + ww - 2, cur_x + tw)
                if tx2 <= cur_x:
                    break

                t_fill = nb_bg if is_active else "#e2e8f0"
                t_fg = "#1e293b" if is_active else "#64748b"

                self.canvas.create_rectangle(
                    cur_x, wy, tx2, content_y + (1 if is_active else 0),
                    fill=t_fill, outline="#cbd5e1", tags=tags
                )
                if is_active:
                    self.canvas.create_line(cur_x + 1, wy, tx2 - 1, wy, fill=COLOR_SELECTION, width=2, tags=tags)
                self.canvas.create_text(
                    (cur_x + tx2) // 2, wy + tab_h // 2,
                    text=ttxt, fill=t_fg, font=(FONT_UI_FAMILY, 8, "bold" if is_active else "normal"), tags=tags
                )
                self._tab_rects[w.id].append((tid, cur_x, wy, tx2, content_y))
                cur_x = tx2 + 2

        # -------------------------------------------------------------
        # TPanedwindow
        # -------------------------------------------------------------
        elif wtype == "TPanedwindow":
            pw_bg = custom_bg or "#f8fafc"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=pw_bg, outline="#cbd5e1", tags=tags)
            orient = props.get("orient", "horizontal")
            if orient == "vertical":
                sash_y = wy + wh // 2
                self.canvas.create_line(wx, sash_y, wx + ww, sash_y, fill="#94a3b8", width=2, tags=tags)
                mid_x = wx + ww // 2
                self.canvas.create_rectangle(mid_x - 12, sash_y - 3, mid_x + 12, sash_y + 3, fill="#cbd5e1", outline="#94a3b8", tags=tags)
            else:
                sash_x = wx + ww // 2
                self.canvas.create_line(sash_x, wy, sash_x, wy + wh, fill="#94a3b8", width=2, tags=tags)
                mid_y = wy + wh // 2
                self.canvas.create_rectangle(sash_x - 3, mid_y - 12, sash_x + 3, mid_y + 12, fill="#cbd5e1", outline="#94a3b8", tags=tags)

        # -------------------------------------------------------------
        # TSizegrip
        # -------------------------------------------------------------
        elif wtype == "TSizegrip":
            self.canvas.create_line(wx + ww - 3, wy + wh - 11, wx + ww - 11, wy + wh - 3, fill="#64748b", width=1.5, tags=tags)
            self.canvas.create_line(wx + ww - 3, wy + wh - 7, wx + ww - 7, wy + wh - 3, fill="#64748b", width=1.5, tags=tags)
            self.canvas.create_line(wx + ww - 3, wy + wh - 3, wx + ww - 4, wy + wh - 3, fill="#64748b", width=1.5, tags=tags)

        # -------------------------------------------------------------
        # Treeview / Scrolledtreeview
        # -------------------------------------------------------------
        elif wtype == "Treeview":
            tv_bg = custom_bg or "#ffffff"
            tv_fg = custom_fg or "#1e293b"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=tv_bg, outline="#94a3b8", tags=tags)
            hdr_h = 22
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + hdr_h, fill="#f1f5f9", outline="#94a3b8", tags=tags)
            cols = props.get("columns", ["Col 1", "Col 2"])
            col_w = max(40, ww // max(1, len(cols)))
            for i, col in enumerate(cols):
                cx1 = wx + i * col_w
                cx2 = min(wx + ww, cx1 + col_w)
                self.canvas.create_line(cx2, wy, cx2, wy + wh, fill="#e2e8f0", tags=tags)
                self.canvas.create_text(cx1 + 6, wy + hdr_h // 2, text=str(col), fill="#475569", anchor="w", font=(FONT_UI_FAMILY, 8, "bold"), tags=tags)
            for r in range(1, 4):
                ry = wy + hdr_h + (r * 18)
                if ry < wy + wh:
                    self.canvas.create_line(wx, ry, wx + ww, ry, fill="#f1f5f9", tags=tags)
                    self.canvas.create_text(wx + 8, ry - 9, text=f"Data row {r}", fill=tv_fg, anchor="w", font=(FONT_UI_FAMILY, 8), tags=tags)

        elif wtype == "Scrolledtreeview":
            sb_w = 16
            tv_bg = custom_bg or "#ffffff"
            tv_fg = custom_fg or "#1e293b"
            main_w = max(20, ww - sb_w)
            self.canvas.create_rectangle(wx, wy, wx + main_w, wy + wh, fill=tv_bg, outline="#94a3b8", tags=tags)
            hdr_h = 22
            self.canvas.create_rectangle(wx, wy, wx + main_w, wy + hdr_h, fill="#f1f5f9", outline="#94a3b8", tags=tags)
            cols = props.get("columns", ["Col 1", "Col 2"])
            col_w = max(40, main_w // max(1, len(cols)))
            for i, col in enumerate(cols):
                cx1 = wx + i * col_w
                cx2 = min(wx + main_w, cx1 + col_w)
                self.canvas.create_line(cx2, wy, cx2, wy + wh, fill="#e2e8f0", tags=tags)
                self.canvas.create_text(cx1 + 6, wy + hdr_h // 2, text=str(col), fill="#475569", anchor="w", font=(FONT_UI_FAMILY, 8, "bold"), tags=tags)
            sx1 = wx + main_w
            self.canvas.create_rectangle(sx1, wy, wx + ww, wy + wh, fill="#f8fafc", outline="#94a3b8", tags=tags)
            self.canvas.create_text(sx1 + sb_w // 2, wy + 7, text="▲", fill="#64748b", font=(FONT_UI_FAMILY, 6), tags=tags)
            self.canvas.create_text(sx1 + sb_w // 2, wy + wh - 7, text="▼", fill="#64748b", font=(FONT_UI_FAMILY, 6), tags=tags)
            self.canvas.create_rectangle(sx1 + 2, wy + 16, wx + ww - 2, wy + min(wh - 16, 45), fill="#cbd5e1", outline="", tags=tags)

        # -------------------------------------------------------------
        # Scrolledentry
        # -------------------------------------------------------------
        elif wtype == "Scrolledentry":
            e_bg = custom_bg or "#ffffff"
            e_fg = custom_fg or "#1e293b"
            sb_h = 7
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh - sb_h, fill=e_bg, outline="#94a3b8", tags=tags)
            self.canvas.create_text(wx + 6, wy + (wh - sb_h) // 2, text=text or "", fill=e_fg, anchor="w", font=(FONT_UI_FAMILY, 9), tags=tags)
            sy1 = wy + wh - sb_h
            self.canvas.create_rectangle(wx, sy1, wx + ww, wy + wh, fill="#f1f5f9", outline="#94a3b8", tags=tags)
            self.canvas.create_rectangle(wx + 4, sy1 + 1, wx + max(15, ww // 3), wy + wh - 1, fill="#94a3b8", outline="", tags=tags)

        # -------------------------------------------------------------
        # Scrolledwindow
        # -------------------------------------------------------------
        elif wtype == "Scrolledwindow":
            sw_bg = custom_bg or "#ffffff"
            sb_size = 14
            main_w = max(20, ww - sb_size)
            main_h = max(20, wh - sb_size)
            self.canvas.create_rectangle(wx, wy, wx + main_w, wy + main_h, fill=sw_bg, outline="#94a3b8", tags=tags)
            self.canvas.create_text(wx + main_w // 2, wy + main_h // 2, text=f"[ScrolledWindow: {w.name}]", fill="#94a3b8", font=(FONT_UI_FAMILY, 8), tags=tags)
            # V scrollbar
            self.canvas.create_rectangle(wx + main_w, wy, wx + ww, wy + main_h, fill="#f8fafc", outline="#94a3b8", tags=tags)
            self.canvas.create_rectangle(wx + main_w + 2, wy + 10, wx + ww - 2, wy + min(main_h - 10, 40), fill="#cbd5e1", outline="", tags=tags)
            # H scrollbar
            self.canvas.create_rectangle(wx, wy + main_h, wx + main_w, wy + wh, fill="#f8fafc", outline="#94a3b8", tags=tags)
            self.canvas.create_rectangle(wx + 10, wy + main_h + 2, wx + min(main_w - 10, 40), wy + wh - 2, fill="#cbd5e1", outline="", tags=tags)
            # Corner
            self.canvas.create_rectangle(wx + main_w, wy + main_h, wx + ww, wy + wh, fill="#e2e8f0", outline="#94a3b8", tags=tags)

        # -------------------------------------------------------------
        # Custom Widget
        # -------------------------------------------------------------
        elif wtype == "Custom":
            c_bg = custom_bg or "#f5f3ff"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=c_bg, outline="#6366f1", dash=(4, 2), tags=tags)
            cls_name = props.get("class_name") or text or "CustomWidget"
            self.canvas.create_text(
                wx + ww // 2, wy + wh // 2 - 6,
                text=f"<{cls_name}>", fill="#4f46e5", font=(FONT_UI_FAMILY, 9, "bold"), tags=tags
            )
            mod_name = props.get("module_name", "")
            if mod_name:
                self.canvas.create_text(
                    wx + ww // 2, wy + wh // 2 + 10,
                    text=mod_name, fill="#6366f1", font=(FONT_UI_FAMILY, 7), tags=tags
                )

        # -------------------------------------------------------------
        # Toplevel Window
        # -------------------------------------------------------------
        elif wtype == "Toplevel":
            top_bg = custom_bg or "#f8fafc"
            tb_h = 22
            # Drop shadow
            self.canvas.create_rectangle(wx + 3, wy + 3, wx + ww + 3, wy + wh + 3, fill="#0f172a", outline="", tags=tags)
            # Titlebar
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + tb_h, fill="#334155", outline="#1e293b", tags=tags)
            title_str = props.get("title", text or "Toplevel Window")
            self.canvas.create_text(wx + 8, wy + tb_h // 2, text=title_str, fill="#f8fafc", anchor="w", font=(FONT_UI_FAMILY, 8, "bold"), tags=tags)
            self.canvas.create_text(wx + ww - 10, wy + tb_h // 2, text="✕", fill="#cbd5e1", font=(FONT_UI_FAMILY, 7), tags=tags)
            self.canvas.create_text(wx + ww - 24, wy + tb_h // 2, text="□", fill="#cbd5e1", font=(FONT_UI_FAMILY, 7), tags=tags)
            self.canvas.create_text(wx + ww - 38, wy + tb_h // 2, text="—", fill="#cbd5e1", font=(FONT_UI_FAMILY, 7), tags=tags)
            # Client body
            self.canvas.create_rectangle(wx, wy + tb_h, wx + ww, wy + wh, fill=top_bg, outline="#334155", tags=tags)

        # -------------------------------------------------------------
        # Popupmenu
        # -------------------------------------------------------------
        elif wtype == "Popupmenu":
            pm_bg = custom_bg or "#ffffff"
            self.canvas.create_rectangle(wx + 2, wy + 2, wx + ww + 2, wy + wh + 2, fill="#000000", outline="", stipple="gray25", tags=tags)
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=pm_bg, outline="#cbd5e1", tags=tags)
            menu_items = ["Menu Item 1", "Menu Item 2", "---", "Menu Item 3"]
            for idx, m_item in enumerate(menu_items):
                my = wy + 4 + (idx * 16)
                if my < wy + wh:
                    if m_item == "---":
                        self.canvas.create_line(wx + 4, my + 8, wx + ww - 4, my + 8, fill="#e2e8f0", tags=tags)
                    else:
                        self.canvas.create_text(wx + 10, my + 8, text=m_item, fill="#1e293b", anchor="w", font=(FONT_UI_FAMILY, 8), tags=tags)

        # -------------------------------------------------------------
        # Generic Fallback
        # -------------------------------------------------------------
        else:
            gen_bg = custom_bg or "#f5f5f9"
            gen_fg = custom_fg or "#444450"
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=gen_bg, outline="#a0a0ab", tags=tags)
            self.canvas.create_text(
                wx + ww // 2, wy + wh // 2,
                text=text or f"[{wtype}]", fill=gen_fg, font=(FONT_UI_FAMILY, 8), tags=tags
            )

    # --------------------------------------------------------------------------
    # Selection & Handles Rendering (with Lock Badge)
    # --------------------------------------------------------------------------

    def _render_selection_handles(self, w: WidgetInstance):
        """Draws bounding box, lock indicator badge, and 8 handles around active selection."""
        if not self.is_widget_visible(w):
            return

        wx, wy, ww, wh = self.get_canvas_bounds(w)

        # Bounding box
        box_color = "#e63946" if w.locked else COLOR_SELECTION
        self.canvas.create_rectangle(
            wx - 1, wy - 1, wx + ww + 1, wy + wh + 1,
            outline=box_color, width=2, tags="selection"
        )

        # Coordinate badge
        lock_str = " [🔒 LOCKED]" if w.locked else ""
        badge_text = f"{w.name}{lock_str}  ({w.x}, {w.y}) {w.width}x{w.height}"
        self.canvas.create_text(
            wx, wy - 10,
            text=badge_text,
            fill=box_color,
            anchor="w",
            font=(FONT_UI_FAMILY, 8, "bold"),
            tags="selection"
        )

        # Lock badge in corner of selection handles
        if w.locked:
            badge_w = 26
            badge_h = 16
            bx1 = wx + ww - badge_w
            by1 = wy - badge_h - 2
            bx2 = wx + ww
            by2 = wy - 2
            self.canvas.create_rectangle(
                bx1, by1, bx2, by2,
                fill="#e63946", outline="#ffffff", width=1, tags="selection"
            )
            self.canvas.create_text(
                (bx1 + bx2) // 2, (by1 + by2) // 2,
                text="[🔒]", fill="#ffffff",
                font=(FONT_UI_FAMILY, 7, "bold"), tags="selection"
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
        handle_fill = "#fca5a5" if w.locked else COLOR_HANDLE_FILL
        handle_outline = "#e63946" if w.locked else COLOR_HANDLE_OUTLINE
        for h_name, (hx, hy) in handles.items():
            self.canvas.create_rectangle(
                hx - hs, hy - hs, hx + hs, hy + hs,
                fill=handle_fill,
                outline=handle_outline,
                width=1.5,
                tags=("selection", f"handle_{h_name}")
            )

    def _get_handle_at(self, cx: int, cy: int) -> Optional[str]:
        """Checks if mouse is over any resize handle of the selected widget."""
        w = self.state.get_selected_widget()
        if not w or not self.is_widget_visible(w):
            return None
        wx, wy, ww, wh = self.get_canvas_bounds(w)

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

    # --------------------------------------------------------------------------
    # Event Handlers: Dragging, Resizing & Placement
    # --------------------------------------------------------------------------

    def _on_mouse_down(self, event):
        self.canvas.focus_set()
        cx = int(self.canvas.canvasx(event.x))
        cy = int(self.canvas.canvasy(event.y))

        # 1. Placement mode active: Drop widget & auto-parent to container if clicked inside
        if self.pending_widget_type:
            container = self._get_container_at(cx, cy)
            if container:
                cont_x, cont_y, cont_w, cont_h = self.get_canvas_bounds(container)
                local_x = max(0, cx - cont_x)
                local_y = max(0, cy - cont_y)
                new_widget = WidgetInstance.create(
                    self.pending_widget_type, local_x, local_y, parent_id=container.id
                )
                if container.widget_type in ("TNotebook", "Notebook"):
                    new_widget.container_tab_or_pane = self.get_active_tab(container)
            else:
                rx = cx - self.offset_x
                ry = cy - self.offset_y
                rx = max(0, min(rx, self.state.width - 20))
                ry = max(0, min(ry, self.state.height - 20))
                new_widget = WidgetInstance.create(self.pending_widget_type, rx, ry)

            self.state.add_widget(new_widget)
            self.set_pending_placement(None)
            return

        # 2. Check if clicked a resize handle
        handle = self._get_handle_at(cx, cy)
        selected = self.state.get_selected_widget()
        if handle and selected and not selected.locked:
            self.drag_mode = "resize"
            self.active_handle = handle
            self.drag_start_x = cx
            self.drag_start_y = cy
            self.orig_geom = {selected.id: (selected.x, selected.y, selected.width, selected.height)}
            return

        # 3. Check if clicked an interactive notebook tab header
        nb_hit = self._get_notebook_tab_at(cx, cy)
        if nb_hit:
            nb, tab_id = nb_hit
            self.notebook_active_tabs[nb.id] = tab_id
            nb.properties["active_tab"] = tab_id
            self.state.select_widget(nb.id)
            self.render()
            return

        # 4. Check if clicked a widget
        clicked_widget = self._get_widget_at(cx, cy)
        if clicked_widget:
            is_shift = (event.state & 0x0001) != 0
            self.state.select_widget(clicked_widget.id, additive=is_shift)
            self.drag_mode = "move"
            self.drag_start_x = cx
            self.drag_start_y = cy
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

        cx = int(self.canvas.canvasx(event.x))
        cy = int(self.canvas.canvasy(event.y))

        dx = cx - self.drag_start_x
        dy = cy - self.drag_start_y

        if self.drag_mode == "move":
            # Only directly update selected widgets whose parent is NOT also selected.
            # Child widgets will automatically visually move because of cumulative coordinates!
            active_ids = [
                wid for wid in self.state.selected_ids
                if not self._has_selected_ancestor(wid)
            ]
            for wid in active_ids:
                if wid not in self.orig_geom:
                    continue
                w = self.state.widgets.get(wid)
                if not w or w.locked:
                    continue
                ox, oy, ow, oh = self.orig_geom[wid]
                max_cw, max_ch = self._get_parent_container_dimensions(w)
                max_x = max(0, max_cw - ow)
                max_y = max(0, max_ch - oh)
                new_x = max(0, min(ox + dx, max_x))
                new_y = max(0, min(oy + dy, max_y))
                self.state.update_widget_geometry(wid, new_x, new_y, ow, oh, commit=False)

        elif self.drag_mode == "resize" and self.active_handle:
            w = self.state.get_selected_widget()
            if not w or w.locked or w.id not in self.orig_geom:
                return
            ox, oy, ow, oh = self.orig_geom[w.id]
            h = self.active_handle

            max_cw, max_ch = self._get_parent_container_dimensions(w)
            min_size = 15

            new_x, new_y, new_w, new_h = ox, oy, ow, oh

            if "e" in h:
                max_w = max(min_size, max_cw - ox)
                new_w = max(min_size, min(ow + dx, max_w))
            if "s" in h:
                max_h = max(min_size, max_ch - oy)
                new_h = max(min_size, min(oh + dy, max_h))
            if "w" in h:
                right_edge = ox + ow
                new_x = max(0, min(ox + dx, right_edge - min_size))
                new_w = right_edge - new_x
            if "n" in h:
                bottom_edge = oy + oh
                new_y = max(0, min(oy + dy, bottom_edge - min_size))
                new_h = bottom_edge - new_y

            self.state.update_widget_geometry(w.id, new_x, new_y, new_w, new_h, commit=False)

    def _on_mouse_up(self, event):
        if self.drag_mode:
            self.drag_mode = None
            self.active_handle = None
            self.orig_geom.clear()
            self.state.is_dragging = False
            self.state.push_state()

    def _on_mouse_hover(self, event):
        if self.drag_mode or self.pending_widget_type:
            return
        cx = int(self.canvas.canvasx(event.x))
        cy = int(self.canvas.canvasy(event.y))
        handle = self._get_handle_at(cx, cy)
        selected = self.state.get_selected_widget()
        if handle and selected and not selected.locked:
            cursors = {
                "nw": "top_left_corner", "se": "bottom_right_corner",
                "ne": "top_right_corner", "sw": "bottom_left_corner",
                "n": "top_side", "s": "bottom_side",
                "e": "right_side", "w": "left_side"
            }
            self.canvas.config(cursor=cursors.get(handle, "cross"))
        elif self._get_notebook_tab_at(cx, cy):
            self.canvas.config(cursor="hand2")
        elif self._get_widget_at(cx, cy):
            self.canvas.config(cursor="fleur")
        else:
            self.canvas.config(cursor="arrow")

    def _on_delete_key(self, event=None):
        if self._is_text_editing(event):
            return
        if self.state.selected_ids:
            self.state.remove_selected()

    def _nudge_selected(self, dx: int, dy: int, event):
        if self._is_text_editing(event):
            return
        if not self.state.selected_ids:
            return
        step = 10 if (event.state & 0x0001) else 1
        active_ids = [
            wid for wid in self.state.selected_ids
            if not self._has_selected_ancestor(wid)
        ]
        for wid in active_ids:
            w = self.state.widgets.get(wid)
            if not w or w.locked:
                continue
            max_cw, max_ch = self._get_parent_container_dimensions(w)
            max_x = max(0, max_cw - w.width)
            max_y = max(0, max_ch - w.height)
            new_x = max(0, min(w.x + dx * step, max_x))
            new_y = max(0, min(w.y + dy * step, max_y))
            self.state.update_widget_geometry(
                wid, new_x, new_y,
                w.width, w.height, commit=False, snap=False
            )
        self.state.push_state()

