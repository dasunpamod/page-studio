"""
PageStudio - Widget Hierarchy Tree Panel
Provides a hierarchical Treeview representation of all widgets in the project,
with filtering, selection synchronization, right-click context menu, and double-click editor triggers.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, Dict, Any, List
import copy
import uuid

from ..core.state import ProjectState
from ..core.models import WidgetInstance, WIDGET_CATALOG
from ..ui.theme import (
    COLOR_BG_PANEL,
    COLOR_BG_DARK,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    FONT_UI_FAMILY
)
from ..utils.helpers import IS_MAC, get_platform_shortcut


class WidgetTree(tk.Frame):
    """Hierarchy tree panel displaying project widgets and container relationships."""

    _clipboard: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        parent,
        state: ProjectState,
        on_edit_menu: Optional[Callable[[Optional[WidgetInstance]], None]] = None,
        on_edit_notebook: Optional[Callable[[WidgetInstance], None]] = None,
        on_edit_treeview: Optional[Callable[[WidgetInstance], None]] = None,
        **kwargs
    ):
        super().__init__(parent, bg=COLOR_BG_PANEL, **kwargs)
        self.state = state
        self.on_edit_menu = on_edit_menu
        self.on_edit_notebook = on_edit_notebook
        self.on_edit_treeview = on_edit_treeview

        self._is_syncing: bool = False
        self._filter_query: str = ""

        self._build_ui()
        self._build_context_menu()
        self._bind_events()

        # Listen for state changes
        self.state.add_listener(self.refresh)
        self.refresh()

    def _build_ui(self):
        # Header Container
        header_frame = tk.Frame(self, bg=COLOR_BG_PANEL)
        header_frame.pack(fill="x", padx=8, pady=(8, 4))

        self.title_label = tk.Label(
            header_frame,
            text="WIDGET TREE",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w"
        )
        self.title_label.pack(side="left")

        # Search / Filter Bar
        filter_frame = tk.Frame(self, bg=COLOR_BG_DARK, bd=1, relief="solid")
        filter_frame.pack(fill="x", padx=8, pady=(0, 6))

        search_icon = tk.Label(
            filter_frame,
            text="🔍",
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MUTED,
            font=(FONT_UI_FAMILY, 8)
        )
        search_icon.pack(side="left", padx=(4, 2))

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._on_filter_changed)
        self.filter_entry = tk.Entry(
            filter_frame,
            textvariable=self.filter_var,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        self.filter_entry.pack(side="left", fill="x", expand=True, pady=2, padx=(0, 4))

        # Clear button for search
        self.clear_btn = tk.Button(
            filter_frame,
            text="✕",
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MUTED,
            activebackground=COLOR_BG_DARK,
            activeforeground=COLOR_TEXT_MAIN,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=(FONT_UI_FAMILY, 7),
            command=self._clear_filter
        )
        self.clear_btn.pack(side="right", padx=2)

        # Treeview + Scrollbars
        tree_container = tk.Frame(self, bg=COLOR_BG_PANEL)
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(
            tree_container,
            selectmode="browse",
            show="tree"
        )
        v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

    def _build_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="Cut",
            accelerator=get_platform_shortcut("X"),
            command=self.cut_selected
        )
        self.context_menu.add_command(
            label="Copy",
            accelerator=get_platform_shortcut("C"),
            command=self.copy_selected
        )
        self.context_menu.add_command(
            label="Paste",
            accelerator=get_platform_shortcut("V"),
            command=self.paste
        )
        self.context_menu.add_command(
            label="Delete",
            accelerator="Del",
            command=self.delete_selected
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Lock / Unlock Geometry",
            command=self.toggle_lock_selected
        )
        self.context_menu.add_command(
            label="Fill Container",
            command=self.fill_container_selected
        )

    def _bind_events(self):
        # Selection event
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Right-click context menu (macOS & Windows/Linux)
        self.tree.bind("<Button-3>", self._on_right_click)
        if IS_MAC:
            self.tree.bind("<Button-2>", self._on_right_click)
            self.tree.bind("<Control-Button-1>", self._on_right_click)

        # Double-click handler
        self.tree.bind("<Double-Button-1>", self._on_double_click)

        # Keyboard shortcuts
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<BackSpace>", lambda e: self.delete_selected())
        ctrl_key = "Command" if IS_MAC else "Control"
        self.tree.bind(f"<{ctrl_key}-x>", lambda e: self.cut_selected())
        self.tree.bind(f"<{ctrl_key}-c>", lambda e: self.copy_selected())
        self.tree.bind(f"<{ctrl_key}-v>", lambda e: self.paste())

    def _on_filter_changed(self, *args):
        self._filter_query = self.filter_var.get().strip().lower()
        self.refresh()

    def _clear_filter(self):
        self.filter_var.set("")

    def _format_widget_display(self, widget: WidgetInstance) -> str:
        spec = WIDGET_CATALOG.get(widget.widget_type)
        disp_name = spec.display_name if spec else f"ttk.{widget.widget_type}"
        is_locked = getattr(widget, "locked", False) or widget.properties.get("locked", False)
        locked_tag = " 🔒" if is_locked else ""
        return f"{disp_name}: {widget.name}{locked_tag}"

    def _is_container_type(self, widget_type: str) -> bool:
        spec = WIDGET_CATALOG.get(widget_type)
        if spec and spec.is_container:
            return True
        wt = widget_type.lower()
        return wt in (
            "frame", "labelframe", "tframe", "tlabelframe",
            "notebook", "tnotebook", "canvas", "panedwindow",
            "tpanedwindow", "scrolledwindow"
        )

    def refresh(self):
        """Re-populates the Treeview from the current project state."""
        if self._is_syncing:
            return
        if getattr(self.state, "is_dragging", False):
            return

        # Record open state of nodes
        open_nodes = set()
        for item in self.tree.get_children():
            self._collect_open_nodes(item, open_nodes)

        # Clear tree
        self.tree.delete(*self.tree.get_children())

        # Top-level item: Root Window (Toplevel0: root)
        root_id = "__root__"
        root_text = "Toplevel0: root"
        self.tree.insert("", "end", iid=root_id, text=root_text, open=True)

        # Build parent -> children map
        children_map: Dict[Optional[str], List[WidgetInstance]] = {}
        for wid in self.state.widget_order:
            w = self.state.widgets.get(wid)
            if not w:
                continue
            parent = w.parent_id if (w.parent_id and w.parent_id in self.state.widgets) else None
            children_map.setdefault(parent, []).append(w)

        # Recursive population helper
        query = self._filter_query

        def matches_filter(widget: WidgetInstance) -> bool:
            if not query:
                return True
            display = self._format_widget_display(widget).lower()
            return query in display or query in widget.name.lower() or query in widget.widget_type.lower()

        def any_descendant_matches(widget: WidgetInstance) -> bool:
            if matches_filter(widget):
                return True
            for child in children_map.get(widget.id, []):
                if any_descendant_matches(child):
                    return True
            return False

        def insert_children(parent_node_id: str, parent_wid: Optional[str]):
            for widget in children_map.get(parent_wid, []):
                # If filter active, only include if widget or descendant matches
                if query and not any_descendant_matches(widget):
                    continue

                node_id = widget.id
                text = self._format_widget_display(widget)
                is_open = (node_id in open_nodes) or bool(query) or self._is_container_type(widget.widget_type)

                self.tree.insert(
                    parent_node_id,
                    "end",
                    iid=node_id,
                    text=text,
                    open=is_open
                )
                insert_children(node_id, widget.id)

        insert_children(root_id, None)

        # Synchronize selection
        self._sync_tree_selection_from_state()

    def _collect_open_nodes(self, item_id: str, open_set: set):
        try:
            if self.tree.item(item_id, "open"):
                open_set.add(item_id)
            for child in self.tree.get_children(item_id):
                self._collect_open_nodes(child, open_set)
        except Exception:
            pass

    def _sync_tree_selection_from_state(self):
        """Highlights the active widget in the tree based on state.selected_ids."""
        self._is_syncing = True
        try:
            selected_ids = self.state.selected_ids
            if selected_ids:
                wid = selected_ids[-1]
                if self.tree.exists(wid):
                    self.tree.selection_set(wid)
                    self.tree.see(wid)
                else:
                    self.tree.selection_remove(*self.tree.selection())
            else:
                if self.tree.exists("__root__"):
                    self.tree.selection_set("__root__")
                else:
                    self.tree.selection_remove(*self.tree.selection())
        finally:
            self._is_syncing = False

    def _on_tree_select(self, event):
        """Called when user clicks an item in the treeview."""
        if self._is_syncing:
            return

        selected = self.tree.selection()
        if not selected:
            return

        item_id = selected[0]
        self._is_syncing = True
        try:
            if item_id == "__root__":
                self.state.select_widget(None)
            elif item_id in self.state.widgets:
                self.state.select_widget(item_id)
        finally:
            self._is_syncing = False

    def _on_right_click(self, event):
        """Pops up the context menu on right-click."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            if item == "__root__":
                self.state.select_widget(None)
            elif item in self.state.widgets:
                self.state.select_widget(item)

        # Enable/disable menu items based on selection
        has_sel = bool(self.state.selected_ids)
        state_str = "normal" if has_sel else "disabled"
        self.context_menu.entryconfig("Cut", state=state_str)
        self.context_menu.entryconfig("Copy", state=state_str)
        self.context_menu.entryconfig("Delete", state=state_str)
        self.context_menu.entryconfig("Lock / Unlock Geometry", state=state_str)
        self.context_menu.entryconfig("Fill Container", state=state_str)

        can_paste = bool(WidgetTree._clipboard is not None)
        self.context_menu.entryconfig("Paste", state="normal" if can_paste else "disabled")

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _on_double_click(self, event):
        """Triggers specialized dialog editor on double-clicking supported widgets."""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        if item == "__root__":
            if self.on_edit_menu:
                self.on_edit_menu(None)
            return

        widget = self.state.widgets.get(item)
        if not widget:
            return

        wt = widget.widget_type.lower()
        if wt in ("notebook", "tnotebook"):
            if self.on_edit_notebook:
                self.on_edit_notebook(widget)
        elif wt in ("treeview", "scrolledtreeview"):
            if self.on_edit_treeview:
                self.on_edit_treeview(widget)
        elif wt in ("menu", "menubar", "menubutton", "tmenubutton", "popupmenu") or "menu" in widget.properties:
            if self.on_edit_menu:
                self.on_edit_menu(widget)

    # Context menu actions
    def cut_selected(self):
        """Cuts selected widget to clipboard."""
        self.copy_selected()
        self.delete_selected()

    def copy_selected(self):
        """Copies selected widget to clipboard."""
        w = self.state.get_selected_widget()
        if w:
            WidgetTree._clipboard = copy.deepcopy(w.to_dict())

    def paste(self):
        """Pastes widget from clipboard into project."""
        if not WidgetTree._clipboard:
            return
        data = copy.deepcopy(WidgetTree._clipboard)
        new_uid = str(uuid.uuid4())[:8]
        data["id"] = new_uid
        data["name"] = f"{data['widget_type'].lower()}_{new_uid}"
        data["x"] = data.get("x", 0) + 20
        data["y"] = data.get("y", 0) + 20
        new_w = WidgetInstance.from_dict(data)
        self.state.add_widget(new_w)

    def delete_selected(self):
        """Deletes selected widget from project."""
        self.state.remove_selected()

    def toggle_lock_selected(self):
        """Toggles lock status of selected widget geometry."""
        w = self.state.get_selected_widget()
        if not w:
            return
        current = getattr(w, "locked", False) or w.properties.get("locked", False)
        new_val = not current
        if hasattr(w, "locked"):
            w.locked = new_val
        w.properties["locked"] = new_val
        self.state.push_state()

    def fill_container_selected(self):
        """Resizes selected widget to fill its parent container or root window."""
        w = self.state.get_selected_widget()
        if not w:
            return
        if w.parent_id and w.parent_id in self.state.widgets:
            parent = self.state.widgets[w.parent_id]
            pw, ph = parent.width, parent.height
        else:
            pw, ph = self.state.width, self.state.height

        self.state.update_widget_geometry(w.id, 0, 0, pw, ph, commit=True, snap=False)
