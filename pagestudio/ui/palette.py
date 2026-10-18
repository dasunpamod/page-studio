"""
PageStudio - Widget Palette
Left-hand sidebar displaying all 42 available widgets grouped into clear,
collapsible and scrollable sections:
  - Basic Controls: Button, Entry, Label, Checkbutton, Radiobutton, Spinbox, Message, Menubutton, Separator, Popupmenu
  - Themed Controls: TButton, TEntry, TLabel, TCheckbutton, TRadiobutton, TCombobox, TSpinbox, TMenubutton, TScale, TProgressbar, TSeparator, TSizegrip
  - Containers & Windows: Frame, LabelFrame, TFrame, TLabelframe, TNotebook, TPanedwindow, Canvas, Toplevel
  - Data & Choices: Combobox, Listbox, Text, Scale, Progressbar
  - Scrolled & Advanced: Scrolledtext, Scrolledlistbox, Scrolledtreeview, Scrolledentry, Scrolledwindow, Treeview, Custom

Includes a search/filter entry at the top to quickly filter widgets by name in real-time.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Callable, Optional, Set
from ..core.models import WIDGET_CATALOG
from ..ui.theme import (
    COLOR_BG_PANEL,
    COLOR_BG_DARK,
    COLOR_ACCENT,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    FONT_UI_FAMILY
)
from ..utils.helpers import IS_MAC


PALETTE_SECTIONS: Dict[str, List[str]] = {
    "Basic Controls": [
        "Button", "Entry", "Label", "Checkbutton", "Radiobutton",
        "Spinbox", "Message", "Menubutton", "Separator", "Popupmenu"
    ],
    "Themed Controls": [
        "TButton", "TEntry", "TLabel", "TCheckbutton", "TRadiobutton",
        "TCombobox", "TSpinbox", "TMenubutton", "TScale", "TProgressbar",
        "TSeparator", "TSizegrip"
    ],
    "Containers & Windows": [
        "Frame", "LabelFrame", "TFrame", "TLabelframe",
        "TNotebook", "TPanedwindow", "Canvas", "Toplevel"
    ],
    "Data & Choices": [
        "Combobox", "Listbox", "Text", "Scale", "Progressbar"
    ],
    "Scrolled & Advanced": [
        "Scrolledtext", "Scrolledlistbox", "Scrolledtreeview",
        "Scrolledentry", "Scrolledwindow", "Treeview", "Custom"
    ]
}


class WidgetPalette(tk.Frame):
    """Component tool palette with search filter and collapsible categorized sections."""

    def __init__(self, parent, on_select_widget: Callable[[Optional[str]], None], **kwargs):
        super().__init__(parent, bg=COLOR_BG_PANEL, **kwargs)
        self.on_select_widget = on_select_widget
        self.active_type: Optional[str] = None
        self.buttons: Dict[str, tk.Button] = {}

        # Section collapse tracking: {section_name: is_collapsed}
        self.collapsed: Dict[str, bool] = {sec: False for sec in PALETTE_SECTIONS}
        self.section_frames: Dict[str, tk.Frame] = {}
        self.section_headers: Dict[str, tk.Button] = {}
        self.section_bodies: Dict[str, tk.Frame] = {}
        self.section_widgets: Dict[str, List[str]] = {}

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
            pady=6
        )
        header.pack(fill="x", pady=(2, 0))

        # Search / Filter Bar at top
        filter_box = tk.Frame(self, bg=COLOR_BG_DARK, bd=1, relief="solid")
        filter_box.pack(fill="x", padx=8, pady=(0, 6))

        search_icon = tk.Label(
            filter_box,
            text="🔍",
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MUTED,
            font=(FONT_UI_FAMILY, 8)
        )
        search_icon.pack(side="left", padx=(6, 2))

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._on_filter_changed)
        self.filter_entry = tk.Entry(
            filter_box,
            textvariable=self.filter_var,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            insertbackground=COLOR_TEXT_MAIN,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        self.filter_entry.pack(side="left", fill="x", expand=True, pady=3, padx=(0, 2))

        self.clear_btn = tk.Button(
            filter_box,
            text="✕",
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MUTED,
            activebackground=COLOR_BG_DARK,
            activeforeground=COLOR_TEXT_MAIN,
            relief="flat",
            bd=0,
            font=(FONT_UI_FAMILY, 8),
            cursor="hand2",
            command=lambda: self.filter_var.set("")
        )
        self.clear_btn.pack(side="right", padx=(0, 4))

        # Scrollable container for categories
        self.canvas = tk.Canvas(self, bg=COLOR_BG_PANEL, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=COLOR_BG_PANEL)

        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw", width=200)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self._content_window, width=e.width)
        )

        # Mouse wheel support across platforms (Windows, macOS, Linux)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_linux_scroll_up)
        self.canvas.bind("<Button-5>", self._on_linux_scroll_down)
        self.content.bind("<MouseWheel>", self._on_mousewheel)
        self.content.bind("<Button-4>", self._on_linux_scroll_up)
        self.content.bind("<Button-5>", self._on_linux_scroll_down)

        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_linux_scroll_up, add="+")
        self.bind_all("<Button-5>", self._on_linux_scroll_down, add="+")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Build sections
        self._populate_sections()

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

    def _populate_sections(self):
        placed_widgets: Set[str] = set()

        for sec_name, widget_names in PALETTE_SECTIONS.items():
            valid_names = [name for name in widget_names if name in WIDGET_CATALOG]
            placed_widgets.update(valid_names)
            self.section_widgets[sec_name] = valid_names

            # Outer frame for section
            sec_frame = tk.Frame(self.content, bg=COLOR_BG_PANEL)
            sec_frame.pack(fill="x", pady=(2, 2))
            self.section_frames[sec_name] = sec_frame

            # Section header button (collapsible toggle)
            hdr_btn = tk.Button(
                sec_frame,
                text=f"▼  {sec_name.upper()}",
                bg="#1c1c24",
                fg="#a0a0b5",
                activebackground="#2a2a35",
                activeforeground="#ffffff",
                relief="flat",
                anchor="w",
                padx=10,
                pady=4,
                font=(FONT_UI_FAMILY, 8, "bold"),
                cursor="hand2",
                command=lambda s=sec_name: self._toggle_section(s)
            )
            hdr_btn.pack(fill="x")
            self.section_headers[sec_name] = hdr_btn

            # Section body frame containing widget buttons
            body_frame = tk.Frame(sec_frame, bg=COLOR_BG_PANEL)
            body_frame.pack(fill="x", pady=2)
            self.section_bodies[sec_name] = body_frame

            for name in valid_names:
                btn = tk.Button(
                    body_frame,
                    text=f" +  {name}",
                    bg="#2d2d38",
                    fg="#e0e0ea",
                    activebackground=COLOR_ACCENT,
                    activeforeground="#ffffff",
                    relief="flat",
                    anchor="w",
                    padx=14,
                    pady=3,
                    font=(FONT_UI_FAMILY, 9),
                    cursor="hand2",
                    command=lambda t=name: self._handle_click(t)
                )
                btn.pack(fill="x", padx=6, pady=1)
                self.buttons[name] = btn

        # Fallback for any unexpected catalog additions
        remaining = [k for k in WIDGET_CATALOG if k not in placed_widgets]
        if remaining:
            sec_name = "Other Controls"
            self.section_widgets[sec_name] = remaining
            sec_frame = tk.Frame(self.content, bg=COLOR_BG_PANEL)
            sec_frame.pack(fill="x", pady=(2, 2))
            self.section_frames[sec_name] = sec_frame

            hdr_btn = tk.Button(
                sec_frame,
                text=f"▼  {sec_name.upper()}",
                bg="#1c1c24",
                fg="#a0a0b5",
                activebackground="#2a2a35",
                activeforeground="#ffffff",
                relief="flat",
                anchor="w",
                padx=10,
                pady=4,
                font=(FONT_UI_FAMILY, 8, "bold"),
                cursor="hand2",
                command=lambda s=sec_name: self._toggle_section(s)
            )
            hdr_btn.pack(fill="x")
            self.section_headers[sec_name] = hdr_btn

            body_frame = tk.Frame(sec_frame, bg=COLOR_BG_PANEL)
            body_frame.pack(fill="x", pady=2)
            self.section_bodies[sec_name] = body_frame

            for name in remaining:
                btn = tk.Button(
                    body_frame,
                    text=f" +  {name}",
                    bg="#2d2d38",
                    fg="#e0e0ea",
                    activebackground=COLOR_ACCENT,
                    activeforeground="#ffffff",
                    relief="flat",
                    anchor="w",
                    padx=14,
                    pady=3,
                    font=(FONT_UI_FAMILY, 9),
                    cursor="hand2",
                    command=lambda t=name: self._handle_click(t)
                )
                btn.pack(fill="x", padx=6, pady=1)
                self.buttons[name] = btn

    def _toggle_section(self, sec_name: str):
        """Toggle collapsed/expanded state of a section."""
        is_collapsed = not self.collapsed.get(sec_name, False)
        self.collapsed[sec_name] = is_collapsed
        body = self.section_bodies.get(sec_name)
        hdr = self.section_headers.get(sec_name)

        if is_collapsed:
            if body:
                body.pack_forget()
            if hdr:
                hdr.config(text=f"▶  {sec_name.upper()}")
        else:
            if body:
                body.pack(fill="x", pady=2)
            if hdr:
                hdr.config(text=f"▼  {sec_name.upper()}")

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_filter_changed(self, *args):
        """Filter widget buttons in real-time as user types query."""
        query = self.filter_var.get().strip().lower()

        if not query:
            # Restore normal section views according to collapse state
            for sec_name, body in self.section_bodies.items():
                sec_frame = self.section_frames.get(sec_name)
                hdr = self.section_headers.get(sec_name)
                if sec_frame:
                    sec_frame.pack(fill="x", pady=(2, 2))

                is_collapsed = self.collapsed.get(sec_name, False)
                if is_collapsed:
                    body.pack_forget()
                    if hdr:
                        hdr.config(text=f"▶  {sec_name.upper()}")
                else:
                    body.pack(fill="x", pady=2)
                    if hdr:
                        hdr.config(text=f"▼  {sec_name.upper()}")

                # Show all buttons in section
                for name in self.section_widgets.get(sec_name, []):
                    btn = self.buttons.get(name)
                    if btn:
                        btn.pack(fill="x", padx=6, pady=1)
        else:
            # Filter per section
            for sec_name, body in self.section_bodies.items():
                sec_frame = self.section_frames.get(sec_name)
                hdr = self.section_headers.get(sec_name)
                matching = []

                for name in self.section_widgets.get(sec_name, []):
                    btn = self.buttons.get(name)
                    spec = WIDGET_CATALOG.get(name)
                    disp = spec.display_name.lower() if spec else ""
                    if query in name.lower() or query in disp:
                        matching.append(name)
                        if btn:
                            btn.pack(fill="x", padx=6, pady=1)
                    else:
                        if btn:
                            btn.pack_forget()

                if matching:
                    if sec_frame:
                        sec_frame.pack(fill="x", pady=(2, 2))
                    body.pack(fill="x", pady=2)
                    if hdr:
                        hdr.config(text=f"▼  {sec_name.upper()} ({len(matching)})")
                else:
                    if sec_frame:
                        sec_frame.pack_forget()

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

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
