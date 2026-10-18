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
        
        # History and notifications
        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []
        self._listeners: List[Callable[[], None]] = []
        self.is_dragging: bool = False
        
        # Save initial state snapshot
        self._record_snapshot()

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register a callback for when state changes without duplicates."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        """Unregister a callback."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def clear_listeners(self) -> None:
        """Remove all registered callbacks."""
        self._listeners.clear()

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
            "menus": copy.deepcopy({k: v.to_dict() for k, v in self.menus.items()}),
            "popup_menus": copy.deepcopy({k: v.to_dict() for k, v in self.popup_menus.items()}),
            "widgets": [copy.deepcopy(w.to_dict()) for w in [self.widgets[wid] for wid in self.widget_order if wid in self.widgets]],
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
        
        self.menus = {k: MenuBarSpec.from_dict(copy.deepcopy(v)) for k, v in (snapshot.get("menus") or {}).items()}
        self.popup_menus = {k: MenuBarSpec.from_dict(copy.deepcopy(v)) for k, v in (snapshot.get("popup_menus") or {}).items()}
        
        self.widgets = {}
        self.widget_order = []
        for idx, wdata in enumerate(snapshot.get("widgets") or []):
            widget = WidgetInstance.from_dict(copy.deepcopy(wdata))
            widget.z_order = idx
            self.widgets[widget.id] = widget
            self.widget_order.append(widget.id)
            
        self._sync_z_orders()
        self.selected_ids = [sid for sid in (snapshot.get("selected_ids") or []) if sid in self.widgets]
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
        self.is_dragging = False
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
    def is_valid_parent(self, widget_id: str, potential_parent_id: Optional[str]) -> bool:
        """
        Check if setting potential_parent_id as parent of widget_id would create
        a self-reference or circular hierarchy loop. Returns False if invalid.
        """
        if potential_parent_id is None:
            return True
        if potential_parent_id == widget_id:
            return False
        if potential_parent_id not in self.widgets:
            return False
        # Walk up from potential_parent_id to check if widget_id is an ancestor
        curr: Optional[str] = potential_parent_id
        visited: Set[str] = set()
        while curr is not None:
            if curr == widget_id:
                return False
            if curr in visited:
                break
            visited.add(curr)
            curr = self.widgets[curr].parent_id if curr in self.widgets else None
        return True

    def set_widget_parent(self, widget_id: str, new_parent_id: Optional[str]) -> None:
        """
        Reparent a widget to a new container (or root canvas if None).
        Enforces circular hierarchy prevention and raises ValueError on violation.
        """
        if widget_id not in self.widgets:
            raise ValueError(f"Widget '{widget_id}' not found in project state.")
        if new_parent_id is not None:
            if new_parent_id == widget_id:
                raise ValueError(f"Cannot parent widget '{widget_id}' to itself.")
            if new_parent_id not in self.widgets:
                raise ValueError(f"Parent widget '{new_parent_id}' does not exist.")
            if not self.is_valid_parent(widget_id, new_parent_id):
                raise ValueError(f"Cannot parent widget '{widget_id}' to its descendant '{new_parent_id}' (circular hierarchy).")
        self.widgets[widget_id].parent_id = new_parent_id
        self.push_state()

    def add_widget(self, widget: WidgetInstance, parent_id: Optional[str] = None) -> None:
        target_parent = parent_id if parent_id is not None else widget.parent_id
        if target_parent is not None:
            if target_parent == widget.id:
                raise ValueError(f"Cannot parent widget '{widget.id}' to itself.")
            if not self.is_valid_parent(widget.id, target_parent):
                raise ValueError(f"Cannot parent widget '{widget.id}' to its descendant '{target_parent}' (circular hierarchy).")
            widget.parent_id = target_parent

        # Snap coordinates if configured and not relative
        if self.snap_to_grid and self.grid_size > 1 and not widget.is_relative:
            widget.x = (widget.x // self.grid_size) * self.grid_size
            widget.y = (widget.y // self.grid_size) * self.grid_size
            
        self.widgets[widget.id] = widget
        if widget.id not in self.widget_order:
            self.widget_order.append(widget.id)
        self._sync_z_orders()
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

    def get_all_descendants(self, parent_id: str, visited: Optional[Set[str]] = None) -> List[WidgetInstance]:
        """Return all descendants of the specified parent_id recursively."""
        if visited is None:
            visited = set()
        visited.add(parent_id)
        descendants: List[WidgetInstance] = []
        direct_children = self.get_children(parent_id)
        for child in direct_children:
            if child.id not in visited:
                visited.add(child.id)
                descendants.append(child)
                descendants.extend(self.get_all_descendants(child.id, visited))
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
        self._sync_z_orders()
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
        self._sync_z_orders()
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
            self.is_dragging = False
            self.push_state()
        else:
            self.is_dragging = True
            self.notify()

    def duplicate_selected(self) -> List[str]:
        """Duplicates selected widgets and their descendants with offset."""
        if not self.selected_ids:
            return []
        saved_clipboard = copy.deepcopy(self._clipboard)
        self.copy_selected()
        new_ids = self.paste(offset=(20, 20))
        self._clipboard = saved_clipboard
        return new_ids

    # --------------------------------------------------------------------------
    # Clipboard & Locking Operations
    # --------------------------------------------------------------------------
    def copy_selected(self) -> None:
        """Serialize selected widgets and all their descendants to clipboard with true deep copies."""
        if not self.selected_ids:
            return
        all_ids: List[str] = []
        for wid in self.selected_ids:
            if wid in self.widgets and wid not in all_ids:
                all_ids.append(wid)
                for desc in self.get_all_descendants(wid):
                    if desc.id not in all_ids:
                        all_ids.append(desc.id)
        self._clipboard = [copy.deepcopy(self.widgets[wid].to_dict()) for wid in all_ids if wid in self.widgets]

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
            elif old_parent not in self.widgets:
                cloned_data["parent_id"] = None

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

        self._sync_z_orders()
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

    # --------------------------------------------------------------------------
    # Z-Order (Stacking Order) Management
    # --------------------------------------------------------------------------
    def _sync_z_orders(self) -> None:
        """Synchronizes z_order attribute on all widgets with their index in widget_order."""
        for idx, wid in enumerate(self.widget_order):
            if wid in self.widgets:
                self.widgets[wid].z_order = idx

    def bring_to_front(self, widget_id: str) -> None:
        """Moves widget and all its descendants to the top of widget_order (Z-order)."""
        if widget_id not in self.widgets or widget_id not in self.widget_order:
            return
        desc_ids = {d.id for d in self.get_all_descendants(widget_id)}
        subtree = [wid for wid in self.widget_order if wid == widget_id or wid in desc_ids]
        if not subtree:
            return
        for wid in subtree:
            self.widget_order.remove(wid)
        self.widget_order.extend(subtree)
        self._sync_z_orders()
        self.push_state()

    def send_to_back(self, widget_id: str) -> None:
        """Moves widget and all its descendants to the bottom of widget_order (Z-order)."""
        if widget_id not in self.widgets or widget_id not in self.widget_order:
            return
        desc_ids = {d.id for d in self.get_all_descendants(widget_id)}
        subtree = [wid for wid in self.widget_order if wid == widget_id or wid in desc_ids]
        if not subtree:
            return
        for wid in subtree:
            self.widget_order.remove(wid)
        self.widget_order = subtree + self.widget_order
        self._sync_z_orders()
        self.push_state()

    def bring_forward(self, widget_id: str) -> None:
        """Moves widget and all its descendants one position forward past the next widget block."""
        if widget_id not in self.widgets or widget_id not in self.widget_order:
            return
        desc_ids = {d.id for d in self.get_all_descendants(widget_id)}
        subtree = [wid for wid in self.widget_order if wid == widget_id or wid in desc_ids]
        last_subtree_idx = max(self.widget_order.index(wid) for wid in subtree)
        if last_subtree_idx >= len(self.widget_order) - 1:
            return  # Already at the front
        next_wid = self.widget_order[last_subtree_idx + 1]
        next_desc_ids = {d.id for d in self.get_all_descendants(next_wid)}
        target_idx = max(self.widget_order.index(wid) for wid in [next_wid] + [wid for wid in self.widget_order if wid in next_desc_ids])
        target_wid = self.widget_order[target_idx]

        for wid in subtree:
            self.widget_order.remove(wid)
        insert_idx = self.widget_order.index(target_wid) + 1
        self.widget_order[insert_idx:insert_idx] = subtree
        self._sync_z_orders()
        self.push_state()

    def send_backward(self, widget_id: str) -> None:
        """Moves widget and all its descendants one position backward past the preceding widget block."""
        if widget_id not in self.widgets or widget_id not in self.widget_order:
            return
        desc_ids = {d.id for d in self.get_all_descendants(widget_id)}
        subtree = [wid for wid in self.widget_order if wid == widget_id or wid in desc_ids]
        first_subtree_idx = min(self.widget_order.index(wid) for wid in subtree)
        if first_subtree_idx <= 0:
            return  # Already at the back
        prev_wid = self.widget_order[first_subtree_idx - 1]
        prev_desc_ids = {d.id for d in self.get_all_descendants(prev_wid)}
        target_idx = min(self.widget_order.index(wid) for wid in [prev_wid] + [wid for wid in self.widget_order if wid in prev_desc_ids])
        target_wid = self.widget_order[target_idx]

        for wid in subtree:
            self.widget_order.remove(wid)
        insert_idx = self.widget_order.index(target_wid)
        self.widget_order[insert_idx:insert_idx] = subtree
        self._sync_z_orders()
        self.push_state()


