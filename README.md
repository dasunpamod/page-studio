# PageStudio 🎨
> **Modern, Cross-Platform Visual GUI Generator for Python Tkinter**  
> Native macOS, Windows, and Linux support with **Zero Third-Party Dependencies Required**.

---

## Overview

**PageStudio** is a modern reincarnation and clean-slate rebuild of **PAGE** (Python Automatic GUI Generator). It allows Python developers to design rich desktop user interfaces visually and generate clean, human-readable Python Tkinter code.

### Why Legacy PAGE Failed on Mac
Legacy PAGE was built on top of late-1990s Visual Tcl (`vTcl`) and spawned multiple floating X11/Win32 toolbars. On macOS, Apple's Aqua Tk window manager broke down or crashed when handling those unmanaged floating windows.

### How PageStudio Solves It
* **100% Native Single-Window Workspace**: Built as a single cohesive IDE window using standard Python `tkinter` and `ttk`. It runs seamlessly on macOS (Apple Silicon M1/M2/M3/M4 & Intel), Windows, and Linux.
* **Zero External Dependencies**: Uses only the Python standard library. No `pip install` required!
* **PAGE's Signature 2-File Architecture**:
  * `<name>.py`: The GUI presentation module defining window layout and exact widget placements using Tkinter's `place` geometry manager (supporting both absolute and relative coordinates).
  * `<name>_support.py`: The application logic module providing event handler skeletons and global Tk variables (`StringVar`, `BooleanVar`, `DoubleVar`). Custom logic written in this file is preserved when re-saving from the designer!
* **Git-Friendly Project Files**: Projects are saved as clean, human-readable `.pgproj` JSON files instead of arcane Tcl state files.

---

## Complete Catalog of 42 Widgets

PageStudio includes full visual mockups, property inspection, and code generation for **42 distinct widget types** across four functional categories:

### 1. Standard Tk Widgets (19)
| Widget Type | Display Name | Category | Description |
|---|---|---|---|
| `Button` | `tk.Button` | Standard Tk | Push button control with click callback |
| `Entry` | `tk.Entry` | Standard Tk | Single-line editable text input |
| `Label` | `tk.Label` | Standard Tk | Text and image display label |
| `Checkbutton` | `tk.Checkbutton` | Standard Tk | Binary checkbox toggle with variable binding |
| `Radiobutton` | `tk.Radiobutton` | Standard Tk | Mutually-exclusive option selector |
| `Combobox` | `ttk.Combobox` | Standard Tk | Dropdown selection and text input |
| `Listbox` | `tk.Listbox` | Standard Tk | Scrollable list of selectable text items |
| `Text` | `tk.Text` | Standard Tk | Multi-line rich text editor |
| `Progressbar` | `ttk.Progressbar` | Standard Tk | Progress meter indicator |
| `Scale` | `tk.Scale` | Standard Tk | Numeric slider input |
| `Separator` | `ttk.Separator` | Standard Tk | Horizontal or vertical divider line |
| `Frame` | `tk.Frame` | Standard Tk | General-purpose rectangular container |
| `LabelFrame` | `tk.LabelFrame` | Standard Tk | Bordered container with header title label |
| `Canvas` | `tk.Canvas` | Standard Tk | Vector graphics and structured drawing surface |
| `Spinbox` | `tk.Spinbox` | Standard Tk | Numeric entry with increment/decrement steppers |
| `Message` | `tk.Message` | Standard Tk | Multi-line automatic-wrapping text display |
| `Menubutton` | `tk.Menubutton` | Standard Tk | Button that triggers an associated menu popup |
| `Popupmenu` | `tk.Menu` | Standard Tk | Contextual popup menu triggered by events |
| `Toplevel` | `tk.Toplevel` | Standard Tk | Secondary modal/non-modal top-level window |

