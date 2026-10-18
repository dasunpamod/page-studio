"""
PageStudio - Treeview Column Editor Dialog
Modal dialog for configuring ttk.Treeview columns, headings, widths, alignments, and stretch behavior.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List
import copy

from ..core.models import WidgetInstance
from ..core.state import ProjectState
from ..ui.theme import (
    COLOR_BG_DARK,
    COLOR_BG_PANEL,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT,
    FONT_UI_FAMILY
)


class TreeviewColumnEditorDialog(tk.Toplevel):
    """Modal dialog to configure columns for a ttk.Treeview widget."""

    ANCHORS = ("w", "center", "e", "nw", "n", "ne", "sw", "s", "se")

    def __init__(
        self,
        parent,
        widget: Optional[WidgetInstance] = None,
        state: Optional[ProjectState] = None,
        initial_columns: Optional[List[Dict[str, Any]]] = None,
        on_save: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        modal: bool = False
    ):
        super().__init__(parent)
        self.title("PageStudio - Treeview Column Editor")
        self.geometry("740x460")
        self.minsize(620, 380)
        self.configure(bg=COLOR_BG_DARK)

        self.widget = widget
        self.state = state
        self.on_save = on_save
        self.result: Optional[List[Dict[str, Any]]] = None

        # Load columns
        if initial_columns is not None:
            self.columns: List[Dict[str, Any]] = copy.deepcopy(initial_columns)
        elif self.widget and "columns" in self.widget.properties:
            self.columns = copy.deepcopy(self.widget.properties["columns"])
        else:
            self.columns = [
                {"id": "col1", "heading": "Column 1", "width": 120, "anchor": "w", "stretch": True},
                {"id": "col2", "heading": "Column 2", "width": 150, "anchor": "w", "stretch": True}
            ]

        self.selected_index: Optional[int] = None
        self._is_populating: bool = False

        self._build_ui()
        self._populate_list()

        # Modal setup
        self.transient(parent)
        try:
            self.grab_set()
        except tk.TclError:
            pass

        self.protocol("WM_DELETE_WINDOW", self._on_cancel_clicked)
        self.bind("<Escape>", lambda e: self._on_cancel_clicked())

        if modal:
            self.wait_window(self)


    @classmethod
    def edit_columns(
        cls,
        parent,
        widget: Optional[WidgetInstance] = None,
        state: Optional[ProjectState] = None,
        initial_columns: Optional[List[Dict[str, Any]]] = None,
        on_save: Optional[Callable[[List[Dict[str, Any]]], None]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Convenience method to show dialog modally and return updated columns."""
        dialog = cls(parent, widget=widget, state=state, initial_columns=initial_columns, on_save=on_save, modal=False)
        parent.wait_window(dialog)
        return dialog.result

    def _build_ui(self):
        # Master Horizontal Container
        container = tk.Frame(self, bg=COLOR_BG_DARK)
        container.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        # --- LEFT: Table of Columns ---
        table_frame = tk.Frame(container, bg=COLOR_BG_PANEL)
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tbl_header = tk.Label(
            table_frame,
            text="COLUMNS CONFIGURATION",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=10,
            pady=8
        )
        tbl_header.pack(fill="x")

        tree_scroll_frame = tk.Frame(table_frame, bg=COLOR_BG_PANEL)
        tree_scroll_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        cols = ("id", "heading", "width", "anchor", "stretch")
        self.tree = ttk.Treeview(
            tree_scroll_frame,
            columns=cols,
            show="headings",
            selectmode="browse"
        )
        self.tree.heading("id", text="Column ID")
        self.tree.column("id", width=85, anchor="w")

        self.tree.heading("heading", text="Heading Text")
        self.tree.column("heading", width=140, anchor="w")

        self.tree.heading("width", text="Width")
        self.tree.column("width", width=60, anchor="center")

        self.tree.heading("anchor", text="Anchor")
        self.tree.column("anchor", width=65, anchor="center")

        self.tree.heading("stretch", text="Stretch")
        self.tree.column("stretch", width=60, anchor="center")

        v_scroll = ttk.Scrollbar(tree_scroll_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_column_selected)

        # --- RIGHT: Property Editor & Action Buttons ---
        right_panel = tk.Frame(container, bg=COLOR_BG_PANEL, width=220)
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)

        prop_header = tk.Label(
            right_panel,
            text="COLUMN PROPERTIES",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=10,
            pady=8
        )
        prop_header.pack(fill="x")

        form_frame = tk.Frame(right_panel, bg=COLOR_BG_PANEL)
        form_frame.pack(fill="x", padx=10, pady=4)

        # Column ID
        tk.Label(form_frame, text="Column ID:", bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), anchor="w").pack(fill="x")
        self.id_var = tk.StringVar()
        self.id_entry = tk.Entry(form_frame, textvariable=self.id_var, bg=COLOR_BG_DARK, fg=COLOR_TEXT_MAIN, relief="flat", font=(FONT_UI_FAMILY, 9))
        self.id_entry.pack(fill="x", pady=(2, 6))
        self.id_var.trace_add("write", lambda *a: self._on_field_changed())

        # Heading Text
        tk.Label(form_frame, text="Heading Text:", bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), anchor="w").pack(fill="x")
        self.heading_var = tk.StringVar()
        self.heading_entry = tk.Entry(form_frame, textvariable=self.heading_var, bg=COLOR_BG_DARK, fg=COLOR_TEXT_MAIN, relief="flat", font=(FONT_UI_FAMILY, 9))
        self.heading_entry.pack(fill="x", pady=(2, 6))
        self.heading_var.trace_add("write", lambda *a: self._on_field_changed())

        # Width
        tk.Label(form_frame, text="Width (px):", bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), anchor="w").pack(fill="x")
        self.width_var = tk.StringVar()
        self.width_entry = tk.Entry(form_frame, textvariable=self.width_var, bg=COLOR_BG_DARK, fg=COLOR_TEXT_MAIN, relief="flat", font=(FONT_UI_FAMILY, 9))
        self.width_entry.pack(fill="x", pady=(2, 6))
        self.width_var.trace_add("write", lambda *a: self._on_field_changed())

        # Anchor
        tk.Label(form_frame, text="Alignment (Anchor):", bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), anchor="w").pack(fill="x")
        self.anchor_var = tk.StringVar(value="w")
        self.anchor_cb = ttk.Combobox(form_frame, textvariable=self.anchor_var, values=self.ANCHORS, state="readonly", font=(FONT_UI_FAMILY, 8))
        self.anchor_cb.pack(fill="x", pady=(2, 6))
        self.anchor_cb.bind("<<ComboboxSelected>>", lambda e: self._on_field_changed())

        # Stretch
        self.stretch_var = tk.BooleanVar(value=True)
        self.stretch_cb = tk.Checkbutton(
            form_frame,
            text="Stretch Column",
            variable=self.stretch_var,
            bg=COLOR_BG_PANEL,
            fg=COLOR_TEXT_MAIN,
            activebackground=COLOR_BG_PANEL,
            activeforeground=COLOR_TEXT_MAIN,
            selectcolor=COLOR_BG_DARK,
            font=(FONT_UI_FAMILY, 8),
            command=self._on_field_changed
        )
        self.stretch_cb.pack(anchor="w", pady=(2, 10))

        # Action Buttons
        self._add_action_btn(right_panel, "+ Add Column", self._on_add_column)
        self._add_action_btn(right_panel, "✕ Remove Column", self._on_remove_column, bg="#8b263e")
        self._add_action_btn(right_panel, "▲ Move Up", self._on_move_up)
        self._add_action_btn(right_panel, "▼ Move Down", self._on_move_down)

        # --- BOTTOM BAR ---
        bottom_bar = tk.Frame(self, bg=COLOR_BG_DARK, height=48)
        bottom_bar.pack(fill="x", padx=12, pady=10)

        self.save_btn = tk.Button(
            bottom_bar,
            text="Save Columns",
            bg=COLOR_ACCENT,
            fg="#ffffff",
            activebackground="#2670e8",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 9, "bold"),
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_save_clicked
        )
        self.save_btn.pack(side="right", padx=(6, 0))

        self.cancel_btn = tk.Button(
            bottom_bar,
            text="Cancel",
            bg="#383844",
            fg="#ffffff",
            activebackground="#4a4a58",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 9),
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._on_cancel_clicked
        )
        self.cancel_btn.pack(side="right")

    def _add_action_btn(self, parent, text, command, bg="#333342"):
        btn = tk.Button(
            parent,
            text=text,
            bg=bg,
            fg="#ffffff",
            activebackground="#444455",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 8),
            padx=6,
            pady=4,
            cursor="hand2",
            command=command
        )
        btn.pack(fill="x", padx=10, pady=3)
        return btn

    def _populate_list(self):
        curr_idx = self.selected_index
        self.tree.delete(*self.tree.get_children())

        for idx, col in enumerate(self.columns):
            item_id = str(idx)
            self.tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    col.get("id", f"col{idx+1}"),
                    col.get("heading", ""),
                    col.get("width", 100),
                    col.get("anchor", "w"),
                    "Yes" if col.get("stretch", True) else "No"
                )
            )

        if curr_idx is not None and 0 <= curr_idx < len(self.columns):
            self.tree.selection_set(str(curr_idx))
            self.tree.see(str(curr_idx))
        elif self.columns:
            self.tree.selection_set("0")
            self.tree.see("0")

        self._on_column_selected(None)

    def _on_column_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            self.selected_index = None
            self.id_entry.config(state="disabled")
            self.heading_entry.config(state="disabled")
            self.width_entry.config(state="disabled")
            self.anchor_cb.config(state="disabled")
            self.stretch_cb.config(state="disabled")
            return

        self.selected_index = int(selected[0])
        col = self.columns[self.selected_index]

        self._is_populating = True
        try:
            self.id_entry.config(state="normal")
            self.heading_entry.config(state="normal")
            self.width_entry.config(state="normal")
            self.anchor_cb.config(state="readonly")
            self.stretch_cb.config(state="normal")

            self.id_var.set(col.get("id", ""))
            self.heading_var.set(col.get("heading", ""))
            self.width_var.set(str(col.get("width", 100)))
            self.anchor_var.set(col.get("anchor", "w"))
            self.stretch_var.set(bool(col.get("stretch", True)))
        finally:
            self._is_populating = False

    def _on_field_changed(self):
        if self._is_populating or self.selected_index is None:
            return

        col = self.columns[self.selected_index]
        col["id"] = self.id_var.get().strip()
        col["heading"] = self.heading_var.get()
        w_str = self.width_var.get().strip()
        col["width"] = int(w_str) if w_str.isdigit() else 100
        col["anchor"] = self.anchor_var.get()
        col["stretch"] = bool(self.stretch_var.get())

        item_id = str(self.selected_index)
        if self.tree.exists(item_id):
            self.tree.item(
                item_id,
                values=(
                    col["id"],
                    col["heading"],
                    col["width"],
                    col["anchor"],
                    "Yes" if col["stretch"] else "No"
                )
            )

    def _on_add_column(self):
        num = len(self.columns) + 1
        new_col = {
            "id": f"col{num}",
            "heading": f"Column {num}",
            "width": 120,
            "anchor": "w",
            "stretch": True
        }
        self.columns.append(new_col)
        self.selected_index = len(self.columns) - 1
        self._populate_list()
        self.heading_entry.focus_set()

    def _on_remove_column(self):
        if self.selected_index is None:
            return
        if len(self.columns) <= 1:
            messagebox.showwarning("Warning", "Treeview must have at least one column.")
            return

        del self.columns[self.selected_index]
        self.selected_index = min(self.selected_index, len(self.columns) - 1)
        self._populate_list()

    def _on_move_up(self):
        if self.selected_index is None or self.selected_index <= 0:
            return
        idx = self.selected_index
        self.columns[idx], self.columns[idx - 1] = self.columns[idx - 1], self.columns[idx]
        self.selected_index = idx - 1
        self._populate_list()

    def _on_move_down(self):
        if self.selected_index is None or self.selected_index >= len(self.columns) - 1:
            return
        idx = self.selected_index
        self.columns[idx], self.columns[idx + 1] = self.columns[idx + 1], self.columns[idx]
        self.selected_index = idx + 1
        self._populate_list()

    def destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        super().destroy()

    def _on_save_clicked(self):
        self.result = [dict(c) for c in self.columns]
        if self.widget:
            self.widget.properties["columns"] = [dict(c) for c in self.columns]
        if self.state:
            self.state.push_state()
        if self.on_save:
            self.on_save(self.result)
        self.destroy()

    def _on_cancel_clicked(self):
        self.result = None
        self.destroy()

