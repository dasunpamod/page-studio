"""
PageStudio - Project State Management & Undo/Redo Engine
Maintains active canvas dimensions, widgets, menus, selection, clipboard, and change history.
"""

from typing import List, Dict, Optional, Any, Callable, Set, Tuple
import copy
import uuid
from .models import WidgetInstance, MenuBarSpec

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
        self.is_relative_mode: bool = False
        
        # Menus
        self.menus: Dict[str, MenuBarSpec] = {}
        self.popup_menus: Dict[str, MenuBarSpec] = {}
        
        # Clipboard
        self._clipboard: List[Dict[str, Any]] = []
        
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
            "grid_size": self.grid_size,
            "snap_to_grid": self.snap_to_grid,
            "is_relative_mode": self.is_relative_mode,
            "menus": {k: v.to_dict() for k, v in self.menus.items()},
            "popup_menus": {k: v.to_dict() for k, v in self.popup_menus.items()},
            "widgets": [w.to_dict() for w in [self.widgets[wid] for wid in self.widget_order if wid in self.widgets]],
            "selected_ids": list(self.selected_ids)
        }

    def _restore_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.title = snapshot.get("title", "My Application")
        self.width = snapshot.get("width", 600)
        self.height = snapshot.get("height", 400)
        self.resizable_x = snapshot.get("resizable_x", True)
        self.resizable_y = snapshot.get("resizable_y", True)
        self.grid_size = snapshot.get("grid_size", self.grid_size)
        self.snap_to_grid = snapshot.get("snap_to_grid", self.snap_to_grid)
        self.is_relative_mode = snapshot.get("is_relative_mode", False)
        
        self.menus = {k: MenuBarSpec.from_dict(v) for k, v in snapshot.get("menus", {}).items()}
        self.popup_menus = {k: MenuBarSpec.from_dict(v) for k, v in snapshot.get("popup_menus", {}).items()}
        
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

    # --------------------------------------------------------------------------
    # Widget & Hierarchy Operations
    # --------------------------------------------------------------------------
    def add_widget(self, widget: WidgetInstance, parent_id: Optional[str] = None) -> None:
        if parent_id is not None:
            widget.parent_id = parent_id
            
        # Snap coordinates if configured and not relative
        if self.snap_to_grid and self.grid_size > 1 and not widget.is_relative:
            widget.x = (widget.x // self.grid_size) * self.grid_size
            widget.y = (widget.y // self.grid_size) * self.grid_size
            
        self.widgets[widget.id] = widget
        if widget.id not in self.widget_order:
            self.widget_order.append(widget.id)
        self.selected_ids = [widget.id]
        if self.is_relative_mode:
            widget.is_relative = True
            self.calculate_relative_coordinates(widget.id)
        self.push_state()

    def get_children(self, parent_id: Optional[str]) -> List[WidgetInstance]:
        """Return direct children of the specified parent_id (or root canvas if None)."""
        return [
            self.widgets[wid] for wid in self.widget_order
            if wid in self.widgets and self.widgets[wid].parent_id == parent_id
        ]

    def get_all_descendants(self, parent_id: str) -> List[WidgetInstance]:
        """Return all descendants of the specified parent_id recursively."""
        descendants: List[WidgetInstance] = []
        direct_children = self.get_children(parent_id)
        for child in direct_children:
            descendants.append(child)
            descendants.extend(self.get_all_descendants(child.id))
        return descendants

    def remove_widget(self, widget_id: str) -> None:
        if widget_id not in self.widgets:
            return
        descendants = self.get_all_descendants(widget_id)
        all_to_remove = [widget_id] + [d.id for d in descendants]
        for wid in all_to_remove:
            if wid in self.widgets:
                del self.widgets[wid]
            if wid in self.widget_order:
                self.widget_order.remove(wid)
            if wid in self.selected_ids:
                self.selected_ids.remove(wid)
        self.push_state()

    def remove_selected(self) -> None:
        if not self.selected_ids:
            return
        all_to_remove: Set[str] = set()
        for wid in list(self.selected_ids):
            if wid in self.widgets:
                all_to_remove.add(wid)
                for desc in self.get_all_descendants(wid):
                    all_to_remove.add(desc.id)
        for wid in all_to_remove:
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
        if w.locked:
            return
            
        if snap and self.snap_to_grid and self.grid_size > 1 and not w.is_relative:
            x = (x // self.grid_size) * self.grid_size
            y = (y // self.grid_size) * self.grid_size
            width = max(self.grid_size, (width // self.grid_size) * self.grid_size)
            height = max(self.grid_size, (height // self.grid_size) * self.grid_size)
            
        w.x = max(0, x)
        w.y = max(0, y)
        w.width = max(10, width)
        w.height = max(10, height)
        
        if w.is_relative or self.is_relative_mode:
            w.is_relative = True
            self.calculate_relative_coordinates(widget_id)

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

    # --------------------------------------------------------------------------
    # Clipboard & Locking Operations
    # --------------------------------------------------------------------------
    def copy_selected(self) -> None:
        """Serialize selected widgets and all their descendants to clipboard."""
        if not self.selected_ids:
            return
        all_ids: List[str] = []
        for wid in self.selected_ids:
            if wid in self.widgets and wid not in all_ids:
                all_ids.append(wid)
                for desc in self.get_all_descendants(wid):
                    if desc.id not in all_ids:
                        all_ids.append(desc.id)
        self._clipboard = [self.widgets[wid].to_dict() for wid in all_ids if wid in self.widgets]

    def cut_selected(self) -> None:
        """Serialize selected widgets + descendants to clipboard and remove from project."""
        self.copy_selected()
        self.remove_selected()

    def paste(self, offset: Tuple[int, int] = (20, 20)) -> List[str]:
        """
        Deserialize from _clipboard, assign new UUIDs, offset positions,
        add to state, and select pasted widgets. Returns list of new widget IDs.
        """
        if not self._clipboard:
            return []

        # First pass: map old id -> new id
        id_map: Dict[str, str] = {}
        for wdata in self._clipboard:
            old_id = wdata["id"]
            new_id = str(uuid.uuid4())[:8]
            id_map[old_id] = new_id

        pasted_instances: List[WidgetInstance] = []
        for wdata in self._clipboard:
            cloned_data = copy.deepcopy(wdata)
            old_id = cloned_data["id"]
            new_id = id_map[old_id]
            cloned_data["id"] = new_id

            # Update parent_id if parent was also in clipboard
            old_parent = cloned_data.get("parent_id")
            if old_parent in id_map:
                cloned_data["parent_id"] = id_map[old_parent]

            # Offset positions
            cloned_data["x"] = cloned_data.get("x", 0) + offset[0]
            cloned_data["y"] = cloned_data.get("y", 0) + offset[1]

            # New name to avoid duplicate identifiers
            wtype = cloned_data.get("widget_type", "widget")
            cloned_data["name"] = f"{wtype.lower()}_{new_id}"

            inst = WidgetInstance.from_dict(cloned_data)
            pasted_instances.append(inst)

        for inst in pasted_instances:
            self.widgets[inst.id] = inst
            self.widget_order.append(inst.id)

        # Select the newly pasted widgets
        self.selected_ids = [inst.id for inst in pasted_instances]
        self.push_state()
        return self.selected_ids

    def toggle_lock_selected(self) -> None:
        """Toggle the locked state of selected widgets."""
        if not self.selected_ids:
            return
        selected_widgets = [self.widgets[wid] for wid in self.selected_ids if wid in self.widgets]
        if not selected_widgets:
            return
        all_locked = all(w.locked for w in selected_widgets)
        new_locked = not all_locked
        for w in selected_widgets:
            w.locked = new_locked
        self.push_state()

    def fill_parent_container(self, widget_id: str) -> None:
        """Resizes the widget to fill its parent container (or root canvas)."""
        if widget_id not in self.widgets:
            return
        w = self.widgets[widget_id]
        if w.locked:
            return
        if w.parent_id and w.parent_id in self.widgets:
            parent = self.widgets[w.parent_id]
            w.x = parent.x
            w.y = parent.y
            w.width = parent.width
            w.height = parent.height
        else:
            w.x = 0
            w.y = 0
            w.width = self.width
            w.height = self.height
        
        w.is_relative = True
        w.rel_x = 0.0
        w.rel_y = 0.0
        w.rel_width = 1.0
        w.rel_height = 1.0
        self.push_state()

    def calculate_relative_coordinates(self, widget_id: str) -> Tuple[float, float, float, float]:
        """
        Calculates and updates (rel_x, rel_y, rel_width, rel_height) for a widget
        relative to its parent container (or root canvas if parent_id is None).
        Returns (rel_x, rel_y, rel_width, rel_height).
        """
        if widget_id not in self.widgets:
            return (0.0, 0.0, 0.0, 0.0)
        w = self.widgets[widget_id]
        if w.parent_id and w.parent_id in self.widgets:
            parent = self.widgets[w.parent_id]
            pw = max(1, parent.width)
            ph = max(1, parent.height)
            rel_x = max(0.0, (w.x - parent.x) / pw)
            rel_y = max(0.0, (w.y - parent.y) / ph)
            rel_w = min(1.0, max(0.0, w.width / pw))
            rel_h = min(1.0, max(0.0, w.height / ph))
        else:
            pw = max(1, self.width)
            ph = max(1, self.height)
            rel_x = max(0.0, w.x / pw)
            rel_y = max(0.0, w.y / ph)
            rel_w = min(1.0, max(0.0, w.width / pw))
            rel_h = min(1.0, max(0.0, w.height / ph))

        w.rel_x = round(rel_x, 4)
        w.rel_y = round(rel_y, 4)
        w.rel_width = round(rel_w, 4)
        w.rel_height = round(rel_h, 4)
        return (w.rel_x, w.rel_y, w.rel_width, w.rel_height)

    def calculate_absolute_coordinates(self, widget_id: str) -> Tuple[int, int, int, int]:
        """
        Calculates and updates (x, y, width, height) from relative coordinates.
        Returns (x, y, width, height).
        """
        if widget_id not in self.widgets:
            return (0, 0, 0, 0)
        w = self.widgets[widget_id]
        if w.rel_x is None or w.rel_y is None:
            return (w.x, w.y, w.width, w.height)
        if w.parent_id and w.parent_id in self.widgets:
            parent = self.widgets[w.parent_id]
            pw = parent.width
            ph = parent.height
            px = parent.x
            py = parent.y
        else:
            pw = self.width
            ph = self.height
            px = 0
            py = 0

        w.x = int(px + w.rel_x * pw)
        w.y = int(py + w.rel_y * ph)
        if w.rel_width is not None:
            w.width = max(10, int(w.rel_width * pw))
        if w.rel_height is not None:
            w.height = max(10, int(w.rel_height * ph))
        return (w.x, w.y, w.width, w.height)

    def set_relative_mode(self, enabled: bool) -> None:
        """Sets relative placement mode and updates all widgets' relative coordinates."""
        self.is_relative_mode = enabled
        if enabled:
            for wid in self.widgets:
                self.widgets[wid].is_relative = True
                self.calculate_relative_coordinates(wid)
        self.push_state()

