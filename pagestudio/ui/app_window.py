"""
PageStudio - Main IDE Window
Unified workspace integrating the Left Pane (Widget Palette + Widget Tree),
Center Pane (Canvas + Live Code Preview), and Right Pane (Property Inspector),
along with Toolbar controls, Theme Switcher, Relative Mode Toggle, and native Menus.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
from typing import Optional

from ..core.state import ProjectState
from ..core.models import WidgetInstance, MenuBarSpec
from ..core.serializer import ProjectSerializer
from ..core.generator import CodeGenerator
from ..ui.canvas import DesignCanvas
from ..ui.palette import WidgetPalette
from ..ui.inspector import PropertyInspector
from ..ui.preview import CodePreviewPanel
from ..ui.widget_tree import WidgetTree
from ..ui.menu_editor import MenuEditorDialog
from ..ui.notebook_editor import NotebookTabEditorDialog
from ..ui.treeview_editor import TreeviewColumnEditorDialog
from ..ui.theme import (
    apply_theme,
    COLOR_BG_DARK,
    FONT_UI_FAMILY
)
from ..utils.helpers import IS_MAC, get_platform_shortcut, is_text_editing


class PageStudioApp:
    """Main Application Controller for PageStudio."""

    def __init__(self, root: tk.Tk, initial_project: Optional[str] = None):
        self.root = root
        self.root.title("PageStudio - Modern Python GUI Builder")
        self.root.geometry("1280x840")
        self.root.minsize(960, 640)

        # State
        self.current_file_path: Optional[str] = None
        self.state = ProjectState(title="My Application", width=550, height=380)

        # Styling
        self.style = apply_theme(self.root)

        self._build_toolbar()
        self._build_statusbar()
        self._build_workspace()
        self._build_menus()
        self._bind_global_shortcuts()

        # Wire state listeners
        self._wire_state_listeners()

        # If an initial project file was specified, load it
        if initial_project and os.path.exists(initial_project):
            self.load_project_file(initial_project)
        else:
            # Initial render
            self.canvas.render()
            self.state.notify()

    def _build_menus(self):
        menubar = tk.Menu(self.root)

        # File Menu: New, Open, Save, Save As, Export Python..., Exit
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", accelerator=get_platform_shortcut("N"), command=self.new_project)
        file_menu.add_command(label="Open...", accelerator=get_platform_shortcut("O"), command=self.open_project)
        file_menu.add_command(label="Save", accelerator=get_platform_shortcut("S"), command=self.save_project)
        file_menu.add_command(label="Save As...", accelerator=get_platform_shortcut("Shift+S"), command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export Python...", accelerator=get_platform_shortcut("E"), command=self.export_python_code)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit Menu: Undo, Redo, Cut, Copy, Paste, Duplicate, Delete, Design Menubar...
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator=get_platform_shortcut("Z"), command=self.state.undo)
        edit_menu.add_command(label="Redo", accelerator=get_platform_shortcut("Y"), command=self.state.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator=get_platform_shortcut("X"), command=self.cut)
        edit_menu.add_command(label="Copy", accelerator=get_platform_shortcut("C"), command=self.copy)
        edit_menu.add_command(label="Paste", accelerator=get_platform_shortcut("V"), command=self.paste)
        edit_menu.add_command(label="Duplicate", accelerator=get_platform_shortcut("D"), command=self.duplicate)
        edit_menu.add_command(label="Delete", accelerator="Del", command=self.delete_selected)
        edit_menu.add_separator()
        edit_menu.add_command(label="Design Menubar...", command=self.open_menu_editor)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Window Menu: Toggle Widget Tree, Reset Layout
        window_menu = tk.Menu(menubar, tearoff=0)
        window_menu.add_command(label="Toggle Widget Tree", command=self.toggle_widget_tree)
        window_menu.add_command(label="Reset Layout", command=self.reset_layout)
        menubar.add_cascade(label="Window", menu=window_menu)

        # Run Menu: Run / Test GUI
        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Run / Test GUI", accelerator=get_platform_shortcut("R"), command=self.run_test_gui)
        menubar.add_cascade(label="Run", menu=run_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About PageStudio", command=self._show_about)
        help_menu.add_command(label="macOS & Cross-Platform Notes", command=self._show_mac_notes)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bg=COLOR_BG_DARK, height=40)
        toolbar.pack(fill="x", side="top")

        # Action Buttons (matching PAGE Screenshot 1)
        # New, Open, Save, | , Undo, Redo, Cut, Copy, Paste, | , Delete.
        self._add_tool_btn(toolbar, "New", self.new_project)
        self._add_tool_btn(toolbar, "Open", self.open_project)
        self._add_tool_btn(toolbar, "Save", self.save_project)

        self._add_tool_separator(toolbar)
        self._add_tool_btn(toolbar, "↶ Undo", self.state.undo)
        self._add_tool_btn(toolbar, "↷ Redo", self.state.redo)
        self._add_tool_btn(toolbar, "✂ Cut", self.cut)
        self._add_tool_btn(toolbar, "📋 Copy", self.copy)
        self._add_tool_btn(toolbar, "📥 Paste", self.paste)

        self._add_tool_separator(toolbar)
        self._add_tool_btn(toolbar, "🗑 Delete", self.delete_selected, bg="#5a2a2a")

        self._add_tool_separator(toolbar)

        # Theme Selector dropdown: Theme: [clam ▼]
        theme_lbl = tk.Label(
            toolbar,
            text="Theme:",
            bg=COLOR_BG_DARK,
            fg="#c0c0d0",
            font=(FONT_UI_FAMILY, 8, "bold")
        )
        theme_lbl.pack(side="left", padx=(4, 2), pady=6)

        available_themes = list(self.style.theme_names()) if hasattr(self, "style") else ["clam"]
        current_theme = self.style.theme_use() if hasattr(self, "style") else "clam"
        if not current_theme and available_themes:
            current_theme = available_themes[0]

        self.theme_var = tk.StringVar(value=current_theme)
        self.theme_combo = ttk.Combobox(
            toolbar,
            textvariable=self.theme_var,
            values=available_themes,
            state="readonly",
            width=10,
            font=(FONT_UI_FAMILY, 8)
        )
        self.theme_combo.pack(side="left", padx=(2, 6), pady=6)
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_changed)

        self._add_tool_separator(toolbar)

        # Relative Placement Toggle: [Relative Mode] checkbox
        self.relative_mode_var = tk.BooleanVar(value=self.state.is_relative_mode)
        self.rel_check = tk.Checkbutton(
            toolbar,
            text="Relative Mode",
            variable=self.relative_mode_var,
            command=self._on_relative_toggle,
            bg=COLOR_BG_DARK,
            fg="#ffffff",
            selectcolor="#2a2a35",
            activebackground=COLOR_BG_DARK,
            activeforeground="#ffffff",
            font=(FONT_UI_FAMILY, 8, "bold"),
            cursor="hand2"
        )
        self.rel_check.pack(side="left", padx=6, pady=6)

        self._add_tool_separator(toolbar)

        # Export Python (blue), Run Test (teal)
        self._add_tool_btn(toolbar, "Export Python", self.export_python_code, bg="#3a86ff")
        self._add_tool_btn(toolbar, "▶ Run Test", self.run_test_gui, bg="#2a9d8f")

    def _add_tool_btn(self, parent, text, command, bg="#333340"):
        btn = tk.Button(
            parent,
            text=text,
            bg=bg,
            fg="#ffffff",
            activebackground="#444455",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 8, "bold"),
            padx=10,
            pady=4,
            cursor="hand2",
            command=command
        )
        btn.pack(side="left", padx=3, pady=6)
        return btn

    def _add_tool_separator(self, parent):
        sep = tk.Frame(parent, width=1, bg="#454555", height=24)
        sep.pack(side="left", padx=6, pady=8)

    def _build_workspace(self):
        # Master horizontal PanedWindow
        self.h_paned = ttk.PanedWindow(self.root, orient="horizontal")
        self.h_paned.pack(fill="both", expand=True)

        # 1. Left pane: PanedWindow with Top = Widget Palette, Bottom = WidgetTree
        self.left_paned = ttk.PanedWindow(self.h_paned, orient="vertical")
        self.h_paned.add(self.left_paned, weight=0)

        self.palette = WidgetPalette(self.left_paned, on_select_widget=self._on_palette_tool_selected)
        self.left_paned.add(self.palette, weight=1)

        self.widget_tree = WidgetTree(
            self.left_paned,
            self.state,
            on_edit_menu=self._open_menu_editor,
            on_edit_notebook=self._open_notebook_editor,
            on_edit_treeview=self._open_treeview_editor
        )
        self.left_paned.add(self.widget_tree, weight=1)
        self._widget_tree_visible = True

        # 2. Center pane: PanedWindow with Top = Canvas, Bottom = Code Preview
        self.center_paned = ttk.PanedWindow(self.h_paned, orient="vertical")
        self.h_paned.add(self.center_paned, weight=1)

        self.canvas = DesignCanvas(self.center_paned, self.state)
        self.center_paned.add(self.canvas, weight=3)

        self.preview_panel = CodePreviewPanel(self.center_paned, self.state, app_name="main_app")
        self.center_paned.add(self.preview_panel, weight=1)

        # 3. Right pane: Property Inspector
        self.inspector = PropertyInspector(self.h_paned, self.state)
        self.h_paned.add(self.inspector, weight=0)

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self.root, bg="#181820", height=24)
        self.statusbar.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            self.statusbar,
            text="Ready  |  Click a widget in the palette, then click canvas to place.",
            bg="#181820",
            fg="#88889a",
            font=(FONT_UI_FAMILY, 8),
            anchor="w",
            padx=10
        )
        self.status_label.pack(side="left")

        self.info_label = tk.Label(
            self.statusbar,
            text=f"Grid: {self.state.grid_size}px (Snap On)",
            bg="#181820",
            fg="#88889a",
            font=(FONT_UI_FAMILY, 8),
            anchor="e",
            padx=10
        )
        self.info_label.pack(side="right")

    def _is_text_editing(self, event=None) -> bool:
        """Returns True if the focused widget or event source is a text input field."""
        return is_text_editing(self.root, event)

    def cut(self, event=None):
        if self._is_text_editing(event):
            return
        self.state.cut_selected()

    def copy(self, event=None):
        if self._is_text_editing(event):
            return
        self.state.copy_selected()

    def paste(self, event=None):
        if self._is_text_editing(event):
            return
        self.state.paste()

    def duplicate(self, event=None):
        if self._is_text_editing(event):
            return
        self.state.duplicate_selected()

    def delete_selected(self, event=None):
        if self._is_text_editing(event):
            return
        self.state.remove_selected()

    def _bind_global_shortcuts(self):
        mod = "Command" if IS_MAC else "Control"

        # File shortcuts
        self.root.bind_all(f"<{mod}-n>", lambda e: self.new_project())
        self.root.bind_all(f"<{mod}-o>", lambda e: self.open_project())
        self.root.bind_all(f"<{mod}-s>", lambda e: self.save_project())

        # Edit shortcuts
        self.root.bind_all(f"<{mod}-z>", lambda e: self.state.undo())
        self.root.bind_all(f"<{mod}-y>", lambda e: self.state.redo())
        self.root.bind_all(f"<{mod}-x>", lambda e: self.cut(e))
        self.root.bind_all(f"<{mod}-c>", lambda e: self.copy(e))
        self.root.bind_all(f"<{mod}-v>", lambda e: self.paste(e))
        self.root.bind_all(f"<{mod}-d>", lambda e: self.duplicate(e))
        self.root.bind_all("<Delete>", lambda e: self.delete_selected(e))
        self.root.bind_all("<BackSpace>", lambda e: self.delete_selected(e))

        # Run & Export shortcuts
        self.root.bind_all(f"<{mod}-e>", lambda e: self.export_python_code())
        self.root.bind_all(f"<{mod}-r>", lambda e: self.run_test_gui())

    def _on_theme_changed(self, event=None):
        new_theme = self.theme_var.get()
        if new_theme:
            try:
                self.style.theme_use(new_theme)
                self.root.update_idletasks()
                self.status_label.config(text=f"Active theme: {new_theme}")
            except Exception as e:
                print(f"Error applying theme {new_theme}: {e}")

    def _on_relative_toggle(self):
        new_val = bool(self.relative_mode_var.get())
        if hasattr(self.state, "set_relative_mode"):
            self.state.set_relative_mode(new_val)
        else:
            self.state.is_relative_mode = new_val
            self.state.push_state()
        mode_str = "Relative Mode (relx, rely, relwidth, relheight)" if new_val else "Absolute Mode (pixels)"
        self.status_label.config(text=f"Placement changed to {mode_str}")

    def toggle_widget_tree(self):
        """Toggle visibility of the WidgetTree in the left pane."""
        if self._widget_tree_visible:
            self.left_paned.forget(self.widget_tree)
            self._widget_tree_visible = False
            self.status_label.config(text="Widget Tree hidden.")
        else:
            self.left_paned.add(self.widget_tree, weight=1)
            self._widget_tree_visible = True
            self.widget_tree.refresh()
            self.status_label.config(text="Widget Tree visible.")

    def reset_layout(self):
        """Reset workspace panels and ensure WidgetTree is visible."""
        if not self._widget_tree_visible:
            self.left_paned.add(self.widget_tree, weight=1)
            self._widget_tree_visible = True
            self.widget_tree.refresh()
        self.status_label.config(text="Workspace layout reset.")

    def open_menu_editor(self):
        """Opens the MenuEditorDialog to design the application menubar."""
        initial_spec = self.state.menus.get("main_menu")

        def _on_save(spec: MenuBarSpec):
            self.state.menus["main_menu"] = spec
            self.state.push_state()
            if hasattr(self, "widget_tree"):
                self.widget_tree.refresh()
            self.status_label.config(text="Application menubar updated.")

        MenuEditorDialog(self.root, initial_spec=initial_spec, on_save=_on_save)

    def _open_menu_editor(self, widget: Optional[WidgetInstance] = None):
        """Callback from WidgetTree right-click / double-click."""
        self.open_menu_editor()

    def _open_notebook_editor(self, widget: WidgetInstance):
        def _on_save(tabs):
            widget.properties["tabs"] = tabs
            self.state.push_state()
            if hasattr(self, "widget_tree"):
                self.widget_tree.refresh()
            self.status_label.config(text=f"Tabs updated for {widget.name}.")

        NotebookTabEditorDialog(self.root, widget=widget, state=self.state, on_save=_on_save)

    def _open_treeview_editor(self, widget: WidgetInstance):
        def _on_save(columns):
            widget.properties["columns"] = columns
            self.state.push_state()
            if hasattr(self, "widget_tree"):
                self.widget_tree.refresh()
            self.status_label.config(text=f"Columns updated for {widget.name}.")

        TreeviewColumnEditorDialog(self.root, widget=widget, state=self.state, on_save=_on_save)

    def run_test_gui(self):
        """Launches the live GUI in an interactive test sandbox."""
        if hasattr(self, "preview_panel"):
            self.preview_panel.run_test_gui()

    def _on_palette_tool_selected(self, widget_type: Optional[str]):
        self.canvas.set_pending_placement(widget_type)
        if widget_type:
            self.status_label.config(text=f"Placement Mode: Click anywhere on canvas to drop a {widget_type}")
        else:
            self.status_label.config(text="Ready")

    def _update_status(self):
        sel = self.state.get_selected_widget()
        mode_str = " [Rel]" if self.state.is_relative_mode else ""
        if sel:
            pos_info = f"at ({sel.x}, {sel.y})"
            if sel.is_relative and sel.rel_x is not None:
                pos_info += f" rel=({sel.rel_x:.2f}, {sel.rel_y:.2f})"
            self.status_label.config(text=f"Selected: {sel.name} ({sel.widget_type}) {pos_info}{mode_str}")
        else:
            self.status_label.config(text=f"Window: {self.state.title}  ({self.state.width}x{self.state.height}){mode_str}")
        self.palette.set_active_type(self.canvas.pending_widget_type)
        if hasattr(self, "relative_mode_var"):
            self.relative_mode_var.set(self.state.is_relative_mode)

    def _wire_state_listeners(self):
        self.canvas.state = self.state
        self.inspector.state = self.state
        self.preview_panel.state = self.state
        if hasattr(self, "widget_tree"):
            self.widget_tree.state = self.state

        self.state.add_listener(self.canvas.render)
        self.state.add_listener(self.inspector.refresh)
        self.state.add_listener(self.preview_panel.update_code)
        if hasattr(self, "widget_tree"):
            self.state.add_listener(self.widget_tree.refresh)
        self.state.add_listener(self._update_status)

    # --------------------------------------------------------------------------
    # File Operations
    # --------------------------------------------------------------------------

    def new_project(self):
        if self.state.widgets:
            if not messagebox.askyesno("New Project", "Start a new project? Any unsaved changes will be lost."):
                return
        self.state = ProjectState(title="New Application", width=550, height=380)
        self._wire_state_listeners()
        self.current_file_path = None
        self.state.notify()

    def open_project(self):
        path = filedialog.askopenfilename(
            title="Open PageStudio Project",
            filetypes=[("PageStudio Projects", "*.pgproj"), ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not path:
            return
        self.load_project_file(path)

    def load_project_file(self, path: str):
        try:
            self.state = ProjectSerializer.load_from_file(path)
            self._wire_state_listeners()
            self.current_file_path = path
            self.state.notify()
            self.status_label.config(text=f"Opened: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load project file:\n{e}")

    def save_project(self):
        if not self.current_file_path:
            self.save_project_as()
        else:
            try:
                ProjectSerializer.save_to_file(self.state, self.current_file_path)
                self.status_label.config(text=f"Saved: {os.path.basename(self.current_file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save project:\n{e}")

    def save_project_as(self):
        path = filedialog.asksaveasfilename(
            title="Save PageStudio Project",
            defaultextension=".pgproj",
            filetypes=[("PageStudio Projects", "*.pgproj"), ("JSON Files", "*.json")]
        )
        if not path:
            return
        self.current_file_path = path
        self.save_project()

    def export_python_code(self):
        # Prompt user to choose application base name
        app_name = simpledialog.askstring("Export Python", "Enter application base name:", initialvalue="app")
        if not app_name:
            return
        app_name = app_name.strip()
        if not app_name:
            return

        target_dir = filedialog.askdirectory(title="Select Folder to Export Python Files")
        if not target_dir:
            return

        try:
            gui_path, sup_path = CodeGenerator.generate_all(self.state, app_name, target_dir)
            messagebox.showinfo(
                "Export Complete",
                f"Successfully generated 2 Python modules:\n\n1. {gui_path}\n2. {sup_path}"
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to generate code:\n{e}")

    def _show_about(self):
        messagebox.showinfo(
            "About PageStudio",
            "PageStudio v1.0.0\n"
            "A modern, cross-platform visual GUI generator for Python and Tkinter.\n\n"
            "• Pure Python - zero third-party dependencies required\n"
            "• Natively supports macOS (Apple Silicon & Intel), Windows, and Linux\n"
            "• Clean 2-file architecture (<app>.py + <app>_support.py)\n"
            "• Visual drag-and-drop, 8-point resize handles & grid snapping\n"
            "• Hierarchical Widget Tree & Menu/Notebook/Treeview Visual Editors"
        )

    def _show_mac_notes(self):
        messagebox.showinfo(
            "macOS Compatibility",
            "Unlike legacy PAGE which crashed on Mac due to X11 floating windows,\n"
            "PageStudio is built in a single unified frame using standard Python Tkinter.\n\n"
            "It runs 100% natively on macOS (with full support for ⌘ Command shortcuts and Retina display rendering)!"
        )
