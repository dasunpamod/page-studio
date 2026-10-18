"""
PageStudio - Project Serializer
Encodes and decodes PageStudio projects to/from human-readable JSON files (.pgproj).
"""

import json
from typing import Dict, Any, Optional
from .state import ProjectState
from .models import WidgetInstance

class ProjectSerializer:
    """Handles serialization and file I/O for PageStudio project files."""
    VERSION = "1.0.0"

    @classmethod
    def to_dict(cls, state: ProjectState) -> Dict[str, Any]:
        return {
            "format": "pagestudio",
            "version": cls.VERSION,
            "window": {
                "title": state.title,
                "width": state.width,
                "height": state.height,
                "resizable_x": state.resizable_x,
                "resizable_y": state.resizable_y,
            },
            "canvas": {
                "grid_size": state.grid_size,
                "snap_to_grid": state.snap_to_grid,
            },
            "widgets": [
                state.widgets[wid].to_dict()
                for wid in state.widget_order
                if wid in state.widgets
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectState:
        win = data.get("window", {})
        state = ProjectState(
            title=win.get("title", "My Application"),
            width=win.get("width", 600),
            height=win.get("height", 400)
        )
        state.resizable_x = win.get("resizable_x", True)
        state.resizable_y = win.get("resizable_y", True)
        
        cv = data.get("canvas", {})
        state.grid_size = cv.get("grid_size", 10)
        state.snap_to_grid = cv.get("snap_to_grid", True)
        
        state.widgets.clear()
        state.widget_order.clear()
        for wdata in data.get("widgets", []):
            widget = WidgetInstance.from_dict(wdata)
            state.widgets[widget.id] = widget
            state.widget_order.append(widget.id)
            
        state.selected_ids.clear()
        state.push_state()
        return state

    @classmethod
    def save_to_file(cls, state: ProjectState, file_path: str) -> None:
        data = cls.to_dict(state)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str) -> ProjectState:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