### 2. Themed ttk Widgets (16)
| Widget Type | Display Name | Category | Description |
|---|---|---|---|
| `TButton` | `ttk.Button` | Themed ttk | Native themed pushbutton |
| `TCheckbutton` | `ttk.Checkbutton` | Themed ttk | Native themed binary checkbutton |
| `TCombobox` | `ttk.Combobox` | Themed ttk | Native themed dropdown selection |
| `TEntry` | `ttk.Entry` | Themed ttk | Native themed single-line entry |
| `TFrame` | `ttk.Frame` | Themed ttk | Native themed layout frame container |
| `TLabel` | `ttk.Label` | Themed ttk | Native themed text/image label |
| `TLabelframe` | `ttk.Labelframe` | Themed ttk | Native themed bordered label container |
| `TMenubutton` | `ttk.Menubutton` | Themed ttk | Native themed menu trigger button |
| `TNotebook` | `ttk.Notebook` | Themed ttk | Tabbed multi-page container control |
| `TPanedwindow` | `ttk.Panedwindow` | Themed ttk | Container with movable pane sashes |
| `TProgressbar` | `ttk.Progressbar` | Themed ttk | Native themed progress indicator |
| `TRadiobutton` | `ttk.Radiobutton` | Themed ttk | Native themed radio option |
| `TScale` | `ttk.Scale` | Themed ttk | Native themed slider control |
| `TSeparator` | `ttk.Separator` | Themed ttk | Native themed divider line |
| `TSizegrip` | `ttk.Sizegrip` | Themed ttk | Window corner resizing grip handle |
| `TSpinbox` | `ttk.Spinbox` | Themed ttk | Native themed spinbox stepper |

### 3. Scrolled Compound Widgets (5)
| Widget Type | Display Name | Category | Description |
|---|---|---|---|
| `Scrolledtext` | `ScrolledText` | Scrolled Widgets | Multi-line text with built-in scrollbar |
| `Scrolledlistbox` | `ScrolledListbox` | Scrolled Widgets | Listbox combined with vertical scrollbar |
| `Scrolledtreeview` | `ScrolledTreeview` | Scrolled Widgets | Hierarchical tree combined with scrollbars |
| `Scrolledentry` | `ScrolledEntry` | Scrolled Widgets | Entry with horizontal scroll navigation |
| `Scrolledwindow` | `ScrolledWindow` | Scrolled Widgets | Scrollable viewport container for arbitrary widgets |

### 4. Advanced & Custom Widgets (2)
| Widget Type | Display Name | Category | Description |
|---|---|---|---|
| `Treeview` | `ttk.Treeview` | Advanced | Multi-column tabular and hierarchical data view |
| `Custom` | `Custom Widget` | Advanced | User-defined custom Tkinter widget extension |

---

## Container Nesting & Hierarchy Management

PageStudio provides first-class support for nested GUI container architectures:
* **Recognized Container Types**: `Frame`, `LabelFrame`, `TFrame`, `TLabelframe`, `TNotebook`, `TPanedwindow`, `Canvas`, `Scrolledwindow`, and `Toplevel`.
* **Cumulative Coordinate Translation**: Child widget locations are visually calculated and rendered relative to all ancestor containers on the scrollable canvas.
* **Synchronized Container Dragging**: Moving a parent container moves all nested child widgets automatically while preserving their relative offsets.
* **Container Boundary Guards**: Dragging and keyboard micro-nudging prevent widgets from moving out of their parent container's boundaries.
* **Interactive Notebook Tab Switching**: Clicking notebook tabs on the canvas or in the Widget Tree filters visible widgets to display only those belonging to the active tab page.
* **Recursive Deletion**: Deleting a container safely and recursively removes its entire subtree, complete with multi-level Undo/Redo and clipboard support.
* **Relative vs Absolute Geometry**: Seamlessly toggle between absolute pixel layout (`place(x=..., y=..., width=..., height=...)`) and responsive relative coordinates (`place(relx=..., rely=..., relwidth=..., relheight=...)`).

---

## Dedicated Visual Editors

PageStudio integrates four dedicated modal visual editors for complex widget configuration:

1. **Menu Editor (`MenuEditorDialog`)**:
   * Design Application Menubars, Cascades, Separators, Checkbuttons, Radiobuttons, and Context/Popup Menus.
   * Configure menu commands, keyboard accelerators, and variable bindings in a visual hierarchical tree.
2. **Notebook Tab Editor (`NotebookTabEditorDialog`)**:
   * Add, remove, reorder, and configure tabs for `ttk.Notebook` widgets.
   * Configure tab titles, icons, and tab states (`normal`, `hidden`, `disabled`).
3. **Treeview Column Editor (`TreeviewColumnEditorDialog`)**:
   * Visually configure multi-column data grids for `ttk.Treeview`.
   * Set column IDs, header titles, column widths, stretch properties, and alignments (`w`, `center`, `e`).
