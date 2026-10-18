"""
PageStudio - Visual Menu Editor Dialog
Modal dialog to design application Menubars, Cascades, and Popup/Context Menus,
matching PAGE's Menu Editor specifications with zero third-party dependencies.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List, Union, Tuple
from dataclasses import dataclass, field
import uuid
import copy

from ..ui.theme import (
    COLOR_BG_DARK,
    COLOR_BG_PANEL,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT,
    FONT_UI_FAMILY
)


@dataclass
class MenuItemSpec:
    """Specification for an individual menu entry or cascade submenu."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    item_type: str = "command"  # "command", "cascade", "checkbutton", "radiobutton", "separator"
    label: str = ""
    command: str = ""
    accelerator: str = ""
    variable: str = ""
    value: str = ""
    state: str = "normal"  # "normal", "disabled"
    underline: int = -1
    children: List["MenuItemSpec"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "item_type": self.item_type,
            "label": self.label,
            "command": self.command,
            "accelerator": self.accelerator,
            "variable": self.variable,
            "value": self.value,
            "state": self.state,
            "underline": self.underline,
            "children": [c.to_dict() for c in self.children]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MenuItemSpec":
        spec = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            item_type=data.get("item_type", "command"),
            label=data.get("label", ""),
            command=data.get("command", ""),
            accelerator=data.get("accelerator", ""),
            variable=data.get("variable", ""),
            value=data.get("value", ""),
            state=data.get("state", "normal"),
            underline=int(data.get("underline", -1)) if str(data.get("underline", "")).lstrip("-").isdigit() else -1,
            children=[cls.from_dict(c) for c in data.get("children", [])]
        )
        return spec


