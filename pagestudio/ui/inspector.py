"""
PageStudio - Property & Event Inspector
Right-hand sidebar allowing developers to inspect and modify properties,
geometry coordinates, names, appearance, typography, and event callbacks in real time.
Organized into 6 collapsible sections matching PAGE specifications.
"""

import tkinter as tk
from tkinter import ttk
import tkinter.colorchooser as colorchooser
from typing import Optional, Dict, Any, List
from ..core.state import ProjectState
from ..core.models import WidgetInstance, WIDGET_CATALOG
from ..ui.theme import COLOR_BG_PANEL, FONT_UI_FAMILY
from .font_chooser import FontChooserDialog
from .menu_editor import MenuEditorDialog
from .notebook_editor import NotebookTabEditorDialog
from .treeview_editor import TreeviewColumnEditorDialog
from ..utils.helpers import IS_MAC


class PropertyInspector(tk.Frame):
    """Real-time property, geometry, appearance, and callback editor with 6 collapsible sections."""

    def __init__(self, parent, state: ProjectState, **kwargs):
        super().__init__(parent, bg=COLOR_BG_PANEL, **kwargs)
        self.state = state
        self._updating: bool = False

        # Persistent collapse/expand states across refreshes
        self.section_expanded: Dict[str, bool] = {
            "identification": True,
            "geometry": True,
            "appearance": True,
            "text": True,
            "behavior": True,
            "specific": True,
            "win_geometry": True,
            "win_grid": True,
            "win_menu": True,
        }

        self._build_ui()
        self.state.add_listener(self.refresh)
        self.refresh()

    def _build_ui(self):
        # Header label
        self.header_label = tk.Label(
            self,
            text="WINDOW SETTINGS",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=12,
            pady=10
        )
        self.header_label.pack(fill="x")

        # Scrollable container
        self.canvas = tk.Canvas(self, bg=COLOR_BG_PANEL, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=COLOR_BG_PANEL)

        self.content.bind(
            "<Configure>",
            lambda e: self._update_scroll_region()
        )
        self._canvas_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw", width=250)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._canvas_window, width=e.width)
        )

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Mousewheel scrolling across platforms (Windows, macOS, Linux)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_linux_scroll_up)
        self.canvas.bind("<Button-5>", self._on_linux_scroll_down)
        self.content.bind("<MouseWheel>", self._on_mousewheel)
        self.content.bind("<Button-4>", self._on_linux_scroll_up)
        self.content.bind("<Button-5>", self._on_linux_scroll_down)

        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_linux_scroll_up, add="+")
        self.bind_all("<Button-5>", self._on_linux_scroll_down, add="+")

    def _is_mouse_over(self) -> bool:
        try:
            x, y = self.winfo_pointerxy()
            widget_under = self.winfo_containing(x, y)
            return widget_under is not None and (widget_under == self or str(widget_under).startswith(str(self)))
        except Exception:
            return False

    def _on_mousewheel(self, event):
        if not self._is_mouse_over():
            return
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

    def _on_linux_scroll_up(self, event):
        if self._is_mouse_over():
            self.canvas.yview_scroll(-1, "units")

    def _on_linux_scroll_down(self, event):
        if self._is_mouse_over():
            self.canvas.yview_scroll(1, "units")


    def _update_scroll_region(self):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

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

        self.content.update_idletasks()
        self._update_scroll_region()

    # --------------------------------------------------------------------------
    # Collapsible Section Component
    # --------------------------------------------------------------------------
    def _create_collapsible_section(self, section_key: str, title: str) -> tk.Frame:
        """Creates a collapsible section container with clickable toggle header."""
        is_open = self.section_expanded.get(section_key, True)

        sec_container = tk.Frame(self.content, bg=COLOR_BG_PANEL)
        sec_container.pack(fill="x", padx=6, pady=(4, 2))

        # Header bar
        header_bar = tk.Frame(sec_container, bg="#23232f", cursor="hand2")
        header_bar.pack(fill="x", ipady=3)

        arrow_text = "▼" if is_open else "▶"
        arrow_lbl = tk.Label(
            header_bar,
            text=arrow_text,
            bg="#23232f",
            fg="#9d9dae",
            font=(FONT_UI_FAMILY, 8),
            width=2
        )
        arrow_lbl.pack(side="left", padx=(6, 2))

        title_lbl = tk.Label(
            header_bar,
            text=title.upper(),
            bg="#23232f",
            fg="#e0e0ee",
            font=(FONT_UI_FAMILY, 8, "bold"),
            anchor="w"
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        body_frame = tk.Frame(sec_container, bg=COLOR_BG_PANEL)
        if is_open:
            body_frame.pack(fill="x", pady=(4, 6))

        def _toggle(event=None):
            new_state = not self.section_expanded.get(section_key, True)
            self.section_expanded[section_key] = new_state
            if new_state:
                arrow_lbl.config(text="▼")
                body_frame.pack(fill="x", pady=(4, 6))
            else:
                arrow_lbl.config(text="▶")
                body_frame.pack_forget()
            self.content.update_idletasks()
            self._update_scroll_region()

        header_bar.bind("<Button-1>", _toggle)
        arrow_lbl.bind("<Button-1>", _toggle)
        title_lbl.bind("<Button-1>", _toggle)

        return body_frame

    # --------------------------------------------------------------------------
    # Window Inspector (No widget selected)
    # --------------------------------------------------------------------------
    def _render_window_inspector(self):
        """Displays window level properties (Title, Size, Resizable, Grid, Menubar)."""
        sec_geom = self._create_collapsible_section("win_geometry", "Window Geometry")
        self._add_entry(sec_geom, "Title", self.state.title, self._on_window_title_change)
        self._add_entry(sec_geom, "Width", str(self.state.width), self._on_window_width_change)
        self._add_entry(sec_geom, "Height", str(self.state.height), self._on_window_height_change)
        self._add_checkbox(sec_geom, "Resizable X", self.state.resizable_x, lambda val: self._on_window_resizable(val, "x"))
        self._add_checkbox(sec_geom, "Resizable Y", self.state.resizable_y, lambda val: self._on_window_resizable(val, "y"))

        sec_grid = self._create_collapsible_section("win_grid", "Canvas Grid")
        self._add_checkbox(sec_grid, "Snap to Grid", self.state.snap_to_grid, self._on_snap_grid_change)
        self._add_entry(sec_grid, "Grid Size (px)", str(self.state.grid_size), self._on_grid_size_change)

        sec_menu = self._create_collapsible_section("win_menu", "Application Menubar")
        btn_menu = tk.Button(
            sec_menu,
            text="Edit Menubar...",
            bg="#2c2c3c",
            fg="#ffffff",
            activebackground="#3e3e52",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 8, "bold"),
            pady=4,
            cursor="hand2",
            command=self._on_edit_root_menu
        )
        btn_menu.pack(fill="x", padx=12, pady=6)

    def _on_window_resizable(self, val: bool, axis: str):
        if axis == "x":
            self.state.resizable_x = val
        else:
            self.state.resizable_y = val
        self.state.push_state()

    def _on_edit_root_menu(self):
        initial_spec = self.state.menus.get("main_menu")

        def on_save(saved_spec):
            self.state.menus["main_menu"] = saved_spec
            self.state.push_state()

        MenuEditorDialog.edit_menu(self.winfo_toplevel(), initial_spec=initial_spec, on_save=on_save)

    # --------------------------------------------------------------------------
    # Widget Inspector (6 Collapsible Sections)
    # --------------------------------------------------------------------------
    def _render_widget_inspector(self, w: WidgetInstance):
        """Renders the 6 clean collapsible sections for a selected widget."""
        # 1. IDENTIFICATION
        self._render_section_identification(w)

        # 2. GEOMETRY
        self._render_section_geometry(w)

        # 3. APPEARANCE
        self._render_section_appearance(w)

        # 4. TEXT & TYPOGRAPHY
        self._render_section_text(w)

        # 5. BEHAVIOR & BINDINGS
        self._render_section_behavior(w)

        # 6. WIDGET-SPECIFIC EDITORS
        self._render_section_specific(w)

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
            pady=5,
            cursor="hand2",
            command=self.state.remove_selected
        )
        del_btn.pack(fill="x", padx=12, pady=16)

    # --- SECTION 1: IDENTIFICATION ---
    def _render_section_identification(self, w: WidgetInstance):
        body = self._create_collapsible_section("identification", "Identification")

        # Name / Alias (auto-replaces spaces with _)
        self._add_entry(body, "Name", w.name, lambda val: self._on_widget_name_change(w, val))

        # Class (Read-only)
        spec = WIDGET_CATALOG.get(w.widget_type)
        class_name = spec.display_name if spec else f"ttk.{w.widget_type}"
        self._add_readonly_text(body, "Class", class_name)

        # Widget Type (Read-only)
        self._add_readonly_text(body, "Widget Type", w.widget_type)

        # Parent Container Dropdown
        container_options: Dict[str, Optional[str]] = {"Root (Canvas)": None}
        for wid, other in self.state.widgets.items():
            if wid == w.id:
                continue
            ospec = WIDGET_CATALOG.get(other.widget_type)
            if ospec and ospec.is_container and self.state.is_valid_parent(w.id, other.id):
                label = f"{other.name} ({other.widget_type})"
                container_options[label] = other.id

        current_label = "Root (Canvas)"
        if w.parent_id:
            for lbl, cid in container_options.items():
                if cid == w.parent_id:
                    current_label = lbl
                    break

        def on_parent_selected(selected_lbl: str):
            new_parent_id = container_options.get(selected_lbl)
            if w.parent_id != new_parent_id:
                try:
                    self.state.set_widget_parent(w.id, new_parent_id)
                except ValueError:
                    pass

        self._add_dropdown(body, "Parent", current_label, list(container_options.keys()), on_parent_selected)

    # --- SECTION 2: GEOMETRY ---
    def _render_section_geometry(self, w: WidgetInstance):
        body = self._create_collapsible_section("geometry", "Geometry")

        # Mode: Toggle between Absolute and Relative
        mode_row = tk.Frame(body, bg=COLOR_BG_PANEL)
        mode_row.pack(fill="x", padx=12, pady=3)

        mode_lbl = tk.Label(
            mode_row, text="Mode", bg=COLOR_BG_PANEL, fg="#c0c0cc",
            font=(FONT_UI_FAMILY, 8), width=12, anchor="w"
        )
        mode_lbl.pack(side="left")

        btn_abs = tk.Button(
            mode_row,
            text="Absolute (px)",
            bg="#3a3a4c" if not w.is_relative else "#1e1e26",
            fg="#ffffff" if not w.is_relative else "#7e7e90",
            relief="flat",
            font=(FONT_UI_FAMILY, 8, "bold" if not w.is_relative else "normal"),
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._set_geometry_mode(w, False)
        )
        btn_abs.pack(side="left", padx=(0, 4))

        btn_rel = tk.Button(
            mode_row,
            text="Relative (0.0-1.0)",
            bg="#3a3a4c" if w.is_relative else "#1e1e26",
            fg="#ffffff" if w.is_relative else "#7e7e90",
            relief="flat",
            font=(FONT_UI_FAMILY, 8, "bold" if w.is_relative else "normal"),
            padx=6,
            pady=2,
            cursor="hand2",
            command=lambda: self._set_geometry_mode(w, True)
        )
        btn_rel.pack(side="left")

        # Geometry coordinate entries
        if w.is_relative:
            rx_str = f"{w.rel_x:.4f}" if w.rel_x is not None else "0.0000"
            ry_str = f"{w.rel_y:.4f}" if w.rel_y is not None else "0.0000"
            rw_str = f"{w.rel_width:.4f}" if w.rel_width is not None else "0.0000"
            rh_str = f"{w.rel_height:.4f}" if w.rel_height is not None else "0.0000"
            self._add_entry(body, "Rel X", rx_str, lambda val: self._on_rel_geom_change(w, "rel_x", val))
            self._add_entry(body, "Rel Y", ry_str, lambda val: self._on_rel_geom_change(w, "rel_y", val))
            self._add_entry(body, "Rel Width", rw_str, lambda val: self._on_rel_geom_change(w, "rel_width", val))
            self._add_entry(body, "Rel Height", rh_str, lambda val: self._on_rel_geom_change(w, "rel_height", val))
        else:
            self._add_entry(body, "X", str(w.x), lambda val: self._on_geom_change(w, "x", val))
            self._add_entry(body, "Y", str(w.y), lambda val: self._on_geom_change(w, "y", val))
            self._add_entry(body, "Width", str(w.width), lambda val: self._on_geom_change(w, "width", val))
            self._add_entry(body, "Height", str(w.height), lambda val: self._on_geom_change(w, "height", val))

        # Anchor dropdown
        anchors = ["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]
        curr_anchor = w.properties.get("anchor", "nw")
        self._add_dropdown(body, "Anchor", curr_anchor, anchors, lambda val: self._on_prop_change(w, "anchor", val))

        # Lock Geometry Button
        lock_text = "🔓 Unlock Geometry" if w.locked else "🔒 Lock Geometry"
        lock_bg = "#b35900" if w.locked else "#282834"
        btn_lock = tk.Button(
            body,
            text=lock_text,
            bg=lock_bg,
            fg="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 8, "bold"),
            pady=3,
            cursor="hand2",
            command=lambda: (setattr(w, "locked", not w.locked), self.state.push_state(), self.refresh())
        )
        btn_lock.pack(fill="x", padx=12, pady=(6, 2))

        # Fill Container Button
        btn_fill = tk.Button(
            body,
            text="⛶ Fill Container",
            bg="#2c2c3c",
            fg="#ffffff",
            activebackground="#3e3e52",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 8, "bold"),
            pady=3,
            cursor="hand2",
            command=lambda: self.state.fill_parent_container(w.id)
        )
        btn_fill.pack(fill="x", padx=12, pady=2)

    def _set_geometry_mode(self, w: WidgetInstance, is_relative: bool):
        w.is_relative = is_relative
        if is_relative and (w.rel_x is None or w.rel_y is None):
            pw = self.state.widgets[w.parent_id].width if (w.parent_id and w.parent_id in self.state.widgets) else self.state.width
            ph = self.state.widgets[w.parent_id].height if (w.parent_id and w.parent_id in self.state.widgets) else self.state.height
            w.rel_x = round(w.x / max(1, pw), 4)
            w.rel_y = round(w.y / max(1, ph), 4)
            w.rel_width = round(w.width / max(1, pw), 4)
            w.rel_height = round(w.height / max(1, ph), 4)
        self.state.push_state()
        self.refresh()

    # --- SECTION 3: APPEARANCE ---
    def _render_section_appearance(self, w: WidgetInstance):
        body = self._create_collapsible_section("appearance", "Appearance")

        # Color Swatches
        self._add_color_field(body, "background", w.properties.get("bg", w.properties.get("background", "")), lambda val: self._on_color_prop_change(w, "bg", val))
        self._add_color_field(body, "foreground", w.properties.get("fg", w.properties.get("foreground", "")), lambda val: self._on_color_prop_change(w, "fg", val))
        self._add_color_field(body, "act_bg", w.properties.get("activebackground", ""), lambda val: self._on_prop_change(w, "activebackground", val))
        self._add_color_field(body, "act_fg", w.properties.get("activeforeground", ""), lambda val: self._on_prop_change(w, "activeforeground", val))
        self._add_color_field(body, "dis_fg", w.properties.get("disabledforeground", ""), lambda val: self._on_prop_change(w, "disabledforeground", val))
        self._add_color_field(body, "hi_bg", w.properties.get("highlightbackground", ""), lambda val: self._on_prop_change(w, "highlightbackground", val))
        self._add_color_field(body, "hi_color", w.properties.get("highlightcolor", ""), lambda val: self._on_prop_change(w, "highlightcolor", val))

        # Relief Dropdown
        relief_options = ["flat", "groove", "raised", "ridge", "solid", "sunken"]
        curr_relief = w.properties.get("relief", "flat")
        self._add_dropdown(body, "Relief", curr_relief, relief_options, lambda val: self._on_prop_change(w, "relief", val))

        # Borderwidth Spinbox / Entry
        curr_bd = str(w.properties.get("borderwidth", w.properties.get("bd", 1)))
        self._add_spinbox(body, "Borderwidth", curr_bd, 0, 50, lambda val: self._on_prop_change(w, "borderwidth", int(val) if val.isdigit() else 1))

        # Cursor Dropdown
        cursors = ["arrow", "hand2", "xterm", "watch", "crosshair", "fleur", "plus", "sizing", "circle", "heart"]
        curr_cursor = w.properties.get("cursor", "arrow")
        self._add_dropdown(body, "Cursor", curr_cursor, cursors, lambda val: self._on_prop_change(w, "cursor", val))

    # --- SECTION 4: TEXT & TYPOGRAPHY ---
    def _render_section_text(self, w: WidgetInstance):
        body = self._create_collapsible_section("text", "Text & Typography")

        # text
        self._add_entry(body, "Text", w.properties.get("text", ""), lambda val: self._on_prop_change(w, "text", val))

        # textvariable
        self._add_entry(body, "Text Variable", w.properties.get("textvariable", ""), lambda val: self._on_prop_change(w, "textvariable", val))

        # font (Entry + "..." font chooser dialog button)
        self._add_font_field(body, "Font", w.properties.get("font", ""), lambda val: self._on_prop_change(w, "font", val))

        # justify dropdown
        justifies = ["left", "center", "right"]
        curr_justify = w.properties.get("justify", "left")
        self._add_dropdown(body, "Justify", curr_justify, justifies, lambda val: self._on_prop_change(w, "justify", val))

        # text anchor dropdown
        anchors = ["w", "center", "e", "nw", "n", "ne", "sw", "s", "se"]
        curr_tanchor = w.properties.get("text_anchor", w.properties.get("anchor", "w"))
        self._add_dropdown(body, "Text Anchor", curr_tanchor, anchors, lambda val: self._on_prop_change(w, "text_anchor", val))

        # wraplength
        curr_wrap = str(w.properties.get("wraplength", 0))
        self._add_entry(body, "Wrap Length", curr_wrap, lambda val: self._on_prop_change(w, "wraplength", int(val) if val.isdigit() else 0))

        # underline
        curr_under = str(w.properties.get("underline", -1))
        self._add_entry(body, "Underline", curr_under, lambda val: self._on_prop_change(w, "underline", int(val) if val.lstrip('-').isdigit() else -1))

    # --- SECTION 5: BEHAVIOR & BINDINGS ---
    def _render_section_behavior(self, w: WidgetInstance):
        body = self._create_collapsible_section("behavior", "Behavior & Bindings")

        # state dropdown
        states = ["normal", "active", "disabled", "readonly"]
        curr_state = w.properties.get("state", "normal")
        self._add_dropdown(body, "State", curr_state, states, lambda val: self._on_prop_change(w, "state", val))

        # takefocus checkbox
        curr_focus = bool(w.properties.get("takefocus", True))
        self._add_checkbox(body, "Take Focus", curr_focus, lambda val: self._on_prop_change(w, "takefocus", val))

        # command (Entry - callback in support module)
        curr_cmd = w.events.get("command", "")
        self._add_entry(body, "Command", curr_cmd, lambda val: self._on_event_change(w, "command", val))

        # variable
        curr_var = w.properties.get("variable", "")
        self._add_entry(body, "Variable", curr_var, lambda val: self._on_prop_change(w, "variable", val))

        # value
        curr_val = str(w.properties.get("value", ""))
        self._add_entry(body, "Value", curr_val, lambda val: self._on_prop_change(w, "value", val))

        # show (mask for passwords)
        curr_show = w.properties.get("show", "")
        self._add_entry(body, "Show (mask)", curr_show, lambda val: self._on_prop_change(w, "show", val))

    # --- SECTION 6: WIDGET-SPECIFIC EDITORS ---
    def _render_section_specific(self, w: WidgetInstance):
        body = self._create_collapsible_section("specific", "Widget-Specific Editors")

        w_type = w.widget_type

        # 1. Menu Editor (Toplevel / Root / Menubutton / has menu)
        if w_type in ("Toplevel", "Root", "Popupmenu", "Menubutton", "TMenubutton") or "menu" in w.properties:
            btn_menu = tk.Button(
                body,
                text="Menu: <Click to edit...>",
                bg="#2c2c3c",
                fg="#ffffff",
                activebackground="#3e3e52",
                activeforeground="#ffffff",
                relief="flat",
                font=(FONT_UI_FAMILY, 8, "bold"),
                pady=3,
                cursor="hand2",
                command=lambda: self._on_edit_widget_menu(w)
            )
            btn_menu.pack(fill="x", padx=12, pady=3)

        # 2. Notebook Tabs Editor
        if w_type in ("Notebook", "TNotebook"):
            btn_tabs = tk.Button(
                body,
                text="Edit Tabs...",
                bg="#2c2c3c",
                fg="#ffffff",
                activebackground="#3e3e52",
                activeforeground="#ffffff",
                relief="flat",
                font=(FONT_UI_FAMILY, 8, "bold"),
                pady=3,
                cursor="hand2",
                command=lambda: self._on_edit_notebook_tabs(w)
            )
            btn_tabs.pack(fill="x", padx=12, pady=3)

        # 3. Treeview Column Editor
        if w_type in ("Treeview", "Scrolledtreeview"):
            btn_cols = tk.Button(
                body,
                text="Edit Columns...",
                bg="#2c2c3c",
                fg="#ffffff",
                activebackground="#3e3e52",
                activeforeground="#ffffff",
                relief="flat",
                font=(FONT_UI_FAMILY, 8, "bold"),
                pady=3,
                cursor="hand2",
                command=lambda: self._on_edit_treeview_columns(w)
            )
            btn_cols.pack(fill="x", padx=12, pady=3)

        # 4. Values (Combobox / Spinbox / TCombobox / TSpinbox)
        if w_type in ("Combobox", "TCombobox", "Spinbox", "TSpinbox"):
            vals = w.properties.get("values", [])
            vals_str = ", ".join(str(v) for v in vals) if isinstance(vals, list) else str(vals)
            self._add_entry(
                body,
                "Values (csv)",
                vals_str,
                lambda val: self._on_prop_change(w, "values", [s.strip() for s in val.split(",") if s.strip()])
            )

        # 5. From & To (Scale / Spinbox / TScale / TSpinbox)
        if w_type in ("Scale", "TScale", "Spinbox", "TSpinbox"):
            curr_from = str(w.properties.get("from_", 0))
            curr_to = str(w.properties.get("to", 100))
            self._add_entry(body, "From", curr_from, lambda val: self._on_prop_change(w, "from_", int(val) if val.lstrip('-').isdigit() else 0))
            self._add_entry(body, "To", curr_to, lambda val: self._on_prop_change(w, "to", int(val) if val.lstrip('-').isdigit() else 100))

        # 6. Orient (Scale / Separator / Progressbar / Panedwindow / T-variants)
        if w_type in ("Scale", "TScale", "Separator", "TSeparator", "Progressbar", "TProgressbar", "TPanedwindow"):
            curr_orient = w.properties.get("orient", "horizontal")
            self._add_dropdown(body, "Orient", curr_orient, ["horizontal", "vertical"], lambda val: self._on_prop_change(w, "orient", val))

        # 7. Progressbar Mode & Maximum
        if w_type in ("Progressbar", "TProgressbar"):
            curr_mode = w.properties.get("mode", "determinate")
            self._add_dropdown(body, "Mode", curr_mode, ["determinate", "indeterminate"], lambda val: self._on_prop_change(w, "mode", val))
            curr_max = str(w.properties.get("maximum", 100))
            self._add_entry(body, "Maximum", curr_max, lambda val: self._on_prop_change(w, "maximum", int(val) if val.isdigit() else 100))

    def _on_edit_widget_menu(self, w: WidgetInstance):
        menu_key = w.name if w.name in self.state.menus else "main_menu"
        initial_spec = self.state.menus.get(menu_key) or self.state.menus.get("main_menu")

        def on_save(saved_spec):
            self.state.menus[menu_key] = saved_spec
            w.properties["menu"] = saved_spec.name
            self.state.push_state()

        MenuEditorDialog.edit_menu(self.winfo_toplevel(), initial_spec=initial_spec, on_save=on_save)

    def _on_edit_notebook_tabs(self, w: WidgetInstance):
        def on_save(saved_tabs):
            w.properties["tabs"] = saved_tabs
            self.state.push_state()

        NotebookTabEditorDialog.edit_tabs(self.winfo_toplevel(), widget=w, state=self.state, on_save=on_save)

    def _on_edit_treeview_columns(self, w: WidgetInstance):
        def on_save(saved_cols):
            w.properties["columns"] = saved_cols
            self.state.push_state()

        TreeviewColumnEditorDialog.edit_columns(self.winfo_toplevel(), widget=w, state=self.state, on_save=on_save)

    # --------------------------------------------------------------------------
    # UI Component Helpers
    # --------------------------------------------------------------------------
    def _add_entry(self, parent, label_text: str, current_val: str, on_change) -> tk.Entry:
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=2)

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

        entry.bind("<FocusOut>", lambda e: on_change(var.get()))
        entry.bind("<Return>", lambda e: (on_change(var.get()), entry.select_range(0, "end")))
        return entry

    def _add_readonly_text(self, parent, label_text: str, current_val: str):
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=2)

        lbl = tk.Label(
            row, text=label_text, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            font=(FONT_UI_FAMILY, 8), width=12, anchor="w"
        )
        lbl.pack(side="left")

        val_lbl = tk.Label(
            row, text=current_val, bg="#141419", fg="#8f90a2",
            font=(FONT_UI_FAMILY, 8), anchor="w", padx=6, pady=2, relief="flat"
        )
        val_lbl.pack(side="right", fill="x", expand=True)

    def _add_dropdown(self, parent, label_text: str, current_val: str, options: List[str], on_change) -> ttk.Combobox:
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=2)

        lbl = tk.Label(
            row, text=label_text, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            font=(FONT_UI_FAMILY, 8), width=12, anchor="w"
        )
        lbl.pack(side="left")

        cb = ttk.Combobox(row, values=options, state="readonly", font=(FONT_UI_FAMILY, 8))
        if current_val in options:
            cb.set(current_val)
        elif options:
            cb.set(options[0])
        cb.pack(side="right", fill="x", expand=True)

        cb.bind("<<ComboboxSelected>>", lambda e: on_change(cb.get()))
        return cb

    def _add_spinbox(self, parent, label_text: str, current_val: str, from_: int, to: int, on_change) -> ttk.Spinbox:
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=2)

        lbl = tk.Label(
            row, text=label_text, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            font=(FONT_UI_FAMILY, 8), width=12, anchor="w"
        )
        lbl.pack(side="left")

        var = tk.StringVar(value=current_val)
        sb = ttk.Spinbox(
            row, from_=from_, to=to, textvariable=var,
            font=(FONT_UI_FAMILY, 8), command=lambda: on_change(var.get())
        )
        sb.pack(side="right", fill="x", expand=True)
        sb.bind("<FocusOut>", lambda e: on_change(var.get()))
        sb.bind("<Return>", lambda e: on_change(var.get()))
        return sb

    def _add_checkbox(self, parent, label_text: str, current_val: bool, on_change):
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=3)

        var = tk.BooleanVar(value=current_val)
        chk = tk.Checkbutton(
            row, text=label_text, variable=var, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            activebackground=COLOR_BG_PANEL, activeforeground="#ffffff",
            selectcolor="#1a1a20", font=(FONT_UI_FAMILY, 8),
            command=lambda: on_change(var.get())
        )
        chk.pack(anchor="w")

    def _add_color_field(self, parent, label_text: str, current_val: str, on_change):
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=2)

        lbl = tk.Label(
            row, text=label_text, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            font=(FONT_UI_FAMILY, 8), width=12, anchor="w"
        )
        lbl.pack(side="left")

        # Color square swatch button
        swatch_color = current_val if current_val and current_val.startswith("#") else "#2d2d38"
        swatch_btn = tk.Button(
            row, bg=swatch_color, activebackground=swatch_color,
            width=2, height=1, relief="solid", bd=1, cursor="hand2"
        )
        swatch_btn.pack(side="right", padx=(4, 0))

        var = tk.StringVar(value=current_val)
        entry = tk.Entry(
            row, textvariable=var, bg="#1a1a20", fg="#ffffff",
            insertbackground="#ffffff", relief="flat", font=(FONT_UI_FAMILY, 8)
        )
        entry.pack(side="right", fill="x", expand=True)

        def pick_color():
            initial = var.get() if var.get().startswith("#") else "#ffffff"
            res = colorchooser.askcolor(color=initial, parent=self.winfo_toplevel(), title=f"Choose {label_text}")
            if res and res[1]:
                hex_color = res[1]
                var.set(hex_color)
                try:
                    swatch_btn.config(bg=hex_color, activebackground=hex_color)
                except Exception:
                    pass
                on_change(hex_color)

        swatch_btn.config(command=pick_color)

        def on_entry_change(e=None):
            val = var.get().strip()
            if val.startswith("#"):
                try:
                    swatch_btn.config(bg=val, activebackground=val)
                except Exception:
                    pass
            on_change(val)

        entry.bind("<FocusOut>", on_entry_change)
        entry.bind("<Return>", on_entry_change)

    def _add_font_field(self, parent, label_text: str, current_val: str, on_change):
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", padx=12, pady=2)

        lbl = tk.Label(
            row, text=label_text, bg=COLOR_BG_PANEL, fg="#c0c0cc",
            font=(FONT_UI_FAMILY, 8), width=12, anchor="w"
        )
        lbl.pack(side="left")

        font_btn = tk.Button(
            row, text="...", bg="#2d2d38", fg="#ffffff",
            relief="flat", font=(FONT_UI_FAMILY, 8), width=3, cursor="hand2"
        )
        font_btn.pack(side="right", padx=(4, 0))

        var = tk.StringVar(value=current_val)
        entry = tk.Entry(
            row, textvariable=var, bg="#1a1a20", fg="#ffffff",
            insertbackground="#ffffff", relief="flat", font=(FONT_UI_FAMILY, 8)
        )
        entry.pack(side="right", fill="x", expand=True)

        def choose_font_action():
            def on_save_font(font_tuple):
                fam, sz, st = font_tuple
                fstr = f"{{{fam}}} {sz} {st}".strip() if fam else ""
                var.set(fstr)
                on_change(fstr)

            FontChooserDialog.choose_font(
                self.winfo_toplevel(),
                initial_font=var.get(),
                on_save=on_save_font
            )

        font_btn.config(command=choose_font_action)
        entry.bind("<FocusOut>", lambda e: on_change(var.get()))
        entry.bind("<Return>", lambda e: on_change(var.get()))

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
        if clean_name and clean_name != w.name:
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

    def _on_rel_geom_change(self, w: WidgetInstance, prop: str, val: str):
        try:
            fv = float(val)
            fv = max(0.0, min(1.0, fv))
            if prop == "rel_x":
                w.rel_x = fv
            elif prop == "rel_y":
                w.rel_y = fv
            elif prop == "rel_width":
                w.rel_width = fv
            elif prop == "rel_height":
                w.rel_height = fv
            self.state.push_state()
        except ValueError:
            pass

    def _on_prop_change(self, w: WidgetInstance, prop: str, val: Any):
        w.properties[prop] = val
        self.state.push_state()

    def _on_color_prop_change(self, w: WidgetInstance, prop: str, val: str):
        w.properties[prop] = val
        self.state.push_state()

    def _on_event_change(self, w: WidgetInstance, event_name: str, val: str):
        clean_handler = val.strip().replace(" ", "_")
        w.events[event_name] = clean_handler
        self.state.push_state()
