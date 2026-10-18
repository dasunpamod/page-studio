"""
PageStudio - Notebook Tab Editor Dialog
Modal dialog for configuring ttk.Notebook tabs, labels, states, and ordering.
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


class NotebookTabEditorDialog(tk.Toplevel):
    """Modal dialog to manage tabs for a ttk.Notebook widget."""

    TAB_STATES = ("normal", "hidden", "disabled")

    def __init__(
        self,
        parent,
        widget: Optional[WidgetInstance] = None,
        state: Optional[ProjectState] = None,
        initial_tabs: Optional[List[Dict[str, Any]]] = None,
        on_save: Optional[Callable[[List[Dict[str, Any]]], None]] = None,
        modal: bool = False
    ):
        super().__init__(parent)
        self.title("PageStudio - Notebook Tab Editor")
        self.geometry("640x420")
        self.minsize(560, 360)
        self.configure(bg=COLOR_BG_DARK)

        self.widget = widget
        self.state = state
        self.on_save = on_save
        self.result: Optional[List[Dict[str, Any]]] = None

        # Load tabs
        if initial_tabs is not None:
            self.tabs: List[Dict[str, Any]] = copy.deepcopy(initial_tabs)
        elif self.widget and "tabs" in self.widget.properties:
            self.tabs = copy.deepcopy(self.widget.properties["tabs"])
        else:
            self.tabs = [
                {"id": "tab_1", "text": "Tab 1", "state": "normal"},
                {"id": "tab_2", "text": "Tab 2", "state": "normal"}
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
    def edit_tabs(
        cls,
        parent,
        widget: Optional[WidgetInstance] = None,
        state: Optional[ProjectState] = None,
        initial_tabs: Optional[List[Dict[str, Any]]] = None,
        on_save: Optional[Callable[[List[Dict[str, Any]]], None]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Convenience method to show dialog modally and return updated tabs."""
        dialog = cls(parent, widget=widget, state=state, initial_tabs=initial_tabs, on_save=on_save, modal=False)
        parent.wait_window(dialog)
        return dialog.result

    def _build_ui(self):
        # Main Layout: Left table, Right editor panel
        container = tk.Frame(self, bg=COLOR_BG_DARK)
        container.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        # --- LEFT: Table of Tabs ---
        table_frame = tk.Frame(container, bg=COLOR_BG_PANEL)
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tbl_header = tk.Label(
            table_frame,
            text="NOTEBOOK TABS",
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

        columns = ("index", "id", "text", "state")
        self.tree = ttk.Treeview(
            tree_scroll_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        self.tree.heading("index", text="#")
        self.tree.column("index", width=35, anchor="center")

        self.tree.heading("id", text="Tab ID")
        self.tree.column("id", width=90, anchor="w")

        self.tree.heading("text", text="Label Text")
        self.tree.column("text", width=140, anchor="w")

        self.tree.heading("state", text="State")
        self.tree.column("state", width=80, anchor="center")

        v_scroll = ttk.Scrollbar(tree_scroll_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_tab_selected)

        # --- RIGHT: Property Editor & Action Buttons ---
        right_panel = tk.Frame(container, bg=COLOR_BG_PANEL, width=200)
        right_panel.pack(side="right", fill="y", padx=(0, 0))
        right_panel.pack_propagate(False)

        prop_header = tk.Label(
            right_panel,
            text="TAB PROPERTIES",
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

        # Tab ID
        tk.Label(form_frame, text="Tab ID:", bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), anchor="w").pack(fill="x")
        self.id_var = tk.StringVar()
        self.id_entry = tk.Entry(
            form_frame,
            textvariable=self.id_var,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        self.id_entry.pack(fill="x", pady=(2, 8))
        self.id_var.trace_add("write", lambda *a: self._on_field_changed())

        # Tab Text
        tk.Label(form_frame, text="Tab Label:", bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), anchor="w").pack(fill="x")
        self.text_var = tk.StringVar()
        self.text_entry = tk.Entry(
            form_frame,
            textvariable=self.text_var,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        self.text_entry.pack(fill="x", pady=(2, 8))
        self.text_var.trace_add("write", lambda *a: self._on_field_changed())

        # Tab State
        tk.Label(form_frame, text="State:", bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), anchor="w").pack(fill="x")
        self.state_var = tk.StringVar(value="normal")
        self.state_cb = ttk.Combobox(form_frame, textvariable=self.state_var, values=self.TAB_STATES, state="readonly", font=(FONT_UI_FAMILY, 8))
        self.state_cb.pack(fill="x", pady=(2, 12))
        self.state_cb.bind("<<ComboboxSelected>>", lambda e: self._on_field_changed())

        # Action Buttons
        self._add_action_btn(right_panel, "+ Add Tab", self._on_add_tab)
        self._add_action_btn(right_panel, "✕ Remove Tab", self._on_remove_tab, bg="#8b263e")
        self._add_action_btn(right_panel, "▲ Move Up", self._on_move_up)
        self._add_action_btn(right_panel, "▼ Move Down", self._on_move_down)

        # --- BOTTOM BAR ---
        bottom_bar = tk.Frame(self, bg=COLOR_BG_DARK, height=48)
        bottom_bar.pack(fill="x", padx=12, pady=10)

        self.save_btn = tk.Button(
            bottom_bar,
            text="Save Tabs",
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

        for idx, tab in enumerate(self.tabs):
            item_id = str(idx)
            self.tree.insert(
                "",
                "end",
                iid=item_id,
                values=(idx + 1, tab.get("id", ""), tab.get("text", ""), tab.get("state", "normal"))
            )

        if curr_idx is not None and 0 <= curr_idx < len(self.tabs):
            self.tree.selection_set(str(curr_idx))
            self.tree.see(str(curr_idx))
        elif self.tabs:
            self.tree.selection_set("0")
            self.tree.see("0")

        self._on_tab_selected(None)

    def _on_tab_selected(self, event):
        selected = self.tree.selection()
        if not selected:
            self.selected_index = None
            self.id_entry.config(state="disabled")
            self.text_entry.config(state="disabled")
            self.state_cb.config(state="disabled")
            return

        self.selected_index = int(selected[0])
        tab = self.tabs[self.selected_index]

        self._is_populating = True
        try:
            self.id_entry.config(state="normal")
            self.text_entry.config(state="normal")
            self.state_cb.config(state="readonly")

            self.id_var.set(tab.get("id", ""))
            self.text_var.set(tab.get("text", ""))
            self.state_var.set(tab.get("state", "normal"))
        finally:
            self._is_populating = False

    def _on_field_changed(self):
        if self._is_populating or self.selected_index is None:
            return

        tab = self.tabs[self.selected_index]
        tab["id"] = self.id_var.get().strip()
        tab["text"] = self.text_var.get()
        tab["state"] = self.state_var.get()

        item_id = str(self.selected_index)
        if self.tree.exists(item_id):
            self.tree.item(
                item_id,
                values=(self.selected_index + 1, tab["id"], tab["text"], tab["state"])
            )

    def _on_add_tab(self):
        num = len(self.tabs) + 1
        new_tab = {
            "id": f"tab_{num}",
            "text": f"Tab {num}",
            "state": "normal"
        }
        self.tabs.append(new_tab)
        self.selected_index = len(self.tabs) - 1
        self._populate_list()
        self.text_entry.focus_set()

    def _on_remove_tab(self):
        if self.selected_index is None:
            return
        if len(self.tabs) <= 1:
            messagebox.showwarning("Warning", "Notebook must have at least one tab.")
            return

        del self.tabs[self.selected_index]
        self.selected_index = min(self.selected_index, len(self.tabs) - 1)
        self._populate_list()

    def _on_move_up(self):
        if self.selected_index is None or self.selected_index <= 0:
            return
        idx = self.selected_index
        self.tabs[idx], self.tabs[idx - 1] = self.tabs[idx - 1], self.tabs[idx]
        self.selected_index = idx - 1
        self._populate_list()

    def _on_move_down(self):
        if self.selected_index is None or self.selected_index >= len(self.tabs) - 1:
            return
        idx = self.selected_index
        self.tabs[idx], self.tabs[idx + 1] = self.tabs[idx + 1], self.tabs[idx]
        self.selected_index = idx + 1
        self._populate_list()

    def destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        super().destroy()

    def _on_save_clicked(self):
        self.result = [dict(t) for t in self.tabs]
        if self.widget:
            self.widget.properties["tabs"] = [dict(t) for t in self.tabs]
        if self.state:
            self.state.push_state()
        if self.on_save:
            self.on_save(self.result)
        self.destroy()

    def _on_cancel_clicked(self):
        self.result = None
        self.destroy()

