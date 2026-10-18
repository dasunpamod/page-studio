"""
PageStudio - Project Serializer
Encodes and decodes PageStudio projects to/from human-readable JSON files (.pgproj).
"""

import json
import os
from typing import Dict, Any
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

        win = data.get("window") if isinstance(data.get("window"), dict) else {}
        title = str(win.get("title")) if win.get("title") is not None else "My Application"
        try:
            width = int(win.get("width")) if win.get("width") is not None else 600
        except (ValueError, TypeError):
            width = 600
        try:
            height = int(win.get("height")) if win.get("height") is not None else 400
        except (ValueError, TypeError):
            height = 400
        width = max(100, min(10000, width))
        height = max(100, min(10000, height))

        state = ProjectState(
            title=title,
            width=width,
            height=height
        )
        state.resizable_x = bool(win.get("resizable_x", True))
        state.resizable_y = bool(win.get("resizable_y", True))
        
        cv = data.get("canvas") if isinstance(data.get("canvas"), dict) else {}
        try:
            grid_size = int(cv.get("grid_size", 10)) if cv.get("grid_size") is not None else 10
        except (ValueError, TypeError):
            grid_size = 10
        state.grid_size = max(1, min(100, grid_size))
        state.snap_to_grid = bool(cv.get("snap_to_grid", True))
        state.is_relative_mode = bool(cv.get("is_relative_mode", False))
        
        menus_dict = data.get("menus") if isinstance(data.get("menus"), dict) else {}
        popup_dict = data.get("popup_menus") if isinstance(data.get("popup_menus"), dict) else {}
        state.menus = {k: MenuBarSpec.from_dict(v) for k, v in menus_dict.items() if isinstance(v, dict)}
        state.popup_menus = {k: MenuBarSpec.from_dict(v) for k, v in popup_dict.items() if isinstance(v, dict)}

        state.widgets.clear()
        state.widget_order.clear()
        for wdata in (data.get("widgets") or []):
            if not isinstance(wdata, dict):
                continue
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
            content = f.read().strip()
            if not content:
                raise ValueError("Project file is empty.")
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValueError(f"Corrupted or invalid JSON project file: {e}")
        return cls.from_dict(data)