4. **Font Chooser (`FontChooserDialog`)**:
   * Interactive typography picker supporting font family selection, font size scale (8pt to 72pt), and styles (`bold`, `italic`, `underline`, `overstrike`).
   * Includes real-time live preview text rendering.

---

## Core IDE Features

* **Drag-and-Drop WYSIWYG Canvas**:
  * 8-point interactive resize handles (NW, N, NE, E, SE, S, SW, W).
  * Snap-to-grid with customizable grid size (1px to 50px, default: 10px).
  * Smooth 2D canvas scrolling with horizontal/vertical scrollbars and cross-platform mouse wheel support.
  * Real-time coordinate badges, lock indicators, and live color previews.
* **Real-Time Property Inspector**:
  * 6 collapsible sections: **Identification**, **Geometry**, **Appearance**, **Text & Typography**, **Behavior & Bindings**, and **Widget-Specific Editors**.
  * Instant property updates with automatic canvas re-rendering.
* **Live Code Preview & Test Runner**:
  * Syntax-highlighted live preview of generated GUI code and Support code.
  * **`▶ Run / Test GUI`** button launches a live interactive sandbox of your application in an isolated subprocess.
* **Native Keyboard Shortcuts & Focus Guards**:
  * **File Operations**: `Ctrl+N` / `⌘N` (New), `Ctrl+O` / `⌘O` (Open), `Ctrl+S` / `⌘S` (Save), `Ctrl+E` / `⌘E` (Export)
  * **Edit Operations**: `Ctrl+Z` / `⌘Z` (Undo), `Ctrl+Y` / `⌘Y` (Redo), `Ctrl+C` / `⌘C` (Copy), `Ctrl+X` / `⌘X` (Cut), `Ctrl+V` / `⌘V` (Paste), `Ctrl+D` / `⌘D` (Duplicate), `Delete` / `Backspace` (Delete)
  * **Execution**: `Ctrl+R` / `⌘R` (Test Run)
  * **Canvas Nudging**: Arrow keys (1px micro-nudge), `Shift+Arrow` (10px grid jump)
  * **Focus Guards**: Text entry fields (`Entry`, `Text`, `Spinbox`) automatically retain control of arrow keys, backspace, and delete when typing, preventing accidental canvas deletion or widget movement.

---

## Quick Start

### 1. Requirements
* **Python**: Version 3.8+ (tested and verified up to Python 3.14+)
* **Tkinter**: Bundled by default with official Python installers on macOS and Windows. On Linux:
  ```bash
  # Debian / Ubuntu / Mint
  sudo apt-get install python3-tk

  # Fedora / RHEL
  sudo dnf install python3-tkinter

  # Arch Linux
  sudo pacman -S tk
  ```
* **Dependencies**: None! 100% standard library.

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
│   ├── __init__.py             # Package exports (PageStudioApp, models, state)
│   ├── core/
│   │   ├── models.py           # Widget specifications, schemas & 42-widget catalog
│   │   ├── state.py            # Project state, hierarchy & Undo/Redo command stack
│   │   ├── generator.py        # 2-file Python code generator (GUI + Support)
│   │   └── serializer.py       # JSON .pgproj serialization
│   ├── ui/
│   │   ├── app_window.py       # Main unified IDE window
│   │   ├── canvas.py           # WYSIWYG design surface with 8 handles & container math
│   │   ├── palette.py          # Categorized widget palette with instant search filter
│   │   ├── inspector.py        # 6-section collapsible property & callback inspector
│   │   ├── preview.py          # Live code preview & sandbox runner
│   │   ├── theme.py            # Modern color palette & ttk themes
│   │   ├── widget_tree.py      # Hierarchical widget treeview panel
│   │   ├── menu_editor.py      # Modal visual menu editor
│   │   ├── notebook_editor.py  # Modal visual notebook tab editor
│   │   ├── treeview_editor.py  # Modal visual treeview column editor
│   │   └── font_chooser.py     # Modal visual typography chooser
│   └── utils/
│       └── helpers.py          # Cross-platform normalization & shortcut bindings
├── examples/
│   └── generated_login/        # Example generated application
└── tests/                      # Automated test suite (124+ unit tests)
```

---

## Running Automated Tests

Run the full automated test suite using Python's standard `unittest`:

```bash
python -m unittest discover tests -v
```

---

## License

PageStudio is open source under the MIT License.
