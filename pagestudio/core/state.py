"""
PageStudio - Project State Management & Undo/Redo Engine
Maintains active canvas dimensions, widgets, selection, and change history.
"""

from typing import List, Dict, Optional, Any, Callable
import copy
from .models import WidgetInstance

class Command:
    """Base class for reversible undoable commands."""
    def execute(self) -> None:
        raise NotImplementedError
        
    def undo(self) -> None:
        raise NotImplementedError

class ProjectState:
    """Central store for a PageStudio design project."""
    def __init__(self, title: str = "My Application", width: int = 600, height: int = 400):
        self.title: str = title
        self.width: int = width
        self.height: int = height
        self.resizable_x: bool = True
        self.resizable_y: bool = True
        self.grid_size: int = 10
        self.snap_to_grid: bool = True
        
        # Mapping from widget ID to WidgetInstance
        self.widgets: Dict[str, WidgetInstance] = {}
        # Order of widget creation (Z-order)
        self.widget_order: List[str] = []
        
        # Selection
        self.selected_ids: List[str] = []
        
        # Undo / Redo history
        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []
        self._listeners: List[Callable[[], None]] = []
        
        # Save initial state snapshot
        self._record_snapshot()

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback for when state changes."""
        self._listeners.append(listener)

    def notify(self) -> None:
        """Notify all listeners that the project state has updated."""
        for listener in self._listeners:
            try:
                listener()
            except Exception as e:
                print(f"Error in state listener: {e}")

    def _create_snapshot(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "width": self.width,
            "height": self.height,
            "resizable_x": self.resizable_x,
            "resizable_y": self.resizable_y,
            "widgets": [w.to_dict() for w in [self.widgets[wid] for wid in self.widget_order if wid in self.widgets]],
            "selected_ids": list(self.selected_ids)
        }

    def _restore_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.title = snapshot.get("title", "My Application")
        self.width = snapshot.get("width", 600)
        self.height = snapshot.get("height", 400)
        self.resizable_x = snapshot.get("resizable_x", True)
        self.resizable_y = snapshot.get("resizable_y", True)
        
        self.widgets = {}
        self.widget_order = []
        for wdata in snapshot.get("widgets", []):
            widget = WidgetInstance.from_dict(wdata)
            self.widgets[widget.id] = widget
            self.widget_order.append(widget.id)
            
        self.selected_ids = [sid for sid in snapshot.get("selected_ids", []) if sid in self.widgets]
        self.notify()

    def _record_snapshot(self) -> None:
        snapshot = self._create_snapshot()
        self._undo_stack.append(snapshot)
        # Limit undo history to 50 steps
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def push_state(self) -> None:
        """Explicitly checkpoint current state for undo."""
        self._record_snapshot()
        self.notify()

    def undo(self) -> bool:
        if len(self._undo_stack) <= 1:
            return False
        current = self._undo_stack.pop()
        self._redo_stack.append(current)
        prev = self._undo_stack[-1]
        self._restore_snapshot(prev)
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        next_state = self._redo_stack.pop()
        self._undo_stack.append(next_state)
        self._restore_snapshot(next_state)
        return True

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 1

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    # Widget operations
    def add_widget(self, widget: WidgetInstance) -> None:
        # Snap coordinates if configured
        if self.snap_to_grid and self.grid_size > 1:
            widget.x = (widget.x // self.grid_size) * self.grid_size
            widget.y = (widget.y // self.grid_size) * self.grid_size
            
        self.widgets[widget.id] = widget
        self.widget_order.append(widget.id)
        self.selected_ids = [widget.id]
        self.push_state()

    def remove_widget(self, widget_id: str) -> None:
        if widget_id in self.widgets:
            del self.widgets[widget_id]
            if widget_id in self.widget_order:
                self.widget_order.remove(widget_id)
            if widget_id in self.selected_ids:
                self.selected_ids.remove(widget_id)
            self.push_state()

    def remove_selected(self) -> None:
        if not self.selected_ids:
            return
        for wid in list(self.selected_ids):
            if wid in self.widgets:
                del self.widgets[wid]
            if wid in self.widget_order:
                self.widget_order.remove(wid)
        self.selected_ids.clear()
        self.push_state()

    def select_widget(self, widget_id: Optional[str], additive: bool = False) -> None:
        if widget_id is None:
            self.selected_ids.clear()
        elif additive:
            if widget_id in self.selected_ids:
                self.selected_ids.remove(widget_id)
            else:
                self.selected_ids.append(widget_id)
        else:
            self.selected_ids = [widget_id] if widget_id in self.widgets else []
        self.notify()

    def get_selected_widget(self) -> Optional[WidgetInstance]:
        if self.selected_ids and self.selected_ids[-1] in self.widgets:
            return self.widgets[self.selected_ids[-1]]
        return None

    def update_widget_geometry(self, widget_id: str, x: int, y: int, width: int, height: int, commit: bool = True, snap: bool = True) -> None:
        if widget_id not in self.widgets:
            return
        w = self.widgets[widget_id]
        if snap and self.snap_to_grid and self.grid_size > 1:
            x = (x // self.grid_size) * self.grid_size
            y = (y // self.grid_size) * self.grid_size
            width = max(self.grid_size, (width // self.grid_size) * self.grid_size)
            height = max(self.grid_size, (height // self.grid_size) * self.grid_size)
            
        w.x = max(0, x)
        w.y = max(0, y)
        w.width = max(10, width)
        w.height = max(10, height)
        
        if commit:
            self.push_state()
        else:
            self.notify()

    def duplicate_selected(self) -> None:
        if not self.selected_ids:
            return
        new_ids = []
        for wid in self.selected_ids:
            w = self.widgets.get(wid)
            if not w:
                continue
            new_w = copy.deepcopy(w)
            import uuid
            new_uid = str(uuid.uuid4())[:8]
            new_w.id = new_uid
            new_w.name = f"{w.widget_type.lower()}_{new_uid}"
            new_w.x += 20
            new_w.y += 20
            self.widgets[new_uid] = new_w
            self.widget_order.append(new_uid)
            new_ids.append(new_uid)
            
        self.selected_ids = new_ids
        self.push_state()
