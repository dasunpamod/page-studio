"""
PageStudio - Project Serializer
Encodes and decodes PageStudio projects to/from human-readable JSON files (.pgproj).
"""

import json
import os
from typing import Dict, Any, Optional
from .state import ProjectState
from .models import WidgetInstance, MenuBarSpec

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
                "is_relative_mode": state.is_relative_mode,
            },
            "menus": {k: v.to_dict() for k, v in state.menus.items()},
            "popup_menus": {k: v.to_dict() for k, v in state.popup_menus.items()},
            "widgets": [
                state.widgets[wid].to_dict()
                for wid in state.widget_order
                if wid in state.widgets
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectState:
        if not isinstance(data, dict):
            raise ValueError("Invalid project file content: root must be a JSON object.")
        if data.get("format") and data.get("format") != "pagestudio":
            raise ValueError(f"Invalid file format: {data.get('format')}")

        win = data.get("window") or {}
        state = ProjectState(
            title=win.get("title", "My Application"),
            width=win.get("width", 600),
            height=win.get("height", 400)
        )
        state.resizable_x = win.get("resizable_x", True)
        state.resizable_y = win.get("resizable_y", True)
        
        cv = data.get("canvas") or {}
        state.grid_size = cv.get("grid_size", 10)
        state.snap_to_grid = cv.get("snap_to_grid", True)
        state.is_relative_mode = cv.get("is_relative_mode", False)
        
        state.menus = {k: MenuBarSpec.from_dict(v) for k, v in (data.get("menus") or {}).items()}
        state.popup_menus = {k: MenuBarSpec.from_dict(v) for k, v in (data.get("popup_menus") or {}).items()}

        state.widgets.clear()
        state.widget_order.clear()
        for wdata in (data.get("widgets") or []):
            widget = WidgetInstance.from_dict(wdata)
            state.widgets[widget.id] = widget
            state.widget_order.append(widget.id)
            
        # Clean up any dangling or circular parent_id references in loaded data
        for wid, widget in list(state.widgets.items()):
            if widget.parent_id and widget.parent_id not in state.widgets:
                widget.parent_id = None
            elif widget.parent_id == wid:
                widget.parent_id = None
            elif widget.parent_id:
                # Walk ancestors to detect and break circular references
                curr = widget.parent_id
                visited = {wid}
                while curr and curr in state.widgets:
                    if curr in visited:
                        widget.parent_id = None
                        break
                    visited.add(curr)
                    curr = state.widgets[curr].parent_id

        state._sync_z_orders()
        state.selected_ids.clear()
        # Initialize undo/redo history cleanly with loaded state
        state._undo_stack.clear()
        state._redo_stack.clear()
        state._record_snapshot()
        return state

    @classmethod
    def save_to_file(cls, state: ProjectState, file_path: str) -> None:
        data = cls.to_dict(state)
        dir_name = os.path.dirname(os.path.abspath(file_path))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_file(cls, file_path: str) -> ProjectState:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)
