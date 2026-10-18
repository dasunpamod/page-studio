# PageStudio 🎨
> **Modern, Cross-Platform Visual GUI Generator for Python Tkinter**  
> Native macOS, Windows, and Linux support with **Zero Third-Party Dependencies Required**.

---

## Overview

**PageStudio** is a modern reincarnation and clean-slate rebuild of **PAGE** (Python Automatic GUI Generator). 

### Why Legacy PAGE Failed on Mac
Legacy PAGE was built on top of late-1990s Visual Tcl (`vTcl`) and spawned multiple floating X11/Win32 toolbars. On macOS, Apple's Aqua Tk window manager broke down or crashed when handling those unmanaged floating windows.

### How PageStudio Solves It
* **100% Native on macOS, Windows, and Linux**: Built as a single cohesive IDE window using standard Python `tkinter` and `ttk`. It runs seamlessly on macOS (Apple Silicon M1/M2/M3/M4 & Intel), Windows, and Linux.
* **Zero External Dependencies**: Uses only the Python standard library. No `pip install` required!
* **PAGE's Signature 2-File Architecture**:
  * `<name>.py`: The GUI presentation module defining window layout and exact widget placements using Tkinter's `place` geometry manager.
  * `<name>_support.py`: The application logic module providing event handler skeletons and global Tk variables (`StringVar`, `BooleanVar`, `DoubleVar`). Custom logic written in this file is preserved when re-saving from the designer!
* **Git-Friendly Project Files**: Projects are saved as clean, human-readable `.pgproj` JSON files instead of arcane Tcl state files.

---

## Features

* **Drag-and-Drop WYSIWYG Canvas**:
  * 8-point interactive resize handles (NW, N, NE, E, SE, S, SW, W).
  * Snap-to-grid with customizable grid size (default: 10px).
  * Keyboard arrow micro-nudging (1px regular, 10px with Shift).
  * Real-time coordinate badges (X, Y, Width, Height).
* **Comprehensive Widget Catalog**:
  * **Basic Controls**: `ttk.Button`, `ttk.Entry`, `ttk.Label`, `ttk.Checkbutton`, `ttk.Radiobutton`
  * **Data & Choice**: `ttk.Combobox`, `tk.Listbox`, `tk.Text`
  * **Indicators**: `ttk.Progressbar`, `ttk.Scale` (Slider)
  * **Containers & Layout**: `ttk.Separator`, `ttk.Frame`, `ttk.LabelFrame`, `tk.Canvas`
* **Real-Time Property Inspector**:
  * Edit widget names, geometry coordinates, display text, default values, and variable names.
  * Register event callback functions (e.g. `on_login_click`, `<Return>`, `<Double-Button-1>`).
* **Live Code Preview & Test Runner**:
  * Built-in syntax-highlighted code viewer updates in real time as you design.
  * **`▶ Run / Test GUI`** button launches a live interactive sandbox of your application with a single click.
* **Native Keyboard Shortcuts**:
  * macOS: `⌘N` (New), `⌘O` (Open), `⌘S` (Save), `⌘Z` (Undo), `⌘Y` (Redo), `⌘D` (Duplicate), `⌘R` (Test Run), `⌘E` (Export)
  * Windows / Linux: `Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `Ctrl+Z`, `Ctrl+Y`, `Ctrl+D`, `Ctrl+R`, `Ctrl+E`

---

## Quick Start

### 1. Requirements
- Python 3.8+ (tested and verified up to Python 3.14+)
- Standard Tkinter (bundled by default with official Python installers on macOS and Windows)

### 2. Launching PageStudio
```bash
cd page-studio
python main.py
```

---

## Project Structure

```
page-studio/
├── main.py                     # Application entry point
├── pagestudio/
│   ├── core/
│   │   ├── models.py           # Widget specifications and catalog
│   │   ├── state.py            # Project state & Undo/Redo command stack
│   │   ├── generator.py        # 2-file Python code generator
│   │   └── serializer.py       # JSON .pgproj serialization
│   ├── ui/
│   │   ├── app_window.py       # Main unified IDE window
│   │   ├── canvas.py           # WYSIWYG design surface with 8 handles
│   │   ├── palette.py          # Categorized widget palette
│   │   ├── inspector.py        # Property & callback inspector
│   │   ├── preview.py          # Live code preview & sandbox runner
│   │   └── theme.py            # Modern color palette & ttk themes
│   └── utils/
│       └── helpers.py          # macOS vs Windows/Linux normalization
├── examples/
│   └── login_demo.pgproj       # Sample project file
└── tests/                      # Automated test suite
```

---

## Running Automated Tests

```bash
python -m unittest discover tests
```

---

## License

PageStudio is open source under the MIT License.
