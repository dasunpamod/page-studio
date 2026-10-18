"""
PageStudio - Live Code Preview & Runner
Bottom / modal tab providing live Python code preview and instant test-run capabilities.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import tempfile
import subprocess
import os
import sys
import shutil
import atexit
from typing import Optional, Set
from ..core.state import ProjectState
from ..core.generator import CodeGenerator
from ..ui.theme import COLOR_BG_PANEL, FONT_UI_FAMILY, FONT_CODE_FAMILY

PREVIEW_DIR = os.path.join(tempfile.gettempdir(), "pagestudio_preview")
_active_processes: Set[subprocess.Popen] = set()

def _cleanup_preview():
    for p in list(_active_processes):
        try:
            if p.poll() is None:
                p.terminate()
        except Exception:
            pass
    try:
        if os.path.exists(PREVIEW_DIR):
            shutil.rmtree(PREVIEW_DIR, ignore_errors=True)
    except Exception:
        pass

atexit.register(_cleanup_preview)

class CodePreviewPanel(tk.Frame):
    """Live interactive preview of generated Python Tkinter code."""

    def __init__(self, parent, state: ProjectState, app_name: str = "app", **kwargs):
        super().__init__(parent, bg=COLOR_BG_PANEL, **kwargs)
        self.state = state
        self.app_name = app_name
        self._active_proc: Optional[subprocess.Popen] = None
        
        self._build_ui()
        self.state.add_listener(self.update_code)
        self.update_code()

    def _build_ui(self):
        # Top toolbar
        toolbar = tk.Frame(self, bg=COLOR_BG_PANEL)
        toolbar.pack(fill="x", padx=12, pady=6)

        title = tk.Label(
            toolbar,
            text="LIVE CODE PREVIEW",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold")
        )
        title.pack(side="left")

        # Run Test Button
        self.run_btn = tk.Button(
            toolbar,
            text="▶  Run / Test GUI",
            bg="#2a9d8f",
            fg="#ffffff",
            activebackground="#21867a",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 9, "bold"),
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.run_test_gui
        )
        self.run_btn.pack(side="right", padx=4)

        # Tab Notebook for <app>.py and <app>_support.py
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # GUI Tab
        gui_frame = tk.Frame(self.notebook, bg="#181820")
        self.gui_text = tk.Text(
            gui_frame,
            bg="#181820",
            fg="#e0e0ea",
            insertbackground="#ffffff",
            font=(FONT_CODE_FAMILY, 10),
            wrap="none",
            relief="flat",
            padx=8,
            pady=8
        )
        gui_scroll_y = ttk.Scrollbar(gui_frame, orient="vertical", command=self.gui_text.yview)
        gui_scroll_x = ttk.Scrollbar(gui_frame, orient="horizontal", command=self.gui_text.xview)
        self.gui_text.configure(xscrollcommand=gui_scroll_x.set, yscrollcommand=gui_scroll_y.set)

        self.gui_text.pack(side="left", fill="both", expand=True)
        gui_scroll_y.pack(side="right", fill="y")
        gui_scroll_x.pack(side="bottom", fill="x")

        self.notebook.add(gui_frame, text=f"  {self.app_name}.py (GUI)  ")

        # Support Tab
        sup_frame = tk.Frame(self.notebook, bg="#181820")
        self.sup_text = tk.Text(
            sup_frame,
            bg="#181820",
            fg="#e0e0ea",
            insertbackground="#ffffff",
            font=(FONT_CODE_FAMILY, 10),
            wrap="none",
            relief="flat",
            padx=8,
            pady=8
        )
        sup_scroll_y = ttk.Scrollbar(sup_frame, orient="vertical", command=self.sup_text.yview)
        sup_scroll_x = ttk.Scrollbar(sup_frame, orient="horizontal", command=self.sup_text.xview)
        self.sup_text.configure(xscrollcommand=sup_scroll_x.set, yscrollcommand=sup_scroll_y.set)

        self.sup_text.pack(side="left", fill="both", expand=True)
        sup_scroll_y.pack(side="right", fill="y")
        sup_scroll_x.pack(side="bottom", fill="x")

        self.notebook.add(sup_frame, text=f"  {self.app_name}_support.py (Logic)  ")

    def update_code(self):
        """Regenerates live code and updates the preview text boxes."""
        if getattr(self.state, "is_dragging", False):
            return
        try:
            gui_code = CodeGenerator.generate_gui_code(self.state, self.app_name, f"{self.app_name}_support")
            sup_code = CodeGenerator.generate_support_code(self.state, self.app_name)

            self.gui_text.config(state="normal")
            self.gui_text.delete("1.0", "end")
            self.gui_text.insert("1.0", gui_code)
            self.gui_text.config(state="disabled")

            self.sup_text.config(state="normal")
            self.sup_text.delete("1.0", "end")
            self.sup_text.insert("1.0", sup_code)
            self.sup_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating live code preview: {e}")

    def _terminate_active_proc(self):
        """Terminates any actively running preview subprocess."""
        if self._active_proc:
            if self._active_proc.poll() is None:
                try:
                    self._active_proc.terminate()
                    try:
                        self._active_proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        self._active_proc.kill()
                except Exception:
                    pass
            _active_processes.discard(self._active_proc)
            self._active_proc = None

    def run_test_gui(self):
        """Generates preview files and launches the live GUI in a test subprocess."""
        # Terminate any running preview process before starting a new one
        self._terminate_active_proc()

        try:
            os.makedirs(PREVIEW_DIR, exist_ok=True)
            gui_path, support_path = CodeGenerator.generate_all(self.state, self.app_name, PREVIEW_DIR)
            proc = subprocess.Popen([sys.executable, gui_path], shell=False)
            self._active_proc = proc
            _active_processes.add(proc)
        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to launch test GUI:\n{e}")

    def cleanup(self):
        """Explicitly terminates any active preview subprocess and removes temp files."""
        self._terminate_active_proc()
        _cleanup_preview()

    def destroy(self):
        """Cleanup process when panel is destroyed."""
        self._terminate_active_proc()
        super().destroy()

def cleanup_preview():
    """Module-level cleanup helper for terminating subprocesses and removing preview directory."""
    _cleanup_preview()

