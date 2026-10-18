"""
PageStudio - Main IDE Window
Unified single-pane workspace integrating the Palette, Canvas, Property Inspector,
and Code Preview with native menu and toolbars.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from typing import Optional
from ..core.state import ProjectState
from ..core.models import WidgetInstance
from ..core.serializer import ProjectSerializer
from ..core.generator import CodeGenerator
from ..ui.canvas import DesignCanvas
from ..ui.palette import WidgetPalette
from ..ui.inspector import PropertyInspector
from ..ui.preview import CodePreviewPanel
from ..ui.theme import apply_theme, COLOR_BG_DARK, COLOR_BG_PANEL, FONT_UI_FAMILY
from ..utils.helpers import IS_MAC, get_platform_shortcut

class PageStudioApp:
    """Main Application Controller for PageStudio."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PageStudio - Modern Python GUI Builder")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        # State
        self.current_file_path: Optional[str] = None
        self.state = ProjectState(title="My Application", width=550, height=380)
        
        # Styling
        apply_theme(self.root)
        
        self._build_toolbar()
        self._build_statusbar()
        self._build_workspace()
        self._build_menus()
        self._bind_global_shortcuts()

        # Initial render
        self.canvas.render()
        self.state.add_listener(self._update_status)

    def _build_menus(self):
        menubar = tk.Menu(self.root)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Project", accelerator=get_platform_shortcut("N"), command=self.new_project)
        file_menu.add_command(label="Open Project...", accelerator=get_platform_shortcut("O"), command=self.open_project)
        file_menu.add_command(label="Save Project", accelerator=get_platform_shortcut("S"), command=self.save_project)
        file_menu.add_command(label="Save Project As...", accelerator=get_platform_shortcut("Shift+S"), command=self.save_project_as)
        file_menu.add_separator()
        file_menu.add_command(label="Export Python Code...", accelerator=get_platform_shortcut("E"), command=self.export_python_code)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit Menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", accelerator=get_platform_shortcut("Z"), command=self.state.undo)
        edit_menu.add_command(label="Redo", accelerator=get_platform_shortcut("Y"), command=self.state.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Duplicate", accelerator=get_platform_shortcut("D"), command=self.state.duplicate_selected)
        edit_menu.add_command(label="Delete", accelerator="Del", command=self.state.remove_selected)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Run Menu
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

        # Action Buttons
        self._add_tool_btn(toolbar, "New", self.new_project)
        self._add_tool_btn(toolbar, "Open", self.open_project)
        self._add_tool_btn(toolbar, "Save", self.save_project)
        
        self._add_tool_separator(toolbar)
        self._add_tool_btn(toolbar, "↶ Undo", self.state.undo)
        self._add_tool_btn(toolbar, "↷ Redo", self.state.redo)

        self._add_tool_separator(toolbar)
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
        btn.pack(side="left", padx=4, pady=6)
        return btn

    def _add_tool_separator(self, parent):
        sep = tk.Frame(parent, width=1, bg="#454555", height=24)
        sep.pack(side="left", padx=6, pady=8)

    def _build_workspace(self):
        # Master paned container
        self.h_paned = ttk.PanedWindow(self.root, orient="horizontal")
        self.h_paned.pack(fill="both", expand=True)

        # 1. Left: Widget Palette
        self.palette = WidgetPalette(self.h_paned, on_select_widget=self._on_palette_tool_selected)
        self.h_paned.add(self.palette, weight=0)

        # 2. Center: Canvas and Preview Paned Vertically
        center_paned = ttk.PanedWindow(self.h_paned, orient="vertical")
        self.h_paned.add(center_paned, weight=1)

        self.canvas = DesignCanvas(center_paned, self.state)
        center_paned.add(self.canvas, weight=3)

        self.preview_panel = CodePreviewPanel(center_paned, self.state, app_name="main_app")
        center_paned.add(self.preview_panel, weight=1)

        # 3. Right: Property Inspector
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

    def _bind_global_shortcuts(self):
        mod = "Command" if IS_MAC else "Control"
        self.root.bind_all(f"<{mod}-n>", lambda e: self.new_project())
        self.root.bind_all(f"<{mod}-o>", lambda e: self.open_project())
        self.root.bind_all(f"<{mod}-s>", lambda e: self.save_project())
        self.root.bind_all(f"<{mod}-z>", lambda e: self.state.undo())
        self.root.bind_all(f"<{mod}-y>", lambda e: self.state.redo())
        self.root.bind_all(f"<{mod}-d>", lambda e: self.state.duplicate_selected())
        self.root.bind_all(f"<{mod}-e>", lambda e: self.export_python_code())
        self.root.bind_all(f"<{mod}-r>", lambda e: self.run_test_gui())

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
        if sel:
            self.status_label.config(text=f"Selected: {sel.name} ({sel.widget_type}) at ({sel.x}, {sel.y})")
        else:
            self.status_label.config(text=f"Window: {self.state.title}  ({self.state.width}x{self.state.height})")
        self.palette.set_active_type(self.canvas.pending_widget_type)

    # --------------------------------------------------------------------------
    # File Operations
    # --------------------------------------------------------------------------

    def new_project(self):
        if self.state.widgets:
            if not messagebox.askyesno("New Project", "Start a new project? Any unsaved changes will be lost."):
                return
        self.state = ProjectState(title="New Application", width=550, height=380)
        self.canvas.state = self.state
        self.inspector.state = self.state
        self.preview_panel.state = self.state
        self.state.add_listener(self.canvas.render)
        self.state.add_listener(self.inspector.refresh)
        self.state.add_listener(self.preview_panel.update_code)
        self.state.add_listener(self._update_status)
        self.current_file_path = None
        self.state.notify()

    def open_project(self):
        path = filedialog.askopenfilename(
            title="Open PageStudio Project",
            filetypes=[("PageStudio Projects", "*.pgproj"), ("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            self.state = ProjectSerializer.load_from_file(path)
            self.canvas.state = self.state
            self.inspector.state = self.state
            self.preview_panel.state = self.state
            self.state.add_listener(self.canvas.render)
            self.state.add_listener(self.inspector.refresh)
            self.state.add_listener(self.preview_panel.update_code)
            self.state.add_listener(self._update_status)
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
        target_dir = filedialog.askdirectory(title="Select Folder to Export Python Files")
        if not target_dir:
            return
        app_name = "app"
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
            "• Visual drag-and-drop, 8-point resize handles & grid snapping"
        )

    def _show_mac_notes(self):
        messagebox.showinfo(
            "macOS Compatibility",
            "Unlike legacy PAGE which crashed on Mac due to X11 floating windows,\n"
            "PageStudio is built in a single unified frame using standard Python Tkinter.\n\n"
            "It runs 100% natively on macOS (with full support for ⌘ Command shortcuts and Retina display rendering)!"
        )
