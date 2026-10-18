"""
PageStudio - Property & Event Inspector
Right-hand sidebar allowing developers to inspect and modify properties,
geometry coordinates, names, and event callbacks in real time.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any
from ..core.state import ProjectState
from ..core.models import WidgetInstance
from ..ui.theme import COLOR_BG_PANEL, COLOR_ACCENT, FONT_UI_FAMILY

class PropertyInspector(tk.Frame):
    """Real-time property and callback editor."""

    def __init__(self, parent, state: ProjectState, **kwargs):
        super().__init__(parent, bg=COLOR_BG_PANEL, **kwargs)
        self.state = state
        self._updating: bool = False
        
        self._build_ui()
        self.state.add_listener(self.refresh)

    def _build_ui(self):
        # Header
        self.header_label = tk.Label(
            self,
            text="PROPERTIES",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=12,
            pady=10
        )
        self.header_label.pack(fill="x")

        # Scrollable container
        canvas = tk.Canvas(self, bg=COLOR_BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.content = tk.Frame(canvas, bg=COLOR_BG_PANEL)

        self.content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.content, anchor="nw", width=220)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def refresh(self):
        """Rebuilds property form fields based on active selection."""
        if self._updating:
            return
            
        # Clear existing fields
        for widget in self.content.winfo_children():
            widget.destroy()

        selected = self.state.get_selected_widget()
        if selected:
            self.header_label.config(text=f"PROPERTIES: {selected.widget_type.upper()}")
            self._render_widget_inspector(selected)
        else:
            self.header_label.config(text="WINDOW SETTINGS")
            self._render_window_inspector()

    def _render_window_inspector(self):
        """Displays window level properties (Title, Size, Resizable, Grid)."""
        self._add_section_header("Window Geometry")
        
        # Title
        self._add_entry("Title", self.state.title, self._on_window_title_change)
        
        # Width & Height
        self._add_entry("Width", str(self.state.width), self._on_window_width_change)
        self._add_entry("Height", str(self.state.height), self._on_window_height_change)
        
        self._add_section_header("Canvas Grid")
        self._add_checkbox("Snap to Grid", self.state.snap_to_grid, self._on_snap_grid_change)
        self._add_entry("Grid Size (px)", str(self.state.grid_size), self._on_grid_size_change)

    def _render_widget_inspector(self, w: WidgetInstance):
        """Displays widget identification, geometry, and properties."""
        self._add_section_header("Identification")
        self._add_entry("Name", w.name, lambda val: self._on_widget_name_change(w, val))

        self._add_section_header("Geometry (Absolute)")
        self._add_entry("X", str(w.x), lambda val: self._on_geom_change(w, "x", val))
        self._add_entry("Y", str(w.y), lambda val: self._on_geom_change(w, "y", val))
        self._add_entry("Width", str(w.width), lambda val: self._on_geom_change(w, "width", val))
        self._add_entry("Height", str(w.height), lambda val: self._on_geom_change(w, "height", val))

        self._add_section_header("Attributes")
        if "text" in w.properties:
            self._add_entry("Text", w.properties.get("text", ""), lambda val: self._on_prop_change(w, "text", val))

        if "variable" in w.properties:
            self._add_entry("Variable", w.properties.get("variable", ""), lambda val: self._on_prop_change(w, "variable", val))

        if "value" in w.properties:
            self._add_entry("Value", str(w.properties.get("value", "")), lambda val: self._on_prop_change(w, "value", val))

        if "values" in w.properties:
            vals_str = ", ".join(w.properties.get("values", []))
            self._add_entry("Options (csv)", vals_str, lambda val: self._on_prop_change(w, "values", [s.strip() for s in val.split(",")]))

        if "show" in w.properties:
            self._add_entry("Show (Password)", w.properties.get("show", ""), lambda val: self._on_prop_change(w, "show", val))

        if "maximum" in w.properties:
            self._add_entry("Maximum", str(w.properties.get("maximum", 100)), lambda val: self._on_prop_change(w, "maximum", int(val) if val.isdigit() else 100))

        if "value" in w.properties and w.widget_type == "Progressbar":
            self._add_entry("Value", str(w.properties.get("value", 50)), lambda val: self._on_prop_change(w, "value", int(val) if val.isdigit() else 50))

        # Events & Callbacks
        self._add_section_header("Event Callbacks")
        if "command" in w.events:
            self._add_entry("command", w.events.get("command", ""), lambda val: self._on_event_change(w, "command", val))

        for evt, handler in w.events.items():
            if evt != "command":
                self._add_entry(evt, handler, lambda val, e=evt: self._on_event_change(w, e, val))

        # Delete Button
        del_btn = tk.Button(
            self.content,
            text="Delete Widget",
            bg="#d90429",
            fg="#ffffff",
            activebackground="#ef233c",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 9, "bold"),
            pady=4,
            cursor="hand2",
            command=self.state.remove_selected
        )
        del_btn.pack(fill="x", padx=12, pady=16)

    # --------------------------------------------------------------------------
    # UI Component Helpers
    # --------------------------------------------------------------------------

    def _add_section_header(self, title: str):
        lbl = tk.Label(
            self.content,
            text=title.upper(),
            bg=COLOR_BG_PANEL,
            fg="#5f5f70",
            font=(FONT_UI_FAMILY, 8, "bold"),
            anchor="w",
            padx=12,
            pady=8
        )
        lbl.pack(fill="x")

    def _add_entry(self, label_text: str, current_val: str, on_change):
        row = tk.Frame(self.content, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=3)

        lbl = tk.Label(
            row, text=label_text, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            font=(FONT_UI_FAMILY, 8), width=12, anchor="w"
        )
        lbl.pack(side="left")

        var = tk.StringVar(value=current_val)
        entry = tk.Entry(
            row, textvariable=var, bg="#1a1a20", fg="#ffffff",
            insertbackground="#ffffff", relief="flat", font=(FONT_UI_FAMILY, 9)
        )
        entry.pack(side="right", fill="x", expand=True)

        def _handle_focus_out(event):
            val = var.get()
            on_change(val)

        entry.bind("<FocusOut>", _handle_focus_out)
        entry.bind("<Return>", lambda e: (on_change(var.get()), entry.select_range(0, "end")))

    def _add_checkbox(self, label_text: str, current_val: bool, on_change):
        row = tk.Frame(self.content, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=4)

        var = tk.BooleanVar(value=current_val)
        chk = tk.Checkbutton(
            row, text=label_text, variable=var, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            activebackground=COLOR_BG_PANEL, activeforeground="#ffffff",
            selectcolor="#1a1a20", font=(FONT_UI_FAMILY, 8),
            command=lambda: on_change(var.get())
        )
        chk.pack(anchor="w")

    # --------------------------------------------------------------------------
    # Value Change Mutators
    # --------------------------------------------------------------------------

    def _on_window_title_change(self, val: str):
        self.state.title = val
        self.state.push_state()

    def _on_window_width_change(self, val: str):
        if val.isdigit() and int(val) >= 100:
            self.state.width = int(val)
            self.state.push_state()

    def _on_window_height_change(self, val: str):
        if val.isdigit() and int(val) >= 100:
            self.state.height = int(val)
            self.state.push_state()

    def _on_snap_grid_change(self, val: bool):
        self.state.snap_to_grid = val
        self.state.push_state()

    def _on_grid_size_change(self, val: str):
        if val.isdigit() and int(val) >= 2:
            self.state.grid_size = int(val)
            self.state.push_state()

    def _on_widget_name_change(self, w: WidgetInstance, val: str):
        clean_name = val.strip().replace(" ", "_")
        if clean_name:
            w.name = clean_name
            self.state.push_state()

    def _on_geom_change(self, w: WidgetInstance, prop: str, val: str):
        if not val.isdigit():
            return
        v = int(val)
        if prop == "x":
            w.x = max(0, v)
        elif prop == "y":
            w.y = max(0, v)
        elif prop == "width":
            w.width = max(10, v)
        elif prop == "height":
            w.height = max(10, v)
        self.state.push_state()

    def _on_prop_change(self, w: WidgetInstance, prop: str, val: Any):
        w.properties[prop] = val
        self.state.push_state()

    def _on_event_change(self, w: WidgetInstance, event_name: str, val: str):
        clean_handler = val.strip().replace(" ", "_")
        w.events[event_name] = clean_handler
        self.state.push_state()
