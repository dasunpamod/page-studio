"""
PageStudio - Widget Models and Schema Definitions
Defines supported widgets, default properties, dimensions, and geometry models.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import uuid

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
    # Basic Input
    "Button": WidgetTypeSpec(
        type_name="Button",
        display_name="ttk.Button",
        category="Basic Controls",
        default_width=110,
        default_height=32,
        default_text="Button",
        supported_events=["command", "<Button-1>", "<Double-Button-1>"],
        supported_props=["text", "state", "style"]
    ),
    "Entry": WidgetTypeSpec(
        type_name="Entry",
        display_name="ttk.Entry",
        category="Basic Controls",
        default_width=160,
        default_height=28,
        default_text="",
        supported_events=["<Return>", "<FocusIn>", "<FocusOut>", "<KeyRelease>"],
        supported_props=["text", "variable", "show", "state"]
    ),
    "Label": WidgetTypeSpec(
        type_name="Label",
        display_name="ttk.Label",
        category="Basic Controls",
        default_width=120,
        default_height=26,
        default_text="Label Text",
        supported_events=["<Button-1>"],
        supported_props=["text", "anchor", "font", "justify"]
    ),
    "Checkbutton": WidgetTypeSpec(
        type_name="Checkbutton",
        display_name="ttk.Checkbutton",
        category="Basic Controls",
        default_width=130,
        default_height=28,
        default_text="Check Option",
        supported_events=["command"],
        supported_props=["text", "variable", "state"]
    ),
    "Radiobutton": WidgetTypeSpec(
        type_name="Radiobutton",
        display_name="ttk.Radiobutton",
        category="Basic Controls",
        default_width=130,
        default_height=28,
        default_text="Radio Option",
        supported_events=["command"],
        supported_props=["text", "variable", "value", "state"]
    ),
    "Combobox": WidgetTypeSpec(
        type_name="Combobox",
        display_name="ttk.Combobox",
        category="Data & Choice",
        default_width=160,
        default_height=28,
        default_text="",
        supported_events=["<<ComboboxSelected>>", "<Return>"],
        supported_props=["values", "variable", "state"]
    ),
    "Listbox": WidgetTypeSpec(
        type_name="Listbox",
        display_name="tk.Listbox",
        category="Data & Choice",
        default_width=160,
        default_height=120,
        default_text="",
        supported_events=["<<ListboxSelect>>", "<Double-Button-1>"],
        supported_props=["selectmode", "exportselection"]
    ),
    "Text": WidgetTypeSpec(
        type_name="Text",
        display_name="tk.Text",
        category="Data & Choice",
        default_width=240,
        default_height=140,
        default_text="",
        supported_events=["<KeyRelease>", "<FocusIn>", "<FocusOut>"],
        supported_props=["wrap", "state"]
    ),
    "Progressbar": WidgetTypeSpec(
        type_name="Progressbar",
        display_name="ttk.Progressbar",
        category="Indicators",
        default_width=180,
        default_height=22,
        default_text="",
        supported_events=[],
        supported_props=["mode", "maximum", "value"]
    ),
    "Scale": WidgetTypeSpec(
        type_name="Scale",
        display_name="ttk.Scale",
        category="Indicators",
        default_width=180,
        default_height=28,
        default_text="",
        supported_events=["command"],
        supported_props=["from_", "to", "orient", "variable"]
    ),
    "Separator": WidgetTypeSpec(
        type_name="Separator",
        display_name="ttk.Separator",
        category="Containers & Layout",
        default_width=200,
        default_height=10,
        default_text="",
        supported_events=[],
        supported_props=["orient"]
    ),
    "Frame": WidgetTypeSpec(
        type_name="Frame",
        display_name="ttk.Frame",
        category="Containers & Layout",
        default_width=240,
        default_height=160,
        default_text="",
        is_container=True,
        supported_events=["<Button-1>"],
        supported_props=["relief", "borderwidth"]
    ),
    "LabelFrame": WidgetTypeSpec(
        type_name="LabelFrame",
        display_name="ttk.LabelFrame",
        category="Containers & Layout",
        default_width=240,
        default_height=160,
        default_text="Group Box",
        is_container=True,
        supported_events=[],
        supported_props=["text", "relief"]
    ),
    "Canvas": WidgetTypeSpec(
        type_name="Canvas",
        display_name="tk.Canvas",
        category="Containers & Layout",
        default_width=200,
        default_height=150,
        default_text="",
        supported_events=["<Button-1>", "<B1-Motion>"],
        supported_props=["bg", "relief", "borderwidth"]
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

    @classmethod
    def create(cls, widget_type: str, x: int, y: int, name_hint: Optional[str] = None) -> "WidgetInstance":
        spec = WIDGET_CATALOG.get(widget_type)
        if not spec:
            raise ValueError(f"Unknown widget type: {widget_type}")
        
        uid = str(uuid.uuid4())[:8]
        type_prefix = widget_type.lower()
        name = name_hint or f"{type_prefix}_{uid}"
        
        props: Dict[str, Any] = {}
        if spec.default_text:
            props["text"] = spec.default_text
        
        if widget_type == "Combobox":
            props["values"] = ["Option 1", "Option 2", "Option 3"]
        elif widget_type == "Progressbar":
            props["mode"] = "determinate"
            props["maximum"] = 100
            props["value"] = 50
        elif widget_type == "Scale":
            props["from_"] = 0
            props["to"] = 100
            props["orient"] = "horizontal"
        elif widget_type == "Separator":
            props["orient"] = "horizontal"
        elif widget_type in ("Checkbutton", "Radiobutton"):
            props["variable"] = f"{name}_var"
            if widget_type == "Radiobutton":
                props["value"] = "1"
        elif widget_type == "Entry":
            props["variable"] = f"{name}_var"
            
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
            parent_id=None
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
            "properties": dict(self.properties),
            "events": dict(self.events),
            "parent_id": self.parent_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WidgetInstance":
        return cls(
            id=data["id"],
            widget_type=data["widget_type"],
            name=data["name"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            properties=data.get("properties", {}),
            events=data.get("events", {}),
            parent_id=data.get("parent_id")
        )
