"""
PageStudio - Widget Palette
Left-hand sidebar displaying available widgets grouped by category.
Clicking a tool arms the canvas for placement.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Callable, Optional
from ..core.models import WIDGET_CATALOG, WidgetTypeSpec
from ..ui.theme import COLOR_BG_PANEL, COLOR_ACCENT, FONT_UI_FAMILY

class WidgetPalette(tk.Frame):
    """Component tool palette."""

    def __init__(self, parent, on_select_widget: Callable[[str], None], **kwargs):
        super().__init__(parent, bg=COLOR_BG_PANEL, **kwargs)
        self.on_select_widget = on_select_widget
        self.active_type: Optional[str] = None
        self.buttons: Dict[str, tk.Button] = {}
        
        self._build_ui()

    def _build_ui(self):
        # Header title
        header = tk.Label(
            self,
            text="WIDGET PALETTE",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=12,
            pady=10
        )
        header.pack(fill="x")

        # Scrollable container for categories
        canvas = tk.Canvas(self, bg=COLOR_BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=COLOR_BG_PANEL)

        content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=content, anchor="nw", width=180)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Group widgets by category
        categories: Dict[str, List[WidgetTypeSpec]] = {}
        for spec in WIDGET_CATALOG.values():
            categories.setdefault(spec.category, []).append(spec)

        for cat_name, specs in categories.items():
            cat_label = tk.Label(
                content,
                text=cat_name.upper(),
                bg=COLOR_BG_PANEL,
                fg="#5f5f70",
                font=(FONT_UI_FAMILY, 8, "bold"),
                anchor="w",
                padx=12,
                pady=6
            )
            cat_label.pack(fill="x")

            for spec in specs:
                btn = tk.Button(
                    content,
                    text=f" +  {spec.type_name}",
                    bg="#2d2d38",
                    fg="#e0e0ea",
                    activebackground=COLOR_ACCENT,
                    activeforeground="#ffffff",
                    relief="flat",
                    anchor="w",
                    padx=12,
                    pady=4,
                    font=(FONT_UI_FAMILY, 9),
                    cursor="hand2",
                    command=lambda t=spec.type_name: self._handle_click(t)
                )
                btn.pack(fill="x", padx=8, pady=2)
                self.buttons[spec.type_name] = btn

    def _handle_click(self, widget_type: str):
        if self.active_type == widget_type:
            # Deselect
            self.set_active_type(None)
            self.on_select_widget(None)
        else:
            self.set_active_type(widget_type)
            self.on_select_widget(widget_type)

    def set_active_type(self, widget_type: Optional[str]):
        """Visually updates which tool is highlighted."""
        self.active_type = widget_type
        for t, btn in self.buttons.items():
            if t == widget_type:
                btn.config(bg=COLOR_ACCENT, fg="#ffffff")
            else:
                btn.config(bg="#2d2d38", fg="#e0e0ea")