@dataclass
class MenuBarSpec:
    """Specification representing a complete menubar hierarchy."""
    items: List[MenuItemSpec] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items]
        }

    @classmethod
    def from_dict(cls, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> "MenuBarSpec":
        if isinstance(data, list):
            items = [MenuItemSpec.from_dict(it) for it in data]
        elif isinstance(data, dict):
            items = [MenuItemSpec.from_dict(it) for it in data.get("items", [])]
        else:
            items = []
        return cls(items=items)


class MenuEditorDialog(tk.Toplevel):
    """Visual modal dialog for constructing and editing menus."""

    ITEM_TYPES = ("command", "cascade", "checkbutton", "radiobutton", "separator")
    STATES = ("normal", "disabled")

    def __init__(
        self,
        parent,
        initial_spec: Optional[Union[MenuBarSpec, Dict[str, Any], List[Dict[str, Any]]]] = None,
        on_save: Optional[Callable[[MenuBarSpec], None]] = None,
        modal: bool = False
    ):
        super().__init__(parent)
        self.title("PageStudio - Menu Editor")
        self.geometry("820x540")
        self.minsize(700, 450)
        self.configure(bg=COLOR_BG_DARK)

        self.on_save = on_save
        self.result: Optional[MenuBarSpec] = None

        # Parse initial spec or create sensible default
        if initial_spec is None:
            self.spec = self._create_default_spec()
        elif isinstance(initial_spec, MenuBarSpec):
            self.spec = copy.deepcopy(initial_spec)
        else:
            self.spec = MenuBarSpec.from_dict(initial_spec)

        self.selected_item_id: Optional[str] = None
        self._is_populating: bool = False

        self._build_ui()
        self._populate_tree()

        # Modal window setup
        self.transient(parent)
        try:
            self.grab_set()
        except tk.TclError:
            pass

        if modal:
            self.wait_window(self)

    @classmethod
    def edit_menu(
        cls,
        parent,
        initial_spec: Optional[Union[MenuBarSpec, Dict[str, Any], List[Dict[str, Any]]]] = None,
        on_save: Optional[Callable[[MenuBarSpec], None]] = None
    ) -> Optional[MenuBarSpec]:
        """Convenience method to show dialog modally and return updated MenuBarSpec."""
        dialog = cls(parent, initial_spec=initial_spec, on_save=on_save, modal=False)
        parent.wait_window(dialog)
        return dialog.result

    def _create_default_spec(self) -> MenuBarSpec:
        """Generates a standard default File/Edit menubar if none provided."""
        file_menu = MenuItemSpec(
            item_type="cascade",
            label="File",
            children=[
                MenuItemSpec(item_type="command", label="New", accelerator="Ctrl+N", command="on_file_new"),
                MenuItemSpec(item_type="command", label="Open...", accelerator="Ctrl+O", command="on_file_open"),
                MenuItemSpec(item_type="separator"),
                MenuItemSpec(item_type="command", label="Exit", accelerator="Alt+F4", command="on_file_exit"),
            ]
        )
        edit_menu = MenuItemSpec(
            item_type="cascade",
            label="Edit",
            children=[
                MenuItemSpec(item_type="command", label="Undo", accelerator="Ctrl+Z", command="on_undo"),
                MenuItemSpec(item_type="command", label="Redo", accelerator="Ctrl+Y", command="on_redo"),
            ]
        )
        return MenuBarSpec(items=[file_menu, edit_menu])

    def _build_ui(self):
        # Master Horizontal Paned Container
        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # --- LEFT PANE: Hierarchy & Actions ---
        left_pane = tk.Frame(self.paned, bg=COLOR_BG_PANEL)
        self.paned.add(left_pane, weight=3)

        tree_header = tk.Label(
            left_pane,
            text="MENU HIERARCHY",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=10,
            pady=8
        )
        tree_header.pack(fill="x")

        tree_container = tk.Frame(left_pane, bg=COLOR_BG_PANEL)
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        self.tree = ttk.Treeview(
            tree_container,
            selectmode="browse",
            show="tree"
        )
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Toolbar under tree
        btn_frame1 = tk.Frame(left_pane, bg=COLOR_BG_PANEL)
        btn_frame1.pack(fill="x", padx=8, pady=2)

        self._add_action_btn(btn_frame1, "+ Add Item", self._on_add_command)
        self._add_action_btn(btn_frame1, "+ Add Submenu", self._on_add_cascade)
        self._add_action_btn(btn_frame1, "+ Add Separator", self._on_add_separator)

        btn_frame2 = tk.Frame(left_pane, bg=COLOR_BG_PANEL)
        btn_frame2.pack(fill="x", padx=8, pady=(2, 8))

        self._add_action_btn(btn_frame2, "▲ Move Up", self._on_move_up)
        self._add_action_btn(btn_frame2, "▼ Move Down", self._on_move_down)
        self._add_action_btn(btn_frame2, "✕ Delete", self._on_delete_item, bg="#8b263e")

        # --- RIGHT PANE: Item Properties ---
        right_pane = tk.Frame(self.paned, bg=COLOR_BG_PANEL)
        self.paned.add(right_pane, weight=2)

        prop_header = tk.Label(
            right_pane,
            text="ITEM PROPERTIES",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=12,
            pady=8
        )
        prop_header.pack(fill="x")

        form_container = tk.Frame(right_pane, bg=COLOR_BG_PANEL)
        form_container.pack(fill="both", expand=True, padx=12, pady=4)

        # Property fields
        self.type_var = tk.StringVar(value="command")
        self.label_var = tk.StringVar()
        self.command_var = tk.StringVar()
        self.accel_var = tk.StringVar()
        self.variable_var = tk.StringVar()
        self.value_var = tk.StringVar()
        self.state_var = tk.StringVar(value="normal")
        self.underline_var = tk.StringVar(value="-1")

        self.type_cb = self._add_form_dropdown(form_container, "Item Type:", self.type_var, self.ITEM_TYPES, self._on_prop_edited)
        self.label_entry = self._add_form_entry(form_container, "Label:", self.label_var, self._on_prop_edited)
        self.command_entry = self._add_form_entry(form_container, "Command:", self.command_var, self._on_prop_edited)
        self.accel_entry = self._add_form_entry(form_container, "Accelerator:", self.accel_var, self._on_prop_edited)
        self.variable_entry = self._add_form_entry(form_container, "Variable:", self.variable_var, self._on_prop_edited)
        self.value_entry = self._add_form_entry(form_container, "Value:", self.value_var, self._on_prop_edited)
        self.state_cb = self._add_form_dropdown(form_container, "State:", self.state_var, self.STATES, self._on_prop_edited)
        self.underline_entry = self._add_form_entry(form_container, "Underline:", self.underline_var, self._on_prop_edited)

        # --- BOTTOM ACTION BAR ---
        bottom_bar = tk.Frame(self, bg=COLOR_BG_DARK, height=48)
        bottom_bar.pack(fill="x", padx=12, pady=10)

        self.save_btn = tk.Button(
            bottom_bar,
            text="Save Menu",
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
            padx=8,
            pady=3,
            cursor="hand2",
            command=command
        )
        btn.pack(side="left", padx=2, expand=True, fill="x")
        return btn

    def _add_form_entry(self, parent, label_text, str_var, on_change_callback) -> tk.Entry:
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", pady=3)

        lbl = tk.Label(row, text=label_text, bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), width=12, anchor="w")
        lbl.pack(side="left")

        entry = tk.Entry(
            row,
            textvariable=str_var,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        entry.pack(side="left", fill="x", expand=True)
        str_var.trace_add("write", lambda *args: on_change_callback())
        return entry

    def _add_form_dropdown(self, parent, label_text, str_var, values, on_change_callback) -> ttk.Combobox:
        row = tk.Frame(parent, bg=COLOR_BG_PANEL)
        row.pack(fill="x", pady=3)

        lbl = tk.Label(row, text=label_text, bg=COLOR_BG_PANEL, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8), width=12, anchor="w")
        lbl.pack(side="left")

        cb = ttk.Combobox(row, textvariable=str_var, values=values, state="readonly", font=(FONT_UI_FAMILY, 8))
        cb.pack(side="left", fill="x", expand=True)
        cb.bind("<<ComboboxSelected>>", lambda e: on_change_callback())
        return cb

    def _format_item_label(self, item: MenuItemSpec) -> str:
        if item.item_type == "separator":
            return "──────── (Separator)"
        prefix = {
            "cascade": "📁 Submenu",
            "command": "⚡ Command",
            "checkbutton": "☑ Check",
            "radiobutton": "🔘 Radio"
        }.get(item.item_type, "•")

        label = item.label or "(untitled)"
        if item.accelerator:
            return f"{prefix}: {label}  [{item.accelerator}]"
        return f"{prefix}: {label}"

    def _populate_tree(self):
        """Builds treeview representation of spec.items."""
        selected_id = self.selected_item_id
        self.tree.delete(*self.tree.get_children())

        def insert_recursive(parent_node: str, items: List[MenuItemSpec]):
            for it in items:
                text = self._format_item_label(it)
                self.tree.insert(parent_node, "end", iid=it.id, text=text, open=True)
                if it.item_type == "cascade" and it.children:
                    insert_recursive(it.id, it.children)

        insert_recursive("", self.spec.items)

        # Restore selection
        if selected_id and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)
            self.tree.see(selected_id)
        elif self.spec.items:
            first_id = self.spec.items[0].id
            if self.tree.exists(first_id):
                self.tree.selection_set(first_id)

        self._on_tree_select(None)

    def _find_item(self, item_id: str) -> Tuple[Optional[MenuItemSpec], Optional[List[MenuItemSpec]], Optional[MenuItemSpec]]:
        """Returns (target_item, parent_children_list, parent_item)."""
        def search(items: List[MenuItemSpec], parent_item: Optional[MenuItemSpec]):
            for it in items:
                if it.id == item_id:
                    return it, items, parent_item
                if it.children:
                    found, lst, p = search(it.children, it)
                    if found:
                        return found, lst, p
            return None, None, None

        return search(self.spec.items, None)

    def _on_tree_select(self, event):
        """Updates property fields when an item is selected in tree."""
        selected = self.tree.selection()
        if not selected:
            self._disable_all_fields()
            self.selected_item_id = None
            return

        item_id = selected[0]
        self.selected_item_id = item_id
        item, _, _ = self._find_item(item_id)
        if not item:
            self._disable_all_fields()
            return

        self._is_populating = True
        try:
            self.type_var.set(item.item_type)
            self.label_var.set(item.label)
            self.command_var.set(item.command)
            self.accel_var.set(item.accelerator)
            self.variable_var.set(item.variable)
            self.value_var.set(item.value)
            self.state_var.set(item.state)
            self.underline_var.set(str(item.underline) if item.underline >= 0 else "-1")
            self._adjust_field_states(item.item_type)
        finally:
            self._is_populating = False

    def _adjust_field_states(self, item_type: str):
        """Enables/disables fields appropriate for the item_type."""
        is_sep = (item_type == "separator")
        is_cascade = (item_type == "cascade")
        is_check = (item_type == "checkbutton")
        is_radio = (item_type == "radiobutton")

        def set_state(entry, enabled):
            entry.config(state="normal" if enabled else "disabled")

        self.type_cb.config(state="readonly")
        set_state(self.label_entry, not is_sep)
        set_state(self.command_entry, not is_sep and not is_cascade)
        set_state(self.accel_entry, not is_sep and not is_cascade)
        set_state(self.variable_entry, is_check or is_radio)
        set_state(self.value_entry, is_radio)
        self.state_cb.config(state="readonly" if not is_sep else "disabled")
        set_state(self.underline_entry, not is_sep)

    def _disable_all_fields(self):
        for w in (self.label_entry, self.command_entry, self.accel_entry,
                  self.variable_entry, self.value_entry, self.underline_entry):
            w.config(state="disabled")
        self.type_cb.config(state="disabled")
        self.state_cb.config(state="disabled")

    def _on_prop_edited(self):
        """Syncs edits from property fields back into the MenuItemSpec and treeview."""
        if self._is_populating or not self.selected_item_id:
            return

        item, _, _ = self._find_item(self.selected_item_id)
        if not item:
            return

        old_type = item.item_type
        new_type = self.type_var.get()
        item.item_type = new_type
        item.label = self.label_var.get()
        item.command = self.command_var.get()
        item.accelerator = self.accel_var.get()
        item.variable = self.variable_var.get()
        item.value = self.value_var.get()
        item.state = self.state_var.get()

        u_str = self.underline_var.get().strip()
        try:
            item.underline = int(u_str) if u_str else -1
        except ValueError:
            item.underline = -1

        if old_type != new_type:
            self._adjust_field_states(new_type)

        # Update Tree node text
        if self.tree.exists(item.id):
            self.tree.item(item.id, text=self._format_item_label(item))

    # --- ACTION BUTTON HANDLERS ---
    def _add_new_item(self, item_type: str, default_label: str) -> MenuItemSpec:
        new_item = MenuItemSpec(
            item_type=item_type,
            label=default_label,
            command=f"on_{default_label.lower().replace(' ', '_')}" if item_type == "command" else ""
        )

        selected = self.tree.selection()
        if selected:
            sel_id = selected[0]
            item, sib_list, parent = self._find_item(sel_id)
            if item and item.item_type == "cascade":
                # Add inside cascade
                item.children.append(new_item)
            elif sib_list is not None and item:
                # Add after selected sibling
                idx = sib_list.index(item)
                sib_list.insert(idx + 1, new_item)
            else:
                self.spec.items.append(new_item)
        else:
            self.spec.items.append(new_item)

        self.selected_item_id = new_item.id
        self._populate_tree()
        self.label_entry.focus_set()
        return new_item

    def _on_add_command(self):
        self._add_new_item("command", "New Item")

    def _on_add_cascade(self):
        self._add_new_item("cascade", "New Menu")

    def _on_add_separator(self):
        self._add_new_item("separator", "---")

    def _on_move_up(self):
        if not self.selected_item_id:
            return
        item, sib_list, _ = self._find_item(self.selected_item_id)
        if sib_list is not None and item in sib_list:
            idx = sib_list.index(item)
            if idx > 0:
                sib_list[idx], sib_list[idx - 1] = sib_list[idx - 1], sib_list[idx]
                self._populate_tree()

    def _on_move_down(self):
        if not self.selected_item_id:
            return
        item, sib_list, _ = self._find_item(self.selected_item_id)
        if sib_list is not None and item in sib_list:
            idx = sib_list.index(item)
            if idx < len(sib_list) - 1:
                sib_list[idx], sib_list[idx + 1] = sib_list[idx + 1], sib_list[idx]
                self._populate_tree()

    def _on_delete_item(self):
        if not self.selected_item_id:
            return
        item, sib_list, _ = self._find_item(self.selected_item_id)
        if sib_list is not None and item in sib_list:
            idx = sib_list.index(item)
            sib_list.remove(item)
            # Pick next selection
            if sib_list:
                next_idx = min(idx, len(sib_list) - 1)
                self.selected_item_id = sib_list[next_idx].id
            else:
                self.selected_item_id = None
            self._populate_tree()

    def _on_save_clicked(self):
        self.result = self.spec
        if self.on_save:
            try:
                self.on_save(self.result)
            except Exception as e:
                messagebox.showerror("Save Error", f"Error saving menu: {e}")
                return
        self.destroy()

    def _on_cancel_clicked(self):
        self.result = None
        self.destroy()
