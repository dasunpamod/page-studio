"""
PageStudio - Widget Models and Schema Definitions
Defines supported widgets, menu models, default properties, dimensions, and geometry models.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import copy
import uuid

@dataclass
class MenuItemSpec:
    """Represents an item within a menu or submenu."""
    id: str
    item_type: str = "command"  # "command", "cascade", "checkbutton", "radiobutton", "separator"
    label: str = ""
    command: Optional[str] = None
    accelerator: Optional[str] = None
    variable: Optional[str] = None
    value: Optional[str] = None
    image: Optional[str] = None
    state: str = "normal"  # "normal", "active", "disabled"
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
            "image": self.image,
            "state": self.state,
            "underline": self.underline,
            "children": [c.to_dict() for c in self.children]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MenuItemSpec":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            item_type=data.get("item_type", "command"),
            label=data.get("label", ""),
            command=data.get("command"),
            accelerator=data.get("accelerator"),
            variable=data.get("variable"),
            value=data.get("value"),
            image=data.get("image"),
            state=data.get("state", "normal"),
            underline=data.get("underline", -1),
            children=[cls.from_dict(c) for c in (data.get("children") or [])]
        )

@dataclass
class MenuBarSpec:
    """Represents a top-level menubar or popup context menu."""
    id: str
    name: str = "main_menu"
    items: List[MenuItemSpec] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "items": [item.to_dict() for item in self.items]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MenuBarSpec":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "main_menu"),
            items=[MenuItemSpec.from_dict(item) for item in (data.get("items") or [])]
        )

@dataclass
class WidgetTypeSpec:
    type_name: str
    display_name: str
    category: str
    default_width: int
    default_height: int
    default_text: str = ""
    is_container: bool = False
    supported_events: List[str] = field(default_factory=lambda: ["command"])
    supported_props: List[str] = field(default_factory=lambda: ["text", "font", "fg", "bg", "state"])

# Catalog of supported widgets in PageStudio
WIDGET_CATALOG: Dict[str, WidgetTypeSpec] = {
    # -------------------------------------------------------------
    # Standard Tk Widgets
    # -------------------------------------------------------------
    "Button": WidgetTypeSpec(
        type_name="Button",
        display_name="tk.Button",
        category="Standard Tk",
        default_width=110,
        default_height=32,
        default_text="Button",
        supported_events=["command", "<Button-1>", "<Double-Button-1>"],
        supported_props=["text", "state", "style", "bg", "fg", "font"]
    ),
    "Entry": WidgetTypeSpec(
        type_name="Entry",
        display_name="tk.Entry",
        category="Standard Tk",
        default_width=160,
        default_height=26,
        default_text="",
        supported_events=["<Return>", "<FocusIn>", "<FocusOut>", "<KeyRelease>"],
        supported_props=["text", "variable", "show", "state", "font"]
    ),
    "Label": WidgetTypeSpec(
        type_name="Label",
        display_name="tk.Label",
        category="Standard Tk",
        default_width=120,
        default_height=26,
        default_text="Label Text",
        supported_events=["<Button-1>"],
        supported_props=["text", "anchor", "font", "justify", "fg", "bg"]
    ),
    "Checkbutton": WidgetTypeSpec(
        type_name="Checkbutton",
        display_name="tk.Checkbutton",
        category="Standard Tk",
        default_width=130,
        default_height=26,
        default_text="Check Option",
        supported_events=["command"],
        supported_props=["text", "variable", "state", "onvalue", "offvalue"]
    ),
    "Radiobutton": WidgetTypeSpec(
        type_name="Radiobutton",
        display_name="tk.Radiobutton",
        category="Standard Tk",
        default_width=130,
        default_height=26,
        default_text="Radio Option",
        supported_events=["command"],
        supported_props=["text", "variable", "value", "state"]
    ),
    "Combobox": WidgetTypeSpec(
        type_name="Combobox",
        display_name="ttk.Combobox",
        category="Standard Tk",
        default_width=160,
        default_height=26,
        default_text="",
        supported_events=["<<ComboboxSelected>>", "<Return>"],
        supported_props=["values", "variable", "state"]
    ),
    "Listbox": WidgetTypeSpec(
        type_name="Listbox",
        display_name="tk.Listbox",
        category="Standard Tk",
        default_width=160,
        default_height=120,
        default_text="",
        supported_events=["<<ListboxSelect>>", "<Double-Button-1>"],
        supported_props=["selectmode", "exportselection"]
    ),
    "Text": WidgetTypeSpec(
        type_name="Text",
        display_name="tk.Text",
        category="Standard Tk",
        default_width=240,
        default_height=140,
        default_text="",
        supported_events=["<KeyRelease>", "<FocusIn>", "<FocusOut>"],
        supported_props=["wrap", "state", "font"]
    ),
    "Progressbar": WidgetTypeSpec(
        type_name="Progressbar",
        display_name="ttk.Progressbar",
        category="Standard Tk",
        default_width=180,
        default_height=22,
        default_text="",
        supported_events=[],
        supported_props=["mode", "maximum", "value"]
    ),
    "Scale": WidgetTypeSpec(
        type_name="Scale",
        display_name="tk.Scale",
        category="Standard Tk",
        default_width=180,
        default_height=28,
        default_text="",
        supported_events=["command"],
        supported_props=["from_", "to", "orient", "variable"]
    ),
    "Separator": WidgetTypeSpec(
        type_name="Separator",
        display_name="ttk.Separator",
        category="Standard Tk",
        default_width=200,
        default_height=10,
        default_text="",
        supported_events=[],
        supported_props=["orient"]
    ),
    "Frame": WidgetTypeSpec(
        type_name="Frame",
        display_name="tk.Frame",
        category="Standard Tk",
        default_width=240,
        default_height=160,
        default_text="",
        is_container=True,
        supported_events=["<Button-1>"],
        supported_props=["relief", "borderwidth", "bg"]
    ),
    "LabelFrame": WidgetTypeSpec(
        type_name="LabelFrame",
        display_name="tk.LabelFrame",
        category="Standard Tk",
        default_width=240,
        default_height=160,
        default_text="Group Box",
        is_container=True,
        supported_events=[],
        supported_props=["text", "relief", "borderwidth"]
    ),
    "Canvas": WidgetTypeSpec(
        type_name="Canvas",
        display_name="tk.Canvas",
        category="Standard Tk",
        default_width=200,
        default_height=150,
        default_text="",
        is_container=True,
        supported_events=["<Button-1>", "<B1-Motion>"],
        supported_props=["bg", "relief", "borderwidth"]
    ),
    "Spinbox": WidgetTypeSpec(
        type_name="Spinbox",
        display_name="tk.Spinbox",
        category="Standard Tk",
        default_width=140,
        default_height=26,
        default_text="0",
        supported_events=["command", "<Return>"],
        supported_props=["from_", "to", "increment", "variable", "state"]
    ),
    "Message": WidgetTypeSpec(
        type_name="Message",
        display_name="tk.Message",
        category="Standard Tk",
        default_width=160,
        default_height=60,
        default_text="Message",
        supported_events=["<Button-1>"],
        supported_props=["text", "aspect", "justify", "font", "fg", "bg"]
    ),
    "Menubutton": WidgetTypeSpec(
        type_name="Menubutton",
        display_name="tk.Menubutton",
        category="Standard Tk",
        default_width=110,
        default_height=30,
        default_text="Menu",
        supported_events=[],
        supported_props=["text", "relief", "direction"]
    ),
    "Popupmenu": WidgetTypeSpec(
        type_name="Popupmenu",
        display_name="tk.Menu",
        category="Standard Tk",
        default_width=120,
        default_height=30,
        default_text="Popup",
        supported_events=[],
        supported_props=["tearoff"]
    ),
    "Toplevel": WidgetTypeSpec(
        type_name="Toplevel",
        display_name="tk.Toplevel",
        category="Standard Tk",
        default_width=320,
        default_height=220,
        default_text="Window",
        is_container=True,
        supported_events=[],
        supported_props=["title", "bg"]
    ),

    # -------------------------------------------------------------
    # Themed ttk Widgets
    # -------------------------------------------------------------
    "TButton": WidgetTypeSpec(
        type_name="TButton",
        display_name="ttk.Button",
        category="Themed ttk",
        default_width=110,
        default_height=32,
        default_text="TButton",
        supported_events=["command", "<Button-1>", "<Double-Button-1>"],
        supported_props=["text", "state", "style"]
    ),
    "TCheckbutton": WidgetTypeSpec(
        type_name="TCheckbutton",
        display_name="ttk.Checkbutton",
        category="Themed ttk",
        default_width=130,
        default_height=26,
        default_text="TCheck",
        supported_events=["command"],
        supported_props=["text", "variable", "state", "style"]
    ),
    "TCombobox": WidgetTypeSpec(
        type_name="TCombobox",
        display_name="ttk.Combobox",
        category="Themed ttk",
        default_width=160,
        default_height=26,
        default_text="",
        supported_events=["<<ComboboxSelected>>", "<Return>"],
        supported_props=["values", "variable", "state", "style"]
    ),
    "TEntry": WidgetTypeSpec(
        type_name="TEntry",
        display_name="ttk.Entry",
        category="Themed ttk",
        default_width=160,
        default_height=26,
        default_text="",
        supported_events=["<Return>", "<FocusIn>", "<FocusOut>", "<KeyRelease>"],
        supported_props=["text", "variable", "show", "state", "style"]
    ),
    "TFrame": WidgetTypeSpec(
        type_name="TFrame",
        display_name="ttk.Frame",
        category="Themed ttk",
        default_width=240,
        default_height=160,
        default_text="",
        is_container=True,
        supported_events=["<Button-1>"],
        supported_props=["relief", "style"]
    ),
    "TLabel": WidgetTypeSpec(
        type_name="TLabel",
        display_name="ttk.Label",
        category="Themed ttk",
        default_width=120,
        default_height=26,
        default_text="TLabel",
        supported_events=["<Button-1>"],
        supported_props=["text", "anchor", "font", "justify", "style"]
    ),
    "TLabelframe": WidgetTypeSpec(
        type_name="TLabelframe",
        display_name="ttk.Labelframe",
        category="Themed ttk",
        default_width=240,
        default_height=160,
        default_text="TLabelframe",
        is_container=True,
        supported_events=[],
        supported_props=["text", "relief", "style"]
    ),
    "TMenubutton": WidgetTypeSpec(
        type_name="TMenubutton",
        display_name="ttk.Menubutton",
        category="Themed ttk",
        default_width=110,
        default_height=30,
        default_text="TMenu",
        supported_events=[],
        supported_props=["text", "direction", "style"]
    ),
    "TNotebook": WidgetTypeSpec(
        type_name="TNotebook",
        display_name="ttk.Notebook",
        category="Themed ttk",
        default_width=300,
        default_height=200,
        default_text="",
        is_container=True,
        supported_events=["<<NotebookTabChanged>>"],
        supported_props=["style"]
    ),
    "TPanedwindow": WidgetTypeSpec(
        type_name="TPanedwindow",
        display_name="ttk.Panedwindow",
        category="Themed ttk",
        default_width=300,
        default_height=200,
        default_text="",
        is_container=True,
        supported_events=[],
        supported_props=["orient", "style"]
    ),
    "TProgressbar": WidgetTypeSpec(
        type_name="TProgressbar",
        display_name="ttk.Progressbar",
        category="Themed ttk",
        default_width=180,
        default_height=22,
        default_text="",
        supported_events=[],
        supported_props=["mode", "maximum", "value", "style"]
    ),
    "TRadiobutton": WidgetTypeSpec(
        type_name="TRadiobutton",
        display_name="ttk.Radiobutton",
        category="Themed ttk",
        default_width=130,
        default_height=26,
        default_text="TRadio",
        supported_events=["command"],
        supported_props=["text", "variable", "value", "state", "style"]
    ),
    "TScale": WidgetTypeSpec(
        type_name="TScale",
        display_name="ttk.Scale",
        category="Themed ttk",
        default_width=180,
        default_height=28,
        default_text="",
        supported_events=["command"],
        supported_props=["from_", "to", "orient", "variable", "style"]
    ),
    "TSeparator": WidgetTypeSpec(
        type_name="TSeparator",
        display_name="ttk.Separator",
        category="Themed ttk",
        default_width=200,
        default_height=10,
        default_text="",
        supported_events=[],
        supported_props=["orient", "style"]
    ),
    "TSizegrip": WidgetTypeSpec(
        type_name="TSizegrip",
        display_name="ttk.Sizegrip",
        category="Themed ttk",
        default_width=20,
        default_height=20,
        default_text="",
        supported_events=[],
        supported_props=["style"]
    ),
    "TSpinbox": WidgetTypeSpec(
        type_name="TSpinbox",
        display_name="ttk.Spinbox",
        category="Themed ttk",
        default_width=140,
        default_height=26,
        default_text="0",
        supported_events=["command", "<Return>"],
        supported_props=["from_", "to", "increment", "variable", "state", "style"]
    ),

    # -------------------------------------------------------------
    # Scrolled Widgets
    # -------------------------------------------------------------
    "Scrolledtext": WidgetTypeSpec(
        type_name="Scrolledtext",
        display_name="ScrolledText",
        category="Scrolled Widgets",
        default_width=240,
        default_height=140,
        default_text="",
        supported_events=["<KeyRelease>", "<FocusIn>", "<FocusOut>"],
        supported_props=["wrap", "state", "font"]
    ),
    "Scrolledlistbox": WidgetTypeSpec(
        type_name="Scrolledlistbox",
        display_name="ScrolledListbox",
        category="Scrolled Widgets",
        default_width=160,
        default_height=120,
        default_text="",
        supported_events=["<<ListboxSelect>>"],
        supported_props=["selectmode", "exportselection"]
    ),
    "Scrolledtreeview": WidgetTypeSpec(
        type_name="Scrolledtreeview",
        display_name="ScrolledTreeview",
        category="Scrolled Widgets",
        default_width=280,
        default_height=160,
        default_text="",
        supported_events=["<<TreeviewSelect>>", "<Double-Button-1>"],
        supported_props=["columns", "show", "selectmode"]
    ),
    "Scrolledentry": WidgetTypeSpec(
        type_name="Scrolledentry",
        display_name="ScrolledEntry",
        category="Scrolled Widgets",
        default_width=160,
        default_height=28,
        default_text="",
        supported_events=["<Return>", "<FocusIn>", "<FocusOut>"],
        supported_props=["text", "variable", "state"]
    ),
    "Scrolledwindow": WidgetTypeSpec(
        type_name="Scrolledwindow",
        display_name="ScrolledWindow",
        category="Scrolled Widgets",
        default_width=260,
        default_height=180,
        default_text="",
        is_container=True,
        supported_events=[],
        supported_props=["bg", "relief"]
    ),

    # -------------------------------------------------------------
    # Advanced
    # -------------------------------------------------------------
    "Treeview": WidgetTypeSpec(
        type_name="Treeview",
        display_name="ttk.Treeview",
        category="Advanced",
        default_width=260,
        default_height=150,
        default_text="",
        supported_events=["<<TreeviewSelect>>", "<Double-Button-1>"],
        supported_props=["columns", "show", "selectmode"]
    ),
    "Custom": WidgetTypeSpec(
        type_name="Custom",
        display_name="Custom Widget",
        category="Advanced",
        default_width=140,
        default_height=60,
        default_text="Custom Widget",
        supported_events=[],
        supported_props=["class_name", "module_name"]
    ),
}

@dataclass
class WidgetInstance:
    """Represents an instantiated widget placed on the design canvas."""
    id: str
    widget_type: str
    name: str
    x: int
    y: int
    width: int
    height: int
    properties: Dict[str, Any] = field(default_factory=dict)
    events: Dict[str, str] = field(default_factory=dict)
    parent_id: Optional[str] = None  # None indicates root canvas/toplevel
    rel_x: Optional[float] = None
    rel_y: Optional[float] = None
    rel_width: Optional[float] = None
    rel_height: Optional[float] = None
    is_relative: bool = False
    locked: bool = False
    z_order: int = 0
    container_tab_or_pane: Optional[str] = None

    @classmethod
    def create(cls, widget_type: str, x: int, y: int, name_hint: Optional[str] = None, parent_id: Optional[str] = None) -> "WidgetInstance":
        spec = WIDGET_CATALOG.get(widget_type)
        if not spec:
            raise ValueError(f"Unknown widget type: {widget_type}")
        
        uid = str(uuid.uuid4())[:8]
        type_prefix = widget_type.lower()
        name = name_hint or f"{type_prefix}_{uid}"
        
        props: Dict[str, Any] = {}
        if spec.default_text:
            props["text"] = spec.default_text
        
        if widget_type in ("Combobox", "TCombobox"):
            props["values"] = ["Option 1", "Option 2", "Option 3"]
        elif widget_type in ("Progressbar", "TProgressbar"):
            props["mode"] = "determinate"
            props["maximum"] = 100
            props["value"] = 50
        elif widget_type in ("Scale", "TScale"):
            props["from_"] = 0
            props["to"] = 100
            props["orient"] = "horizontal"
        elif widget_type in ("Separator", "TSeparator"):
            props["orient"] = "horizontal"
        elif widget_type in ("Checkbutton", "TCheckbutton", "Radiobutton", "TRadiobutton"):
            props["variable"] = f"{name}_var"
            if "radio" in widget_type.lower():
                props["value"] = "1"
        elif widget_type in ("Entry", "TEntry", "Spinbox", "TSpinbox", "Scrolledentry"):
            props["variable"] = f"{name}_var"
            if "spinbox" in widget_type.lower():
                props["from_"] = 0
                props["to"] = 100
        elif widget_type == "TNotebook":
            props["tabs"] = ["Tab 1", "Tab 2"]
        elif widget_type in ("Treeview", "Scrolledtreeview"):
            props["columns"] = ["col1", "col2"]
            
        events: Dict[str, str] = {}
        if "command" in spec.supported_events:
            events["command"] = f"on_{name}_click"

        return cls(
            id=uid,
            widget_type=widget_type,
            name=name,
            x=max(0, x),
            y=max(0, y),
            width=spec.default_width,
            height=spec.default_height,
            properties=props,
            events=events,
            parent_id=parent_id,
            rel_x=None,
            rel_y=None,
            rel_width=None,
            rel_height=None,
            is_relative=False,
            locked=False,
            z_order=0,
            container_tab_or_pane=None
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "widget_type": self.widget_type,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "properties": copy.deepcopy(self.properties),
            "events": copy.deepcopy(self.events),
            "parent_id": self.parent_id,
            "rel_x": self.rel_x,
            "rel_y": self.rel_y,
            "rel_width": self.rel_width,
            "rel_height": self.rel_height,
            "is_relative": self.is_relative,
            "locked": self.locked,
            "z_order": self.z_order,
            "container_tab_or_pane": self.container_tab_or_pane,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WidgetInstance":
        return cls(
            id=data["id"],
            widget_type=data["widget_type"],
            name=data["name"],
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 100),
            height=data.get("height", 30),
            properties=copy.deepcopy(data.get("properties") or {}),
            events=copy.deepcopy(data.get("events") or {}),
            parent_id=data.get("parent_id"),
            rel_x=data.get("rel_x"),
            rel_y=data.get("rel_y"),
            rel_width=data.get("rel_width"),
            rel_height=data.get("rel_height"),
            is_relative=data.get("is_relative", False),
            locked=data.get("locked", False),
            z_order=data.get("z_order", 0),
            container_tab_or_pane=data.get("container_tab_or_pane"),
        )
