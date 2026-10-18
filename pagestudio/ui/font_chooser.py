"""
PageStudio - Visual Font Chooser Dialog
Modal dialog for selecting font family, size, and styles with real-time preview.
Uses standard library tkinter/ttk and tkinter.font with zero dependencies.
"""

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from typing import Optional, Callable, Tuple, Any, List

from ..ui.theme import (
    COLOR_BG_DARK,
    COLOR_BG_PANEL,
    COLOR_CANVAS_PAPER,
    COLOR_TEXT_MAIN,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT,
    FONT_UI_FAMILY
)
from ..utils.helpers import IS_MAC


class FontChooserDialog(tk.Toplevel):
    """Modal dialog allowing developers to visually pick font family, size, and styles."""

    COMMON_SIZES = (8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 28, 32, 36, 48, 72)
    PREVIEW_TEXT = "The quick brown fox jumps over the lazy dog 123"

    def __init__(
        self,
        parent,
        initial_font: Optional[Any] = None,
        on_save: Optional[Callable[[Tuple[str, int, str]], None]] = None,
        modal: bool = False
    ):
        super().__init__(parent)
        self.title("PageStudio - Font Chooser")
        self.geometry("700x500")
        self.minsize(620, 420)
        self.configure(bg=COLOR_BG_DARK)

        self.on_save = on_save
        self.result: Optional[Tuple[str, int, str]] = None

        # Parse initial font parameters
        family, size, bold, italic, underline = self._parse_font_spec(initial_font)
        self.current_family: str = family
        self.current_size: int = size

        self.bold_var = tk.BooleanVar(value=bold)
        self.italic_var = tk.BooleanVar(value=italic)
        self.underline_var = tk.BooleanVar(value=underline)
        self.search_var = tk.StringVar()
        self.size_var = tk.StringVar(value=str(size))

        # Query system fonts
        self.all_families: List[str] = self._get_font_families()

        self._is_updating: bool = False
        self.preview_font: Optional[tkfont.Font] = None

        self._build_ui()
        self._populate_families()
        self._select_family(self.current_family)
        self._update_preview()

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
    def choose_font(
        cls,
        parent,
        initial_font: Optional[Any] = None,
        on_save: Optional[Callable[[Tuple[str, int, str]], None]] = None
    ) -> Optional[Tuple[str, int, str]]:
        """Convenience method to show dialog modally and return (family, size, style_string)."""
        dialog = cls(parent, initial_font=initial_font, on_save=on_save, modal=False)
        parent.wait_window(dialog)
        return dialog.result

    def _get_font_families(self) -> List[str]:
        try:
            raw = list(tkfont.families(self))
            # Filter out internal/hidden fonts starting with @ on Windows
            clean = sorted(set(f for f in raw if not f.startswith("@")))
            return clean if clean else ["Arial", "Courier", "Helvetica", "Times"]
        except Exception:
            return ["Arial", "Courier", "Helvetica", "Times", "Segoe UI"]

    def _parse_font_spec(self, spec: Any) -> Tuple[str, int, bool, bool, bool]:
        """Parses various font specification formats into (family, size, bold, italic, underline)."""
        default_family = "Helvetica" if IS_MAC else "Segoe UI"
        default_size = 10
        bold = False
        italic = False
        underline = False

        if not spec:
            return default_family, default_size, bold, italic, underline

        if isinstance(spec, (tuple, list)):
            if len(spec) >= 1 and spec[0]:
                default_family = str(spec[0])
            if len(spec) >= 2:
                try:
                    default_size = int(spec[1])
                except (ValueError, TypeError):
                    default_size = 10
            if len(spec) >= 3 and spec[2]:
                style_str = str(spec[2]).lower()
                bold = "bold" in style_str
                italic = "italic" in style_str
                underline = "underline" in style_str
            return default_family, default_size, bold, italic, underline

        if isinstance(spec, dict):
            fam = spec.get("family", default_family)
            sz = int(spec.get("size", default_size))
            b = spec.get("weight") == "bold" or spec.get("bold", False)
            i = spec.get("slant") == "italic" or spec.get("italic", False)
            u = bool(spec.get("underline", False))
            return fam, sz, b, i, u

        if isinstance(spec, str):
            tokens = spec.split()
            if tokens:
                # Last token could be style or size
                # Check for styles
                lower_tokens = [t.lower() for t in tokens]
                bold = "bold" in lower_tokens
                italic = "italic" in lower_tokens
                underline = "underline" in lower_tokens

                # Check for size integer
                family_tokens = []
                for t in tokens:
                    if t.isdigit():
                        default_size = int(t)
                    elif t.lower() not in ("bold", "italic", "underline", "normal", "roman"):
                        family_tokens.append(t)
                if family_tokens:
                    default_family = " ".join(family_tokens)

        return default_family, default_size, bold, italic, underline

    def _build_ui(self):
        main_frame = tk.Frame(self, bg=COLOR_BG_DARK)
        main_frame.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        # --- UPPER SECTION: 3 Columns (Family, Size, Style) ---
        upper_frame = tk.Frame(main_frame, bg=COLOR_BG_DARK)
        upper_frame.pack(fill="both", expand=True)

        # 1. Family Column
        family_frame = tk.Frame(upper_frame, bg=COLOR_BG_PANEL)
        family_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(
            family_frame,
            text="FONT FAMILY",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=8,
            pady=6
        ).pack(fill="x")

        # Search filter
        search_box = tk.Frame(family_frame, bg=COLOR_BG_DARK)
        search_box.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(search_box, text="🔍", bg=COLOR_BG_DARK, fg=COLOR_TEXT_MUTED, font=(FONT_UI_FAMILY, 8)).pack(side="left", padx=2)
        search_entry = tk.Entry(
            search_box,
            textvariable=self.search_var,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        search_entry.pack(side="left", fill="x", expand=True, pady=2)
        self.search_var.trace_add("write", lambda *a: self._filter_families())

        # Family listbox + scrollbar
        fam_list_frame = tk.Frame(family_frame, bg=COLOR_BG_DARK)
        fam_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.family_listbox = tk.Listbox(
            fam_list_frame,
            selectmode="browse",
            exportselection=False,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            selectbackground=COLOR_ACCENT,
            selectforeground="#ffffff",
            highlightthickness=0,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        fam_scroll = ttk.Scrollbar(fam_list_frame, orient="vertical", command=self.family_listbox.yview)
        self.family_listbox.configure(yscrollcommand=fam_scroll.set)

        self.family_listbox.pack(side="left", fill="both", expand=True)
        fam_scroll.pack(side="right", fill="y")
        self.family_listbox.bind("<<ListboxSelect>>", self._on_family_selected)

        # 2. Size Column
        size_frame = tk.Frame(upper_frame, bg=COLOR_BG_PANEL, width=120)
        size_frame.pack(side="left", fill="y", padx=3)
        size_frame.pack_propagate(False)

        tk.Label(
            size_frame,
            text="SIZE",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=8,
            pady=6
        ).pack(fill="x")

        # Size Entry / Spinbox
        size_entry = tk.Entry(
            size_frame,
            textvariable=self.size_var,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            relief="flat",
            font=(FONT_UI_FAMILY, 9),
            justify="center"
        )
        size_entry.pack(fill="x", padx=8, pady=(0, 4))
        self.size_var.trace_add("write", lambda *a: self._on_size_entry_changed())

        # Size listbox
        sz_list_frame = tk.Frame(size_frame, bg=COLOR_BG_DARK)
        sz_list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.size_listbox = tk.Listbox(
            sz_list_frame,
            selectmode="browse",
            exportselection=False,
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MAIN,
            selectbackground=COLOR_ACCENT,
            selectforeground="#ffffff",
            highlightthickness=0,
            relief="flat",
            font=(FONT_UI_FAMILY, 9)
        )
        sz_scroll = ttk.Scrollbar(sz_list_frame, orient="vertical", command=self.size_listbox.yview)
        self.size_listbox.configure(yscrollcommand=sz_scroll.set)

        for s in self.COMMON_SIZES:
            self.size_listbox.insert("end", str(s))

        self.size_listbox.pack(side="left", fill="both", expand=True)
        sz_scroll.pack(side="right", fill="y")
        self.size_listbox.bind("<<ListboxSelect>>", self._on_size_list_selected)

        # 3. Styles Column
        style_frame = tk.Frame(upper_frame, bg=COLOR_BG_PANEL, width=150)
        style_frame.pack(side="left", fill="y", padx=(6, 0))
        style_frame.pack_propagate(False)

        tk.Label(
            style_frame,
            text="STYLE",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 9, "bold"),
            anchor="w",
            padx=8,
            pady=6
        ).pack(fill="x")

        checks_frame = tk.Frame(style_frame, bg=COLOR_BG_PANEL)
        checks_frame.pack(fill="x", padx=10, pady=8)

        self._add_style_check(checks_frame, "Bold", self.bold_var)
        self._add_style_check(checks_frame, "Italic", self.italic_var)
        self._add_style_check(checks_frame, "Underline", self.underline_var)

        # --- LOWER SECTION: Live Preview ---
        preview_container = tk.Frame(main_frame, bg=COLOR_BG_PANEL, bd=1, relief="solid")
        preview_container.pack(fill="x", pady=(10, 0))

        tk.Label(
            preview_container,
            text="SAMPLE PREVIEW",
            bg=COLOR_BG_PANEL,
            fg="#88889a",
            font=(FONT_UI_FAMILY, 8, "bold"),
            anchor="w",
            padx=8,
            pady=4
        ).pack(fill="x")

        preview_card = tk.Frame(preview_container, bg=COLOR_CANVAS_PAPER, height=75)
        preview_card.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        preview_card.pack_propagate(False)

        self.preview_label = tk.Label(
            preview_card,
            text=self.PREVIEW_TEXT,
            bg=COLOR_CANVAS_PAPER,
            fg="#1a1a1a",
            anchor="center"
        )
        self.preview_label.pack(fill="both", expand=True)

        # --- BOTTOM ACTION BAR ---
        bottom_bar = tk.Frame(self, bg=COLOR_BG_DARK, height=48)
        bottom_bar.pack(fill="x", padx=12, pady=10)

        self.summary_label = tk.Label(
            bottom_bar,
            text="",
            bg=COLOR_BG_DARK,
            fg=COLOR_TEXT_MUTED,
            font=(FONT_UI_FAMILY, 8)
        )
        self.summary_label.pack(side="left")

        self.ok_btn = tk.Button(
            bottom_bar,
            text="Select Font",
            bg=COLOR_ACCENT,
            fg="#ffffff",
            activebackground="#2670e8",
            activeforeground="#ffffff",
            relief="flat",
            font=(FONT_UI_FAMILY, 9, "bold"),
            padx=16,
            pady=6,
            cursor="hand2",
            command=self._on_ok_clicked
        )
        self.ok_btn.pack(side="right", padx=(6, 0))

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

    def _add_style_check(self, parent, text, var):
        chk = tk.Checkbutton(
            parent,
            text=text,
            variable=var,
            bg=COLOR_BG_PANEL,
            fg=COLOR_TEXT_MAIN,
            activebackground=COLOR_BG_PANEL,
            activeforeground=COLOR_TEXT_MAIN,
            selectcolor=COLOR_BG_DARK,
            font=(FONT_UI_FAMILY, 9),
            command=self._update_preview
        )
        chk.pack(anchor="w", pady=4)
        return chk

    def _populate_families(self, query: str = ""):
        self.family_listbox.delete(0, "end")
        query = query.strip().lower()
        self.filtered_families = [f for f in self.all_families if not query or query in f.lower()]
        for f in self.filtered_families:
            self.family_listbox.insert("end", f)

    def _filter_families(self):
        query = self.search_var.get()
        self._populate_families(query)
        # Select current family if present
        self._select_family(self.current_family)

    def _select_family(self, family_name: str):
        if not hasattr(self, "filtered_families"):
            return
        for idx, f in enumerate(self.filtered_families):
            if f.lower() == family_name.lower():
                self.family_listbox.selection_clear(0, "end")
                self.family_listbox.selection_set(idx)
                self.family_listbox.see(idx)
                self.current_family = f
                break

    def _on_family_selected(self, event):
        sel = self.family_listbox.curselection()
        if sel and sel[0] < len(self.filtered_families):
            self.current_family = self.filtered_families[sel[0]]
            self._update_preview()

    def _on_size_entry_changed(self):
        val = self.size_var.get().strip()
        if val.isdigit():
            sz = int(val)
            if 4 <= sz <= 144:
                self.current_size = sz
                self._update_preview()

    def _on_size_list_selected(self, event):
        sel = self.size_listbox.curselection()
        if sel and sel[0] < len(self.COMMON_SIZES):
            sz = self.COMMON_SIZES[sel[0]]
            self.current_size = sz
            self.size_var.set(str(sz))
            self._update_preview()

    def _build_style_string(self) -> str:
        styles = []
        if self.bold_var.get():
            styles.append("bold")
        if self.italic_var.get():
            styles.append("italic")
        if self.underline_var.get():
            styles.append("underline")
        return " ".join(styles) if styles else "normal"

    def _update_preview(self):
        style_str = self._build_style_string()
        weight = "bold" if self.bold_var.get() else "normal"
        slant = "italic" if self.italic_var.get() else "roman"
        underline = 1 if self.underline_var.get() else 0

        try:
            self.preview_font = tkfont.Font(
                self,
                family=self.current_family,
                size=self.current_size,
                weight=weight,
                slant=slant,
                underline=underline
            )
            self.preview_label.config(font=self.preview_font)
        except Exception:
            pass

        summary = f"{self.current_family}, {self.current_size}pt"
        if style_str != "normal":
            summary += f", {style_str.title()}"
        self.summary_label.config(text=f"Selected: {summary}")

    @property
    def font_tuple(self) -> Tuple[str, int, str]:
        return (self.current_family, self.current_size, self._build_style_string())

    @property
    def font_string(self) -> str:
        style = self._build_style_string()
        return f"{self.current_family} {self.current_size} {style}".strip()

    def destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        super().destroy()

    def _on_ok_clicked(self):
        self.result = self.font_tuple
        if self.on_save:
            self.on_save(self.result)
        self.destroy()

    def _on_cancel_clicked(self):
        self.result = None
        self.destroy()

